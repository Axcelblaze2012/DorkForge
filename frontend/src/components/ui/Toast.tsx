import { useToast } from "@/stores/toast";

export function Toast() {
  const message = useToast((state) => state.message);
  if (!message) return null;

  return (
    <div className="toast animate-fade-up" role="status" aria-live="polite">
      {message}
    </div>
  );
}
