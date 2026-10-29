import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import type { RegisterOptions } from "react-hook-form";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { useScreening } from "../../context/ScreeningContext";
import { confirmKtp } from "../../api/services";
import type { KtpFields } from "../../api/services";
import { getErrorMessage } from "../../api/client";
import { useToast } from "../../components/Common";
import FlowLayout from "../../components/FlowLayout";
import type { KtpOcrResult, KtpScanResult } from "../../api/types";

type FormValues = KtpFields;
type Name = keyof FormValues;

const JENIS_KELAMIN = ["LAKI-LAKI", "PEREMPUAN"];
const AGAMA = ["ISLAM", "KRISTEN", "KATOLIK", "HINDU", "BUDDHA", "KONGHUCU"];
const STATUS = ["BELUM KAWIN", "KAWIN", "CERAI HIDUP", "CERAI MATI"];
const WARGA = ["WNI", "WNA"];

const DATE_RE = /(\d{2})[-/. ](\d{2})[-/. ](\d{4})/;

interface FieldDef {
  name: Name; label: string; kind?: "text" | "select" | "textarea";
  options?: string[]; placeholder?: string; full?: boolean; numeric?: boolean; maxLength?: number;
}
const SECTIONS: { title: string; fields: FieldDef[] }[] = [
  { title: "Identitas", fields: [
    { name: "nik", label: "NIK (16 digit)", full: true, numeric: true, maxLength: 16, placeholder: "16 digit angka" },
    { name: "nama", label: "Nama sesuai KTP", full: true },
  ] },
  { title: "Kelahiran", fields: [
    { name: "tempat_lahir", label: "Tempat lahir" },
    { name: "tanggal_lahir", label: "Tanggal lahir", placeholder: "DD-MM-YYYY" },
    { name: "jenis_kelamin", label: "Jenis kelamin", kind: "select", options: JENIS_KELAMIN },
    { name: "agama", label: "Agama", kind: "select", options: AGAMA },
  ] },
  { title: "Alamat", fields: [
    { name: "alamat", label: "Alamat", kind: "textarea", full: true },
    { name: "rt_rw", label: "RT/RW", placeholder: "001/002" },
    { name: "kelurahan", label: "Kelurahan/Desa" },
    { name: "kecamatan", label: "Kecamatan", full: true },
  ] },
  { title: "Lainnya", fields: [
    { name: "status_perkawinan", label: "Status perkawinan", kind: "select", options: STATUS },
    { name: "kewarganegaraan", label: "Kewarganegaraan", kind: "select", options: WARGA },
    { name: "pekerjaan_ktp", label: "Pekerjaan", full: true },
  ] },
];
const ALL_NAMES: Name[] = SECTIONS.flatMap((s) => s.fields.map((f) => f.name));

function validDate(v: string) {
  const m = v.match(/^(\d{2})[-/](\d{2})[-/](\d{4})$/);
  if (!m) return "Format DD-MM-YYYY";
  const [d, mo, y] = [Number(m[1]), Number(m[2]), Number(m[3])];
  if (mo < 1 || mo > 12 || d < 1 || d > 31 || y < 1900 || y > new Date().getFullYear()) return "Tanggal tidak valid";
  return true;
}

const RULES: Partial<Record<Name, RegisterOptions<FormValues, Name>>> = {
  nik: { pattern: { value: /^[0-9]{16}$/, message: "NIK harus 16 digit angka" } },
  tanggal_lahir: { validate: (v) => validDate(String(v ?? "").trim()) },
};

/** Map an OCR string onto one of the fixed options. Compares letters only, so
 *  "LAKILAKI" or "Laki laki" still match "LAKI-LAKI" (KTP prints these in capitals). */
function matchOption(value: string | null | undefined, options: string[]): string {
  const letters = (t: string) => t.toUpperCase().replace(/[^A-Z]/g, "");
  const v = letters(value ?? "");
  if (v.length < 3) return "";
  return options.find((o) => letters(o) === v) ?? options.find((o) => v.includes(letters(o)) || letters(o).includes(v)) ?? "";
}

/** OCR often returns "BOGOR, 01-02-1995" on one line; split it and drop leaked labels. */
function splitBirth(ocr?: KtpOcrResult) {
  const src = `${ocr?.tempat_lahir ?? ""} ${ocr?.tanggal_lahir ?? ""}`;
  const m = src.match(DATE_RE);
  const date = m ? `${m[1]}-${m[2]}-${m[3]}` : "";
  let place = (ocr?.tempat_lahir ?? "").replace(DATE_RE, "").replace(/[,\s]+$/, "").trim();
  if (/lahir/i.test(place) || place.length < 2) place = "";
  return { place, date };
}

