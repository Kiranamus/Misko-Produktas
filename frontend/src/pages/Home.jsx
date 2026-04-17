import { useNavigate } from "react-router-dom";
import PageTopbar from "../components/PageTopbar";
import "./Home.css";

const plans = [
  {
    id: "county_day",
    title: "Vienos dienos narystė duomenims iš vienos apskrities",
    description:
      "Trumpalaikė prieiga konkrečiai apskričiai, kai reikia greitai peržiūrėti vienos teritorijos objektus ir jų investicinį potencialą.",
  },
  {
    id: "lithuania_day",
    title: "Vienos dienos narystė visai Lietuvai",
    description:
      "Skirta trumpam visos Lietuvos objektų palyginimui, kai norisi apžvelgti platesnį vaizdą per vieną dieną.",
  },
  {
    id: "lithuania_month",
    title: "Mėnesio prenumerata visai Lietuvai",
    description:
      "Patogiausias pasirinkimas ilgesniam darbui su žemėlapiu, kai prie duomenų ir analizės reikia grįžti nuolat.",
  },
];

export default function Home() {
  const navigate = useNavigate();

  return (
    <div className="home-page">
      <PageTopbar />

      <div className="home-bg home-bg-1" />
      <div className="home-bg home-bg-2" />
      <div className="home-bg home-bg-3" />

      <main className="home-main">
        <section className="home-card intro-card">
          <span className="section-chip">Miškininkystės analizės ir investavimo platforma</span>
          <h1 className="hero-title">
            Forest
            <span>ForYou</span>
          </h1>
          <p className="hero-subtitle">
            Interaktyvi sistema miško teritorijų vertinimui, skirta padėti aiškiau suprasti investicinį potencialą pagal
            geoduomenis, ribojimus, dirvožemio savybes ir susisiekimą.
          </p>
          <p className="hero-note">
            Sprendimas orientuotas į duomenimis pagrįstą pasirinkimą: naudotojas mato prioritetines teritorijas žemėlapyje
            ir gali koreguoti vertinimo svorius pagal savo tikslus.
          </p>
          <p className="hero-note">
            Sistema padeda greičiau susiaurinti paiešką ir suprasti, kurios vietovės atrodo patraukliausios pagal
            pasirinktą investavimo logiką.
          </p>
        </section>

        <section className="home-card about-card" id="about-project">
          <h2>Apie projektą</h2>
          <p>
            ForestForYou yra kuriama SaaS tipo miškininkystės analizės platforma, orientuota į patogų teritorijų
            vertinimą ir aiškų investavimo sprendimų palaikymą. Sistemos tikslas yra padėti naudotojui greitai pamatyti,
            kurios vietovės gali būti palankiausios pagal pasirinktus kriterijus.
          </p>
        </section>

        <section className="plans-section">
          {plans.map((plan) => (
            <article className="plan-card" key={plan.id}>
              <span className="plan-chip">Planas</span>
              <h3>{plan.title}</h3>
              <p>{plan.description}</p>
              <button className="primary-btn" onClick={() => navigate(`/plan-access?plan=${plan.id}`)}>
                Pasirinkti
              </button>
            </article>
          ))}
        </section>

        <section className="team-section">
          <div className="home-card team-card">
            <h2>Komandos nariai</h2>
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
            <h2>Mentorius</h2>
            <p>Prof. Rytis Maskeliūnas</p>
          </div>
        </section>
      </main>
    </div>
  );
}
