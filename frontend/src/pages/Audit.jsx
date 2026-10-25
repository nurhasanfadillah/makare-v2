import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { PageHeader, Loading, EmptyState, selectCls } from "@/components/app/common";
import { api, errMsg } from "@/lib/api";
import { dateTimeID } from "@/lib/format";

const ENTITIES = ["", "attendance", "overtime", "employee", "payroll_period", "cash_advance", "settings", "user", "department", "auth", "kiosk"];

const show = (v) => (v ? Object.entries(v).map(([k, x]) => `${k}: ${typeof x === "object" ? JSON.stringify(x) : x}`).join(" · ") : "—");

export default function Audit() {
  const [entity, setEntity] = useState("");
  const [q, setQ] = useState("");
  const [list, setList] = useState(null);
  useEffect(() => { api.get("/audit", { params: { entity, limit: 300 } }).then((r) => setList(r.data)).catch((e) => toast.error(errMsg(e))); }, [entity]);
  const rows = (list || []).filter((r) => `${r.actor} ${r.action}`.toLowerCase().includes(q.toLowerCase()));
  return (
    <div>
      <PageHeader eyebrow="Keamanan" title="Audit Log" subtitle="Pelaku, waktu, nilai sebelum/sesudah, dan hasil setiap tindakan penting." />
      <div className="mk-card">
        <div className="flex flex-col sm:flex-row gap-3 p-4 border-b">
          <Input placeholder="Cari pelaku atau aksi…" value={q} onChange={(e) => setQ(e.target.value)} className="max-w-xs" data-testid="audit-search-input" />
          <select className={`${selectCls} sm:w-52`} value={entity} onChange={(e) => setEntity(e.target.value)} data-testid="audit-entity-filter">
            {ENTITIES.map((x) => <option key={x} value={x}>{x || "Semua entitas"}</option>)}
          </select>
        </div>
        {!list ? <Loading /> : rows.length === 0 ? <EmptyState title="Belum ada catatan" /> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm" data-testid="audit-table">
              <thead className="bg-[#F4F7FB] text-left text-xs uppercase tracking-wider text-muted-foreground">
                <tr><th className="px-4 py-3">Waktu</th><th className="px-4 py-3">Pelaku</th><th className="px-4 py-3">Aksi</th><th className="px-4 py-3">Entitas</th><th className="px-4 py-3">Sebelum</th><th className="px-4 py-3">Sesudah</th><th className="px-4 py-3">Hasil</th></tr>
              </thead>
              <tbody>{rows.map((r) => (
                <tr key={r.id} className="border-t align-top">
                  <td className="px-4 py-2 whitespace-nowrap text-xs">{dateTimeID(r.created_at)}</td>
                  <td className="px-4 py-2 font-medium">{r.actor}</td>
                  <td className="px-4 py-2 mk-num text-xs">{r.action}</td>
                  <td className="px-4 py-2 text-xs">{r.entity}{r.entity_id ? ` #${r.entity_id}` : ""}</td>
                  <td className="px-4 py-2 text-xs text-muted-foreground max-w-[240px] break-words">{show(r.before)}</td>
                  <td className="px-4 py-2 text-xs text-muted-foreground max-w-[280px] break-words">{show(r.after)}</td>
                  <td className="px-4 py-2 text-xs"><span className={r.result === "success" ? "text-emerald-700" : "text-red-700"}>{r.result === "success" ? "Berhasil" : "Gagal"}</span></td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
