# Codex sed prefix-rule RCE

> 상태: `소스 확인` · `0.147.0 full impact` · `0.148.0 policy oracle 재확인` · `벤더 미확인 0-day 후보`
>
> 증거 표기: **[소스]** 구현에서 확인 · **[동적]** 로컬 실행 관찰 · **[추론]** 확인된 edge에서 도출 · **[미검증]** 별도 검증 필요
>
> callback payload를 제외한 비공개 제출용 초안. marker-only 재현을 권장한다.


## 핵심 요약

- Codex CLI `0.147.0`에서 고정 파일을 읽는 GNU `sed` 명령에 영구 승인된 argv prefix가 있으면, 같은 prefix 뒤에 기능을 확장하는 인자를 붙여도 새 사용자 승인 없이 `allow`로 판정되는 현상을 로컬에서 검증했다.
- GNU sed는 입력 파일 피연산자 뒤의 옵션도 계속 해석하며, 뒤에 추가한 `-e` 프로그램의 `e` 명령은 셸을 호출하므로 “고정 범위 읽기”가 “임의 호스트 명령 실행”으로 바뀐다.
- Codex의 prefix matcher는 후행 argv를 검사하지 않고, 일치한 allow rule은 실행 경로에서 `Unsandboxed`를 선택할 수 있어 정책 범위 불일치가 실제 샌드박스·승인 경계 우회로 이어진다.
- 정책 전용 PoC, 무해한 `/usr/bin/id` 실행, workspace 밖 marker 생성, 연구자 소유 호스트의 loopback callback까지 단계적으로 확인했으며 재사용 위험이 있는 callback payload는 이 노트에서 의도적으로 제외한다.
- OWASP Agentic Top 10의 지침에 따라 주 분류는 `ASI05 Unexpected Code Execution`, 보조 분류는 `ASI02 Tool Misuse & Exploitation`이며, 제안 심각도는 선행 영구 승인 조건을 반영한 High이다.

## 배경과 조사 범위

이 조사는 사용자가 직접 소유한 로컬 Linux 호스트와 일회성 파일만을 대상으로 수행했다. 관찰된 제품은 `codex-cli 0.147.0`, GNU sed `4.9`이며, 검토한 Codex 소스 revision은 `85fc4def358b7df21883e72ae8dda43a0f572f32`(2026-08-15)이다. 현재 세션의 권한 설정과 과거 검증 당시 설정은 달라질 수 있으므로, 아래 내용은 **당시 저장된 정책·출력과 소스 분석을 기준으로 한 검증 결과**다.

문제의 핵심은 prefix rule 자체가 존재한다는 사실이 아니다. Codex Rules 문서는 prefix matching이 후속 인자를 포함하는 재사용 승인임을 설명하고 제안된 prefix를 사용자가 주의 깊게 검토해야 한다고 안내한다. 취약한 불변식은 다음과 같다.

> 화면에 표시된 고정 읽기 작업을 영구 승인했을 때, 미래의 후행 argv만으로 그 작업이 샌드박스 밖 임의 코드 실행으로 변해서는 안 된다.

