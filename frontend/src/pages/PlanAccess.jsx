import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import PageTopbar from "../components/PageTopbar";
import StripePayment from "../components/StripePayment";
import { useAuth } from "../context/AuthContext";
import "./PlanAccess.css";

const API_BASE = "http://localhost:8000";

const PLAN_CONTENT = {
  county_day: {
    title: "Vienos dienos narystė vienai apskričiai",
    description: "Trumpalaikė prieiga konkrečios apskrities duomenų peržiūrai ir investicinio potencialo įvertinimui.",
    price: 4.99,
    priceCents: 499,
  },
  lithuania_day: {
    title: "Vienos dienos narystė visai Lietuvai",
    description: "Vienos dienos prieiga visos Lietuvos objektų peržiūrai, skirta greitam rinkos nuskanavimui.",
    price: 9.99,
    priceCents: 999,
  },
  lithuania_month: {
    title: "Mėnesio prenumerata visai Lietuvai",
    description: "Pilnesniam darbui skirta prenumerata, kai reikia reguliariai grįžti prie visos Lietuvos duomenų.",
    price: 29.99,
    priceCents: 2999,
  },
};

export default function PlanAccess() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [counties, setCounties] = useState([]);
  const [loadingCounties, setLoadingCounties] = useState(false);
  const [selectedCounty, setSelectedCounty] = useState("");
  const [paymentSuccess, setPaymentSuccess] = useState(false);
  const [paymentError, setPaymentError] = useState(null);

  const { recordPurchase, isPlanPurchased } = useAuth();

  const planId = searchParams.get("plan") || "county_day";
  const plan = PLAN_CONTENT[planId] || PLAN_CONTENT.county_day;
  const needsCounty = planId === "county_day";

  const alreadyPurchased = isPlanPurchased(planId);

  useEffect(() => {
    if (!needsCounty) return;

    let active = true;
    setLoadingCounties(true);

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
      .catch((err) => {
        console.error("Nepavyko užkrauti apskričių:", err);
      })
      .finally(() => {
        if (active) setLoadingCounties(false);
      });

    return () => {
      active = false;
    };
  }, [needsCounty]);

  const handlePaymentSuccess = async (paymentIntent) => {
    console.log("Payment successful:", paymentIntent);

    try {
      await recordPurchase(planId, paymentIntent.id);

      setPaymentSuccess(true);
      setPaymentError(null);

      localStorage.setItem("payment_completed", "true");
      localStorage.setItem("payment_plan", planId);
      localStorage.setItem("payment_amount", plan.price);

      if (needsCounty && selectedCounty) {
        localStorage.setItem("purchased_county", selectedCounty);
      }

      alert(`Mokėjimas sėkmingas! Jūs turite prieigą prie ${plan.title}`);
    } catch (error) {
      console.error("Failed to record purchase:", error);
      setPaymentError("Mokėjimas atliktas, bet įrašyti nepavyko. Susisiekite su administratoriumi.");
    }
  };

  const handlePaymentError = (error) => {
    console.error("Payment failed:", error);
    setPaymentError(error.message || "Mokėjimas nepavyko. Bandykite dar kartą.");
    setPaymentSuccess(false);
  };

  const handleGoToMap = () => {
    const params = new URLSearchParams();

    if (needsCounty && selectedCounty) {
      params.set("county", selectedCounty);
    }

    navigate(`/map${params.toString() ? `?${params.toString()}` : ""}`);
  };

  if (alreadyPurchased) {
    return (
      <div className="plan-page">
        <PageTopbar />

        <main className="plan-main">
          <section className="plan-card">
            <span className="plan-chip purchased-chip">Jau įsigyta</span>
            <h1>{plan.title}</h1>
            <p>{plan.description}</p>
            <div className="plan-price">
              <span className="price-amount">{plan.price.toFixed(2)} €</span>
              {planId === "lithuania_month" && <span className="price-period">/ mėn.</span>}
            </div>
          </section>

          <section className="checkout-card">
            <h2>Mokėjimas</h2>

            <div className="payment-success">
              <p>Jūs jau turite šį planą! Galite naudotis žemėlapiu.</p>
              <button className="primary-btn" onClick={handleGoToMap}>
                Eiti į žemėlapį
              </button>
            </div>

            <div className="plan-actions">
              <button
                className="secondary-btn"
                onClick={() => navigate("/")}
                style={{ marginTop: "16px" }}
              >
                Grįžti į pradinį puslapį
              </button>
            </div>
          </section>
        </main>
      </div>
    );
  }

  return (
    <div className="plan-page">
      <PageTopbar />

      <main className="plan-main">
        <section className="plan-card">
          <span className="plan-chip">Pasirinktas planas</span>
          <h1>{plan.title}</h1>
          <p>{plan.description}</p>
          <div className="plan-price">
            <span className="price-amount">{plan.price.toFixed(2)} €</span>
            {planId === "lithuania_month" && <span className="price-period">/ mėn.</span>}
          </div>
        </section>

        <section className="checkout-card">
          <h2>Mokėjimas</h2>

          {paymentSuccess ? (
            <div className="payment-success">
              <p>Mokėjimas sėkmingas! Jūs jau turite prieigą.</p>
              <button className="primary-btn" onClick={handleGoToMap}>
                Eiti į žemėlapį
              </button>
            </div>
          ) : (
            <>
              {needsCounty && (
                <div className="municipality-select-block">
                  <label htmlFor="county">Pasirinkite apskritį</label>
                  <select
                    id="county"
                    value={selectedCounty}
                    onChange={(e) => setSelectedCounty(e.target.value)}
                    disabled={loadingCounties || counties.length === 0}
                  >
                    {counties.map((county) => (
                      <option key={county} value={county}>
                        {county}
                      </option>
                    ))}
                  </select>
                  {loadingCounties && <span className="helper-text">Kraunamas apskričių sąrašas...</span>}
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

          <div className="plan-actions">
            <button
              className="secondary-btn"
              onClick={() => navigate("/")}
              style={{ marginTop: "16px" }}
            >
              Grįžti į pradinį puslapį
            </button>
          </div>
        </section>
      </main>
    </div>
  );
}