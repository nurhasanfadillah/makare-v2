import { useState, useEffect } from "react";
import { Loader2 } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Field, selectCls } from "@/components/app/common";
import { hmOf, timeWIB, dateID } from "@/lib/format";

export function EntryDialog({ open, onClose, onSubmit, title, description, initial, historical, correction, busy }) {
  const [f, setF] = useState({});
  useEffect(() => { if (open) setF(initial || {}); }, [open, initial]);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const showTimes = f.status === "hadir" && (historical || correction);
  const statuses = historical || correction ? ["hadir", "sakit", "izin", "alfa"] : ["sakit", "izin", "alfa"];
  const needReason = historical || correction;
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent data-testid="attendance-entry-dialog">
        <DialogHeader><DialogTitle>{title}</DialogTitle>{description && <DialogDescription>{description}</DialogDescription>}</DialogHeader>
        <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); onSubmit(f); }}>
          <Field label="Status" required>
            <select className={selectCls} value={f.status || ""} onChange={set("status")} required data-testid="entry-status-select">
              <option value="" disabled>Pilih status</option>
              {statuses.map((s) => <option key={s} value={s}>{s[0].toUpperCase() + s.slice(1)}</option>)}
            </select>
          </Field>
          {showTimes && (
            <div className="grid grid-cols-2 gap-3">
              <Field label="Jam Masuk" required><Input type="time" value={f.check_in || ""} onChange={set("check_in")} required data-testid="entry-checkin-input" /></Field>
              <Field label="Jam Keluar"><Input type="time" value={f.check_out || ""} onChange={set("check_out")} data-testid="entry-checkout-input" /></Field>
              <label className="col-span-2 flex items-center gap-2 text-sm">
                <Checkbox checked={!!f.check_out_next_day} onCheckedChange={(v) => setF({ ...f, check_out_next_day: !!v })} data-testid="entry-nextday-checkbox" />
                Keluar pada hari berikutnya (shift lintas tengah malam)
              </label>
            </div>
          )}
          <Field label="Catatan"><Input value={f.note || ""} onChange={set("note")} data-testid="entry-note-input" /></Field>
          {needReason && <Field label="Alasan koreksi / input historis" required><Input value={f.reason || ""} onChange={set("reason")} required minLength={3} data-testid="entry-reason-input" /></Field>}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>Batal</Button>
            <Button disabled={busy} className="mk-gradient text-white" data-testid="entry-submit-button">{busy && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}Simpan</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export function correctionInitial(a) {
  return { status: a.status, check_in: hmOf(a.check_in), check_out: hmOf(a.check_out), note: a.note || "",
    check_out_next_day: !!(a.check_out && dateID(a.check_out) !== dateID(a.work_date)) };
}

export function PinInputDialog({ open, onClose, onSubmit, busy, name }) {
  const [pin, setPin] = useState("");
  useEffect(() => { if (open) setPin(""); }, [open]);
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent data-testid="early-pin-input-dialog">
        <DialogHeader>
          <DialogTitle>PIN Keluar Lebih Awal</DialogTitle>
          <DialogDescription>{name} keluar sebelum jadwal selesai. Masukkan PIN 6 digit dari Administrator.</DialogDescription>
        </DialogHeader>
        <Input autoFocus inputMode="numeric" maxLength={6} className="h-14 text-center text-2xl tracking-[0.5em] mk-num" value={pin}
          onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))} data-testid="early-pin-input" />
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Batal</Button>
          <Button disabled={busy || pin.length !== 6} onClick={() => onSubmit(pin)} className="mk-gradient text-white" data-testid="early-pin-submit">Konfirmasi Keluar</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function PinShowDialog({ data, onClose }) {
  return (
    <Dialog open={!!data} onOpenChange={(o) => !o && onClose()}>
      <DialogContent data-testid="early-pin-show-dialog">
        <DialogHeader>
          <DialogTitle>PIN Keluar Lebih Awal</DialogTitle>
          <DialogDescription>Berikan PIN ini kepada {data?.name}. Hanya berlaku sekali untuk sesi ini.</DialogDescription>
        </DialogHeader>
        <div className="rounded-xl mk-gradient text-white text-center py-6">
          <div className="text-4xl font-bold tracking-[0.4em] mk-num" data-testid="early-pin-value">{data?.pin}</div>
          <div className="text-sm text-white/80 mt-2">Berlaku sampai {timeWIB(data?.expires_at)} WIB</div>
        </div>
        <DialogFooter><Button onClick={onClose} data-testid="early-pin-close">Tutup</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
