import { API } from "../api.js";

export async function loginUser(credentials) {
  const response = await API.post("/login", credentials);
  return response.data;
}

export async function registerUser(payload) {
  const response = await API.post("/register", payload);
  return response.data;
}

export async function requestPasswordReset(username) {
  const response = await API.post("/forgot-password", { username });
  return response.data;
}

export async function resetPassword(payload) {
  const response = await API.post("/reset-password", payload);
  return response.data;
}

export function getAuthErrorMessage(error, fallbackMessage) {
  return error.response?.data?.detail || fallbackMessage;
}
