import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ToastProvider } from "./components/Common";
import { ScreeningProvider } from "./context/ScreeningContext";
import { AdminAuthProvider } from "./context/AdminAuthContext";

import Landing from "./pages/public/Landing";
import DataDiri from "./pages/public/DataDiri";
import Dashboard from "./pages/public/Dashboard";
import Profile from "./pages/public/Profile";
import KtpScan from "./pages/public/KtpScan";
import KtpConfirm from "./pages/public/KtpConfirm";
import Screening from "./pages/public/Screening";
import ResultPage from "./pages/public/ResultPage";
import Help from "./pages/public/Help";
import Contact from "./pages/public/Contact";

import AdminLogin from "./pages/admin/AdminLogin";
import AdminDashboard from "./pages/admin/Dashboard";
import Participants from "./pages/admin/Participants";
import Screenings from "./pages/admin/Screenings";
import Positions from "./pages/admin/Positions";
import Questions from "./pages/admin/Questions";
import Categories from "./pages/admin/Categories";
import AuditLogs from "./pages/admin/AuditLogs";
import Export from "./pages/admin/Export";
import Support from "./pages/admin/Support";
import Retake from "./pages/admin/Retake";
import AdminLayout, { RequireAdminAuth } from "./layouts/AdminLayout";
import MemberLayout from "./layouts/MemberLayout";
import AdminShortcut from "./components/AdminShortcut";
import HelpFab from "./components/HelpFab";

function App() {
  return (
    <ToastProvider>
      <AdminAuthProvider>
        <ScreeningProvider>
          <BrowserRouter>
            <AdminShortcut />
            <HelpFab />
            <Routes>
              {/* Public: landing, then data diri */}
              <Route path="/" element={<Landing />} />
              <Route path="/data-diri" element={<DataDiri />} />
              <Route path="/bantuan" element={<Help />} />

              {/* After data diri: home, profile (KTP confirmation) and contact. Sends visitors to data diri first. */}
              <Route element={<MemberLayout />}>
                <Route path="/beranda" element={<Dashboard />} />
                <Route path="/profil" element={<Profile />} />
                <Route path="/profil/ktp" element={<KtpScan />} />
                <Route path="/profil/ktp/konfirmasi" element={<KtpConfirm />} />
                <Route path="/kontak" element={<Contact />} />
              </Route>

              {/* Questions: only reachable from Beranda once the KTP is confirmed */}
              <Route path="/screening" element={<Screening />} />
              <Route path="/hasil" element={<ResultPage />} />

              {/* Admin */}
              <Route path="/admin/login" element={<AdminLogin />} />
              <Route element={<RequireAdminAuth />}>
                <Route element={<AdminLayout />}>
                  <Route path="/admin/dashboard" element={<AdminDashboard />} />
                  <Route path="/admin/participants" element={<Participants />} />
                  <Route path="/admin/screenings" element={<Screenings />} />
                  <Route path="/admin/support" element={<Support />} />
                  <Route path="/admin/retake-requests" element={<Retake />} />
                  <Route path="/admin/positions" element={<Positions />} />
                  <Route path="/admin/questions" element={<Questions />} />
                  <Route path="/admin/categories" element={<Categories />} />
                  <Route path="/admin/audit-logs" element={<AuditLogs />} />
                  <Route path="/admin/export" element={<Export />} />
                  <Route path="/admin" element={<Navigate to="/admin/dashboard" replace />} />
                </Route>
              </Route>

              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </BrowserRouter>
        </ScreeningProvider>
      </AdminAuthProvider>
    </ToastProvider>
  );
}

export default App;
