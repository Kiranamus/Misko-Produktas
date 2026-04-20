import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { clearStoredAuth, loadStoredAuth, storeAuth } from "../services/authStorage";
import { API } from "../api";

const AuthContext = createContext();

export function useAuth() {
  return useContext(AuthContext);
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [purchasedPlans, setPurchasedPlans] = useState([]);
  const [hasActivePlan, setHasActivePlan] = useState(false);
  const [loading, setLoading] = useState(true);

  // Fetch user's purchased plans
  const fetchUserPlans = async (token) => {
    if (!token) return;
    
    try {
      const response = await API.get('/api/user-plans', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setPurchasedPlans(response.data.purchased_plans || []);
    } catch (error) {
      console.error('Failed to fetch user plans:', error);
      setPurchasedPlans([]);
    }
  };

  // Check if user has any active plan
  const fetchHasActivePlan = async (token) => {
    if (!token) return;
    
    try {
      const response = await API.get('/api/has-active-plan', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setHasActivePlan(response.data.has_active_plan || false);
    } catch (error) {
      console.error('Failed to fetch active plan status:', error);
      setHasActivePlan(false);
    }
  };

  // Record a purchase after successful payment
  const recordPurchase = async (planId, transactionId) => {
    const token = localStorage.getItem('token');
    if (!token) {
      throw new Error('No authentication token found');
    }
    
    try {
      const response = await API.post('/api/record-purchase', 
        { plan_id: planId, transaction_id: transactionId },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      if (response.data.success) {
        // Refresh user's plans after successful purchase
        await fetchUserPlans(token);
        await fetchHasActivePlan(token);
      }
      
      return response.data;
    } catch (error) {
      console.error('Failed to record purchase:', error);
      throw error;
    }
  };

  // Check if a specific plan is purchased
  const isPlanPurchased = (planId) => {
    return purchasedPlans.includes(planId);
  };

  // Login function
  const login = async (token, userData) => {
    storeAuth(token, userData);
    setUser(userData);
    
    // Fetch user's plans after login
    await fetchUserPlans(token);
    await fetchHasActivePlan(token);
  };

  // Logout function
  const logout = () => {
    clearStoredAuth();
    setUser(null);
    setPurchasedPlans([]);
    setHasActivePlan(false);
  };

  // Load user data on initial mount
  useEffect(() => {
    const loadUserData = async () => {
      setLoading(true);
      const { token, user: storedUser } = loadStoredAuth();
      
      if (token && storedUser) {
        setUser(storedUser);
        await fetchUserPlans(token);
        await fetchHasActivePlan(token);
      }
      
      setLoading(false);
    };
    
    loadUserData();
  }, []);

  const value = useMemo(
    () => ({ 
      user, 
      login, 
      logout, 
      purchasedPlans,
      hasActivePlan,
      isPlanPurchased,
      recordPurchase,
      isAuthenticated: !!user,
      loading
    }),
    [user, purchasedPlans, hasActivePlan, loading]
  );

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}