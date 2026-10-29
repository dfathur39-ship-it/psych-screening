import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import PublicHeader from "../../components/PublicHeader";

interface Faq { q: string; a: string }
interface Group { title: string; items: Faq[] }

const GROUPS: Group[] = [
  {
    title: "Sebelum mulai",
    items: [
      { q: "Apa itu skrining ini?", a: "Skrining awal untuk melihat bagaimana kondisi psikologis Anda terkait pekerjaan. Hasilnya berupa skor dan kategori, bukan diagnosis psikologis atau medis." },
      { q: "Untuk apa email dan nomor HP saya?", a: "Untuk mengenali Anda saat memakai Hubungi kami dan agar admin bisa menghubungi Anda bila perlu. Anda tidak perlu kata sandi: data diri di perangkat ini dipakai untuk masuk." },
      { q: "Berapa lama pengerjaannya?", a: "Sekitar 10 menit. Jumlah pertanyaan berbeda-beda menurut jabatan Anda." },
      { q: "Jabatan saya tidak ada di daftar. Bagaimana?", a: "Tidak masalah. Ketik jabatan Anda apa adanya, misalnya \"Senior Software Engineer\". Kalau belum ada pertanyaan khusus untuk jabatan itu, Anda mendapat pertanyaan umum sehingga tetap bisa menyelesaikan skrining." },
    ],
  },
  {
    title: "Scan KTP",
    items: [
      { q: "Kenapa saya perlu mengisi data KTP?", a: "Untuk memastikan identitas peserta. Konfirmasi KTP dilakukan di halaman Profil dan wajib selesai sebelum Anda bisa mulai menjawab pertanyaan. Data dibaca otomatis dari foto, lalu Anda memeriksa dan mengoreksinya sebelum disimpan." },
      { q: "Tombol Mulai skrining belum bisa ditekan. Kenapa?", a: "Tombol itu terbuka setelah KTP Anda dikonfirmasi. Buka Profil, pilih Scan KTP, lalu periksa dan konfirmasi datanya. Kalau Anda memfoto ulang KTP, datanya harus dikonfirmasi lagi." },
      { q: "KTP saya tidak terbaca atau hasilnya salah. Apa yang harus dilakukan?", a: "Pembacaan otomatis memang tidak selalu sempurna. Pakai cahaya yang cukup, letakkan KTP rata tanpa pantulan, dan pastikan seluruh kartu terlihat. Kalau tetap gagal, isi atau koreksi datanya langsung di halaman periksa data." },
      { q: "Foto KTP saya ditolak. Format apa yang diterima?", a: "JPG, PNG, atau WEBP dengan ukuran maksimal 5 MB. Foto iPhone berformat HEIC belum didukung. Ubah pengaturan kamera ke \"Paling Kompatibel\" atau ekspor fotonya ke JPG." },
      { q: "Apakah foto KTP saya disimpan?", a: "Secara bawaan tidak. Foto dihapus segera setelah dibaca, dan yang tersimpan hanya data teks yang Anda konfirmasi. Foto tidak pernah dapat diakses lewat tautan publik." },
    ],
  },
  {
    title: "Mengerjakan skrining",
    items: [
      { q: "Bagaimana kalau halaman ter-refresh di tengah jalan?", a: "Jawaban tersimpan setiap kali Anda memilih. Buka kembali halaman dari perangkat dan peramban yang sama, lalu Anda dilanjutkan dari pertanyaan yang belum dijawab." },
      { q: "Bisakah saya mengubah jawaban?", a: "Bisa, selama Anda belum menekan Selesai. Gunakan tombol Sebelumnya untuk kembali ke pertanyaan yang ingin diubah." },
      { q: "Kenapa saya tidak bisa menekan Selesai?", a: "Semua pertanyaan harus dijawab. Jika ada yang terlewat, Anda akan diarahkan ke pertanyaan pertama yang belum terisi." },
    ],
  },
  {
    title: "Hasil dan privasi",
    items: [
      { q: "Apa arti skor dan kategori saya?", a: "Kategori ditentukan dari total skor mengikuti pengaturan tim yang mengelola skrining ini. Anggap sebagai gambaran awal, bukan penilaian akhir. Untuk penilaian yang tepat, bicarakan dengan psikolog atau tenaga kesehatan." },
      { q: "Siapa yang bisa melihat hasil saya?", a: "Hanya admin yang berwenang. NIK Anda disamarkan di tampilan admin dan tidak ikut dalam ekspor data." },
    ],
  },
];

export default function Help() {
  const [query, setQuery] = useState("");

  const groups = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return GROUPS;
    return GROUPS
      .map((g) => ({ ...g, items: g.items.filter((i) => (i.q + " " + i.a).toLowerCase().includes(q)) }))
      .filter((g) => g.items.length > 0);
  }, [query]);

  return (
    <div className="lp">
      <PublicHeader />
      <main className="page-narrow">
        <h1>Bantuan</h1>
        <p className="page-lead">Jawaban untuk pertanyaan yang paling sering muncul.</p>

        <input
          className="form-control help-search" type="search" placeholder="Cari, misalnya: KTP, refresh, jabatan"
          value={query} onChange={(e) => setQuery(e.target.value)} aria-label="Cari bantuan"
        />

        {groups.length === 0 ? (
          <div className="card empty-state">
            <p>Tidak ada jawaban yang cocok dengan "{query}".</p>
            <Link className="btn btn-primary" to="/kontak">Tanya admin</Link>
          </div>
        ) : (
          groups.map((g) => (
            <section className="faq-group" key={g.title}>
              <h2>{g.title}</h2>
              {g.items.map((i) => (
                <details className="faq" key={i.q} open={query.trim() !== ""}>
                  <summary>{i.q}</summary>
                  <div className="faq-body">{i.a}</div>
                </details>
              ))}
            </section>
          ))
        )}

        <div className="callout">
          Jika Anda merasa sangat tertekan atau berpikir untuk menyakiti diri sendiri, jangan menunggu hasil skrining.
          Segera hubungi layanan kesehatan terdekat atau orang yang Anda percaya.
        </div>

        <div className="card help-cta">
          <div>
            <h3>Belum menemukan jawabannya?</h3>
            <p>Kirim pesan ke admin dan balasannya muncul langsung di halaman ini.</p>
          </div>
          <Link className="btn btn-primary" to="/kontak">Hubungi kami</Link>
        </div>
      </main>
    </div>
  );
}
