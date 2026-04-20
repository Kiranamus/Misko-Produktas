import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import PageTopbar from "../components/PageTopbar";
import { useAuth } from "../context/AuthContext";
import { getAuthErrorMessage, loginUser } from "../services/authApi";
import "./Login.css";

export default function Login() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = async (event) => {
    event.preventDefault();

    try {
      const response = await loginUser({ username: email, password });
      login(response.access_token, response.user);
      alert("Prisijungta sėkmingai!");
      navigate("/");
    } catch (error) {
      alert(getAuthErrorMessage(error, "Neteisingi prisijungimo duomenys"));
    }
  };

  return (
    <div className="app-shell login-page">
      <PageTopbar />

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
                placeholder="ivestas@email.com"
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
