import { useCallback, useEffect, useState } from "react";
import { Plus, Trash2, Copy, RefreshCw, Save, Pencil, ExternalLink } from "lucide-react";
import { toast } from "sonner";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PageHeader, Loading, Field, StatusBadge, selectCls } from "@/components/app/common";
import { api, errMsg } from "@/lib/api";

const DAYS = [[1, "Sen"], [2, "Sel"], [3, "Rab"], [4, "Kam"], [5, "Jum"], [6, "Sab"], [7, "Min"]];
const Card = ({ title, children }) => <div className="mk-card p-6 space-y-4"><div className="font-bold text-[#0B1F3A]">{title}</div>{children}</div>;
const Toggle = ({ label, checked, onChange, testid, hint }) => (
  <div className="flex items-start justify-between gap-4"><div><div className="text-sm font-medium">{label}</div>{hint && <div className="text-xs text-muted-foreground">{hint}</div>}</div><Switch checked={!!checked} onCheckedChange={onChange} data-testid={testid} /></div>
);

function GeneralForm({ s, setS, save }) {
  const num = (k) => (e) => setS({ ...s, [k]: Number(e.target.value) });
  const txt = (k) => (e) => setS({ ...s, [k]: e.target.value });
  const setBreak = (i, k, v) => setS({ ...s, breaks: s.breaks.map((b, j) => (j === i ? { ...b, [k]: v } : b)) });
  return (
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
      <Card title="Identitas perusahaan & payroll">
        <Field label="Nama perusahaan" required><Input value={s.company_name} onChange={txt("company_name")} data-testid="settings-company-name" /></Field>
        <Field label="Alamat"><Input value={s.company_address} onChange={txt("company_address")} data-testid="settings-company-address" /></Field>
        <Field label="Tanggal mulai payroll pertama" hint={s.payroll_start_locked ? "Terkunci karena sudah ada tutup buku" : "Awal periode pertama sebelum ada tutup buku"}>
          <Input type="date" value={s.payroll_start_date} disabled={s.payroll_start_locked} onChange={txt("payroll_start_date")} data-testid="settings-payroll-start" />
        </Field>
      </Card>
      <Card title="Jadwal kerja global">
        <div>
          <div className="text-sm font-medium mb-2">Hari kerja</div>
          <div className="flex flex-wrap gap-2">{DAYS.map(([d, l]) => {
            const on = s.work_days.includes(d);
            return <button type="button" key={d} data-testid={`settings-day-${d}`} onClick={() => setS({ ...s, work_days: on ? s.work_days.filter((x) => x !== d) : [...s.work_days, d].sort() })}
              className={`h-9 w-12 rounded-lg border text-sm font-semibold transition-colors ${on ? "mk-gradient text-white border-transparent" : "bg-white text-muted-foreground"}`}>{l}</button>;
          })}</div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Jam masuk"><Input type="time" value={s.start_time} onChange={txt("start_time")} data-testid="settings-start-time" /></Field>
          <Field label="Jam pulang"><Input type="time" value={s.end_time} onChange={txt("end_time")} data-testid="settings-end-time" /></Field>
        </div>
        <div className="space-y-2">
          <div className="flex items-center justify-between"><span className="text-sm font-medium">Jadwal istirahat</span>
            <Button type="button" size="sm" variant="outline" onClick={() => setS({ ...s, breaks: [...s.breaks, { start: "15:00", end: "15:15" }] })} data-testid="settings-add-break"><Plus className="h-3.5 w-3.5" /></Button></div>
          {s.breaks.map((b, i) => (
            <div key={i} className="flex gap-2 items-center"><Input type="time" value={b.start} onChange={(e) => setBreak(i, "start", e.target.value)} data-testid={`settings-break-start-${i}`} /><span>–</span>
              <Input type="time" value={b.end} onChange={(e) => setBreak(i, "end", e.target.value)} data-testid={`settings-break-end-${i}`} />
              <Button type="button" variant="ghost" size="icon" onClick={() => setS({ ...s, breaks: s.breaks.filter((_, j) => j !== i) })} aria-label="Hapus"><Trash2 className="h-4 w-4 text-red-600" /></Button></div>
          ))}
        </div>
      </Card>
      <Card title="Keterlambatan & pembulatan">
        <div className="grid grid-cols-2 gap-3">
          <Field label="Toleransi terlambat (menit)"><Input type="number" min="0" value={s.late_tolerance_minutes} onChange={num("late_tolerance_minutes")} data-testid="settings-late-tolerance" /></Field>
          <Field label="Ambang pembulatan naik (menit)" hint="Sisa ≥ ambang dibulatkan naik"><Input type="number" min="1" max="60" value={s.rounding_threshold_minutes} onChange={num("rounding_threshold_minutes")} data-testid="settings-rounding" /></Field>
          <Field label="Batas jam reguler / hari (menit)"><Input type="number" min="60" value={s.max_regular_minutes} onChange={num("max_regular_minutes")} data-testid="settings-max-regular" /></Field>
        </div>
        <Toggle label="Aturan pengakuan jam pertama" hint="Terlambat melebihi toleransi → jam pertama tidak diakui" checked={s.first_hour_rule} onChange={(v) => setS({ ...s, first_hour_rule: v })} testid="settings-first-hour" />
      </Card>
      <Card title="Keluar lebih awal">
        <Toggle label="Wajib PIN Administrator" hint="PIN 6 digit, sekali pakai, terikat pada sesi" checked={s.early_leave_requires_pin} onChange={(v) => setS({ ...s, early_leave_requires_pin: v })} testid="settings-early-pin" />
        <Field label="Masa berlaku PIN (menit)"><Input type="number" min="1" max="120" value={s.early_pin_ttl_minutes} onChange={num("early_pin_ttl_minutes")} data-testid="settings-early-pin-ttl" /></Field>
      </Card>
      <Card title="Lembur">
        <Toggle label="Aktifkan lembur" hint="Jika nonaktif, server menolak transaksi lembur baru" checked={s.overtime_enabled} onChange={(v) => setS({ ...s, overtime_enabled: v })} testid="settings-overtime-enabled" />
        <div className="grid grid-cols-2 gap-3">
          <Field label="Potongan istirahat lembur (menit)"><Input type="number" min="0" value={s.overtime_break_minutes} onChange={num("overtime_break_minutes")} data-testid="settings-ot-break" /></Field>
          <Field label="Berlaku jika lembur ≥ (menit)"><Input type="number" min="0" value={s.overtime_break_after_minutes} onChange={num("overtime_break_after_minutes")} data-testid="settings-ot-break-after" /></Field>
        </div>
      </Card>
      <div className="xl:col-span-2 flex justify-end"><Button className="mk-gradient text-white" onClick={save} data-testid="settings-save-button"><Save className="h-4 w-4 mr-1" />Simpan Pengaturan</Button></div>
    </div>
  );
}

