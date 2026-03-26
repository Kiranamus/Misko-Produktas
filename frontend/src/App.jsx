import { Routes, Route, NavLink } from "react-router-dom";
import Home from "./pages/Home";
import MapPage from "./pages/MapPage";
import "./App.css";

export default function App() {
  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar-inner">
          <NavLink to="/" className="brand">
            <div className="brand-mark">F</div>
            <div className="brand-text">
              <span className="brand-title">ForestForYou</span>
              <span className="brand-subtitle">
                Miškininkystės analizė ir investavimas
              </span>
            </div>
          </NavLink>

          <nav className="topbar-nav">
            <NavLink
              to="/"
              className={({ isActive }) =>
                isActive ? "nav-link active" : "nav-link"
              }
            >
              Pagrindinis
            </NavLink>

            <NavLink
              to="/map"
              className={({ isActive }) =>
                isActive ? "nav-link active" : "nav-link"
              }
            >
              Žemėlapis
            </NavLink>
          </nav>
        </div>
      </header>

      <main className="app-main">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/map" element={<MapPage />} />
        </Routes>
      </main>
    </div>
  );
}