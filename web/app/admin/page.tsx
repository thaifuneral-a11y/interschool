// app/admin/page.tsx
"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Settings, Plus, ToggleLeft, ToggleRight, School, Users, BarChart3 } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { format } from "date-fns";

const schoolSchema = z.object({
  name: z.string().min(2),
  slug: z.string().min(2).regex(/^[a-z0-9-]+$/, "Lowercase letters, numbers and hyphens only"),
  country: z.string().min(2),
  timezone: z.string().min(2),
});

export default function AdminPage() {
  const [showForm, setShowForm] = useState(false);
  const [statsId, setStatsId] = useState<string | null>(null);
  const qc = useQueryClient();

  const { data: schools, isLoading } = useQuery({
    queryKey: ["admin-schools"],
    queryFn: () => api.get("/admin/schools").then((r) => r.data),
  });

  const { data: stats } = useQuery({
    queryKey: ["school-stats", statsId],
    queryFn: () => api.get(`/admin/schools/${statsId}/stats`).then((r) => r.data),
    enabled: !!statsId,
  });

  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm({
    resolver: zodResolver(schoolSchema),
    defaultValues: { timezone: "Asia/Bangkok" },
  });

  const createSchool = useMutation({
    mutationFn: (d: any) => api.post("/admin/schools", d),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin-schools"] }); reset(); setShowForm(false); },
  });

  const toggleSchool = useMutation({
    mutationFn: (id: string) => api.put(`/admin/schools/${id}/toggle`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-schools"] }),
  });

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="flex items-center gap-2"><Settings size={22} className="text-slate-600" /> Admin Console</h1>
          <p className="text-sm text-slate-500 mt-0.5">Super admin — manage all schools</p>
        </div>
        <button className="btn-primary text-sm flex items-center gap-2" onClick={() => setShowForm(true)}>
          <Plus size={14} /> New School
        </button>
      </div>

      {/* Stats panel */}
      {statsId && stats && (
        <div className="card p-5 bg-brand-50 border-brand-100">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-brand-800">School Statistics</h3>
            <button className="text-xs text-brand-600 hover:underline" onClick={() => setStatsId(null)}>Close</button>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="text-center"><p className="text-2xl font-bold text-brand-700">{stats.students}</p><p className="text-xs text-brand-500">Active Students</p></div>
            <div className="text-center"><p className="text-2xl font-bold text-brand-700">{stats.users}</p><p className="text-xs text-brand-500">Active Staff</p></div>
          </div>
        </div>
      )}

      {/* Schools table */}
      <div className="card overflow-hidden">
        {isLoading ? (
          <div className="flex justify-center py-16"><div className="w-7 h-7 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" /></div>
        ) : !schools?.length ? (
          <div className="p-16 text-center text-slate-400"><School size={36} className="mx-auto mb-3 opacity-30" /><p>No schools yet. Create one above.</p></div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 border-b border-surface-border">
                {["School", "Slug", "Country", "Timezone", "Status", "Actions"].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border">
              {schools.map((s: any) => (
                <tr key={s.id} className="hover:bg-slate-50 transition-colors">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-brand-100 rounded-lg flex items-center justify-center text-brand-700 text-xs font-bold">{s.name[0]}</div>
                      <span className="font-medium text-slate-900">{s.name}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-slate-500 font-mono text-xs">{s.slug}</td>
                  <td className="px-4 py-3 text-slate-600">{s.country}</td>
                  <td className="px-4 py-3 text-slate-500 text-xs">{s.timezone}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${s.is_active ? "bg-green-50 text-green-700" : "bg-slate-100 text-slate-500"}`}>
                      {s.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <button className="p-1.5 rounded hover:bg-blue-50 text-slate-400 hover:text-brand-600 transition-colors" title="Stats" onClick={() => setStatsId(statsId === s.id ? null : s.id)}>
                        <BarChart3 size={14} />
                      </button>
                      <button
                        className={`p-1.5 rounded transition-colors ${s.is_active ? "hover:bg-red-50 text-slate-400 hover:text-red-600" : "hover:bg-green-50 text-slate-400 hover:text-green-600"}`}
                        title={s.is_active ? "Deactivate" : "Activate"}
                        onClick={() => toggleSchool.mutate(s.id)}
                      >
                        {s.is_active ? <ToggleRight size={16} /> : <ToggleLeft size={16} />}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Create School Modal */}
      {showForm && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-modal w-full max-w-md">
            <div className="p-5 border-b border-surface-border flex items-center justify-between">
              <h2 className="font-semibold text-slate-900">Create New School</h2>
              <button onClick={() => setShowForm(false)} className="text-slate-400 hover:text-slate-600 text-xl">&times;</button>
            </div>
            <form onSubmit={handleSubmit((d) => createSchool.mutate(d))} className="p-5 space-y-4">
              <div>
                <label className="label">School Name</label>
                <input {...register("name")} className="input" placeholder="Bangkok International School" />
                {errors.name && <p className="text-xs text-red-500 mt-1">{errors.name.message as string}</p>}
              </div>
              <div>
                <label className="label">URL Slug</label>
                <input {...register("slug")} className="input" placeholder="bangkok-international" />
                {errors.slug && <p className="text-xs text-red-500 mt-1">{errors.slug.message as string}</p>}
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label">Country</label>
                  <input {...register("country")} className="input" placeholder="Thailand" />
                </div>
                <div>
                  <label className="label">Timezone</label>
                  <input {...register("timezone")} className="input" placeholder="Asia/Bangkok" />
                </div>
              </div>
              <div className="flex gap-3 pt-2">
                <button type="button" className="btn-secondary flex-1" onClick={() => setShowForm(false)}>Cancel</button>
                <button type="submit" className="btn-primary flex-1" disabled={isSubmitting || createSchool.isPending}>
                  {createSchool.isPending ? "Creating…" : "Create School"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
