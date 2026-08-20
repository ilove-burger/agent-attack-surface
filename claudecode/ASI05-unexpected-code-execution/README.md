# ASI05 — Unexpected Code Execution (RCE)

> 에이전트가 실행 권한을 갖고 있다는 점을 악용한 임의 코드 실행.

**제품:** Claude Code (Anthropic)  ·  **상태:** ✅ 조사됨

| ID | 서피스 | 상태 | 상세 |
|---|---|---|---|
| A12 | .git/config core.fsmonitor pre-trust RCE | 🔴 LIVE? · ↗ external | 포인터 (본문 없음) |

- **A12** — malhyuk; 제보/중복(Sonar 2026-04-30) 미확정. 라이브 리버스셸 PoC가 민감 → 이 repo에서 **제외**.
