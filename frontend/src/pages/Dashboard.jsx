import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Users, CalendarCheck, AlarmClock, Timer, ArrowRight, Wallet, BookLock } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { StatCard, Loading, EmptyState } from "@/components/app/common";
import { dateID, dateTimeID, rupiah } from "@/lib/format";
import { Button } from "@/components/ui/button";

const ACTIONS = {
  regular_in: "Masuk reguler", regular_out: "Keluar reguler", overtime_in: "Masuk lembur", overtime_out: "Keluar lembur",
  attendance_manual: "Absensi manual", attendance_corrected: "Koreksi absensi", employee_created: "Karyawan ditambahkan",
  employee_updated: "Data karyawan diubah", closing_finalized: "Tutup buku", kasbon_granted: "Kasbon diberikan",
  settings_updated: "Pengaturan diubah", early_pin_created: "PIN keluar awal dibuat",
};

export default function Dashboard() {
  const { user, isAdmin } = useAuth();
  const [d, setD] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try { setD((await api.get("/dashboard")).data); }
    catch (e) { setD(null); setError(errMsg(e)); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  if (loading) return <Loading />;
  if (error) return <EmptyState title="Gagal memuat dashboard" hint={error} action={<Button onClick={load}>Coba lagi</Button>} />;
  if (!d) return <Loading />;
  const t = d.today;
  return (
    <div className="space-y-6">
      <section className="mk-gradient mk-hero-grid rounded-2xl text-white p-6 sm:p-8 shadow-xl shadow-blue-900/15 relative overflow-hidden mk-fade" data-testid="dashboard-hero">
        <div className="text-xs uppercase tracking-[0.2em] text-white/70">{dateID(d.date, true)}</div>
        <h1 className="mt-2 text-3xl sm:text-4xl font-extrabold tracking-tight">Halo, {user.full_name}</h1>
        <p className="text-white/80 mt-1">Ringkasan operasional hari ini dari database.</p>
        <div className="mt-6 grid grid-cols-2 sm:grid-cols-4 gap-3 max-w-3xl">
          {[["Hadir", t.hadir], ["Sakit", t.sakit], ["Izin", t.izin], ["Alfa", t.alfa]].map(([l, v]) => (
            <div key={l} className="rounded-xl bg-white/12 backdrop-blur-md border border-white/15 px-4 py-3" data-testid={`hero-count-${l.toLowerCase()}`}>
              <div className="text-xs text-white/70">{l}</div>
              <div className="text-2xl font-bold mk-num">{v}</div>
            </div>
          ))}
        </div>
      </section>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard testid="stat-active-employees" label="Karyawan aktif" value={d.active_employees} icon={Users} />
        <StatCard testid="stat-present-today" label="Kehadiran hari ini" value={t.hadir} hint={`dari ${d.active_employees} karyawan aktif`} icon={CalendarCheck} />
        <StatCard testid="stat-late-today" label="Terlambat" value={d.late_today} hint="Masuk setelah jam kerja dimulai" icon={AlarmClock} />
        <StatCard testid="stat-open-sessions" label="Sesi terbuka" value={d.open_sessions} hint={d.overtime_enabled ? `${d.open_overtime} sesi lembur terbuka` : "Lembur nonaktif"} icon={Timer} />
      </div>

      {isAdmin && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="mk-card p-6" data-testid="payroll-period-card">
            <div className="flex items-center gap-2 mk-eyebrow"><BookLock className="h-4 w-4" /> Periode payroll berjalan</div>
            <div className="mt-3 text-lg font-bold text-[#0B1F3A]">{dateID(d.next_period.start_date)} — hari ini</div>
            <div className="text-sm text-muted-foreground mt-1">
              {d.last_period ? `Tutup buku terakhir: ${dateID(d.last_period.start_date)} – ${dateID(d.last_period.end_date)}` : "Belum ada tutup buku"}
            </div>
            <Link to="/tutup-buku" className="mt-4 inline-flex items-center gap-1 text-sm font-semibold text-[#174EA6] hover:gap-2 transition-[gap]" data-testid="goto-closing-link">
              Mulai tutup buku <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
          <div className="mk-card p-6" data-testid="kasbon-card">
            <div className="flex items-center gap-2 mk-eyebrow"><Wallet className="h-4 w-4" /> Saldo kasbon beredar</div>
            <div className="mt-3 text-2xl font-bold text-[#0B1F3A] mk-num">{rupiah(d.kasbon_outstanding)}</div>
            <Link to="/kasbon" className="mt-4 inline-flex items-center gap-1 text-sm font-semibold text-[#174EA6]">Lihat kasbon <ArrowRight className="h-4 w-4" /></Link>
          </div>
          <div className="mk-card p-6" data-testid="recent-activity-card">
            <div className="mk-eyebrow mb-3">Aktivitas terbaru</div>
            {d.recent_activity.length === 0 ? <p className="text-sm text-muted-foreground">Belum ada aktivitas.</p> : (
              <ul className="space-y-2.5">
                {d.recent_activity.map((a, i) => (
                  <li key={i} className="flex justify-between gap-3 text-sm">
                    <span className="truncate"><span className="font-semibold">{a.actor}</span> · {ACTIONS[a.action] || a.action}</span>
                    <span className="text-xs text-muted-foreground whitespace-nowrap">{dateTimeID(a.created_at)}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
      {!isAdmin && (
        <Link to="/absensi" data-testid="operator-goto-attendance" className="mk-card p-6 flex items-center justify-between hover:shadow-md transition-shadow">
          <div><div className="font-bold text-[#0B1F3A]">Catat absensi hari ini</div><div className="text-sm text-muted-foreground">Masuk, Keluar, Sakit, Izin, atau Alfa</div></div>
          <ArrowRight className="h-5 w-5 text-[#174EA6]" />
        </Link>
      )}
    </div>
  );
}
