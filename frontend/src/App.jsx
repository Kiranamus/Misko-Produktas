import { Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import MapPage from "./pages/MapPage";
import Login from "./pages/Login";
import Register from "./pages/Register";
import ResetPassword from "./pages/ResetPassword";
import { AuthProvider } from "./context/AuthContext";
import ResetPasswordConfirm from "./pages/ResetPasswordConfirm";
import PlanAccess from "./pages/PlanAccess";
import "./App.css";

export default function App() {
  return (
    <AuthProvider>
      <div className="app-shell">
        <main className="app-main">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/map" element={<MapPage />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/reset-password" element={<ResetPassword />} />
            <Route path="/reset-password-confirm" element={<ResetPasswordConfirm />} />
            <Route path="/plan-access" element={<PlanAccess />} />
          </Routes>
        </main>
      </div>
    </AuthProvider>
  );
}
