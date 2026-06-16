// app/notifications/page.tsx
"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { notificationsApi } from "@/lib/api";
import { Bell, CheckCheck } from "lucide-react";
import { formatDistanceToNow } from "date-fns";

const CATEGORY_COLOR: Record<string, string> = {
  attendance: "bg-yellow-100 text-yellow-700",
  counseling: "bg-purple-100 text-purple-700",
  safeguarding: "bg-red-100 text-red-700",
  announcement: "bg-brand-100 text-brand-700",
  meeting: "bg-green-100 text-green-700",
  system: "bg-slate-100 text-slate-600",
};

export default function NotificationsPage() {
  const qc = useQueryClient();

  const { data: notifications, isLoading } = useQuery({
    queryKey: ["notifications"],
    queryFn: () => notificationsApi.list({ limit: 50 }).then((r) => r.data),
  });

  const markRead = useMutation({
    mutationFn: (id: string) => notificationsApi.markRead(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications"] }),
  });

  const markAll = useMutation({
    mutationFn: () => notificationsApi.markAllRead(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications"] }),
  });

  const unreadCount = notifications?.filter((n: any) => !n.is_read).length ?? 0;

  return (
    <div className="space-y-5 max-w-2xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="flex items-center gap-2"><Bell size={22} className="text-brand-600" /> Notifications</h1>
          <p className="text-sm text-slate-500 mt-0.5">{unreadCount} unread</p>
        </div>
        {unreadCount > 0 && (
          <button className="btn-secondary text-sm flex items-center gap-2" onClick={() => markAll.mutate()}>
            <CheckCheck size={14} /> Mark all read
          </button>
        )}
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16"><div className="w-7 h-7 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" /></div>
      ) : !notifications?.length ? (
        <div className="card p-16 text-center text-slate-400">
          <Bell size={36} className="mx-auto mb-3 opacity-20" />
          <p className="font-medium">You're all caught up</p>
          <p className="text-sm mt-1">No notifications yet</p>
        </div>
      ) : (
        <div className="space-y-2">
          {notifications.map((n: any) => (
            <div
              key={n.id}
              className={`card p-4 flex items-start gap-4 cursor-pointer transition-colors ${
                !n.is_read ? "bg-brand-50/40 border-brand-100" : "hover:bg-slate-50"
              }`}
              onClick={() => !n.is_read && markRead.mutate(n.id)}
            >
              <div className={`p-2 rounded-lg text-xs font-bold uppercase ${CATEGORY_COLOR[n.category] ?? "bg-slate-100 text-slate-600"}`}>
                <Bell size={14} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-2">
                  <p className={`text-sm ${!n.is_read ? "font-semibold text-slate-900" : "font-medium text-slate-700"}`}>{n.title}</p>
                  <span className={`shrink-0 w-2 h-2 rounded-full mt-1.5 ${!n.is_read ? "bg-brand-500" : "invisible"}`} />
                </div>
                <p className="text-sm text-slate-500 mt-0.5 leading-snug">{n.body}</p>
                <p className="text-xs text-slate-400 mt-1.5">{formatDistanceToNow(new Date(n.created_at), { addSuffix: true })}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
