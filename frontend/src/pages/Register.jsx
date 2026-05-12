import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import PageTopbar from "../components/PageTopbar";
import { useLanguage } from "../context/LanguageContext";
import { getAuthErrorMessage, registerUser } from "../services/authApi";
import "./Register.css";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PASSWORD_PATTERN = /^(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$/;

export default function Register() {
  const navigate = useNavigate();
  const { t } = useLanguage();
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [formError, setFormError] = useState("");
  const [formSuccess, setFormSuccess] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const validateForm = () => {
    if (!firstName.trim()) {
      return t("firstNameRequired");
    }

    if (!lastName.trim()) {
      return t("lastNameRequired");
    }

    if (!EMAIL_PATTERN.test(email.trim())) {
      return t("invalidEmail");
    }

    if (!PASSWORD_PATTERN.test(password)) {
      return t("strongPassword");
    }

    if (password !== confirmPassword) {
      return t("passwordsDoNotMatch");
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
      const response = await registerUser({
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        email: email.trim(),
        password,
      });
      setFormSuccess(
        response.message
          ? getAuthErrorMessage({ response: { data: { detail: response.message } } }, t("accountCreated"), t)
          : t("accountCreated")
      );
      setFirstName("");
      setLastName("");
      setEmail("");
      setPassword("");
      setConfirmPassword("");
      window.setTimeout(() => navigate("/login"), 800);
    } catch (error) {
      setFormError(getAuthErrorMessage(error, t("genericError"), t));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="register-page">
      <PageTopbar />

      <main className="register-content">
        <div className="auth-card">
          <h1>{t("registerTitle")}</h1>
          <p>{t("registerIntro")}</p>

          <form className="auth-form" onSubmit={handleSubmit} noValidate>
            <label className="auth-label">
              {t("firstName")}
              <input
                type="text"
                value={firstName}
                onChange={(event) => setFirstName(event.target.value)}
                required
                placeholder={t("firstName")}
              />
            </label>

            <label className="auth-label">
              {t("lastName")}
              <input
                type="text"
                value={lastName}
                onChange={(event) => setLastName(event.target.value)}
                required
                placeholder={t("lastName")}
              />
            </label>

            <label className="auth-label">
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

            <label className="auth-label">
              {t("password")}
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
                minLength={8}
                pattern="^(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$"
                placeholder={t("password")}
              />
            </label>

            <label className="auth-label">
              {t("confirmPassword")}
              <input
                type="password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                required
                placeholder={t("confirmPassword")}
              />
            </label>

            <div className="password-hint">{t("strongPassword")}</div>

            {formError && <div className="form-message error">{formError}</div>}
            {formSuccess && <div className="form-message success">{formSuccess}</div>}

            <button type="submit" className="primary-btn" disabled={submitting}>
              {submitting ? t("processing") : t("createAccount")}
            </button>
          </form>

          <div className="auth-bottom">
            <p>{t("alreadyHaveAccount")}</p>
            <NavLink to="/login" className="secondary-btn">{t("login")}</NavLink>
          </div>
        </div>
      </main>
    </div>
  );
}
