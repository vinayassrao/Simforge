import clsx from "clsx";
import { BookOpen } from "lucide-react";
import { useMemo } from "react";
import ReactMarkdown from "react-markdown";
import { NavLink, useParams } from "react-router-dom";
import remarkGfm from "remark-gfm";

import { Card, EmptyState, ErrorNote, PageHeader, Spinner } from "@/components/ui/primitives";
import { useApi } from "@/hooks/useApi";
import { api } from "@/services/api";
import type { DocumentSummary } from "@/types/api";

export function groupDocuments(documents: DocumentSummary[]): [string, DocumentSummary[]][] {
  const groups = new Map<string, DocumentSummary[]>();
  for (const document of documents) {
    groups.set(document.group, [...(groups.get(document.group) ?? []), document]);
  }
  return [...groups.entries()];
}

function DocumentBody({ slug }: { slug: string }) {
  const { data, error, loading, reload } = useApi(() => api.document(slug), [slug]);
  if (loading) return <Spinner label="Loading the guide" />;
  if (error || !data) return <ErrorNote message={error ?? "Guide not found."} onRetry={reload} />;
  return (
    <article className="prose-doc">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{data.content}</ReactMarkdown>
    </article>
  );
}

export function Workflows() {
  const { slug } = useParams();
  const { data, error, loading, reload } = useApi(api.documents);
  const groups = useMemo(() => groupDocuments(data ?? []), [data]);
  const activeSlug = slug ?? data?.[0]?.slug;

  return (
    <div className="mx-auto max-w-7xl">
      <PageHeader
        title="Workflows & Tutorials"
        subtitle="Step-by-step guides to how SIMFORGE is built and how to use it, plus reusable task specifications for AI coding agents."
      />
      {loading && <Spinner label="Loading guides" />}
      {error && <ErrorNote message={error} onRetry={reload} />}
      {data && data.length === 0 && (
        <Card>
          <EmptyState icon={BookOpen} title="No guides found" text="The server could not find the docs folder." />
        </Card>
      )}
      {data && data.length > 0 && (
        <div className="grid gap-5 lg:grid-cols-[17rem_minmax(0,1fr)]">
          <nav aria-label="Guides" className="lg:sticky lg:top-20 lg:max-h-[calc(100vh-6rem)] lg:overflow-y-auto">
            <Card className="p-3">
              {groups.map(([group, documents]) => (
                <div key={group} className="mb-3 last:mb-0">
                  <h2 className="px-2 pb-1 text-[0.7rem] font-semibold uppercase tracking-wide text-faint">{group}</h2>
                  <ul>
                    {documents.map((document) => (
                      <li key={document.slug}>
                        <NavLink
                          to={`/workflows/${document.slug}`}
                          className={({ isActive }) =>
                            clsx(
                              "block rounded-md px-2 py-1.5 text-sm transition-colors",
                              isActive || document.slug === activeSlug
                                ? "bg-accent/10 font-medium text-accent"
                                : "text-soft hover:bg-raised hover:text-ink",
                            )
                          }
                        >
                          {document.title}
                        </NavLink>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </Card>
          </nav>
          <Card className="min-w-0 p-5 sm:p-7">{activeSlug && <DocumentBody slug={activeSlug} />}</Card>
        </div>
      )}
    </div>
  );
}
