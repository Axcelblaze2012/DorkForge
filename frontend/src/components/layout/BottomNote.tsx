import { ShieldCheck } from "lucide-react";

export function BottomNote() {
  return (
    <div className="mt-8 flex items-start gap-3 border-t border-line pt-5 text-xs leading-relaxed text-fg-muted">
      <ShieldCheck
        size={16}
        strokeWidth={1.5}
        className="mt-0.5 flex-none text-fg-secondary"
      />
      <span>
        <strong className="font-medium text-fg">Responsible use.</strong> Google
        dorks are search operators, not exploit vectors. This library
        intentionally excludes presets designed to target credentials or private
        records. Only investigate assets you own or have explicit authorization
        to assess.
      </span>
    </div>
  );
}
