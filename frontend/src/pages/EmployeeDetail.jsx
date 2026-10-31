import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Pencil, NotebookPen } from "lucide-react";
import { Button } from "@/components/ui/button";
import { StatusBadge, Loading, EmptyState, PageHeader } from "@/components/app/common";
import EmployeeForm from "./EmployeeForm";
import { api, errMsg } from "@/lib/api";
import { dateID, dateTimeID, MODE_LABEL, rupiah } from "@/lib/format";

const FIELD_LABELS = {
  full_name: "Nama lengkap",
  gender: "Jenis kelamin",
  address: "Alamat",
  birth_date: "Tanggal lahir",
  ktp: "Nomor KTP",
  phone: "Nomor telepon",
  department_id: "Departemen",
  join_date: "Tanggal masuk",
  payroll_mode: "Mode payroll",
  regular_rate: "Tarif reguler",
  overtime_rate: "Tarif lembur",
  components: "Komponen penghasilan",
  active: "Status aktif",
  code: "ID karyawan",
};

const ACTION_LABELS = {
  employee_created: "Data karyawan dibuat",
  employee_updated: "Data karyawan diperbarui",
  employee_activated: "Karyawan diaktifkan",
  employee_deactivated: "Karyawan dinonaktifkan",
};

function DetailItem({ label, children }) {
  return <div className="min-w-0"><dt className="text-xs text-muted-foreground">{label}</dt><dd className="mt-1 break-words text-sm font-medium">{children || "—"}</dd></div>;
}

