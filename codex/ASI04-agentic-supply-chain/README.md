# ASI04 — Agentic Supply Chain Vulnerabilities

> 동적으로 발견·통합되는 도구/MCP 서버 생태계가 오염됨. GitHub MCP exploit이 대표 사례.

**제품:** Codex (OpenAI)  ·  **상태:** ✅ 조사됨

| ID | 서피스 | 상태 | 상세 |
|---|---|---|---|
| CVE-2025-61260 | 프로젝트 .env가 CODEX_HOME 재지정 → 로컬 MCP 자동 spawn | 🟢 재현 (golden target) | [cve-2025-61260-env-codexhome](cve-2025-61260-env-codexhome/) |

- **CVE-2025-61260** — vuln 0.21.0 / fixed 0.22.0 / current 0.147.0 3-tier 재현. 알려진 패치 CVE. 하네스: `compare-codex-61260`.
