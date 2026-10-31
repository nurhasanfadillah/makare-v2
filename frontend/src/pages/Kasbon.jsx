import { useCallback, useEffect, useState } from "react";
import { Plus, History, FileDown } from "lucide-react";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PageHeader, Loading, EmptyState, Field, selectCls } from "@/components/app/common";
import { api, downloadPdf, errMsg } from "@/lib/api";
import { rupiah, dateID } from "@/lib/format";

function GrantDialog({ open, onClose, onSaved }) {
  const [emps, setEmps] = useState([]);
  const [f, setF] = useState({ employee_id: "", amount: "", note: "" });
  const [busy, setBusy] = useState(false);
  const [employeesLoading, setEmployeesLoading] = useState(false);
  const [employeesError, setEmployeesError] = useState("");
  useEffect(() => {
    if (open) {
      let ignore = false;
      setF({ employee_id: "", amount: "", note: "" });
      setEmployeesLoading(true); setEmployeesError(""); setEmps([]);
      api.get("/employees", { params: { status: "active" } }).then((r) => { if (!ignore) setEmps(r.data); })
        .catch((e) => { if (!ignore) setEmployeesError(errMsg(e)); })
        .finally(() => { if (!ignore) setEmployeesLoading(false); });
      return () => { ignore = true; };
    }
  }, [open]);
  const save = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await api.post("/kasbon", { employee_id: Number(f.employee_id), amount: Number(f.amount), note: f.note || null });
      toast.success("Kasbon tercatat");
      onSaved();
      onClose();
    } catch (ex) { toast.error(errMsg(ex)); } finally { setBusy(false); }
  };
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent data-testid="kasbon-grant-dialog">
        <DialogHeader><DialogTitle>Catat Pemberian Kasbon</DialogTitle></DialogHeader>
        <form onSubmit={save} className="space-y-4">
          <Field label="Karyawan" required>
            <select className={selectCls} value={f.employee_id} onChange={(e) => setF({ ...f, employee_id: e.target.value })} required disabled={employeesLoading || !!employeesError || emps.length === 0} data-testid="kasbon-employee-select">
              <option value="">{employeesLoading ? "Memuat karyawan…" : employeesError ? "Gagal memuat karyawan" : emps.length === 0 ? "Tidak ada karyawan aktif" : "Pilih karyawan"}</option>
              {emps.map((x) => <option key={x.id} value={x.id}>{x.code} — {x.full_name}</option>)}
            </select>
          </Field>
          {employeesError && <div className="text-sm text-red-700" role="alert">{employeesError} <Button type="button" variant="link" onClick={async () => { setEmployeesLoading(true); setEmployeesError(""); try { setEmps((await api.get("/employees", { params: { status: "active" } })).data); } catch (e) { setEmployeesError(errMsg(e)); } finally { setEmployeesLoading(false); } }}>Coba lagi</Button></div>}
          <Field label="Nominal (Rp)" required><Input type="number" min="1" value={f.amount} onChange={(e) => setF({ ...f, amount: e.target.value })} required data-testid="kasbon-amount-input" /></Field>
          <Field label="Keterangan"><Input value={f.note} onChange={(e) => setF({ ...f, note: e.target.value })} data-testid="kasbon-note-input" /></Field>
          <p className="text-xs text-muted-foreground">Saldo tidak dapat diedit langsung. Potongan dicatat otomatis saat tutup buku.</p>
          <DialogFooter><Button type="button" variant="outline" onClick={onClose}>Batal</Button><Button disabled={busy || employeesLoading || !!employeesError || emps.length === 0} className="mk-gradient text-white" data-testid="kasbon-save-button">{busy ? "Menyimpan…" : "Simpan"}</Button></DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function LedgerDialog({ emp, onClose }) {
  const [rows, setRows] = useState(null);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    if (!emp) { setRows(null); setError(""); return; }
    let ignore = false;
    setRows(null); setError("");
    api.get(`/kasbon/${emp.employee_id}`).then((r) => { if (!ignore) setRows(r.data); })
      .catch((e) => { if (!ignore) setError(errMsg(e)); });
    return () => { ignore = true; };
  }, [emp, attempt]);
  return (
    <Dialog open={!!emp} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-2xl" data-testid="kasbon-ledger-dialog">
        <DialogHeader><DialogTitle>Riwayat Kasbon · {emp?.full_name}</DialogTitle></DialogHeader>
        {error ? <EmptyState title="Riwayat kasbon gagal dimuat" hint={error} action={<Button onClick={() => setAttempt((n) => n + 1)}>Coba lagi</Button>} /> : !rows ? <Loading /> : rows.length === 0 ? <EmptyState title="Belum ada transaksi kasbon" /> : (
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase text-muted-foreground"><tr><th className="py-2">Tanggal</th><th>Jenis</th><th>Keterangan</th><th className="text-right">Nominal</th></tr></thead>
            <tbody>{rows.map((r) => (
              <tr key={r.id} className="border-t">
                <td className="py-2">{dateID(r.tx_date)}</td>
                <td>{{ grant: "Pemberian", deduction: "Potongan payroll", reversal: "Pembatalan potongan (koreksi)" }[r.kind]}</td>
                <td className="text-muted-foreground">{r.note || "—"}{r.period_id && ` (periode #${r.period_id})`}</td>
                <td className={`text-right mk-num ${r.kind === "deduction" ? "text-red-700" : "text-emerald-700"}`}>{r.kind === "deduction" ? "−" : "+"}{rupiah(r.amount)}</td>
              </tr>
            ))}</tbody>
          </table>
        )}
      </DialogContent>
    </Dialog>
  );
}

