import { api } from "./client";
import type {
  AdminRetakeRequestItem, Participant, ParticipantProfile, QuestionPublic, RetakeRequest, QuestionAdmin, Position, ResultCategory,
  ScreeningResult, KtpOcrResult, KtpScanResult, PaginatedResponse, AdminStatistics,
  SupportThreadState, AdminThreadItem, AdminThreadDetail, SupportMessage,
} from "./types";

// ---------- Public: Participant ----------
export async function createParticipant(payload: {
  nama: string; usia: number; jabatan: string; no_hp: string; email: string;
}): Promise<Participant> {
  const { data } = await api.post<Participant>("/api/participants", payload);
  return data;
}

export async function getParticipant(id: string): Promise<ParticipantProfile> {
  const { data } = await api.get<ParticipantProfile>(`/api/participants/${id}`);
  return data;
}

// ---------- Public: OCR (VLM utama, auto-confirm bila lengkap) ----------
export async function uploadKtp(
  participantId: string,
  file: File,
  opts?: { provider?: "auto" | "vlm" | "tesseract"; autoConfirm?: boolean },
): Promise<KtpOcrResult> {
  const form = new FormData();
  form.append("participant_id", participantId);
  form.append("file", file);
  const params = {
    provider: opts?.provider ?? "auto",
    auto_confirm: opts?.autoConfirm ?? true,
  };
  const { data } = await api.post<KtpOcrResult>("/api/ocr/ktp", form, {
    headers: { "Content-Type": "multipart/form-data" },
    params,
  });
  return data;
}

// ---------- Public: Scan KTP dengan AI (stateless; hasil = draft yang wajib dicek user) ----------
export async function scanKtp(participantId: string, file: File): Promise<KtpScanResult> {
  const form = new FormData();
  form.append("participant_id", participantId);
  form.append("file", file);
  const { data } = await api.post<KtpScanResult>("/api/ktp/scan", form, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 90_000, // VLM bisa lambat; backend sendiri membatasi lewat VLM_TIMEOUT_S
  });
  return data;
}

export interface KtpFields {
  nik: string; nama: string; tempat_lahir: string; tanggal_lahir: string; jenis_kelamin: string;
  alamat: string; rt_rw: string; kelurahan: string; kecamatan: string; agama: string;
  status_perkawinan: string; pekerjaan_ktp: string; kewarganegaraan: string;
}

export async function confirmKtp(
  payload: KtpFields & { participant_id: string; scan_provider?: string; scan_confidence?: number },
): Promise<Participant> {
  const { data } = await api.post<Participant>("/api/ocr/ktp/confirm", payload);
  return data;
}

// ---------- Public: Screening ----------
export async function requestRetake(participantId: string, reason?: string): Promise<RetakeRequest> {
  const { data } = await api.post<RetakeRequest>(`/api/participants/${participantId}/retake-requests`, { reason });
  return data;
}

export async function startScreening(participantId: string, jabatan: string) {
  const { data } = await api.post<{ session_id: string; resumed: boolean }>(
    "/api/screening/start", { participant_id: participantId, jabatan }
  );
  return data;
}

export async function getSessionQuestions(sessionId: string): Promise<QuestionPublic[]> {
  const { data } = await api.get<QuestionPublic[]>(`/api/screening/${sessionId}/questions`);
  return data;
}

export async function submitAnswer(sessionId: string, questionId: string, answerOptionId: string) {
  const { data } = await api.post(`/api/screening/${sessionId}/answers`, {
    question_id: questionId, answer_option_id: answerOptionId,
  });
  return data;
}

export async function completeScreening(sessionId: string): Promise<ScreeningResult> {
  const { data } = await api.post<ScreeningResult>(`/api/screening/${sessionId}/complete`);
  return data;
}

export async function getScreeningResult(sessionId: string): Promise<ScreeningResult> {
  const { data } = await api.get<ScreeningResult>(`/api/screening/${sessionId}/result`);
  return data;
}

// ---------- Admin: Auth ----------
export async function adminLogin(username: string, password: string) {
  const { data } = await api.post<{ access_token: string; role: string; username: string }>(
    "/api/admin/login", { username, password }
  );
  return data;
}

export async function updateAdminProfile(payload: {
  current_password: string; new_username?: string; new_password?: string;
}) {
  const { data } = await api.put<{ access_token: string; role: string; username: string }>(
    "/api/admin/me/profile", payload
  );
  return data;
}

export async function adminLogout() {
  await api.post("/api/admin/logout");
}

// ---------- Admin: Questions ----------
export async function listQuestions(page = 1, pageSize = 20, active?: boolean) {
  const { data } = await api.get<PaginatedResponse<QuestionAdmin>>("/api/admin/questions", {
    params: { page, page_size: pageSize, active },
  });
  return data;
}

export async function getQuestion(id: string) {
  const { data } = await api.get<QuestionAdmin>(`/api/admin/questions/${id}`);
  return data;
}

export interface QuestionPayload {
  question_text: string;
  active: boolean;
  position_ids: string[];
  options: { option_code: "A" | "B" | "C" | "D"; option_text: string; score: number; order_number: number }[];
}

export async function createQuestion(payload: QuestionPayload) {
  const { data } = await api.post<QuestionAdmin>("/api/admin/questions", payload);
  return data;
}

export async function updateQuestion(id: string, payload: Partial<QuestionPayload>) {
  const { data } = await api.put<QuestionAdmin>(`/api/admin/questions/${id}`, payload);
  return data;
}