function KioskTab({ s, setS, save, reload }) {
  const [pin, setPin] = useState("");
  const link = `${window.location.origin}/kiosk/${s.kiosk_token}`;
  const rotate = async () => {
    if (!window.confirm("Rotasi tautan? Tautan lama langsung tidak berlaku.")) return;
    try { await api.post("/settings/kiosk-rotate"); toast.success("Tautan kiosk dirotasi"); reload(); } catch (e) { toast.error(errMsg(e)); }
  };
  const savePin = async () => {
    try { await api.post("/settings/overtime-pin", { pin }); setPin(""); toast.success("PIN lembur kiosk diperbarui"); } catch (e) { toast.error(errMsg(e)); }
  };
  return (
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
      <Card title="Tautan kiosk publik">
        <Toggle label="Kiosk aktif" checked={s.kiosk_enabled} onChange={(v) => setS({ ...s, kiosk_enabled: v })} testid="settings-kiosk-enabled" />
        <div className="flex gap-2"><Input readOnly value={link} className="mk-num text-xs" data-testid="settings-kiosk-link" />
          <Button variant="outline" size="icon" onClick={() => { navigator.clipboard.writeText(link); toast.success("Tautan disalin"); }} aria-label="Salin" data-testid="settings-kiosk-copy"><Copy className="h-4 w-4" /></Button>
          <Button variant="outline" size="icon" onClick={() => window.open(link, "_blank")} aria-label="Buka" data-testid="settings-kiosk-open"><ExternalLink className="h-4 w-4" /></Button></div>
        <div className="flex flex-wrap gap-2"><Button variant="outline" onClick={rotate} data-testid="settings-kiosk-rotate"><RefreshCw className="h-4 w-4 mr-1" />Rotasi Token</Button>
          <Button className="mk-gradient text-white" onClick={save} data-testid="settings-kiosk-save">Simpan Status</Button></div>
      </Card>
      <Card title="PIN mode lembur kiosk">
        <p className="text-sm text-muted-foreground">Dimasukkan sekali saat membuka mode Lembur di tab kiosk. Tidak membuka akses panel admin.</p>
        <div className="flex gap-2"><Input inputMode="numeric" maxLength={6} placeholder="PIN baru 6 digit" value={pin} onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))} data-testid="settings-ot-pin-input" />
          <Button disabled={pin.length !== 6} onClick={savePin} data-testid="settings-ot-pin-save">Simpan PIN</Button></div>
      </Card>
    </div>
  );
}

