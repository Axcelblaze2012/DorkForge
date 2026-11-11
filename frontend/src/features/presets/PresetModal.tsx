import { useEffect, useState, type FormEvent } from "react";

import { Modal } from "@/components/ui/Modal";
import {
  Button,
  Field,
  Input,
  Select,
  Textarea,
} from "@/components/ui/primitives";
import { presetScope } from "@/lib/query";
import { newId } from "@/lib/utils";
import { api } from "@/services/api";
import { useToast } from "@/stores/toast";
import { useWorkspace } from "@/stores/workspace";
import { CATEGORIES, type Category, type Preset } from "@/types";

export function PresetModal({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const [name, setName] = useState("");
  const [category, setCategory] = useState<Category>("Site Discovery");
  const [query, setQuery] = useState("");

  const addCustom = useWorkspace((state) => state.addCustom);
  const attachServerId = useWorkspace((state) => state.attachServerId);
  const setView = useWorkspace((state) => state.setView);
  const setCategoryFilter = useWorkspace((state) => state.setCategory);
  const apiBase = useWorkspace((state) => state.apiBase);
  const apiKey = useWorkspace((state) => state.apiKey);
  const online = useWorkspace((state) => state.server.status === "online");
  const showToast = useToast((state) => state.show);

  useEffect(() => {
    if (!open) return;
    setName("");
    setCategory("Site Discovery");
    setQuery("");
  }, [open]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const title = name.trim();
    const presetQuery = query.trim();
    if (!title || !presetQuery) {
      showToast("Add a name and a query");
      return;
    }

    const preset: Preset = {
      id: `c${newId()}`,
      title,
      description: "Custom search pattern saved in this workspace.",
      category,
      query: presetQuery,
      scope: presetScope(presetQuery),
      source: "custom",
    };

    addCustom(preset);
    setView("custom");
    setCategoryFilter("All");
    onClose();
    showToast("Preset saved locally");

    if (!online) return;

    void api
      .createPreset(
        { baseUrl: apiBase, apiKey },
        {
          title,
          description: preset.description,
          query: presetQuery,
          category,
        },
      )
      .then((created) => {
        attachServerId(preset.id, created.id);
        showToast("Preset saved to Atlas");
      })
      .catch(() => {
        showToast("Saved locally; Atlas sync failed");
      });
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Create a preset"
      description="Save a query pattern to your workspace"
      width="max-w-[480px]"
    >
      <form className="grid gap-4" onSubmit={handleSubmit}>
        <Field label="Preset name" htmlFor="preset-name">
          <Input
            id="preset-name"
            data-autofocus
            value={name}
            onChange={(event) => setName(event.target.value)}
            maxLength={80}
            required
            placeholder="e.g. Public policy documents"
          />
        </Field>

        <Field label="Category" htmlFor="preset-category">
          <Select
            id="preset-category"
            value={category}
            onChange={(event) => setCategory(event.target.value as Category)}
          >
            {CATEGORIES.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </Select>
        </Field>

        <Field label="Google query" htmlFor="preset-query">
          <Textarea
            id="preset-query"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            maxLength={500}
            required
            placeholder='site:{domain} filetype:pdf "annual report"'
            className="font-mono text-[13px]"
          />
        </Field>

        <p className="text-xs leading-relaxed text-fg-muted">
          Saved in this browser. Use{" "}
          <code className="font-mono text-accent">{"{domain}"}</code> as a
          placeholder for the target domain.
        </p>

        <div className="mt-2 flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary">
            Save preset
          </Button>
        </div>
      </form>
    </Modal>
  );
}
