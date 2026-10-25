import { useEffect, useState } from "react";
import { api } from "./api";

const TZ = "Asia/Jakarta";

export const rupiah = (v) => "Rp " + Math.round(Number(v || 0)).toLocaleString("id-ID");

export const dur = (m) => {
  let x = Math.round(Number(m || 0));
  const s = x < 0 ? "-" : "";
  x = Math.abs(x);
  return `${s}${Math.floor(x / 60)}j ${String(x % 60).padStart(2, "0")}m`;
};

export const timeWIB = (iso) =>
  iso ? new Date(iso).toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit", timeZone: TZ }) : "—";

export const dateID = (iso, long = false) => {
  if (!iso) return "—";
  const d = new Date(iso.length === 10 ? `${iso}T00:00:00+07:00` : iso);
  return d.toLocaleDateString("id-ID", long ? { weekday: "long", day: "numeric", month: "long", year: "numeric", timeZone: TZ }
    : { day: "2-digit", month: "short", year: "numeric", timeZone: TZ });
};

export const dateTimeID = (iso) => (iso ? `${dateID(iso)} ${timeWIB(iso)}` : "—");

export const hmOf = (iso) =>
  iso ? new Date(iso).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", timeZone: TZ, hour12: false }) : "";

export const MODE_LABEL = { hourly: "Harian Berbasis Jam", manual: "Manual" };

export function useServerClock(path = "/time") {
  const [offset, setOffset] = useState(0);
  const [now, setNow] = useState(new Date());
  useEffect(() => {
    const sync = () => {
      const t0 = Date.now();
      api.get(path).then((r) => {
        const srv = new Date(r.data.now).getTime();
        setOffset(srv - (t0 + (Date.now() - t0) / 2));
      }).catch(() => {});
    };
    sync();
    const s = setInterval(sync, 60000);
    return () => clearInterval(s);
  }, [path]);
  useEffect(() => {
    const t = setInterval(() => setNow(new Date(Date.now() + offset)), 1000);
    return () => clearInterval(t);
  }, [offset]);
  return new Date(now.getTime());
}

export const clockText = (d) =>
  d.toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit", second: "2-digit", timeZone: TZ, hour12: false });
