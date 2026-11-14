import { Compass } from "lucide-react";
import { lazy, Suspense } from "react";
import { Route, Routes } from "react-router-dom";

import { ButtonLink, Card, EmptyState, Spinner } from "@/components/ui/primitives";
import { AppLayout } from "@/layouts/AppLayout";
import { AgentStudio } from "@/pages/AgentStudio";
import { ApiDocs } from "@/pages/ApiDocs";
import { EvaluationReport } from "@/pages/EvaluationReport";
import { LiveSimulation, LiveSimulationEntry } from "@/pages/LiveSimulation";
import { Overview } from "@/pages/Overview";
import { RunHistory } from "@/pages/RunHistory";
import { ScenarioDetail } from "@/pages/ScenarioDetail";
import { ScenarioLibrary } from "@/pages/ScenarioLibrary";

// The charting and Markdown libraries are large, so these two pages load on demand.
const Evaluations = lazy(() => import("@/pages/Evaluations").then((module) => ({ default: module.Evaluations })));
const Workflows = lazy(() => import("@/pages/Workflows").then((module) => ({ default: module.Workflows })));

function NotFound() {
  return (
    <Card className="mx-auto mt-10 max-w-xl">
      <EmptyState
        icon={Compass}
        title="Page not found"
        text="That address does not match any page in SIMFORGE."
        action={
          <ButtonLink to="/" variant="primary">
            Back to the overview
          </ButtonLink>
        }
      />
    </Card>
  );
}

export function App() {
  return (
    <Suspense fallback={<Spinner />}>
      <AppRoutes />
    </Suspense>
  );
}

function AppRoutes() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<Overview />} />
        <Route path="scenarios" element={<ScenarioLibrary />} />
        <Route path="scenarios/:scenarioId" element={<ScenarioDetail />} />
        <Route path="simulation" element={<LiveSimulationEntry />} />
        <Route path="simulation/:episodeId" element={<LiveSimulation />} />
        <Route path="agents" element={<AgentStudio />} />
        <Route path="evaluations" element={<Evaluations />} />
        <Route path="evaluations/:episodeId" element={<EvaluationReport />} />
        <Route path="history" element={<RunHistory />} />
        <Route path="api-docs" element={<ApiDocs />} />
        <Route path="workflows" element={<Workflows />} />
        <Route path="workflows/:slug" element={<Workflows />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
