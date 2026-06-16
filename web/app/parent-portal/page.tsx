// app/parent-portal/page.tsx
"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { parentApi } from "@/lib/api";
import { Calendar, Bell, BookOpen, Users, CheckCircle, XCircle, Clock, Plus } from "lucide-react";
import { format, parseISO } from "date-fns";
import { useForm } from "react-hook-form";

type Tab = "attendance" | "announcements" | "meetings";

const STATUS_ICON: Record<string, React.ElementType> = {
  present: CheckCircle,
  late: Clock,
  absent: XCircle,
  excused: CheckCircle,
};
const STATUS_COLOR: Record<string, string> = {
  present: "text-green-600",
  late: "text-yellow-600",
  absent: "text-red-600",
  excused: "text-blue-600",
};

export default function ParentPortalPage() {
  const [tab, setTab] = useState<Tab>("attendance");
  const [selectedChild, setSelectedChild] = useState<string>("");
  const [showMeetingForm, setShowMeetingForm] = useState(false);
  const qc = useQueryClient();

  const { data: children } = useQuery({
    queryKey: ["my-children"],
    queryFn: () => parentApi.myChildren().then((r) => r.data),
  });

  const activeChildId = selectedChild || children?.[0]?.student_id || "";

  const { data: attendance } = useQuery({
    queryKey: ["child-attendance", activeChildId],
    queryFn: () => parentApi.childAttendance(activeChildId).then((r) => r.data),
    enabled: !!activeChildId && tab === "attendance",
  });

  const { data: announcements } = useQuery({
    queryKey: ["parent-announcements"],
    queryFn: () => parentApi.announcements().then((r) => r.data),
    enabled: tab === "announcements",
  });

  const { data: meetings } = useQuery({
    queryKey: ["my-meetings"],
    queryFn: () => parentApi.myMeetings().then((r) => r.data),
    enabled: tab === "meetings",
  });

  const meetingForm = useForm();

  const bookMeeting = useMutation({
    mutationFn: (d: any) => parentApi.bookMeeting(d),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["my-meetings"] }); meetingForm.reset(); setShowMeetingForm(false); },
  });

  const cancelMeeting = useMutation({
    mutationFn: (id: string) => parentApi.cancelMeeting(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["my-meetings"] }),
  });

  // Compute summary stats from attendance
  const totalAbsent = attendance?.filter((a: any) => a.status === "absent" && !a.is_excused).length ?? 0;
  const attendanceRate = attendance?.length
    ? Math.round((attendance.filter((a: any) => ["present", "late", "excused"].includes(a.status)).length / attendance.length) * 100)
    : null;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="flex items-center gap-2"><Users size={22} className="text-brand-600" /> Parent Portal</h1>
        <p className="text-sm text-slate-500 mt-0.5">Stay informed about your child's progress</p>
      </div>

      {/* Child selector */}
      {children && children.length > 1 && (
        <div className="flex gap-2 flex-wrap">
          {children.map((c: any) => (
            <button
              key={c.student_id}
              onClick={() => setSelectedChild(c.student_id)}
              className={`px-4 py-2 rounded-full text-sm font-medium border transition-colors ${
                activeChildId === c.student_id
                  ? "bg-brand-500 text-white border-brand-500"
                  : "bg-white text-slate-600 border-surface-border hover:bg-slate-50"
              }`}
            >
              {c.relationship}
            </button>
          ))}
        </div>
      )}

      {/* Attendance summary cards */}
      {tab === "attendance" && attendance && (
        <div className="grid grid-cols-3 gap-3">
          <div className="card p-4 text-center">
            <p className="text-2xl font-bold text-brand-600">{attendanceRate ?? "—"}%</p>
            <p className="text-xs text-slate-500 mt-0.5">Attendance Rate</p>
          </div>
          <div className="card p-4 text-center">
            <p className="text-2xl font-bold text-red-500">{totalAbsent}</p>
            <p className="text-xs text-slate-500 mt-0.5">Unexcused Absences</p>
          </div>
          <div className="card p-4 text-center">
            <p className="text-2xl font-bold text-slate-700">{attendance.length}</p>
            <p className="text-xs text-slate-500 mt-0.5">Days Recorded</p>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-surface-border flex gap-6">
        {[
          { key: "attendance",    label: "Attendance",     icon: Calendar },
          { key: "announcements", label: "Announcements",  icon: Bell },
          { key: "meetings",      label: "Meetings",       icon: BookOpen },
        ].map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setTab(key as Tab)}
            className={`pb-3 text-sm font-medium flex items-center gap-1.5 border-b-2 transition-colors ${
              tab === key ? "border-brand-500 text-brand-600" : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            <Icon size={14} />{label}
          </button>
        ))}
      </div>

      {/* Attendance Tab */}
      {tab === "attendance" && (
        <div className="card overflow-hidden">
          {!attendance?.length ? (
            <div className="p-12 text-center text-slate-400"><Calendar size={32} className="mx-auto mb-2 opacity-30" /><p>No attendance records</p></div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-slate-50 border-b border-surface-border">
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Date</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Status</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Notes</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-border">
                  {attendance.slice(0, 30).map((a: any) => {
                    const Icon = STATUS_ICON[a.status] ?? CheckCircle;
                    return (
                      <tr key={a.id} className="hover:bg-slate-50">
                        <td className="px-4 py-3 font-medium text-slate-800">{format(parseISO(a.date), "EEE, dd MMM yyyy")}</td>
                        <td className="px-4 py-3">
                          <span className={`flex items-center gap-1.5 font-medium capitalize ${STATUS_COLOR[a.status]}`}>
                            <Icon size={14} />{a.status}{a.is_excused && " (excused)"}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-slate-400 text-xs">{a.notes ?? "—"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Announcements Tab */}
      {tab === "announcements" && (
        <div className="space-y-3">
          {!announcements?.length ? (
            <div className="card p-12 text-center text-slate-400"><Bell size={32} className="mx-auto mb-2 opacity-30" /><p>No announcements</p></div>
          ) : (
            announcements.map((a: any) => (
              <div key={a.id} className="card p-5">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h3 className="font-semibold text-slate-800">{a.title}</h3>
                    <p className="text-sm text-slate-600 mt-1 leading-relaxed">{a.body}</p>
                    <p className="text-xs text-slate-400 mt-2">{format(new Date(a.created_at), "dd MMM yyyy")}</p>
                  </div>
                  <span className="text-xs bg-brand-50 text-brand-600 px-2 py-0.5 rounded-full shrink-0">{a.audience}</span>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Meetings Tab */}
      {tab === "meetings" && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <button className="btn-primary text-sm flex items-center gap-2" onClick={() => setShowMeetingForm(true)}>
              <Plus size={14} /> Book Meeting
            </button>
          </div>
          {!meetings?.length ? (
            <div className="card p-12 text-center text-slate-400"><BookOpen size={32} className="mx-auto mb-2 opacity-30" /><p>No meetings booked</p></div>
          ) : (
            meetings.map((m: any) => (
              <div key={m.id} className={`card p-4 border-l-4 ${m.status === "cancelled" ? "border-l-slate-300 opacity-60" : "border-l-brand-400"}`}>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-medium text-slate-800">{format(new Date(m.scheduled_at), "EEE, dd MMM yyyy · HH:mm")}</p>
                    <p className="text-sm text-slate-500 mt-0.5">{m.duration_minutes} min · {m.location ?? "TBC"}</p>
                    {m.meeting_link && <a href={m.meeting_link} className="text-xs text-brand-600 hover:underline mt-0.5 block">Join Online</a>}
                  </div>
                  {m.status !== "cancelled" && (
                    <button
                      className="text-xs text-red-500 hover:text-red-700 border border-red-200 hover:border-red-400 px-2 py-1 rounded-lg transition-colors"
                      onClick={() => cancelMeeting.mutate(m.id)}
                    >
                      Cancel
                    </button>
                  )}
                </div>
              </div>
            ))
          )}

          {showMeetingForm && (
            <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
              <div className="bg-white rounded-xl shadow-modal w-full max-w-md">
                <div className="p-5 border-b border-surface-border flex items-center justify-between">
                  <h2 className="font-semibold text-slate-900">Book Parent-Teacher Meeting</h2>
                  <button onClick={() => setShowMeetingForm(false)} className="text-slate-400 hover:text-slate-600 text-xl">&times;</button>
                </div>
                <form onSubmit={meetingForm.handleSubmit((d) => bookMeeting.mutate({ ...d, student_id: activeChildId }))} className="p-5 space-y-4">
                  <div>
                    <label className="label">Teacher ID</label>
                    <input {...meetingForm.register("teacher_id", { required: true })} className="input" placeholder="Teacher's user ID" />
                  </div>
                  <div>
                    <label className="label">Preferred Date & Time</label>
                    <input type="datetime-local" {...meetingForm.register("scheduled_at", { required: true })} className="input" />
                  </div>
                  <div>
                    <label className="label">Location (optional)</label>
                    <input {...meetingForm.register("location")} className="input" placeholder="Room 12 or Google Meet link" />
                  </div>
                  <div className="flex gap-3 pt-2">
                    <button type="button" className="btn-secondary flex-1" onClick={() => setShowMeetingForm(false)}>Cancel</button>
                    <button type="submit" className="btn-primary flex-1" disabled={bookMeeting.isPending}>
                      {bookMeeting.isPending ? "Booking…" : "Confirm Booking"}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
