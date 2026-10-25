import { useEffect, useState } from "react";
import { Plus, Trash2, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Field, selectCls } from "@/components/app/common";
import { api, errMsg } from "@/lib/api";
import { rupiah } from "@/lib/format";

const EMPTY = {
  full_name: "", gender: "L", address: "", birth_date: "", ktp: "", phone: "", department_id: "",
  join_date: new Date().toISOString().slice(0, 10), payroll_mode: "hourly", regular_rate: 0, overtime_rate: 0, components: [],
};

function Components({ list, onChange, mode }) {
  const set = (i, k, v) => onChange(list.map((c, j) => (j === i ? { ...c, [k]: v } : c)));
  const total = list.reduce((s, c) => s + Number(c.amount || 0) * Number(c.volume || 0), 0);
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="text-sm font-semibold">{mode === "manual" ? "Komponen gaji manual" : "Tambahan penghasilan"}</div>
        <Button type="button" variant="outline" size="sm" data-testid="add-component-button"
          onClick={() => onChange([...list, { name: "", amount: 0, volume: 1, note: "" }])}><Plus className="h-3.5 w-3.5 mr-1" />Komponen</Button>
      </div>
      {list.map((c, i) => (
        <div key={i} className="grid grid-cols-12 gap-2" data-testid={`component-row-${i}`}>
          <Input className="col-span-4" placeholder="Nama" value={c.name} onChange={(e) => set(i, "name", e.target.value)} data-testid={`component-name-${i}`} />
          <Input className="col-span-3" type="number" min="0" placeholder="Nominal" value={c.amount} onChange={(e) => set(i, "amount", e.target.value)} data-testid={`component-amount-${i}`} />
          <Input className="col-span-2" type="number" min="0" step="0.5" placeholder="Volume" value={c.volume} onChange={(e) => set(i, "volume", e.target.value)} data-testid={`component-volume-${i}`} />
          <Input className="col-span-2" placeholder="Ket." value={c.note || ""} onChange={(e) => set(i, "note", e.target.value)} />
          <Button type="button" variant="ghost" size="icon" className="col-span-1" onClick={() => onChange(list.filter((_, j) => j !== i))} aria-label="Hapus komponen"><Trash2 className="h-4 w-4 text-red-600" /></Button>
        </div>
      ))}
      {list.length > 0 && <div className="text-right text-sm">Total komponen: <span className="mk-num font-semibold">{rupiah(total)}</span></div>}
    </div>
  );
}

export default function EmployeeForm({ open, onClose, employeeId, departments, onSaved }) {
  const [f, setF] = useState(EMPTY);
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open) return;
    setF(EMPTY);
    setCode("");
    if (!employeeId) return;
    setLoading(true);
    api.get(`/employees/${employeeId}`).then(({ data }) => {
      setCode(data.code);
      setF({ ...EMPTY, ...Object.fromEntries(Object.keys(EMPTY).map((k) => [k, data[k] ?? EMPTY[k]])), department_id: data.department_id || "" });
    }).catch((e) => { toast.error(errMsg(e)); onClose(); }).finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, employeeId]);

  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const save = async (e) => {
    e.preventDefault();
    setBusy(true);
    const body = {
      ...f, department_id: f.department_id ? Number(f.department_id) : null, birth_date: f.birth_date || null,
      regular_rate: Number(f.regular_rate || 0), overtime_rate: Number(f.overtime_rate || 0),
      components: f.components.filter((c) => c.name.trim()).map((c) => ({ ...c, amount: Number(c.amount || 0), volume: Number(c.volume || 0) })),
    };
    try {
      if (employeeId) await api.put(`/employees/${employeeId}`, body);
      else await api.post("/employees", body);
      toast.success(employeeId ? "Data karyawan diperbarui" : "Karyawan ditambahkan");
      onSaved();
      onClose();
    } catch (ex) {
      toast.error(errMsg(ex));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto" data-testid="employee-form-dialog">
        <DialogHeader><DialogTitle>{employeeId ? `Edit Karyawan · ${code}` : "Tambah Karyawan"}</DialogTitle></DialogHeader>
        {loading ? <div className="flex items-center justify-center gap-2 py-20 text-muted-foreground" data-testid="employee-form-loading"><Loader2 className="h-5 w-5 animate-spin" />Memuat data karyawan…</div> : (
        <form onSubmit={save} className="space-y-6">
          <section className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="ID Karyawan" hint="Dibuat otomatis dan tidak dapat diubah">
              <Input value={code || "Otomatis"} disabled data-testid="employee-code-input" />
            </Field>
            <Field label="Nama lengkap" required><Input value={f.full_name} onChange={set("full_name")} required data-testid="employee-name-input" /></Field>
            <Field label="Jenis kelamin" required>
              <select className={selectCls} value={f.gender} onChange={set("gender")} data-testid="employee-gender-select">
                <option value="L">Laki-laki</option><option value="P">Perempuan</option>
              </select>
            </Field>
            <Field label="Tanggal lahir"><Input type="date" value={f.birth_date || ""} onChange={set("birth_date")} data-testid="employee-birthdate-input" /></Field>
            <Field label="No. KTP" hint="Opsional, 16 digit"><Input value={f.ktp || ""} onChange={set("ktp")} inputMode="numeric" maxLength={16} data-testid="employee-ktp-input" /></Field>
            <Field label="Kontak / No. HP"><Input value={f.phone || ""} onChange={set("phone")} data-testid="employee-phone-input" /></Field>
            <div className="sm:col-span-2"><Field label="Alamat"><Input value={f.address || ""} onChange={set("address")} data-testid="employee-address-input" /></Field></div>
          </section>
          <section className="grid grid-cols-1 sm:grid-cols-3 gap-4 border-t pt-5">
            <Field label="Departemen">
              <select className={selectCls} value={f.department_id} onChange={set("department_id")} data-testid="employee-department-select">
                <option value="">— Tanpa departemen —</option>
                {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
              </select>
            </Field>
            <Field label="Tanggal masuk" required><Input type="date" value={f.join_date} onChange={set("join_date")} required data-testid="employee-joindate-input" /></Field>
            <Field label="Mode payroll" required>
              <select className={selectCls} value={f.payroll_mode} onChange={set("payroll_mode")} data-testid="employee-mode-select">
                <option value="hourly">Harian Berbasis Jam</option><option value="manual">Manual</option>
              </select>
            </Field>
            {f.payroll_mode === "hourly" && <>
              <Field label="Tarif reguler / jam (Rp)"><Input type="number" min="0" value={f.regular_rate} onChange={set("regular_rate")} data-testid="employee-regular-rate-input" /></Field>
              <Field label="Tarif lembur / jam (Rp)"><Input type="number" min="0" value={f.overtime_rate} onChange={set("overtime_rate")} data-testid="employee-overtime-rate-input" /></Field>
            </>}
          </section>
          <section className="border-t pt-5">
            <Components list={f.components} mode={f.payroll_mode} onChange={(c) => setF({ ...f, components: c })} />
          </section>
          <p className="text-xs text-muted-foreground">Perubahan tarif hanya berlaku untuk periode yang belum tutup buku. Payroll final tetap memakai snapshot.</p>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>Batal</Button>
            <Button disabled={busy || loading} className="mk-gradient text-white" data-testid="employee-save-button">{busy && <Loader2 className="h-4 w-4 animate-spin mr-2" />}Simpan</Button>
          </DialogFooter>
        </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
