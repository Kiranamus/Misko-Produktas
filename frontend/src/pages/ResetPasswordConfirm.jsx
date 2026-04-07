import { useState } from "react";
import { NavLink, useNavigate, useSearchParams } from "react-router-dom";
import { API } from "../api";
import { useAuth } from "../context/AuthContext";
import "./ResetPassword.css";

export default function ResetPasswordConfirm() {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const token = searchParams.get("token");
    const { isAuthenticated } = useAuth();

    const [newPassword, setNewPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");

    const handleSubmit = async (event) => {
        event.preventDefault();

        if (newPassword !== confirmPassword) {
            alert("Slaptažodžiai nesutampa");
            return;
        }

        if (!token) {
            alert("Neteisingas arba pasenęs atkūrimo kodas");
            return;
        }

        try {
            await API.post("/reset-password", {
                token: token,
                new_password: newPassword
            });
            alert("Slaptažodis sėkmingai pakeistas! Galite prisijungti.");
            navigate("/login");
        } catch (err) {
            alert(err.response?.data?.detail || "Įvyko klaida. Kodas gali būti pasenęs.");
        }
    };

    if (!token) {
        return (
            <div className="reset-page">
                <div className="reset-content">
                    <div className="reset-card">
                        <h1>Klaida</h1>
                        <p>Neteisingas arba pasenęs slaptažodžio atkūrimo kodas.</p>
                        <NavLink to="/forgot-password" className="primary-btn">
                            Bandyti dar kartą
                        </NavLink>
                    </div>
                </div>
            </div>
        );
    }

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
                    <h1>Naujo slaptažodžio nustatymas</h1>
                    <p>Įveskite naują slaptažodį.</p>

                    <form className="reset-form" onSubmit={handleSubmit}>
                        <label className="reset-label">
                            Naujas slaptažodis
                            <input
                                type="password"
                                value={newPassword}
                                onChange={(e) => setNewPassword(e.target.value)}
                                required
                                placeholder="Naujas slaptažodis"
                            />
                        </label>

                        <label className="reset-label">
                            Pakartokite naują slaptažodį
                            <input
                                type="password"
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                required
                                placeholder="Pakartokite slaptažodį"
                            />
                        </label>

                        <button type="submit" className="primary-btn" style={{ width: "100%" }}>
                            Keisti slaptažodį
                        </button>
                    </form>
                </div>
            </div>
        </div>
    );
}