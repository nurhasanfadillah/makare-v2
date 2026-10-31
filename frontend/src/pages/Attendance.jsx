import { useCallback, useEffect, useState } from "react";
import { LogIn, LogOut, Lock, KeyRound, PencilLine, Moon, ClipboardPlus } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PageHeader, StatusBadge, Loading, EmptyState } from "@/components/app/common";
import { useAuth } from "@/context/AuthContext";
import { api, errMsg } from "@/lib/api";
import { timeWIB, dur, dateID } from "@/lib/format";
import { EntryDialog, PinInputDialog, PinShowDialog, correctionInitial } from "./AttendanceDialogs";

function RegularCell({ a }) {
  if (!a) return <StatusBadge status="none" />;
  if (a.status !== "hadir") return <StatusBadge status={a.status} />;
  const open = !a.check_out;
  return (
    <div className="flex flex-wrap gap-1">
      <StatusBadge status={open ? "open" : "hadir"} />
      {a.calc?.is_late && <StatusBadge status="late" label={`Terlambat ${dur(a.calc.late_minutes)}${a.calc.first_hour_forfeited ? " · jam pertama gugur" : ""}`} />}
    </div>
  );
}

export default function Attendance() {
  const { isAdmin } = useAuth();
  const [date, setDate] = useState("");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(null);
  const [entry, setEntry] = useState(null);
  const [pinAsk, setPinAsk] = useState(null);
  const [pinShow, setPinShow] = useState(null);

  const load = useCallback(async () => {
    setLoading(true); setLoadError("");
    try {
      const r = await api.get("/attendance", { params: date ? { work_date: date } : {} });
      setData(r.data);
      if (!date) setDate(r.data.date);
    } catch (e) { setData(null); setLoadError(errMsg(e)); }
    finally { setLoading(false); }
  }, [date]);
  useEffect(() => { load(); }, [load]);

  const isToday = data && data.date === data.today;

  const doClock = async (emp, mode, action, early_pin) => {
    setBusy(emp.id);
    try {
      await api.post("/attendance/clock", { employee_id: emp.id, mode, action, early_pin });
      toast.success(`${emp.full_name}: ${action === "in" ? "Masuk" : "Keluar"} ${mode === "overtime" ? "lembur " : ""}tercatat`);
      setPinAsk(null);
      load();
    } catch (e) {
      if (e.response?.status === 428) setPinAsk({ emp, mode, action });
      else toast.error(errMsg(e));
    } finally { setBusy(null); }
  };

  const submitEntry = async (f) => {
    setBusy("entry");
    try {
      if (entry.record) {
        await api.put(`/attendance/${entry.record.id}`, f);
      } else {
        await api.post("/attendance/manual", { ...f, employee_id: entry.emp.id, work_date: isToday ? undefined : data.date });
      }
      toast.success("Absensi tersimpan");
      setEntry(null);
      load();
    } catch (e) { toast.error(errMsg(e)); } finally { setBusy(null); }
  };

  const genPin = async (emp) => {
    try {
      const r = await api.post(`/attendance/${emp.attendance.id}/early-pin`);
      setPinShow({ ...r.data, name: emp.full_name });
    } catch (e) { toast.error(errMsg(e)); }
  };

  if (loading && !data) return <Loading />;
  if (!data) return <div><PageHeader eyebrow="Absensi" title="Absensi" /><EmptyState title="Data absensi gagal dimuat" hint={loadError} action={<Button onClick={load}>Coba lagi</Button>} /></div>;
  const list = data.rows.filter((r) => `${r.code} ${r.full_name}`.toLowerCase().includes(q.toLowerCase()));

  return (
    <div>
      <PageHeader eyebrow={isToday ? "Hari ini" : "Historis"} title="Absensi" subtitle={`${dateID(data.date, true)} · waktu transaksi memakai jam server WIB`}
        actions={isAdmin && (
          <Input type="date" max={data.today} value={date} onChange={(e) => setDate(e.target.value)} className="w-44 bg-white" data-testid="attendance-date-input" />
        )} />
      {loading && <div className="mb-3 text-sm text-muted-foreground" role="status">Memuat data terbaru…</div>}
      {loadError && <div className="mb-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900" role="alert">Data terbaru gagal dimuat: {loadError} <Button variant="link" onClick={load}>Coba lagi</Button></div>}
      {data.locked && (
        <div className="mb-4 flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800" data-testid="attendance-locked-alert">
          <Lock className="h-4 w-4" /> Tanggal ini berada dalam periode yang sudah tutup buku. Data hanya dapat dilihat.
        </div>
      )}
      <div className="mk-card">
        <div className="p-4 border-b"><Input placeholder="Cari nama atau ID…" value={q} onChange={(e) => setQ(e.target.value)} className="max-w-sm" data-testid="attendance-search-input" /></div>
        {list.length === 0 ? <EmptyState title="Tidak ada karyawan" hint="Tambahkan karyawan aktif di menu Data Karyawan." /> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm" data-testid="attendance-table">
              <thead className="bg-[#F4F7FB] text-left text-xs uppercase tracking-wider text-muted-foreground">
                <tr><th className="px-4 py-3">Karyawan</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Masuk</th><th className="px-4 py-3">Keluar</th><th className="px-4 py-3">Dibayar</th><th className="px-4 py-3">Lembur</th><th className="px-4 py-3 text-right">Aksi</th></tr>
              </thead>
              <tbody>
                {list.map((r) => {
                  const a = r.attendance;
                  const open = a && a.status === "hadir" && !a.check_out;
                  const otMin = r.overtime.reduce((s, o) => s + o.calc.paid_minutes, 0);
                  const canAct = !data.locked && r.active;
                  return (
                    <tr key={r.id} className="border-t align-middle" data-testid={`attendance-row-${r.code}`}>
                      <td className="px-4 py-3"><div className="font-medium">{r.full_name}</div><div className="text-xs text-muted-foreground mk-num">{r.code} · {r.department || "—"}</div></td>
                      <td className="px-4 py-3"><RegularCell a={a} /></td>
                      <td className="px-4 py-3 mk-num">{timeWIB(a?.check_in)}{a && a.work_date !== data.date && <div className="text-xs text-amber-700">dari {dateID(a.work_date)}</div>}</td>
                      <td className="px-4 py-3 mk-num">{timeWIB(a?.check_out)}{a?.early_leave && <div className="text-xs text-amber-700">lebih awal</div>}</td>
                      <td className="px-4 py-3 mk-num">{a?.calc && !a.calc.incomplete ? dur(a.calc.paid_minutes) : "—"}</td>
                      <td className="px-4 py-3 mk-num">{r.overtime_open ? <StatusBadge status="open" label="Lembur berjalan" /> : otMin ? dur(otMin) : "—"}</td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap justify-end gap-1.5">
                          {canAct && isToday && !a && <>
                            <Button size="sm" disabled={busy === r.id} onClick={() => doClock(r, "regular", "in")} className="bg-emerald-600 hover:bg-emerald-700 text-white" data-testid={`clock-in-${r.code}`}><LogIn className="h-3.5 w-3.5 mr-1" />Masuk</Button>
                            <Button size="sm" variant="outline" onClick={() => setEntry({ emp: r, title: `Status ${r.full_name}` })} data-testid={`status-entry-${r.code}`}><ClipboardPlus className="h-3.5 w-3.5 mr-1" />Sakit/Izin/Alfa</Button>
                          </>}
                          {canAct && open && <Button size="sm" disabled={busy === r.id} onClick={() => doClock(r, "regular", "out")} className="bg-red-600 hover:bg-red-700 text-white" data-testid={`clock-out-${r.code}`}><LogOut className="h-3.5 w-3.5 mr-1" />Keluar</Button>}
                          {canAct && open && isAdmin && <Button size="sm" variant="outline" onClick={() => genPin(r)} data-testid={`early-pin-${r.code}`}><KeyRound className="h-3.5 w-3.5 mr-1" />PIN</Button>}
                          {canAct && isToday && data.overtime_enabled && !open && (
                            <Button size="sm" variant="outline" disabled={busy === r.id} onClick={() => doClock(r, "overtime", r.overtime_open ? "out" : "in")} data-testid={`overtime-${r.overtime_open ? "out" : "in"}-${r.code}`}>
                              <Moon className="h-3.5 w-3.5 mr-1" />{r.overtime_open ? "Keluar Lembur" : "Masuk Lembur"}
                            </Button>
                          )}
                          {isAdmin && !data.locked && !isToday && !a && r.active && <Button size="sm" variant="outline" onClick={() => setEntry({ emp: r, historical: true, title: `Input historis ${r.full_name}` })} data-testid={`historical-entry-${r.code}`}><ClipboardPlus className="h-3.5 w-3.5 mr-1" />Input</Button>}
                          {isAdmin && !data.locked && a && <Button size="sm" variant="ghost" onClick={() => setEntry({ emp: r, record: a, correction: true, initial: correctionInitial(a), title: `Koreksi ${r.full_name}` })} data-testid={`correct-${r.code}`}><PencilLine className="h-3.5 w-3.5 mr-1" />Koreksi</Button>}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
      <EntryDialog open={!!entry} onClose={() => setEntry(null)} onSubmit={submitEntry} busy={busy === "entry"} title={entry?.title}
        historical={entry?.historical} correction={entry?.correction} initial={entry?.initial}
        description={entry?.correction ? "Koreksi tercatat di audit log beserta nilai sebelum dan sesudah." : undefined} />
      <PinInputDialog open={!!pinAsk} name={pinAsk?.emp.full_name} busy={busy === pinAsk?.emp.id} onClose={() => setPinAsk(null)}
        onSubmit={(pin) => doClock(pinAsk.emp, pinAsk.mode, pinAsk.action, pin)} />
      <PinShowDialog data={pinShow} onClose={() => setPinShow(null)} />
    </div>
  );
}
