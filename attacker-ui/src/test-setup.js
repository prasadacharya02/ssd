import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

afterEach(cleanup);

// Mirrors the runtime block the Python service injects into index.html, so
// tests exercise the same link/token resolution the browser gets.
window.__ENTROPY_CONSOLE__ = {
  token: "entropy-lab",
  victimUrl: "http://127.0.0.1:5001",
  dashboardUrl: "http://127.0.0.1:5000",
  attackerUrl: "http://127.0.0.1:8001",
};

window.open = vi.fn();
