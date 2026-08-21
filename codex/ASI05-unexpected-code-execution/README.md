# ASI05 — Unexpected Code Execution (RCE)

> 에이전트가 실행 권한을 갖고 있다는 점을 악용한 임의 코드 실행.

**제품:** Codex (OpenAI)

## 검증한 기법

> 아래 판정은 **각 기법 단위**의 결론이다. 이 카테고리 전체가 다 조사됐다는 뜻이 아니다 — 밑의 **미탐색 표면**을 함께 볼 것.

| 기법 | 판정 | 상세 |
|---|---|---|
| 승인된 project hook의 대상 스크립트 치환 | 🔴 LIVE (제보 예정) | [hook-target-script-substitution](hook-target-script-substitution/) |
| writable ancestor relocation을 통한 `.codex` 보호 우회와 stdio MCP 실행 | 🔴 LIVE (0.147.0, 10/10) | [ancestor-relocation-mcp-rce](ancestor-relocation-mcp-rce/) |
| client-known cloud-config HMAC을 통한 다음 실행 policy escalation | 🔴 LIVE (배치 조건부, 6/6) | [cloud-config-policy-escalation](cloud-config-policy-escalation/) |
| direct full-network에서 App Server Unix socket confused deputy | 🔴 LIVE (조건부, UID 1000 E2E) | [full-network-uds-rce](full-network-uds-rce/) |
| GNU sed suffix를 통한 persistent prefix approval scope 확장 | 🔴 LIVE (0.148.0 policy 재현) | [sed-prefix-rule-rce](sed-prefix-rule-rce/) |

- **hook 대상 스크립트 치환** — hook 신뢰 해시가 hook 정의만 커버하고 참조 스크립트 내용을 제외 →
  승인된 hook의 스크립트를 교체하면 재승인 없이 command sandbox 밖 same-user 실행. 소스+unit test+
  E2E(bypass 없는 faithful 포함) 4단 재현. 0.148.0 LIVE. Secondary: ASI02.

- **ancestor relocation MCP RCE** — rename 가능한 writable ancestor와 decoy를 두 sandbox 호출 사이에
  배치해 실제 project `.codex`의 read-only carveout을 우회하고, fresh session의 stdio MCP startup으로
  same-user host execution. 0.147.0 disposable Docker 10/10. Secondary: ASI02.

- **cloud-config policy escalation** — 모든 client가 아는 대칭 HMAC key로 enterprise cache를 위조하고,
  writable custom `CODEX_HOME`을 거쳐 다음 process를 `Never + DangerFullAccess`로 전환. 내부/actual CLI
  test 6/6. 배치 조건을 보고서에 명시. Secondary: ASI03, ASI06.

- **full-network UDS RCE** — direct full-network가 AF_UNIX 격리도 제거하고 동일 UID App Server가 peer를
  인증하지 않아 `process/spawn`/`fs/writeFile` deputy가 됨. restricted/proxy 대조군과 UID 1000 VM
  full-chain 확인. Secondary: ASI02, ASI03.

- **sed prefix-rule RCE** — 승인된 fixed-read argv prefix 뒤 GNU sed `-e` shell capability를 붙여도
  기존 allow가 재사용되고 unsandboxed escalation으로 이어짐. 0.147.0 impact, 0.148.0 policy oracle 확인.
  Secondary: ASI02.

## 미탐색 표면 (open variants)

이 카테고리에서 아직 안 판 기법들. 검증한 게 있어도 카테고리가 '끝난' 건 아니다.

- ☐ 세션 승인 후 대상 파일/스크립트 치환 (shell approval 캐시)
- ☐ 다른 pre-trust 자동 실행 벡터
