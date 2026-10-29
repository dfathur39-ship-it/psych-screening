export interface Participant {
  id: string;
  nama: string;
  usia: number;
  jabatan: string;
  no_hp: string;
  email: string | null;
  nik_masked: string | null;
  ktp_confirmed: boolean;
  created_at: string;
}

/** Participant plus screening state, as returned by GET /api/participants/{id}. */
export interface ParticipantProfile extends Participant {
  in_progress_session_id: string | null;
  completed_session_id: string | null;
  retake_status: "pending" | "approved" | "rejected" | null;
}

export interface RetakeRequest {
  id: string;
  status: "pending" | "approved" | "rejected" | "used";
  reason: string | null;
  admin_note: string | null;
  created_at: string;
  decided_at: string | null;
}

export interface AdminRetakeRequestItem {
  id: string;
  participant_id: string;
  participant_nama: string;
  participant_jabatan: string;
  participant_no_hp: string;
  participant_email: string | null;
  reason: string | null;
  status: "pending" | "approved" | "rejected" | "used";
  admin_note: string | null;
  created_at: string;
  decided_at: string | null;
}

export interface AnswerOptionPublic {
  id: string;
  option_code: "A" | "B" | "C" | "D";
  option_text: string;
  order_number: number;
}

export interface AnswerOptionAdmin extends AnswerOptionPublic {
  score: number;
}

export interface QuestionPublic {
  id: string;
  question_text: string;
  order_number: number;
  options: AnswerOptionPublic[];
  answered_option_id: string | null;
}

export interface QuestionAdmin {
  id: string;
  question_text: string;
  active: boolean;
  options: AnswerOptionAdmin[];
  position_ids: string[];
  created_at: string;
}

export interface Position {
  id: string;
  nama_jabatan: string;
  description: string | null;
  active: boolean;
  question_count: number;
}

export interface ResultCategory {
  id: string;
  name: string;
  min_score: number;
  max_score: number;
  message: string;
  recommendation: string;
  active: boolean;
}

export interface ScreeningResult {
  session_id: string;
  total_score: number;
  category_name: string | null;
  message: string | null;
  recommendation: string | null;
  disclaimer: string;
}

export interface KtpOcrResult {
  success: boolean;
  ktp_document_id: string | null;
  nik: string | null;
  nama: string | null;
  tempat_lahir: string | null;
  tanggal_lahir: string | null;
  jenis_kelamin: string | null;
  alamat: string | null;
  rt_rw: string | null;
  kelurahan: string | null;
  kecamatan: string | null;
  agama: string | null;
  status_perkawinan: string | null;
  pekerjaan_ktp: string | null;
  kewarganegaraan: string | null;
  confidence: number | null;
  message: string | null;
  ocr_provider?: string | null;
  fallback_used?: boolean | null;
  auto_confirmed?: boolean | null;
  ktp_confirmed?: boolean | null;
}

/** Hasil POST /api/ktp/scan (draft AI; belum disimpan sebelum user konfirmasi). */
export type KtpFieldStatus = "ok" | "review" | "unreadable";
export interface KtpScanResult {
  success: boolean;
  message: string | null;
  data: {
    nik: string | null; nama: string | null; tempat_lahir: string | null;
    tanggal_lahir: string | null; // YYYY-MM-DD
    jenis_kelamin: string | null; alamat: string | null; rt_rw: string | null;
    kelurahan: string | null; kecamatan: string | null; agama: string | null;
    status_perkawinan: string | null; pekerjaan: string | null; kewarganegaraan: string | null;
  };
  confidence: Record<string, number | null>;
  field_status: Record<string, KtpFieldStatus>;
  needs_review: string[];
  warnings: string[];
  overall_confidence: number | null;
  confidence_threshold: number;
  provider: string;
  model: string;
  saved: boolean;
  fallback_used?: boolean;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AdminStatistics {
  total_participants: number;
  total_screenings: number;
  total_positions: number;
  total_questions: number;
  distribusi_kategori: { label: string; value: number }[];
  distribusi_jabatan: { label: string; value: number }[];
}

// ---------- Support chat ----------
export interface SupportMessage {
  id: string;
  sender: "visitor" | "admin";
  body: string;
  created_at: string;
}
export interface SupportThreadState {
  thread_id: string;
  status: "open" | "closed";
  messages: SupportMessage[];
}
export interface AdminThreadItem {
  id: string;
  visitor_name: string;
  visitor_contact: string | null;
  status: "open" | "closed";
  last_message_at: string;
  last_message_preview: string;
  last_sender: "visitor" | "admin" | null;
  unread_count: number;
}
export interface AdminThreadDetail {
  id: string;
  visitor_name: string;
  visitor_contact: string | null;
  status: "open" | "closed";
  messages: SupportMessage[];
}
