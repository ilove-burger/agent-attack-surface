# ASI05 — Unexpected Code Execution (RCE)

> 에이전트가 실행 권한을 갖고 있다는 점을 악용한 임의 코드 실행.

**제품:** Codex (OpenAI)

## 검증한 기법

> 아래 판정은 **각 기법 단위**의 결론이다. 이 카테고리 전체가 다 조사됐다는 뜻이 아니다 — 밑의 **미탐색 표면**을 함께 볼 것.

| 기법 | 판정 | 상세 |
|---|---|---|
| 승인된 project hook의 대상 스크립트 치환 | 🔴 LIVE (제보 예정) | [hook-target-script-substitution](hook-target-script-substitution/) |

- **hook 대상 스크립트 치환** — hook 신뢰 해시가 hook 정의만 커버하고 참조 스크립트 내용을 제외 →
  승인된 hook의 스크립트를 교체하면 재승인 없이 command sandbox 밖 same-user 실행. 소스+unit test+
  E2E(bypass 없는 faithful 포함) 4단 재현. 0.148.0 LIVE. Secondary: ASI02.

## 미탐색 표면 (open variants)

이 카테고리에서 아직 안 판 기법들. 검증한 게 있어도 카테고리가 '끝난' 건 아니다.

- ☐ ancestor relocation → 보호된 `.codex` 변조 → stdio MCP 명령 실행 (Path/Filesystem 계열; 소스+baseline live, E2E 남음)
- ☐ 승인된 명령의 인자 확장 LOLBin (sed `e`/`w`, rg `--pre` 등) — Command/Capability 계열
- ☐ 세션 승인 후 대상 파일/스크립트 치환 (shell approval 캐시)
- ☐ 다른 pre-trust 자동 실행 벡터