export default function EmployeeDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [employee, setEmployee] = useState(null);
  const [departments, setDepartments] = useState([]);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [historyError, setHistoryError] = useState("");
  const [editOpen, setEditOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    setHistoryError("");
    try {
      const [employeeResponse, departmentResponse] = await Promise.all([
        api.get(`/employees/${id}`),
        api.get("/departments"),
      ]);
      setEmployee(employeeResponse.data);
      setDepartments(departmentResponse.data);
      try {
        setHistory((await api.get(`/employees/${id}/history`)).data);
      } catch (e) {
        setHistory([]);
        setHistoryError(errMsg(e));
      }
    } catch (e) {
      setEmployee(null);
      setError(errMsg(e));
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  if (loading) return <Loading text="Memuat detail karyawan…" />;
  if (error || !employee) return <div><PageHeader eyebrow="Master data" title="Detail Karyawan" /><EmptyState title="Detail karyawan gagal dimuat" hint={error || "Karyawan tidak ditemukan."} action={<Button onClick={load}>Coba lagi</Button>} /></div>;

  const department = departments.find((item) => item.id === employee.department_id)?.name || employee.department || "—";
  return <div>
    <Button type="button" variant="ghost" className="mb-3 -ml-3" onClick={() => navigate("/karyawan")}><ArrowLeft className="mr-2 h-4 w-4" />Kembali ke Data Karyawan</Button>
    <PageHeader eyebrow={`Master data · ${employee.code}`} title={employee.full_name}
      subtitle={`${MODE_LABEL[employee.payroll_mode] || employee.payroll_mode} · ${department}`}
      actions={<>
        <Button type="button" variant="outline" onClick={() => navigate(`/karyawan/${id}/catatan`)}><NotebookPen className="mr-2 h-4 w-4" />Catatan</Button>
        <Button type="button" className="mk-gradient text-white" onClick={() => setEditOpen(true)}><Pencil className="mr-2 h-4 w-4" />Ubah Data</Button>
      </>} />

    <div className="mb-5 flex flex-wrap items-center gap-3 rounded-xl border bg-white px-4 py-3">
      <StatusBadge status={employee.active ? "active" : "inactive"} />
      <span className="text-sm text-muted-foreground">ID karyawan <span className="font-semibold text-foreground">{employee.code}</span></span>
      <span className="text-sm text-muted-foreground">Masuk {dateID(employee.join_date)}</span>
    </div>

    <div className="grid gap-5 xl:grid-cols-2">
      <section className="mk-card p-5" aria-labelledby="employee-personal-heading">
        <h2 id="employee-personal-heading" className="mb-4 font-bold text-[#0B1F3A]">Data pribadi</h2>
        <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <DetailItem label="Nama lengkap">{employee.full_name}</DetailItem>
          <DetailItem label="Jenis kelamin">{employee.gender === "L" ? "Laki-laki" : employee.gender === "P" ? "Perempuan" : "—"}</DetailItem>
          <DetailItem label="Tanggal lahir">{employee.birth_date ? dateID(employee.birth_date) : "—"}</DetailItem>
          <DetailItem label="Nomor KTP">{employee.ktp}</DetailItem>
          <DetailItem label="Nomor telepon">{employee.phone}</DetailItem>
          <DetailItem label="Alamat">{employee.address}</DetailItem>
        </dl>
      </section>

      <section className="mk-card p-5" aria-labelledby="employee-work-heading">
        <h2 id="employee-work-heading" className="mb-4 font-bold text-[#0B1F3A]">Pekerjaan dan payroll</h2>
        <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <DetailItem label="Departemen">{department}</DetailItem>
          <DetailItem label="Tanggal masuk">{dateID(employee.join_date)}</DetailItem>
          <DetailItem label="Mode payroll">{MODE_LABEL[employee.payroll_mode] || employee.payroll_mode}</DetailItem>
          {employee.payroll_mode === "hourly" && <>
            <DetailItem label="Tarif reguler per jam">{rupiah(employee.regular_rate)}</DetailItem>
            <DetailItem label="Tarif lembur per jam">{rupiah(employee.overtime_rate)}</DetailItem>
          </>}
          <DetailItem label="Saldo kasbon">{rupiah(employee.kasbon_balance)}</DetailItem>
        </dl>
        {employee.payroll_mode === "manual" && <div className="mt-5 border-t pt-4">
          <h3 className="mb-3 text-sm font-semibold">Komponen gaji</h3>
          {employee.components?.length ? <ul className="space-y-2">{employee.components.map((component, index) => <li key={`${component.name}-${index}`} className="flex flex-wrap justify-between gap-x-4 gap-y-1 text-sm">
            <span>{component.name}{component.note ? <span className="text-muted-foreground"> · {component.note}</span> : null}</span>
            <span className="mk-num">{rupiah(Number(component.amount) * Number(component.volume))}</span>
          </li>)}</ul> : <p className="text-sm text-muted-foreground">Belum ada komponen gaji.</p>}
        </div>}
      </section>

      <section className="mk-card p-5 xl:col-span-2" aria-labelledby="employee-history-heading">
        <h2 id="employee-history-heading" className="mb-4 font-bold text-[#0B1F3A]">Riwayat perubahan</h2>
        {historyError ? <div role="alert" className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">Riwayat perubahan gagal dimuat: {historyError} <Button variant="link" onClick={load}>Coba lagi</Button></div>
          : history.length === 0 ? <p className="text-sm text-muted-foreground">Belum ada riwayat perubahan.</p>
            : <ol className="space-y-4">{history.map((event) => <li key={event.id} className="border-l-2 border-blue-200 pl-4" data-testid={`employee-history-${event.id}`}>
              <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                <span className="text-sm font-semibold">{ACTION_LABELS[event.action] || event.action}</span>
                <time className="text-xs text-muted-foreground" dateTime={event.created_at}>{dateTimeID(event.created_at)} WIB</time>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">Oleh {event.actor}{event.changed_fields?.length ? ` · Field: ${event.changed_fields.map((field) => FIELD_LABELS[field] || field).join(", ")}` : ""}</p>
            </li>)}</ol>}
      </section>
    </div>

    <EmployeeForm open={editOpen} employeeId={employee.id} departments={departments} onClose={() => setEditOpen(false)} onSaved={load} />
  </div>;
}
