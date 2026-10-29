import { useCallback, useEffect, useRef, useState } from "react";
import { MessageList, Composer } from "../../components/Chat";
import { Spinner, EmptyState, useToast } from "../../components/Common";
import { usePolling } from "../../hooks/usePolling";
import { formatChatTime } from "../../lib/format";
import {
  listSupportThreads, getSupportThread, replySupportThread, setSupportThreadStatus,
} from "../../api/services";
import { getErrorMessage } from "../../api/client";
import type { AdminThreadItem, AdminThreadDetail } from "../../api/types";

type Filter = "open" | "closed" | "all";
const FILTERS: { key: Filter; label: string }[] = [
  { key: "open", label: "Terbuka" },
  { key: "closed", label: "Selesai" },
  { key: "all", label: "Semua" },
];

export default function Support() {
  const { showToast } = useToast();
  const [filter, setFilter] = useState<Filter>("open");
  const [threads, setThreads] = useState<AdminThreadItem[] | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<AdminThreadDetail | null>(null);
  const selectedRef = useRef<string | null>(null);

  const loadList = useCallback(async () => {
    try {
      setThreads((await listSupportThreads(filter)).items);
    } catch (err) {
      showToast(getErrorMessage(err), "error");
      setThreads((prev) => prev ?? []);
    }
  }, [filter, showToast]);

  const loadDetail = useCallback(async (id: string) => {
    try {
      const d = await getSupportThread(id);
      if (selectedRef.current === id) setDetail(d); // ignore late responses for a thread we already left
    } catch (err) {
      showToast(getErrorMessage(err), "error");
    }
  }, [showToast]);

  useEffect(() => { void loadList(); }, [loadList]);
  usePolling(loadList, 5000);

  useEffect(() => {
    selectedRef.current = selectedId;
    setDetail(null);
    if (selectedId) void loadDetail(selectedId);
  }, [selectedId, loadDetail]);
  usePolling(() => (selectedId ? loadDetail(selectedId) : undefined), 4000, selectedId !== null);

  const handleReply = async (text: string) => {
    if (!selectedId) return;
    try {
      const res = await replySupportThread(selectedId, text);
      setDetail((d) => (d ? { ...d, status: "open", messages: res.messages } : d));
      void loadList();
    } catch (err) {
      showToast(getErrorMessage(err), "error");
      throw err;
    }
  };

  const toggleStatus = async () => {
    if (!detail) return;
    const next = detail.status === "open" ? "closed" : "open";
    try {
      await setSupportThreadStatus(detail.id, next);
      setDetail({ ...detail, status: next });
      showToast(next === "closed" ? "Percakapan ditandai selesai" : "Percakapan dibuka kembali", "success");
      void loadList();
    } catch (err) {
      showToast(getErrorMessage(err), "error");
    }
  };

  return (
    <div>
      <div className="admin-topbar">
        <div>
          <h1 style={{ marginBottom: 4 }}>Pesan</h1>
          <p className="page-sub">Percakapan dari halaman Hubungi kami. Diperbarui otomatis.</p>
        </div>
      </div>

      <div className={`inbox ${selectedId ? "show-thread" : ""}`}>
        <aside className="inbox-list">
          <div className="inbox-tabs" role="tablist">
            {FILTERS.map((f) => (
              <button key={f.key} role="tab" aria-selected={filter === f.key}
                className={filter === f.key ? "active" : ""} onClick={() => { setFilter(f.key); setSelectedId(null); }}>
                {f.label}
              </button>
            ))}
          </div>
          <div className="inbox-items">
            {!threads ? <Spinner /> : threads.length === 0 ? (
              <EmptyState message={filter === "open" ? "Belum ada percakapan terbuka." : "Tidak ada percakapan."} />
            ) : threads.map((t) => (
              <button key={t.id} className={`inbox-item ${selectedId === t.id ? "active" : ""}`} onClick={() => setSelectedId(t.id)}>
                <div className="inbox-row">
                  <strong>{t.visitor_name}</strong>
                  <span className="inbox-time">{formatChatTime(t.last_message_at)}</span>
                </div>
                <div className="inbox-row">
                  <span className="inbox-preview">{t.last_sender === "admin" ? "Anda: " : ""}{t.last_message_preview}</span>
                  {t.unread_count > 0 && <span className="nav-badge">{t.unread_count}</span>}
                </div>
              </button>
            ))}
          </div>
        </aside>

        <section className="inbox-pane">
          {!selectedId ? (
            <div className="inbox-placeholder">Pilih percakapan di sebelah kiri untuk membaca dan membalas.</div>
          ) : !detail ? (
            <Spinner label="Memuat percakapan..." />
          ) : (
            <>
              <div className="chat-head">
                <div>
                  <button className="link-btn inbox-back" onClick={() => setSelectedId(null)}>Kembali</button>
                  <strong>{detail.visitor_name}</strong>
                  <span>{detail.visitor_contact || "Tidak ada kontak"}</span>
                </div>
                <button className="btn btn-secondary btn-sm" onClick={toggleStatus}>
                  {detail.status === "open" ? "Tandai selesai" : "Buka lagi"}
                </button>
              </div>
              <MessageList messages={detail.messages} me="admin" theirLabel={detail.visitor_name} />
              {detail.status === "closed" && <div className="chat-closed">Percakapan ini selesai. Membalas akan membukanya kembali.</div>}
              <Composer onSend={handleReply} placeholder="Tulis balasan..." />
            </>
          )}
        </section>
      </div>
    </div>
  );
}
