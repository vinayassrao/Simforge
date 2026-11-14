import type { Cell, Incident, ScenarioLayout } from "@/types/api";

interface PathMapProps {
  grid: { width: number; height: number };
  layout: ScenarioLayout;
  trajectory: [number, number, number, string][];
  incidents: Incident[];
  /** Show the route only up to this step, for scrubbing through a finished run. */
  untilStep?: number;
}

const CELL = 28;

/**
 * A top-down map of a finished run, drawn from the stored trajectory.
 * This is a 2D summary; the 3D view is rendered by Panda3D.
 */
export function PathMap({ grid, layout, trajectory, incidents, untilStep }: PathMapProps) {
  const width = grid.width * CELL;
  const height = grid.height * CELL;
  const x = (cell: Cell | [number, number]) => cell[0] * CELL;
  const y = (cell: Cell | [number, number]) => (grid.height - 1 - cell[1]) * CELL;
  const centre = (cx: number, cy: number) => `${cx * CELL + CELL / 2},${(grid.height - 1 - cy) * CELL + CELL / 2}`;

  const visible = untilStep === undefined ? trajectory : trajectory.filter(([step]) => step <= untilStep);
  const route = visible.map(([, cx, cy]) => centre(cx, cy)).join(" ");
  const last = visible[visible.length - 1];
  const shownIncidents = untilStep === undefined ? incidents : incidents.filter((incident) => incident.step <= untilStep);

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="h-auto w-full rounded-lg border border-line bg-[#0b1220]"
      role="img"
      aria-label={`Top-down map of the route: ${visible.length - 1} steps, ${shownIncidents.length} safety incidents`}
    >
      <defs>
        <pattern id="map-grid" width={CELL} height={CELL} patternUnits="userSpaceOnUse">
          <path d={`M ${CELL} 0 L 0 0 0 ${CELL}`} fill="none" stroke="#1c2942" strokeWidth="1" />
        </pattern>
      </defs>
      <rect width={width} height={height} fill="url(#map-grid)" />
      {layout.zones.flatMap((zone) =>
        zone.cells.map((cell) => (
          <rect
            key={`${zone.id}-${cell[0]}-${cell[1]}`}
            x={x(cell)}
            y={y(cell)}
            width={CELL}
            height={CELL}
            fill={zone.color}
            fillOpacity={zone.kind === "restricted" ? 0.4 : 0.28}
          />
        )),
      )}
      {layout.shelves.map((cell) => (
        <rect key={`s-${cell[0]}-${cell[1]}`} x={x(cell) + 2} y={y(cell) + 2} width={CELL - 4} height={CELL - 4} rx="3" fill="#d98a25" />
      ))}
      {layout.static_obstacles.map((cell) => (
        <rect key={`o-${cell[0]}-${cell[1]}`} x={x(cell) + 4} y={y(cell) + 4} width={CELL - 8} height={CELL - 8} rx="3" fill="#8b6b4a" />
      ))}
      {route && <polyline points={route} fill="none" stroke="#22d3ee" strokeWidth="3" strokeLinejoin="round" strokeLinecap="round" />}
      <circle cx={x(layout.start) + CELL / 2} cy={y(layout.start) + CELL / 2} r="6" fill="#94a3b8" />
      {shownIncidents.map((incident, index) => (
        <g key={index} stroke="#f87171" strokeWidth="3" strokeLinecap="round">
          <line x1={x(incident.cell) + 7} y1={y(incident.cell) + 7} x2={x(incident.cell) + CELL - 7} y2={y(incident.cell) + CELL - 7} />
          <line x1={x(incident.cell) + CELL - 7} y1={y(incident.cell) + 7} x2={x(incident.cell) + 7} y2={y(incident.cell) + CELL - 7} />
        </g>
      ))}
      {last && <circle cx={last[1] * CELL + CELL / 2} cy={(grid.height - 1 - last[2]) * CELL + CELL / 2} r="7" fill="#22d3ee" stroke="#04222a" strokeWidth="2" />}
    </svg>
  );
}

export function PathMapLegend() {
  const items = [
    { label: "Route taken", className: "bg-accent" },
    { label: "Shelf", className: "bg-[#d98a25]" },
    { label: "Pallet", className: "bg-[#8b6b4a]" },
    { label: "Collision or restricted entry", className: "bg-bad" },
    { label: "Start", className: "bg-slate-400" },
  ];
  return (
    <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-faint">
      {items.map((item) => (
        <li key={item.label} className="flex items-center gap-1.5">
          <span className={`size-2.5 rounded-sm ${item.className}`} aria-hidden="true" />
          {item.label}
        </li>
      ))}
    </ul>
  );
}
