# Dork Atlas Ultimate — Security & Privacy Specification

## 1. Responsible Use & Scope Policy

Dork Atlas Ultimate is an intelligence discovery and public-web research platform.
- **Search Operators, Not Exploits**: The platform intentionally excludes presets designed to target credentials, private records, or administrative backdoors.
- **Scope Restriction**: Security research must be restricted to assets owned by the researcher or where explicit written permission has been obtained.
- **No Automated Exploitation**: The platform does not attempt brute forcing, credential access, authentication bypass, or private data harvesting.

---

## 2. Backend Security Measures

- **Zero Secret Exposure**: Search API keys (Brave, AI provider keys) reside exclusively on the server and are masked in diagnostic outputs (`mask_key`). No API secrets are exposed to client JavaScript bundles.
- **SSRF Protection**: Crawler and document retrieval pipelines restrict DNS resolution, prohibiting RFC 1918 private network addresses, loopback addresses (`127.0.0.1`, `localhost`), link-local addresses (`169.254.169.254`), and cloud metadata endpoints.
- **Request Size Limiting**: `RequestSizeLimitMiddleware` terminates requests with bodies exceeding 512 KB to mitigate denial-of-service attempts.
- **Rate Limiting**: Bounded sliding-window IP rate limiter protects against abusive request bursts.
- **SQL Injection Prevention**: All database access uses SQLAlchemy 2.0 parameterized queries and ORM mappings.
- **Security Headers**: Injected on all HTTP responses:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `Permissions-Policy: geolocation=(), camera=(), microphone=()`

---

## 3. Privacy & Data Portability

- **Local-First Architecture**: Local development operates entirely without external analytics or user tracking.
- **Data Export & Erasure**: Users can export their entire search history and preset collections as JSON or clear them at any time.
- **History Retention**: Configurable automated pruning deletes unpinned searches older than the retention threshold (default 180 days).

---

## 4. Reporting Security Vulnerabilities

To report a vulnerability or security issue, please open a private security advisory or contact the project maintainers with reproduction steps and scope details.
