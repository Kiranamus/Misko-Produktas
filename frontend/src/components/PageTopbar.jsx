import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useLanguage } from "../context/LanguageContext";
import { translatePlaceName } from "../features/map/formatters";

export default function PageTopbar() {
  const navigate = useNavigate();
  const { isAuthenticated, hasActivePlan, purchasedPlans, getPurchasedCounty, logout } = useAuth();
  const { language, setLanguage, t } = useLanguage();

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
          <svg className="brand-tree-icon" viewBox="0 0 64 72" aria-hidden="true">
            <path d="M32 4 57 39H43l14 20H38v10H26V59H7l14-20H7L32 4Zm0 14L20 35h9L18 51h10v-9h8v9h10L35 35h9L32 18Z" />
            <path d="M32 18v51" />
          </svg>
          <div className="brand-text">
            <span className="brand-title">
              <span className="brand-title-forest">Forest</span>
              <span className="brand-title-foryou">ForYou</span>
            </span>
          </div>
        </NavLink>

        <nav className="topbar-nav">
          {isAuthenticated && hasActivePlan && (
            <NavLink
              to={getMapLink()}
              className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
            >
              {t("navMap")}
              {hasCountyPlan && purchasedCounty && ` (${translatePlaceName(purchasedCounty, language, "county")})`}
            </NavLink>
          )}

          {!isAuthenticated ? (
            <>
              <NavLink to="/register" className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>
                {t("register")}
              </NavLink>
              <NavLink to="/login" className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>
                {t("login")}
              </NavLink>
            </>
          ) : (
            <button
              type="button"
              onClick={handleLogout}
              className="nav-link nav-button"
            >
              {t("logout")}
            </button>
          )}

          <NavLink to="/" className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>
            {t("home")}
          </NavLink>

          <div className="language-selector" aria-label={t("languageSelector")}>
            <button
              type="button"
              className={`language-choice ${language === "lt" ? "active" : ""}`}
              onClick={() => setLanguage("lt")}
            >
              <span className="language-flag flag-lt" aria-hidden="true" />
              LT
            </button>
            <button
              type="button"
              className={`language-choice ${language === "en" ? "active" : ""}`}
              onClick={() => setLanguage("en")}
            >
              <span className="language-flag flag-gb" aria-hidden="true">
                <svg viewBox="0 0 60 36" focusable="false">
                  <rect width="60" height="36" fill="#012169" />
                  <path d="M0 0 60 36M60 0 0 36" stroke="#fff" strokeWidth="8" />
                  <path d="M0 0 60 36M60 0 0 36" stroke="#C8102E" strokeWidth="4" />
                  <path d="M30 0v36M0 18h60" stroke="#fff" strokeWidth="12" />
                  <path d="M30 0v36M0 18h60" stroke="#C8102E" strokeWidth="7" />
                </svg>
              </span>
              EN
            </button>
          </div>
        </nav>
      </div>
    </header>
  );
}
