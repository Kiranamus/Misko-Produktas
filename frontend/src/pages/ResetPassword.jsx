import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { API } from "../api";
import "./ResetPassword.css";
import { useAuth } from "../context/AuthContext";

export default function ResetPassword() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const { isAuthenticated, logout } = useAuth();

  const handleSubmit = async (event) => {
    event.preventDefault();
    try {
      const res = await API.post("/forgot-password", { username: email });
      const resetLink = `${window.location.origin}/reset-password-confirm?token=${res.data.token}`;
      
      window.open(resetLink, '_blank');
      
      alert("Slaptažodžio atkūrimo nuoroda atidaryta naujame skirtuke!");
      navigate("/login");
    } catch (err) {
      alert(err.response?.data?.detail || "Įvyko klaida");
    }
  };

  return (
    <div className="reset-page">
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
            {isAuthenticated && (
              <NavLink to="/map" className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>Žemėlapis</NavLink>
            )}

            {!isAuthenticated ? (
              <>
                <NavLink to="/register" className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>Registruotis</NavLink>
                <NavLink to="/login" className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>Prisijungti</NavLink>
              </>
            ) : (
              <button onClick={logout} className="logout-btn" style={{ background: 'none', border: 'none', color: '#fff', cursor: 'pointer', fontSize: '16px' }}>
                Atsijungti
              </button>
            )}
            <NavLink to="/" className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>Pagrindinis</NavLink>
          </nav>
        </div>
      </header>

      <div className="reset-content">
        <div className="reset-card">
          <h1>Slaptažodžio atstatymas</h1>
          <p>Įveskite el. paštą, kad atsiųstume atkūrimo nuorodą.</p>

          <form className="reset-form" onSubmit={handleSubmit}>
            <label className="reset-label">
              El. paštas
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                placeholder="įvestas@email.com"
              />
            </label>

            <button type="submit" className="primary-btn" style={{ width: "100%" }}>
              Siųsti nuorodą
            </button>
          </form>

          <div className="reset-actions">
            <NavLink to="/login" className="secondary-btn" style={{ width: "100%" }}>
              Grįžti prisijungti
            </NavLink>
          </div>
        </div>
      </div>
    </div>
  );
}