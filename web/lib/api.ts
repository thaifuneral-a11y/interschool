// lib/api.ts — Axios client with JWT auto-refresh

import axios, { AxiosInstance, InternalAxiosRequestConfig } from "axios";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

let isRefreshing = false;
let failedQueue: Array<{ resolve: (v: string) => void; reject: (e: unknown) => void }> = [];

function processQueue(error: unknown, token: string | null) {
  failedQueue.forEach((p) => (error ? p.reject(error) : p.resolve(token!)));
  failedQueue = [];
}

export const api: AxiosInstance = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  timeout: 15000,
  headers: { "Content-Type": "application/json" },
});

// Request interceptor: attach access token
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: auto-refresh on 401
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return api(originalRequest);
        });
      }
      originalRequest._retry = true;
      isRefreshing = true;
      const refreshToken = localStorage.getItem("refresh_token");
      if (!refreshToken) {
        window.location.href = "/auth/login";
        return Promise.reject(error);
      }
      try {
        const { data } = await axios.post(`${BASE_URL}/api/v1/auth/refresh`, {
          refresh_token: refreshToken,
        });
        localStorage.setItem("access_token", data.access_token);
        processQueue(null, data.access_token);
        originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
        return api(originalRequest);
      } catch (err) {
        processQueue(err, null);
        localStorage.clear();
        window.location.href = "/auth/login";
        return Promise.reject(err);
      } finally {
        isRefreshing = false;
      }
    }
    return Promise.reject(error);
  }
);

// ── API helpers ───────────────────────────────────────────────────────────────
export const authApi = {
  login: (data: { email: string; password: string; school_slug: string }) =>
    api.post("/auth/login", data),
  googleAuth: (data: { id_token: string; school_slug: string }) =>
    api.post("/auth/google", data),
  logout: (refresh_token: string) => api.post("/auth/logout", { refresh_token }),
  me: () => api.get("/auth/me"),
  forgotPassword: (email: string) => api.post("/auth/forgot-password", { email }),
  resetPassword: (token: string, new_password: string) =>
    api.post("/auth/reset-password", { token, new_password }),
  invite: (data: object) => api.post("/auth/invite", data),
};

export const studentsApi = {
  list: (params?: object) => api.get("/students", { params }),
  get: (id: string) => api.get(`/students/${id}`),
  create: (data: object) => api.post("/students", data),
  update: (id: string, data: object) => api.put(`/students/${id}`, data),
  deactivate: (id: string) => api.delete(`/students/${id}`),
  bulkUpload: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return api.post("/students/bulk-upload", fd, { headers: { "Content-Type": "multipart/form-data" } });
  },
  getEmergencyContacts: (id: string) => api.get(`/students/${id}/emergency-contacts`),
  addEmergencyContact: (id: string, data: object) => api.post(`/students/${id}/emergency-contacts`, data),
  getMedical: (id: string) => api.get(`/students/${id}/medical`),
  updateMedical: (id: string, data: object) => api.put(`/students/${id}/medical`, data),
};

export const attendanceApi = {
  getRoll: (params: object) => api.get("/attendance", { params }),
  bulkMark: (data: object) => api.post("/attendance/bulk", data),
  update: (id: string, params: object) => api.put(`/attendance/${id}`, null, { params }),
  getStats: (date?: string) => api.get("/attendance/stats", { params: { date } }),
  getStudentHistory: (studentId: string, params?: object) =>
    api.get(`/attendance/student/${studentId}`, { params }),
  submitExplanation: (data: object) => api.post("/attendance/absence-explanations", data),
  reviewExplanation: (id: string, data: object) =>
    api.put(`/attendance/absence-explanations/${id}`, data),
};

export const counselingApi = {
  createReferral: (data: object) => api.post("/counseling/referrals", data),
  listReferrals: (params?: object) => api.get("/counseling/referrals", { params }),
  updateReferral: (id: string, data: object) => api.put(`/counseling/referrals/${id}`, data),
  createSession: (data: object) => api.post("/counseling/sessions", data),
  listSessions: (params?: object) => api.get("/counseling/sessions", { params }),
  createFollowup: (data: object) => api.post("/counseling/followups", data),
  listFollowups: (params?: object) => api.get("/counseling/followups", { params }),
  completeFollowup: (id: string) => api.put(`/counseling/followups/${id}/complete`),
  dashboard: () => api.get("/counseling/dashboard"),
};

export const safeguardingApi = {
  reportIncident: (data: object) => api.post("/safeguarding/incidents", data),
  listIncidents: (params?: object) => api.get("/safeguarding/incidents", { params }),
  getIncident: (id: string) => api.get(`/safeguarding/incidents/${id}`),
  updateRiskLevel: (id: string, risk_level: string) =>
    api.put(`/safeguarding/incidents/${id}/risk-level`, null, { params: { risk_level } }),
  escalate: (id: string, data: object) => api.post(`/safeguarding/incidents/${id}/escalate`, data),
  addNote: (id: string, data: object) => api.post(`/safeguarding/incidents/${id}/notes`, data),
  close: (id: string, resolution_notes: string) =>
    api.post(`/safeguarding/incidents/${id}/close`, null, { params: { resolution_notes } }),
};

export const dashboardApi = {
  overview: () => api.get("/dashboard/overview"),
  attendanceTrend: (days?: number) => api.get("/dashboard/attendance-trend", { params: { days } }),
  atRiskStudents: () => api.get("/dashboard/at-risk-students"),
};

export const notificationsApi = {
  list: (params?: object) => api.get("/notifications", { params }),
  markRead: (id: string) => api.put(`/notifications/${id}/read`),
  markAllRead: () => api.put("/notifications/mark-all-read"),
  registerPushToken: (token: string) => api.post("/notifications/push-token", { token }),
};

export const parentApi = {
  myChildren: () => api.get("/parent/children"),
  childAttendance: (id: string) => api.get(`/parent/children/${id}/attendance`),
  announcements: () => api.get("/parent/announcements"),
  bookMeeting: (data: object) => api.post("/parent/meetings/book", data),
  myMeetings: () => api.get("/parent/meetings"),
  cancelMeeting: (id: string) => api.delete(`/parent/meetings/${id}`),
};
