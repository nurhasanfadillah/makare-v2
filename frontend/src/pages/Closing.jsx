import { Fragment, useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronDown, ChevronRight, Loader2, RefreshCw, ShieldCheck, AlertTriangle, Lock, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { PageHeader, Loading, EmptyState } from "@/components/app/common";
import { PayrollBreakdown } from "@/components/app/PayrollBreakdown";
import { api, errMsg } from "@/lib/api";
import { rupiah, dur, dateID } from "@/lib/format";

const STEPS = ["Pilih periode", "Pratinjau & penyesuaian", "Konfirmasi"];

function Stepper({ step }) {
  return (
    <ol className="flex flex-wrap gap-2 mb-6" data-testid="closing-stepper">
      {STEPS.map((s, i) => (
        <li key={s} className={`flex items-center gap-2 rounded-full px-4 py-1.5 text-sm font-semibold border ${i === step ? "mk-gradient text-white border-transparent" : i < step ? "bg-white text-[#174EA6] border-blue-200" : "bg-white text-muted-foreground"}`}>
          <span className="mk-num">{i + 1}</span>{s}
        </li>
      ))}
    </ol>
  );
}

function Totals({ t }) {
  const items = [["Karyawan", t.employees, false], ["Gaji kotor", t.gross], ["Potongan lain", t.other_deduction], ["Potongan kasbon", t.kasbon_deduction], ["Total gaji bersih", t.net_final]];
  return (
    <div className="mk-gradient mk-hero-grid rounded-2xl text-white p-6 grid grid-cols-2 md:grid-cols-5 gap-4" data-testid="closing-totals">
      {items.map(([l, v, money = true]) => (
        <div key={l}><div className="text-xs text-white/70">{l}</div><div className="text-xl font-bold mk-num">{money ? rupiah(v) : v}</div></div>
      ))}
    </div>
  );
}

function PeriodComponents({ line, value, onChange }) {
  const components = value ?? line.components ?? [];
  const update = (index, key, next) => onChange(components.map((item, i) => i === index ? { ...item, [key]: next } : item));
  return (
    <div className="border-t bg-slate-50 p-4" data-testid={`period-components-${line.code}`}>
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
        <div><div className="text-sm font-semibold text-[#0B1F3A]">Komponen gaji periode ini</div><div className="text-xs text-muted-foreground">Perubahan hanya berlaku untuk periode ini. Klik Hitung Ulang sebelum menyetujui total.</div></div>
        <Button type="button" variant="outline" size="sm" disabled={busy} onClick={() => onChange([...components, { name: "", amount: 0, volume: 1, note: "" }])} data-testid={`add-period-component-${line.code}`}><Plus className="h-3.5 w-3.5 mr-1" />Tambah komponen</Button>
      </div>
      {components.length === 0 && <div className="mb-3 text-xs text-muted-foreground">Belum ada komponen; tambahkan bonus, insentif, atau komponen penghasilan periode ini.</div>}
      <div className="space-y-2">{components.map((component, index) => (
        <div className="grid grid-cols-12 gap-2" key={`${component.name}-${index}`} data-testid={`period-component-row-${line.code}-${index}`}>
          <Input disabled={busy} className="col-span-12 sm:col-span-4" aria-label="Nama komponen periode" placeholder="Nama komponen" value={component.name} onChange={(e) => update(index, "name", e.target.value)} />
          <Input disabled={busy} className="col-span-5 sm:col-span-3" aria-label="Nominal komponen periode" type="number" min="0" step="1" placeholder="Nominal Rp" value={component.amount} onChange={(e) => update(index, "amount", e.target.value === "" ? 0 : Number(e.target.value))} />
          <Input disabled={busy} className="col-span-3 sm:col-span-2" aria-label="Volume komponen periode" type="number" min="0" step="0.01" placeholder="Volume" value={component.volume} onChange={(e) => update(index, "volume", e.target.value === "" ? 0 : Number(e.target.value))} />
          <Input disabled={busy} className="col-span-3 sm:col-span-2" aria-label="Keterangan komponen periode" placeholder="Keterangan" value={component.note || ""} onChange={(e) => update(index, "note", e.target.value)} />
          <Button disabled={busy} className="col-span-1" type="button" variant="ghost" size="icon" aria-label="Hapus komponen periode" onClick={() => onChange(components.filter((_, i) => i !== index))}><Trash2 className="h-4 w-4 text-red-600" /></Button>
        </div>
      ))}</div>
    </div>
  );
}

export default function Closing() {
  const nav = useNavigate();
  const [period, setPeriod] = useState(null);
  const [end, setEnd] = useState("");
  const [step, setStep] = useState(0);
  const [preview, setPreview] = useState(null);
  const [adj, setAdj] = useState({});
  const [open, setOpen] = useState({});
  const [busy, setBusy] = useState(false);
  const [agree, setAgree] = useState(false);
  const [periodError, setPeriodError] = useState("");
  const [periodLoading, setPeriodLoading] = useState(true);
  const idem = useRef(crypto.randomUUID());

  const loadPeriod = useCallback(async () => {
    setPeriodLoading(true); setPeriodError("");
    try { const r = await api.get("/payroll/next-period"); setPeriod(r.data); setEnd((v) => v || r.data.max_end_date); }
    catch (e) { setPeriod(null); setPeriodError(errMsg(e)); }
    finally { setPeriodLoading(false); }
  }, []);
  useEffect(() => { loadPeriod(); }, [loadPeriod]);

  const run = async (nextStep) => {
    setBusy(true);
    try {
      const r = await api.post("/payroll/preview", { end_date: end, adjustments: adj });
      setPreview(r.data);
      setStep(nextStep);
    } catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };

  const setA = (eid, k, v) => setAdj((prev) => ({ ...prev, [eid]: { ...prev[eid], [k]: v === "" ? (k === "kasbon_deduction" ? null : 0) : Number(v) } }));
  const setComponents = (eid, components) => setAdj((prev) => ({ ...prev, [eid]: { ...prev[eid], components } }));
  const toggleLine = (line) => {
    const isOpening = !open[line.employee_id];
    setOpen((prev) => ({ ...prev, [line.employee_id]: isOpening }));
    if (isOpening) setAdj((prev) => ({ ...prev, [line.employee_id]: { ...prev[line.employee_id], components: prev[line.employee_id]?.components ?? line.components.map((c) => ({ ...c })) } }));
  };

  const finalize = async () => {
    setBusy(true);
    try {
      const r = await api.post("/payroll/finalize", { end_date: end, adjustments: adj, idempotency_key: idem.current });
      toast.success("Tutup buku berhasil. Periode telah dikunci.");
      nav(`/riwayat/${r.data.period_id}`);
    } catch (e) { toast.error(errMsg(e)); setBusy(false); }
  };

  if (periodLoading) return <Loading />;
  if (!period) return <div><PageHeader eyebrow="Penggajian" title="Tutup Buku" /><EmptyState title="Periode payroll gagal dimuat" hint={periodError} action={<Button onClick={loadPeriod}>Coba lagi</Button>} /></div>;
  const startAfterEnd = period.start_date > period.max_end_date;
  const incomplete = preview?.lines.reduce((s, l) => s + l.counts.incomplete, 0) || 0;

  return (
    <div>
      <PageHeader eyebrow="Penggajian" title="Tutup Buku" subtitle="Pratinjau dihitung server. Snapshot final tidak dapat diedit setelah dikunci." />
      <Stepper step={step} />
      {step === 0 && (
        <div className="mk-card p-6 max-w-xl mk-fade" data-testid="closing-step-period">
          {startAfterEnd ? <EmptyState title="Belum ada hari yang dapat ditutup" hint={`Periode berikutnya dimulai ${dateID(period.start_date)}.`} /> : <>
            <div className="grid grid-cols-2 gap-4">
              <div><div className="mk-eyebrow">Tanggal awal</div><div className="mt-1 text-lg font-bold" data-testid="closing-start-date">{dateID(period.start_date)}</div><div className="text-xs text-muted-foreground">Hari setelah tutup buku terakhir</div></div>
              <label><div className="mk-eyebrow">Tanggal akhir</div>
                <Input type="date" className="mt-1" min={period.start_date} max={period.max_end_date} value={end} onChange={(e) => setEnd(e.target.value)} data-testid="closing-end-date-input" /></label>
            </div>
            <Button className="mt-6 mk-gradient text-white" disabled={busy || !end} onClick={() => run(1)} data-testid="closing-preview-button">{busy && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}Buat Pratinjau Payroll</Button>
          </>}
        </div>
      )}
      {step >= 1 && preview && (
        <div className="space-y-5 mk-fade">
          <div className="text-sm text-muted-foreground">Periode <b className="text-[#0B1F3A]">{dateID(preview.start_date)} – {dateID(preview.end_date)}</b></div>
          <Totals t={preview.totals} />
          {incomplete > 0 && <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800" data-testid="closing-incomplete-warning"><AlertTriangle className="h-4 w-4" />{incomplete} sesi belum Keluar dan tidak dibayar. Koreksi di menu Absensi sebelum tutup buku jika perlu.</div>}
          {step === 1 && (
            <div className="mk-card overflow-x-auto">
              <table className="w-full text-sm" data-testid="closing-preview-table">
                <thead className="bg-[#F4F7FB] text-left text-xs uppercase tracking-wider text-muted-foreground">
                  <tr><th className="px-3 py-3" /><th className="px-3 py-3">Karyawan</th><th className="px-3 py-3 text-right">Jam dibayar</th><th className="px-3 py-3 text-right">Lembur</th><th className="px-3 py-3 text-right">Gaji kotor</th><th className="px-3 py-3 text-right">Potongan lain</th><th className="px-3 py-3 text-right">Saldo kasbon</th><th className="px-3 py-3 text-right">Potongan kasbon</th><th className="px-3 py-3 text-right">Gaji bersih</th></tr>
                </thead>
                <tbody>{preview.lines.map((l) => (
                  <Fragment key={l.employee_id}>
                    <tr className="border-t" data-testid={`preview-row-${l.code}`}>
                      <td className="px-3 py-2"><button onClick={() => toggleLine(l)} aria-label="Rincian dan komponen gaji" data-testid={`preview-expand-${l.code}`}>{open[l.employee_id] ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}</button></td>
                      <td className="px-3 py-2"><div className="font-medium">{l.full_name}</div><div className="text-xs text-muted-foreground mk-num">{l.code} · {l.payroll_mode === "hourly" ? "Harian Jam" : "Manual"}</div></td>
                      <td className="px-3 py-2 text-right mk-num">{l.payroll_mode === "hourly" ? dur(l.durations.paid_minutes) : "—"}</td>
                      <td className="px-3 py-2 text-right mk-num">{dur(l.overtime_minutes)}</td>
                      <td className="px-3 py-2 text-right mk-num">{rupiah(l.gross)}</td>
                      <td className="px-3 py-2 text-right"><Input type="number" min="0" max={l.gross} className="h-8 w-32 ml-auto text-right" defaultValue={l.other_deduction} onChange={(e) => setA(l.employee_id, "other_deduction", e.target.value)} data-testid={`other-deduction-${l.code}`} /></td>
                      <td className="px-3 py-2 text-right mk-num">{rupiah(l.kasbon_balance)}</td>
                      <td className="px-3 py-2 text-right"><Input type="number" min="0" max={l.kasbon_cap} disabled={l.kasbon_cap === 0} className="h-8 w-32 ml-auto text-right" defaultValue={l.kasbon_deduction} onChange={(e) => setA(l.employee_id, "kasbon_deduction", e.target.value)} data-testid={`kasbon-deduction-${l.code}`} /><div className="text-[11px] text-muted-foreground">maks {rupiah(l.kasbon_cap)}</div></td>
                      <td className="px-3 py-2 text-right mk-num font-semibold text-[#0B1F3A]" data-testid={`net-final-${l.code}`}>{rupiah(l.net_final)}</td>
                    </tr>
                    {open[l.employee_id] && <tr><td colSpan={9} className="p-0"><PayrollBreakdown line={l} /><PeriodComponents line={l} value={adj[l.employee_id]?.components} onChange={(components) => setComponents(l.employee_id, components)} /></td></tr>}
                  </Fragment>
                ))}</tbody>
              </table>
              {preview.lines.length === 0 && <EmptyState title="Tidak ada karyawan pada periode ini" />}
            </div>
          )}
          {step === 1 && (
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" onClick={() => setStep(0)}>Kembali</Button>
              <Button variant="outline" disabled={busy} onClick={() => run(1)} data-testid="closing-recalculate-button"><RefreshCw className="h-4 w-4 mr-1" />Hitung Ulang</Button>
              <Button className="mk-gradient text-white" disabled={busy} onClick={() => run(2)} data-testid="closing-summary-button">{busy && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}Lanjut ke Ringkasan</Button>
            </div>
          )}
          {step === 2 && (
            <div className="mk-card p-6 max-w-2xl" data-testid="closing-confirm-step">
              <div className="flex items-center gap-2 font-bold text-[#0B1F3A]"><Lock className="h-5 w-5 text-[#174EA6]" /> Kunci periode {dateID(preview.start_date)} – {dateID(preview.end_date)}</div>
              <ul className="mt-3 text-sm text-muted-foreground space-y-1 list-disc pl-5">
                <li>Snapshot payroll {preview.totals.employees} karyawan disimpan dan tidak dapat diedit.</li>
                <li>Potongan kasbon {rupiah(preview.totals.kasbon_deduction)} dicatat sebagai transaksi.</li>
                <li>Absensi pada periode ini dikunci dari perubahan.</li>
              </ul>
              <label className="mt-5 flex items-start gap-2 text-sm"><Checkbox checked={agree} onCheckedChange={(v) => setAgree(!!v)} data-testid="closing-agree-checkbox" />Saya telah memeriksa seluruh rincian dan menyetujui finalisasi.</label>
              <div className="mt-5 flex gap-2">
                <Button variant="outline" disabled={busy} onClick={() => setStep(1)}>Kembali</Button>
                <Button className="mk-gradient text-white" disabled={!agree || busy} onClick={finalize} data-testid="closing-finalize-button">{busy ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <ShieldCheck className="h-4 w-4 mr-2" />}Kunci & Tutup Buku</Button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
