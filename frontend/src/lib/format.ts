export function formatChatTime(iso: string): string {
  const d = new Date(iso);
  const time = d.toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" });
  if (d.toDateString() === new Date().toDateString()) return time;
  return `${d.toLocaleDateString("id-ID", { day: "numeric", month: "short" })} ${time}`;
}
