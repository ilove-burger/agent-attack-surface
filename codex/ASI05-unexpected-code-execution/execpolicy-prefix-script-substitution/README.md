# 저장된 execpolicy argv prefix가 대상 스크립트 변경을 반영하지 않아 교체된 코드를 재승인 없이 실행

> **상태:** 🔴 LIVE 후보 — Codex CLI `0.149.1` 실제 TUI에서 Linux와 Windows native 명령으로 재현
>
> **중요한 교정:** 일반 shell 명령의 공식 TUI에는 내부 `ApprovedForSession` 선택지가 없다. 실제 도달 가능한 경로는 사용자가 `p`로 선택하는 **“이 prefix로 시작하는 명령은 다시 묻지 않기”**이며, `$CODEX_HOME/rules/default.rules`에 영속되는 execpolicy 규칙이다.
>
> **CWE(잠정):** CWE-345 · 관련 CWE-829
>
> **OWASP Agentic:** Primary ASI05 · Secondary ASI02
> **최종 확인:** 2026-08-26

## 결론

Codex TUI가 제안하는 execpolicy amendment는 명령의 argv prefix만 저장한다.

```text
prefix_rule(pattern=["bash", "approved.sh"], decision="allow")
prefix_rule(pattern=["cmd.exe", "/d", "/c", "approved.cmd"], decision="allow")
```

규칙은 `approved.sh`/`approved.cmd`의 내용, digest, inode, 실제 해석 결과를 묶지 않는다. 따라서 사용자가 무해한 스크립트 실행을 한 번 승인하고 `p`를 선택한 뒤 대상 파일 내용만 바뀌면, 동일 argv의 두 번째 호출은 재승인 없이 교체된 내용을 sandbox 밖에서 실행한다.

```text
무해한 script + require_escalated 명령
  → 실제 TUI에서 p 선택
    → argv prefix allow 규칙 저장
      → script content만 교체
        → 동일 argv 재호출
          → 승인 프롬프트 없음 + 교체된 content 실행
```

## 실제 TUI 결과

대상은 2026-08-26 npm stable 최신인 `@openai/codex 0.149.1`이다. dummy API key, loopback model endpoint, fake `HOME`/`CODEX_HOME`, synthetic marker만 사용했다. bypass 플래그는 사용하지 않았다.

| 플랫폼/체인 | 결과 | 핵심 관찰 |
|---|---:|---|
| Linux full prompt-injection chain | PASS | `ATTACK.md` 읽기 → 무해 명령 `p` 승인 → workspace `apply_patch` 교체 → 동일 argv 재호출, marker 생성 |
| Linux cross-process restart | PASS | 첫 TUI 종료 후 같은 `CODEX_HOME`으로 새 TUI 실행; 저장된 규칙이 유지되어 변경된 script를 재승인 없이 실행 |
| Linux `git pull` delivery | PASS | fast-forward 커밋이 `approved.sh` 하나만 변경; clean worktree에서 동일 argv가 재승인 없이 실행 |
| Linux execpolicy positive 반복 | 3/3 PASS | 승인 프롬프트 1회, 두 번째 실행은 `AFTER_APPROVAL_ATTACKER_CONTENT` |
| Linux approve-once control | PASS | 두 번째 호출에서 승인 프롬프트 재발생, marker 없음 |
| Linux argv-change control | PASS | `bash approved.sh`→`bash ./approved.sh` 변경 시 프롬프트 재발생, marker 없음 |
| Windows native positive | PASS | 실제 Windows Codex TUI + `cmd.exe /d /c approved.cmd`; content 교체 뒤 동일 argv가 재승인 없이 실행 |
| Windows approve-once control | PASS | 규칙이 저장되지 않고 두 번째 호출에서 재승인 요구, marker 없음 |
| Windows argv-change control | PASS | `approved.cmd`→`.\approved.cmd` 변경 시 재승인 요구, marker 없음 |

