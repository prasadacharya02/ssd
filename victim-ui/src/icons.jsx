import React from "react";
export function Icon({ name, size = 18, ...props }) {
  const paths = {
    plus: <path d="M12 5v14M5 12h14" />,
    cut: (
      <>
        <circle cx="6" cy="17" r="3" />
        <circle cx="6" cy="7" r="3" />
        <path d="m8.5 8.5 11 11m-11-4 11-11" />
      </>
    ),
    copy: (
      <>
        <rect x="8" y="8" width="12" height="13" rx="2" />
        <path d="M15 8V3H3v13h5" />
      </>
    ),
    paste: (
      <>
        <rect x="5" y="5" width="14" height="16" rx="2" />
        <rect x="9" y="2" width="6" height="5" rx="1" />
      </>
    ),
    rename: (
      <>
        <path d="M4 7H2v11h7m6-11h7v11h-7M9 3h6m-3 0v18m-3 0h6" />
      </>
    ),
    refresh: (
      <>
        <path d="M20 7v5h-5M4 17v-5h5" />
        <path d="M6 7a7 7 0 0 1 12-1l2 6M4 12l2 6a7 7 0 0 0 12-1" />
      </>
    ),
    lock: (
      <>
        <rect x="5" y="10" width="14" height="11" rx="2" />
        <path d="M8 10V6a4 4 0 0 1 8 0v4m-4 4v3" />
      </>
    ),
    home: (
      <>
        <path d="m3 10 9-7 9 7v11h-7v-7h-4v7H3Z" />
      </>
    ),
    pc: (
      <>
        <rect x="3" y="3" width="18" height="13" rx="1" />
        <path d="M12 16v5m-5 0h10" />
      </>
    ),
    download: (
      <>
        <path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5" />
      </>
    ),
    document: (
      <>
        <path d="M5 2h9l5 5v15H5Zm9 0v6h5M8 12h8m-8 4h8" />
      </>
    ),
    picture: (
      <>
        <rect x="3" y="3" width="18" height="18" rx="2" />
        <circle cx="8" cy="8" r="2" />
        <path d="m3 18 6-6 4 3 4-6 4 5" />
      </>
    ),
    left: <path d="m14 5-7 7 7 7M7 12h14" />,
    right: <path d="m10 5 7 7-7 7M3 12h14" />,
    up: <path d="m5 10 7-7 7 7M12 3v18" />,
    chevron: <path d="m9 5 7 7-7 7" />,
    down: <path d="m5 9 7 7 7-7" />,
    search: (
      <>
        <circle cx="10" cy="10" r="7" />
        <path d="m15 15 6 6" />
      </>
    ),
    close: <path d="m6 6 12 12M6 18 18 6" />,
    minimize: <path d="M5 12h14" />,
    maximize: <rect x="5" y="5" width="14" height="14" />,
    restore: (
      <>
        <path d="M9 7V3h12v12h-4" />
        <rect x="3" y="7" width="14" height="14" />
      </>
    ),
    grid: (
      <>
        <path d="M3 3h7v7H3Zm11 0h7v7h-7ZM3 14h7v7H3Zm11 0h7v7h-7Z" />
      </>
    ),
  };
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...props}
    >
      {paths[name] || paths.document}
    </svg>
  );
}
export function FolderIcon({ type }) {
  if (type === "Quarantine")
    return (
      <svg viewBox="0 0 80 72" className="folder-icon" aria-hidden="true">
        <path
          d="M36 5 62 15v19c0 16-12 27-26 34C22 61 10 50 10 34V15Z"
          fill="#1685d5"
        />
        <path d="m36 10 21 9v15c0 13-9 22-21 29Z" fill="#0874bf" />
        <path
          d="M29 37V26a9 9 0 0 1 18 0v11"
          fill="none"
          stroke="#edf7ff"
          strokeWidth="5"
        />
        <rect
          x="23"
          y="34"
          width="30"
          height="24"
          rx="4"
          fill="#f8c94b"
          stroke="#dcaa29"
        />
        <circle cx="38" cy="44" r="3" fill="#956517" />
        <path d="M38 44v7" stroke="#956517" strokeWidth="3" />
      </svg>
    );
  if (type === "Local Disk (C:)")
    return (
      <svg viewBox="0 0 80 72" className="folder-icon" aria-hidden="true">
        <path d="m14 25 49-1 11 29H5Z" fill="#cdd7e2" stroke="#97a6b6" />
        <path d="m17 28 42-1 6 18H12Z" fill="#eef2f6" />
        <rect x="5" y="49" width="69" height="15" rx="3" fill="#aab8c9" />
        <path d="M10 55h34" stroke="#788ba2" strokeWidth="2" />
        <circle cx="66" cy="56" r="2" fill="#43a891" />
        <path
          d="m26 30 9-1v8h-9Zm11-1 9-1v9h-9ZM26 39h9v8l-9-1Zm11 0h9v9l-9-1Z"
          fill="#168ce3"
        />
      </svg>
    );
  return (
    <svg viewBox="0 0 80 72" className="folder-icon" aria-hidden="true">
      <path d="M5 16q0-4 4-4h23l8 8h30q4 0 4 4v36H5Z" fill="#dda426" />
      <path d="M10 24h60v30H10Z" fill="#fff2c2" />
      <path
        d="M5 29q0-4 4-4h23l6 5h32q4 0 4 4v27q0 4-4 4H9q-4 0-4-4Z"
        fill="#f5c64a"
      />
      <path d="M5 34h69v27q0 4-4 4H9q-4 0-4-4Z" fill="#ffd45b" />
      <g transform="translate(41 39)" color="#aa7c17">
        <foreignObject width="25" height="25">
          <Icon
            name={
              {
                Documents: "document",
                Downloads: "download",
                Desktop: "pc",
                Pictures: "picture",
              }[type]
            }
            size={22}
          />
        </foreignObject>
      </g>
    </svg>
  );
}
