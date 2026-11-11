import { tokenizeQuery, type QueryTokenKind } from "@/lib/query";
import { cn } from "@/lib/utils";

const TOKEN_CLASS: Record<QueryTokenKind, string> = {
  text: "text-fg",
  operator: "text-accent",
  phrase: "text-fg",
  boolean: "text-fg-secondary",
  exclude: "text-danger",
};

export function QueryText({
  query,
  className,
  placeholder,
}: {
  query: string;
  className?: string;
  placeholder?: string;
}) {
  if (!query) {
    return (
      <code className={cn("font-mono", className)}>
        <span className="text-fg-muted">{placeholder}</span>
      </code>
    );
  }

  return (
    <code className={cn("font-mono", className)}>
      {tokenizeQuery(query).map((token, index) => (
        <span key={index} className={TOKEN_CLASS[token.kind]}>
          {token.text}
        </span>
      ))}
    </code>
  );
}
