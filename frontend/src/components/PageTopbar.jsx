import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function PageTopbar() {
  const navigate = useNavigate();
  const { isAuthenticated, hasActivePlan, purchasedPlans, user, getPurchasedCounty, logout } = useAuth();

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  const purchasedCounty = getPurchasedCounty();
  const hasCountyPlan = purchasedPlans.includes("county_day");

  const getMapLink = () => {
    if (hasCountyPlan && purchasedCounty) {
      return `/map?county=${encodeURIComponent(purchasedCounty)}`;
    }
    return "/map";
  };

  return (
    <header className="topbar">
      <div className="topbar-inner">
        <NavLink to="/" className="brand">
          <div className="brand-mark">F</div>
          <div className="brand-text">
            <span className="brand-title">ForestForYou</span>
            <span className="brand-subtitle">Miškininkystės analizė ir investavimas</span>
          </div>
        </NavLink>

        <nav className="topbar-nav">
          {isAuthenticated && hasActivePlan && (
            <NavLink
              to={getMapLink()}
              className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
            >
              Žemėlapis
              {hasCountyPlan && purchasedCounty && ` (${purchasedCounty})`}
            </NavLink>
          )}

          {!isAuthenticated ? (
            <>
              <NavLink to="/register" className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>
                Registruotis
              </NavLink>
              <NavLink to="/login" className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>
                Prisijungti
              </NavLink>
            </>
          ) : (
            <button
              type="button"
              onClick={handleLogout}
              className="nav-link"
              style={{ background: "none", border: "none", cursor: "pointer" }}
            >
              Atsijungti
            </button>
          )}

          <NavLink to="/" className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>
            Pagrindinis
          </NavLink>
        </nav>
      </div>
    </header>
  );
}