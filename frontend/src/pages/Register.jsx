import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { API } from "../api";
import "./Register.css";
import { useAuth } from "../context/AuthContext";

export default function Register() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const { isAuthenticated, logout } = useAuth();

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (password !== confirmPassword) {
      alert("Slaptažodžiai nesutampa");
      return;
    }
    try {
      await API.post("/register", {
        name: name,
        email: email,
        password: password
      });
      alert("Paskyra sukurta sėkmingai!");
      navigate("/login");
    } catch (err) {
      alert(err.response?.data?.detail || "Įvyko klaida");
    }
  };

  return (
    <div className="register-page">
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

      <main className="register-content">
        <div className="auth-card">
          <h1>Registracija</h1>
          <p>Sukurkite paskyrą ir pradėkite naudoti sistemą.</p>

          <form className="auth-form" onSubmit={handleSubmit}>
            <label className="auth-label">
              Vardas
              <input type="text" value={name} onChange={(e) => setName(e.target.value)} required placeholder="Vardas" />
            </label>
            <label className="auth-label">
              El. paštas
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required placeholder="įvestas@email.com" />
            </label>
            <label className="auth-label">
              Slaptažodis
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required placeholder="Slaptažodis" />
            </label>
            <label className="auth-label">
              Patvirtinkite slaptažodį
              <input type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} required placeholder="Pakartokite slaptažodį" />
            </label>

            <button type="submit" className="primary-btn">Kurti paskyrą</button>
          </form>

          <div className="auth-bottom">
            <p>Jau turite paskyrą?</p>
            <NavLink to="/login" className="secondary-btn">Prisijungti</NavLink>
          </div>
        </div>
      </main>
    </div>
  );
}
