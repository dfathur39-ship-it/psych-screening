import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useScreening } from "../context/ScreeningContext";
import PublicHeader from "../components/PublicHeader";
import { Spinner } from "../components/Common";

/** Pages for someone who has filled in their data diri (Beranda, Profil, KTP, Hubungi kami).
 *  Without data diri the visitor is sent to fill it in and brought back afterwards. */
export default function MemberLayout() {
  const { participantId, profile, profileError, refreshProfile } = useScreening();
  const location = useLocation();

  if (!participantId) {
    return <Navigate to="/data-diri" replace state={{ from: location.pathname }} />;
  }

  return (
    <div className="lp">
      <PublicHeader />
      {profile ? (
        <Outlet />
      ) : (
        <main className="page-narrow">
          {profileError ? (
            <div className="empty-state">
              <p>{profileError}</p>
              <button className="btn btn-secondary" onClick={() => void refreshProfile()}>Coba lagi</button>
            </div>
          ) : (
            <Spinner label="Memuat profil..." />
          )}
        </main>
      )}
    </div>
  );
}
