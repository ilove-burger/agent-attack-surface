# Internal approval-cache test and reachability correction

## What the Rust test proves

`repro-test.patch` adds an integration test to the `codex-core` approvals suite. It sends the internal `ReviewDecision::ApprovedForSession`, changes a referenced script's content, and verifies that the same shell approval cache key is reused while the changed bytes execute.

```text
test suite::approvals::approving_shell_command_for_session_reuses_approval_despite_script_content_change ... ok
test result: ok. 1 passed; 0 failed
```

The complete approvals suite also passed with the added test.

```text
test result: ok. 21 passed; 0 failed
```

This remains useful defense-in-depth evidence: the internal session cache key does not bind referenced file content.

## What the Rust test does not prove

It does not prove that an ordinary user can select `ApprovedForSession` for a normal shell command in the official TUI.

Actual 0.149.1 TUI observation:

```text
1. Yes, proceed (y)
2. Yes, and don't ask again for commands that start with ... (p)
3. No ... (esc)
```

Source `protocol/src/approvals.rs::default_available_decisions()` agrees:

- network approval: `Approved`, `ApprovedForSession`, optional network amendment, `Abort`
- ordinary command: `Approved`, optional `ApprovedExecpolicyAmendment`, `Abort`

Therefore the old claim that the TUI's `a` key makes the internal session-cache test directly exploitable for ordinary commands is withdrawn.

## Reachable replacement finding

The real TUI `p` decision persists a content-blind execpolicy prefix rule. Actual Linux and Windows E2E tests proved the same substitution primitive through this reachable path. Those results supersede the internal-only test for exploitability and are recorded in [`TUI_E2E_0.149.1.md`](TUI_E2E_0.149.1.md).

## Source versions

| Tag | Commit | Observation |
|---|---|---|
| `rust-v0.149.1` | `ff29a44391deccde0aba0f8390337d7f3c319ea4` | ordinary command decision set and prefix amendment behavior confirmed |
| `rust-v0.150.0-alpha.9` | `a1a7e0b1d11436a3c33d14b2f019004bdf453777` | reviewed diff contains no target-content binding fix |

The alpha statement is source-only; no alpha binary runtime result is claimed.
