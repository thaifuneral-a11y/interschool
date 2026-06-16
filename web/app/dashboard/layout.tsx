// app/dashboard/layout.tsx
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard, Users, Calendar, BookOpen, ShieldAlert,
  Bell, Settings, LogOut, Menu, X, ChevronDown, School
} from "lucide-react";
import { authApi, notificationsApi } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";
import clsx from "clsx";

const NAV_ITEMS = [
  { href: "/dashboard",           icon: LayoutDashboard, label: "Dashboard",    roles: [] },
  { href: "/students",            icon: Users,           label: "Students",     roles: [] },
  { href: "/attendance",          icon: Calendar,        label: "Attendance",   roles: [] },
  { href: "/counseling",          icon: BookOpen,        label: "Counseling",   roles: ["counselor","principal","school_admin","super_admin"] },
  { href: "/safeguarding",        icon: ShieldAlert,     label: "Safeguarding", roles: ["counselor","principal","school_admin","super_admin"] },
  { href: "/parent-portal",       icon: Users,           label: "Parent Portal",roles: ["parent"] },
  { href: "/notifications",       icon: Bell,            label: "Notifications",roles: [] },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const { data: user } = useQuery({
    queryKey: ["me"],
    queryFn: () => authApi.me().then((r) => r.data),
    retry: false,
  });

  const { data: notifs } = useQuery({
    queryKey: ["notifications-unread"],
    queryFn: () => notificationsApi.list({ unread_only: true, limit: 5 }).then((r) => r.data),
    refetchInterval: 30000,
  });

  const unreadCount = Array.isArray(notifs) ? notifs.length : 0;

  const handleLogout = async () => {
    const rt = localStorage.getItem("refresh_token") ?? "";
    await authApi.logout(rt).catch(() => {});
    localStorage.clear();
    router.push("/auth/login");
  };

  return (
    <div className="flex h-screen overflow-hidden bg-surface">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={clsx(
          "fixed inset-y-0 left-0 z-30 w-64 bg-white border-r border-surface-border flex flex-col transition-transform duration-200 lg:relative lg:translate-x-0",
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {/* Logo */}
        <div className="flex items-center gap-3 px-6 py-5 border-b border-surface-border">
          <div className="w-8 h-8 bg-brand-500 rounded-lg flex items-center justify-center">
            <School size={16} className="text-white" />
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-900 leading-tight">Student Care OS</p>
            <p className="text-xs text-slate-500">International School</p>
          </div>
          <button className="ml-auto lg:hidden" onClick={() => setSidebarOpen(false)}>
            <X size={18} className="text-slate-400" />
          </button>
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-1">
          {NAV_ITEMS.map((item) => {
            const active = pathname === item.href || pathname.startsWith(item.href + "/");
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setSidebarOpen(false)}
                className={clsx(
                  "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
                  active
                    ? "bg-brand-50 text-brand-700"
                    : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                )}
              >
                <item.icon size={18} className={active ? "text-brand-600" : "text-slate-400"} />
                {item.label}
                {item.href === "/notifications" && unreadCount > 0 && (
                  <span className="ml-auto bg-brand-500 text-white text-xs rounded-full px-2 py-0.5">
                    {unreadCount}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* User */}
        <div className="border-t border-surface-border p-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-brand-100 rounded-full flex items-center justify-center text-brand-700 text-sm font-semibold">
              {user?.full_name?.[0] ?? "U"}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-slate-900 truncate">{user?.full_name ?? "Loading…"}</p>
              <p className="text-xs text-slate-500 truncate">{user?.email ?? ""}</p>
            </div>
            <button onClick={handleLogout} title="Logout" className="p-1.5 rounded-lg hover:bg-slate-100 transition-colors">
              <LogOut size={16} className="text-slate-400" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <header className="bg-white border-b border-surface-border px-4 lg:px-6 h-14 flex items-center gap-4 shrink-0">
          <button className="lg:hidden p-2 rounded-lg hover:bg-slate-100" onClick={() => setSidebarOpen(true)}>
            <Menu size={20} className="text-slate-600" />
          </button>
          <div className="flex-1" />
          <Link href="/notifications" className="relative p-2 rounded-lg hover:bg-slate-100">
            <Bell size={20} className="text-slate-600" />
            {unreadCount > 0 && (
              <span className="absolute top-1 right-1 w-4 h-4 bg-brand-500 text-white text-xs rounded-full flex items-center justify-center">
                {unreadCount}
              </span>
            )}
          </Link>
        </header>

        {/* Page */}
        <main className="flex-1 overflow-y-auto p-4 lg:p-6">{children}</main>
      </div>
    </div>
  );
}
