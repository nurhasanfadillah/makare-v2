import { Fragment, useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { FileDown, ChevronDown, ChevronRight, Lock, ArrowLeft } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { PageHeader, Loading } from "@/components/app/common";
import { PayrollBreakdown } from "@/components/app/PayrollBreakdown";
import { api, errMsg, downloadPdf } from "@/lib/api";
import { rupiah, dur, dateID, dateTimeID } from "@/lib/format";

export default function PeriodDetail() {
  const { id } = useParams();
  const [p, setP] = useState(null);
  const [open, setOpen] = useState({});
  useEffect(() => { api.get(`/payroll/periods/${id}`).then((r) => setP(r.data)).catch((e) => toast.error(errMsg(e))); }, [id]);
  const pdf = (path, name) => downloadPdf(path, name).catch((e) => toast.error(errMsg(e)));
  if (!p) return <Loading />;
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
            <tr><th className="px-3 py-3" /><th className="px-3 py-3">Karyawan</th><th className="px-3 py-3 text-right">Jam dibayar</th><th className="px-3 py-3 text-right">Gaji kotor</th><th className="px-3 py-3 text-right">Kasbon</th><th className="px-3 py-3 text-right">Gaji bersih</th><th className="px-3 py-3 text-right">Slip</th></tr>
          </thead>
          <tbody>{p.lines.map((l) => (
            <Fragment key={l.employee_id}>
              <tr className="border-t" data-testid={`period-line-${l.code}`}>
                <td className="px-3 py-2"><button onClick={() => setOpen({ ...open, [l.employee_id]: !open[l.employee_id] })} aria-label="Rincian">{open[l.employee_id] ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}</button></td>
                <td className="px-3 py-2"><div className="font-medium">{l.full_name}</div><div className="text-xs text-muted-foreground mk-num">{l.code}</div></td>
                <td className="px-3 py-2 text-right mk-num">{dur(l.durations.paid_minutes)}</td>
                <td className="px-3 py-2 text-right mk-num">{rupiah(l.gross)}</td>
                <td className="px-3 py-2 text-right mk-num">{rupiah(l.kasbon_deduction)}</td>
                <td className="px-3 py-2 text-right mk-num font-semibold">{rupiah(l.net_final)}</td>
                <td className="px-3 py-2 text-right"><Button size="sm" variant="outline" onClick={() => pdf(`/payroll/periods/${p.id}/slip/${l.employee_id}.pdf`, `slip-${l.code}-${p.id}.pdf`)} data-testid={`slip-pdf-${l.code}`}><FileDown className="h-3.5 w-3.5" /></Button></td>
              </tr>
              {open[l.employee_id] && <tr><td colSpan={7} className="p-0"><PayrollBreakdown line={l} /></td></tr>}
            </Fragment>
          ))}</tbody>
        </table>
      </div>
    </div>
  );
}