/** Hasil /api/ktp/scan -> bentuk yang dipakai formulir (tanggal YYYY-MM-DD -> DD-MM-YYYY, pekerjaan -> pekerjaan_ktp). */
function scanToOcr(scan: KtpScanResult): KtpOcrResult {
  const d = scan.data;
  const iso = d.tanggal_lahir?.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  return {
    success: scan.success, ktp_document_id: null, nik: d.nik, nama: d.nama, tempat_lahir: d.tempat_lahir,
    tanggal_lahir: iso ? `${iso[3]}-${iso[2]}-${iso[1]}` : null,
    jenis_kelamin: d.jenis_kelamin, alamat: d.alamat, rt_rw: d.rt_rw, kelurahan: d.kelurahan,
    kecamatan: d.kecamatan, agama: d.agama, status_perkawinan: d.status_perkawinan,
    pekerjaan_ktp: d.pekerjaan, kewarganegaraan: d.kewarganegaraan,
    confidence: scan.overall_confidence == null ? null : Math.round(scan.overall_confidence * 100),
    message: scan.message, ocr_provider: scan.provider,
  };
}

type Flag = { kind: "ok" | "review" | "unreadable" | "edited"; text: string };
const FLAG_TEXT: Record<Flag["kind"], string> = {
  ok: "✓ Data berhasil dibaca",
  review: "⚠ Periksa kembali",
  unreadable: "✕ Tidak terbaca",
  edited: "✓ Sudah Anda periksa",
};

function initialValues(ocr?: KtpOcrResult): FormValues {
  const { place, date } = splitBirth(ocr);
  return {
    nik: ocr?.nik ?? "",
    nama: ocr?.nama ?? "",
    tempat_lahir: place,
    tanggal_lahir: date,
    jenis_kelamin: matchOption(ocr?.jenis_kelamin, JENIS_KELAMIN),
    alamat: ocr?.alamat ?? "",
    rt_rw: ocr?.rt_rw ?? "",
    kelurahan: ocr?.kelurahan ?? "",
    kecamatan: ocr?.kecamatan ?? "",
    agama: matchOption(ocr?.agama, AGAMA),
    status_perkawinan: matchOption(ocr?.status_perkawinan, STATUS),
    pekerjaan_ktp: ocr?.pekerjaan_ktp ?? "",
    kewarganegaraan: matchOption(ocr?.kewarganegaraan, WARGA),
  };
}

