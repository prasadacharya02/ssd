/** Stroke icons, 1.5px weight, drawn for legibility at 16px. */

function Base({ children, className = "h-4 w-4" }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      {children}
    </svg>
  );
}

export const CrosshairIcon = ({ className }) => (
  <Base className={className}>
    <circle cx="12" cy="12" r="7" />
    <path d="M12 3v3M12 18v3M3 12h3M18 12h3" />
  </Base>
);

export const ShieldIcon = ({ className }) => (
  <Base className={className}>
    <path d="M12 3 5 6v5c0 4.4 3 8.2 7 10 4-1.8 7-5.6 7-10V6l-7-3Z" />
    <path d="m9.2 11.8 2 2 3.6-3.9" />
  </Base>
);

export const PlayIcon = ({ className }) => (
  <Base className={className}>
    <path d="M7 4.5 19 12 7 19.5V4.5Z" />
  </Base>
);

export const StopIcon = ({ className }) => (
  <Base className={className}>
    <rect x="6" y="6" width="12" height="12" rx="1.5" />
  </Base>
);

export const PauseIcon = ({ className }) => (
  <Base className={className}>
    <path d="M9 5v14M15 5v14" />
  </Base>
);

export const ResetIcon = ({ className }) => (
  <Base className={className}>
    <path d="M3.5 12a8.5 8.5 0 1 0 2.6-6.1" />
    <path d="M3.5 5v5h5" />
  </Base>
);

export const DownloadIcon = ({ className }) => (
  <Base className={className}>
    <path d="M12 4v11" />
    <path d="m7.5 10.5 4.5 4.5 4.5-4.5" />
    <path d="M5 20h14" />
  </Base>
);

export const CopyIcon = ({ className }) => (
  <Base className={className}>
    <rect x="9" y="9" width="11" height="11" rx="1.5" />
    <path d="M15 5.5A1.5 1.5 0 0 0 13.5 4h-8A1.5 1.5 0 0 0 4 5.5v8A1.5 1.5 0 0 0 5.5 15" />
  </Base>
);

export const ExternalIcon = ({ className }) => (
  <Base className={className}>
    <path d="M14 4h6v6" />
    <path d="M20 4 11 13" />
    <path d="M18 14.5V19a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h4.5" />
  </Base>
);

export const ServerIcon = ({ className }) => (
  <Base className={className}>
    <rect x="4" y="4" width="16" height="6" rx="1" />
    <rect x="4" y="14" width="16" height="6" rx="1" />
    <path d="M8 7h.01M8 17h.01" />
  </Base>
);

export const FileIcon = ({ className }) => (
  <Base className={className}>
    <path d="M13 3H7a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V8l-5-5Z" />
    <path d="M13 3v5h5" />
  </Base>
);

export const TerminalIcon = ({ className }) => (
  <Base className={className}>
    <rect x="3" y="4" width="18" height="16" rx="2" />
    <path d="m7 9 2.5 3L7 15" />
    <path d="M12.5 15H17" />
  </Base>
);

export const ActivityIcon = ({ className }) => (
  <Base className={className}>
    <path d="M3 12h3.5l2.5-6 3.5 12 2.5-6H21" />
  </Base>
);

export const BoltIcon = ({ className }) => (
  <Base className={className}>
    <path d="M13 2 4.5 13.5H11l-1 8.5 8.5-11.5H12l1-8.5Z" />
  </Base>
);

export const SearchIcon = ({ className }) => (
  <Base className={className}>
    <circle cx="11" cy="11" r="7" />
    <path d="m20 20-3.2-3.2" />
  </Base>
);

export const AlertIcon = ({ className }) => (
  <Base className={className}>
    <path d="M12 4 2.8 20h18.4L12 4Z" />
    <path d="M12 10v4.5M12 17.5h.01" />
  </Base>
);

export const LockIcon = ({ className }) => (
  <Base className={className}>
    <rect x="4.5" y="10" width="15" height="10" rx="2" />
    <path d="M8 10V7.5a4 4 0 0 1 8 0V10" />
  </Base>
);

export const ClockIcon = ({ className }) => (
  <Base className={className}>
    <circle cx="12" cy="12" r="8" />
    <path d="M12 7.5V12l3 2" />
  </Base>
);

export const MenuIcon = ({ className }) => (
  <Base className={className}>
    <path d="M4 7h16M4 12h16M4 17h16" />
  </Base>
);

export const CloseIcon = ({ className }) => (
  <Base className={className}>
    <path d="m6 6 12 12M18 6 6 18" />
  </Base>
);
