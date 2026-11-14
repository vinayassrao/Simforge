import clsx from "clsx";
import { Fragment, type ReactNode } from "react";

import { CopyButton } from "@/components/ui/primitives";

type Language = "json" | "python" | "bash" | "text";

const TOKEN_CLASSES = {
  key: "text-sky-300",
  string: "text-emerald-300",
  number: "text-amber-300",
  keyword: "text-fuchsia-300",
  comment: "text-slate-500 italic",
} as const;

const PATTERNS: Record<Exclude<Language, "text">, RegExp> = {
  json: /("(?:[^"\\]|\\.)*")(\s*:)?|\b(true|false|null)\b|(-?\d+(?:\.\d+)?)/g,
  python:
    /(#.*$)|("""[\s\S]*?"""|"(?:[^"\\\n]|\\.)*"|'(?:[^'\\\n]|\\.)*')|\b(def|class|return|import|from|if|elif|else|for|while|in|not|and|or|None|True|False|with|as|try|except|raise|break|continue|pass|lambda)\b|\b(\d+(?:\.\d+)?)\b/gm,
  bash: /(#.*$)|("(?:[^"\\]|\\.)*"|'[^']*')|\b(curl|python|pip|npm|cd|export|set)\b|(\s-{1,2}[\w-]+)/gm,
};

/** Small, dependency-free syntax highlighting for the three languages the app shows. */
function highlight(code: string, language: Language): ReactNode {
  if (language === "text") return code;
  const pattern = new RegExp(PATTERNS[language]);
  const parts: ReactNode[] = [];
  let cursor = 0;
  for (const match of code.matchAll(pattern)) {
    const index = match.index ?? 0;
    if (index > cursor) parts.push(code.slice(cursor, index));
    const [text, first, second, third] = match;
    if (language === "json" && first && second) {
      // A string followed by a colon is an object key; keep the colon unstyled.
      parts.push(
        <span key={index} className={TOKEN_CLASSES.key}>
          {first}
        </span>,
        second,
      );
    } else {
      const token: keyof typeof TOKEN_CLASSES =
        language === "json"
          ? first
            ? "string"
            : third
              ? "keyword"
              : "number"
          : first
            ? "comment"
            : second
              ? "string"
              : third
                ? "keyword"
                : "number";
      parts.push(
        <span key={index} className={TOKEN_CLASSES[token]}>
          {text}
        </span>,
      );
    }
    cursor = index + text.length;
  }
  if (cursor < code.length) parts.push(code.slice(cursor));
  return parts.map((part, index) => <Fragment key={index}>{part}</Fragment>);
}

interface CodeBlockProps {
  code: string;
  language?: Language;
  title?: string;
  className?: string;
  maxHeightClass?: string;
}

export function CodeBlock({ code, language = "text", title, className, maxHeightClass = "max-h-96" }: CodeBlockProps) {
  return (
    <figure className={clsx("min-w-0 overflow-hidden rounded-lg border border-line bg-[#0b1220]", className)}>
      <figcaption className="flex items-center justify-between gap-2 border-b border-line bg-raised px-3 py-1.5">
        <span className="truncate font-mono text-xs text-faint">{title ?? language}</span>
        <CopyButton text={code} />
      </figcaption>
      <pre
        tabIndex={0}
        className={clsx("overflow-auto p-3 font-mono text-[0.78rem] leading-relaxed text-slate-200", maxHeightClass)}
      >
        <code>{highlight(code, language)}</code>
      </pre>
    </figure>
  );
}
