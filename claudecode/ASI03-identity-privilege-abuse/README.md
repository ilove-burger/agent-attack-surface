# ASI03 — Identity & Privilege Abuse

> 에이전트의 신원/권한을 도용하거나 과도한 권한을 악용.

**제품:** Claude Code (Anthropic)  ·  **상태:** ✅ 조사됨

| ID | 서피스 | 상태 | 상세 |
|---|---|---|---|
| A01 | claude-cli:// 딥링크 --settings 재주입 | ⚪ PATCHED · ↗ external | 포인터 (본문 없음) |
| A04 | NM7 헬퍼 non-interactive trust 우회 실행 | 🟡 INFO · ↗ external | 포인터 (본문 없음) |

- **A01** — malhyuk; ≤2.1.117 수정. 포인터.
- **A04** — malhyuk; '문서화된 --print 동작'일 가능성. 포인터.
