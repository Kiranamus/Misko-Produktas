/* eslint-disable react-refresh/only-export-components */
import React, { createContext, useContext, useCallback, useEffect, useRef, useState } from "react";
import { clearStoredAuth, loadStoredAuth, storeAuth } from "../services/authStorage";
import { API } from "../api";

const AuthContext = createContext();
const IDLE_TIMEOUT_MS = 4 * 60 * 60 * 1000;
const REFRESH_CHECK_MS = 5 * 60 * 1000;
const REFRESH_BEFORE_EXP_MS = 20 * 60 * 1000;

function getTokenExpiresAt(token) {
  if (!token) return null;

  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return payload.exp ? payload.exp * 1000 : null;
  } catch (error) {
    console.error("Nepavyko nuskaityti prisijungimo tokeno:", error);
    return null;
  }
}

export function useAuth() {
  return useContext(AuthContext);
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [purchasedPlans, setPurchasedPlans] = useState([]);
  const [activePlan, setActivePlan] = useState(null);
  const [hasActivePlan, setHasActivePlan] = useState(false);
  const [loading, setLoading] = useState(true);
  const lastActivityRef = useRef(0);

  const fetchUserPlans = async (token) => {
    if (!token) return;

    try {
      const response = await API.get('/api/user-plans', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setPurchasedPlans(response.data.purchased_plans || []);
      setActivePlan(response.data.active_plan || response.data.purchased_plans?.[0] || null);
    } catch (error) {
      console.error("Nepavyko gauti naudotojo planų:", error);
      setPurchasedPlans([]);
      setActivePlan(null);
    }
  };

  const getPurchasedCounty = () => {
    return localStorage.getItem("purchased_county");
  };

  const fetchHasActivePlan = async (token) => {
    if (!token) return;

    try {
      const response = await API.get('/api/has-active-plan', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setHasActivePlan(response.data.has_active_plan || false);
    } catch (error) {
      console.error("Nepavyko patikrinti aktyvaus plano:", error);
      setHasActivePlan(false);
    }
  };

  const recordPurchase = async (planId, transactionId) => {
    const token = localStorage.getItem('token');
    if (!token) {
      throw new Error("Prisijunkite ir bandykite dar kartą.");
    }

    try {
      const response = await API.post('/api/record-purchase',
        { plan_id: planId, transaction_id: transactionId },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      if (response.data.success) {
        await refreshPlanState(token);
      }

      return response.data;
    } catch (error) {
      console.error("Nepavyko įrašyti pirkimo:", error);
      throw error;
    }
  };

  const refreshPlanState = async (token) => {
    await Promise.all([
      fetchUserPlans(token),
      fetchHasActivePlan(token),
    ]);
  };

  const cancelActivePlan = async () => {
    const token = localStorage.getItem("token");
    if (!token) {
      throw new Error("Prisijunkite ir bandykite dar kartą.");
    }

    const response = await API.post("/api/cancel-active-plan", {}, {
      headers: { Authorization: `Bearer ${token}` }
    });

    await refreshPlanState(token);
    return response.data;
  };

  const isPlanPurchased = (planId) => {
    return purchasedPlans.includes(planId);
  };

  const login = async (token, userData) => {
    storeAuth(token, userData);
    setUser(userData);
    lastActivityRef.current = Date.now();

    await refreshPlanState(token);
  };

  const logout = useCallback(() => {
    clearStoredAuth();
    setUser(null);
    setPurchasedPlans([]);
    setActivePlan(null);
    setHasActivePlan(false);
  }, []);

  const refreshSession = useCallback(async () => {
    const token = localStorage.getItem("token");
    if (!token) return false;

    try {
      const response = await API.post("/refresh-token", {});
      const nextToken = response.data.access_token;
      const nextUser = response.data.user;

      storeAuth(nextToken, nextUser);
      setUser(nextUser);
      return true;
    } catch (error) {
      console.error("Nepavyko atnaujinti prisijungimo sesijos:", error);
      return false;
    }
  }, []);

  useEffect(() => {
    const loadUserData = async () => {
      setLoading(true);
      const { token, user: storedUser } = loadStoredAuth();

      if (token && storedUser) {
        setUser(storedUser);
        await refreshPlanState(token);
      }

      setLoading(false);
    };

    loadUserData();
    // Pradinį naudotojo atkūrimą iš localStorage vykdome tik kartą po app užkrovimo.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const value = {
    user,
    login,
    logout,
    purchasedPlans,
    activePlan,
    hasActivePlan,
    isPlanPurchased,
    recordPurchase,
    cancelActivePlan,
    getPurchasedCounty,
    isAuthenticated: !!user,
    loading
  };

  useEffect(() => {
    const checkTokenExpiration = () => {
      const token = localStorage.getItem("token");
      const exp = getTokenExpiresAt(token);

      if (exp && Date.now() >= exp) {
        logout();
        window.location.href = "/login";
      }
    };

    checkTokenExpiration();

    const interval = setInterval(checkTokenExpiration, 60000);

    return () => clearInterval(interval);
  }, [logout]);

  useEffect(() => {
    const recordActivity = () => {
      lastActivityRef.current = Date.now();
    };

    recordActivity();

    const activityEvents = ["click", "keydown", "mousemove", "scroll", "touchstart"];
    activityEvents.forEach((eventName) => {
      window.addEventListener(eventName, recordActivity, { passive: true });
    });

    return () => {
      activityEvents.forEach((eventName) => {
        window.removeEventListener(eventName, recordActivity);
      });
    };
  }, []);

  useEffect(() => {
    const maybeRefreshSession = async () => {
      const token = localStorage.getItem("token");
      const exp = getTokenExpiresAt(token);
      const isRecentlyActive = Date.now() - lastActivityRef.current < IDLE_TIMEOUT_MS;

      if (!token || !exp || !isRecentlyActive) return;

      if (exp - Date.now() <= REFRESH_BEFORE_EXP_MS) {
        await refreshSession();
      }
    };

    const interval = setInterval(maybeRefreshSession, REFRESH_CHECK_MS);
    return () => clearInterval(interval);
  }, [refreshSession]);

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}
