import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { clearStoredAuth, loadStoredAuth, storeAuth } from "../services/authStorage";

const AuthContext = createContext();

export function useAuth() {
  return useContext(AuthContext);
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);

  useEffect(() => {
    const { token, user: storedUser } = loadStoredAuth();
    if (token && storedUser) {
      setUser(storedUser);
    }
  }, []);

  const login = (token, userData) => {
    storeAuth(token, userData);
    setUser(userData);
  };

  const logout = () => {
    clearStoredAuth();
    setUser(null);
  };

  const value = useMemo(
    () => ({ user, login, logout, isAuthenticated: !!user }),
    [user]
  );

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}
