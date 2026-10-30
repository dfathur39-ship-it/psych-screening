import { WaveScene } from "../../components/Illustrations";
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { MessageList, Composer } from "../../components/Chat";
import { ConfirmDialog, Spinner, useToast } from "../../components/Common";
import { usePolling } from "../../hooks/usePolling";
import { useProfile } from "../../context/ScreeningContext";
import { createSupportThread, getSupportMessages, sendSupportMessage } from "../../api/services";
import { getErrorMessage } from "../../api/client";
import type { SupportThreadState } from "../../api/types";

interface Stored { id: string; token: string }

// One conversation per participant, so two people sharing a browser never see each other's chat.
const storageKey = (participantId: string) => `support_thread_${participantId}`;

function loadStored(key: string): Stored | null {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as Stored) : null;
  } catch {
    return null;
  }
}

/** Hubungi kami. The sender is the participant's data diri, so there is nothing to type but the message. */
export default function Contact() {
  const profile = useProfile();
  const key = storageKey(profile.id);
  const { showToast } = useToast();
  const [stored, setStored] = useState<Stored | null>(() => loadStored(key));
  const [thread, setThread] = useState<SupportThreadState | null>(null);
  const [checking, setChecking] = useState(stored !== null);
  const [confirmNew, setConfirmNew] = useState(false);

  const [message, setMessage] = useState("");
  const [creating, setCreating] = useState(false);

  const forget = useCallback(() => {
    localStorage.removeItem(key);
    setStored(null);
    setThread(null);
  }, [key]);

  const refresh = useCallback(async () => {
    if (!stored) return;
    try {
      setThread(await getSupportMessages(stored.id, stored.token));
    } catch (err) {
      // 404 = conversation no longer exists (or the token is wrong): start fresh.
      if ((err as { response?: { status?: number } })?.response?.status === 404) forget();
    }
  }, [stored, forget]);

  useEffect(() => {
    if (!stored) return;
    void refresh().finally(() => setChecking(false));
  }, [stored, refresh]);

  usePolling(refresh, 4000, stored !== null);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim()) return;
    setCreating(true);
    try {
      const res = await createSupportThread({ participant_id: profile.id, message: message.trim() });
      const next: Stored = { id: res.thread_id, token: res.token };
      localStorage.setItem(key, JSON.stringify(next));
      setStored(next);
      setThread({ thread_id: res.thread_id, status: res.status, messages: res.messages });
      setMessage("");
    } catch (err) {
      showToast(getErrorMessage(err), "error");
    } finally {
      setCreating(false);
    }
  };

  const handleSend = async (text: string) => {
    if (!stored) return;
    try {
      setThread(await sendSupportMessage(stored.id, stored.token, text));
    } catch (err) {
      showToast(getErrorMessage(err), "error");
      throw err;
    }
  };

  const waiting = thread !== null && !thread.messages.some((m) => m.sender === "admin");

  return (
    <main className="page-narrow">
      <div className="page-head">
        <div>
          <h1>Hubungi kami</h1>
          <p className="page-lead">
            Tanyakan apa saja soal skrining ini. Admin membalas langsung di sini.
            Cek juga <Link to="/bantuan">halaman Bantuan</Link>, siapa tahu jawabannya sudah ada.
          </p>
        </div>
        <div className="spot" aria-hidden="true"><WaveScene /></div>
      </div>

      {checking ? (
        <Spinner label="Membuka percakapan..." />
      ) : !stored || !thread ? (
        <form className="card" onSubmit={handleCreate}>
          <div className="sender-card" aria-label="Pengirim">
            <span className="sender-label">Dikirim sebagai</span>
            <strong>{profile.nama}</strong>
            <span>{[profile.email, profile.no_hp].filter(Boolean).join(" · ")}</span>
          </div>
          <div className="form-group">
            <label htmlFor="c-msg">Pesan</label>
            <textarea id="c-msg" className="form-control" rows={4} maxLength={2000} value={message}
              onChange={(e) => setMessage(e.target.value)} required autoFocus />
            <div className="form-hint">Admin mengenali kamu dari data diri ini dan bisa menghubungi lewat email atau nomor HP di atas.</div>
          </div>
          <button className="btn btn-primary btn-block" type="submit" disabled={creating || !message.trim()}>
            {creating ? "Mengirim..." : "Kirim pesan"}
          </button>
        </form>
      ) : (
        <>
          <div className="chat-card">
            <div className="chat-head">
              <div>
                <strong>Tim admin</strong>
                <span>Percakapan sebagai {profile.nama}</span>
              </div>
              <button className="link-btn" onClick={() => setConfirmNew(true)}>Percakapan baru</button>
            </div>
            <MessageList
              messages={thread.messages} me="visitor" theirLabel="Admin"
              note={waiting ? "Pesan kamu sudah terkirim. Menunggu balasan admin." : undefined}
            />
            {thread.status === "closed" ? (
              <div className="chat-closed">
                <p>Admin sudah menyelesaikan percakapan ini. Untuk chat lagi, mulai percakapan baru.</p>
                <button className="btn btn-primary" onClick={() => setConfirmNew(true)}>Mulai percakapan baru</button>
              </div>
            ) : (
              <Composer onSend={handleSend} />
            )}
          </div>
          <p className="form-hint" style={{ textAlign: "center", marginTop: 12 }}>
            Kamu boleh menutup halaman ini. Percakapan tetap tersimpan di perangkat ini dan balasan admin muncul saat kamu kembali.
          </p>
        </>
      )}

      <ConfirmDialog
        open={confirmNew}
        title="Mulai percakapan baru"
        message="Percakapan ini tidak akan tampil lagi di perangkatmu. Admin tetap menyimpan riwayatnya. Lanjutkan?"
        onConfirm={() => { setConfirmNew(false); forget(); }}
        onCancel={() => setConfirmNew(false)}
      />
    </main>
  );
}
