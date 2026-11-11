import { useEffect } from "react";

export function useHotkeys(): void {
  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const typing = target
        ? ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName) ||
          target.isContentEditable
        : false;

      if (
        event.key === "/" &&
        !typing &&
        !event.metaKey &&
        !event.ctrlKey &&
        !event.altKey
      ) {
        event.preventDefault();
        document.getElementById("catalog-search")?.focus();
      }
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);
}
