import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { PageHeader, Loading, EmptyState } from "@/components/app/common";
import { api, errMsg } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { rupiah, dateID, dateTimeID } from "@/lib/format";

export default function Periods() {
  const [list, setList] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const load = useCallback(async () => {
    setLoading(true); setError("");
    try { setList((await api.get("/payroll/periods")).data); }
    catch (e) { setList(null); setError(errMsg(e)); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);
  return (
    <div>
      <PageHeader eyebrow="Penggajian" title="Riwayat Tutup Buku" subtitle="Setiap periode tersimpan sebagai snapshot final." />
      <div className="mk-card">
        {loading ? <Loading /> : error ? <EmptyState title="Riwayat gagal dimuat" hint={error} action={<Button onClick={load}>Coba lagi</Button>} /> : list.length === 0 ? <EmptyState title="Belum ada tutup buku" hint="Periode yang sudah dikunci akan muncul di sini." /> : (
          <table className="w-full text-sm" data-testid="periods-table">
            <thead className="bg-[#F4F7FB] text-left text-xs uppercase tracking-wider text-muted-foreground">
              <tr><th className="px-4 py-3">Periode</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Karyawan</th><th className="px-4 py-3 text-right">Gaji kotor</th><th className="px-4 py-3 text-right">Kasbon</th><th className="px-4 py-3 text-right">Gaji bersih</th><th className="px-4 py-3 text-right">Koreksi</th><th className="px-4 py-3">Dikunci</th><th /></tr>
            </thead>
            <tbody>{list.map((p) => (
              <tr key={p.id} className="border-t" data-testid={`period-row-${p.id}`}>
                <td className="px-4 py-3 font-medium">{dateID(p.start_date)} – {dateID(p.end_date)}</td>
                <td className="px-4 py-3"><span className="inline-flex rounded-full bg-emerald-50 px-2 py-1 text-xs font-medium text-emerald-700">{p.status === "closed" ? "Tutup buku final" : p.status}</span></td>
                <td className="px-4 py-3 mk-num">{p.totals.employees}</td>
                <td className="px-4 py-3 text-right mk-num">{rupiah(p.totals.gross)}</td>
                <td className="px-4 py-3 text-right mk-num">{rupiah(p.totals.kasbon_deduction)}</td>
                <td className="px-4 py-3 text-right mk-num font-semibold">{rupiah(p.totals.net_final)}</td>
                <td className="px-4 py-3 text-right mk-num text-xs" data-testid={`period-adj-${p.id}`}>{p.adjustment_count ? `${p.adjustment_count}× · ${p.adjustment_net >= 0 ? "+" : "−"}${rupiah(Math.abs(p.adjustment_net))}` : "—"}</td>
                <td className="px-4 py-3 text-xs text-muted-foreground">{p.closed_by} · {dateTimeID(p.closed_at)}</td>
                <td className="px-4 py-3 text-right"><Link to={`/riwayat/${p.id}`} className="inline-flex items-center gap-1 text-[#174EA6] font-semibold" data-testid={`period-open-${p.id}`}>Detail <ArrowRight className="h-4 w-4" /></Link></td>
              </tr>
            ))}</tbody>
          </table>
        )}
      </div>
    </div>
  );
}
