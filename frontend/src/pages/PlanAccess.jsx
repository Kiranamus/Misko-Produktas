import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import PageTopbar from "../components/PageTopbar";
import "./PlanAccess.css";

const API_BASE = "http://localhost:8000";

const PLAN_CONTENT = {
  county_day: {
    title: "Vienos dienos narystė vienai apskričiai",
    description:
      "Trumpalaikė prieiga konkrečios apskrities duomenų peržiūrai ir investicinio potencialo įvertinimui.",
  },
  lithuania_day: {
    title: "Vienos dienos narystė visai Lietuvai",
    description:
      "Vienos dienos prieiga visos Lietuvos objektų peržiūrai, skirta greitam rinkos nuskanavimui.",
  },
  lithuania_month: {
    title: "Mėnesio prenumerata visai Lietuvai",
    description:
      "Pilnesniam darbui skirta prenumerata, kai reikia reguliariai grįžti prie visos Lietuvos duomenų.",
  },
};

export default function PlanAccess() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [counties, setCounties] = useState([]);
  const [loadingCounties, setLoadingCounties] = useState(false);
  const [selectedCounty, setSelectedCounty] = useState("");

  const planId = searchParams.get("plan") || "county_day";
  const plan = PLAN_CONTENT[planId] || PLAN_CONTENT.county_day;
  const needsCounty = planId === "county_day";

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

  const paymentLabel = useMemo(() => {
    if (planId === "county_day") return "Mokėjimas už vienos apskrities peržiūrą bus prijungtas čia.";
    if (planId === "lithuania_day") return "Mokėjimas už vienos dienos Lietuvos prieigą bus prijungtas čia.";
    return "Mėnesinės prenumeratos mokėjimas bus prijungtas čia.";
  }, [planId]);

  const handleGoToMap = () => {
    const params = new URLSearchParams();

    if (needsCounty && selectedCounty) {
      params.set("county", selectedCounty);
    }

    navigate(`/map${params.toString() ? `?${params.toString()}` : ""}`);
  };

  return (
    <div className="plan-page">
      <PageTopbar />

      <main className="plan-main">
        <section className="plan-card">
          <span className="plan-chip">Pasirinktas planas</span>
          <h1>{plan.title}</h1>
          <p>{plan.description}</p>
        </section>

        <section className="checkout-card">
          <h2>Mokėjimas</h2>
          <p>{paymentLabel}</p>

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

          <div className="plan-actions">
            <button
              className="primary-btn"
              onClick={handleGoToMap}
              disabled={needsCounty && !selectedCounty}
            >
              Eiti į žemėlapį
            </button>
            <button className="secondary-btn" onClick={() => navigate("/")}>
              Grįžti į pradinį puslapį
            </button>
          </div>
        </section>
      </main>
    </div>
  );
}
