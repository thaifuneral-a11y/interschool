// app/attendance/page.tsx
"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { studentsApi, attendanceApi } from "@/lib/api";
import { format } from "date-fns";
import { Calendar, Check, Clock, X, AlertCircle, Save } from "lucide-react";

type Status = "present" | "absent" | "late" | "excused";

const STATUS_OPTIONS: { value: Status; label: string; color: string; icon: React.ElementType }[] = [
  { value: "present", label: "Present", color: "bg-green-500", icon: Check },
  { value: "late",    label: "Late",    color: "bg-yellow-500", icon: Clock },
  { value: "absent",  label: "Absent",  color: "bg-red-500",    icon: X },
  { value: "excused", label: "Excused", color: "bg-blue-500",   icon: AlertCircle },
];

export default function AttendancePage() {
  const today = format(new Date(), "yyyy-MM-dd");
  const [date, setDate] = useState(today);
  const [grade, setGrade] = useState("");
  const [marks, setMarks] = useState<Record<string, Status>>({});
  const queryClient = useQueryClient();

  const { data: students, isLoading } = useQuery({
    queryKey: ["students-for-roll", grade],
    queryFn: () =>
      studentsApi.list({ grade_level: grade || undefined, per_page: 100 }).then((r) => r.data.items),
  });

  const { data: stats } = useQuery({
    queryKey: ["attendance-stats", date],
    queryFn: () => attendanceApi.getStats(date).then((r) => r.data),
    refetchInterval: 30000,
  });

  const mutation = useMutation({
    mutationFn: () =>
      attendanceApi.bulkMark({
        date,
        records: Object.entries(marks).map(([student_id, status]) => ({ student_id, status })),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["attendance-stats"] });
      alert("Attendance saved!");
    },
  });

  const markAll = (status: Status) => {
    const all: Record<string, Status> = {};
    (students ?? []).forEach((s: any) => { all[s.id] = status; });
    setMarks(all);
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1>Attendance</h1>
          <p className="text-sm text-slate-500 mt-0.5">Mark daily class roll</p>
        </div>
      </div>

      {/* Controls */}
      <div className="card p-4 flex flex-wrap gap-3 items-center">
        <div className="flex items-center gap-2">
          <Calendar size={16} className="text-slate-400" />
          <input
            type="date"
            className="input w-40"
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
        </div>
        <select className="input w-36" value={grade} onChange={(e) => setGrade(e.target.value)}>
          <option value="">All Grades</option>
          {["G1","G2","G3","G4","G5","G6","G7","G8","G9","G10","G11","G12"].map((g) => (
            <option key={g} value={g}>{g}</option>
          ))}
        </select>
        <div className="ml-auto flex gap-2">
          <button className="btn-secondary text-sm py-1.5" onClick={() => markAll("present")}>
            ✓ All Present
          </button>
          <button
            className="btn-primary flex items-center gap-2 text-sm"
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending || Object.keys(marks).length === 0}
          >
            <Save size={15} />
            {mutation.isPending ? "Saving…" : "Save Roll"}
          </button>
        </div>
      </div>

      {/* Stats bar */}
      {stats && (
        <div className="grid grid-cols-4 gap-3">
          {[
            { label: "Present", val: stats.present, color: "text-green-600 bg-green-50" },
            { label: "Late",    val: stats.late,    color: "text-yellow-600 bg-yellow-50" },
            { label: "Absent",  val: stats.absent,  color: "text-red-600 bg-red-50" },
            { label: "Rate",    val: `${stats.attendance_rate}%`, color: "text-brand-600 bg-brand-50" },
          ].map((s) => (
            <div key={s.label} className={`card p-3 text-center ${s.color}`}>
              <p className="text-xl font-bold">{s.val}</p>
              <p className="text-xs font-medium mt-0.5">{s.label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Roll */}
      <div className="card overflow-hidden">
        {isLoading ? (
          <div className="flex justify-center items-center h-40">
            <div className="w-7 h-7 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 border-b border-surface-border">
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Student</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Grade</th>
                  {STATUS_OPTIONS.map((s) => (
                    <th key={s.value} className="px-2 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide">
                      {s.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {(students ?? []).map((s: any) => (
                  <tr key={s.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div className="w-7 h-7 bg-brand-100 rounded-full flex items-center justify-center text-brand-700 text-xs font-bold">
                          {s.full_name[0]}
                        </div>
                        <span className="font-medium text-slate-800">{s.full_name}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-slate-500">{s.grade_level ?? "—"}</td>
                    {STATUS_OPTIONS.map((opt) => (
                      <td key={opt.value} className="px-2 py-3 text-center">
                        <button
                          onClick={() => setMarks((m) => ({ ...m, [s.id]: opt.value }))}
                          className={`w-8 h-8 rounded-full flex items-center justify-center mx-auto transition-all border-2 ${
                            marks[s.id] === opt.value
                              ? `${opt.color} text-white border-transparent scale-110`
                              : "bg-white border-surface-border text-slate-300 hover:border-slate-300"
                          }`}
                        >
                          <opt.icon size={14} />
                        </button>
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
