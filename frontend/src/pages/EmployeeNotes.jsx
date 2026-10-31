import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, History, Plus, Save, X } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Field, Loading, EmptyState, PageHeader } from "@/components/app/common";

const todayWib = () => new Date(Date.now() + 7 * 60 * 60 * 1000).toISOString().slice(0, 10);
const emptyForm = () => ({ title: "", category: "Umum", note_date: todayWib(), body: "" });
const dateLabel = (value) => new Date(`${value.slice(0, 10)}T00:00:00+07:00`).toLocaleDateString("id-ID", { day: "numeric", month: "long", year: "numeric", timeZone: "Asia/Jakarta" });

export default function EmployeeNotes() {
  const { id } = useParams();
  const [employee, setEmployee] = useState(null);
  const [notes, setNotes] = useState(null);
  const [form, setForm] = useState(null);
  const [busy, setBusy] = useState(false);
  const [revisions, setRevisions] = useState({});
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const load = useCallback(async () => {
    setLoading(true); setLoadError("");
    try {
      const [employeeRes, noteRes] = await Promise.all([api.get(`/employees/${id}`), api.get(`/employees/${id}/notes`)]);
      setEmployee(employeeRes.data);
      setNotes(noteRes.data);
    } catch (e) { setEmployee(null); setNotes(null); setLoadError(errMsg(e)); }
    finally { setLoading(false); }
  }, [id]);
  useEffect(() => { load(); }, [load]);

  const save = async (event) => {
    event.preventDefault();
    setBusy(true);
    try {
      if (form.id) await api.put(`/employee-notes/${form.id}`, form);
      else await api.post(`/employees/${id}/notes`, form);
      toast.success(form.id ? "Catatan diperbarui; revisi sebelumnya tersimpan" : "Catatan ditambahkan");
      setForm(null); await load();
    } catch (e) { toast.error(errMsg(e)); }
    finally { setBusy(false); }
  };

  const toggleRevisions = async (noteId) => {
    if (revisions[noteId]) { setRevisions((v) => ({ ...v, [noteId]: null })); return; }
    try {
      const r = await api.get(`/employee-notes/${noteId}/revisions`);
      setRevisions((v) => ({ ...v, [noteId]: r.data }));
    } catch (e) { toast.error(errMsg(e)); }
  };

  if (loading) return <Loading />;
  if (loadError || !notes) return <div><PageHeader eyebrow="Riwayat karyawan" title="Catatan Karyawan" /><EmptyState title="Catatan karyawan gagal dimuat" hint={loadError || "Coba muat ulang data."} action={<Button onClick={load}>Coba lagi</Button>} /></div>;
  return <div>
    <Link to="/karyawan" className="inline-flex items-center gap-2 text-sm text-[#174EA6] mb-5"><ArrowLeft className="h-4 w-4" /> Kembali ke Data Karyawan</Link>
    <PageHeader eyebrow="Riwayat karyawan" title="Catatan Karyawan" subtitle={employee ? `${employee.code} · ${employee.full_name}` : "Catatan internal yang hanya dapat diakses Administrator."}
      actions={!form && <Button className="mk-gradient text-white" onClick={() => setForm({ ...emptyForm() })}><Plus className="h-4 w-4" /> Tambah Catatan</Button>} />

    {form && <form onSubmit={save} className="mk-card p-5 mb-5 space-y-4" data-testid="employee-note-form">
      <div className="flex items-center justify-between"><h2 className="font-semibold">{form.id ? "Ubah Catatan" : "Catatan Baru"}</h2><Button type="button" variant="ghost" size="icon" onClick={() => setForm(null)} aria-label="Tutup"><X /></Button></div>
      <div className="grid gap-4 sm:grid-cols-3">
        <Field label="Judul" required><Input required maxLength={120} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></Field>
        <Field label="Kategori" required><Input required maxLength={40} value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} placeholder="Umum, Kinerja, Disiplin…" /></Field>
        <Field label="Tanggal" required><Input type="date" required value={form.note_date} onChange={(e) => setForm({ ...form, note_date: e.target.value })} /></Field>
      </div>
      <Field label="Isi catatan" required><Textarea required maxLength={5000} rows={5} value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} /></Field>
      <div className="flex justify-end gap-2"><Button type="button" variant="outline" disabled={busy} onClick={() => setForm(null)}>Batal</Button><Button disabled={busy} className="mk-gradient text-white"><Save className="h-4 w-4" /> {busy ? "Menyimpan…" : "Simpan"}</Button></div>
    </form>}

    {notes.length === 0 ? <div className="mk-card"><EmptyState title="Belum ada catatan" hint="Catatan internal akan tampil di sini dan tidak dibagikan ke kiosk." /></div> : <div className="space-y-3">{notes.map((note) => <article className="mk-card p-5" key={note.id} data-testid={`employee-note-${note.id}`}>
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
        <div><div className="flex flex-wrap items-center gap-2"><h2 className="font-semibold text-[#0B1F3A]">{note.title}</h2><span className="rounded-full bg-blue-50 text-blue-700 px-2 py-0.5 text-xs">{note.category}</span></div><p className="text-xs text-muted-foreground mt-1">{dateLabel(note.note_date)} · dibuat {note.created_by} · {new Date(note.created_at).toLocaleString("id-ID", { timeZone: "Asia/Jakarta" })} WIB</p></div>
        <div className="flex gap-2 shrink-0"><Button size="sm" variant="outline" onClick={() => setForm({ id: note.id, title: note.title, category: note.category, note_date: note.note_date.slice(0, 10), body: note.body })}>Ubah</Button>{note.revision_count > 0 && <Button size="sm" variant="ghost" onClick={() => toggleRevisions(note.id)}><History className="h-4 w-4" /> Revisi ({note.revision_count})</Button>}</div>
      </div>
      <p className="mt-4 text-sm whitespace-pre-wrap break-words">{note.body}</p>
      {revisions[note.id] && <div className="mt-4 border-t pt-4 space-y-3">{revisions[note.id].map((rev) => <div key={rev.id} className="rounded-lg bg-slate-50 p-3"><div className="text-xs text-muted-foreground">{new Date(rev.changed_at).toLocaleString("id-ID", { timeZone: "Asia/Jakarta" })} WIB · {rev.changed_by}</div><div className="font-medium mt-1">{rev.title} <span className="text-xs font-normal">({rev.category}, {dateLabel(rev.note_date)})</span></div><p className="text-sm whitespace-pre-wrap mt-1">{rev.body}</p></div>)}</div>}
    </article>)}</div>}
  </div>;
}
