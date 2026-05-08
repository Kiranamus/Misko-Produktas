import { useState } from "react";
import { useNavigate } from "react-router-dom";
import PageTopbar from "../components/PageTopbar";
import { useAuth } from "../context/AuthContext";
import { useLanguage } from "../context/LanguageContext";
import "./Home.css";

const planDefinitions = [
  {
    id: "county_day",
    titleKey: "countyDayTitle",
    descriptionKey: "countyDayDescription",
    price: "14,99 €",
  },
  {
    id: "lithuania_day",
    titleKey: "lithuaniaDayTitle",
    descriptionKey: "lithuaniaDayDescription",
    price: "24,99 €",
  },
  {
    id: "lithuania_month",
    titleKey: "lithuaniaMonthTitle",
    descriptionKey: "lithuaniaMonthDescription",
    price: "39,99 €",
    monthly: true,
  },
];

export default function Home() {
  const navigate = useNavigate();
  const { isAuthenticated, isPlanPurchased, hasActivePlan, activePlan, getPurchasedCounty, cancelActivePlan } = useAuth();
  const { t } = useLanguage();
  const [planNotice, setPlanNotice] = useState("");
  const [cancelingPlan, setCancelingPlan] = useState(false);
  const [showCancelConfirm, setShowCancelConfirm] = useState(false);

  const handlePlanClick = (planId, purchased) => {
    if (!isAuthenticated) {
      navigate("/login");
      return;
    }

    if (purchased) {
      const county = getPurchasedCounty();
      const params = planId === "county_day" && county ? `?county=${encodeURIComponent(county)}` : "";
      navigate(`/map${params}`);
      return;
    }

    navigate(`/plan-access?plan=${planId}`);
  };

  const handleCancelPlan = async () => {
    setPlanNotice("");
    setCancelingPlan(true);

    try {
      await cancelActivePlan();
      setPlanNotice(t("planCancelled"));
    } catch {
      setPlanNotice(t("genericError"));
    } finally {
      setCancelingPlan(false);
      setShowCancelConfirm(false);
    }
  };

  return (
    <div className="home-page">
      <PageTopbar />

      <main className="home-main">
        <section className="home-card intro-card">
          <span className="section-chip">{t("heroChip")}</span>
          <h1 className="hero-title">
            Forest
            <span>ForYou</span>
          </h1>
          <p className="hero-subtitle">{t("heroSubtitle")}</p>
          <p className="hero-note">{t("heroNote")}</p>
        </section>

        <section className="home-card about-card" id="about-project">
          <h2>{t("aboutProject")}</h2>
          <p>{t("aboutProjectText")}</p>
        </section>

        <section className="plans-section">
          <h2 className="plans-title">{t("choosePlan")}</h2>
          {planNotice && <div className="plans-notice">{planNotice}</div>}
          <div className="plans-grid">
            {planDefinitions.map((plan) => {
              const purchased = isAuthenticated && isPlanPurchased(plan.id);
              const blockedByOtherPlan = isAuthenticated && hasActivePlan && !purchased && activePlan !== plan.id;

              return (
                <article className={`plan-card ${purchased ? "purchased" : ""}`} key={plan.id}>
                  <span className="plan-chip">{purchased ? t("purchased") : t("plan")}</span>
                  <h3>{t(plan.titleKey)}</h3>
                  <p>{t(plan.descriptionKey)}</p>
                  <div className="plan-price">
                    {plan.price}
                    {plan.monthly && ` / ${t("monthPeriod")}`}
                  </div>
                  {purchased ? (
                    <div className="purchased-plan-actions">
                      <button
                        className="primary-btn go-map-btn"
                        onClick={() => handlePlanClick(plan.id, true)}
                      >
                        {t("goToMap")}
                      </button>
                      <button
                        className="cancel-plan-home-btn"
                        onClick={() => setShowCancelConfirm(true)}
                        disabled={cancelingPlan}
                      >
                        {cancelingPlan ? t("processing") : t("cancelPlan")}
                      </button>
                    </div>
                  ) : (
                    <button
                      className={blockedByOtherPlan ? "disabled-btn" : "primary-btn"}
                      onClick={() => handlePlanClick(plan.id, false)}
                      disabled={blockedByOtherPlan}
                    >
                      {blockedByOtherPlan ? t("currentPlanFirst") : t("choose")}
                    </button>
                  )}
                </article>
              );
            })}
          </div>
        </section>

        {showCancelConfirm && (
          <div className="confirm-backdrop" role="presentation">
            <div className="confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="cancel-plan-title">
              <h3 id="cancel-plan-title">{t("cancelPlanTitle")}</h3>
              <p>{t("cancelPlanText")}</p>
              <div className="confirm-actions">
                <button
                  type="button"
                  className="secondary-btn"
                  onClick={() => setShowCancelConfirm(false)}
                  disabled={cancelingPlan}
                >
                  {t("keepPlan")}
                </button>
                <button
                  type="button"
                  className="danger-btn"
                  onClick={handleCancelPlan}
                  disabled={cancelingPlan}
                >
                  {cancelingPlan ? t("processing") : t("confirmCancelPlan")}
                </button>
              </div>
            </div>
          </div>
        )}

        <section className="team-section">
          <div className="home-card team-card">
            <h2>{t("teamMembers")}</h2>
            <div className="team-list">
              <span>Matas Kučas</span>
              <span>Mindaugas Matulaitis</span>
              <span>Giedrė Jansonaitė</span>
              <span>Simas Janulynas</span>
              <span>Kastautas Maižvila</span>
              <span>Ugnius Sasnauskas</span>
            </div>
          </div>

          <div className="home-card mentor-card">
            <h2>{t("mentor")}</h2>
            <p>Prof. Rytis Maskeliūnas</p>
          </div>
        </section>
      </main>
    </div>
  );
}
