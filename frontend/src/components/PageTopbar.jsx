import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function PageTopbar() {
  const navigate = useNavigate();
  const { isAuthenticated, hasActivePlan, logout } = useAuth();

  const handleLogout = () => {
    logout();
    navigate("/");
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
            <NavLink to="/map" className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>
              Žemėlapis
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