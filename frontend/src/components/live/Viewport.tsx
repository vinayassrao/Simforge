import clsx from "clsx";
import { Camera, Grid3x3, MapPinned, Minus, Plus, Route, Shapes, Tags, TriangleAlert, VideoOff } from "lucide-react";
import { type ReactNode, useState } from "react";

import { Badge, Button, Card } from "@/components/ui/primitives";
import { api, STREAM_URL } from "@/services/api";
import type { ViewSettings } from "@/types/api";

const DEFAULT_VIEW: ViewSettings = {
  grid: false,
  paths: true,
  collisions: true,
  labels: true,
  collision_shapes: false,
  camera: "perspective",
  zoom: 1,
};

const LEGEND: { label: string; className: string }[] = [
  { label: "Robot (arrow shows its heading)", className: "bg-slate-200" },
  { label: "Current target marker", className: "bg-accent" },
  { label: "Planned route", className: "bg-cyan-300" },
  { label: "Collection bay", className: "bg-sky-400" },
  { label: "Green delivery zone", className: "bg-green-500" },
  { label: "Orange delivery zone", className: "bg-orange-500" },
  { label: "Restricted area (striped)", className: "bg-red-500" },
  { label: "Forklift (moving obstacle)", className: "bg-yellow-400" },
  { label: "Shelves and pallets (static)", className: "bg-amber-600" },
  { label: "Collision marker", className: "bg-red-400" },
];

const CAMERA_OPTIONS: { id: ViewSettings["camera"]; label: string }[] = [
  { id: "perspective", label: "Front" },
  { id: "isometric", label: "Angled" },
  { id: "top", label: "Top-down" },
];

function Toggle({ active, onClick, icon, children }: { active: boolean; onClick: () => void; icon: ReactNode; children: ReactNode }) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={clsx(
        "inline-flex h-8 items-center gap-1.5 rounded-lg border px-2.5 text-xs font-medium transition-colors",
        active ? "border-accent/50 bg-accent/15 text-accent" : "border-line bg-raised text-soft hover:text-ink",
      )}
    >
      {icon}
      {children}
    </button>
  );
}

interface ViewportProps {
  isLive: boolean;
  rendering: boolean;
  banner?: ReactNode;
}

/** The live view: frames rendered off-screen by Panda3D and streamed to the browser. */
export function Viewport({ isLive, rendering, banner }: ViewportProps) {
  const [view, setView] = useState<ViewSettings>(DEFAULT_VIEW);
  const [showLegend, setShowLegend] = useState(false);
  const [streamFailed, setStreamFailed] = useState(false);

  const apply = (request: Promise<ViewSettings>) => {
    request.then(setView, () => undefined);
  };
  const toggle = (key: "grid" | "paths" | "collisions" | "labels" | "collision_shapes") =>
    apply(api.setView({ [key]: !view[key] }));

  const showStream = rendering && !streamFailed;

  return (
    <Card className="overflow-hidden">
      <div className="viewport-frame relative aspect-video w-full">
        {showStream ? (
          <img
            src={STREAM_URL}
            alt="Live Panda3D render of the warehouse simulation"
            className="size-full object-contain"
            onError={() => setStreamFailed(true)}
          />
        ) : (
          <div className="flex size-full flex-col items-center justify-center gap-2 p-6 text-center text-sm text-slate-300">
            <VideoOff className="size-8 text-slate-500" aria-hidden="true" />
            <p className="font-medium">The 3D view is not available</p>
            <p className="max-w-md text-xs text-slate-400">
              The server is running the simulation without the Panda3D renderer. Everything else on this page still
              shows the real simulation state.
            </p>
          </div>
        )}
        <div className="absolute left-3 top-3 flex flex-wrap gap-1.5">
          <Badge tone="accent" className="bg-[#0b1220]/80 backdrop-blur">
            Panda3D render
          </Badge>
          {!isLive && (
            <Badge tone="warn" className="bg-[#0b1220]/80 backdrop-blur">
              Not the active run
            </Badge>
          )}
        </div>
        {showLegend && (
          <div className="absolute right-3 top-3 w-64 rounded-lg border border-line bg-panel/95 p-3 shadow-card backdrop-blur">
            <p className="mb-2 text-xs font-semibold text-ink">What you are looking at</p>
            <ul className="flex flex-col gap-1.5 text-xs text-soft">
              {LEGEND.map((item) => (
                <li key={item.label} className="flex items-center gap-2">
                  <span className={clsx("size-2.5 shrink-0 rounded-sm", item.className)} aria-hidden="true" />
                  {item.label}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {banner && <div className="border-t border-line p-3">{banner}</div>}

      <div className="flex flex-wrap items-center gap-2 border-t border-line px-3 py-2.5">
        <div role="group" aria-label="Camera" className="flex flex-wrap items-center gap-1.5">
          <Button size="sm" icon={Camera} onClick={() => apply(api.camera("reset"))}>
            Reset camera
          </Button>
          <Button size="sm" icon={Plus} onClick={() => apply(api.camera("zoom_in"))} aria-label="Zoom in" />
          <Button size="sm" icon={Minus} onClick={() => apply(api.camera("zoom_out"))} aria-label="Zoom out" />
          {CAMERA_OPTIONS.map((option) => (
            <Toggle
              key={option.id}
              active={view.camera === option.id}
              onClick={() => apply(api.camera("preset", option.id))}
              icon={null}
            >
              {option.label}
            </Toggle>
          ))}
        </div>
        <span className="mx-1 hidden h-5 w-px bg-line sm:block" aria-hidden="true" />
        <div role="group" aria-label="Overlays" className="flex flex-wrap items-center gap-1.5">
          <Toggle active={view.grid} onClick={() => toggle("grid")} icon={<Grid3x3 className="size-3.5" aria-hidden="true" />}>
            Grid
          </Toggle>
          <Toggle active={view.paths} onClick={() => toggle("paths")} icon={<Route className="size-3.5" aria-hidden="true" />}>
            Planned route
          </Toggle>
          <Toggle
            active={view.collisions}
            onClick={() => toggle("collisions")}
            icon={<TriangleAlert className="size-3.5" aria-hidden="true" />}
          >
            Collision marks
          </Toggle>
          <Toggle active={view.labels} onClick={() => toggle("labels")} icon={<Tags className="size-3.5" aria-hidden="true" />}>
            Labels
          </Toggle>
          <Toggle
            active={view.collision_shapes}
            onClick={() => toggle("collision_shapes")}
            icon={<Shapes className="size-3.5" aria-hidden="true" />}
          >
            Collision shapes
          </Toggle>
          <Toggle active={showLegend} onClick={() => setShowLegend((value) => !value)} icon={<MapPinned className="size-3.5" aria-hidden="true" />}>
            Legend
          </Toggle>
        </div>
      </div>
    </Card>
  );
}
