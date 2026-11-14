import clsx from "clsx";
import { Check, Copy, Info, Loader2, type LucideIcon } from "lucide-react";
import { type ButtonHTMLAttributes, type HTMLAttributes, type ReactNode, useId, useState } from "react";
import { Link, type LinkProps } from "react-router-dom";

export type Tone = "neutral" | "accent" | "good" | "warn" | "bad" | "info";

const TONE_TEXT: Record<Tone, string> = {
  neutral: "text-soft",
  accent: "text-accent",
  good: "text-good",
  warn: "text-warn",
  bad: "text-bad",
  info: "text-info",
};

const TONE_BADGE: Record<Tone, string> = {
  neutral: "border-line bg-raised text-soft",
  accent: "border-accent/30 bg-accent/10 text-accent",
  good: "border-good/30 bg-good/10 text-good",
  warn: "border-warn/30 bg-warn/10 text-warn",
  bad: "border-bad/30 bg-bad/10 text-bad",
  info: "border-info/30 bg-info/10 text-info",
};

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
type ButtonSize = "sm" | "md" | "lg";

const BUTTON_BASE =
  "inline-flex items-center justify-center gap-2 rounded-lg font-semibold transition-colors duration-150 " +
  "disabled:cursor-not-allowed disabled:opacity-45 whitespace-nowrap";
const BUTTON_VARIANTS: Record<ButtonVariant, string> = {
  primary: "bg-accent text-accent-ink hover:brightness-110",
  secondary: "border border-line bg-raised text-ink hover:border-accent/50",
  ghost: "text-soft hover:bg-raised hover:text-ink",
  danger: "border border-bad/40 bg-bad/10 text-bad hover:bg-bad/20",
};
const BUTTON_SIZES: Record<ButtonSize, string> = {
  sm: "h-8 px-2.5 text-xs",
  md: "h-9 px-3.5 text-sm",
  lg: "h-11 px-5 text-[0.95rem]",
};

export function buttonClasses(variant: ButtonVariant = "secondary", size: ButtonSize = "md", extra?: string): string {
  return clsx(BUTTON_BASE, BUTTON_VARIANTS[variant], BUTTON_SIZES[size], extra);
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  icon?: LucideIcon;
  busy?: boolean;
}

export function Button({ variant, size, icon: Icon, busy, className, children, ...props }: ButtonProps) {
  return (
    <button type="button" className={buttonClasses(variant, size, className)} {...props} disabled={props.disabled || busy}>
      {busy ? (
        <Loader2 className="size-4 animate-spin" aria-hidden="true" />
      ) : (
        Icon && <Icon className="size-4" aria-hidden="true" />
      )}
      {children}
    </button>
  );
}

interface ButtonLinkProps extends LinkProps {
  variant?: ButtonVariant;
  size?: ButtonSize;
  icon?: LucideIcon;
}

export function ButtonLink({ variant, size, icon: Icon, className, children, ...props }: ButtonLinkProps) {
  return (
    <Link className={buttonClasses(variant, size, className)} {...props}>
      {Icon && <Icon className="size-4" aria-hidden="true" />}
      {children}
    </Link>
  );
}

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={clsx("rounded-xl border border-line bg-panel shadow-card", className)} {...props} />;
}

interface SectionCardProps {
  title: string;
  hint?: string;
  help?: string;
  actions?: ReactNode;
  className?: string;
  bodyClassName?: string;
  children: ReactNode;
}

/** A titled panel. `hint` is the plain-language line; `help` is an optional deeper explanation. */
export function SectionCard({ title, hint, help, actions, className, bodyClassName, children }: SectionCardProps) {
  const headingId = useId();
  return (
    <Card className={clsx("flex min-w-0 flex-col", className)}>
      <section aria-labelledby={headingId} className="flex min-h-0 flex-1 flex-col">
        <header className="flex flex-wrap items-start justify-between gap-2 border-b border-line px-4 py-3">
          <div className="min-w-0">
            <h2 id={headingId} className="flex items-center gap-1.5 text-sm font-semibold text-ink">
              {title}
              {help && <InfoTip text={help} />}
            </h2>
            {hint && <p className="mt-0.5 text-xs text-faint">{hint}</p>}
          </div>
          {actions && <div className="flex max-w-full min-w-0 flex-wrap items-center gap-1.5">{actions}</div>}
        </header>
        <div className={clsx("min-h-0 flex-1 p-4", bodyClassName)}>{children}</div>
      </section>
    </Card>
  );
}

export function Badge({ tone = "neutral", className, ...props }: HTMLAttributes<HTMLSpanElement> & { tone?: Tone }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium",
        TONE_BADGE[tone],
        className,
      )}
      {...props}
    />
  );
}

