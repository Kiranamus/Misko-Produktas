import test from "node:test";
import assert from "node:assert/strict";

import { clearStoredAuth, loadStoredAuth, storeAuth } from "./authStorage.js";

function installLocalStorage() {
  const store = new Map();
  globalThis.localStorage = {
    getItem: (key) => (store.has(key) ? store.get(key) : null),
    setItem: (key, value) => store.set(key, String(value)),
    removeItem: (key) => store.delete(key),
  };
}

test("stored auth loads empty state without token or user", () => {
  installLocalStorage();

  assert.deepEqual(loadStoredAuth(), { token: null, user: null });
});

test("storeAuth and loadStoredAuth round-trip user data", () => {
  installLocalStorage();

  storeAuth("token", { id: 1, email: "a@example.com" });

  assert.deepEqual(loadStoredAuth(), {
    token: "token",
    user: { id: 1, email: "a@example.com" },
  });
});

test("loadStoredAuth clears invalid user JSON", () => {
  installLocalStorage();
  localStorage.setItem("token", "token");
  localStorage.setItem("user", "{bad json");

  assert.deepEqual(loadStoredAuth(), { token: null, user: null });
  assert.equal(localStorage.getItem("token"), null);
  assert.equal(localStorage.getItem("user"), null);
});

test("clearStoredAuth removes both auth keys", () => {
  installLocalStorage();
  storeAuth("token", { id: 1 });

  clearStoredAuth();

  assert.deepEqual(loadStoredAuth(), { token: null, user: null });
});