function Departments() {
  const [list, setList] = useState([]);
  const [name, setName] = useState("");
  const load = useCallback(() => { api.get("/departments").then((r) => setList(r.data)); }, []);
  useEffect(() => { load(); }, [load]);
  const act = async (fn, msg) => { try { await fn(); toast.success(msg); load(); } catch (e) { toast.error(errMsg(e)); } };
  return (
    <Card title="Departemen">
      <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); act(() => api.post("/departments", { name }), "Departemen ditambahkan").then(() => setName("")); }}>
        <Input placeholder="Nama departemen baru" value={name} onChange={(e) => setName(e.target.value)} required data-testid="department-name-input" />
        <Button data-testid="department-add-button"><Plus className="h-4 w-4 mr-1" />Tambah</Button>
      </form>
      <ul className="divide-y">{list.map((d) => (
        <li key={d.id} className="flex items-center justify-between py-2.5" data-testid={`department-row-${d.id}`}>
          <span className="font-medium">{d.name} <span className="text-xs text-muted-foreground">· {d.employees} karyawan</span></span>
          <span>
            <Button variant="ghost" size="sm" onClick={() => { const n = window.prompt("Nama baru", d.name); if (n) act(() => api.put(`/departments/${d.id}`, { name: n }), "Departemen diubah"); }} data-testid={`department-edit-${d.id}`}><Pencil className="h-4 w-4" /></Button>
            <Button variant="ghost" size="sm" onClick={() => window.confirm(`Hapus ${d.name}?`) && act(() => api.delete(`/departments/${d.id}`), "Departemen dihapus")} data-testid={`department-delete-${d.id}`}><Trash2 className="h-4 w-4 text-red-600" /></Button>
          </span>
        </li>
      ))}</ul>
    </Card>
  );
}

