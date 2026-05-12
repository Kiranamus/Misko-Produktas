import { useState } from "react";
import { NavLink } from "react-router-dom";
import PageTopbar from "../components/PageTopbar";
import { useLanguage } from "../context/LanguageContext";
import { getAuthErrorMessage, requestPasswordReset } from "../services/authApi";
import "./ResetPassword.css";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function ResetPassword() {
  const { t } = useLanguage();
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setMessage("");
    setError("");

    if (!EMAIL_PATTERN.test(email.trim())) {
      setError(t("invalidEmail"));
      return;
    }

    setSubmitting(true);

    try {
      await requestPasswordReset(email.trim());
      setMessage(t("resetPasswordSent"));
    } catch (requestError) {
      setError(getAuthErrorMessage(requestError, t("genericError"), t));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="reset-page">
      <PageTopbar />

      <div className="reset-content">
        <div className="reset-card">
          <h1>{t("resetPasswordTitle")}</h1>
          <p>{t("resetPasswordIntro")}</p>

          <form className="reset-form" onSubmit={handleSubmit} noValidate>
            <label className="reset-label">
              {t("email")}
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
                pattern="^[^\s@]+@[^\s@]+\.[^\s@]+$"
                placeholder="vardas@example.com"
              />
            </label>

            {error && <div className="form-message error">{error}</div>}
            {message && <div className="form-message success">{message}</div>}

            <button type="submit" className="primary-btn" style={{ width: "100%" }} disabled={submitting}>
              {submitting ? t("processing") : t("sendResetLink")}
            </button>
          </form>

          <div className="reset-actions">
            <NavLink to="/login" className="secondary-btn" style={{ width: "100%" }}>
              {t("backToLogin")}
            </NavLink>
          </div>
        </div>
      </div>
    </div>
  );
}
