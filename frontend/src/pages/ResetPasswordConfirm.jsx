import { useState } from "react";
import { NavLink, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import PageTopbar from "../components/PageTopbar";
import { useLanguage } from "../context/LanguageContext";
import { getAuthErrorMessage, resetPassword } from "../services/authApi";
import "./ResetPassword.css";

const PASSWORD_PATTERN = /^(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$/;

export default function ResetPasswordConfirm() {
  const navigate = useNavigate();
  const location = useLocation();
  const { t } = useLanguage();
  const [searchParams] = useSearchParams();
  const hashSearch = location.hash.includes("?")
    ? new URLSearchParams(location.hash.split("?")[1])
    : null;
  const token = searchParams.get("token") || hashSearch?.get("token");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setMessage("");

    if (!token) {
      setError("Neteisingas arba pasenęs atkūrimo kodas.");
      return;
    }

    if (!PASSWORD_PATTERN.test(newPassword)) {
      setError(t("strongPassword"));
      return;
    }

    if (newPassword !== confirmPassword) {
      setError(t("passwordsDoNotMatch"));
      return;
    }

    setSubmitting(true);

    try {
      await resetPassword({ token, new_password: newPassword });
      setMessage("Slaptažodis sėkmingai pakeistas. Galite prisijungti.");
      window.setTimeout(() => navigate("/login"), 900);
    } catch (requestError) {
      setError(getAuthErrorMessage(requestError, "Įvyko klaida. Kodas gali būti pasenęs."));
    } finally {
      setSubmitting(false);
    }
  };

  if (!token) {
    return (
      <div className="reset-page">
        <PageTopbar />
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

          <form className="reset-form" onSubmit={handleSubmit} noValidate>
            <label className="reset-label">
              Naujas slaptažodis
              <input
                type="password"
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
                required
                minLength={8}
                pattern="^(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$"
                placeholder="Naujas slaptažodis"
              />
            </label>

            <label className="reset-label">
              Pakartokite naują slaptažodį
              <input
                type="password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                required
                placeholder="Pakartokite slaptažodį"
              />
            </label>

            <div className="password-hint">{t("strongPassword")}</div>
            {error && <div className="form-message error">{error}</div>}
            {message && <div className="form-message success">{message}</div>}

            <button type="submit" className="primary-btn" style={{ width: "100%" }} disabled={submitting}>
              {submitting ? t("processing") : "Keisti slaptažodį"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
