// app/counseling/page.tsx
"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { counselingApi, studentsApi } from "@/lib/api";
import { BookOpen, Plus, Clock, CheckCircle2, AlertCircle, User } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { format } from "date-fns";

const URGENCY_STYLES: Record<string, string> = {
  low:    "bg-slate-100 text-slate-600",
  normal: "bg-blue-50 text-blue-700",
  high:   "bg-orange-50 text-orange-700",
  urgent: "bg-red-50 text-red-700",
};

const STATUS_STYLES: Record<string, string> = {
  open:     "bg-yellow-50 text-yellow-700",
  active:   "bg-blue-50 text-blue-700",
  closed:   "bg-green-50 text-green-700",
  archived: "bg-slate-100 text-slate-500",
};

const referralSchema = z.object({
  student_id: z.string().min(1, "Student required"),
  reason: z.string().min(10, "Please provide more detail"),
  urgency: z.enum(["low", "normal", "high", "urgent"]),
});

const sessionSchema = z.object({
  referral_id: z.string().min(1),
  session_date: z.string().min(1),
  duration_minutes: z.coerce.number().min(10).max(180),
  session_type: z.enum(["individual", "group", "family"]),
  notes: z.string().optional(),
});

type Tab = "referrals" | "sessions" | "followups";

