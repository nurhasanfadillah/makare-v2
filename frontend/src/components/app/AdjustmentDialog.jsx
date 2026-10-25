import { useEffect, useRef, useState } from "react";
import { Loader2, ArrowRight, AlertTriangle } from "lucide-react";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Field, selectCls } from "@/components/app/common";
import { api, errMsg } from "@/lib/api";
import { rupiah } from "@/lib/format";

export const KIND_LABEL = {
  earning: "Tambahan (kurang bayar)",
  deduction: "Potongan (lebih bayar)",
  kasbon_reversal: "Pembatalan potongan kasbon",
};

function ImpactTable({ imp }) {
  const rowsDef = [
    ["Gaji bersih efektif", "net_final"],
    ["Potongan kasbon periode", "kasbon_deduction"],
    ["Saldo kasbon karyawan", "kasbon_balance"],
  ];
  return (
    <div className="rounded-xl border overflow-hidden" data-testid="adjustment-impact">
      <table className="w-full text-sm">
        <thead className="bg-[#F4F7FB] text-xs uppercase tracking-wider text-muted-foreground">
          <tr><th className="px-3 py-2 text-left">Nilai</th><th className="px-3 py-2 text-right">Sebelum</th><th /><th className="px-3 py-2 text-right">Sesudah</th></tr>
        </thead>
        <tbody>{rowsDef.map(([l, k]) => {
          const changed = imp.before[k] !== imp.after[k];
          return (
            <tr key={k} className="border-t">
              <td className="px-3 py-2">{l}</td>
              <td className="px-3 py-2 text-right mk-num">{rupiah(imp.before[k])}</td>
              <td className="px-1 text-muted-foreground"><ArrowRight className="h-3.5 w-3.5" /></td>
              <td className={`px-3 py-2 text-right mk-num ${changed ? "font-bold text-[#174EA6]" : ""}`} data-testid={`impact-after-${k}`}>{rupiah(imp.after[k])}</td>
            </tr>
          );
        })}</tbody>
      </table>
      <div className={`px-3 py-2 text-sm font-semibold border-t ${imp.delta_net >= 0 ? "bg-emerald-50 text-emerald-800" : "bg-red-50 text-red-800"}`} data-testid="impact-delta">
        Dampak finansial: {imp.delta_net >= 0 ? "+" : "−"}{rupiah(Math.abs(imp.delta_net))} terhadap gaji bersih karyawan
      </div>
    </div>
  );
}

export function AdjustmentDialog({ periodId, line, onClose, onSaved }) {
  const [f, setF] = useState({ kind: "earning", amount: "", reason: "" });
  const [imp, setImp] = useState(null);
  const [agree, setAgree] = useState(false);
  const [busy, setBusy] = useState(false);
  const idem = useRef("");

  useEffect(() => {
    if (line) {
      setF({ kind: "earning", amount: "", reason: "" });
      setImp(null);
      setAgree(false);
      idem.current = crypto.randomUUID();
    }
  }, [line]);

  const set = (k) => (e) => { setF({ ...f, [k]: e.target.value }); setImp(null); setAgree(false); };
  const body = () => ({ employee_id: line.employee_id, kind: f.kind, amount: Number(f.amount) });

  const preview = async () => {
    setBusy(true);
    try { setImp((await api.post(`/payroll/periods/${periodId}/adjustments/preview`, body())).data); }
    catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };

  const submit = async () => {
    setBusy(true);
    try {
      await api.post(`/payroll/periods/${periodId}/adjustments`, { ...body(), reason: f.reason.trim(), idempotency_key: idem.current });
      toast.success("Koreksi tercatat sebagai transaksi penyesuaian");
      onSaved();
      onClose();
    } catch (e) { toast.error(errMsg(e)); setBusy(false); }
  };

  const ready = Number(f.amount) > 0 && f.reason.trim().length >= 5;
  return (
    <Dialog open={!!line} onOpenChange={(o) => !o && !busy && onClose()}>
      <DialogContent className="max-w-lg" data-testid="adjustment-dialog">
        <DialogHeader>
          <DialogTitle>Koreksi Payroll · {line?.full_name}</DialogTitle>
          <DialogDescription>Snapshot asli tidak diubah. Koreksi disimpan sebagai transaksi penyesuaian beserta alasan dan pelaku.</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <Field label="Jenis koreksi" required>
            <select className={selectCls} value={f.kind} onChange={set("kind")} data-testid="adjustment-kind-select">
              {Object.entries(KIND_LABEL).map(([k, l]) => <option key={k} value={k} disabled={k === "kasbon_reversal" && !line?.kasbon_effective}>{l}</option>)}
            </select>
          </Field>
          <Field label="Nominal (Rp)" required hint={f.kind === "kasbon_reversal" ? `Maks ${rupiah(line?.kasbon_effective)} (potongan kasbon efektif)` : f.kind === "deduction" ? `Maks ${rupiah(line?.net_effective)} (gaji bersih efektif)` : undefined}>
            <Input type="number" min="1" value={f.amount} onChange={set("amount")} data-testid="adjustment-amount-input" />
          </Field>
          <Field label="Alasan koreksi" required hint="Minimal 5 karakter, tersimpan di audit log">
            <Textarea rows={3} value={f.reason} onChange={set("reason")} data-testid="adjustment-reason-input" />
          </Field>
          {imp && <ImpactTable imp={imp} />}
          {imp && (
            <label className="flex items-start gap-2 text-sm"><Checkbox checked={agree} onCheckedChange={(v) => setAgree(!!v)} data-testid="adjustment-agree-checkbox" />
              Saya memahami dampak finansial di atas dan koreksi ini tidak dapat dihapus.</label>
          )}
          {f.kind === "kasbon_reversal" && <div className="flex gap-2 text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded-lg p-2"><AlertTriangle className="h-4 w-4 shrink-0" />Saldo kasbon karyawan akan bertambah kembali sebesar nominal ini.</div>}
        </div>
        <DialogFooter>
          <Button variant="outline" disabled={busy} onClick={onClose} data-testid="adjustment-cancel-button">Batal</Button>
          {!imp ? (
            <Button disabled={!ready || busy} onClick={preview} className="mk-gradient text-white" data-testid="adjustment-preview-button">{busy && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}Lihat Dampak</Button>
          ) : (
            <Button disabled={!agree || busy} onClick={submit} className="mk-gradient text-white" data-testid="adjustment-submit-button">{busy && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}Simpan Koreksi</Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
