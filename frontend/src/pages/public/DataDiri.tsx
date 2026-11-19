import { useForm } from "react-hook-form";
import { Navigate, useLocation } from "react-router-dom";
import { useState } from "react";
import { useScreening } from "../../context/ScreeningContext";
import { createParticipant } from "../../api/services";
import { getErrorMessage } from "../../api/client";
import { useToast } from "../../components/Common";
import FlowLayout from "../../components/FlowLayout";
import { WaveScene } from "../../components/Illustrations";

interface FormValues {
  nama: string;
  email: string;
  usia: number;
  jabatan: string;
  no_hp: string;
}

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

export default function DataDiri() {
  const { register, handleSubmit, formState: { errors } } = useForm<FormValues>();
  const location = useLocation();
  const { participantId, setParticipantId } = useScreening();
  const { showToast } = useToast();
  const [submitting, setSubmitting] = useState(false);

  // MemberLayout sends visitors here with the page they wanted (e.g. /kontak) so we can return them to it.
  const from = (location.state as { from?: string } | null)?.from;

  // Once data diri is saved, participantId is set and this redirect takes the visitor onward.
  if (participantId) return <Navigate to={from && from !== "/data-diri" ? from : "/beranda"} replace />;

  const onSubmit = async (values: FormValues) => {
    setSubmitting(true);
    try {
      const participant = await createParticipant({
        nama: values.nama.trim(),
        email: values.email.trim(),
        usia: Number(values.usia),
        jabatan: values.jabatan.trim(),
        no_hp: values.no_hp.trim(),
      });
      setParticipantId(participant.id);
    } catch (err) {
      showToast(getErrorMessage(err), "error");
      setSubmitting(false);
    }
  };

  return (
    <FlowLayout>
      <div className="flow-hello">
        <div className="spot"><WaveScene /></div>
        <div>
          <h1 className="flow-title">Halo, kenalan dulu yuk</h1>
          <p className="flow-sub">Isi data dirimu dulu. Nama dan usia harus sama dengan KTP-mu, karena nanti dicocokkan saat pindai KTP. Mendaftar lagi dengan data yang sama akan masuk ke akun yang sama.</p>
        </div>
      </div>

      {from && (
        <div className="notice">Isi data dirimu dulu supaya bisa lanjut. Tidak sampai satu menit.</div>
      )}

      <form className="stagger" onSubmit={handleSubmit(onSubmit)} noValidate>
        <div className="form-group">
          <label htmlFor="nama">Nama lengkap</label>
          <input id="nama" className="form-control" autoComplete="name" autoFocus
            {...register("nama", { required: "Nama wajib diisi", minLength: { value: 2, message: "Nama terlalu pendek" } })} />
          {errors.nama && <div className="form-error">{errors.nama.message}</div>}
        </div>

        <div className="form-group">
          <label htmlFor="email">Email</label>
          <input id="email" type="email" inputMode="email" className="form-control" placeholder="nama@contoh.com" autoComplete="email"
            {...register("email", {
              required: "Email wajib diisi",
              maxLength: { value: 255, message: "Email terlalu panjang" },
              pattern: { value: EMAIL_RE, message: "Format email tidak valid" },
            })} />
          {errors.email && <div className="form-error">{errors.email.message}</div>}
        </div>

        <div className="field-grid">
          <div className="form-group">
            <label htmlFor="usia">Usia</label>
            <input id="usia" type="number" inputMode="numeric" className="form-control" placeholder="Tahun"
              {...register("usia", {
                required: "Usia wajib diisi",
                min: { value: 15, message: "Usia minimal 15 tahun" },
                max: { value: 100, message: "Usia tidak valid" },
              })} />
            {errors.usia && <div className="form-error">{errors.usia.message}</div>}
          </div>

          <div className="form-group">
            <label htmlFor="no_hp">Nomor HP</label>
            <input id="no_hp" type="tel" inputMode="tel" className="form-control" placeholder="08xxxxxxxxxx" autoComplete="tel"
              {...register("no_hp", {
                required: "Nomor HP wajib diisi",
                minLength: { value: 8, message: "Nomor HP terlalu pendek" },
                pattern: { value: /^[0-9+\-\s]+$/, message: "Nomor HP tidak valid" },
              })} />
            {errors.no_hp && <div className="form-error">{errors.no_hp.message}</div>}
          </div>
        </div>

        <div className="form-group">
          <label htmlFor="jabatan">Jabatan</label>
          <input id="jabatan" className="form-control" placeholder="Contoh: Senior Software Engineer"
            {...register("jabatan", { required: "Jabatan wajib diisi" })} />
          <div className="form-hint">Ketik jabatanmu sendiri, tidak harus sesuai daftar baku.</div>
          {errors.jabatan && <div className="form-error">{errors.jabatan.message}</div>}
        </div>

        <button className="btn btn-primary btn-block btn-lg" disabled={submitting} type="submit">
          {submitting ? "Sebentar, lagi disimpan..." : "Simpan dan lanjut"}
        </button>
      </form>
    </FlowLayout>
  );
}
