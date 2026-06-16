// app/safeguarding/page.tsx
"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { safeguardingApi, studentsApi } from "@/lib/api";
import { ShieldAlert, Plus, AlertTriangle } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { format } from "date-fns";

const RISK_COLORS: Record<string, string> = {
  low:      "risk-low",
  medium:   "risk-medium",
  high:     "risk-high",
  critical: "risk-critical",
};

const schema = z.object({
  student_id: z.string().min(1),
  risk_level: z.enum(["low", "medium", "high", "critical"]),
  category: z.string().min(1),
  description: z.string().min(10),
  incident_date: z.string().min(1),
});

export default function SafeguardingPage() {
  const [showForm, setShowForm] = useState(false);
  const [filterRisk, setFilterRisk] = useState("");
  const qc = useQueryClient();

  const { data: incidents, isLoading } = useQuery({
    queryKey: ["incidents", filterRisk],
    queryFn: () =>
      safeguardingApi.listIncidents(filterRisk ? { risk_level: filterRisk } : undefined).then((r) => r.data),
  });

  const { data: students } = useQuery({
    queryKey: ["students-slim"],
    queryFn: () => studentsApi.list({ per_page: 200 }).then((r) => r.data.items),
  });

  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm({
    resolver: zodResolver(schema),
    defaultValues: { incident_date: format(new Date(), "yyyy-MM-dd") },
  });

  const mutation = useMutation({
    mutationFn: (data: any) => safeguardingApi.reportIncident(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["incidents"] });
      reset();
      setShowForm(false);
    },
  });

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="flex items-center gap-2">
            <ShieldAlert size={22} className="text-red-500" /> Safeguarding
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">Incident reporting and case management</p>
        </div>
        <button className="btn-primary flex items-center gap-2 text-sm" onClick={() => setShowForm(true)}>
          <Plus size={15} /> Report Incident
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-2 flex-wrap">
        {["", "low", "medium", "high", "critical"].map((r) => (
          <button
            key={r}
            onClick={() => setFilterRisk(r)}
            className={`px-3 py-1.5 rounded-full text-sm font-medium border transition-colors ${
              filterRisk === r
                ? "bg-slate-800 text-white border-slate-800"
                : "bg-white text-slate-600 border-surface-border hover:bg-slate-50"
            }`}
          >
            {r === "" ? "All" : r.charAt(0).toUpperCase() + r.slice(1)}
          </button>
        ))}
      </div>

      {/* Incidents */}
      <div className="space-y-3">
        {isLoading ? (
          <div className="flex justify-center items-center h-32">
            <div className="w-7 h-7 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : !incidents?.length ? (
          <div className="card p-12 text-center text-slate-400">
            <ShieldAlert size={36} className="mx-auto mb-3 opacity-30" />
            <p>No incidents recorded</p>
          </div>
        ) : (
          incidents.map((inc: any) => (
            <div key={inc.id} className={`card p-4 border-l-4 ${
              inc.risk_level === "critical" ? "border-l-red-600" :
              inc.risk_level === "high"     ? "border-l-orange-500" :
              inc.risk_level === "medium"   ? "border-l-yellow-500" :
              "border-l-green-500"
            }`}>
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold border ${RISK_COLORS[inc.risk_level]}`}>
                      {inc.risk_level === "critical" && <AlertTriangle size={11} className="mr-1" />}
                      {inc.risk_level.toUpperCase()}
                    </span>
                    <span className="text-xs text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full">{inc.category}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${
                      inc.status === "resolved" ? "bg-green-50 text-green-700" :
                      inc.status === "escalated" ? "bg-red-50 text-red-700" :
                      "bg-yellow-50 text-yellow-700"
                    }`}>{inc.status}</span>
                  </div>
                  <p className="text-sm text-slate-700 mt-1">{inc.description}</p>
                  <p className="text-xs text-slate-400 mt-1.5">
                    Incident date: {format(new Date(inc.incident_date), "dd MMM yyyy")} ·
                    Reported: {format(new Date(inc.created_at), "dd MMM yyyy HH:mm")}
                    {inc.is_escalated && " · 🚨 Escalated"}
                  </p>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Report Modal */}
      {showForm && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-modal w-full max-w-lg">
            <div className="p-6 border-b border-surface-border">
              <h2 className="font-semibold text-slate-900">Report Safeguarding Incident</h2>
            </div>
            <form onSubmit={handleSubmit((d) => mutation.mutate(d))} className="p-6 space-y-4">
              <div>
                <label className="label">Student</label>
                <select {...register("student_id")} className="input">
                  <option value="">Select student…</option>
                  {(students ?? []).map((s: any) => (
                    <option key={s.id} value={s.id}>{s.full_name} ({s.student_number})</option>
                  ))}
                </select>
                {errors.student_id && <p className="text-xs text-red-500 mt-1">{errors.student_id.message}</p>}
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label">Risk Level</label>
                  <select {...register("risk_level")} className="input">
                    {["low","medium","high","critical"].map((r) => (
                      <option key={r} value={r}>{r.charAt(0).toUpperCase() + r.slice(1)}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="label">Category</label>
                  <select {...register("category")} className="input">
                    <option value="">Select…</option>
                    {["Abuse","Neglect","Bullying","Self-harm","Online Safety","Domestic Violence","Other"].map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div>
                <label className="label">Incident Date</label>
                <input type="date" {...register("incident_date")} className="input" />
              </div>
              <div>
                <label className="label">Description</label>
                <textarea {...register("description")} className="input" rows={4} placeholder="Describe the incident in detail…" />
                {errors.description && <p className="text-xs text-red-500 mt-1">{errors.description.message}</p>}
              </div>
              <div className="flex gap-3 pt-2">
                <button type="button" className="btn-secondary flex-1" onClick={() => setShowForm(false)}>Cancel</button>
                <button type="submit" disabled={isSubmitting || mutation.isPending} className="btn-primary flex-1">
                  {mutation.isPending ? "Submitting…" : "Submit Report"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
