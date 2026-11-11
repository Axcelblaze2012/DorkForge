"""Seed the database with the original Dork Atlas built-in presets.

The 56 presets below are copied verbatim from Dork_Atlas_Final.html (the
`builtins` array). Their order and legacy ids ('b0'..'b55') are preserved so
legacy localStorage favorites migrate without losing a single entry.
"""

from __future__ import annotations

import re
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import QueryPreset

# (title, description, category, query, scope)
_RAW_PRESETS = [
    # Site discovery
    ["Indexed pages", "List pages Google has indexed for a domain.", "Site Discovery", "site:{domain}", "Scoped"],
    ["Subdomain index", "Explore indexed subdomains for an owned domain.", "Site Discovery", "site:*.{domain}", "Scoped"],
    ["Pages by title", "Find pages whose title contains a chosen term.", "Site Discovery", "site:{domain} intitle:overview", "Scoped"],
    ["URL path discovery", "Find indexed pages with a path keyword.", "Site Discovery", "site:{domain} inurl:blog", "Scoped"],
    ["Exclude a section", "Review indexed pages while excluding one site section.", "Site Discovery", "site:{domain} -inurl:blog", "Scoped"],
    ["Recently indexed pages", "Narrow indexed pages to a recent time window.", "Site Discovery", "site:{domain} after:2025-01-01", "Scoped"],
    ["Exact phrase on site", "Find a known phrase on a specific public site.", "Site Discovery", 'site:{domain} "annual overview"', "Scoped"],
    ["Related public sites", "Find sites Google considers related to a domain.", "Site Discovery", "related:{domain}", "Scoped"],
    ["URL with a file path", "Search a site for a known public path or slug.", "Site Discovery", "site:{domain} inurl:resources", "Scoped"],
    # Documents
    ["Public PDF documents", "Discover publicly indexed PDF files.", "Public Documents", "site:{domain} filetype:pdf", "Scoped"],
    ["Word documents", "Find public DOC and DOCX documents.", "Public Documents", "site:{domain} (filetype:doc OR filetype:docx)", "Scoped"],
    ["Presentation files", "Find public PowerPoint presentations.", "Public Documents", "site:{domain} (filetype:ppt OR filetype:pptx)", "Scoped"],
    ["Spreadsheet files", "Find public spreadsheet documents.", "Public Documents", "site:{domain} (filetype:xls OR filetype:xlsx OR filetype:csv)", "Scoped"],
    ["Public text resources", "Find publicly indexed TXT resources.", "Public Documents", "site:{domain} filetype:txt", "Scoped"],
    ["Annual reports", "Find public annual-report documents.", "Public Documents", 'site:{domain} ("annual report" OR "annual review") filetype:pdf', "Scoped"],
    ["Public user manuals", "Find manuals and user guides.", "Public Documents", 'site:{domain} (manual OR "user guide") filetype:pdf', "Scoped"],
    ["Public policy documents", "Find public policies and governance documents.", "Public Documents", "site:{domain} (policy OR guidelines) filetype:pdf", "Scoped"],
    ["Research publications", "Locate research papers and publications.", "Public Documents", "site:{domain} (research OR publication) filetype:pdf", "Scoped"],
    ["Public datasets", "Find datasets described on a public domain.", "Public Documents", "site:{domain} (dataset OR data portal) (CSV OR XLSX)", "Scoped"],
    ["Public XML resources", "Find publicly indexed XML resources.", "Public Documents", "site:{domain} filetype:xml", "Scoped"],
    # Technology
    ["WordPress footprint", "Identify publicly visible WordPress asset references.", "Technology", 'site:{domain} "wp-content"', "Scoped"],
    ["Drupal footprint", "Identify publicly visible Drupal path references.", "Technology", 'site:{domain} "sites/default/files"', "Scoped"],
    ["Shopify footprint", "Find public pages referencing Shopify assets.", "Technology", "site:{domain} myshopify.com", "Scoped"],
    ["Next.js assets", "Find indexed references to public Next.js assets.", "Technology", 'site:{domain} "_next/static"', "Scoped"],
    ["Published JavaScript", "Find JavaScript files indexed from a site.", "Technology", "site:{domain} filetype:js", "Scoped"],
    ["Public CSS assets", "Find published stylesheet references.", "Technology", "site:{domain} filetype:css", "Scoped"],
    ["API documentation", "Find public API reference and documentation pages.", "Technology", "site:{domain} (inurl:api OR intitle:API) (docs OR reference)", "Scoped"],
    ["Developer documentation", "Find public developer guides and docs.", "Technology", "site:{domain} (developer OR documentation) (guide OR reference)", "Scoped"],
    ["Release notes", "Find public product release notes and changelogs.", "Technology", 'site:{domain} (intitle:changelog OR "release notes")', "Scoped"],
    ["Sitemap references", "Find pages mentioning public sitemap resources.", "Technology", 'site:{domain} (inurl:sitemap OR "sitemap.xml")', "Scoped"],
    # Content research
    ["Blog archive", "Find public blog pages and archives.", "Content Research", "site:{domain} inurl:blog", "Scoped"],
    ["Author pages", "Find public author or contributor pages.", "Content Research", "site:{domain} (inurl:author OR inurl:team)", "Scoped"],
    ["Case studies", "Find public case studies and customer stories.", "Content Research", 'site:{domain} ("case study" OR "customer story")', "Scoped"],
    ["Press releases", "Find public press releases and media updates.", "Content Research", 'site:{domain} ("press release" OR newsroom)', "Scoped"],
    ["FAQ pages", "Find frequently asked questions.", "Content Research", 'site:{domain} (intitle:FAQ OR "frequently asked questions")', "Scoped"],
    ["Events and webinars", "Find public event and webinar pages.", "Content Research", "site:{domain} (webinar OR event OR conference)", "Scoped"],
    ["Job and career pages", "Find public careers and hiring pages.", "Content Research", "site:{domain} (careers OR vacancies OR jobs)", "Scoped"],
    ["Contact information pages", "Find official public contact pages.", "Content Research", "site:{domain} (inurl:contact OR intitle:Contact)", "Scoped"],
    ["Accessibility statements", "Find public accessibility information.", "Content Research", 'site:{domain} ("accessibility statement" OR accessibility)', "Scoped"],
    ["Multilingual pages", "Find language-specific public pages.", "Content Research", "site:{domain} (inurl:en OR inurl:hi)", "Scoped"],
    # Safe security and policy
    ["Security.txt policy", "Locate a published security contact policy.", "Security & Policy", 'site:{domain} "security.txt"', "Scoped"],
    ["Responsible disclosure", "Find public vulnerability disclosure guidance.", "Security & Policy", 'site:{domain} ("responsible disclosure" OR "vulnerability disclosure")', "Scoped"],
    ["Bug bounty program", "Find an official public bug bounty program page.", "Security & Policy", 'site:{domain} ("bug bounty" OR "security rewards")', "Scoped"],
    ["Privacy policy", "Find the public privacy notice.", "Security & Policy", 'site:{domain} (intitle:privacy OR "privacy policy")', "Scoped"],
    ["Terms of service", "Find the public terms of service.", "Security & Policy", 'site:{domain} ("terms of service" OR "terms of use")', "Scoped"],
    ["Security advisories", "Find published security advisories from a vendor.", "Security & Policy", 'site:{domain} ("security advisory" OR "security bulletin")', "Scoped"],
    ["Patch and update notes", "Find public patch notes and update notices.", "Security & Policy", "site:{domain} (patch OR update) (advisory OR bulletin)", "Scoped"],
    ["CVE references", "Find public CVE references on a vendor site.", "Security & Policy", "site:{domain} CVE", "Scoped"],
    ["Security standards", "Find public references to security standards.", "Security & Policy", 'site:{domain} ("ISO 27001" OR "SOC 2" OR "security standard")', "Scoped"],
    ["TLS guidance", "Find public TLS and HTTPS implementation guidance.", "Security & Policy", 'site:{domain} ("TLS 1.3" OR HSTS OR HTTPS) (guide OR policy)', "Scoped"],
    # Learning
    ["Google operator guide", "Find official help for Google search operators.", "Learning", 'site:support.google.com/websearch "refine web searches"', "General"],
    ["OWASP documentation", "Find public OWASP guidance and documentation.", "Learning", "site:owasp.org (cheat sheet OR guide OR documentation)", "General"],
    ["NIST publications", "Find public NIST cybersecurity publications.", "Learning", "site:nist.gov cybersecurity filetype:pdf", "General"],
    ["CISA advisories", "Find public CISA alerts and advisories.", "Learning", "site:cisa.gov (alert OR advisory) filetype:pdf", "General"],
    ["RFC specifications", "Find public RFC technical specifications.", "Learning", "site:rfc-editor.org (protocol OR security) filetype:txt", "General"],
    ["Academic research papers", "Find academic papers by topic across public sources.", "Learning", '"{topic}" (research paper OR study) filetype:pdf', "General"],
]

