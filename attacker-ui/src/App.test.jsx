import React from "react";
import { beforeEach, expect, test, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App.jsx";

const FAMILIES = [
  {
    id: "wannacry",
    name: "WannaCry (2017)",
    short_name: "WannaCry",
    extension: ".WNCRY",
    note: "@Please_Read_Me@.txt",
    speed: "10-50 files/sec",
    style: "Fast full-file simulation",
  },
  {
    id: "ryuk",
    name: "Ryuk (2019)",
    short_name: "Ryuk",
    extension: ".ryk",
    note: "RyukReadMe.html",
    speed: "2-5 files/sec",
    style: "Slow selective simulation",
  },
];

const ESTATE = {
  exists: true,
  total: 18,
  bytes: 1106510,
  attackable: 18,
  locked: 0,
  notes: 0,
  folders: [{ name: "Documents", files: 6, bytes: 7339 }],
  extensions: [{ ext: ".jpg", files: 4 }],
  quarantine_evidence: 3,
  backed_up: 18,
};

function stats(overrides = {}) {
  return {
    active: false,
    family: null,
    phase: "IDLE",
    paused: false,
    progress: 0,
    targets: 0,
    files_hit: 0,
    files_skipped: 0,
    notes_dropped: 0,
    bytes_encrypted: 0,
    files_per_second: 0,
    elapsed_seconds: 0,
    pid: null,
    exit_code: null,
    defender_killed: false,
    speed_factor: 1,
    log: [],
    victim: { exists: true, total: 18, locked: 0, notes: 0, bytes: 1106510 },
    ...overrides,
  };
}

let current;
let posts;

beforeEach(() => {
  current = stats();
  posts = [];

  vi.stubGlobal(
    "fetch",
    vi.fn(async (path, options = {}) => {
      const method = options.method || "GET";

      if (path === "/api/families") return json(FAMILIES);
      if (path === "/api/stats") return json(current);
      if (path === "/api/targets") return json(ESTATE);
      if (method === "POST") {
        posts.push({
          path,
          body: options.body ? JSON.parse(options.body) : null,
          headers: options.headers || {},
        });
        return json({ ok: true });
      }
      throw new Error(`unexpected request ${path}`);
    }),
  );
});

function json(data) {
  return { ok: true, status: 200, json: async () => data };
}

test("renders the payload catalog and idle telemetry from the service", async () => {
  render(<App />);

  expect(await screen.findByText("WannaCry (2017)")).toBeInTheDocument();
  expect(screen.getByText("Ryuk")).toBeInTheDocument();
  expect(screen.getByText(/No campaign running/i)).toBeInTheDocument();

  // Estate counters come from /api/targets.
  await waitFor(() => expect(screen.getByText("Attackable")).toBeInTheDocument());
  expect(screen.getByText("Evidence held")).toBeInTheDocument();
});

test("reports the defender kill verdict when the pipeline terminates the process", async () => {
  current = stats({
    phase: "KILLED_BY_DEFENDER",
    defender_killed: true,
    family: "wannacry",
    targets: 18,
    files_hit: 2,
    exit_code: 42,
    progress: 11.1,
    log: [
      {
        time: "14:02:07",
        at: Date.now() / 1000,
        msg: "!! TERMINATED BY DEFENSE SYSTEM (pid=1908 killed by defender)",
        level: "critical",
      },
    ],
  });

  render(<App />);

  expect(await screen.findByText(/Defense won this run/i)).toBeInTheDocument();
  expect(screen.getAllByText(/KILLED BY DEFENDER/i).length).toBeGreaterThan(0);
  expect(screen.getAllByText(/were never touched/i).length).toBeGreaterThan(0);
});

test("launch is a two-step confirmation and posts the selected family with the operator token", async () => {
  const user = userEvent.setup();
  render(<App />);

  const launch = await screen.findByRole("button", { name: /execute payload/i });
  await user.click(launch);

  expect(posts).toHaveLength(0);
  const confirm = screen.getByRole("button", { name: /confirm WannaCry launch/i });

  await user.click(confirm);

  await waitFor(() => expect(posts).toHaveLength(1));
  expect(posts[0].path).toBe("/api/launch");
  expect(posts[0].body).toEqual({ family: "wannacry" });
  expect(posts[0].headers.Authorization).toBe("Bearer entropy-lab");
});

test("selecting another payload targets that family", async () => {
  const user = userEvent.setup();
  render(<App />);

  await user.click(await screen.findByText("Ryuk"));
  await user.click(screen.getByRole("button", { name: /execute payload/i }));
  await user.click(screen.getByRole("button", { name: /confirm Ryuk launch/i }));

  await waitFor(() => expect(posts).toHaveLength(1));
  expect(posts[0].body).toEqual({ family: "ryuk" });
});

test("running campaigns expose abort and pause, and the log filter isolates errors", async () => {
  current = stats({
    active: true,
    family: "wannacry",
    phase: "ENCRYPTING",
    targets: 18,
    files_hit: 4,
    progress: 22.2,
    pid: 4242,
    log: [
      { time: "14:02:01", at: Date.now() / 1000, msg: "scan complete: 18 targets, 0 skipped", level: "info" },
      { time: "14:02:02", at: Date.now() / 1000, msg: "encrypting 1/18 Documents/Tax_Returns.pdf (1628 bytes)", level: "info" },
      { time: "14:02:03", at: Date.now() / 1000, msg: "Note failed: permission denied", level: "error" },
    ],
    speed_factor: 2,
  });

  const user = userEvent.setup();
  render(<App />);

  expect(await screen.findByRole("button", { name: /abort/i })).toBeEnabled();
  expect(screen.getByRole("button", { name: /pause/i })).toBeEnabled();
  expect(screen.queryByRole("button", { name: /confirm WannaCry launch/i })).toBeNull();

  const log = await screen.findByText(/scan complete: 18 targets/);
  expect(log).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: /Errors/ }));
  await waitFor(() =>
    expect(screen.queryByText(/scan complete: 18 targets/)).toBeNull(),
  );
  expect(screen.getByText(/Note failed: permission denied/)).toBeInTheDocument();
});

test("pause control issues a pause or resume request depending on state", async () => {
  current = stats({
    active: true,
    family: "wannacry",
    phase: "PAUSED",
    paused: true,
    targets: 18,
    files_hit: 2,
    pid: 4242,
  });

  const user = userEvent.setup();
  render(<App />);

  await user.click(await screen.findByRole("button", { name: /^Resume$/ }));
  await waitFor(() => expect(posts).toHaveLength(1));
  expect(posts[0].path).toBe("/api/resume");
});
