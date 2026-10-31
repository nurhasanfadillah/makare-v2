import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import AppShell from "@/components/app/AppShell";
import { Loading } from "@/components/app/common";
import Login from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";
import Employees from "@/pages/Employees";
import EmployeeDetail from "@/pages/EmployeeDetail";
import Attendance from "@/pages/Attendance";
import Kasbon from "@/pages/Kasbon";
import Closing from "@/pages/Closing";
import Periods from "@/pages/Periods";
import PeriodDetail from "@/pages/PeriodDetail";
import SettingsPage from "@/pages/Settings";
import Audit from "@/pages/Audit";
import Kiosk from "@/pages/Kiosk";
import EmployeeNotes from "@/pages/EmployeeNotes";
import ManualPayroll from "@/pages/ManualPayroll";
import AttendanceReport from "@/pages/AttendanceReport";

function Protected({ admin, children }) {
  const { user, ready } = useAuth();
  if (!ready) return <Loading />;
  if (!user) return <Navigate to="/login" replace />;
  if (admin && user.role !== "admin") return <Navigate to="/absensi" replace />;
  return children;
}

const A = (el) => <Protected admin>{el}</Protected>;

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Toaster richColors position="top-right" />
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/kiosk/:token" element={<Kiosk />} />
          <Route element={<Protected><AppShell /></Protected>}>
            <Route index element={<Dashboard />} />
            <Route path="absensi" element={<Attendance />} />
            <Route path="laporan-absensi" element={A(<AttendanceReport />)} />
            <Route path="karyawan" element={A(<Employees />)} />
            <Route path="karyawan/:id" element={A(<EmployeeDetail />)} />
            <Route path="karyawan/:id/catatan" element={A(<EmployeeNotes />)} />
            <Route path="kasbon" element={A(<Kasbon />)} />
            <Route path="gaji-manual" element={A(<ManualPayroll />)} />
            <Route path="tutup-buku" element={A(<Closing />)} />
            <Route path="riwayat" element={A(<Periods />)} />
            <Route path="riwayat/:id" element={A(<PeriodDetail />)} />
            <Route path="pengaturan" element={A(<SettingsPage />)} />
            <Route path="audit" element={A(<Audit />)} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
