# Codex — 커버리지 상세

상태 범례는 [루트 README](../README.md) 참고. 재현은 `hunma_agent` 하네스로 SHA-256 고정된
`@openai/codex` 아티팩트(`harness/versions/manifest.json`)를 상대로 한다.

## 여기서 검증함

| ID | 서피스 | 판정 | 하네스 |
|---|---|---|---|
| [CVE-2025-61260](cve-2025-61260-env-codexhome/) | 프로젝트 `.env`가 `CODEX_HOME` 재지정 → 로컬 MCP 자동 spawn | vuln/fixed/current 전 구간 재현 | `compare-codex-61260` (+ `-variants`) |

## Open / 후보 각도

새 Codex 각도는 CVE-2025-61260 하네스 위에서 탐색한다(config-reload, gitdir/commondir,
nested/symlink/worktree repo, session-resume, 사전 존재 CODEX_HOME 음성 대조군). `hunma_agent`의
`compare-codex-61260-variants` 케이스 매트릭스 참고. 아직 승격된 신규 Codex 발견은 없음.
