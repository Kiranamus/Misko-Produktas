import { Link } from "react-router-dom";
import { useNavigate } from "react-router-dom";
import "./Home.css";

export default function Home() {
  const navigate = useNavigate();
  
  return (
    <div className="home">
      <div className="parag">
        <p>
          Programa skirta surasti geriausią miško plotą investavimui
        </p>

        <p>
          Komanda K603
        </p>

        <p>
          Giedrė Jansonaitė,
          Simas Janulynas,
          Matas Kučas,
          Kastautas Maižvila,
          Mindaugas Matulaitis,
          Ugnius Sasnauskas
        </p>

        <p>
          Mentorius
          Prof. Rytis Maskeliūnas
        </p>
      </div>


      <button className="go-map-btn"
        onClick={() => navigate("/map")}
      >
        Eiti į žemėlapį
      </button>
    </div>
  );
}
