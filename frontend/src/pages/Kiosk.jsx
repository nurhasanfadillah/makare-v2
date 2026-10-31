import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { Search, LogIn, LogOut, Moon, Sun, CheckCircle2, XCircle, Loader2, Lock, X } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { useServerClock, clockText, timeWIB } from "@/lib/format";

const OT_KEY = "makare_kiosk_ot";

function Modal({ children, testid, onClose }) {
  const dialogRef = useRef(null);
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return undefined;
    const previous = document.activeElement;
    const focusable = () => [...dialog.querySelectorAll('button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])')];
    (focusable()[0] || dialog).focus();
    const handleKeyDown = (event) => {
      if (event.key === "Escape" && onClose) { event.preventDefault(); onClose(); return; }
      if (event.key !== "Tab") return;
      const items = focusable();
      if (!items.length) { event.preventDefault(); dialog.focus(); return; }
      const first = items[0];
      const last = items[items.length - 1];
      if (event.shiftKey && (document.activeElement === first || !dialog.contains(document.activeElement))) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && (document.activeElement === last || !dialog.contains(document.activeElement))) { event.preventDefault(); first.focus(); }
    };
    dialog.addEventListener("keydown", handleKeyDown);
    return () => { dialog.removeEventListener("keydown", handleKeyDown); if (previous?.isConnected) previous.focus(); };
  }, [onClose]);
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#0B1F3A]/80 backdrop-blur-sm p-4" data-testid={testid}>
      <div ref={dialogRef} role="dialog" aria-modal="true" aria-labelledby={`${testid}-title`} tabIndex={-1} className="w-full max-w-md rounded-3xl bg-white text-[#172A46] p-8 shadow-2xl mk-fade">{children}</div>
    </div>
  );
}

function PinPad({ title, hint, onSubmit, onCancel, busy, error, testid }) {
  const [pin, setPin] = useState("");
  const press = (k) => setPin((p) => (k === "del" ? p.slice(0, -1) : p.length < 6 ? p + k : p));
  return (
    <Modal testid={testid} onClose={onCancel}>
      <h2 id={`${testid}-title`} className="text-xl font-bold text-[#0B1F3A]">{title}</h2>
      <p className="text-sm text-muted-foreground mt-1">{hint}</p>
      <div className="my-5 flex justify-center gap-2" data-testid={`${testid}-dots`}>{[0, 1, 2, 3, 4, 5].map((i) => <span key={i} className={`h-4 w-4 rounded-full ${i < pin.length ? "bg-[#174EA6]" : "bg-slate-200"}`} />)}</div>
      {error && <div className="mb-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm px-3 py-2 text-center" role="alert">{error}</div>}
      <div className="grid grid-cols-3 gap-3">
        {["1", "2", "3", "4", "5", "6", "7", "8", "9", "del", "0", "ok"].map((k) => (
          <button key={k} disabled={busy || (k === "ok" && pin.length !== 6)} aria-label={k === "del" ? "Hapus satu digit" : k === "ok" ? "Konfirmasi PIN" : `Digit ${k}`} data-testid={`${testid}-key-${k}`}
            onClick={() => (k === "ok" ? onSubmit(pin) : press(k))}
            className={`h-16 rounded-2xl text-xl font-bold transition-transform active:scale-95 disabled:opacity-40 ${k === "ok" ? "mk-gradient text-white" : "bg-[#F4F7FB] text-[#0B1F3A]"}`}>
            {k === "del" ? "⌫" : k === "ok" ? (busy ? <Loader2 className="h-5 w-5 animate-spin mx-auto" /> : "OK") : k}
          </button>
        ))}
      </div>
      <button onClick={onCancel} className="mt-4 w-full py-3 text-sm font-semibold text-muted-foreground" data-testid={`${testid}-cancel`}>Batal</button>
    </Modal>
  );
}

