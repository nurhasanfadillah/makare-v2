import { useCallback, useEffect, useState } from "react";
import { FileDown, Search } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { PageHeader, Loading, EmptyState, selectCls } from "@/components/app/common";
import { api, downloadPdf, errMsg } from "@/lib/api";
import { dateID } from "@/lib/format";

const today = new Date();
const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const monthStart = new Date(today.getFullYear(), today.getMonth(), 1);
const hm = (m) => `${Math.floor(m / 60)}j ${String(m % 60).padStart(2, "0")}m`;
const statusLabel = { hadir: "Hadir", sakit: "Sakit", izin: "Izin", alfa: "Alfa manual", tanpa_catatan: "Tanpa catatan (inferensi)" };

export default function AttendanceReport() {
  const [employees, setEmployees] = useState([]);
  const [filter, setFilter] = useState({ start_date: iso(monthStart), end_date: iso(today), employee_id: "" });
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [reportError, setReportError] = useState("");
  const [employeeError, setEmployeeError] = useState("");
  useEffect(() => { api.get("/employees", { params: { status: "all" } }).then((r) => setEmployees(r.data)).catch((e) => setEmployeeError(errMsg(e))); }, []);
  const load = useCallback(async () => {
    setLoading(true);
    setReportError("");
    try { const r = await api.get("/reports/attendance", { params: { ...filter, employee_id: filter.employee_id || undefined } }); setReport(r.data); }
    catch (e) { setReport(null); setReportError(errMsg(e)); }
    finally { setLoading(false); }
  }, [filter]);
  const field = (key) => (e) => setFilter((v) => ({ ...v, [key]: e.target.value }));
  const exportPdf = () => {
    const params = new URLSearchParams({ start_date: filter.start_date, end_date: filter.end_date });
    if (filter.employee_id) params.set("employee_id", filter.employee_id);
    downloadPdf(`/reports/attendance.pdf?${params}`, "rekap-kehadiran.pdf").catch((e) => toast.error(errMsg(e)));
  };
  return <div>
    <PageHeader eyebrow="Analisis" title="Laporan Absensi" subtitle="Membedakan Alfa yang dicatat dengan hari kerja tanpa catatan kehadiran."
      actions={<Button variant="outline" onClick={exportPdf} disabled={!report}><FileDown className="h-4 w-4 mr-1" />Unduh PDF</Button>} />
    <div className="mk-card mb-5 p-4 flex flex-col md:flex-row gap-3 md:items-end">
      <label className="text-sm flex flex-col gap-1">Dari tanggal<input className={selectCls} type="date" value={filter.start_date} onChange={field("start_date")} /></label>
      <label className="text-sm flex flex-col gap-1">Sampai tanggal<input className={selectCls} type="date" value={filter.end_date} onChange={field("end_date")} /></label>
      <label className="text-sm flex flex-col gap-1 flex-1">Karyawan<select className={selectCls} value={filter.employee_id} onChange={field("employee_id")}><option value="">Semua karyawan</option>{employees.map((e) => <option key={e.id} value={e.id}>{e.code} — {e.full_name}</option>)}</select></label>
      <Button className="mk-gradient text-white" onClick={load} disabled={loading}><Search className="h-4 w-4 mr-1" />Tampilkan</Button>
    </div>
    {employeeError && <div className="mb-3 text-sm text-amber-800" role="alert">Filter karyawan gagal dimuat: {employeeError}</div>}
    {loading ? <Loading /> : reportError ? <EmptyState title="Laporan gagal dimuat" hint={reportError} action={<Button onClick={load}>Coba lagi</Button>} /> : !report ? <EmptyState title="Pilih filter laporan" hint="Tentukan rentang tanggal dan tampilkan untuk melihat rekap." /> : <>
      <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3 mb-5">
        {[['Hadir', report.summary.hadir], ['Sakit', report.summary.sakit], ['Izin', report.summary.izin], ['Alfa manual', report.summary.alfa_manual], ['Tanpa catatan', report.summary.inferred_absence], ['Durasi > 24 jam', report.summary.sessions_over_24h]].map(([label, value]) => <div className="mk-card p-4" key={label}><div className="text-xs text-muted-foreground">{label}</div><div className="text-xl font-bold mk-num">{value}</div></div>)}
      </div>
      {report.rows.length === 0 ? <EmptyState title="Tidak ada data pada filter ini" /> : <div className="mk-card overflow-x-auto"><table className="w-full text-sm"><thead className="bg-[#F4F7FB] text-left text-xs uppercase text-muted-foreground"><tr>{['Tanggal','ID','Nama','Status','Reguler','Lembur','Terlambat','Sumber','Peringatan'].map((x) => <th className="px-3 py-3" key={x}>{x}</th>)}</tr></thead><tbody>{report.rows.map((r, i) => <tr key={`${r.employee_id}-${r.work_date}-${i}`} className="border-t"><td className="px-3 py-2 whitespace-nowrap">{dateID(r.work_date)}</td><td className="px-3 py-2">{r.code}</td><td className="px-3 py-2">{r.full_name}</td><td className="px-3 py-2">{statusLabel[r.status] || r.status}</td><td className="px-3 py-2 mk-num">{hm(r.regular_minutes)}{r.regular_open ? ' · terbuka' : ''}</td><td className="px-3 py-2 mk-num">{hm(r.overtime_minutes)}{r.overtime_open ? ' · terbuka' : ''}</td><td className="px-3 py-2 mk-num">{hm(r.late_minutes)}</td><td className="px-3 py-2">{r.inferred_absence ? 'Inferensi' : r.attendance_source || '—'}</td><td className="px-3 py-2">{r.duration_over_24h ? <span className="font-medium text-amber-700">Periksa durasi</span> : '—'}</td></tr>)}</tbody></table></div>}
    </>}
  </div>;
}
