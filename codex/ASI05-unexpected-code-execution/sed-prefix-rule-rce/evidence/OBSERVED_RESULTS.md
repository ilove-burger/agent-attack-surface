# Sanitized observed results

> policy-only 최신 재확인: 2026-08-21
> Codex: `codex-cli 0.148.0`
> Binary SHA-256: `ac2cfed85fb647d61e0150b8548102b330e4799d9d81ad5d354de701edf6b074`
> GNU sed: `4.9`
> full marker E2E: `codex-cli 0.147.0`

## 0.148.0 policy oracle

`policy-0.148.0.json`은 실제 binary의 `execpolicy check` 출력이다. 고정 file operand에서
`matchedPrefix`가 끝나지만 뒤에 `-e '1e /usr/bin/id'`가 붙은 전체 argv의 decision이 `allow`다.

다른 input path를 사용한 negative control은 다음과 같았다.

```json
{
  "matchedRules": []
}
```

## 0.147.0 impact oracle

- literal `-e '1e /usr/bin/id'`가 child command를 실행했다.
- disposable outside marker가 새 승인 없이 생성됐다.
- 연구자 소유 `127.0.0.1` listener에서 비대화형 callback을 관찰했다.
- 재사용 위험이 있는 callback payload는 보존하거나 첨부하지 않았다.

## 판정 경계

0.148.0에서 재확인한 것은 policy scope bypass다. 0.148.0에서 실제 UI 승인과 unsandboxed marker를
다시 수행했다고 주장하지 않는다. full impact E2E 증거는 0.147.0 기준이다.

