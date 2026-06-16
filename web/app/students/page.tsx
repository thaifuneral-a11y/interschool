// app/students/page.tsx
"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { studentsApi } from "@/lib/api";
import { Search, Plus, Upload, Filter } from "lucide-react";
import Link from "next/link";

export default function StudentsPage() {
  const [q, setQ] = useState("");
  const [grade, setGrade] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ["students", q, grade, page],
    queryFn: () =>
      studentsApi.list({ q: q || undefined, grade_level: grade || undefined, page, per_page: 20 }).then((r) => r.data),
    placeholderData: (prev) => prev,
  });

  const students = data?.items ?? [];
  const total = data?.total ?? 0;
  const pages = data?.pages ?? 1;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1>Students</h1>
          <p className="text-sm text-slate-500 mt-0.5">{total} students enrolled</p>
        </div>
        <div className="flex gap-2">
          <button className="btn-secondary flex items-center gap-2 text-sm">
            <Upload size={15} /> Import CSV
          </button>
          <Link href="/students/new" className="btn-primary flex items-center gap-2 text-sm">
            <Plus size={15} /> Add Student
          </Link>
        </div>
      </div>

      {/* Filters */}
      <div className="card p-4 flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            className="input pl-9"
            placeholder="Search by name or student number…"
            value={q}
            onChange={(e) => { setQ(e.target.value); setPage(1); }}
          />
        </div>
        <select
          className="input sm:w-40"
          value={grade}
          onChange={(e) => { setGrade(e.target.value); setPage(1); }}
        >
          <option value="">All Grades</option>
          {["G1","G2","G3","G4","G5","G6","G7","G8","G9","G10","G11","G12"].map((g) => (
            <option key={g} value={g}>{g}</option>
          ))}
        </select>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        {isLoading ? (
          <div className="flex justify-center items-center h-40">
            <div className="w-7 h-7 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : students.length === 0 ? (
          <div className="text-center py-16 text-slate-400">
            <p className="text-lg">No students found</p>
            <p className="text-sm mt-1">Try adjusting your search or filters.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 border-b border-surface-border">
                  {["Student", "ID", "Grade", "Class", "Status"].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {students.map((s: any) => (
                  <tr key={s.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-4 py-3">
                      <Link href={`/students/${s.id}`} className="flex items-center gap-3 group">
                        <div className="w-8 h-8 bg-brand-100 rounded-full flex items-center justify-center text-brand-700 text-xs font-bold shrink-0">
                          {s.full_name[0]}
                        </div>
                        <div>
                          <p className="font-medium text-slate-900 group-hover:text-brand-600 transition-colors">
                            {s.full_name}
                          </p>
                          {s.preferred_name && (
                            <p className="text-xs text-slate-400">"{s.preferred_name}"</p>
                          )}
                        </div>
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-slate-500">{s.student_number}</td>
                    <td className="px-4 py-3 text-slate-700">{s.grade_level ?? "—"}</td>
                    <td className="px-4 py-3 text-slate-700">{s.class_name ?? "—"}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                        s.is_active ? "bg-green-50 text-green-700" : "bg-slate-100 text-slate-500"
                      }`}>
                        {s.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {pages > 1 && (
          <div className="px-4 py-3 border-t border-surface-border flex items-center justify-between">
            <p className="text-sm text-slate-500">
              Page {page} of {pages}
            </p>
            <div className="flex gap-2">
              <button
                className="btn-secondary text-sm py-1.5 px-3"
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
              >
                Previous
              </button>
              <button
                className="btn-secondary text-sm py-1.5 px-3"
                disabled={page >= pages}
                onClick={() => setPage(page + 1)}
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
