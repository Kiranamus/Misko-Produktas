import test from "node:test";
import assert from "node:assert/strict";

globalThis.localStorage = {
  getItem: () => null,
  removeItem: () => {},
};
globalThis.window = { location: { href: "" } };

const authApi = await import("./authApi.js");
const { API } = await import("../api.js");

test("auth API helpers post to expected endpoints", async () => {
  const calls = [];
  API.post = async (url, payload) => {
    calls.push([url, payload]);
    return { data: { url, payload } };
  };

  assert.deepEqual(await authApi.loginUser({ username: "a" }), {
    url: "/login",
    payload: { username: "a" },
  });
  assert.deepEqual(await authApi.registerUser({ email: "a" }), {
    url: "/register",
    payload: { email: "a" },
  });
  assert.deepEqual(await authApi.requestPasswordReset("a@example.com"), {
    url: "/forgot-password",
    payload: { username: "a@example.com" },
  });
  assert.deepEqual(await authApi.resetPassword({ token: "t" }), {
    url: "/reset-password",
    payload: { token: "t" },
  });
  assert.equal(calls.length, 4);
});

test("getAuthErrorMessage prefers backend detail over fallback", () => {
  assert.equal(
    authApi.getAuthErrorMessage({ response: { data: { detail: "Blogai" } } }, "Fallback"),
    "Blogai",
  );
  assert.equal(authApi.getAuthErrorMessage({}, "Fallback"), "Fallback");
});

test("getAuthErrorMessage translates known backend auth details", () => {
  const t = (key) => ({
    authEmailExists: "A user with this email address already exists.",
    strongPassword: "Password rules",
  }[key] || key);

  assert.equal(
    authApi.getAuthErrorMessage(
      { response: { data: { detail: "Naudotojas su šiuo el. pašto adresu jau egzistuoja." } } },
      "Fallback",
      t,
    ),
    "A user with this email address already exists.",
  );

  assert.equal(
    authApi.getAuthErrorMessage(
      { response: { data: { detail: "Slaptažodis turi būti bent 8 simbolių, turėti bent vieną didžiąją raidę, bent vieną skaičių ir bent vieną specialų simbolį." } } },
      "Fallback",
      t,
    ),
    "Password rules",
  );
});
