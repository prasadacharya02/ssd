import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { Icon, FolderIcon } from "./icons";
import "./styles.css";

const samples = [
  { name: "Documents", file_count: 6, size: "7.2 KB" },
  { name: "Downloads", file_count: 4, size: "161.2 KB" },
  { name: "Desktop", file_count: 4, size: "13.1 KB" },
  { name: "Pictures", file_count: 4, size: "900.1 KB" },
  { name: "Quarantine", locked: true },
  { name: "Local Disk (C:)", file_count: 18 },
];
const navIcons = {
  Home: "home",
  Desktop: "pc",
  Downloads: "download",
  Documents: "document",
  Pictures: "picture",
  "This PC": "pc",
  Quarantine: "lock",
  "Local Disk (C:)": "pc",
};
/**
 * Vault credential, mirrored from the login response.
 *
 * The session cookie is the primary mechanism, but browsers withhold
 * cookies from an embedded (iframe) view and block third-party cookies
 * outright in some configurations — in which case the PIN would be accepted
 * and the vault would then render empty. Keeping the signed token here and
 * replaying it in a header makes the unlock independent of cookie policy.
 */
const VAULT_TOKEN_KEY = "entropy.vault.token";
let vaultToken =
  (typeof sessionStorage !== "undefined" &&
    sessionStorage.getItem(VAULT_TOKEN_KEY)) ||
  "";

function setVaultToken(token) {
  vaultToken = token || "";
  try {
    if (vaultToken) sessionStorage.setItem(VAULT_TOKEN_KEY, vaultToken);
    else sessionStorage.removeItem(VAULT_TOKEN_KEY);
  } catch {
    /* private mode / storage disabled — the in-memory copy still works */
  }
}

