import { test } from "node:test";
import assert from "node:assert/strict";
import { mockGetWeather, weatherArgs } from "../src/index.ts";

test("mock weather tool returns canned data (keyless)", () => {
  const out = mockGetWeather(weatherArgs.parse({ city: "Paris" }));
  assert.equal(out.temp_c, 18);
});
