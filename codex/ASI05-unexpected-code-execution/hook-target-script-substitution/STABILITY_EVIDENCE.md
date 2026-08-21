# 실제 UI/API 승인 E2E 안정성 증거

> 실행 시각: 2026-08-21 05:45:11–05:46:14 KST
> 판정: **PASS — UI 3/3 + API 3/3, 총 6/6**

## 고정 대상과 환경

| 항목 | 값 |
|---|---|
| Codex | `codex-cli 0.148.0` |
| Binary SHA-256 | `ac2cfed85fb647d61e0150b8548102b330e4799d9d81ad5d354de701edf6b074` |
| OS | `Linux-6.18.33.1-microsoft-standard-WSL2-x86_64-with-glibc2.35` |
| Kernel | `6.18.33.1-microsoft-standard-WSL2` |
| Python | `3.10.12` |
| Event | `SessionStart` |
| Trust bypass | 사용하지 않음 |

각 run은 별도 project, fake `HOME`, `CODEX_HOME`, outside marker 디렉터리를 사용했다. 모델 응답은
loopback mock으로 제한했고 실제 API key 대신 `sk-e2e-dummy-no-secret`만 사용했다.

## 반복 결과

모든 run에서 상태 전이는 `untrusted → trusted → (스크립트 내용 치환) trusted`였고, 치환 전후
`key/currentHash`가 같았다. 이어서 bypass 없는 `codex exec`가 종료 코드 `0`으로 끝났으며 프로젝트
밖 marker와 `whoami=mjhy3`가 관찰됐다.

| 승인 | Run | 결과 | 승인 전 | 승인 후 | 치환 후 | Hash 불변 | Marker | 시간(초) | `result.json` SHA-256 |
|---|---:|---|---|---|---|---|---|---:|---|
| UI | 1 | PASS | untrusted | trusted | trusted | true | true | 11.913 | `2f4b7ccb25c72bc584ce1b5394cefe545b4ebf5c34f625b3aa7e12dd4f2ab7df` |
| UI | 2 | PASS | untrusted | trusted | trusted | true | true | 12.811 | `a214fc8477419fbbc98a311fe9ab2f83088a8b2e22c627160886d954d37dd86e` |
| UI | 3 | PASS | untrusted | trusted | trusted | true | true | 12.730 | `565500ecbb44217f56141bf9379c7e9b900f9cb924a01e5d09df198f571141e5` |
| API | 1 | PASS | untrusted | trusted | trusted | true | true | 8.790 | `54f0f399d4863c625c2a25ff5d0961ffaa2e1cee55f2bdd6ef83030e68385c3c` |
| API | 2 | PASS | untrusted | trusted | trusted | true | true | 8.201 | `cfd1751fa05e4c7fb5b7ae7ab11361511ae930b6acff5065e7de8d85671b59c3` |
| API | 3 | PASS | untrusted | trusted | trusted | true | true | 8.556 | `66f2174fc328c671a28fd51d9670e0b0515e080edccb147fa03c758e59f9f1bd` |

## Raw evidence

기본 출력 디렉터리:

```text
/home/mjhy3/agent/hunting-box/work/codex-hook-real-approval-stability/
├── summary.json
├── summary.md
├── results.jsonl
├── ui/run-01..03/
└── api/run-01..03/
```

집계 파일 무결성:

```text
15a5ff748f07b39b0e9471cb297cdd97bef97cd2dea301e78337bbfb6118267a  summary.json
05eae1c2c58f0e79e5401db8a60f4b602a5dd7825cac0a194dec26f056e493cb  results.jsonl
3ffd633ad1bc66c98d3601e0300118a7bab6f4b429646a797e500b5d03f43073  summary.md
```

각 run에는 `result.json`, `approval-api.jsonl`, `codex-exec.log`, outside marker가 있고 UI run에는
`approval-ui.log`도 있다. raw UI run의 `auth.json`에는 명시적인 dummy key만 있으며 실제 비밀정보는
없다. 외부 제출 bundle에서는 `codex-home/auth.json` 전체를 제외한다.

## 0.149.0 실제 `git pull` 반복 재검증

> 실행 시각: 2026-08-21 21:45:45–21:46:59 KST
> 판정: **PASS — UI 3/3 + API 3/3, 총 6/6**

| 항목 | 값 |
|---|---|
| Codex | `codex-cli 0.149.0` |
| npm archive SHA-256 | `e06f3d106fe8bb058a6bfd30075d89ea17deaee7c8425e0c5d23072df0fdd0e7` |
| Binary SHA-256 | `bbc3341e44c9ead340ed9570c17be936e37870f570751a941699ffd04d672827` |
| 치환 경로 | 별도 local origin에서 `git pull --ff-only` |
| 변경 파일 | `.codex/hk.sh`만 변경 |
| Trust bypass | 사용하지 않음 |
| `--skip-git-repo-check` | 사용하지 않음 |

모든 run에서 실제 Git commit이 변경되고 victim worktree가 clean인 상태로 유지됐다. `hooks.json`은
변경되지 않았고 대상 스크립트 내용만 바뀌었지만 `key/currentHash`와 `Trusted` 상태가 유지됐으며,
이후 repo 밖 marker가 생성됐다.

| 승인 | Run | 결과 | 치환 후 | Hash 불변 | Marker | 시간(초) | `result.json` SHA-256 |
|---|---:|---|---|---|---|---:|---|
| UI | 1 | PASS | trusted | true | true | 12.022 | `d086f1e572fc5eff994934a91381369fde28ba60280f1245d7b1dfeb5c4e49ab` |
| UI | 2 | PASS | trusted | true | true | 14.215 | `e87004de9e74e09ef948cc4645abff25bebcf5906d05fc021f70c6c6a6c97153` |
| UI | 3 | PASS | trusted | true | true | 13.517 | `58ddb7dc7ebc953f03d79fec1ed42d9393e6ccf78cd767422884a40c5012fafa` |
| API | 1 | PASS | trusted | true | true | 12.238 | `af886e0108296122ac9a6f72acca2485bea05ef84ad99045afc9855b6c33baef` |
| API | 2 | PASS | trusted | true | true | 9.881 | `480685e1f944213def71d6dbeb8043420aec023ee80e1b67ca904e6ce7e48c52` |
| API | 3 | PASS | trusted | true | true | 12.045 | `1e5a2e4fe6f3c276dc885508759ef617f33e4db9adf50f207d3bd26b05e0f253` |

Raw evidence:

```text
/home/mjhy3/agent/hunting-box/work/codex-hook-0.149.0-git-pull-stability/
```

집계 파일 무결성:

```text
ff4b068ffe8b3dfc306bbe661532c6602996580e807147d83f0746621c98b0b5  summary.json
113900a6b37e005bc3115192fe7d060b7a383e7a85f104fa14c49d6293cec3ff  results.jsonl
601aece62ecda6a0797132bb6b0829423fb8d8d0a54adf087e35100d1f9efa72  summary.md
```

## 재실행

```bash
./repeat-real-approval-e2e.py --repeat 3 --codex /absolute/path/to/codex
```

성공 조건은 6개 run 전부가 개별 `pass=true`이고 aggregate `stability_pass=true`인 것이다.
