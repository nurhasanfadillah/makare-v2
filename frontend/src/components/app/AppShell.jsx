import { useEffect, useRef, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { LayoutDashboard, Users, CalendarCheck, Wallet, BookLock, History, Settings, ScrollText, LogOut, Menu, X, WalletCards, FileBarChart2 } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useServerClock, clockText } from "@/lib/format";
import { toast } from "sonner";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, roles: ["admin", "operator"], end: true },
  { to: "/absensi", label: "Absensi", icon: CalendarCheck, roles: ["admin", "operator"] },
  { to: "/laporan-absensi", label: "Laporan Absensi", icon: FileBarChart2, roles: ["admin"] },
  { to: "/karyawan", label: "Data Karyawan", icon: Users, roles: ["admin"] },
  { to: "/kasbon", label: "Kasbon", icon: Wallet, roles: ["admin"] },
  { to: "/gaji-manual", label: "Gaji Manual", icon: WalletCards, roles: ["admin"] },
  { to: "/tutup-buku", label: "Tutup Buku", icon: BookLock, roles: ["admin"] },
  { to: "/riwayat", label: "Riwayat Tutup Buku", icon: History, roles: ["admin"] },
  { to: "/pengaturan", label: "Pengaturan", icon: Settings, roles: ["admin"] },
  { to: "/audit", label: "Audit Log", icon: ScrollText, roles: ["admin"] },
];

function Sidebar({ onNavigate }) {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  return (
    <aside className="flex h-full w-64 flex-col bg-[#0B1F3A] text-white">
      <div className="px-6 py-6">
        <div className="flex items-center gap-2.5">
          <div className="h-9 w-9 rounded-xl mk-gradient flex items-center justify-center font-extrabold">M</div>
          <div>
            <div className="font-extrabold tracking-tight leading-none" data-testid="brand-name">MAKARE</div>
            <div className="text-[11px] text-white/55 mt-1">Manajemen Karyawan Redone</div>
          </div>
        </div>
      </div>
      <nav aria-label="Navigasi utama" className="flex-1 px-3 space-y-1">
        {NAV.filter((n) => n.roles.includes(user?.role)).map((n) => (
          <NavLink key={n.to} to={n.to} end={n.end} onClick={onNavigate} data-testid={`nav-${n.to.replace("/", "") || "dashboard"}`}
            className={({ isActive }) => `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors duration-150 ${isActive ? "mk-gradient text-white shadow-lg shadow-blue-900/30" : "text-white/70 hover:bg-white/5 hover:text-white"}`}>
            <n.icon className="h-4.5 w-4.5" /> {n.label}
          </NavLink>
        ))}
      </nav>
      <div className="m-3 rounded-xl bg-white/5 p-3">
        <div className="text-sm font-semibold truncate" data-testid="current-user-name">{user?.full_name}</div>
        <div className="text-xs text-white/55">{user?.role === "admin" ? "Administrator" : "Operator Input"}</div>
        <button data-testid="logout-button" onClick={async () => {
          const revoked = await logout();
          nav("/login");
          if (!revoked) toast.error("Keluar lokal berhasil, tetapi server belum mengonfirmasi pencabutan sesi.");
        }}
          className="mt-3 flex w-full items-center justify-center gap-2 rounded-lg border border-white/15 py-2 text-xs font-semibold text-white/80 hover:bg-white/10 transition-colors">
          <LogOut className="h-3.5 w-3.5" /> Keluar Akun
        </button>
      </div>
    </aside>
  );
}

export default function AppShell() {
  const [open, setOpen] = useState(false);
  const menuRef = useRef(null);
  const menuTriggerRef = useRef(null);
  const wasOpen = useRef(false);
  const now = useServerClock();
  useEffect(() => {
    if (!open) {
      if (wasOpen.current) menuTriggerRef.current?.focus();
      wasOpen.current = false;
      return;
    }

    wasOpen.current = true;
    const getFocusable = () => menuRef.current?.querySelectorAll(
      'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
    ) || [];
    getFocusable()[0]?.focus();
    const onKeyDown = (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        setOpen(false);
        return;
      }
      if (event.key !== "Tab") return;
      const focusable = getFocusable();
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open]);
  return (
    <div className="flex min-h-screen">
      <a href="#main-content" className="sr-only z-[60] rounded-md bg-white px-4 py-3 text-[#0B1F3A] focus:not-sr-only focus:fixed focus:left-4 focus:top-4">
        Lewati ke konten utama
      </a>
      <div className="hidden lg:block sticky top-0 h-screen"><Sidebar /></div>
      {open && (
        <div id="mobile-navigation" ref={menuRef} role="dialog" aria-modal="true" aria-label="Navigasi utama" className="fixed inset-0 z-50 flex lg:hidden">
          <Sidebar onNavigate={() => setOpen(false)} />
          <button aria-label="Tutup menu" className="flex-1 bg-black/40" onClick={() => setOpen(false)} data-testid="mobile-menu-close" />
        </div>
      )}
      <div className="flex-1 min-w-0">
        <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b bg-white/85 backdrop-blur-xl px-4 sm:px-8">
          <button ref={menuTriggerRef} className="lg:hidden p-2 -ml-2" onClick={() => setOpen((value) => !value)} data-testid="mobile-menu-button" aria-label="Menu" aria-expanded={open} aria-controls="mobile-navigation">
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
          <div className="text-sm text-muted-foreground hidden sm:block">
            {now.toLocaleDateString("id-ID", { weekday: "long", day: "numeric", month: "long", year: "numeric", timeZone: "Asia/Jakarta" })}
          </div>
          <div className="flex items-center gap-2 rounded-full border bg-white px-3 py-1 text-sm" data-testid="header-server-clock">
            <span className="h-2 w-2 rounded-full bg-emerald-500" aria-hidden />
            <span className="mk-num font-semibold text-[#0B1F3A]">{clockText(now)}</span>
            <span className="text-xs text-muted-foreground">WIB · server</span>
          </div>
        </header>
        <main id="main-content" tabIndex={-1} className="px-4 sm:px-8 py-6 sm:py-8 max-w-[1600px] mx-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