/** A small "i" that reveals an explanation on hover or keyboard focus. */
export function InfoTip({ text }: { text: string }) {
  const tipId = useId();
  return (
    <span className="group relative inline-flex">
      <button
        type="button"
        aria-describedby={tipId}
        aria-label="More information"
        className="rounded-full text-faint hover:text-accent"
      >
        <Info className="size-3.5" aria-hidden="true" />
      </button>
      <span
        id={tipId}
        role="tooltip"
        className="pointer-events-none absolute left-1/2 top-full z-30 mt-1.5 hidden w-60 -translate-x-1/2 rounded-lg border border-line bg-raised px-3 py-2 text-xs font-normal leading-relaxed text-soft shadow-card group-focus-within:block group-hover:block"
      >
        {text}
      </span>
    </span>
  );
}

interface StatProps {
  label: string;
  value: ReactNode;
  hint?: string;
  icon?: LucideIcon;
  tone?: Tone;
}

export function Stat({ label, value, hint, icon: Icon, tone = "accent" }: StatProps) {
  return (
    <Card className="animate-rise p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-medium uppercase tracking-wide text-faint">{label}</p>
        {Icon && (
          <span className={clsx("rounded-lg border border-line bg-raised p-1.5", TONE_TEXT[tone])}>
            <Icon className="size-4" aria-hidden="true" />
          </span>
        )}
      </div>
      <p className="mt-2 text-2xl font-semibold tracking-tight text-ink">{value}</p>
      {hint && <p className="mt-0.5 text-xs text-faint">{hint}</p>}
    </Card>
  );
}

export function MiniStat({ label, value, tone }: { label: string; value: ReactNode; tone?: Tone }) {
  return (
    <div className="rounded-lg border border-line bg-raised px-3 py-2">
      <dt className="text-[0.7rem] font-medium uppercase tracking-wide text-faint">{label}</dt>
      <dd className={clsx("mt-0.5 text-base font-semibold", tone ? TONE_TEXT[tone] : "text-ink")}>{value}</dd>
    </div>
  );
}

export function ProgressBar({ value, max = 100, label, tone = "accent" }: { value: number; max?: number; label: string; tone?: Tone }) {
  return <progress className={TONE_TEXT[tone]} value={value} max={max} aria-label={label} />;
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle: string; actions?: ReactNode }) {
  return (
    <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">
        <h1 className="text-2xl font-semibold tracking-tight text-ink">{title}</h1>
        <p className="mt-1 max-w-3xl text-sm text-soft">{subtitle}</p>
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </header>
  );
}

export function Spinner({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 p-10 text-sm text-faint" role="status">
      <Loader2 className="size-4 animate-spin" aria-hidden="true" />
      {label}...
    </div>
  );
}

export function ErrorNote({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex flex-wrap items-center gap-3 rounded-xl border border-bad/40 bg-bad/10 px-4 py-3 text-sm text-bad">
      <span className="min-w-0 flex-1">{message}</span>
      {onRetry && (
        <Button size="sm" variant="danger" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}

export function EmptyState({ icon: Icon, title, text, action }: { icon: LucideIcon; title: string; text: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 px-6 py-10 text-center">
      <span className="rounded-xl border border-line bg-raised p-3 text-accent">
        <Icon className="size-6" aria-hidden="true" />
      </span>
      <p className="text-sm font-semibold text-ink">{title}</p>
      <p className="max-w-md text-sm text-faint">{text}</p>
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}

export function CopyButton({ text, label = "Copy" }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      setCopied(false);
    }
  };
  return (
    <Button size="sm" variant="ghost" icon={copied ? Check : Copy} onClick={copy} aria-live="polite">
      {copied ? "Copied" : label}
    </Button>
  );
}

interface TabsProps<T extends string> {
  tabs: { id: T; label: string; count?: number }[];
  active: T;
  onChange: (id: T) => void;
  label: string;
}

export function Tabs<T extends string>({ tabs, active, onChange, label }: TabsProps<T>) {
  return (
    <div role="tablist" aria-label={label} className="flex flex-wrap gap-1 rounded-lg border border-line bg-raised p-1">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          role="tab"
          aria-selected={tab.id === active}
          onClick={() => onChange(tab.id)}
          className={clsx(
            "rounded-md px-2.5 py-1 text-xs font-medium transition-colors",
            tab.id === active ? "bg-panel text-accent shadow-card" : "text-soft hover:text-ink",
          )}
        >
          {tab.label}
          {tab.count !== undefined && <span className="ml-1.5 text-faint">{tab.count}</span>}
        </button>
      ))}
    </div>
  );
}
