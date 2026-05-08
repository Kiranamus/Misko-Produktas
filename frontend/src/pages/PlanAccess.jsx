import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import PageTopbar from "../components/PageTopbar";
import StripePayment from "../components/StripePayment";
import { useAuth } from "../context/AuthContext";
import { useLanguage } from "../context/LanguageContext";
import "./PlanAccess.css";

const API_BASE = "http://localhost:8000";

const PLAN_CONTENT = {
  county_day: {
    titleKey: "countyDayTitle",
    descriptionKey: "countyDayDescription",
    price: 14.99,
    priceLabel: "14,99 €",
  },
  lithuania_day: {
    titleKey: "lithuaniaDayTitle",
    descriptionKey: "lithuaniaDayDescription",
    price: 24.99,
    priceLabel: "24,99 €",
  },
  lithuania_month: {
    titleKey: "lithuaniaMonthTitle",
    descriptionKey: "lithuaniaMonthDescription",
    price: 39.99,
    priceLabel: "39,99 €",
  },
};

export default function PlanAccess() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { t } = useLanguage();
  const [counties, setCounties] = useState([]);
  const [loadingCounties, setLoadingCounties] = useState(true);
  const [selectedCounty, setSelectedCounty] = useState("");
  const [paymentSuccess, setPaymentSuccess] = useState(false);
  const [paymentError, setPaymentError] = useState(null);

  const { recordPurchase, isPlanPurchased, hasActivePlan, activePlan } = useAuth();

  const planId = searchParams.get("plan") || "county_day";
  const plan = PLAN_CONTENT[planId] || PLAN_CONTENT.county_day;
  const needsCounty = planId === "county_day";
  const alreadyPurchased = isPlanPurchased(planId);
  const blockedByOtherPlan = hasActivePlan && activePlan !== planId && !alreadyPurchased;

  const paramsForMap = useMemo(() => {
    const params = new URLSearchParams();
    if (needsCounty && selectedCounty) {
      params.set("county", selectedCounty);
    }
    return params.toString();
  }, [needsCounty, selectedCounty]);

  useEffect(() => {
    if (!needsCounty) return;

    let active = true;

    fetch(`${API_BASE}/counties`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        if (!active) return;
        const items = Array.isArray(data?.items) ? data.items : [];
        setCounties(items);
        if (items.length > 0) {
          setSelectedCounty((current) => current || items[0]);
        }
      })
      .catch(() => {
        setPaymentError(t("genericError"));
      })
      .finally(() => {
        if (active) setLoadingCounties(false);
      });

    return () => {
      active = false;
    };
  }, [needsCounty, t]);

  const handlePaymentSuccess = async (paymentIntent) => {
    try {
      await recordPurchase(planId, paymentIntent.id);

      setPaymentSuccess(true);
      setPaymentError(null);

      localStorage.setItem("payment_completed", "true");
      localStorage.setItem("payment_plan", planId);
      localStorage.setItem("payment_amount", String(plan.price));

      if (needsCounty && selectedCounty) {
        localStorage.setItem("purchased_county", selectedCounty);
      }
    } catch {
      setPaymentError(t("paymentRecordedError"));
    }
  };

  const handlePaymentError = () => {
    setPaymentError(t("paymentFailed"));
    setPaymentSuccess(false);
  };

  const handleGoToMap = () => {
    navigate(`/map${paramsForMap ? `?${paramsForMap}` : ""}`);
  };

  return (
    <div className="plan-page">
      <PageTopbar />

      <main className="plan-main">
        <section className="plan-card">
          <span className={`plan-chip ${alreadyPurchased ? "purchased-chip" : ""}`}>
            {alreadyPurchased ? t("purchased") : t("selectedPlan")}
          </span>
          <h1>{t(plan.titleKey)}</h1>
          <p>{t(plan.descriptionKey)}</p>
          <div className="plan-price">
            <span className="price-amount">{plan.priceLabel}</span>
            {planId === "lithuania_month" && <span className="price-period">/ {t("monthPeriod")}</span>}
          </div>
        </section>

        <section className="checkout-card">
          <h2>{t("payment")}</h2>

          {alreadyPurchased ? (
            <div className="payment-success">
              <p>{t("alreadyPurchasedText")}</p>
              <button className="primary-btn" onClick={handleGoToMap}>
                {t("goToMap")}
              </button>
            </div>
          ) : blockedByOtherPlan ? (
            <div className="payment-error neutral">
              <p>{t("activePlanBlocks")}</p>
            </div>
          ) : paymentSuccess ? (
            <div className="payment-success">
              <p>{t("paymentSuccess")}</p>
              <button className="primary-btn" onClick={handleGoToMap}>
                {t("goToMap")}
              </button>
            </div>
          ) : (
            <>
              {needsCounty && (
                <div className="municipality-select-block">
                  <label htmlFor="county">{t("selectCounty")}</label>
                  <select
                    id="county"
                    value={selectedCounty}
                    onChange={(event) => setSelectedCounty(event.target.value)}
                    disabled={loadingCounties || counties.length === 0}
                  >
                    {counties.map((county) => (
                      <option key={county} value={county}>
                        {county}
                      </option>
                    ))}
                  </select>
                  {loadingCounties && <span className="helper-text">{t("loadingCounties")}</span>}
                </div>
              )}

              {paymentError && (
                <div className="payment-error">
                  <p>{paymentError}</p>
                </div>
              )}

              <div className="stripe-payment-wrapper">
                <StripePayment
                  amount={plan.price}
                  onSuccess={handlePaymentSuccess}
                  onError={handlePaymentError}
                />
              </div>
            </>
          )}

          {paymentError && (alreadyPurchased || blockedByOtherPlan) && (
            <div className="payment-error">
              <p>{paymentError}</p>
            </div>
          )}

          <div className="plan-actions">
            <button
              className="secondary-btn"
              onClick={() => navigate("/")}
              style={{ marginTop: "16px" }}
            >
              {t("backHome")}
            </button>
          </div>
        </section>
      </main>
    </div>
  );
}
