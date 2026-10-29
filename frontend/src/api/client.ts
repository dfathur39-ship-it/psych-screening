import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: API_URL,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("admin_token");
  if (token && config.url?.includes("/admin")) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401 && window.location.pathname.startsWith("/admin")) {
      localStorage.removeItem("admin_token");
      if (!window.location.pathname.endsWith("/login")) {
        window.location.href = "/admin/login";
      }
    }
    return Promise.reject(err);
  }
);

export interface ApiErrorBody {
  success: false;
  message: string;
  error_code: string;
}

export function getErrorMessage(err: unknown): string {
  const anyErr = err as any;
  const body: ApiErrorBody | undefined = anyErr?.response?.data;
  if (body?.message) return body.message;
  if (anyErr?.message) return anyErr.message;
  return "Terjadi kesalahan yang tidak diketahui";
}