export default function KtpConfirm() {
  const location = useLocation();
  const navigate = useNavigate();
  const { participantId, refreshProfile } = useScreening();
  const { showToast } = useToast();
  const [submitting, setSubmitting] = useState(false);

  const nav = location.state as { ocr?: KtpOcrResult; scan?: KtpScanResult; manual?: boolean } | null;
  const scan = nav?.scan;
  const manual = !!nav?.manual;
  const ocr = useMemo(() => (scan ? scanToOcr(scan) : nav?.ocr), [scan, nav?.ocr]);
  const initial = useMemo(() => initialValues(ocr), [ocr]);

  const { register, handleSubmit, watch, formState: { errors } } = useForm<FormValues>({
    defaultValues: initial,
    mode: "onTouched",
  });

  const values = watch();
  const filled = ALL_NAMES.filter((n) => String(values[n] ?? "").trim() !== "").length;
  const total = ALL_NAMES.length;

  if (!participantId) return <Navigate to="/data-diri" replace />;
  // The scan result travels in router state, so a refresh loses it. Start again from the photo step.
  if (!ocr && !manual) return <Navigate to="/profil/ktp" replace />;

  /** Indikator per kolom: dari hasil AI, atau "sudah diperiksa" bila user mengubah nilainya. */
  const flagFor = (name: Name): Flag | null => {
    if (!scan) return null;
    if (String(values[name] ?? "").trim() !== String(initial[name] ?? "").trim()) return { kind: "edited", text: FLAG_TEXT.edited };
    const st = scan.field_status[name === "pekerjaan_ktp" ? "pekerjaan" : name];
    // kolom kosong namun sudah dipilih/diketik user ditangani oleh cabang "edited" di atas
    if (st === "ok" || st === "review" || st === "unreadable") return { kind: st, text: FLAG_TEXT[st] };
    return null;
  };

  const onSubmit = async (v: FormValues) => {
    setSubmitting(true);
    try {
      const clean = Object.fromEntries(ALL_NAMES.map((n) => [n, String(v[n]).trim()])) as unknown as FormValues;
      await confirmKtp({
        participant_id: participantId, ...clean,
        ...(scan ? { scan_provider: scan.provider, scan_confidence: Math.round((scan.overall_confidence ?? 0) * 100) } : {}),
      });
      await refreshProfile();
      showToast("KTP berhasil dikonfirmasi", "success");
      navigate("/profil", { replace: true });
    } catch (err) {
      showToast(getErrorMessage(err), "error");
    } finally {
      setSubmitting(false);
    }
  };

  const renderField = (f: FieldDef) => {
    const id = `f-${f.name}`;
    const rules: RegisterOptions<FormValues, Name> = {
      required: f.kind === "select" ? "Pilih salah satu" : "Wajib diisi",
      validate: (val) => String(val ?? "").trim() !== "" || "Wajib diisi",
      ...RULES[f.name],
    };
    // when a field has its own validate, keep the "not blank" check too
    if (f.name === "tanggal_lahir") rules.validate = (val) => (String(val ?? "").trim() === "" ? "Wajib diisi" : validDate(String(val).trim()));
    const err = errors[f.name];
    const ok = String(values[f.name] ?? "").trim() !== "" && !err;
    const flag = flagFor(f.name);

    return (
      <div key={f.name} className={`form-group ${f.full ? "field-full" : ""} ${err ? "has-error" : ok ? "is-ok" : ""} ${flag && !err ? `fg-${flag.kind}` : ""}`}>
        <div className="label-row">
          <label htmlFor={id}>{f.label}</label>
          {flag && <span className={`field-flag flag-${flag.kind}`}>{flag.text}</span>}
        </div>
        {f.kind === "select" ? (
          <select id={id} className="form-control" {...register(f.name, rules)}>
            <option value="">Pilih...</option>
            {f.options!.map((o) => <option key={o} value={o}>{o}</option>)}
          </select>
        ) : f.kind === "textarea" ? (
          <textarea id={id} className="form-control" rows={2} {...register(f.name, rules)} />
        ) : (
          <input id={id} className="form-control" placeholder={f.placeholder} maxLength={f.maxLength}
            inputMode={f.numeric ? "numeric" : undefined} autoComplete="off" {...register(f.name, rules)} />
        )}
        {err && <div className="form-error">{String(err.message ?? "Wajib diisi")}</div>}
      </div>
    );
  };

  return (
    <FlowLayout embedded step={2} wide>
      <Link className="back-link" to="/profil/ktp">&larr; {manual ? "Kembali ke scan KTP" : "Scan ulang KTP"}</Link>
      <h1 className="flow-title">Periksa data KTP</h1>
      <p className="flow-sub">
        {manual
          ? "Isi semua kolom sesuai KTP Anda."
          : "Hasil pembacaan otomatis bisa keliru. Cocokkan dengan KTP Anda dan lengkapi semua kolom sebelum lanjut."}
      </p>

      {ocr && !ocr.success && (
        <div className="notice">Data tidak berhasil dibaca sepenuhnya. Silakan lengkapi secara manual.</div>
      )}
      {scan && (
        <div className="notice" role="status">
          {scan.provider === "tesseract"
            ? (scan.fallback_used ? "AI tidak tersedia, data dibaca dengan OCR Tesseract (akurasi terbatas). " : "Data dibaca dengan OCR Tesseract (akurasi terbatas). ")
            : "Data KTP dibaca oleh AI. "}Tanda <strong>✓</strong> = berhasil dibaca, <strong>⚠</strong> = periksa kembali,{" "}
          <strong>✕</strong> = tidak terbaca (isi manual). Data baru disimpan setelah Anda menekan Konfirmasi.
          {scan.warnings.length > 0 && (
            <ul className="scan-warnings">{scan.warnings.map((w) => <li key={w}>{w}</li>)}</ul>
          )}
        </div>
      )}
      {!scan && ocr?.ocr_provider && (
        <div className="notice" style={{ marginTop: 8 }}>
          Dibaca dengan {ocr.ocr_provider === "vlm" ? "AI (VLM)" : "Tesseract"}
          {ocr.fallback_used ? " — VLM tidak tersedia, otomatis pakai Tesseract." : ""} Tetap
          periksa semua kolom sebelum konfirmasi.
        </div>
      )}

      <div className="meter" aria-live="polite">
        <div className="meter-row">
          <span>{filled === total ? "Semua kolom terisi" : `${filled} dari ${total} kolom terisi`}</span>
          <strong>{Math.round((filled / total) * 100)}%</strong>
        </div>
        <div className="progress-track"><div className="progress-fill" style={{ width: `${(filled / total) * 100}%` }} /></div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} noValidate>
        {SECTIONS.map((s) => (
          <section className="form-section rise" key={s.title}>
            <h2 className="form-section-title">{s.title}</h2>
            <div className="field-grid">{s.fields.map(renderField)}</div>
          </section>
        ))}

        <button className="btn btn-primary btn-block btn-lg" disabled={submitting} type="submit">
          {submitting ? "Menyimpan..." : "Konfirmasi KTP"}
        </button>
        {scan && (
          <button className="btn btn-secondary btn-block" style={{ marginTop: 10 }} type="button"
            disabled={submitting} onClick={() => navigate("/profil/ktp")}>
            Scan Ulang
          </button>
        )}
      </form>
    </FlowLayout>
  );
}