async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (vaultToken) headers["X-Vault-Token"] = vaultToken;
  const res = await fetch(path, { ...options, headers });
  const data = await res.json();
  if (!res.ok) {
    const error = new Error(
      data.message || data.error || "Unable to load files.",
    );
    error.status = res.status;
    throw error;
  }
  return data;
}
function Dialog({ title, close, children }) {
  const ref = useRef(null);
  useEffect(() => {
    const previous = document.activeElement;
    ref.current.showModal();
    return () => previous?.focus();
  }, []);
  return (
    <dialog
      ref={ref}
      onCancel={close}
      onClick={(e) => {
        if (e.target === ref.current) close();
      }}
      className="dialog w-[560px] max-w-[92vw] rounded-lg border border-slate-200 bg-white p-0 text-sm"
      aria-label={title}
    >
      <div className="flex items-center justify-between border-b border-slate-200 px-5 py-3">
        <h2 className="truncate font-semibold">{title}</h2>
        <button
          className="nav-button"
          aria-label="Close dialog"
          onClick={close}
        >
          <Icon name="close" />
        </button>
      </div>
      {children}
    </dialog>
  );
}
export function App() {
  const [folder, setFolder] = useState("This PC"),
    [history, setHistory] = useState(["This PC"]),
    [position, setPosition] = useState(0);
  const [folders, setFolders] = useState([]),
    [files, setFiles] = useState([]),
    [query, setQuery] = useState("");
  // Default to the REAL filesystem. The simulation layout exists only as an
  // optional presentation aid; opening on hardcoded sample counts made the
  // estate look unchanged no matter what the pipeline did.
  const [sample, setSample] = useState(false),
    [unlocked, setUnlocked] = useState(false),
    [error, setError] = useState("");
  const [busy, setBusy] = useState(false),
    [revision, setRevision] = useState(0),
    [dialog, setDialog] = useState(null);
  const [pin, setPin] = useState(""),
    [username, setUsername] = useState("victim_user"),
    [authError, setAuthError] = useState(""),
    [authBusy, setAuthBusy] = useState(false);
  const [clock, setClock] = useState(new Date()),
    [maximized, setMaximized] = useState(false),
    [windowState, setWindowState] = useState("open");
  const home =
    folder === "This PC" || folder === "Home" || folder === "Local Disk (C:)";
  useEffect(() => {
    const t = setInterval(() => setClock(new Date()), 1000);
    return () => clearInterval(t);
  }, []);
  useEffect(() => {
    let active = true,
      fetching = false;
    async function load() {
      if (fetching) return;
      fetching = true;
      try {
        const [vault, listing] = await Promise.all([
          api("/api/vault/status"),
          api("/api/folders"),
        ]);
        if (!active) return;
        setUnlocked(vault.unlocked);
        setFolders(listing);
        if (folder === "Quarantine" && !vault.unlocked)
          setDialog((d) => (d?.type === "preview" ? null : d));
        if (!home && (folder !== "Quarantine" || vault.unlocked)) {
          const result = await api("/api/files/" + encodeURIComponent(folder));
          if (active) setFiles(result);
        } else if (active) setFiles([]);
        if (active) setError("");
      } catch (e) {
        if (active) {
          setError("Connection unavailable. " + e.message);
          setFiles([]);
          if (e.status === 401) {
            setVaultToken("");
            setUnlocked(false);
            setDialog(null);
          }
        }
      } finally {
        fetching = false;
        if (active) setBusy(false);
      }
    }
    setBusy(true);
    setFiles([]);
    load();
    const timer = setInterval(load, 3000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [folder, revision]);
  function navigate(name) {
    setFolder(name);
    setQuery("");
    setHistory((h) => [...h.slice(0, position + 1), name]);
    setPosition(position + 1);
  }
  function move(delta) {
    const i = position + delta;
    if (i < 0 || i >= history.length) return;
    setPosition(i);
    setFolder(history[i]);
    setQuery("");
  }
  function loginDialog() {
    setAuthError("");
    setPin("");
    setDialog({ type: "login" });
  }
  async function vaultAction() {
    if (!unlocked) return loginDialog();
    try {
      await api("/api/vault/logout", { method: "POST" });
      setVaultToken("");
      setUnlocked(false);
      setFiles([]);
      setDialog(null);
      setRevision((x) => x + 1);
    } catch (e) {
      setError(e.message);
    }
  }
  async function login(e) {
    e.preventDefault();
    setAuthBusy(true);
    setAuthError("");
    try {
      const result = await api("/api/vault/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, pin }),
      });
      setVaultToken(result.token);
      setUnlocked(true);
      setDialog(null);
      navigate("Quarantine");
      setRevision((x) => x + 1);
    } catch (e) {
      setAuthError(
        e.status === 403
          ? "Incorrect username or PIN. Please try again."
          : e.message,
      );
    } finally {
      setAuthBusy(false);
    }
  }
  async function preview(file) {
    setDialog({ type: "preview", title: file.name, content: "Loading…" });
    try {
      const data = await api(
        `/api/file/${encodeURIComponent(folder)}/${encodeURIComponent(file.name)}`,
      );
      setDialog((d) =>
        d?.title === file.name
          ? {
              ...d,
              content:
                data.content + (data.truncated ? "\n\n… [truncated]" : ""),
            }
          : d,
      );
    } catch (e) {
      if (e.status === 401) {
        setVaultToken("");
        setUnlocked(false);
        loginDialog();
      } else
        setDialog((d) =>
          d?.title === file.name ? { ...d, content: e.message } : d,
        );
    }
  }
  const liveCards = [
    ...folders,
    {
      name: "Local Disk (C:)",
      file_count: folders
        .filter((f) => f.name !== "Quarantine")
        .reduce((n, f) => n + f.file_count, 0),
    },
  ];
  const cards = (sample ? samples : liveCards).filter((f) =>
    f.name.toLowerCase().includes(query.toLowerCase()),
  );
  const filtered = files.filter((f) =>
    f.name.toLowerCase().includes(query.toLowerCase()),
  );
  return (
    <div
      className={`flex min-h-dvh flex-col items-center justify-center ${maximized ? "" : "px-0 md:px-8"}`}
    >
      {windowState === "open" ? (
        <section
          aria-label="File Explorer"
          className={`window relative w-full max-w-[1240px] overflow-hidden rounded-lg border border-slate-200 bg-white ${maximized ? "maximized !max-w-none" : ""}`}
        >
          <header className="absolute inset-x-0 top-0 flex h-11 items-center justify-between border-b border-slate-200 bg-[#f8f8f8] pl-4">
            <div className="flex items-center gap-2 text-xs">
              <span className="text-[#d49b20]">
                <Icon name="document" size={16} />
              </span>
              {folder}
              <span className="ml-5 hidden text-slate-400 sm:inline">
                File Explorer
              </span>
            </div>
            <div className="flex h-full">
              {[
                ["minimize", "Minimize", () => setWindowState("minimized")],
                [
                  maximized ? "restore" : "maximize",
                  maximized ? "Restore" : "Maximize",
                  () => setMaximized((v) => !v),
                ],
                ["close", "Close", () => setWindowState("closed")],
              ].map(([icon, label, action]) => (
                <button
                  key={label}
                  aria-label={label}
                  title={label}
                  className={`flex w-12 items-center justify-center ${icon === "close" ? "hover:bg-[#c42b1c] hover:text-white" : "hover:bg-slate-200"}`}
                  onClick={action}
                >
                  <Icon name={icon} size={14} />
                </button>
              ))}
            </div>
          </header>
          <div
            className="absolute inset-x-0 top-11 flex h-[61px] items-center gap-1 overflow-x-auto border-b border-slate-200 px-4"
            aria-label="Command bar"
          >
            <button
              className="tool"
              disabled
              title="This explorer is read-only"
            >
              <Icon name="plus" />
              New
              <Icon name="down" size={11} />
            </button>
            <div className="mx-2 h-5 border-l border-slate-200" />
            {["Cut", "Copy", "Paste", "Rename"].map((label) => (
              <button
                key={label}
                className="tool"
                disabled
                title={`${label} is unavailable in this read-only simulation`}
              >
                <Icon name={label.toLowerCase()} />
                <span className="hidden lg:inline">{label}</span>
              </button>
            ))}
            <div className="mx-2 h-5 border-l border-slate-200" />
            <button className="tool" onClick={() => setRevision((x) => x + 1)}>
              <Icon name="refresh" />
              Refresh
            </button>
            <button
              className="tool font-medium text-amber-700"
              onClick={vaultAction}
            >
              <Icon name="lock" />
              {unlocked ? "Lock Vault" : "Vault Login"}
            </button>
            <select
              aria-label="Folder summary data source"
              value={sample ? "sample" : "live"}
              onChange={(e) => setSample(e.target.value === "sample")}
              className="ml-auto rounded border border-slate-200 bg-white px-2 py-1.5 text-xs text-slate-500"
            >
              <option value="sample">Simulation layout</option>
              <option value="live">Live filesystem</option>
            </select>
          </div>
          <div className="absolute inset-x-0 top-[105px] flex h-[59px] items-center gap-2 border-b border-slate-200 px-4">
            <button
              className="nav-button"
              aria-label="Back"
              disabled={!position}
              onClick={() => move(-1)}
            >
              <Icon name="left" size={16} />
            </button>
            <button
              className="nav-button hidden sm:flex"
              aria-label="Forward"
              disabled={position === history.length - 1}
              onClick={() => move(1)}
            >
              <Icon name="right" size={16} />
            </button>
            <button
              className="nav-button"
              aria-label="Up to This PC"
              disabled={home}
              onClick={() => navigate("This PC")}
            >
              <Icon name="up" size={16} />
            </button>
            <div className="flex h-8 min-w-0 flex-1 items-center gap-3 rounded border border-slate-200 px-3 text-xs">
              <span className="text-blue-600">
                <Icon name="pc" size={16} />
              </span>
              <button className="shrink-0" onClick={() => navigate("This PC")}>
                This PC
              </button>
              {!home && (
                <>
                  <Icon name="chevron" size={11} />
                  <span className="truncate">{folder}</span>
                </>
              )}
            </div>
            <label className="relative w-[36%] max-w-[250px]">
              <input
                aria-label={`Search ${folder}`}
                className="h-8 w-full rounded border border-slate-200 pl-3 pr-8 text-xs outline-none focus:border-blue-500"
                placeholder={`Search ${folder}`}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
              <span className="pointer-events-none absolute right-3 top-2 text-slate-400">
                <Icon name="search" size={14} />
              </span>
            </label>
          </div>
          <aside
            aria-label="Navigation"
            className="absolute bottom-8 left-0 top-[164px] w-[64px] border-r border-slate-200 bg-[#fafafa] px-2 py-4 sm:w-[190px]"
          >
            {[
              "Home",
              "Desktop",
              "Downloads",
              "Documents",
              "Pictures",
              "This PC",
              "Quarantine",
              "Local Disk (C:)",
            ].map((name, i) => (
              <React.Fragment key={name}>
                {(i === 1 || i === 5) && (
                  <div className="my-3 border-t border-slate-200" />
                )}
                <button
                  title={name}
                  onClick={() => navigate(name)}
                  className={`side-item ${folder === name ? "active" : ""}`}
                  aria-current={folder === name ? "page" : undefined}
                >
                  <span
                    className={
                      name === "Quarantine"
                        ? "text-blue-600"
                        : name === "This PC"
                          ? "text-blue-500"
                          : "text-slate-500"
                    }
                  >
                    <Icon name={navIcons[name]} size={17} />
                  </span>
                  <span className="hidden truncate sm:block">{name}</span>
                  {name === "Quarantine" && !unlocked && (
                    <span className="ml-auto hidden sm:block">
                      <Icon name="lock" size={11} />
                    </span>
                  )}
                </button>
              </React.Fragment>
            ))}
          </aside>
          <main className="absolute bottom-8 left-[64px] right-0 top-[164px] flex flex-col sm:left-[190px]">
            <div className="flex min-h-[64px] shrink-0 flex-wrap items-center justify-between gap-2 px-6 py-3">
              <h1 className="text-sm font-semibold">
                {home ? "Folders" : folder}
                {home && (
                  <span className="ml-2 font-normal text-slate-400">
                    ({cards.length})
                  </span>
                )}
              </h1>
              <span
                title="Simulation indicator; not a defender health attestation"
                className="flex items-center gap-2 rounded-full border border-blue-100 bg-blue-50 px-3 py-1.5 text-[11px] font-medium text-blue-700"
              >
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-blue-500" />
                Ransomware Shield - Monitoring
              </span>
            </div>
            <div
              className="min-h-0 flex-1 overflow-y-auto px-5 pb-6"
              aria-busy={busy}
            >
              {error && (
                <div
                  role="alert"
                  className="mb-4 rounded border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800"
                >
                  {error}{" "}
                  <button
                    className="underline"
                    onClick={() => setRevision((x) => x + 1)}
                  >
                    Retry
                  </button>
                </div>
              )}
              {home ? (
                <>
                  <div className="grid grid-cols-2 gap-x-3 gap-y-4 md:grid-cols-3 xl:grid-cols-6">
                    {cards.map((item) => (
                      <button
                        key={item.name}
                        className="folder-tile"
                        onClick={() => navigate(item.name)}
                      >
                        <FolderIcon type={item.name} />
                        <span className="mb-1.5 text-[13px]">{item.name}</span>
                        <span className="text-xs text-slate-500">
                          {item.name === "Quarantine" && !unlocked
                            ? "Locked"
                            : item.name === "Quarantine"
                              ? `${folders.find((f) => f.name === "Quarantine")?.file_count || 0} items`
                              : `${item.file_count} items${item.size ? " - " + item.size : ""}`}
                        </span>
                      </button>
                    ))}
                  </div>
                  {!cards.length && (
                    <p className="py-16 text-center text-sm text-slate-500">
                      {busy
                        ? "Loading folders…"
                        : "No folders match your search."}
                    </p>
                  )}
                </>
              ) : folder === "Quarantine" && !unlocked ? (
                <div className="mx-auto max-w-sm py-14 text-center">
                  <FolderIcon type="Quarantine" />
                  <h2 className="mb-2 text-base font-semibold">
                    This folder is locked
                  </h2>
                  <p className="mb-5 text-xs leading-6 text-slate-500">
                    Sign in to view the Quarantine folder.
                    <br />
                    Only the authorized endpoint user can access this vault.
                  </p>
                  <button
                    className="rounded bg-[#0078d4] px-5 py-2 text-xs text-white hover:bg-blue-700"
                    onClick={loginDialog}
                  >
                    Unlock Quarantine
                  </button>
                </div>
              ) : (
                <>
                  <div className="grid grid-cols-[minmax(0,1fr)_65px] md:grid-cols-[minmax(0,1fr)_130px_75px] border-y border-slate-200 py-2 text-xs text-slate-500">
                    <span>Name</span>
                    <span className="hidden md:block">Date modified</span>
                    <span>Size</span>
                  </div>
                  {filtered.map((file) => (
                    <button
                      key={file.name}
                      onClick={() => preview(file)}
                      className="grid w-full grid-cols-[minmax(0,1fr)_65px] md:grid-cols-[minmax(0,1fr)_130px_75px] items-center border-b border-slate-100 py-3 text-left text-xs hover:bg-blue-50"
                    >
                      <span className="flex min-w-0 items-center gap-2 pr-3">
                        <Icon name="document" size={18} />
                        <span className="truncate">
                          {file.original_name || file.name}
                        </span>
                      </span>
                      <span className="hidden text-slate-500 md:block">
                        {file.modified}
                      </span>
                      <span className="text-slate-500">{file.size}</span>
                    </button>
                  ))}
                  {!filtered.length && (
                    <p className="py-20 text-center text-sm text-slate-500">
                      {busy
                        ? "Loading…"
                        : query
                          ? "No files match your search."
                          : "This folder is empty."}
                    </p>
                  )}
                </>
              )}
            </div>
          </main>
          <footer className="absolute inset-x-0 bottom-0 flex h-8 items-center justify-between border-t border-slate-200 px-4 text-[11px] text-slate-500">
            <span>{home ? cards.length : filtered.length} items</span>
            <span className="truncate pl-3">
              {home && sample
                ? "Simulation layout · Sample folder counts"
                : "Live filesystem"}{" "}
              · Read-only
            </span>
          </footer>
        </section>
      ) : (
        <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4">
          <Icon name="pc" size={40} />
          <p className="text-sm text-slate-600">
            File Explorer {windowState === "closed" ? "closed" : "minimized"}
          </p>
          <button
            onClick={() => setWindowState("open")}
            className="rounded border border-slate-300 bg-white px-5 py-2 text-sm"
          >
            Open File Explorer
          </button>
        </div>
      )}
      <div
        className={`flex h-[38px] w-full items-center justify-between bg-[#1A1A1A] px-5 text-xs text-slate-300 ${maximized ? "" : "max-w-[1240px] md:mt-3 md:rounded"}`}
      >
        <button
          className="flex items-center gap-3"
          onClick={() => setWindowState("open")}
          title="Open File Explorer"
        >
          <span className="grid grid-cols-2 gap-[2px]">
            {[0, 1, 2, 3].map((i) => (
              <span key={i} className="h-[7px] w-[7px] bg-[#39aaf3]" />
            ))}
          </span>
          <span>Windows 11 - VICTIM-PC</span>
        </button>
        <time
          dateTime={clock.toISOString()}
          className="text-right tabular-nums"
        >
          <span className="hidden sm:inline">
            {clock.toLocaleDateString()} &nbsp;{" "}
          </span>
          {clock.toLocaleTimeString()}
        </time>
      </div>
      {dialog?.type === "login" && (
        <Dialog title="Quarantine Vault Login" close={() => setDialog(null)}>
          <form onSubmit={login} className="space-y-4 p-6">
            <FolderIcon type="Quarantine" />
            <p className="text-center text-xs text-slate-500">
              Authenticate to access the locked Quarantine folder.
            </p>
            <label className="block text-xs">
              Username
              <input
                autoFocus
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="mt-2 w-full rounded border border-slate-300 px-3 py-2 outline-blue-500"
              />
            </label>
            <label className="block text-xs">
              PIN / Password
              <input
                required
                type="password"
                autoComplete="current-password"
                value={pin}
                onChange={(e) => setPin(e.target.value)}
                className="mt-2 w-full rounded border border-slate-300 px-3 py-2 outline-blue-500"
              />
            </label>
            {authError && (
              <p role="alert" className="text-xs text-red-700">
                {authError}
              </p>
            )}
            <div className="flex justify-end gap-2">
              <button
                type="button"
                className="rounded border border-slate-200 px-4 py-2 text-xs"
                onClick={() => setDialog(null)}
              >
                Cancel
              </button>
              <button
                disabled={authBusy}
                className="rounded bg-[#0078d4] px-4 py-2 text-xs text-white"
              >
                {authBusy ? "Signing in…" : "Unlock Vault"}
              </button>
            </div>
          </form>
        </Dialog>
      )}
      {dialog?.type === "preview" && (
        <Dialog title={dialog.title} close={() => setDialog(null)}>
          <pre className="max-h-[60vh] overflow-auto whitespace-pre-wrap break-words bg-[#fafafa] p-5 text-xs leading-6">
            {dialog.content}
          </pre>
        </Dialog>
      )}
    </div>
  );
}
const root = document.getElementById("root");
if (root) createRoot(root).render(<App />);
