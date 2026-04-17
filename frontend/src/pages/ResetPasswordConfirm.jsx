import { useState } from "react";
import { NavLink, useNavigate, useSearchParams } from "react-router-dom";
import PageTopbar from "../components/PageTopbar";
import { getAuthErrorMessage, resetPassword } from "../services/authApi";
import "./ResetPassword.css";

export default function ResetPasswordConfirm() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");
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
      await resetPassword({ token, new_password: newPassword });
      alert("Slaptažodis sėkmingai pakeistas! Galite prisijungti.");
      navigate("/login");
    } catch (error) {
      alert(getAuthErrorMessage(error, "Įvyko klaida. Kodas gali būti pasenęs."));
    }
  };

  if (!token) {
    return (
      <div className="reset-page">
        <div className="reset-content">
          <div className="reset-card">
            <h1>Klaida</h1>
            <p>Neteisingas arba pasenęs slaptažodžio atkūrimo kodas.</p>
            <NavLink to="/reset-password" className="primary-btn">
              Bandyti dar kartą
            </NavLink>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="reset-page">
      <PageTopbar />

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
