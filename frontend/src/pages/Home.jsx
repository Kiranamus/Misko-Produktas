import { NavLink, useNavigate } from "react-router-dom";
import { FaArrowRight, FaMapMarkedAlt, FaLeaf, FaLayerGroup } from "react-icons/fa";
import { useAuth } from "../context/AuthContext";
import "./Home.css";

export default function Home() {
  const navigate = useNavigate();
  const { isAuthenticated, logout } = useAuth();

  return (
    <div className="home-page">
      <header className="topbar">
        <div className="topbar-inner">
          <NavLink to="/" className="brand">
            <div className="brand-mark">F</div>
            <div className="brand-text">
              <span className="brand-title">ForestForYou</span>
              <span className="brand-subtitle">
                Miškininkystės analizė ir investavimas
              </span>
            </div>
          </NavLink>

          <nav className="topbar-nav">
            {isAuthenticated && (
              <NavLink to="/map" className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>Žemėlapis</NavLink>
            )}
            {!isAuthenticated ? (
              <>
                <NavLink to="/register" className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>Registruotis</NavLink>
                <NavLink to="/login" className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>Prisijungti</NavLink>
              </>
            ) : (
              <span onClick={() => { logout(); navigate("/"); }} className="nav-link" style={{ cursor: 'pointer' }}>
                Atsijungti
              </span>
            )}
            <NavLink to="/" className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>Pagrindinis</NavLink>
          </nav>
        </div>
      </header>

      <div className="home-bg home-bg-1"></div>
      <div className="home-bg home-bg-2"></div>
      <div className="home-bg home-bg-3"></div>

      <section className="hero-section">
        <div className="hero-left">
          <div className="hero-badge">Miškininkystės analizės ir investavimo platforma</div>

          <h1 className="hero-title">
            Forest
            <span>ForYou</span>
          </h1>

          <p className="hero-subtitle">
            Interaktyvi sistema miško teritorijų vertinimui, skirta padėti
            aiškiau suprasti investicinį potencialą pagal geoduomenis,
            ribojimus, dirvožemį ir susisiekimą.
          </p>

          <p className="hero-note">
            Sprendimas orientuotas į duomenimis pagrįstą pasirinkimą:
            naudotojas mato prioritetines teritorijas žemėlapyje ir gali
            koreguoti vertinimo svorius pagal savo tikslus.
          </p>

          <p className="hero-note">
            Sprendimas orientuotas į duomenimis pagrįstą pasirinkimą:
            naudotojas mato prioritetines teritorijas žemėlapyje ir gali
            koreguoti vertinimo svorius pagal savo tikslus.
          </p>

          <div className="hero-actions">
            <button className="primary-btn" onClick={() => navigate("/map")}>
              Peržiūrėti investicinį žemėlapį <FaArrowRight />
            </button>
          </div>


          <div className="hero-stats">
            <div className="stat-card">
              <FaMapMarkedAlt className="stat-icon" />
              <div>
                <div className="stat-value">Erdvinė analizė</div>
                <div className="stat-label">GIS pagrindu atliekamas vertinimas</div>
              </div>
            </div>

            <div className="stat-card">
              <FaLayerGroup className="stat-icon" />
              <div>
                <div className="stat-value">PostGIS</div>
                <div className="stat-label">Geo duomenų saugojimas ir apdorojimas</div>
              </div>
            </div>

            <div className="stat-card">
              <FaLeaf className="stat-icon" />
              <div>
                <div className="stat-value">Investicinis indeksas</div>
                <div className="stat-label">Aiškus teritorijų palyginimas</div>
              </div>
            </div>
          </div>
        </div>

        <div className="hero-right">
          <div className="glass-card highlight-card">
            <div className="highlight-top">
              <span className="highlight-chip">ForestForYou</span>
              <span className="highlight-chip muted">K603 komanda</span>
            </div>

            <h2>Miško investavimo žemėlapis su aiškiu vizualiu vertinimu</h2>

            <p>
              Platforma padeda išskirti teritorijas pagal investavimo
              palankumą ir leidžia greitai pamatyti, kur verta koncentruoti
              dėmesį, o kur rizikos didesnės.
            </p>

            <div className="mini-grid">
              <div className="mini-item">
                <span className="mini-number">1</span>
                <span>Apjungiami svarbiausi geografiniai sluoksniai</span>
              </div>
              <div className="mini-item">
                <span className="mini-number">2</span>
                <span>Skaičiuojamas individualizuotas balas</span>
              </div>
              <div className="mini-item">
                <span className="mini-number">3</span>
                <span>Žemėlapyje parodomi perspektyviausi plotai</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="info-section" id="about-project">
        <div className="info-card project-card">
          <h3>Apie projektą</h3>
          <p>
            „ForestForYou“ yra kuriama SaaS tipo miškininkystės analizės
            platforma, orientuota į patogų teritorijų vertinimą ir vizualų
            investavimo sprendimų palaikymą. Sistemos tikslas – padėti
            naudotojui aiškiai pamatyti, kurios vietovės gali būti
            palankiausios pagal pasirinktus kriterijus.
          </p>
        </div>

        <div className="info-card team-card">
          <h3>Komanda K603</h3>
          <div className="team-list">
            <span>Matas Kučas</span>
            <span>Mindaugas Matulaitis</span>
            <span>Giedrė Jansonaitė</span>
            <span>Simas Janulynas</span>
            <span>Kastautas Maižvila</span>
            <span>Ugnius Sasnauskas</span>
          </div>
        </div>

        <div className="info-card mentor-card">
          <h3>Mentorius</h3>
          <p>Prof. Rytis Maskeliūnas</p>
        </div>
      </section>
    </div>
  );
}
