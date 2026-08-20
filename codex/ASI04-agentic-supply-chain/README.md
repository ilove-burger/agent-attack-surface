# ASI04 — Agentic Supply Chain Vulnerabilities

> 동적으로 발견·통합되는 도구/MCP 서버 생태계가 오염됨. GitHub MCP exploit이 대표 사례.

**제품:** Codex (OpenAI)

## 검증한 기법

> 아래 판정은 **각 기법 단위**의 결론이다. 이 카테고리 전체가 '방어됨'을 뜻하지 않는다 — 밑의 **미탐색 표면**을 함께 볼 것.

| 기법 | 판정 | 상세 |
|---|---|---|
| 프로젝트 .env가 CODEX_HOME 재지정 → 로컬 MCP spawn | 🟢 재현 | [cve-2025-61260-env-codexhome](cve-2025-61260-env-codexhome/) |

- **프로젝트 .env가 CODEX_HOME 재지정 → 로컬 MCP spawn** — vuln 0.21.0 / fixed 0.22.0 / current 0.147.0 3-tier golden target. 알려진 패치 CVE. 하네스: `compare-codex-61260`.

## 미탐색 표면 (open variants)

이 카테고리에서 아직 안 판 기법들. 검증한 게 있어도 카테고리가 '끝난' 건 아니다.

- ☐ 다른 CODEX_HOME 재지정 벡터(variants 매트릭스 일부만 진행)
- ☐ repo 내 .codex/config.toml
- ☐ Codex MCP 서버 정의 오염
- ☐ 플러그인/npm 공급망
