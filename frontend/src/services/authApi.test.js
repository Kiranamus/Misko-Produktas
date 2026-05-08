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
