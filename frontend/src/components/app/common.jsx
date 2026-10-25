import { CheckCircle2, Thermometer, FileText, XCircle, Loader2, Inbox, Clock, AlertTriangle } from "lucide-react";

export function PageHeader({ eyebrow, title, subtitle, actions }) {
  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between mb-6 mk-fade">
      <div>
        {eyebrow && <div className="mk-eyebrow mb-1">{eyebrow}</div>}
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-[#0B1F3A]" data-testid="page-title">{title}</h1>
        {subtitle && <p className="text-sm text-muted-foreground mt-1">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

const STATUS = {
  hadir: { label: "Hadir", icon: CheckCircle2, cls: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  sakit: { label: "Sakit", icon: Thermometer, cls: "bg-sky-50 text-sky-700 border-sky-200" },
  izin: { label: "Izin", icon: FileText, cls: "bg-amber-50 text-amber-700 border-amber-200" },
  alfa: { label: "Alfa", icon: XCircle, cls: "bg-red-50 text-red-700 border-red-200" },
  open: { label: "Sedang bekerja", icon: Clock, cls: "bg-blue-50 text-[#174EA6] border-blue-200" },
  late: { label: "Terlambat", icon: AlertTriangle, cls: "bg-amber-50 text-amber-700 border-amber-200" },
  active: { label: "Aktif", icon: CheckCircle2, cls: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  inactive: { label: "Nonaktif", icon: XCircle, cls: "bg-slate-100 text-slate-600 border-slate-200" },
  none: { label: "Belum absen", icon: Clock, cls: "bg-slate-50 text-slate-500 border-slate-200" },
};

export function StatusBadge({ status, label, testid }) {
  const s = STATUS[status] || STATUS.none;
  const Icon = s.icon;
  return (
    <span data-testid={testid} className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-semibold ${s.cls}`}>
      <Icon className="h-3.5 w-3.5" aria-hidden />
      {label || s.label}
    </span>
  );
}

export function Loading({ text = "Memuat data…" }) {
  return (
    <div className="flex items-center justify-center gap-2 py-16 text-muted-foreground" data-testid="loading-state">
      <Loader2 className="h-5 w-5 animate-spin" /> {text}
    </div>
  );
}

export function EmptyState({ title, hint, action }) {
  return (
    <div className="flex flex-col items-center justify-center text-center py-14 px-6" data-testid="empty-state">
      <div className="h-12 w-12 rounded-2xl bg-accent flex items-center justify-center mb-3">
        <Inbox className="h-6 w-6 text-[#174EA6]" />
      </div>
      <div className="font-semibold text-[#0B1F3A]">{title}</div>
      {hint && <p className="text-sm text-muted-foreground mt-1 max-w-sm">{hint}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function StatCard({ label, value, hint, icon: Icon, testid }) {
  return (
    <div className="mk-card p-5 mk-fade" data-testid={testid}>
      <div className="flex items-start justify-between">
        <div className="mk-eyebrow">{label}</div>
        {Icon && <div className="h-9 w-9 rounded-lg bg-accent flex items-center justify-center"><Icon className="h-4.5 w-4.5 text-[#174EA6]" /></div>}
      </div>
      <div className="mt-2 text-3xl font-bold text-[#0B1F3A] mk-num">{value}</div>
      {hint && <div className="text-xs text-muted-foreground mt-1">{hint}</div>}
    </div>
  );
}

export function Field({ label, children, hint, required }) {
  return (
    <label className="block space-y-1.5">
      <span className="text-sm font-medium text-[#172A46]">{label}{required && <span className="text-red-600"> *</span>}</span>
      {children}
      {hint && <span className="block text-xs text-muted-foreground">{hint}</span>}
    </label>
  );
}

export const selectCls = "h-10 w-full rounded-md border border-input bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring";
