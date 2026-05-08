import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import PageTopbar from "../components/PageTopbar";
import { useAuth } from "../context/AuthContext";
import { useLanguage } from "../context/LanguageContext";
import { getAuthErrorMessage, loginUser } from "../services/authApi";
import "./Login.css";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function Login() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const { t } = useLanguage();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [formError, setFormError] = useState("");
  const [formSuccess, setFormSuccess] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const validateForm = () => {
    if (!EMAIL_PATTERN.test(email.trim())) {
      return t("invalidEmail");
    }

    if (!password) {
      return t("passwordRequired");
    }

    return "";
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setFormError("");
    setFormSuccess("");

    const validationError = validateForm();
    if (validationError) {
      setFormError(validationError);
      return;
    }

    setSubmitting(true);

    try {
      const response = await loginUser({ username: email.trim(), password });
      await login(response.access_token, response.user);
      setFormSuccess(t("loginSuccess"));
      navigate("/");
    } catch (error) {
      setFormError(getAuthErrorMessage(error, t("genericError")));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="app-shell login-page">
      <PageTopbar />

      <main className="app-main login-content">
        <div className="login-card">
          <h1>{t("loginTitle")}</h1>
          <p>{t("loginIntro")}</p>

          <form className="login-form" onSubmit={handleSubmit} noValidate>
            <label className="login-label">
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

            <label className="login-label">
              {t("password")}
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
                placeholder={t("password")}
              />
            </label>

            {formError && <div className="form-message error">{formError}</div>}
            {formSuccess && <div className="form-message success">{formSuccess}</div>}

            <button type="submit" className="primary-btn" disabled={submitting}>
              {submitting ? t("processing") : t("login")}
            </button>
          </form>

          <div className="login-actions">
            <NavLink to="/reset-password" className="secondary-btn">
              {t("forgotPassword")}
            </NavLink>
            <NavLink to="/register" className="secondary-btn">
              {t("newAccount")}
            </NavLink>
          </div>
        </div>
      </main>
    </div>
  );
}
