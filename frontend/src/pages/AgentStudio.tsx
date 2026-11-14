import { ArrowRight, Bot, Code2, Eye, Gamepad2, type LucideIcon, RefreshCw, Send, Sparkles } from "lucide-react";
import { useState } from "react";

import { CodeBlock } from "@/components/ui/CodeBlock";
import { Badge, Card, ErrorNote, PageHeader, SectionCard, Spinner, Tabs } from "@/components/ui/primitives";
import { useApi } from "@/hooks/useApi";
import { api } from "@/services/api";
import { humanize } from "@/services/format";
import type { AgentMode } from "@/types/api";

const AGENT_ICONS: Record<AgentMode, LucideIcon> = { manual: Gamepad2, astar: Bot, external: Code2 };

const LOOP_STEPS: { title: string; text: string; icon: LucideIcon }[] = [
  { title: "Observation", text: "The agent reads what it can see.", icon: Eye },
  { title: "Decision", text: "It chooses one action.", icon: Sparkles },
  { title: "Action", text: "It sends that action.", icon: Send },
  { title: "Environment update", text: "The Panda3D world applies the rules.", icon: RefreshCw },
  { title: "New observation", text: "The loop starts again.", icon: Eye },
];

const CONNECT_SNIPPET = `# 1. Create an episode for your agent
curl -X POST http://127.0.0.1:8000/api/v1/episodes/ \\
  -H "Content-Type: application/json" \\
  -d '{"scenario_id": "basic-delivery", "agent_mode": "external"}'

# 2. Start it (use the "id" from the response)
curl -X POST http://127.0.0.1:8000/api/v1/episodes/EPISODE_ID/start/

# 3. Read what the agent sees
curl http://127.0.0.1:8000/api/v1/episodes/EPISODE_ID/observation/

# 4. Send an action, then repeat steps 3 and 4 until "done" is true
curl -X POST http://127.0.0.1:8000/api/v1/episodes/EPISODE_ID/actions/ \\
  -H "Content-Type: application/json" \\
  -d '{"action": "MOVE_FORWARD"}'`;

function LoopDiagram() {
  return (
    <ol className="flex flex-col items-stretch gap-2 lg:flex-row lg:items-center" aria-label="The agent loop">
      {LOOP_STEPS.map(({ title, text, icon: Icon }, index) => (
        <li key={`${title}-${index}`} className="flex flex-1 items-center gap-2">
          <div className="flex-1 rounded-lg border border-line bg-raised p-3">
            <div className="flex items-center gap-2">
              <span className="rounded-md border border-accent/30 bg-accent/10 p-1.5 text-accent">
                <Icon className="size-4" aria-hidden="true" />
              </span>
              <span className="text-sm font-semibold text-ink">{title}</span>
            </div>
            <p className="mt-1.5 text-xs text-soft">{text}</p>
          </div>
          {index < LOOP_STEPS.length - 1 && (
            <ArrowRight className="size-4 shrink-0 rotate-90 text-faint lg:rotate-0" aria-hidden="true" />
          )}
        </li>
      ))}
    </ol>
  );
}