export async function deleteQuestion(id: string) {
  await api.delete(`/api/admin/questions/${id}`);
}

// ---------- Admin: Positions ----------
export async function listPositions() {
  const { data } = await api.get<Position[]>("/api/admin/positions");
  return data;
}

export async function createPosition(payload: { nama_jabatan: string; description?: string; active: boolean }) {
  const { data } = await api.post<Position>("/api/admin/positions", payload);
  return data;
}

export async function updatePosition(id: string, payload: Partial<{ nama_jabatan: string; description: string; active: boolean }>) {
  const { data } = await api.put<Position>(`/api/admin/positions/${id}`, payload);
  return data;
}

export async function deletePosition(id: string) {
  await api.delete(`/api/admin/positions/${id}`);
}

// ---------- Admin: Result Categories ----------
export async function listCategories() {
  const { data } = await api.get<ResultCategory[]>("/api/admin/categories");
  return data;
}

export async function createCategory(payload: Omit<ResultCategory, "id">) {
  const { data } = await api.post<ResultCategory>("/api/admin/categories", payload);
  return data;
}

export async function updateCategory(id: string, payload: Partial<Omit<ResultCategory, "id">>) {
  const { data } = await api.put<ResultCategory>(`/api/admin/categories/${id}`, payload);
  return data;
}

export async function deleteCategory(id: string) {
  await api.delete(`/api/admin/categories/${id}`);
}

// ---------- Admin: Participants & Screenings ----------
export async function listAdminParticipants(params: {
  page?: number; page_size?: number; search?: string; jabatan?: string;
  date_from?: string; date_to?: string;
}) {
  const { data } = await api.get<PaginatedResponse<any>>("/api/admin/participants", { params });
  return data;
}

export async function getParticipantDetail(id: string) {
  const { data } = await api.get(`/api/admin/participants/${id}`);
  return data;
}

export async function listAdminScreenings(params: { page?: number; page_size?: number; status?: string; category_id?: string }) {
  const { data } = await api.get<PaginatedResponse<any>>("/api/admin/screenings", { params });
  return data;
}

// ---------- Admin: Statistics ----------
export async function getStatistics(): Promise<AdminStatistics> {
  const { data } = await api.get<AdminStatistics>("/api/admin/statistics");
  return data;
}

// ---------- Admin: Audit Logs ----------
export async function listAuditLogs(page = 1, pageSize = 20) {
  const { data } = await api.get<PaginatedResponse<any>>("/api/admin/audit-logs", {
    params: { page, page_size: pageSize },
  });
  return data;
}

// ---------- Admin: Export ----------
export function exportUrl(format: "csv" | "excel") {
  const base = (api.defaults.baseURL || "").replace(/\/$/, "");
  return `${base}/api/admin/export/${format}`;
}

export async function downloadExport(format: "csv" | "excel") {
  const { data } = await api.get(`/api/admin/export/${format}`, { responseType: "blob" });
  const blob = new Blob([data]);
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = format === "csv" ? "skrining_export.csv" : "skrining_export.xlsx";
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}

// ---------- Support chat (public, authorised by a per-thread token) ----------
const tokenHeader = (token: string) => ({ headers: { "X-Thread-Token": token } });

export async function createSupportThread(payload: { participant_id: string; message: string }) {
  const { data } = await api.post<SupportThreadState & { token: string }>("/api/support/threads", payload);
  return data;
}

export async function getSupportMessages(threadId: string, token: string) {
  const { data } = await api.get<SupportThreadState>(`/api/support/threads/${threadId}/messages`, tokenHeader(token));
  return data;
}

export async function sendSupportMessage(threadId: string, token: string, body: string) {
  const { data } = await api.post<SupportThreadState>(`/api/support/threads/${threadId}/messages`, { body }, tokenHeader(token));
  return data;
}

// ---------- Support chat (admin) ----------
export async function listSupportThreads(status: "all" | "open" | "closed") {
  const { data } = await api.get<PaginatedResponse<AdminThreadItem>>("/api/admin/support/threads", {
    params: { status, page_size: 50 },
  });
  return data;
}

export async function getSupportThread(id: string) {
  const { data } = await api.get<AdminThreadDetail>(`/api/admin/support/threads/${id}`);
  return data;
}

export async function replySupportThread(id: string, body: string) {
  const { data } = await api.post<{ success: boolean; messages: SupportMessage[] }>(
    `/api/admin/support/threads/${id}/messages`, { body });
  return data;
}

export async function setSupportThreadStatus(id: string, status: "open" | "closed") {
  await api.put(`/api/admin/support/threads/${id}/status`, { status });
}

export async function listRetakeRequests(status: "all" | "pending" | "approved" | "rejected" | "used") {
  const { data } = await api.get(`/api/admin/retake-requests`, { params: { status, page_size: 100 } });
  return data as { items: AdminRetakeRequestItem[]; total: number };
}

export async function decideRetakeRequest(id: string, status: "approved" | "rejected", adminNote?: string) {
  const { data } = await api.post<AdminRetakeRequestItem>(`/api/admin/retake-requests/${id}/decision`,
    { status, admin_note: adminNote });
  return data;
}

export async function getRetakePendingCount() {
  const { data } = await api.get<{ pending: number }>("/api/admin/retake-requests/pending-count");
  return data;
}

export async function getSupportUnread() {
  const { data } = await api.get<{ unread_messages: number; unread_threads: number }>("/api/admin/support/unread-count");
  return data;
}
