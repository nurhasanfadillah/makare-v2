import { useCallback, useEffect, useState } from "react";
import { Plus, Search, Pencil, Power } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PageHeader, StatusBadge, Loading, EmptyState, selectCls } from "@/components/app/common";
import { api, errMsg } from "@/lib/api";
import { rupiah, dateID, MODE_LABEL } from "@/lib/format";
import EmployeeForm from "./EmployeeForm";

export default function Employees() {
  const [list, setList] = useState(null);
  const [deps, setDeps] = useState([]);
  const [filter, setFilter] = useState({ q: "", status: "all", mode: "all", department_id: "" });
  const [form, setForm] = useState({ open: false, id: null });

  const load = useCallback(() => {
    const params = { ...filter, department_id: filter.department_id || undefined };
    api.get("/employees", { params }).then((r) => setList(r.data)).catch((e) => toast.error(errMsg(e)));
  }, [filter]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { api.get("/departments").then((r) => setDeps(r.data)); }, []);

  const toggle = async (e) => {
    if (!window.confirm(`${e.active ? "Nonaktifkan" : "Aktifkan"} ${e.full_name}?`)) return;
    try {
      await api.post(`/employees/${e.id}/status`, { active: !e.active });
      toast.success(e.active ? "Karyawan dinonaktifkan" : "Karyawan diaktifkan");
      load();
    } catch (ex) { toast.error(errMsg(ex)); }
  };

  const fset = (k) => (e) => setFilter({ ...filter, [k]: e.target.value });

  return (
    <div>
      <PageHeader eyebrow="Master data" title="Data Karyawan" subtitle="ID karyawan dibuat otomatis, unik, dan tidak berubah."
        actions={<Button className="mk-gradient text-white" onClick={() => setForm({ open: true, id: null })} data-testid="add-employee-button"><Plus className="h-4 w-4 mr-1" /> Tambah Karyawan</Button>} />
      <div className="mk-card">
        <div className="flex flex-col md:flex-row gap-3 p-4 border-b">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input className="pl-9" placeholder="Cari nama atau ID…" value={filter.q} onChange={fset("q")} data-testid="employee-search-input" />
          </div>
          <select className={`${selectCls} md:w-40`} value={filter.status} onChange={fset("status")} data-testid="employee-status-filter">
            <option value="all">Semua status</option><option value="active">Aktif</option><option value="inactive">Nonaktif</option>
          </select>
          <select className={`${selectCls} md:w-48`} value={filter.mode} onChange={fset("mode")} data-testid="employee-mode-filter">
            <option value="all">Semua mode</option><option value="hourly">Harian Berbasis Jam</option><option value="manual">Manual</option>
          </select>
          <select className={`${selectCls} md:w-44`} value={filter.department_id} onChange={fset("department_id")} data-testid="employee-department-filter">
            <option value="">Semua departemen</option>{deps.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select>
        </div>
        {!list ? <Loading /> : list.length === 0 ? <EmptyState title="Belum ada karyawan" hint="Tambahkan karyawan pertama untuk mulai mencatat absensi." /> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm" data-testid="employees-table">
              <thead className="bg-[#F4F7FB] text-left text-xs uppercase tracking-wider text-muted-foreground">
                <tr><th className="px-4 py-3">ID</th><th className="px-4 py-3">Nama</th><th className="px-4 py-3">Departemen</th><th className="px-4 py-3">Mode Payroll</th><th className="px-4 py-3 text-right">Tarif / jam</th><th className="px-4 py-3">Masuk</th><th className="px-4 py-3">Status</th><th className="px-4 py-3 text-right">Aksi</th></tr>
              </thead>
              <tbody>
                {list.map((e) => (
                  <tr key={e.id} className="border-t hover:bg-[#F4F7FB]/60 transition-colors" data-testid={`employee-row-${e.code}`}>
                    <td className="px-4 py-3 mk-num font-semibold text-[#174EA6]">{e.code}</td>
                    <td className="px-4 py-3 font-medium">{e.full_name}</td>
                    <td className="px-4 py-3">{e.department || "—"}</td>
                    <td className="px-4 py-3">{MODE_LABEL[e.payroll_mode]}</td>
                    <td className="px-4 py-3 text-right mk-num">{e.payroll_mode === "hourly" ? rupiah(e.regular_rate) : "—"}</td>
                    <td className="px-4 py-3">{dateID(e.join_date)}</td>
                    <td className="px-4 py-3"><StatusBadge status={e.active ? "active" : "inactive"} /></td>
                    <td className="px-4 py-3 text-right whitespace-nowrap">
                      <Button variant="ghost" size="sm" onClick={() => setForm({ open: true, id: e.id })} data-testid={`edit-employee-${e.code}`}><Pencil className="h-4 w-4" /></Button>
                      <Button variant="ghost" size="sm" onClick={() => toggle(e)} data-testid={`toggle-employee-${e.code}`} title={e.active ? "Nonaktifkan" : "Aktifkan"}>
                        <Power className={`h-4 w-4 ${e.active ? "text-red-600" : "text-emerald-600"}`} />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      <EmployeeForm open={form.open} employeeId={form.id} departments={deps} onClose={() => setForm({ open: false, id: null })} onSaved={load} />
    </div>
  );
}
