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

export const SearchIcon = ({ className }) => (
  <Base className={className}>
    <circle cx="11" cy="11" r="7" />
    <path d="m20 20-3.2-3.2" />
  </Base>
);

export const BellIcon = ({ className }) => (
  <Base className={className}>
    <path d="M6 8a6 6 0 1 1 12 0c0 5 2 6 2 6H4s2-1 2-6" />
    <path d="M10 18a2 2 0 0 0 4 0" />
  </Base>
);

export const ShieldIcon = ({ className }) => (
  <Base className={className}>
    <path d="M12 3 5 6v5c0 4.4 3 8.2 7 10 4-1.8 7-5.6 7-10V6l-7-3Z" />
    <path d="m9.2 11.8 2 2 3.6-3.9" />
  </Base>
);

export const CrosshairIcon = ({ className }) => (
  <Base className={className}>
    <circle cx="12" cy="12" r="7" />
    <path d="M12 3v3M12 18v3M3 12h3M18 12h3" />
  </Base>
);

export const ServerIcon = ({ className }) => (
  <Base className={className}>
    <rect x="4" y="4" width="16" height="6" rx="1" />
    <rect x="4" y="14" width="16" height="6" rx="1" />
    <path d="M8 7h.01M8 17h.01" />
  </Base>
);

export const SlidersIcon = ({ className }) => (
  <Base className={className}>
    <path d="M4 7h10M18 7h2M4 17h4M12 17h8" />
    <circle cx="16" cy="7" r="2" />
    <circle cx="10" cy="17" r="2" />
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

export const LedgerIcon = ({ className }) => (
  <Base className={className}>
    <path d="M5 4h11a2 2 0 0 1 2 2v14H7a2 2 0 0 1-2-2V4Z" />
    <path d="M18 16v2a2 2 0 0 1-2 2" />
    <path d="M9 8h5M9 12h5" />
  </Base>
);

export const CpuIcon = ({ className }) => (
  <Base className={className}>
    <rect x="7" y="7" width="10" height="10" rx="1" />
    <path d="M10 3v2M14 3v2M10 19v2M14 19v2M3 10h2M3 14h2M19 10h2M19 14h2" />
  </Base>
);

export const PulseIcon = ({ className }) => (
  <Base className={className}>
    <path d="M3 12h4l2.5-6 4 12L16 12h5" />
  </Base>
);

export const InboxIcon = ({ className }) => (
  <Base className={className}>
    <path d="M4 13 6 5h12l2 8" />
    <path d="M4 13v5a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-5h-5a3 3 0 0 1-6 0H4Z" />
  </Base>
);

export const ClockIcon = ({ className }) => (
  <Base className={className}>
    <circle cx="12" cy="12" r="8" />
    <path d="M12 8v4l2.5 2" />
  </Base>
);
