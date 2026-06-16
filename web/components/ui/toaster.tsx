// components/ui/toaster.tsx
"use client";

import { useEffect, useState } from "react";
import { CheckCircle, AlertCircle, X } from "lucide-react";

export type Toast = { id: string; type: "success" | "error" | "info"; message: string };

let _setToasts: React.Dispatch<React.SetStateAction<Toast[]>> | null = null;

export function toast(message: string, type: Toast["type"] = "success") {
  const id = Math.random().toString(36).slice(2);
  _setToasts?.((prev) => [...prev, { id, type, message }]);
  setTimeout(() => _setToasts?.((prev) => prev.filter((t) => t.id !== id)), 4000);
}

export function Toaster() {
  const [toasts, setToasts] = useState<Toast[]>([]);
  useEffect(() => { _setToasts = setToasts; return () => { _setToasts = null; }; }, []);

  return (
    <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 pointer-events-none">
      {toasts.map((t) => (
        <div key={t.id} className={`flex items-center gap-3 px-4 py-3 rounded-xl shadow-modal pointer-events-auto text-sm font-medium animate-in slide-in-from-right duration-300 max-w-sm ${
          t.type === "success" ? "bg-white border border-green-200 text-green-800" :
          t.type === "error"   ? "bg-white border border-red-200 text-red-800" :
                                 "bg-white border border-brand-200 text-brand-800"
        }`}>
          {t.type === "success" ? <CheckCircle size={16} className="text-green-500 shrink-0" /> :
           t.type === "error"   ? <AlertCircle size={16} className="text-red-500 shrink-0" /> :
                                  <AlertCircle size={16} className="text-brand-500 shrink-0" />}
          <span className="flex-1">{t.message}</span>
          <button onClick={() => setToasts((p) => p.filter((x) => x.id !== t.id))} className="text-slate-400 hover:text-slate-600">
            <X size={14} />
          </button>
        </div>
      ))}
    </div>
  );
}