Windows positive에서 생성된 `whoami.txt`는 Windows 사용자와 `C:\Users\...\project` 작업 디렉터리를 기록했다. WSL `bash.exe`가 아닌 native `cmd.exe`/`.cmd` 체인이다.

상세 결과는 [`evidence/TUI_E2E_0.149.1.md`](evidence/TUI_E2E_0.149.1.md)에서 확인할 수 있다.

재현 driver는 [`poc-tui-execpolicy-substitution.py`](poc-tui-execpolicy-substitution.py)다. 기존 결과 디렉터리를 덮어쓰지 않으므로 매 실행마다 새 `--run-dir`을 지정한다.

```bash
python3 ./poc-tui-execpolicy-substitution.py \
  --codex /path/to/codex \
  --scenario execpolicy-prefix-model-chain \
  --mutation-transport model-apply-patch \
  --run-dir /tmp/codex-execpolicy-positive-v1
```

`git pull` 전달 변형은 `--mutation-transport git-pull`로 실행한다. 드라이버가 harness-owned local bare origin에 script-only 커밋을 만들고 victim clone에서 fast-forward한 뒤, before/delivered/after commit과 changed-files를 `result.json`에 기록한다.

Windows binary를 WSL에서 검증할 때는 Windows 사용자가 쓸 수 있는 NTFS 경로를 `--run-dir`로 지정하고 `--mutation-transport external-swap`을 사용한다. driver가 native `cmd.exe` fixture, fake Windows `CODEX_HOME`, terminal cursor query, sandbox setup 화면을 자동 처리한다.

프로세스 재시작 지속성은 별도 [`poc-tui-execpolicy-restart.py`](poc-tui-execpolicy-restart.py)로 검증한다. 첫 TUI에서 `p`를 선택한 뒤 프로세스를 종료하고, script content를 교체한 다음 동일한 격리 `CODEX_HOME`으로 두 번째 TUI를 실행한다.

## UI 도달성 교정

0.149.1 일반 명령 승인 화면은 다음 세 선택지만 제공했다.

```text
1. Yes, proceed (y)
2. Yes, and don't ask again for commands that start with ... (p)
3. No ... (esc)
```

소스 `protocol/src/approvals.rs::default_available_decisions()`도 일반 명령에 `Approved`, 선택적 `ApprovedExecpolicyAmendment`, `Abort`만 넣는다. `ApprovedForSession`은 network approval 같은 다른 문맥에서만 기본 선택지에 포함된다.

따라서 `repro-test.patch`가 증명하는 내부 session cache의 content-blind 동작은 방어 심층화 자료이지만, 일반 명령의 공식 TUI exploitability 증거로 사용하면 안 된다. 실제 finding은 위 execpolicy prefix 경로다.

## 최신 배포본 고정

| 항목 | SHA-256 |
|---|---|
| npm meta archive `0.149.1` | `1616304fd7883b46d8887cf336496e2ae0cdf9a637b7bdf8824baa98c22c5b7b` |
| Linux x64 archive | `734f865ed62d8be68796e7913651bbc69ad7c63a8c01ee28524ad69b4c9ab401` |
| Linux x64 binary | `73dc5888888f411c1f0fa7b81d866e721dcc86b527ce8e3b2cf4708661e823ba` |
| Windows x64 archive | `513bde2e7a1fe31e9b7ab2c9ec1dc87e54eb93d3adc5ae579452a7f0c09e9ed2` |
| Windows x64 binary | `a395030b56b126f608f2403036dddb654a9c063213e9c2b5f85d954cf490ebe6` |
| macOS x64 archive | `e53ee6a57a81998a2661a8159fb0ea478491f28f517d992a6f75fadcb38a9eca` |
| macOS x64 binary | `19ad079130409e2d32cbb4b02b3d622ab44e7de93a2898ce58908a0f2f5d7a06` |
| macOS arm64 archive | `151f8b96af0529c1267e7438d2cbc6d26213922fa017b96540abaf5f07d792d2` |
| macOS arm64 binary | `f0d8762236594359b60cfbe17f4c7e945a3ce8d1c91e74778838c968d250fb6c` |

