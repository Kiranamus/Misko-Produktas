import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import PageTopbar from "../components/PageTopbar";
import { getAuthErrorMessage, registerUser } from "../services/authApi";
import "./Register.css";

export default function Register() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (password !== confirmPassword) {
      alert("Slaptažodžiai nesutampa");
      return;
    }

    try {
      await registerUser({ name, email, password });
      alert("Paskyra sukurta sėkmingai!");
      navigate("/login");
    } catch (error) {
      alert(getAuthErrorMessage(error, "Įvyko klaida"));
    }
  };

  return (
    <div className="register-page">
      <PageTopbar />

      <main className="register-content">
        <div className="auth-card">
          <h1>Registracija</h1>
          <p>Sukurkite paskyrą ir pradėkite naudoti sistemą.</p>

          <form className="auth-form" onSubmit={handleSubmit}>
            <label className="auth-label">
              Vardas
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                placeholder="Vardas"
              />
            </label>

            <label className="auth-label">
              El. paštas
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                placeholder="ivestas@email.com"
              />
            </label>

            <label className="auth-label">
              Slaptažodis
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                placeholder="Slaptažodis"
              />
            </label>

            <label className="auth-label">
              Patvirtinkite slaptažodį
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                placeholder="Pakartokite slaptažodį"
              />
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
