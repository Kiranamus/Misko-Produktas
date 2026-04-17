import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { API } from "../api";
import { useAuth } from "../context/AuthContext";
import "./Login.css";

export default function Login() {
    const navigate = useNavigate();
    const { login } = useAuth();
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const { isAuthenticated, logout } = useAuth();

    const handleSubmit = async (event) => {
        event.preventDefault();
        try {
            const response = await API.post("/login", { username: email, password });
            login(response.data.access_token, response.data.user); // Add this
            alert("Prisijungta sėkmingai!");
            navigate("/map");
        } catch (err) {
            alert(err.response?.data?.detail || "Neteisingi prisijungimo duomenys");
        }
    };

    return (
        <div className="app-shell login-page">
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

            <main className="app-main login-content">
                <div className="login-card">
                    <h1>Prisijungimas</h1>
                    <p>Prisijunkite prie paskyros.</p>

                    <form className="login-form" onSubmit={handleSubmit}>
                        <label className="login-label">
                            El. paštas
                            <input
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                required
                                placeholder="įvestas@email.com"
                            />
                        </label>

                        <label className="login-label">
                            Slaptažodis
                            <input
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                required
                                placeholder="Slaptažodis"
                            />
                        </label>

                        <button type="submit" className="primary-btn">Prisijungti</button>
                    </form>

                    <div className="login-actions">
                        <NavLink to="/reset-password" className="secondary-btn">
                            Pamiršote slaptažodį?
                        </NavLink>
                        <NavLink to="/register" className="secondary-btn">
                            Nauja paskyra
                        </NavLink>
                    </div>
                </div>
            </main>
        </div>
    );
}