export function AgentStudio() {
  const { data, error, loading, reload } = useApi(api.agents);
  const [example, setExample] = useState<string>("");

  if (loading) return <Spinner label="Loading the agent catalogue" />;
  if (error || !data) return <ErrorNote message={error ?? "Could not load agents."} onRetry={reload} />;

  const exampleNames = Object.keys(data.examples);
  const activeExample = exampleNames.includes(example) ? example : (exampleNames[0] ?? "");

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-5">
      <PageHeader
        title="Agent Studio"
        subtitle="An agent is anything that looks at the world and picks the next action. SIMFORGE supports three kinds, and all of them use exactly the same actions and rules."
      />

      <section aria-label="Agent types" className="grid gap-4 md:grid-cols-3">
        {data.agents.map((agent) => {
          const Icon = AGENT_ICONS[agent.id];
          return (
            <Card key={agent.id} className="animate-rise p-4">
              <div className="flex items-center gap-2.5">
                <span className="rounded-lg border border-line bg-raised p-2 text-accent">
                  <Icon className="size-5" aria-hidden="true" />
                </span>
                <div>
                  <h2 className="text-base font-semibold text-ink">{agent.name}</h2>
                  <Badge>{agent.kind}</Badge>
                </div>
              </div>
              <p className="mt-3 text-sm text-soft">{agent.description}</p>
              <p className="mt-2 text-xs text-faint">{agent.how_it_acts}</p>
            </Card>
          );
        })}
      </section>

      <SectionCard
        title="How every agent works"
        hint="Observation -> Decision -> Action -> Environment update -> New observation."
        help="This loop is the standard way to connect an AI agent to a simulation. One trip around the loop is one step of the episode."
      >
        <LoopDiagram />
      </SectionCard>

      <div className="grid gap-5 xl:grid-cols-2">
        <SectionCard title="Action interface" hint="The seven things the robot can do, and when each one fails.">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[34rem] border-collapse text-left text-sm">
              <caption className="sr-only">Available actions with their meaning, precondition and failure behaviour</caption>
              <thead>
                <tr className="border-b border-line text-xs uppercase tracking-wide text-faint">
                  <th scope="col" className="px-2 py-2 font-medium">Action</th>
                  <th scope="col" className="px-2 py-2 font-medium">What it does</th>
                  <th scope="col" className="px-2 py-2 font-medium">Needs</th>
                  <th scope="col" className="px-2 py-2 font-medium">If it fails</th>
                </tr>
              </thead>
              <tbody>
                {data.actions.map((action) => (
                  <tr key={action.name} className="border-b border-line/60 align-top last:border-0">
                    <th scope="row" className="px-2 py-2 font-mono text-xs font-semibold text-accent">{action.name}</th>
                    <td className="px-2 py-2 text-soft">{action.meaning}</td>
                    <td className="px-2 py-2 text-xs text-soft">{action.precondition}</td>
                    <td className="px-2 py-2 text-xs text-faint">{action.failure}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>

        <div className="flex flex-col gap-5">
          <SectionCard title="Agent states" hint="The robot's task state, and which states can follow it.">
            <ul className="flex flex-col gap-2">
              {data.states.map((state) => (
                <li key={state.name} className="flex flex-wrap items-center gap-2 text-sm">
                  <Badge tone="accent" className="font-mono">{state.name}</Badge>
                  <ArrowRight className="size-3.5 text-faint" aria-hidden="true" />
                  {state.next.length === 0 ? (
                    <span className="text-xs text-faint">final state</span>
                  ) : (
                    state.next.map((next) => (
                      <span key={next} className="text-xs text-soft">{humanize(next)}</span>
                    ))
                  )}
                </li>
              ))}
            </ul>
          </SectionCard>

          <SectionCard title="Configuration" hint="Settings that apply to every agent.">
            <dl className="grid gap-2 text-sm">
              <div className="flex justify-between gap-3">
                <dt className="text-faint">Playback speeds (built-in agent)</dt>
                <dd className="font-mono text-ink">{data.speeds.map((speed) => `${speed}x`).join("  ")}</dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt className="text-faint">Base decision rate</dt>
                <dd className="font-mono text-ink">3 actions / second at 1x</dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt className="text-faint">Authentication</dt>
                <dd className="text-ink">None. Local use, no API key.</dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt className="text-faint">Determinism</dt>
                <dd className="text-ink">Same scenario and seed, same world.</dd>
              </div>
            </dl>
          </SectionCard>
        </div>
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <SectionCard
          title="Connect an external Python agent"
          hint="Four HTTP calls. No SDK or key is required."
          bodyClassName="flex flex-col gap-3"
        >
          <CodeBlock code={CONNECT_SNIPPET} language="bash" title="Agent loop with curl" maxHeightClass="max-h-[26rem]" />
          <p className="text-xs text-faint">
            Run the ready-made client from the project root:{" "}
            <code className="font-mono text-soft">python examples/agents/baseline_agent.py --scenario basic-delivery</code>
          </p>
        </SectionCard>

        <SectionCard
          title="Example agent scripts"
          hint="These files ship with the project under examples/agents."
          actions={
            exampleNames.length > 1 ? (
              <Tabs
                label="Example file"
                active={activeExample}
                onChange={setExample}
                tabs={exampleNames.map((name) => ({ id: name, label: name }))}
              />
            ) : undefined
          }
        >
          {activeExample ? (
            <CodeBlock code={data.examples[activeExample]} language="python" title={`examples/agents/${activeExample}`} maxHeightClass="max-h-[26rem]" />
          ) : (
            <p className="text-sm text-faint">No example scripts were found on the server.</p>
          )}
        </SectionCard>
      </div>

      <SectionCard
        title="Observation schema"
        hint="The exact structure of what an agent receives, generated from the Pydantic model."
      >
        <CodeBlock code={JSON.stringify(data.observation_schema, null, 2)} language="json" title="Observation (JSON Schema)" maxHeightClass="max-h-80" />
      </SectionCard>
    </div>
  );
}
