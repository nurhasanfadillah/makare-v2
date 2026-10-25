import { useState } from "react";
import { useNavigate, Navigate } from "react-router-dom";
import { ShieldCheck, Loader2, LockKeyhole, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/context/AuthContext";
import { errMsg } from "@/lib/api";

export default function Login() {
  const { login, user } = useAuth();
  const nav = useNavigate();
  const [form, setForm] = useState({ username: "", password: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  if (user) return <Navigate to={user.role === "admin" ? "/" : "/absensi"} replace />;

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const u = await login(form.username.trim().toLowerCase(), form.password);
      nav(u.role === "admin" ? "/" : "/absensi");
    } catch (ex) {
      setError(errMsg(ex));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-[1.1fr_1fr]">
      <div className="hidden lg:flex flex-col justify-between mk-gradient mk-hero-grid text-white p-12 relative overflow-hidden">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-white/15 backdrop-blur flex items-center justify-center font-extrabold">M</div>
          <span className="font-extrabold tracking-tight text-lg">MAKARE</span>
        </div>
        <div className="max-w-lg">
          <div className="text-xs uppercase tracking-[0.2em] text-white/70 mb-4">Manajemen Karyawan Redone</div>
          <h1 className="text-4xl xl:text-5xl font-extrabold tracking-tight leading-[1.1]">Absensi, jam kerja, dan penggajian yang dapat diaudit.</h1>
          <p className="mt-5 text-white/80 leading-relaxed">Setiap transaksi memakai waktu server WIB, setiap tutup buku tersimpan sebagai snapshot final yang tidak dapat diubah diam-diam.</p>
        </div>
        <div className="flex items-center gap-2 text-sm text-white/75"><ShieldCheck className="h-4 w-4" /> Akses dibatasi berdasarkan peran</div>
        <div className="absolute -right-24 -bottom-24 h-80 w-80 rounded-full border border-white/15" aria-hidden />
        <div className="absolute -right-10 -bottom-10 h-52 w-52 rounded-full border border-white/20" aria-hidden />
      </div>
      <div className="flex items-center justify-center p-6 sm:p-12">
        <form onSubmit={submit} className="w-full max-w-sm mk-fade" data-testid="login-form">
          <div className="lg:hidden mb-8 flex items-center gap-2">
            <div className="h-9 w-9 rounded-xl mk-gradient text-white flex items-center justify-center font-extrabold">M</div>
            <span className="font-extrabold text-[#0B1F3A]">MAKARE</span>
          </div>
          <div className="mk-eyebrow mb-2">Masuk ke panel</div>
          <h2 className="text-3xl font-bold tracking-tight text-[#0B1F3A]">Selamat datang</h2>
          <p className="text-sm text-muted-foreground mt-2 mb-8">Gunakan akun Administrator atau Operator Input Anda.</p>
          <div className="space-y-4">
            <div className="relative">
              <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input data-testid="login-username-input" className="h-12 pl-10 bg-white" placeholder="Username" autoComplete="username"
                value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} required />
            </div>
            <div className="relative">
              <LockKeyhole className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input data-testid="login-password-input" type="password" className="h-12 pl-10 bg-white" placeholder="Kata sandi" autoComplete="current-password"
                value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required />
            </div>
            {error && <div role="alert" data-testid="login-error" className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
            <Button data-testid="login-submit-button" disabled={busy} className="h-12 w-full mk-gradient text-white font-semibold hover:opacity-95 transition-opacity">
              {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Masuk"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
