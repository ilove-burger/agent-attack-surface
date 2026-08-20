# ASI03 — Identity & Privilege Abuse

> 에이전트의 신원/권한을 도용하거나 과도한 권한을 악용.

**제품:** Claude Code (Anthropic)

## 검증한 기법

> 아래 판정은 **각 기법 단위**의 결론이다. 이 카테고리 전체가 '방어됨'을 뜻하지 않는다 — 밑의 **미탐색 표면**을 함께 볼 것.

| 기법 | 판정 | 상세 |
|---|---|---|
| claude-cli:// 딥링크 --settings 재주입 | ⚪ PATCHED · ↗ external | 포인터(본문 없음) |
| NM7 헬퍼 non-interactive trust 우회 실행 | 🟡 INFO · ↗ external | 포인터(본문 없음) |

- **claude-cli:// 딥링크 --settings 재주입** — ≤2.1.117 수정(malhyuk). 포인터.
- **NM7 헬퍼 non-interactive trust 우회 실행** — '문서화된 --print 동작' 가능성(malhyuk). 포인터.

## 미탐색 표면 (open variants)

이 카테고리에서 아직 안 판 기법들. 검증한 게 있어도 카테고리가 '끝난' 건 아니다.

- ☐ env/헤더로 자격증명·토큰 유출
- ☐ OAuth 콜백 파라미터 인젝션
- ☐ settings.json 권한 주입
- ☐ --dangerously-skip-permissions 유도
- ☐ 상위 경로 trust 상속
- ☐ MCP OAuth 토큰 오용
