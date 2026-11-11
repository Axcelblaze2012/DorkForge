import { describe, expect, it } from "vitest";

import {
  cleanDomain,
  resolveTemplate,
  buildQuery,
  localOperators,
} from "../src/lib/query";
import { BUILTIN_PRESETS } from "../src/data/builtins";

describe("Dork Atlas Query & Builtin Library", () => {
  it("preserves all 56 built-in presets across original 6 categories", () => {
    expect(BUILTIN_PRESETS.length).toBe(56);
    const categories = new Set(BUILTIN_PRESETS.map((p) => p.category));
    expect(categories.has("Site Discovery")).toBe(true);
    expect(categories.has("Public Documents")).toBe(true);
    expect(categories.has("Technology")).toBe(true);
    expect(categories.has("Content Research")).toBe(true);
    expect(categories.has("Security & Policy")).toBe(true);
    expect(categories.has("Learning")).toBe(true);
  });

  it("normalizes domains correctly", () => {
    expect(cleanDomain("https://www.example.com/path")).toBe("example.com");
    expect(cleanDomain("http://sub.domain.org/")).toBe("sub.domain.org");
    expect(cleanDomain("  spaced.com  ")).toBe("spaced.com");
  });

  it("resolves template placeholders {domain} and {topic}", () => {
    const tpl = "site:{domain} filetype:pdf {topic}";
    const resolved = resolveTemplate(tpl, "https://test.org", "quarterly earnings");
    expect(resolved).toBe("site:test.org filetype:pdf quarterly earnings");
  });

  it("builds structured dork queries from composer fields", () => {
    const fields = {
      terms: "annual report",
      domain: "https://example.com",
      filetype: "pdf",
      titleTerm: "financial",
      urlTerm: "investors",
      exactPhrase: "audited balance sheet",
      excludeTerm: "draft",
      timeRange: "",
      region: "US",
    };
    const q = buildQuery(fields);
    expect(q).toContain("annual report");
    expect(q).toContain("site:example.com");
    expect(q).toContain("filetype:pdf");
    expect(q).toContain("intitle:financial");
    expect(q).toContain("inurl:investors");
    expect(q).toContain('"audited balance sheet"');
    expect(q).toContain("-draft");
  });

  it("extracts active local operators correctly", () => {
    const fields = {
      terms: "keyword",
      domain: "example.com",
      filetype: "pdf",
      titleTerm: "",
      urlTerm: "",
      exactPhrase: "",
      excludeTerm: "spam",
      timeRange: "",
      region: "IN",
    };
    const ops = localOperators(fields);
    expect(ops).toEqual(["filetype", "site"]);
  });
});