Linux와 Windows binary는 직접 실행해 `codex-cli 0.149.1`을 확인했다. macOS는 공식 archive와 Mach-O binary hash만 고정했으며, 이 Linux/Windows 호스트에서는 실행하지 못했다.

## 최신 소스 확인

- stable `rust-v0.149.1`: `ff29a44391deccde0aba0f8390337d7f3c319ea4`
- preview `rust-v0.150.0-alpha.9`: `a1a7e0b1d11436a3c33d14b2f019004bdf453777`
- 두 태그의 approval decision/execpolicy 관련 diff에서 script content binding이나 동일 prefix 재검증 수정은 확인되지 않았다.

이 항목은 소스상 미수정 정황이다. alpha binary runtime E2E까지 수행했다는 뜻은 아니다.

## 영향과 전제조건

확인한 impact는 Codex가 이미 승인된 command prefix를 sandbox 밖에서 실행할 때 발생하는 same-user 코드 실행이다. Linux와 Windows 모두 repo 밖 marker 쓰기를 관찰했다.

필수 조건은 다음과 같다.

1. 사용자가 최초 승인 화면에서 명시적으로 `p`를 선택한다.
2. 공격자, 공급망 업데이트, `git pull`, 모델의 workspace 편집 등으로 대상 스크립트 내용이 바뀐다.
3. 저장된 prefix와 일치하는 argv가 다시 호출된다.

사용자는 “이 prefix로 시작하는 명령을 다시 묻지 않기”를 명시적으로 선택한다. 이 문구 때문에 벤더가 intended behavior로 판단할 가능성이 있으며, 심각도는 배포/위협 모델에 따라 달라진다. 이전 초안의 CVSS 8.5는 철회한다. 현재는 **조건부 Medium~High 후보, 숫자 미확정**으로 두는 편이 정확하다.

## 권고

1. 인터프리터/스크립트 실행 prefix amendment를 저장할 때 대상 파일 digest를 규칙에 묶는다.
2. 실행 직전에 대상 파일의 identity/content를 재검증하고 불일치하면 재승인을 요구한다.
3. UI에 현재 argv뿐 아니라 해석된 executable/script 경로와 content 변경 여부를 표시한다.
4. 단순 prefix 규칙으로 script interpreter 호출을 영속 허용하지 않거나, 더 좁은 구조화 규칙을 생성한다.
5. `ApprovedForSession` 내부 cache와 execpolicy rule 모두 같은 content-substitution regression test를 둔다.

## 파일

- [`DISCLOSURE.md`](DISCLOSURE.md) — 제보서 초안과 한계
- [`poc-tui-execpolicy-substitution.py`](poc-tui-execpolicy-substitution.py) — Linux/Windows/macOS actual TUI driver
- [`poc-tui-execpolicy-restart.py`](poc-tui-execpolicy-restart.py) — 프로세스 재시작 후 영속 규칙 재사용 E2E
- [`run-macos-matrix.sh`](run-macos-matrix.sh) — macOS actual-TUI positive/control 일괄 실행기
- [`evidence/TUI_E2E_0.149.1.md`](evidence/TUI_E2E_0.149.1.md) — Linux/Windows actual TUI 증거
- [`evidence/results-0.149.1.json`](evidence/results-0.149.1.json) — 공개 가능한 structured result 요약
- [`evidence/MACOS_RUNBOOK.md`](evidence/MACOS_RUNBOOK.md) — macOS 실기 검증 절차와 고정 해시
- [`evidence/OBSERVED_RESULTS.md`](evidence/OBSERVED_RESULTS.md) — 내부 session-cache 테스트와 도달성 교정
- [`repro-test.patch`](repro-test.patch) — 내부 `ApprovedForSession` 방어 심층화 테스트
- [`evidence/SHA256SUMS`](evidence/SHA256SUMS) — finding 파일 무결성
