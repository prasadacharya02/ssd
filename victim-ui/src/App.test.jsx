import React from "react";
import { beforeEach, expect, test, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "./main";
let vault;
beforeEach(() => {
  vault = false;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (path, options) => {
      let data,
        status = 200;
      if (path === "/api/vault/status") data = { unlocked: vault };
      else if (path === "/api/folders")
        data = [
          "Documents",
          "Downloads",
          "Desktop",
          "Pictures",
          "Quarantine",
        ].map((name) => ({
          name,
          file_count: 2,
          size: "1 KB",
          locked: name === "Quarantine" && !vault,
        }));
      else if (path === "/api/vault/login") {
        vault = JSON.parse(options.body).pin === "1234";
        data = vault ? { ok: true } : { message: "Denied" };
        status = vault ? 200 : 403;
      } else if (path === "/api/vault/logout") {
        vault = false;
        data = { ok: true };
      } else if (path.startsWith("/api/files/"))
        data = [
          {
            name: "report.txt",
            size: "1 KB",
            modified: "2026-09-29",
            extension: ".txt",
          },
        ];
      else if (path.startsWith("/api/file/"))
        data = { content: "Preview content" };
      return { ok: status === 200, status, json: async () => data };
    }),
  );
});
test("shows exact simulation counts, icons, badge and disabled write actions", async () => {
  render(<App />);
  expect(screen.getByText("6 items - 7.2 KB")).toBeInTheDocument();
  expect(screen.getByText("4 items - 161.2 KB")).toBeInTheDocument();
  expect(screen.getByText("4 items - 13.1 KB")).toBeInTheDocument();
  expect(screen.getByText("4 items - 900.1 KB")).toBeInTheDocument();
  expect(screen.getByText("18 items")).toBeInTheDocument();
  expect(screen.getByText("Locked")).toBeInTheDocument();
  expect(
    screen.getByText("Ransomware Shield - Monitoring"),
  ).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Rename" })).toBeDisabled();
  await waitFor(() =>
    expect(fetch).toHaveBeenCalledWith("/api/folders", undefined),
  );
});
test("search, live data switch, folder navigation and file preview", async () => {
  const user = userEvent.setup();
  render(<App />);
  await user.type(
    screen.getByRole("textbox", { name: "Search This PC" }),
    "Documents",
  );
  expect(screen.queryByText("4 items - 161.2 KB")).not.toBeInTheDocument();
  await user.selectOptions(screen.getByRole("combobox"), "live");
  expect(await screen.findByText("2 items - 1 KB")).toBeInTheDocument();
  await user.click(
    within(screen.getByRole("main")).getByRole("button", { name: /Documents/ }),
  );
  await user.click(await screen.findByRole("button", { name: /report.txt/ }));
  expect(await screen.findByText("Preview content")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Close dialog" }));
  await user.click(screen.getByRole("button", { name: "Back" }));
  expect(screen.getByRole("textbox", { name: "Search This PC" })).toHaveValue(
    "",
  );
});
test("vault rejects invalid PIN, unlocks and relocks", async () => {
  const user = userEvent.setup();
  render(<App />);
  await user.click(screen.getByRole("button", { name: "Vault Login" }));
  await user.type(screen.getByLabelText("PIN / Password"), "wrong");
  await user.click(screen.getByRole("button", { name: "Unlock Vault" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Incorrect");
  await user.clear(screen.getByLabelText("PIN / Password"));
  await user.type(screen.getByLabelText("PIN / Password"), "1234");
  await user.click(screen.getByRole("button", { name: "Unlock Vault" }));
  expect(
    await screen.findByRole("button", { name: "Lock Vault" }),
  ).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Lock Vault" }));
  expect(await screen.findByText("This folder is locked")).toBeInTheDocument();
});
test("native controls maximize, minimize, restore and close the simulated window", async () => {
  const user = userEvent.setup();
  render(<App />);
  await user.click(screen.getByRole("button", { name: "Maximize" }));
  expect(screen.getByRole("button", { name: "Restore" })).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Minimize" }));
  expect(screen.getByText("File Explorer minimized")).toBeInTheDocument();
  await user.click(
    screen.getByRole("button", { name: "Open File Explorer", exact: true }),
  );
  await user.click(screen.getByRole("button", { name: "Close", exact: true }));
  expect(screen.getByText("File Explorer closed")).toBeInTheDocument();
});
test("network failure is visible and offers retry", async () => {
  fetch.mockRejectedValue(new Error("Offline"));
  render(<App />);
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Connection unavailable",
  );
  expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
});