CATEGORIES = [
    "Site Discovery",
    "Public Documents",
    "Technology",
    "Content Research",
    "Security & Policy",
    "Learning",
]


def _slugify(title: str, index: int) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return f"b{index}-{base}"


def builtin_presets() -> list[dict]:
    presets = []
    for i, (title, desc, category, query, scope) in enumerate(_RAW_PRESETS):
        presets.append(
            {
                "slug": _slugify(title, i),
                "title": title,
                "description": desc,
                "query": query,
                "category": category,
                "scope": scope,
                "tags": [],
                "source": "builtin",
                "legacy_id": f"b{i}",
            }
        )
    return presets


async def seed_presets(session: AsyncSession) -> int:
    """Insert built-in presets that do not exist yet. Returns number added."""
    added = 0
    existing_slugs = set(
        (await session.execute(select(QueryPreset.slug))).scalars().all()
    )
    existing_legacy = set(
        (
            await session.execute(
                select(QueryPreset.legacy_id).where(QueryPreset.legacy_id.isnot(None))
            )
        )
        .scalars()
        .all()
    )
    for data in builtin_presets():
        if data["slug"] in existing_slugs or data["legacy_id"] in existing_legacy:
            continue
        session.add(QueryPreset(**data))
        added += 1
    await session.flush()
    return added


async def ensure_seeded(session: AsyncSession) -> int:
    """Idempotent seed used at startup."""
    count = (
        await session.execute(select(func.count()).select_from(QueryPreset))
    ).scalar_one()
    if count == 0:
        return await seed_presets(session)
    return 0
