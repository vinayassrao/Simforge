import clsx from "clsx";
import {
  BarChart3,
  BookOpen,
  Bot,
  Boxes,
  FileCode2,
  History,
  LayoutDashboard,
  type LucideIcon,
  Menu,
  Moon,
  PanelLeftClose,
  PanelLeftOpen,
  Radio,
  Sun,
  X,
} from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";

import { Button } from "@/components/ui/primitives";
import { useApi } from "@/hooks/useApi";
import { useTheme } from "@/hooks/useTheme";
import { api } from "@/services/api";

interface NavItem {
  to: string;
  label: string;
  hint: string;
  icon: LucideIcon;
  end?: boolean;
}

export const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "Overview", hint: "Your workspace at a glance", icon: LayoutDashboard, end: true },
  { to: "/scenarios", label: "Scenario Library", hint: "Pick a 3D environment", icon: Boxes },
  { to: "/simulation", label: "Live Simulation", hint: "Watch and control a run", icon: Radio },
  { to: "/agents", label: "Agent Studio", hint: "How agents plug in", icon: Bot },
  { to: "/evaluations", label: "Evaluations", hint: "Scores and comparisons", icon: BarChart3 },
  { to: "/history", label: "Run History", hint: "Every past run", icon: History },
  { to: "/api-docs", label: "API Documentation", hint: "Endpoints and schema", icon: FileCode2 },
  { to: "/workflows", label: "Workflows & Tutorials", hint: "Guides and task specs", icon: BookOpen },
];

function Brand({ compact }: { compact: boolean }) {
  return (
    <div className="flex items-center gap-2.5 px-1">
      <svg viewBox="0 0 32 32" className="size-9 shrink-0" aria-hidden="true">
        <rect width="32" height="32" rx="8" className="fill-raised" />
        <path
          d="M16 5 6 10.5v11L16 27l10-5.5v-11L16 5Zm0 2.6 7 3.9-7 3.9-7-3.9 7-3.9ZM8.3 13.4l6.5 3.6v7l-6.5-3.6v-7Zm8.9 10.6v-7l6.5-3.6v7L17.2 24Z"
          className="fill-accent"
        />
      </svg>
      {!compact && (
        <div className="min-w-0 leading-tight">
          <p className="text-[0.95rem] font-bold tracking-[0.14em] text-ink">SIMFORGE</p>
          <p className="truncate text-[0.68rem] text-faint">AI Simulation &amp; Training Lab</p>
        </div>
      )}
    </div>
  );
}

