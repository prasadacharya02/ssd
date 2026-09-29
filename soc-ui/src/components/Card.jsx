import { cx } from "../lib/format.js";

/**
 * The one true card surface: panel background, sharp 1px slate border,
 * p-6 interior padding everywhere. No shadows, no gradients.
 */
export default function Card({ className, children }) {
  return (
    <section className={cx("rounded-lg border border-slate-800 bg-panel p-6", className)}>
      {children}
    </section>
  );
}

export function CardLabel({ children, className }) {
  return (
    <p
      className={cx(
        "text-[11px] font-medium uppercase tracking-[0.14em] text-slate-500",
        className,
      )}
    >
      {children}
    </p>
  );
}
