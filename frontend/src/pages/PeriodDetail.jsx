import { Fragment, useCallback, useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { FileDown, ChevronDown, ChevronRight, Lock, ArrowLeft, PencilLine } from "lucide-react";
import { AdjustmentDialog, KIND_LABEL } from "@/components/app/AdjustmentDialog";
import { toast } from "sonner";
import { PageHeader, Loading, EmptyState } from "@/components/app/common";
import { PayrollBreakdown } from "@/components/app/PayrollBreakdown";
import { api, errMsg, downloadPdf } from "@/lib/api";
import { rupiah, dur, dateID, dateTimeID } from "@/lib/format";
import { Button } from "@/components/ui/button";

export default function PeriodDetail() {
  const { id } = useParams();
  const [p, setP] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState({});
  const [adjLine, setAdjLine] = useState(null);
  const load = useCallback(async () => {
    setLoading(true); setError("");
    try { setP((await api.get(`/payroll/periods/${id}`)).data); }
    catch (e) { setP(null); setError(errMsg(e)); }
    finally { setLoading(false); }
  }, [id]);
  useEffect(() => { load(); }, [load]);
  const pdf = (path, name) => downloadPdf(path, name).catch((e) => toast.error(errMsg(e)));
  if (loading) return <Loading />;
  if (!p) return <div><PageHeader eyebrow="Penggajian" title="Detail Tutup Buku" /><EmptyState title="Periode gagal dimuat" hint={error} action={<Button onClick={load}>Coba lagi</Button>} /></div>;
  return (
    <div>
      <Link to="/riwayat" className="inline-flex items-center gap-1 text-sm text-muted-foreground mb-3"><ArrowLeft className="h-4 w-4" />Riwayat</Link>
      <PageHeader eyebrow={`Snapshot final #${p.id}`} title={`${dateID(p.start_date)} – ${dateID(p.end_date)}`}
        subtitle={`Dikunci oleh ${p.closed_by} · ${dateTimeID(p.closed_at)}`}
        actions={<Button className="mk-gradient text-white" onClick={() => pdf(`/payroll/periods/${p.id}/recap.pdf`, `rekap-gaji-${p.id}.pdf`)} data-testid="recap-pdf-button"><FileDown className="h-4 w-4 mr-1" />Rekap Gaji PDF</Button>} />
      <div className="mb-4 flex items-center gap-2 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-[#174EA6]"><Lock className="h-4 w-4" />Data di bawah berasal dari snapshot tersimpan, bukan dihitung ulang dari data master terbaru.</div>
      <div className="mk-card overflow-x-auto">
        <table className="w-full text-sm" data-testid="period-lines-table">
          <thead className="bg-[#F4F7FB] text-left text-xs uppercase tracking-wider text-muted-foreground">
            <tr><th className="px-3 py-3" /><th className="px-3 py-3">Karyawan</th><th className="px-3 py-3 text-right">Jam dibayar</th><th className="px-3 py-3 text-right">Gaji kotor</th><th className="px-3 py-3 text-right">Kasbon</th><th className="px-3 py-3 text-right">Gaji bersih</th><th className="px-3 py-3 text-right">Koreksi</th><th className="px-3 py-3 text-right">Bersih efektif</th><th className="px-3 py-3 text-right">Aksi</th></tr>
          </thead>
          <tbody>{p.lines.map((l) => (
            <Fragment key={l.employee_id}>
              <tr className="border-t" data-testid={`period-line-${l.code}`}>
                <td className="px-3 py-2"><button type="button" onClick={() => setOpen({ ...open, [l.employee_id]: !open[l.employee_id] })} aria-label={`Rincian gaji ${l.full_name}`} aria-expanded={Boolean(open[l.employee_id])}>{open[l.employee_id] ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}</button></td>
                <td className="px-3 py-2"><div className="font-medium">{l.full_name}</div><div className="text-xs text-muted-foreground mk-num">{l.code}</div></td>
                <td className="px-3 py-2 text-right mk-num">{dur(l.durations.paid_minutes)}</td>
                <td className="px-3 py-2 text-right mk-num">{rupiah(l.gross)}</td>
                <td className="px-3 py-2 text-right mk-num">{rupiah(l.kasbon_deduction)}</td>
                <td className="px-3 py-2 text-right mk-num">{rupiah(l.net_final)}</td>
                <td className={`px-3 py-2 text-right mk-num ${l.adj_net > 0 ? "text-emerald-700" : l.adj_net < 0 ? "text-red-700" : "text-muted-foreground"}`} data-testid={`adj-net-${l.code}`}>{l.adj_count ? `${l.adj_net >= 0 ? "+" : "−"}${rupiah(Math.abs(l.adj_net))}` : "—"}</td>
                <td className="px-3 py-2 text-right mk-num font-semibold text-[#0B1F3A]" data-testid={`net-effective-${l.code}`}>{rupiah(l.net_effective)}</td>
                <td className="px-3 py-2 text-right whitespace-nowrap"><Button size="sm" variant="ghost" onClick={() => setAdjLine(l)} data-testid={`adjust-${l.code}`}><PencilLine className="h-3.5 w-3.5 mr-1" />Koreksi</Button><Button size="sm" variant="outline" aria-label={`Unduh slip gaji ${l.full_name}`} onClick={() => pdf(`/payroll/periods/${p.id}/slip/${l.employee_id}.pdf`, `slip-${l.code}-${p.id}.pdf`)} data-testid={`slip-pdf-${l.code}`}><FileDown className="h-3.5 w-3.5" /></Button></td>
              </tr>
              {open[l.employee_id] && <tr><td colSpan={9} className="p-0"><PayrollBreakdown line={l} /></td></tr>}
            </Fragment>
          ))}</tbody>
        </table>
      </div>
      <div className="mk-card mt-6" data-testid="adjustments-card">
        <div className="flex flex-wrap items-center justify-between gap-2 p-4 border-b">
          <div className="font-bold text-[#0B1F3A]">Riwayat koreksi</div>
          <div className="text-sm">Total dampak <span className="mk-num font-semibold" data-testid="adjustment-net-total">{p.adjustment_net >= 0 ? "+" : "−"}{rupiah(Math.abs(p.adjustment_net))}</span> · Bersih efektif <span className="mk-num font-semibold">{rupiah(p.net_effective_total)}</span></div>
        </div>
        {p.adjustments.length === 0 ? <p className="p-4 text-sm text-muted-foreground">Belum ada koreksi untuk periode ini.</p> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm" data-testid="adjustments-table">
              <thead className="bg-[#F4F7FB] text-left text-xs uppercase tracking-wider text-muted-foreground">
                <tr><th className="px-4 py-3">Waktu</th><th className="px-4 py-3">Karyawan</th><th className="px-4 py-3">Jenis</th><th className="px-4 py-3">Alasan</th><th className="px-4 py-3 text-right">Nominal</th><th className="px-4 py-3 text-right">Bersih sebelum → sesudah</th><th className="px-4 py-3">Oleh</th></tr>
              </thead>
              <tbody>{p.adjustments.map((a) => (
                <tr key={a.id} className="border-t align-top" data-testid={`adjustment-row-${a.id}`}>
                  <td className="px-4 py-2 text-xs whitespace-nowrap">{dateTimeID(a.created_at)}</td>
                  <td className="px-4 py-2"><div className="font-medium">{a.full_name}</div><div className="text-xs text-muted-foreground mk-num">{a.code}</div></td>
                  <td className="px-4 py-2">{KIND_LABEL[a.kind]}</td>
                  <td className="px-4 py-2 text-muted-foreground max-w-xs break-words">{a.reason}</td>
                  <td className={`px-4 py-2 text-right mk-num ${a.kind === "deduction" ? "text-red-700" : "text-emerald-700"}`}>{a.kind === "deduction" ? "−" : "+"}{rupiah(a.amount)}</td>
                  <td className="px-4 py-2 text-right mk-num text-xs">{rupiah(a.before.net_final)} → {rupiah(a.after.net_final)}</td>
                  <td className="px-4 py-2 text-xs">{a.created_by}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </div>
      <AdjustmentDialog periodId={p.id} line={adjLine} onClose={() => setAdjLine(null)} onSaved={load} />
    </div>
  );
}
