// app/students/[id]/page.tsx
"use client";

import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { studentsApi, attendanceApi } from "@/lib/api";
import { ArrowLeft, User, Phone, Heart, Calendar, Edit2 } from "lucide-react";
import Link from "next/link";
import { format, parseISO } from "date-fns";
import { useState } from "react";

type Tab = "overview" | "attendance" | "medical" | "emergency";

const STATUS_COLOR: Record<string, string> = {
  present: "text-green-600 bg-green-50", late: "text-yellow-600 bg-yellow-50",
  absent: "text-red-600 bg-red-50", excused: "text-blue-600 bg-blue-50",
};

export default function StudentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [tab, setTab] = useState<Tab>("overview");

  const { data: student, isLoading } = useQuery({
    queryKey: ["student", id],
    queryFn: () => studentsApi.get(id).then((r) => r.data),
  });

  const { data: contacts } = useQuery({
    queryKey: ["emergency-contacts", id],
    queryFn: () => studentsApi.getEmergencyContacts(id).then((r) => r.data),
    enabled: tab === "emergency",
  });

  const { data: medical } = useQuery({
    queryKey: ["medical", id],
    queryFn: () => studentsApi.getMedical(id).then((r) => r.data).catch(() => null),
    enabled: tab === "medical",
  });

  const { data: attendance } = useQuery({
    queryKey: ["student-attendance", id],
    queryFn: () => attendanceApi.getStudentHistory(id, { from_date: "2024-01-01" }).then((r) => r.data),
    enabled: tab === "attendance",
  });

  if (isLoading) return <div className="flex justify-center pt-20"><div className="w-8 h-8 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" /></div>;
  if (!student) return <div className="text-center pt-20 text-slate-500">Student not found.</div>;

  const totalDays = attendance?.length ?? 0;
  const presentDays = attendance?.filter((a: any) => ["present", "late"].includes(a.status)).length ?? 0;

  return (
    <div className="space-y-5 max-w-4xl">
      {/* Back */}
      <Link href="/students" className="inline-flex items-center gap-2 text-sm text-slate-500 hover:text-brand-600 transition-colors">
        <ArrowLeft size={15} /> Back to Students
      </Link>

      {/* Hero card */}
      <div className="card p-6 flex flex-col sm:flex-row sm:items-start gap-5">
        <div className="w-16 h-16 bg-brand-100 rounded-2xl flex items-center justify-center text-brand-700 text-2xl font-bold shrink-0">
          {student.full_name[0]}
        </div>
        <div className="flex-1">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h1 className="text-xl font-bold text-slate-900">{student.full_name}</h1>
              {student.preferred_name && <p className="text-sm text-slate-500">"{student.preferred_name}"</p>}
            </div>
            <Link href={`/students/${id}/edit`} className="btn-secondary text-sm flex items-center gap-1.5">
              <Edit2 size={13} /> Edit
            </Link>
          </div>
          <div className="flex flex-wrap gap-x-6 gap-y-1.5 mt-3 text-sm text-slate-600">
            <span><span className="text-slate-400">ID: </span>{student.student_number}</span>
            <span><span className="text-slate-400">Grade: </span>{student.grade_level ?? "—"}</span>
            <span><span className="text-slate-400">Class: </span>{student.class_name ?? "—"}</span>
            {student.nationality && <span><span className="text-slate-400">Nationality: </span>{student.nationality}</span>}
            {student.date_of_birth && <span><span className="text-slate-400">DOB: </span>{format(parseISO(student.date_of_birth), "dd MMM yyyy")}</span>}
          </div>
          <div className="mt-2">
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${student.is_active ? "bg-green-50 text-green-700" : "bg-slate-100 text-slate-500"}`}>
              {student.is_active ? "Active" : "Inactive"}
            </span>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-surface-border flex gap-6 overflow-x-auto">
        {(["overview", "attendance", "medical", "emergency"] as Tab[]).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`pb-3 text-sm font-medium capitalize whitespace-nowrap border-b-2 transition-colors ${
              tab === t ? "border-brand-500 text-brand-600" : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >{t === "emergency" ? "Emergency Contacts" : t}</button>
        ))}
      </div>

      {/* Overview */}
      {tab === "overview" && (
        <div className="grid sm:grid-cols-2 gap-4">
          {[
            { label: "Enrollment Date", value: student.enrollment_date ? format(parseISO(student.enrollment_date), "dd MMM yyyy") : "—" },
            { label: "Visa Expiry", value: student.visa_expiry ? format(parseISO(student.visa_expiry), "dd MMM yyyy") : "—" },
            { label: "Passport", value: student.passport_number ?? "—" },
            { label: "Homeroom Teacher ID", value: student.homeroom_teacher_id ?? "—" },
          ].map(({ label, value }) => (
            <div key={label} className="card p-4">
              <p className="text-xs text-slate-400 uppercase font-semibold tracking-wide">{label}</p>
              <p className="text-sm font-medium text-slate-800 mt-1">{value}</p>
            </div>
          ))}
          {student.notes && (
            <div className="card p-4 sm:col-span-2">
              <p className="text-xs text-slate-400 uppercase font-semibold tracking-wide mb-1">Notes</p>
              <p className="text-sm text-slate-700">{student.notes}</p>
            </div>
          )}
        </div>
      )}

      {/* Attendance */}
      {tab === "attendance" && (
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-3">
            <div className="card p-4 text-center">
              <p className="text-xl font-bold text-brand-600">{totalDays > 0 ? Math.round(presentDays / totalDays * 100) : 0}%</p>
              <p className="text-xs text-slate-500 mt-0.5">Attendance Rate</p>
            </div>
            <div className="card p-4 text-center">
              <p className="text-xl font-bold text-slate-800">{presentDays}</p>
              <p className="text-xs text-slate-500 mt-0.5">Days Present</p>
            </div>
            <div className="card p-4 text-center">
              <p className="text-xl font-bold text-red-500">{attendance?.filter((a: any) => a.status === "absent").length ?? 0}</p>
              <p className="text-xs text-slate-500 mt-0.5">Days Absent</p>
            </div>
          </div>
          <div className="card overflow-hidden">
            <table className="w-full text-sm">
              <thead><tr className="bg-slate-50 border-b border-surface-border">
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Date</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Status</th>
              </tr></thead>
              <tbody className="divide-y divide-surface-border">
                {(attendance ?? []).map((a: any) => (
                  <tr key={a.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3 text-slate-700">{format(parseISO(a.date), "EEE dd MMM yyyy")}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium capitalize ${STATUS_COLOR[a.status]}`}>
                        {a.status}{a.is_excused ? " (excused)" : ""}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Medical */}
      {tab === "medical" && (
        <div className="space-y-3">
          {!medical ? (
            <div className="card p-12 text-center text-slate-400"><Heart size={32} className="mx-auto mb-2 opacity-30" /><p>No medical record on file</p></div>
          ) : (
            <div className="grid sm:grid-cols-2 gap-4">
              {[
                { label: "Blood Type", value: medical.blood_type },
                { label: "Allergies", value: medical.allergies },
                { label: "Medical Conditions", value: medical.medical_conditions },
                { label: "Medications", value: medical.medications },
                { label: "Doctor", value: medical.doctor_name },
                { label: "Doctor Phone", value: medical.doctor_phone },
              ].filter(({ value }) => value).map(({ label, value }) => (
                <div key={label} className="card p-4">
                  <p className="text-xs text-slate-400 uppercase font-semibold tracking-wide mb-1">{label}</p>
                  <p className="text-sm text-slate-800">{value}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Emergency Contacts */}
      {tab === "emergency" && (
        <div className="space-y-3">
          {!contacts?.length ? (
            <div className="card p-12 text-center text-slate-400"><Phone size={32} className="mx-auto mb-2 opacity-30" /><p>No emergency contacts</p></div>
          ) : (
            contacts.map((c: any) => (
              <div key={c.id} className="card p-4 flex items-start gap-4">
                <div className="p-2.5 bg-brand-50 text-brand-600 rounded-lg shrink-0"><Phone size={16} /></div>
                <div>
                  <p className="font-semibold text-slate-900">{c.name}</p>
                  <p className="text-xs text-slate-500 capitalize">{c.relationship} · Priority {c.priority}</p>
                  <div className="flex gap-4 mt-1.5 text-sm text-slate-700">
                    <span>{c.phone_primary}</span>
                    {c.phone_secondary && <span className="text-slate-400">{c.phone_secondary}</span>}
                    {c.email && <a href={`mailto:${c.email}`} className="text-brand-600 hover:underline">{c.email}</a>}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