export default function Kiosk() {
  const { token } = useParams();
  const now = useServerClock("/time");
  const [info, setInfo] = useState(null);
  const [fatal, setFatal] = useState("");
  const [mode, setMode] = useState("regular");
  const otStorageKey = `${OT_KEY}:${token}`;
  const [otToken, setOtToken] = useState(() => sessionStorage.getItem(`${OT_KEY}:${token}`));
  const [q, setQ] = useState("");
  const [results, setResults] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState("");
  const [searchRetry, setSearchRetry] = useState(0);
  const [emp, setEmp] = useState(null);
  const [state, setState] = useState(null);
  const [confirm, setConfirm] = useState(false);
  const [pinFor, setPinFor] = useState(null);
  const [busy, setBusy] = useState(false);
  const [pinErr, setPinErr] = useState("");
  const [result, setResult] = useState(null);
  const timer = useRef(null);
  const searchSequence = useRef(0);
  const base = `/kiosk/${token}`;

  useEffect(() => { api.get(base).then((r) => setInfo(r.data)).catch((e) => setFatal(errMsg(e))); }, [base]);
  useEffect(() => () => clearTimeout(timer.current), []);

  useEffect(() => {
    const query = q.trim();
    const sequence = ++searchSequence.current;
    if (!query) { setResults([]); setSearchLoading(false); setSearchError(""); return; }
    setSearchLoading(true);
    setSearchError("");
    const t = setTimeout(() => api.get(`${base}/employees`, { params: { q: query } })
      .then((r) => { if (sequence === searchSequence.current) setResults(r.data); })
      .catch((e) => { if (sequence === searchSequence.current) { setResults([]); setSearchError(errMsg(e)); } })
      .finally(() => { if (sequence === searchSequence.current) setSearchLoading(false); }), 250);
    return () => { clearTimeout(t); if (sequence === searchSequence.current) searchSequence.current += 1; };
  }, [q, base, searchRetry]);

  const reset = useCallback(() => {
    clearTimeout(timer.current);
    setQ(""); setResults([]); setEmp(null); setState(null); setConfirm(false); setPinFor(null); setPinErr(""); setResult(null);
  }, []);

  const pick = async (e) => {
    setEmp(e);
    setState(null);
    try { setState((await api.get(`${base}/employees/${e.id}/state`)).data); } catch (ex) { setResult({ ok: false, msg: errMsg(ex) }); }
  };

  const action = !state ? null : mode === "overtime" ? (state.overtime === "open" ? "out" : "in") : state.regular === "open" ? "out" : state.regular === "none" ? "in" : null;

  const showResult = (r) => {
    setConfirm(false); setPinFor(null); setResult(r);
    clearTimeout(timer.current);
    timer.current = setTimeout(reset, 4500);
  };

  const submit = async (early_pin) => {
    setBusy(true);
    setPinErr("");
    try {
      const r = await api.post(`${base}/clock`, { employee_id: emp.id, mode, action, ot_token: mode === "overtime" ? otToken : undefined, early_pin });
      showResult({ ok: true, msg: `${action === "in" ? "Masuk" : "Keluar"}${mode === "overtime" ? " lembur" : ""} tercatat pukul ${timeWIB(r.data.time)} WIB`, name: emp.full_name });
    } catch (e) {
      const st = e.response?.status;
      if (st === 428) { setConfirm(false); setPinFor("early"); }
      else if (early_pin && st === 403) setPinErr(errMsg(e));
      else if (mode === "overtime" && (st === 401 || (st === 403 && errMsg(e).includes("terkunci")))) {
        sessionStorage.removeItem(otStorageKey);
        setOtToken(null);
        setMode("regular");
        showResult({ ok: false, msg: "Mode lembur terkunci kembali. Masukkan PIN lembur lagi.", name: emp.full_name });
      }
      else showResult({ ok: false, msg: errMsg(e), name: emp.full_name });
    } finally { setBusy(false); }
  };

  const unlockOt = async (pin) => {
    setBusy(true);
    setPinErr("");
    try {
      const r = await api.post(`${base}/overtime-unlock`, { pin });
      sessionStorage.setItem(otStorageKey, r.data.ot_token);
      setOtToken(r.data.ot_token);
      setMode("overtime");
      setPinFor(null);
      reset();
    } catch (e) { setPinErr(errMsg(e)); } finally { setBusy(false); }
  };

  const switchMode = (m) => {
    if (m === "overtime" && !otToken) { setPinErr(""); setPinFor("ot"); return; }
    setMode(m);
    reset();
  };

  if (fatal) return (
    <div className="min-h-screen bg-[#0B1F3A] text-white flex flex-col items-center justify-center p-8 text-center" data-testid="kiosk-unavailable">
      <Lock className="h-12 w-12 text-[#4F7DF3] mb-4" /><div className="text-2xl font-bold">Kiosk tidak tersedia</div><p className="text-white/60 mt-2">{fatal}</p>
    </div>
  );
  if (!info) return <div className="min-h-screen bg-[#0B1F3A] flex items-center justify-center"><Loader2 className="h-8 w-8 text-white animate-spin" /></div>;

  return (
    <div className="min-h-screen bg-[#0B1F3A] text-white flex flex-col select-none" data-testid="kiosk-page">
      <header className="mk-gradient mk-hero-grid px-6 sm:px-10 py-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div><div className="text-xs uppercase tracking-[0.2em] text-white/70">Absensi Kiosk</div><div className="text-2xl font-extrabold tracking-tight" data-testid="kiosk-company">{info.company_name}</div></div>
        <div className="text-left md:text-right">
          <div className="mk-num text-5xl sm:text-6xl font-semibold leading-none" data-testid="kiosk-clock">{clockText(now)}</div>
          <div className="text-sm text-white/80 mt-1">{now.toLocaleDateString("id-ID", { weekday: "long", day: "numeric", month: "long", year: "numeric", timeZone: "Asia/Jakarta" })} · WIB (server)</div>
        </div>
      </header>

      <main className="flex-1 w-full max-w-4xl mx-auto px-5 sm:px-8 py-8">
        {info.overtime_enabled && (
          <div className="mx-auto mb-8 grid grid-cols-2 gap-2 rounded-2xl bg-white/5 border border-white/10 p-1.5 max-w-md" role="group" aria-label="Mode absensi">
            {[["regular", "Reguler", Sun], ["overtime", "Lembur", Moon]].map(([m, l, I]) => (
              <button key={m} type="button" aria-pressed={mode === m} onClick={() => switchMode(m)} data-testid={`kiosk-mode-${m}`}
                className={`h-14 rounded-xl text-lg font-bold flex items-center justify-center gap-2 transition-colors ${mode === m ? "mk-gradient text-white shadow-lg" : "text-white/60 hover:text-white"}`}>
                <I className="h-5 w-5" />{l}{m === "overtime" && !otToken && <Lock className="h-4 w-4" />}
              </button>
            ))}
          </div>
        )}

        {!emp ? (
          <div className="mk-fade">
            <div className="relative">
              <Search className="absolute left-5 top-1/2 -translate-y-1/2 h-6 w-6 text-white/50" />
              <input autoFocus value={q} onChange={(e) => setQ(e.target.value)} placeholder="Ketik nama atau ID karyawan" aria-label="Cari karyawan berdasarkan nama atau ID" aria-describedby="kiosk-search-status" data-testid="kiosk-search-input"
                className="w-full h-20 rounded-2xl bg-white/10 border border-white/15 pl-14 pr-5 text-2xl placeholder:text-white/40 focus:outline-none focus:ring-2 focus:ring-[#4F7DF3]" />
            </div>
            <div id="kiosk-search-status" className="mt-4 min-h-6 text-center text-sm text-white/70" role={searchError ? "alert" : "status"} aria-live={searchError ? "assertive" : "polite"}>
              {searchLoading ? "Mencari karyawan…" : searchError ? <span>{searchError} <button type="button" className="underline font-semibold" onClick={() => setSearchRetry((n) => n + 1)}>Coba lagi</button></span> : null}
            </div>
            <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 gap-3">
              {results.map((r) => (
                <button key={r.id} onClick={() => pick(r)} data-testid={`kiosk-employee-${r.code}`}
                  className="text-left rounded-2xl bg-white/5 border border-white/10 hover:bg-white/10 active:scale-[0.98] transition-transform p-5 min-h-[84px]">
                  <div className="text-xl font-bold">{r.full_name}</div><div className="text-sm text-white/60 mk-num">{r.code} · {r.department || "—"}</div>
                </button>
              ))}
            </div>
            {q.trim() && !searchLoading && !searchError && results.length === 0 && <p className="mt-2 text-center text-white/50" data-testid="kiosk-no-results">Karyawan tidak ditemukan</p>}
          </div>
        ) : (
          <div className="rounded-3xl bg-white/5 border border-white/10 p-8 text-center mk-fade" data-testid="kiosk-selected-employee">
            <div className="text-sm text-white/60 mk-num">{emp.code}</div>
            <div className="text-3xl font-extrabold mt-1">{emp.full_name}</div>
            <div className="text-white/60">{emp.department || ""} · Mode {mode === "overtime" ? "Lembur" : "Reguler"}</div>
            {!state ? <Loader2 className="h-8 w-8 animate-spin mx-auto mt-8" /> : action ? (
              <button onClick={() => setConfirm(true)} data-testid={`kiosk-action-${action}`}
                className={`mt-8 w-full h-28 rounded-3xl text-3xl font-extrabold flex items-center justify-center gap-3 active:scale-[0.98] transition-transform shadow-2xl ${action === "in" ? "bg-emerald-500 hover:bg-emerald-600" : "bg-red-500 hover:bg-red-600"}`}>
                {action === "in" ? <LogIn className="h-9 w-9" /> : <LogOut className="h-9 w-9" />}{action === "in" ? "MASUK" : "KELUAR"}
              </button>
            ) : (
              <div className="mt-8 rounded-2xl bg-white/10 p-5 text-lg" data-testid="kiosk-no-action">
                {state.regular === "done" ? "Absensi reguler hari ini sudah selesai." : `Status hari ini: ${state.regular.replace("status_", "")}. Hubungi Administrator.`}
              </div>
            )}
            <button onClick={reset} className="mt-5 inline-flex items-center gap-2 h-14 px-8 rounded-2xl border border-white/20 text-lg font-semibold text-white/80" data-testid="kiosk-cancel-button"><X className="h-5 w-5" />Batal</button>
          </div>
        )}
      </main>

      {confirm && (
        <Modal testid="kiosk-confirm-dialog" onClose={() => setConfirm(false)}>
          <h2 id="kiosk-confirm-dialog-title" className="text-sm text-muted-foreground">Konfirmasi transaksi</h2>
          <div className="text-2xl font-extrabold text-[#0B1F3A] mt-1">{emp.full_name}</div>
          <div className="mt-3 text-lg">{action === "in" ? "Masuk" : "Keluar"} {mode === "overtime" ? "Lembur" : "Reguler"} · <span className="mk-num font-semibold">{clockText(now)}</span> WIB</div>
          <div className="mt-6 grid grid-cols-2 gap-3">
            <button onClick={() => setConfirm(false)} className="h-16 rounded-2xl bg-[#F4F7FB] text-lg font-bold" data-testid="kiosk-confirm-cancel">Batal</button>
            <button disabled={busy} onClick={() => submit()} className="h-16 rounded-2xl mk-gradient text-white text-lg font-bold flex items-center justify-center" data-testid="kiosk-confirm-submit">{busy ? <Loader2 className="h-6 w-6 animate-spin" /> : "Ya, Simpan"}</button>
          </div>
        </Modal>
      )}
      {pinFor === "early" && <PinPad testid="kiosk-early-pin" title="PIN Keluar Lebih Awal" hint="Jadwal kerja belum selesai. Minta PIN sekali pakai dari Administrator." busy={busy} error={pinErr} onSubmit={submit} onCancel={reset} />}
      {pinFor === "ot" && <PinPad testid="kiosk-ot-pin" title="Buka Mode Lembur" hint="Masukkan PIN lembur dari Administrator. Hanya diminta sekali di tab ini." busy={busy} error={pinErr} onSubmit={unlockOt} onCancel={() => setPinFor(null)} />}
      {result && (
        <Modal testid="kiosk-result" onClose={reset}>
          <div className="text-center">
            {result.ok ? <CheckCircle2 className="h-20 w-20 text-emerald-500 mx-auto" /> : <XCircle className="h-20 w-20 text-red-500 mx-auto" />}
            <h2 id="kiosk-result-title" className="text-2xl font-extrabold mt-3 text-[#0B1F3A]" data-testid="kiosk-result-title">{result.ok ? "Berhasil" : "Gagal"}</h2>
            {result.name && <div className="font-semibold mt-1">{result.name}</div>}
            <p className="text-muted-foreground mt-2" data-testid="kiosk-result-message">{result.msg}</p>
            <button onClick={reset} className="mt-6 w-full h-14 rounded-2xl mk-gradient text-white font-bold" data-testid="kiosk-result-close">Selesai</button>
          </div>
        </Modal>
      )}
    </div>
  );
}
