import { useCallback, useEffect, useMemo, useState } from "react";
import { BookOpenCheck, CalendarClock, LockKeyhole, Pencil, RefreshCw, Wallet } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { PageHeader, Loading, EmptyState } from "@/components/app/common";
import EmployeeForm from "@/pages/EmployeeForm";
import { api, errMsg } from "@/lib/api";
import { dateID, rupiah } from "@/lib/format";

export default function ManualPayroll() {
  const [period, setPeriod] = useState(null);
  const [closedPeriods, setClosedPeriods] = useState([]);
  const [selectedClosed, setSelectedClosed] = useState("");
  const [preview, setPreview] = useState(null);
  const [snapshot, setSnapshot] = useState(null);
  const [departments, setDepartments] = useState([]);
  const [editingEmployee, setEditingEmployee] = useState(null);
  const [loadingCurrent, setLoadingCurrent] = useState(true);
  const [loadingSnapshot, setLoadingSnapshot] = useState(false);
  const [currentError, setCurrentError] = useState("");
  const [snapshotError, setSnapshotError] = useState("");
  const [snapshotAttempt, setSnapshotAttempt] = useState(0);

  const loadCurrent = useCallback(async () => {
    setLoadingCurrent(true);
    setCurrentError("");
    try {
      const [next, periods] = await Promise.all([api.get("/payroll/next-period"), api.get("/payroll/periods")]);
      setPeriod(next.data);
      setClosedPeriods(periods.data);
      if (next.data.start_date <= next.data.max_end_date) {
        const result = await api.post("/payroll/preview", { end_date: next.data.max_end_date, adjustments: {} });
        setPreview(result.data);
      } else {
        setPreview(null);
      }
    } catch (e) {
      setPeriod(null); setPreview(null); setCurrentError(errMsg(e));
    } finally {
      setLoadingCurrent(false);
    }
  }, []);

  useEffect(() => { loadCurrent(); }, [loadCurrent]);
  useEffect(() => { api.get("/departments").then((r) => setDepartments(r.data)).catch((e) => toast.error(errMsg(e))); }, []);

  useEffect(() => {
    if (!selectedClosed) { setSnapshot(null); setSnapshotError(""); setLoadingSnapshot(false); return; }
    let ignore = false;
    setSnapshot(null); setSnapshotError("");
    setLoadingSnapshot(true);
    api.get(`/payroll/periods/${selectedClosed}`)
      .then((r) => { if (!ignore) setSnapshot(r.data); })
      .catch((e) => { if (!ignore) setSnapshotError(errMsg(e)); })
      .finally(() => { if (!ignore) setLoadingSnapshot(false); });
    return () => { ignore = true; };
  }, [selectedClosed, snapshotAttempt]);

  const currentLines = useMemo(() => (preview?.lines || []).filter((line) => line.payroll_mode === "manual"), [preview]);
  const snapshotLines = useMemo(() => (snapshot?.lines || []).filter((line) => line.payroll_mode === "manual"), [snapshot]);
  const currentTotal = currentLines.reduce((sum, line) => sum + line.gross, 0);
  const closedTotal = snapshotLines.reduce((sum, line) => sum + (line.net_effective ?? line.net_final), 0);

  const activeLines = selectedClosed ? snapshotLines : currentLines;
  const isClosed = Boolean(selectedClosed);

  return (
    <div>
      <PageHeader eyebrow="Penggajian · manual" title="Manajemen Gaji Manual"
        subtitle="Kelola komponen gaji karyawan manual dan tinjau nilainya berdasarkan periode payroll."
        actions={<Button variant="outline" onClick={loadCurrent} disabled={loadingCurrent} data-testid="manual-payroll-refresh"><RefreshCw className={`h-4 w-4 mr-2 ${loadingCurrent ? "animate-spin" : ""}`} />Perbarui data</Button>} />

      <div className="grid gap-4 sm:grid-cols-2 mb-5">
        <div className="mk-card p-5">
          <div className="flex items-center gap-2 text-sm font-semibold text-[#174EA6]"><CalendarClock className="h-4 w-4" />Periode berjalan</div>
          {period && <div className="mt-2 text-sm text-muted-foreground">{period.start_date <= period.max_end_date
            ? `${dateID(period.start_date)} – ${dateID(period.max_end_date)} · belum tutup buku`
            : `Menunggu periode berikutnya mulai ${dateID(period.start_date)}`}</div>}
          <div className="mt-3 text-2xl font-bold mk-num text-[#0B1F3A]">{rupiah(currentTotal)}</div>
          <div className="text-xs text-muted-foreground">Pratinjau gaji kotor manual · {currentLines.length} karyawan</div>
        </div>
        <div className="mk-card p-5">
          <div className="flex items-center gap-2 text-sm font-semibold text-[#174EA6]"><LockKeyhole className="h-4 w-4" />Periode ditutup</div>
          <select className="mt-3 h-10 w-full rounded-md border border-input bg-white px-3 text-sm" value={selectedClosed} onChange={(e) => setSelectedClosed(e.target.value)} aria-label="Pilih periode tutup buku" data-testid="manual-payroll-period-select">
            <option value="">Pilih periode tutup buku</option>
            {closedPeriods.map((p) => <option key={p.id} value={p.id}>{dateID(p.start_date)} – {dateID(p.end_date)} · snapshot #{p.id}</option>)}
          </select>
          <div className="mt-2 text-xs text-muted-foreground">{isClosed ? `Bersih efektif · ${snapshotLines.length} karyawan · ${rupiah(closedTotal)}` : `${closedPeriods.length} periode tersimpan`}</div>
        </div>
      </div>

      <div className="mb-4 flex items-start gap-3 rounded-xl border border-blue-200 bg-blue-50 p-4 text-sm text-[#174EA6]">
        {isClosed ? <LockKeyhole className="h-5 w-5 shrink-0" /> : <BookOpenCheck className="h-5 w-5 shrink-0" />}
        <div>{isClosed
          ? "Periode ini sudah tutup buku. Rincian di bawah berasal dari snapshot komponen saat finalisasi dan bersifat hanya-baca. Koreksi nilai final dilakukan melalui Riwayat Tutup Buku."
          : "Periode berjalan memakai komponen master karyawan. Perubahan komponen berlaku pada pratinjau dan periode yang belum ditutup; snapshot periode final tidak berubah."}</div>
      </div>

      {loadingCurrent ? <Loading /> : currentError ? <EmptyState title="Data gaji manual gagal dimuat" hint={currentError} action={<Button onClick={loadCurrent}>Coba lagi</Button>} /> : !period ? <EmptyState title="Periode payroll tidak tersedia" /> : (
        <div className="mk-card overflow-x-auto" data-testid="manual-payroll-table-wrap">
          {loadingSnapshot ? <Loading /> : snapshotError ? <EmptyState title="Snapshot gagal dimuat" hint={snapshotError} action={<Button onClick={() => setSnapshotAttempt((attempt) => attempt + 1)}>Coba lagi</Button>} /> : (
            <table className="w-full text-sm" data-testid="manual-payroll-table">
              <thead className="bg-[#F4F7FB] text-left text-xs uppercase tracking-wider text-muted-foreground">
                <tr><th className="px-4 py-3">Karyawan</th><th className="px-4 py-3">Komponen gaji</th><th className="px-4 py-3 text-right">Gaji kotor manual</th><th className="px-4 py-3 text-right">Saldo kasbon</th><th className="px-4 py-3 text-right">Kasbon periode</th>{isClosed && <th className="px-4 py-3 text-right">Koreksi</th>}<th className="px-4 py-3 text-right">{isClosed ? "Bersih efektif" : "Gaji bersih"}</th><th className="px-4 py-3 text-right">Status / aksi</th></tr>
              </thead>
              <tbody>{activeLines.map((line) => (
                <tr key={line.employee_id} className="border-t align-top" data-testid={`manual-payroll-row-${line.code}`}>
                  <td className="px-4 py-3"><div className="font-semibold text-[#0B1F3A]">{line.full_name}</div><div className="text-xs text-muted-foreground mk-num">{line.code} · {line.department || "Tanpa departemen"}</div></td>
                  <td className="px-4 py-3 min-w-64">{line.components?.length ? <ul className="space-y-1">{line.components.map((c, i) => <li key={`${c.name}-${i}`}><span>{c.name} <span className="text-xs text-muted-foreground">{rupiah(c.amount)} × {c.volume}</span></span></li>)}</ul> : <span className="text-muted-foreground">Belum ada komponen</span>}</td>
                  <td className="px-4 py-3 text-right mk-num font-semibold">{rupiah(line.gross)}</td>
                  <td className="px-4 py-3 text-right mk-num">{rupiah(line.kasbon_balance)}</td>
                  <td className="px-4 py-3 text-right mk-num">{rupiah(line.kasbon_deduction)}</td>
                  {isClosed && <td className="px-4 py-3 text-right mk-num">{line.adj_count ? `${line.adj_net >= 0 ? "+" : "−"}${rupiah(Math.abs(line.adj_net))}` : "—"}</td>}
                  <td className="px-4 py-3 text-right mk-num font-semibold">{rupiah(isClosed ? line.net_effective : line.net_final)}</td>
                  <td className="px-4 py-3 text-right whitespace-nowrap">{isClosed
                    ? <span className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-slate-50 px-2 py-1 text-xs font-semibold text-slate-600"><LockKeyhole className="h-3 w-3" />Terkunci</span>
                    : <Button size="sm" variant="outline" onClick={() => setEditingEmployee(line.employee_id)} data-testid={`manual-payroll-edit-${line.code}`}><Pencil className="h-3.5 w-3.5 mr-1" />Atur komponen</Button>}</td>
                </tr>
              ))}</tbody>
            </table>
          )}
          {!loadingSnapshot && activeLines.length === 0 && <EmptyState title={isClosed ? "Tidak ada gaji manual pada periode ini" : "Belum ada karyawan manual pada periode berjalan"} hint={isClosed ? undefined : "Ubah mode payroll karyawan di Data Karyawan untuk mengelola komponen manual."} />}
        </div>
      )}

      {!isClosed && <div className="mt-4 flex items-center gap-2 text-xs text-muted-foreground"><Wallet className="h-4 w-4" />Komponen dihitung sebagai nominal × volume. Nilai final disimpan saat Tutup Buku; pembayaran kasbon tetap mengikuti pratinjau tutup buku.</div>}

      <EmployeeForm open={editingEmployee !== null} employeeId={editingEmployee} departments={departments}
        onClose={() => setEditingEmployee(null)} onSaved={() => { setEditingEmployee(null); loadCurrent(); }} />
    </div>
  );
}