[Codex Rules 공식 문서](https://learn.chatgpt.com/docs/agent-configuration/rules)

## 전체 공격 체인

```text
고정 sed 읽기 명령에 영구 승인
        ↓
Codex가 완전한 argv가 아닌 argv prefix를 allow rule로 저장
        ↓
동일 prefix 뒤에 GNU sed의 기능 확장 인자 추가
        ↓
execpolicy가 후행 argv를 무시하고 기존 rule로 allow 판정
        ↓
GNU sed가 입력 파일 뒤의 옵션과 추가 프로그램을 해석
        ↓
추가 sed 프로그램의 e 명령이 /bin/sh 호출
        ↓
prefix-rule 기반 escalation이 Unsandboxed 실행 선택
        ↓
새 승인 없이 Codex 프로세스 사용자 권한으로 호스트 명령 실행
```

### 1. 선행 조건: 읽기처럼 보이는 명령의 영구 승인

검증 세션에서 다음과 같은 고정 읽기 명령이 사용자 승인 대상으로 제시됐다.

```text
sed -n 1,260p /tmp/codex-sed-poc-input.txt
```

관찰된 승인 범위는 다음 argv prefix와 동등하다.

```text
["sed", "-n", "1,260p", "/tmp/codex-sed-poc-input.txt"]
```

공격에는 이와 같은 **선행 영구 승인 1회**가 필요하다. 모든 sed 실행이 기본적으로 샌드박스를 탈출한다는 주장은 아니다. 다만 모델이 저장소 문서, 도구 출력, 프롬프트 인젝션 등 신뢰할 수 없는 입력의 영향을 받은 뒤에도 이 prefix를 재사용할 수 있다는 점이 중요하다.

### 2. GNU sed의 후행 옵션 해석

GNU sed `4.9`에서 위 입력 파일 피연산자 뒤에 `--version`을 붙였을 때 파일명으로 처리하지 않고 버전을 출력했다. 이는 GNU sed가 해당 위치에서도 옵션 parsing을 계속한다는 직접 관찰이다. 공식 매뉴얼도 여러 `-e SCRIPT`를 sed 프로그램에 추가할 수 있음을 설명한다. 또한 GNU 확장 `e` 명령은 입력된 명령을 셸로 실행하고, `--sandbox`는 `e/r/w`를 거부한다. [GNU sed 명령행 옵션](https://www.gnu.org/software/sed/manual/html_node/Command_002dLine-Options.html), [GNU sed 명령 목록](https://www.gnu.org/software/sed/manual/html_node/sed-commands-list.html)

따라서 승인된 prefix 뒤에 아래처럼 무해한 추가 프로그램을 **리터럴 argv**로 붙일 수 있다.

```text
-e '1e /usr/bin/id'
```

이 단계에는 바깥 셸의 `$(...)`, redirection, `;` 같은 구문이 필요하지 않다. 그러므로 복잡한 `bash -lc` 문자열을 보수적으로 검사하는 경로는 이 체인을 차단하지 못한다.

### 3. Codex execpolicy가 suffix를 승인 범위에 포함

소스에서 확인한 데이터 흐름은 다음과 같다.

| 위치 | 확인 내용 | 보안상 의미 |
|---|---|---|
| [`execpolicy/src/rule.rs:40`](https://github.com/openai/codex/blob/85fc4def358b7df21883e72ae8dda43a0f572f32/codex-rs/execpolicy/src/rule.rs#L40) | `PrefixPattern::matches_prefix`는 명령 길이가 pattern 이상인지 확인한 뒤 prefix slice만 비교한다. | pattern 뒤 argv는 match의 부정 조건이 아니다. |
| [`core/src/exec_policy.rs:936`](https://github.com/openai/codex/blob/85fc4def358b7df21883e72ae8dda43a0f572f32/codex-rs/core/src/exec_policy.rs#L936) | 제안된 amendment가 현재 parsed command들을 승인하는지 검사한다. | 미래 suffix가 실행 파일의 capability를 확장하는지는 평가하지 않는다. |
| [`unix_escalation.rs:620`](https://github.com/openai/codex/blob/85fc4def358b7df21883e72ae8dda43a0f572f32/codex-rs/core/src/tools/runtimes/shell/unix_escalation.rs#L620) | prefix rule이 내린 결정은 가능한 경우 `EscalationExecution::Unsandboxed`로 이어진다. | 잘못 넓은 allow가 단순 UI 문제가 아니라 샌드박스 밖 실행이 된다. |
| [`shell_spec.rs:327`](https://github.com/openai/codex/blob/85fc4def358b7df21883e72ae8dda43a0f572f32/codex-rs/core/src/tools/handlers/shell_spec.rs#L327) | 모델-facing schema가 `prefix_rule`을 재사용 승인 prefix로 설명한다. | 모델과 사용자는 완전 명령 승인과 재사용 scope를 구분해야 한다. |

### 4. 정책 전용 PoC

다음 검사는 sed나 `/usr/bin/id`를 실행하지 않고 execpolicy의 결정만 확인한다.

```text
codex execpolicy check --pretty \
  --rules poc/policy.rules \
  -- sed -n 1,260p /tmp/codex-sed-poc-input.txt \
  -e '1e /usr/bin/id'
```

`codex-cli 0.147.0`에서 확인된 결과는 다음과 같다. `matchedPrefix`는 고정 파일에서 끝나지만, 후행 `-e`가 있는 전체 명령의 최종 결정도 `allow`다.

```json
{
  "matchedRules": [
    {
      "prefixRuleMatch": {
        "matchedPrefix": [
          "sed",
          "-n",
          "1,260p",
          "/tmp/codex-sed-poc-input.txt"
        ],
        "decision": "allow",
        "justification": "Harmless policy-matcher reproduction for a fixed sed read"
      }
    }
  ],
  "decision": "allow"
}
```

대조군으로 다른 입력 경로를 사용하면 rule이 일치하지 않았다. 즉 임의 명령이 전부 allow되는 문제가 아니라, **승인된 prefix 뒤 suffix가 의미를 바꾸는 문제**다.

### 5. 실행 영향의 단계별 검증

검증은 위험도를 단계적으로 높이며 연구자 소유 환경 안에서만 수행했다.

1. `/usr/bin/id`를 이용해 추가 sed 프로그램이 하위 명령을 실행함을 확인했다.
2. workspace 밖의 일회성 marker 파일을 생성해 실행이 workspace-write 경계를 넘어감을 확인했다.
3. 최종적으로 `127.0.0.1:4444`만 수신하는 연구자 로컬 listener에서 다음 callback을 확인했다.

```text
Listening on localhost 4444
Connection received on localhost 39078
bash: cannot set terminal process group (...): Inappropriate ioctl for device
bash: no job control in this shell
```

위 출력은 비대화형 셸이 loopback listener에 연결됐다는 증거다. 실제 callback payload는 안전을 위해 기록하지 않는다. 정책 전용 PoC와 marker-file 재현만으로도 동일한 승인·샌드박스 불변식 위반을 검증할 수 있다.

## 근본 원인

세 구성요소의 각 동작은 개별적으로 설명 가능하지만, 조합 시 승인 의미가 붕괴한다.

1. **Codex 정책 의미:** 사용자 승인은 완전한 표시 명령이 아니라 재사용 가능한 token prefix로 저장될 수 있다.
2. **프로그램 의미:** GNU sed는 기존 파일 피연산자 뒤의 argv로 새 프로그램과 셸 실행 capability를 추가할 수 있다.
3. **실행 의미:** 해당 prefix allow는 sandbox 내부 편의 허용에 머물지 않고 unsandboxed escalation을 선택할 수 있다.

즉, matcher는 문법적으로 같은 prefix인지 판별하지만 사용자가 승인한 **행위의 capability**가 유지되는지는 검증하지 않는다. 이것이 argument injection에서 host-side code execution까지 이어지는 semantic scope mismatch다.

## 분류

### OWASP Agentic Top 10

- **주 분류 — ASI05 Unexpected Code Execution:** 도구 인자를 통해 예상하지 못한 호스트 코드 실행과 sandbox escape가 발생한다.
- **보조 분류 — ASI02 Tool Misuse & Exploitation:** 합법적인 sed와 영구 승인 기능이 잘못된 인자 범위로 오용된다.

OWASP 공식 문서는 ASI02를 합법적 도구의 잘못된 target·parameter·sequence 사용으로 설명하면서도, 그 오용이 임의 또는 주입된 코드 실행을 낳으면 ASI05로 분류한다고 명시한다. 따라서 폴더와 주 분류는 ASI05가 맞고 ASI02는 원인 성격을 나타내는 보조 분류다. [OWASP Top 10 for Agentic Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/)

### CWE

- **Primary: CWE-88 — Argument Delimiter Injection or Modification:** 승인된 argv 뒤의 공격자 영향 suffix가 기존 정책 scope 안으로 흡수된다.
- **Impact: CWE-78 — Improper Neutralization of Special Elements used in an OS Command:** sed의 `e` capability를 거쳐 셸 명령 실행으로 이어진다.
- 승인 scope 설계 관점에서는 CWE-284 계열도 참고할 수 있으나, 제출 시에는 재현 메커니즘을 가장 직접적으로 설명하는 CWE-88을 우선한다.

## 영향과 한계

### 확인된 영향

- 새 사용자 결정 없이 workspace 밖 파일 쓰기·변조
- 더 엄격한 managed profile이 막으려던 파일 읽기 가능성
- sandbox가 제한했을 네트워크 접근 가능성
- Codex 프로세스와 같은 OS 사용자 권한의 임의 코드 실행

이는 **Codex의 명령 승인·sandbox 경계 탈출**이다. 커널 권한 상승, 다른 OS 사용자 획득, VM 또는 물리 호스트 격리를 넘는 탈출을 의미하지 않는다.

### 필요한 조건과 불확실성

- 사용자가 앞서 suffix를 허용하는 sed prefix를 영구 승인해야 한다.
- 실제 피해에는 모델이 악성 저장소 지시나 다른 비신뢰 입력의 영향을 받아 suffix를 구성하는 경로가 필요하다.
- `Unsandboxed` 선택 가능 여부와 접근 가능한 데이터·네트워크는 실행 프로필에 따라 달라진다.
- 제안 심각도는 **High**지만, 선행 사용자 승인과 배포별 sandbox 구성 때문에 vendor의 최종 triage는 달라질 수 있다.

## 완화 권고

1. 완전한 표시 명령을 영구 승인할 때 기본적으로 **exact argv / end-of-command** rule을 저장한다.
2. interpreter-like 또는 suffix로 capability가 확장되는 프로그램에는 명시적 opt-in 없이 재사용 가능한 unsandboxed prefix를 제안하지 않는다.
3. 최소한 sed를 suffix-sensitive 프로그램으로 분류하고 `-e`, `--expression`, `-f`, `--file`, `-i`, `--in-place`, `--follow-symlinks`, 추가 입력 파일이 나타나면 새 승인을 요구한다.
4. 편의 목적의 prefix allow는 기본적으로 sandbox 내부에 유지하고, unsandboxed 재사용 scope는 별도 경고와 명시적 승인을 받는다.
5. regression test에서 고정 `sed -n 1,260p FILE`은 allow하되, 같은 prefix 뒤 `-e '1e /usr/bin/id'`를 붙인 명령은 기존 승인으로 allow되지 않도록 검증한다.
6. sed 전용 wrapper를 쓴다면 `--sandbox`, `--`, exact path·argc 검증, 추가 argv 거부를 함께 적용한다.

`--posix`만으로는 POSIX sed의 파일 읽기·쓰기 기능이 남으므로 보안 경계가 아니다. `--sandbox`와 `--`도 exact end constraint 없이 추가 입력 파일을 허용하면 읽기 범위가 넓어질 수 있어 defense in depth로만 봐야 한다. [GNU sed sandbox 옵션](https://www.gnu.org/software/sed/manual/html_node/Command_002dLine-Options.html)

## 공개 현황과 제출 상태

2026-08-19 기준 공개 검색에서 이 **sed suffix → prefix allow → unsandboxed shell execution** 전체 체인과 일치하는 issue, PR, Codex 보안 권고는 찾지 못했다. 다만 비공개 Bugcrowd 선행 제출의 존재는 확인할 수 없으므로 0-day 또는 독점성을 확정할 수 없다.

- [GitHub issue #21018](https://github.com/openai/codex/issues/21018)은 exact invocation과 reusable prefix 등 사용자 선택형 승인 scope를 요청하지만, sed suffix에서 unsandboxed shell execution까지 입증하지 않는다.
- [GitHub issue #28732](https://github.com/openai/codex/issues/28732)은 `./sed`처럼 safe basename을 공유하는 path-qualified binary 자동 승인을 다루며, 보고된 실행은 sandbox 안에 머문다.
- [GitHub issue #11583](https://github.com/openai/codex/issues/11583)은 `sed -i`를 이용한 workspace restriction 우회를 다루는 별도 문제다.

Codex 저장소의 보안 정책은 취약점 제보를 OpenAI Bugcrowd로 안내한다. 현재 로컬에는 제출용 초안과 안전한 policy-only PoC가 준비돼 있으나, 이 노트 작성 시점에는 vendor 확인 또는 접수 번호가 없다. [OpenAI Bugcrowd](https://bugcrowd.com/engagements/openai), [Codex Security Policy](https://github.com/openai/codex/security/policy), [OpenAI 취약점 보고 지침](https://learn.chatgpt.com/docs/security/plugin/vulnerability-reports)

## 로컬 증거 위치

- 전체 제출 초안: [`DISCLOSURE.md`](DISCLOSURE.md)
- 안전한 PoC: [`poc/`](poc/)
- 최신 policy oracle: [`evidence/policy-0.148.0.json`](evidence/policy-0.148.0.json)

## 출처

- [OWASP Top 10 for Agentic Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/)
- [OpenAI Codex Rules](https://learn.chatgpt.com/docs/agent-configuration/rules)
- [GNU sed command-line options](https://www.gnu.org/software/sed/manual/html_node/Command_002dLine-Options.html)
- [GNU sed commands list](https://www.gnu.org/software/sed/manual/html_node/sed-commands-list.html)
- [OpenAI Codex source revision `85fc4def`](https://github.com/openai/codex/tree/85fc4def358b7df21883e72ae8dda43a0f572f32)
- [OpenAI Codex Security Policy](https://github.com/openai/codex/security/policy)
- [OpenAI Vulnerability Reports](https://learn.chatgpt.com/docs/security/plugin/vulnerability-reports)
- [OpenAI Bugcrowd program](https://bugcrowd.com/engagements/openai)
- [Related issue #21018](https://github.com/openai/codex/issues/21018)
- [Related issue #28732](https://github.com/openai/codex/issues/28732)
- [Related issue #11583](https://github.com/openai/codex/issues/11583)
