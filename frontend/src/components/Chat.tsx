import { useEffect, useRef, useState } from "react";
import type { SupportMessage } from "../api/types";
import { formatChatTime } from "../lib/format";

const MAX_LEN = 2000;

export function MessageList({
  messages, me, theirLabel, note,
}: { messages: SupportMessage[]; me: "visitor" | "admin"; theirLabel: string; note?: string }) {
  const boxRef = useRef<HTMLDivElement>(null);

  // Keep the newest message in view whenever the conversation grows.
  useEffect(() => {
    const el = boxRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages.length]);

  return (
    <div className="chat-scroll" ref={boxRef} aria-live="polite">
      {messages.map((m) => {
        const mine = m.sender === me;
        return (
          <div key={m.id} className={`msg ${mine ? "mine" : "theirs"}`}>
            {!mine && <div className="msg-name">{theirLabel}</div>}
            {m.body}
            <div className="msg-meta">{formatChatTime(m.created_at)}</div>
          </div>
        );
      })}
      {note && <div className="chat-note">{note}</div>}
    </div>
  );
}

export function Composer({
  onSend, placeholder = "Tulis pesan...", disabled = false,
}: { onSend: (text: string) => Promise<void>; placeholder?: string; disabled?: boolean }) {
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);

  const submit = async () => {
    const value = text.trim();
    if (!value || sending || disabled) return;
    setSending(true);
    try {
      await onSend(value);
      setText(""); // only clear once the message was actually delivered
    } catch {
      // caller shows the error; keep the text so nothing is lost
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="composer">
      <textarea
        className="form-control" rows={2} maxLength={MAX_LEN} placeholder={placeholder}
        value={text} disabled={disabled}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); void submit(); }
        }}
        aria-label="Tulis pesan"
      />
      <button className="btn btn-primary" onClick={() => void submit()} disabled={!text.trim() || sending || disabled}>
        {sending ? "Mengirim..." : "Kirim"}
      </button>
    </div>
  );
}
