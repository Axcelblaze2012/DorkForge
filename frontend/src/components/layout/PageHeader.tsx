import { Stat } from "@/components/ui/primitives";
import { BUILTIN_PRESETS } from "@/data/builtins";
import { useWorkspace } from "@/stores/workspace";

export function PageHeader() {
  const customCount = useWorkspace((state) => state.custom.length);

  return (
    <section className="mb-8 flex items-end justify-between gap-6 max-md:block">
      <div>
        <h1 className="max-w-[680px] text-[30px] font-medium leading-tight tracking-[-0.02em] text-fg max-sm:text-2xl">
          Find the signal in public search
        </h1>
        <p className="mt-2 max-w-[640px] text-sm leading-relaxed text-fg-secondary">
          Build precise Google queries, then run them on Google or your own
          Atlas server.
        </p>
      </div>

      <div className="flex flex-none gap-4 max-md:hidden">
        <Stat value={BUILTIN_PRESETS.length} label="Built-in dorks" />
        <Stat value={11} label="Quick operators" />
        <Stat value={customCount} label="Your presets" />
      </div>
    </section>
  );
}