function Users() {
  const [list, setList] = useState([]);
  const [f, setF] = useState({ username: "", full_name: "", role: "operator", password: "" });
  const load = useCallback(() => { api.get("/users").then((r) => setList(r.data)); }, []);
  useEffect(() => { load(); }, [load]);
  const act = async (fn, msg) => { try { await fn(); toast.success(msg); load(); return true; } catch (e) { toast.error(errMsg(e)); return false; } };
  const create = async (e) => {
    e.preventDefault();
    if (await act(() => api.post("/users", f), "Akun dibuat")) setF({ username: "", full_name: "", role: "operator", password: "" });
  };
  return (
    <Card title="Akun & peran">
      <form onSubmit={create} className="grid grid-cols-1 md:grid-cols-5 gap-2">
        <Input placeholder="username" value={f.username} onChange={(e) => setF({ ...f, username: e.target.value.toLowerCase() })} required data-testid="user-username-input" />
        <Input placeholder="Nama lengkap" value={f.full_name} onChange={(e) => setF({ ...f, full_name: e.target.value })} required data-testid="user-fullname-input" />
        <select className={selectCls} value={f.role} onChange={(e) => setF({ ...f, role: e.target.value })} data-testid="user-role-select"><option value="operator">Operator Input</option><option value="admin">Administrator</option></select>
        <Input type="password" placeholder="Kata sandi (min. 8)" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} required minLength={8} data-testid="user-password-input" />
        <Button data-testid="user-create-button"><Plus className="h-4 w-4 mr-1" />Buat Akun</Button>
      </form>
      <table className="w-full text-sm">
        <thead className="text-left text-xs uppercase text-muted-foreground"><tr><th className="py-2">Username</th><th>Nama</th><th>Peran</th><th>Status</th><th className="text-right">Aksi</th></tr></thead>
        <tbody>{list.map((u) => (
          <tr key={u.id} className="border-t" data-testid={`user-row-${u.username}`}>
            <td className="py-2 mk-num">{u.username}</td><td>{u.full_name}</td><td>{u.role === "admin" ? "Administrator" : "Operator Input"}</td>
            <td><StatusBadge status={u.active ? "active" : "inactive"} /></td>
            <td className="text-right whitespace-nowrap">
              <Button variant="ghost" size="sm" onClick={() => { const p = window.prompt("Kata sandi baru (min. 8 karakter)"); if (p) act(() => api.patch(`/users/${u.id}`, { password: p }), "Kata sandi direset"); }} data-testid={`user-reset-${u.username}`}>Reset sandi</Button>
              <Button variant="ghost" size="sm" onClick={() => act(() => api.patch(`/users/${u.id}`, { active: !u.active }), "Status akun diubah")} data-testid={`user-toggle-${u.username}`}>{u.active ? "Nonaktifkan" : "Aktifkan"}</Button>
            </td>
          </tr>
        ))}</tbody>
      </table>
    </Card>
  );
}

export default function SettingsPage() {
  const [s, setS] = useState(null);
  const load = useCallback(() => { api.get("/settings").then((r) => setS(r.data)).catch((e) => toast.error(errMsg(e))); }, []);
  useEffect(() => { load(); }, [load]);
  const save = async () => {
    const { kiosk_token, has_overtime_pin, payroll_start_locked, ...body } = s;
    try { await api.put("/settings", body); toast.success("Pengaturan disimpan dan tercatat di audit log"); load(); } catch (e) { toast.error(errMsg(e)); }
  };
  if (!s) return <Loading />;
  return (
    <div>
      <PageHeader eyebrow="Konfigurasi" title="Pengaturan" subtitle="Perubahan tidak memengaruhi payroll yang sudah tutup buku." />
      <Tabs defaultValue="umum">
        <TabsList className="bg-white border mb-5 flex-wrap h-auto">
          <TabsTrigger value="umum" data-testid="settings-tab-general">Umum & Jadwal</TabsTrigger>
          <TabsTrigger value="kiosk" data-testid="settings-tab-kiosk">Kiosk & PIN</TabsTrigger>
          <TabsTrigger value="dept" data-testid="settings-tab-departments">Departemen</TabsTrigger>
          <TabsTrigger value="users" data-testid="settings-tab-users">Akun</TabsTrigger>
        </TabsList>
        <TabsContent value="umum"><GeneralForm s={s} setS={setS} save={save} /></TabsContent>
        <TabsContent value="kiosk"><KioskTab s={s} setS={setS} save={save} reload={load} /></TabsContent>
        <TabsContent value="dept"><Departments /></TabsContent>
        <TabsContent value="users"><Users /></TabsContent>
      </Tabs>
    </div>
  );
}
