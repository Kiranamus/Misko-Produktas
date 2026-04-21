import assert from "node:assert/strict";

import { getAuthErrorMessage } from "./authApi.js";


export function run() {
  const error = {
    response: {
      data: {
        detail: "Invalid credentials",
      },
    },
  };

  assert.equal(getAuthErrorMessage(error, "Fallback"), "Invalid credentials");
  assert.equal(getAuthErrorMessage({}, "Fallback"), "Fallback");
}
