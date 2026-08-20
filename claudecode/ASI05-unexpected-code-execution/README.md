# ASI05 — Unexpected Code Execution (RCE)

> 에이전트가 실행 권한을 갖고 있다는 점을 악용한 임의 코드 실행.

**제품:** Claude Code (Anthropic)

## 검증한 기법

> 아래 판정은 **각 기법 단위**의 결론이다. 이 카테고리 전체가 '방어됨'을 뜻하지 않는다 — 밑의 **미탐색 표면**을 함께 볼 것.

| 기법 | 판정 | 상세 |
|---|---|---|
| .git/config core.fsmonitor pre-trust RCE | 🔴 LIVE? · ↗ external | 포인터(본문 없음) |

- **.git/config core.fsmonitor pre-trust RCE** — 제보/중복(Sonar 2026-04-30) 미확정(malhyuk). 라이브 PoC 민감 → 이 repo에서 본문 제외.

## 미탐색 표면 (open variants)

이 카테고리에서 아직 안 판 기법들. 검증한 게 있어도 카테고리가 '끝난' 건 아니다.

- ☐ A12 fsmonitor 재검증 + 중복 확인
- ☐ 다른 git-config 실행 벡터(core.pager, ext diff, 후크)
- ☐ .npmrc script-shell
- ☐ mise.toml / .envrc / pre-commit 자동툴
- ☐ find/CVE-2026-24887 명령 주입
- ☐ IDE 확장 자동 spawn
