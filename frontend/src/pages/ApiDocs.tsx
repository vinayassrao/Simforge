import clsx from "clsx";
import { ExternalLink, Radio } from "lucide-react";
import { useMemo } from "react";

import { CodeBlock } from "@/components/ui/CodeBlock";
import { buttonClasses, ErrorNote, PageHeader, SectionCard, Spinner } from "@/components/ui/primitives";
import { useApi } from "@/hooks/useApi";
import { api, type OpenApiDocument, SWAGGER_URL } from "@/services/api";

const METHOD_CLASS: Record<string, string> = {
  get: "border-info/40 bg-info/10 text-info",
  post: "border-good/40 bg-good/10 text-good",
  put: "border-warn/40 bg-warn/10 text-warn",
  delete: "border-bad/40 bg-bad/10 text-bad",
};

const SOCKET_EXAMPLE = `{ "type": "state",    "state": { "status": "running", "observation": { ... }, "metrics": { ... } } }
{ "type": "events",   "events": [ { "seq": 12, "type": "MOVE_COMPLETED", "description": "..." } ] }
{ "type": "finished", "evaluation": { "score": 100.0, "success": true, "breakdown": [ ... ] } }
{ "type": "perf",     "perf": { "fps": 29.8, "frame_ms": 33.3 } }`;

export interface EndpointGroup {
  tag: string;
  endpoints: { method: string; path: string; summary: string }[];
}

export function groupEndpoints(document: OpenApiDocument): EndpointGroup[] {
  const groups = new Map<string, EndpointGroup["endpoints"]>();
  for (const [path, methods] of Object.entries(document.paths)) {
    for (const [method, operation] of Object.entries(methods)) {
      const tag = operation.tags?.[0] ?? "Other";
      const list = groups.get(tag) ?? [];
      list.push({ method, path, summary: operation.summary ?? "" });
      groups.set(tag, list);
    }
  }
  return [...groups.entries()].map(([tag, endpoints]) => ({ tag, endpoints }));
}

export function ApiDocs() {
  const { data, error, loading, reload } = useApi(api.openapi);
  const groups = useMemo(() => (data ? groupEndpoints(data) : []), [data]);

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-5">
      <PageHeader
        title="API Documentation"
        subtitle="Everything the web interface does goes through this REST API, so your own agent can do the same. This list is read live from the server's OpenAPI schema."
        actions={
          <a className={buttonClasses("primary", "md")} href={SWAGGER_URL} target="_blank" rel="noreferrer">
            <ExternalLink className="size-4" aria-hidden="true" />
            Open Swagger UI
          </a>
        }
      />

      {loading && <Spinner label="Reading the OpenAPI schema" />}
      {error && <ErrorNote message={error} onRetry={reload} />}

      {data && (
        <p className="text-sm text-faint">
          {data.info.title} · version {data.info.version} · base path <code className="font-mono text-soft">/api/v1</code> ·
          errors always look like{" "}
          <code className="font-mono text-soft">{'{"error": {"code", "message", "details"}}'}</code>
        </p>
      )}

      <div className="grid gap-5 xl:grid-cols-2">
        {groups.map((group) => (
          <SectionCard key={group.tag} title={group.tag} hint={`${group.endpoints.length} endpoint${group.endpoints.length === 1 ? "" : "s"}`}>
            <ul className="flex flex-col gap-2">
              {group.endpoints.map((endpoint) => (
                <li key={`${endpoint.method}-${endpoint.path}`} className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
                  <span
                    className={clsx(
                      "w-14 shrink-0 rounded-md border px-1.5 py-0.5 text-center font-mono text-[0.68rem] font-bold uppercase",
                      METHOD_CLASS[endpoint.method] ?? "border-line text-soft",
                    )}
                  >
                    {endpoint.method}
                  </span>
                  <code className="break-all font-mono text-xs text-ink">{endpoint.path}</code>
                  <span className="basis-full pl-16 text-xs text-soft">{endpoint.summary}</span>
                </li>
              ))}
            </ul>
          </SectionCard>
        ))}
      </div>

      <SectionCard
        title="Live updates over WebSocket"
        hint="Connect to /ws/episodes/{id}/ to receive every change as it happens."
        actions={<Radio className="size-4 text-accent" aria-hidden="true" />}
      >
        <p className="mb-3 text-sm text-soft">
          The server sends a <code className="font-mono text-ink">hello</code> message with the current state, then one
          JSON message per change. The Live Simulation page is built on exactly this stream.
        </p>
        <CodeBlock code={SOCKET_EXAMPLE} language="json" title="ws://127.0.0.1:8000/ws/episodes/{id}/" />
      </SectionCard>
    </div>
  );
}