export default function CounselingPage() {
  const [tab, setTab] = useState<Tab>("referrals");
  const [showReferralForm, setShowReferralForm] = useState(false);
  const [showSessionForm, setShowSessionForm] = useState(false);
  const qc = useQueryClient();

  const { data: referrals, isLoading: refLoading } = useQuery({
    queryKey: ["referrals"],
    queryFn: () => counselingApi.listReferrals().then((r) => r.data),
  });

  const { data: sessions, isLoading: sessLoading } = useQuery({
    queryKey: ["sessions"],
    queryFn: () => counselingApi.listSessions().then((r) => r.data),
  });

  const { data: followups, isLoading: fuLoading } = useQuery({
    queryKey: ["followups"],
    queryFn: () => counselingApi.listFollowups().then((r) => r.data),
  });

  const { data: students } = useQuery({
    queryKey: ["students-slim"],
    queryFn: () => studentsApi.list({ per_page: 200 }).then((r) => r.data.items),
  });

  const { data: dash } = useQuery({
    queryKey: ["counseling-dash"],
    queryFn: () => counselingApi.dashboard().then((r) => r.data),
  });

  const refForm = useForm({ resolver: zodResolver(referralSchema), defaultValues: { urgency: "normal" } });
  const sessForm = useForm({ resolver: zodResolver(sessionSchema), defaultValues: { duration_minutes: 50, session_type: "individual" } });

  const createReferral = useMutation({
    mutationFn: (d: any) => counselingApi.createReferral(d),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["referrals"] }); qc.invalidateQueries({ queryKey: ["counseling-dash"] }); refForm.reset(); setShowReferralForm(false); },
  });

  const createSession = useMutation({
    mutationFn: (d: any) => counselingApi.createSession(d),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["sessions"] }); sessForm.reset(); setShowSessionForm(false); },
  });

  const completeFollowup = useMutation({
    mutationFn: (id: string) => counselingApi.completeFollowup(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["followups"] }),
  });

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2"><BookOpen size={22} className="text-purple-600" /> Counseling</h1>
          <p className="text-sm text-slate-500 mt-0.5">Referrals, sessions and follow-ups</p>
        </div>
        <div className="flex gap-2">
          <button className="btn-secondary text-sm flex items-center gap-2" onClick={() => setShowSessionForm(true)}>
            <Plus size={14} /> Log Session
          </button>
          <button className="btn-primary text-sm flex items-center gap-2" onClick={() => setShowReferralForm(true)}>
            <Plus size={14} /> New Referral
          </button>
        </div>
      </div>

      {/* Stats */}
      {dash && (
        <div className="grid grid-cols-2 gap-3">
          <div className="card p-4 flex items-center gap-3">
            <div className="p-2.5 bg-purple-50 text-purple-600 rounded-lg"><AlertCircle size={18} /></div>
            <div><p className="text-2xl font-bold text-slate-900">{dash.open_cases}</p><p className="text-xs text-slate-500">Open Cases</p></div>
          </div>
          <div className="card p-4 flex items-center gap-3">
            <div className="p-2.5 bg-orange-50 text-orange-600 rounded-lg"><Clock size={18} /></div>
            <div><p className="text-2xl font-bold text-slate-900">{dash.overdue_followups}</p><p className="text-xs text-slate-500">Overdue Follow-ups</p></div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-surface-border flex gap-6">
        {(["referrals", "sessions", "followups"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`pb-3 text-sm font-medium capitalize border-b-2 transition-colors ${
              tab === t ? "border-brand-500 text-brand-600" : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            {t}
            {t === "referrals" && referrals && <span className="ml-1.5 text-xs bg-slate-100 px-1.5 py-0.5 rounded-full">{referrals.length}</span>}
            {t === "followups" && followups && <span className="ml-1.5 text-xs bg-orange-100 text-orange-600 px-1.5 py-0.5 rounded-full">{followups.length}</span>}
          </button>
        ))}
      </div>

      {/* Referrals Tab */}
      {tab === "referrals" && (
        <div className="space-y-3">
          {refLoading ? <Spinner /> : !referrals?.length ? <Empty msg="No referrals yet" /> :
            referrals.map((r: any) => (
              <div key={r.id} className="card p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${URGENCY_STYLES[r.urgency]}`}>{r.urgency}</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_STYLES[r.status]}`}>{r.status}</span>
                    </div>
                    <p className="text-sm text-slate-700">{r.reason}</p>
                    <p className="text-xs text-slate-400 mt-1.5">Created {format(new Date(r.created_at), "dd MMM yyyy")}</p>
                  </div>
                  {r.status !== "closed" && r.status !== "archived" && (
                    <button
                      className="text-xs text-slate-400 hover:text-green-600 border border-slate-200 hover:border-green-300 px-2 py-1 rounded-lg transition-colors"
                      onClick={() => counselingApi.updateReferral(r.id, { status: "closed" }).then(() => qc.invalidateQueries({ queryKey: ["referrals"] }))}
                    >
                      Close
                    </button>
                  )}
                </div>
              </div>
            ))
          }
        </div>
      )}

      {/* Sessions Tab */}
      {tab === "sessions" && (
        <div className="space-y-3">
          {sessLoading ? <Spinner /> : !sessions?.length ? <Empty msg="No sessions logged" /> :
            sessions.map((s: any) => (
              <div key={s.id} className="card p-4 flex items-start gap-4">
                <div className="p-2 bg-purple-50 rounded-lg text-purple-600 shrink-0"><BookOpen size={16} /></div>
                <div>
                  <p className="text-sm font-medium text-slate-800">{s.session_type} session</p>
                  <p className="text-xs text-slate-500 mt-0.5">{format(new Date(s.session_date), "dd MMM yyyy HH:mm")} · {s.duration_minutes} min</p>
                </div>
              </div>
            ))
          }
        </div>
      )}

      {/* Followups Tab */}
      {tab === "followups" && (
        <div className="space-y-3">
          {fuLoading ? <Spinner /> : !followups?.length ? <Empty msg="No pending follow-ups" /> :
            followups.map((f: any) => (
              <div key={f.id} className="card p-4 flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm font-medium text-slate-800">{f.task}</p>
                  <p className="text-xs text-slate-400 mt-0.5">Due: {format(new Date(f.due_date), "dd MMM yyyy")}</p>
                </div>
                <button
                  className="shrink-0 p-2 rounded-lg hover:bg-green-50 text-slate-400 hover:text-green-600 transition-colors"
                  onClick={() => completeFollowup.mutate(f.id)}
                  title="Mark complete"
                >
                  <CheckCircle2 size={18} />
                </button>
              </div>
            ))
          }
        </div>
      )}

      {/* Referral Modal */}
      {showReferralForm && (
        <Modal title="New Counseling Referral" onClose={() => setShowReferralForm(false)}>
          <form onSubmit={refForm.handleSubmit((d) => createReferral.mutate(d))} className="space-y-4">
            <div>
              <label className="label">Student</label>
              <select {...refForm.register("student_id")} className="input">
                <option value="">Select student…</option>
                {(students ?? []).map((s: any) => <option key={s.id} value={s.id}>{s.full_name}</option>)}
              </select>
              {refForm.formState.errors.student_id && <p className="text-xs text-red-500 mt-1">{refForm.formState.errors.student_id.message as string}</p>}
            </div>
            <div>
              <label className="label">Urgency</label>
              <select {...refForm.register("urgency")} className="input">
                {["low", "normal", "high", "urgent"].map((u) => <option key={u} value={u}>{u.charAt(0).toUpperCase() + u.slice(1)}</option>)}
              </select>
            </div>
            <div>
              <label className="label">Reason for Referral</label>
              <textarea {...refForm.register("reason")} className="input" rows={4} placeholder="Describe your concern…" />
              {refForm.formState.errors.reason && <p className="text-xs text-red-500 mt-1">{refForm.formState.errors.reason.message as string}</p>}
            </div>
            <div className="flex gap-3 pt-2">
              <button type="button" className="btn-secondary flex-1" onClick={() => setShowReferralForm(false)}>Cancel</button>
              <button type="submit" className="btn-primary flex-1" disabled={createReferral.isPending}>
                {createReferral.isPending ? "Saving…" : "Submit Referral"}
              </button>
            </div>
          </form>
        </Modal>
      )}

      {/* Session Modal */}
      {showSessionForm && (
        <Modal title="Log Counseling Session" onClose={() => setShowSessionForm(false)}>
          <form onSubmit={sessForm.handleSubmit((d) => createSession.mutate(d))} className="space-y-4">
            <div>
              <label className="label">Referral ID</label>
              <input {...sessForm.register("referral_id")} className="input" placeholder="Paste referral ID…" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label">Session Date</label>
                <input type="datetime-local" {...sessForm.register("session_date")} className="input" />
              </div>
              <div>
                <label className="label">Duration (min)</label>
                <input type="number" {...sessForm.register("duration_minutes")} className="input" />
              </div>
            </div>
            <div>
              <label className="label">Session Type</label>
              <select {...sessForm.register("session_type")} className="input">
                {["individual", "group", "family"].map((t) => <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>)}
              </select>
            </div>
            <div>
              <label className="label">Confidential Notes</label>
              <textarea {...sessForm.register("notes")} className="input" rows={3} placeholder="Session notes (visible to counselors only)…" />
            </div>
            <div className="flex gap-3 pt-2">
              <button type="button" className="btn-secondary flex-1" onClick={() => setShowSessionForm(false)}>Cancel</button>
              <button type="submit" className="btn-primary flex-1" disabled={createSession.isPending}>
                {createSession.isPending ? "Saving…" : "Log Session"}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}

function Spinner() {
  return <div className="flex justify-center py-12"><div className="w-7 h-7 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" /></div>;
}
function Empty({ msg }: { msg: string }) {
  return <div className="card p-12 text-center text-slate-400"><p>{msg}</p></div>;
}
function Modal({ title, children, onClose }: { title: string; children: React.ReactNode; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-modal w-full max-w-lg">
        <div className="p-5 border-b border-surface-border flex items-center justify-between">
          <h2 className="font-semibold text-slate-900">{title}</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 text-xl leading-none">&times;</button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}
