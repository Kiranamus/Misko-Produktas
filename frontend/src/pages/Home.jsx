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
      </div>


      <button className="go-map-btn"
        onClick={() => navigate("/map")}
      >
        Eiti į žemėlapį
      </button>
    </div>
  );
}