export default function Kasbon() {
  const [list, setList] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [grant, setGrant] = useState(false);
  const [ledger, setLedger] = useState(null);
  const load = useCallback(async () => {
    setLoading(true); setError("");
    try { setList((await api.get("/kasbon")).data); }
    catch (e) { setList(null); setError(errMsg(e)); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);
  return (
    <div>
      <PageHeader eyebrow="Keuangan" title="Kasbon" subtitle="Saldo dihitung dari transaksi yang dapat ditelusuri. Sisa saldo dibawa ke periode berikutnya."
        actions={<div className="flex flex-wrap gap-2"><Button variant="outline" onClick={() => downloadPdf("/kasbon/report.pdf", "rekap-kasbon.pdf").catch((e) => toast.error(errMsg(e)))} data-testid="kasbon-report-pdf"><FileDown className="h-4 w-4 mr-1" />Rekap PDF</Button><Button className="mk-gradient text-white" onClick={() => setGrant(true)} data-testid="add-kasbon-button"><Plus className="h-4 w-4 mr-1" />Catat Kasbon</Button></div>} />
      <div className="mk-card">
        {loading ? <Loading /> : error ? <EmptyState title="Rekap kasbon gagal dimuat" hint={error} action={<Button onClick={load}>Coba lagi</Button>} /> : list.length === 0 ? <EmptyState title="Belum ada kasbon" /> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm" data-testid="kasbon-table">
              <thead className="bg-[#F4F7FB] text-left text-xs uppercase tracking-wider text-muted-foreground">
                <tr><th className="px-4 py-3">Karyawan</th><th className="px-4 py-3 text-right">Total diberikan</th><th className="px-4 py-3 text-right">Total dipotong</th><th className="px-4 py-3 text-right">Dibatalkan (koreksi)</th><th className="px-4 py-3 text-right">Saldo tersedia</th><th className="px-4 py-3 text-right">Riwayat</th></tr>
              </thead>
              <tbody>{list.map((r) => (
                <tr key={r.employee_id} className="border-t" data-testid={`kasbon-row-${r.code}`}>
                  <td className="px-4 py-3"><div className="font-medium">{r.full_name}</div><div className="text-xs text-muted-foreground mk-num">{r.code}</div></td>
                  <td className="px-4 py-3 text-right mk-num">{rupiah(r.total_grant)}</td>
                  <td className="px-4 py-3 text-right mk-num">{rupiah(r.total_deduction)}</td>
                  <td className="px-4 py-3 text-right mk-num">{rupiah(r.total_reversal)}</td>
                  <td className="px-4 py-3 text-right mk-num font-semibold text-[#0B1F3A]" data-testid={`kasbon-balance-${r.code}`}>{rupiah(r.balance)}</td>
                  <td className="px-4 py-3 text-right"><Button variant="ghost" size="sm" onClick={() => setLedger(r)} data-testid={`kasbon-ledger-${r.code}`}><History className="h-4 w-4" /></Button></td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </div>
      <GrantDialog open={grant} onClose={() => setGrant(false)} onSaved={load} />
      <LedgerDialog emp={ledger} onClose={() => setLedger(null)} />
    </div>
  );
}