function Navigation({ compact, onNavigate }: { compact: boolean; onNavigate?: () => void }) {
  return (
    <nav aria-label="Main" className="flex-1 overflow-y-auto">
      <ul className="flex flex-col gap-1">
        {NAV_ITEMS.map(({ to, label, hint, icon: Icon, end }) => (
          <li key={to}>
            <NavLink
              to={to}
              end={end}
              onClick={onNavigate}
              title={compact ? label : undefined}
              className={({ isActive }) =>
                clsx(
                  "group flex items-center gap-3 rounded-lg border px-2.5 py-2 text-sm transition-colors",
                  compact && "justify-center",
                  isActive
                    ? "border-accent/30 bg-accent/10 text-accent"
                    : "border-transparent text-soft hover:bg-raised hover:text-ink",
                )
              }
            >
              <Icon className="size-[1.1rem] shrink-0" aria-hidden="true" />
              {compact ? (
                <span className="sr-only">{label}</span>
              ) : (
                <span className="min-w-0">
                  <span className="block font-medium leading-tight">{label}</span>
                  <span className="block truncate text-[0.7rem] text-faint">{hint}</span>
                </span>
              )}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}

function EngineStatus({ compact }: { compact: boolean }) {
  const { data, error } = useApi(api.health, [], 5000);
  const online = Boolean(data) && !error;
  const label = online ? (data?.rendering ? "Panda3D engine online" : "Simulation online (no rendering)") : "Server offline";
  return (
    <div
      className={clsx("flex items-center gap-2 rounded-lg border border-line bg-raised px-2.5 py-2 text-xs", compact && "justify-center")}
      title={compact ? label : undefined}
    >
      <span
        className={clsx("size-2 shrink-0 rounded-full", online ? "animate-pulse-dot bg-good" : "bg-bad")}
        aria-hidden="true"
      />
      {compact ? (
        <span className="sr-only">{label}</span>
      ) : (
        <span className="min-w-0">
          <span className="block font-medium text-ink">{label}</span>
          {online && data?.performance.fps !== undefined && (
            <span className="block text-faint">{data.performance.fps.toFixed(0)} FPS render loop</span>
          )}
        </span>
      )}
    </div>
  );
}

export function AppLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const { theme, toggleTheme } = useTheme();
  const location = useLocation();
  const current = NAV_ITEMS.find((item) => (item.end ? location.pathname === item.to : location.pathname.startsWith(item.to)));

  useEffect(() => setDrawerOpen(false), [location.pathname]);

  useEffect(() => {
    if (!drawerOpen) return;
    const close = (event: KeyboardEvent) => event.key === "Escape" && setDrawerOpen(false);
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [drawerOpen]);

  return (
    <div className="app-backdrop flex min-h-screen">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-50 focus:rounded-lg focus:bg-accent focus:px-3 focus:py-2 focus:text-accent-ink"
      >
        Skip to content
      </a>

      <aside
        className={clsx(
          "sticky top-0 hidden h-screen shrink-0 flex-col gap-4 border-r border-line bg-panel/80 p-3 backdrop-blur lg:flex",
          collapsed ? "w-[4.25rem]" : "w-64",
        )}
      >
        <Brand compact={collapsed} />
        <Navigation compact={collapsed} />
        <EngineStatus compact={collapsed} />
        <Button
          variant="ghost"
          size="sm"
          icon={collapsed ? PanelLeftOpen : PanelLeftClose}
          onClick={() => setCollapsed((value) => !value)}
          aria-expanded={!collapsed}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {!collapsed && "Collapse"}
        </Button>
      </aside>

      {drawerOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <button
            type="button"
            className="absolute inset-0 bg-black/60"
            aria-label="Close navigation"
            onClick={() => setDrawerOpen(false)}
          />
          <div
            role="dialog"
            aria-modal="true"
            aria-label="Navigation"
            className="absolute inset-y-0 left-0 flex w-72 max-w-[85vw] flex-col gap-4 border-r border-line bg-panel p-3"
          >
            <div className="flex items-center justify-between">
              <Brand compact={false} />
              <Button variant="ghost" size="sm" icon={X} onClick={() => setDrawerOpen(false)} aria-label="Close navigation" />
            </div>
            <Navigation compact={false} onNavigate={() => setDrawerOpen(false)} />
            <EngineStatus compact={false} />
          </div>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex h-14 items-center gap-3 border-b border-line bg-canvas/85 px-4 backdrop-blur">
          <Button
            variant="ghost"
            size="sm"
            icon={Menu}
            className="lg:hidden"
            onClick={() => setDrawerOpen(true)}
            aria-label="Open navigation"
          />
          <p className="min-w-0 flex-1 truncate text-sm text-faint">
            <span className="text-soft">SIMFORGE</span>
            <span className="mx-2" aria-hidden="true">
              /
            </span>
            <span className="font-medium text-ink">{current?.label ?? "Workspace"}</span>
          </p>
          <p className="hidden text-xs text-faint md:block">Build worlds. Train agents. Evaluate intelligence.</p>
          <Button
            variant="ghost"
            size="sm"
            icon={theme === "dark" ? Sun : Moon}
            onClick={toggleTheme}
            aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
          />
        </header>
        <main id="main" className="min-w-0 flex-1 px-4 py-6 sm:px-6 lg:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
