import { Routes, Route } from "react-router-dom";
import { useNavigate } from "react-router-dom";
import { FaHome } from "react-icons/fa";

import Home from "./pages/Home.jsx";
import MapPage from "./pages/MapPage.jsx";

function App() {
  const navigate = useNavigate();

  return (
    <div className="app">
      <div className="navbar">
        <h1>Miško investicinis žemėlapis</h1>

        <div className="navbar-right">
          <button
            className="transparent-btn"
            title="Pagrindinis"
            onClick={() => navigate("/")}
          >
            <FaHome />
          </button>

          <button
            className="transparent-btn"
            onClick={() => navigate("/map")}
          >
            Žemėlapis
          </button>
        </div>
      </div>
      
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/map" element={<MapPage />} />
      </Routes>
    </div>
  );
}

export default App;
