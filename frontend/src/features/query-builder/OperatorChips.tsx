const OPERATORS = [
  { op: "site:", label: "site:" },
  { op: "filetype:", label: "filetype:" },
  { op: "intitle:", label: "intitle:" },
  { op: "inurl:", label: "inurl:" },
  { op: "intext:", label: "intext:" },
  { op: "before:", label: "before:" },
  { op: "after:", label: "after:" },
  { op: "related:", label: "related:" },
  { op: "AROUND(3)", label: "AROUND(3)" },
  { op: " OR ", label: "OR" },
  { op: " -", label: "− exclude" },
];

export function OperatorChips({
  onInsert,
}: {
  onInsert: (operator: string) => void;
}) {
  return (
    <div className="mt-4 flex flex-wrap items-center gap-1.5 border-t border-line pt-4">
      <span className="mr-1.5 text-xs text-fg-muted">Quick operators</span>
      {OPERATORS.map((item) => (
        <button
          key={item.op}
          type="button"
          onClick={() => onInsert(item.op)}
          className="operator-chip"
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}
