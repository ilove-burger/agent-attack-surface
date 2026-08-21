# ASI06 — Memory & Context Poisoning

> 에이전트의 지속 메모리/컨텍스트에 악성 지시를 심어 나중에(며칠~몇 주 후) 실행되게 함.

**제품:** Codex (OpenAI)

## 검증한 기법

> 아래 판정은 개별 기법의 결론이다. ASI06 전체를 조사 완료했다는 뜻은 아니다.

| 기법 | 판정 | 상세 |
|---|---|---|
| MCP Resource provenance 누락을 통한 durable Memory와 cross-connector chain | 🔴 LIVE primitive / 조건부 full-chain | [mcp-resource-memory-cross-connector-exfiltration](mcp-resource-memory-cross-connector-exfiltration/) |

- **MCP Resource Memory poisoning** — `disable_on_external_context=true`가 일반 MCP tool에는 적용되지만
  Resource read/list/template/error에는 적용되지 않아 thread가 `enabled`로 남는다. 정상 TUI natural
  phase-1과 hardening 대조를 확인했고, 통제된 3-principal 환경에서 source→Memory→private registry→public
  observer canary 전송을 1/1 확인했다. 정상 배포의 phase-2/future chain 성공률은 미확정이다.

## 미탐색 표면 (open variants)

- ☐ 실제 SaaS tenant와 서로 다른 principal을 사용한 반복 cross-connector 검증
- ☐ web search/tool search/app result 등 다른 external-context provenance drift
- ☐ 이미 생성된 poisoned Memory의 revocation·cleanup·reindex 일관성
