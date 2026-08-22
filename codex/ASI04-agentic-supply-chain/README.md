# ASI04 — Agentic Supply Chain Vulnerabilities

> 동적으로 발견·통합되는 도구/MCP 서버 생태계가 오염됨. GitHub MCP exploit이 대표 사례.

**제품:** Codex (OpenAI)

## 검증한 기법

> 아래 판정은 **각 기법 단위**의 결론이다. 이 카테고리 전체가 '방어됨'을 뜻하지 않는다 — 밑의 **미탐색 표면**을 함께 볼 것.

| 기법 | 판정 | 상세 |
|---|---|---|
| 프로젝트 .env가 CODEX_HOME 재지정 → 로컬 MCP spawn | 🟢 재현 | [cve-2025-61260-env-codexhome](cve-2025-61260-env-codexhome/) |
| project-local model_instructions_file → 프로젝트 밖 파일 읽기 → 모델 instructions 주입 | 🔴 LIVE(미패치 후보, 수정안 자체 검증) | [project-model-instructions-outside-read](project-model-instructions-outside-read/) |

- **프로젝트 .env가 CODEX_HOME 재지정 → 로컬 MCP spawn** — vuln 0.21.0 / fixed 0.22.0 / current 0.147.0 3-tier golden target. 알려진 패치 CVE. 하네스: `compare-codex-61260`.
- **project-local model_instructions_file → 프로젝트 밖 파일 읽기 → 모델 instructions 주입** — 최초
  취약 stable `0.78.0`, 최신 `0.149.0`까지 재현(3/3 UI trust E2E + strace 런타임 검증). containment
  수정안 + 회귀 테스트 자체 작성·검증 완료(`cargo test -p codex-config` 261/261). lexical
  containment라 symlink 변형은 미방어로 남음.

## 미탐색 표면 (open variants)

이 카테고리에서 아직 안 판 기법들. 검증한 게 있어도 카테고리가 '끝난' 건 아니다.

- ☐ 다른 CODEX_HOME 재지정 벡터(variants 매트릭스 일부만 진행)
- ☐ Codex MCP 서버 정의 오염
- ☐ 플러그인/npm 공급망
- ☐ model_instructions_file의 symlink containment 우회(lexical 체크만 존재, canonicalize 미적용)
