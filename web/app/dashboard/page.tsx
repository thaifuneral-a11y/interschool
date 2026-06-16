// app/dashboard/page.tsx
"use client";

import { useQuery } from "@tanstack/react-query";
import { dashboardApi } from "@/lib/api";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from "recharts";
import {
  Users, Calendar, BookOpen, ShieldAlert, AlertTriangle, TrendingUp
} from "lucide-react";

function KpiCard({
  label, value, sub, icon: Icon, color = "brand",
}: {
  label: string;
  value: string | number;
  sub?: string;
  icon: React.ElementType;
  color?: string;
}) {
  const colors: Record<string, string> = {
    brand:  "bg-brand-50 text-brand-600",
    green:  "bg-green-50 text-green-600",
    yellow: "bg-yellow-50 text-yellow-600",
    red:    "bg-red-50 text-red-600",
    purple: "bg-purple-50 text-purple-600",
  };
  return (
    <div className="card p-5 flex items-start gap-4">
      <div className={`p-2.5 rounded-lg ${colors[color]}`}>
        <Icon size={20} />
      </div>
      <div>
        <p className="text-2xl font-bold text-slate-900">{value}</p>
        <p className="text-sm font-medium text-slate-700">{label}</p>
        {sub && <p className="text-xs text-slate-400 mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const { data: overview, isLoading } = useQuery({
    queryKey: ["dashboard-overview"],
    queryFn: () => dashboardApi.overview().then((r) => r.data),
    refetchInterval: 60000,
  });

  const { data: trend } = useQuery({
    queryKey: ["attendance-trend"],
    queryFn: () => dashboardApi.attendanceTrend(30).then((r) => r.data),
  });

  const { data: atRisk } = useQuery({
    queryKey: ["at-risk-students"],
    queryFn: () => dashboardApi.atRiskStudents().then((r) => r.data),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Dashboard</h1>
        <p className="text-sm text-slate-500 mt-1">Student wellbeing overview for today</p>
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
        <KpiCard
          label="Attendance Today"
          value={`${overview?.attendance_today_pct ?? 0}%`}
          sub="Present or late"
          icon={Calendar}
          color={overview?.attendance_today_pct >= 90 ? "green" : "yellow"}
        />
        <KpiCard
          label="Weekly Avg Attendance"
          value={`${overview?.attendance_weekly_avg ?? 0}%`}
          sub="Last 7 days"
          icon={TrendingUp}
          color="brand"
        />
        <KpiCard
          label="Chronic Absentees"
          value={overview?.chronic_absentees ?? 0}
          sub="3+ absences in 14 days"
          icon={AlertTriangle}
          color={overview?.chronic_absentees > 0 ? "yellow" : "green"}
        />
        <KpiCard
          label="Total Students"
          value={overview?.total_students ?? 0}
          icon={Users}
          color="brand"
        />
        <KpiCard
          label="Open Counseling Cases"
          value={overview?.open_counseling_cases ?? 0}
          icon={BookOpen}
          color="purple"
        />
        <KpiCard
          label="Safeguarding Incidents"
          value={overview?.open_safeguarding_incidents ?? 0}
          sub={
            overview?.critical_incidents > 0
              ? `${overview.critical_incidents} CRITICAL`
              : "No critical"
          }
          icon={ShieldAlert}
          color={overview?.open_safeguarding_incidents > 0 ? "red" : "green"}
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        {/* Attendance Trend */}
        <div className="card p-5 xl:col-span-2">
          <h2 className="text-base font-semibold text-slate-800 mb-4">Attendance Trend (30 Days)</h2>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={trend ?? []} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} tickLine={false} />
              <YAxis domain={[60, 100]} tick={{ fontSize: 11 }} tickLine={false} unit="%" />
              <Tooltip
                formatter={(v: number) => [`${v}%`, "Attendance"]}
                contentStyle={{ borderRadius: 8, border: "1px solid #E2E8F0" }}
              />
              <Line
                type="monotone"
                dataKey="rate"
                stroke="#1A73E8"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* At Risk Students */}
        <div className="card p-5">
          <h2 className="text-base font-semibold text-slate-800 mb-4">At-Risk Students</h2>
          {!atRisk || atRisk.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-40 text-slate-400">
              <Users size={32} className="mb-2 opacity-30" />
              <p className="text-sm">No at-risk students</p>
            </div>
          ) : (
            <div className="space-y-3 overflow-y-auto max-h-52">
              {atRisk.map((s: any) => (
                <div key={s.student_id} className="flex items-start gap-3 p-3 bg-red-50 rounded-lg border border-red-100">
                  <div className="w-8 h-8 bg-red-100 rounded-full flex items-center justify-center text-red-700 text-xs font-bold shrink-0">
                    {s.full_name[0]}
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-slate-800 truncate">{s.full_name}</p>
                    <p className="text-xs text-slate-500">{s.grade_level} · {s.class_name}</p>
                    <p className="text-xs text-red-600 font-medium mt-0.5">
                      {s.consecutive_absences} days absent
                      {s.open_counseling && " · Counseling"}
                      {s.open_safeguarding && " · Safeguarding"}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
