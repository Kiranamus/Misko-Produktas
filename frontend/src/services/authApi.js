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

const AUTH_DETAIL_KEYS = new Map([
  ["Neteisingas prisijungimo tokenas.", "authInvalidToken"],
  ["Naudotojas nerastas.", "authUserNotFound"],
  [
    "Slaptažodis turi būti bent 8 simbolių, turėti bent vieną didžiąją raidę, bent vieną skaičių ir bent vieną specialų simbolį.",
    "strongPassword",
  ],
  ["Naudotojas su šiuo el. pašto adresu jau egzistuoja.", "authEmailExists"],
  ["Neteisingas el. paštas arba slaptažodis.", "authInvalidCredentials"],
  ["El. paštas nerastas duomenų bazėje.", "authEmailNotFound"],
  ["Nuoroda nebegalioja arba yra neteisinga.", "authResetLinkInvalid"],
  ["Paskyra sukurta sėkmingai. Dabar galite prisijungti.", "accountCreated"],
  ["Slaptažodis pakeistas sėkmingai.", "passwordChanged"],
  ["Invalid or expired token", "authResetLinkInvalid"],
  ["Invalid token", "authInvalidToken"],
  ["User not found", "authUserNotFound"],
  ["Field required", "fieldRequired"],
  ["value is not a valid email address", "invalidEmail"],
  ["Input should be a valid string", "invalidRequest"],
]);

function translateDetail(detail, t) {
  const translationKey = AUTH_DETAIL_KEYS.get(detail);
  return translationKey && t ? t(translationKey) : detail;
}

export function getAuthErrorMessage(error, fallbackMessage, t) {
  const detail = error.response?.data?.detail;

  if (Array.isArray(detail)) {
    const translatedMessages = detail.map((item) => translateDetail(item.msg, t));
    return [...new Set(translatedMessages)].join(" ");
  }

  return detail ? translateDetail(detail, t) : fallbackMessage;
}
