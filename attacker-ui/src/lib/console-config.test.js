/**
 * The console's "SOC" and "Victim PC" links must be reachable from wherever
 * the operator is standing.
 *
 * A hosted preview publishes each port as "<port>-<host>", and its proxy may
 * rewrite the Host header before the request reaches the service — so the
 * links are resolved in the browser from window.location instead of from
 * whatever the server saw. These tests pin both published shapes.
 */
import { afterEach, describe, expect, it } from "vitest";
import { siblingUrl } from "./console-config.js";

function setLocation({ protocol, hostname, port }) {
  Object.defineProperty(window, "location", {
    value: { protocol, hostname, port },
    writable: true,
    configurable: true,
  });
}

afterEach(() => {
  setLocation({ protocol: "http:", hostname: "localhost", port: "" });
});

describe("siblingUrl", () => {
  it("swaps the port on a plain host:port deployment", () => {
    setLocation({ protocol: "http:", hostname: "127.0.0.1", port: "8001" });
    expect(siblingUrl("5000")).toBe("http://127.0.0.1:5000");
    expect(siblingUrl("5001")).toBe("http://127.0.0.1:5001");
  });

  it("swaps the port label behind a port-labelled https proxy", () => {
    setLocation({ protocol: "https:", hostname: "8001-lab.e2b.app", port: "" });
    expect(siblingUrl("5000")).toBe("https://5000-lab.e2b.app");
    expect(siblingUrl("5001")).toBe("https://5001-lab.e2b.app");
  });

  it("keeps https when the page was served over https", () => {
    setLocation({ protocol: "https:", hostname: "8001-lab.e2b.app", port: "" });
    expect(siblingUrl("5000").startsWith("https://")).toBe(true);
  });

  it("never emits a wildcard bind address", () => {
    for (const hostname of ["127.0.0.1", "8001-lab.e2b.app", "lab.internal"]) {
      setLocation({ protocol: "http:", hostname, port: "8001" });
      expect(siblingUrl("5000")).not.toContain("0.0.0.0");
    }
  });

  it("falls back to the hostname when the port is unknown", () => {
    setLocation({ protocol: "https:", hostname: "console.example.com", port: "" });
    expect(siblingUrl("5000")).toBe("https://console.example.com:5000");
  });
});
