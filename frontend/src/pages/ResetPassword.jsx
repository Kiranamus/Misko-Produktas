import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import PageTopbar from "../components/PageTopbar";
import { getAuthErrorMessage, requestPasswordReset } from "../services/authApi";
import "./ResetPassword.css";

export default function ResetPassword() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");

  const handleSubmit = async (event) => {
    event.preventDefault();

    try {
      const data = await requestPasswordReset(email);
      const resetLink = `${window.location.origin}/reset-password-confirm?token=${data.token}`;

      window.open(resetLink, "_blank");
      alert("Slaptažodžio atkūrimo nuoroda atidaryta naujame skirtuke!");
      navigate("/login");
    } catch (error) {
      alert(getAuthErrorMessage(error, "Įvyko klaida"));
    }
  };

  return (
    <div className="reset-page">
      <PageTopbar />

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
                placeholder="ivestas@email.com"
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
