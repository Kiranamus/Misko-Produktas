import assert from "node:assert/strict";

import {
  clearStoredAuth,
  loadStoredAuth,
  storeAuth,
} from "./authStorage.js";


function createStorageMock() {
  const state = new Map();
  return {
    getItem(key) {
      return state.has(key) ? state.get(key) : null;
    },
    setItem(key, value) {
      state.set(key, String(value));
    },
    removeItem(key) {
      state.delete(key);
    },
    clear() {
      state.clear();
    },
  };
}


export function run() {
  globalThis.localStorage = createStorageMock();

  const user = { id: 1, name: "Matas" };

  storeAuth("jwt-token", user);

  assert.deepEqual(loadStoredAuth(), { token: "jwt-token", user });
 
  localStorage.clear();
  assert.deepEqual(loadStoredAuth(), { token: null, user: null });

  localStorage.setItem("token", "jwt-token");
  localStorage.setItem("user", "{broken-json");

  assert.deepEqual(loadStoredAuth(), { token: null, user: null });
  assert.equal(localStorage.getItem("token"), null);
  assert.equal(localStorage.getItem("user"), null);

  storeAuth("jwt-token", { id: 2 });

  clearStoredAuth();

  assert.deepEqual(loadStoredAuth(), { token: null, user: null });
  delete globalThis.localStorage;
}
