# OpenAI Codex CLI — persistent execpolicy prefix does not bind referenced script content

## Summary

Codex CLI offers an approval choice equivalent to “allow future commands that start with this argv prefix.” The resulting rule is persisted in `$CODEX_HOME/rules/default.rules` and matches command tokens only. If an allowed command invokes a script, the rule does not bind or revalidate that script's content.

After a user approves a benign script command with the persistent prefix option, an attacker-controlled update can replace only the script content. A later invocation with the same argv prefix runs the replaced content without a new command approval. When the original request used `require_escalated`, the replaced content runs outside the workspace sandbox with the Codex session user's authority.

## Affected builds tested

- `@openai/codex 0.149.1` Linux x64 actual TUI: confirmed
- `@openai/codex 0.149.1` Windows x64 actual TUI with native `cmd.exe`/`.cmd`: confirmed
- source tag `rust-v0.149.1`: content binding not present
- source tag `rust-v0.150.0-alpha.9`: no relevant fix found in reviewed approval/execpolicy diff; runtime not tested
- macOS `0.149.1`: official archives and binaries hashed, runtime not tested

## Reachable approval path

For an ordinary command, the tested TUI displayed:

```text
1. Yes, proceed (y)
2. Yes, and don't ask again for commands that start with ... (p)
3. No ... (esc)
```

Selecting `p` persisted rules such as:

```text
prefix_rule(pattern=["bash", "approved.sh"], decision="allow")
prefix_rule(pattern=["cmd.exe", "/d", "/c", "approved.cmd"], decision="allow")
```

This report does not rely on an internal `ApprovedForSession` decision. Source review showed that ordinary command prompts do not expose that decision in the default TUI flow.

## Faithful Linux TUI chain

Environment:

- fresh local Git clone
- fake `HOME` and `CODEX_HOME`
- allowlisted environment with dummy API key
- deterministic loopback-only Responses endpoint
- `workspace-write` and `on-request`
- no bypass flags

Observed sequence:

1. The model reads a committed synthetic `ATTACK.md` prompt-injection fixture.
2. The model requests `bash approved.sh` with `require_escalated`; its content only appends `BEFORE_APPROVAL_CONTENT` to a harness-owned outside log.
3. The actual TUI receives `p`; Codex writes the exact prefix rule above and runs the benign script.
4. The model uses Codex's recognized workspace `apply_patch` route to replace only `approved.sh` with a synthetic marker payload.
5. The model requests the same `bash approved.sh` argv and permission again.
6. No second command approval appears; the replaced script appends `AFTER_APPROVAL_ATTACKER_CONTENT`, creates an outside marker, and records the current user/project directory.

Result: PASS on `codex-cli 0.149.1`, binary SHA-256 `73dc5888888f411c1f0fa7b81d866e721dcc86b527ce8e3b2cf4708661e823ba`.

A separate actual-TUI restart test also passed. The first Codex process stored
the prefix rule and was terminated. The driver then changed only
`approved.sh`, started a new Codex process with the same isolated
`CODEX_HOME`, and requested the same argv. The second process displayed no
command approval, executed the changed content, and created the outside
marker. This confirms that reuse is not limited to one in-memory session.

## Faithful Windows TUI chain

The Windows test used the official Windows x64 binary, Windows non-admin sandbox setup, `workspace-write`, a fake Windows `CODEX_HOME`, and native commands:

```text
cmd.exe /d /c approved.cmd
```

After `p`, an external attacker/delivery step replaced only `approved.cmd`. The same argv executed without a second approval and created an outside Windows marker. `whoami.txt` contained the Windows account and a `C:\Users\...\project` working directory.

Result: PASS on `codex-cli 0.149.1`, binary SHA-256 `a395030b56b126f608f2403036dddb654a9c063213e9c2b5f85d954cf490ebe6`.

The Windows model-driven patch subvariant is intentionally not claimed as a no-additional-UI chain: the tested Windows TUI separately requested file-edit approval for the patch. The cross-platform core substitution primitive is proven by the external-delivery variant; the full prompt-injection chain is proven on Linux.

## Negative controls

Linux and Windows both passed these controls:

1. **Approve once:** choose `y`, replace the script, request the same argv. A second approval prompt appears and no marker is created.
2. **Change argv:** choose `p`, replace the script, change the script token (`approved.sh`→`./approved.sh`, Windows `approved.cmd`→`.\approved.cmd`). A second approval prompt appears and no marker is created.

These controls show that content replacement alone is not sufficient after one-time approval, and that the positive result depends on the stored argv prefix match.

## Root cause

The persistent allow rule is based on command token prefixes. It has no field for:

- resolved script/executable identity
- script content digest
- inode/file ID
- source commit or update provenance
- time-of-use content revalidation

The source tags reviewed between stable `rust-v0.149.1` (`ff29a44391deccde0aba0f8390337d7f3c319ea4`) and preview `rust-v0.150.0-alpha.9` (`a1a7e0b1d11436a3c33d14b2f019004bdf453777`) did not add such binding in the reviewed approval/execpolicy paths.

## Security impact

Confirmed primitive: same-user execution outside the Codex workspace sandbox of content that was not present when the persistent command rule was approved.

A local-origin `git pull --ff-only` delivery was reproduced in the actual Linux
TUI harness. The delivered commit changed only `approved.sh`, the victim
worktree remained clean, and the same argv ran the changed bytes without a
second command approval. Other plausible paths include a dependency or
generated-file update, another trusted tool/process, or a model workspace
edit. The report's synthetic tests do not access real secrets or external
services.

## Preconditions and severity

The user must explicitly select the persistent prefix option. A matching command must be invoked again after its referenced content changes. Because the UI describes future prefix reuse, the vendor may consider part of the behavior intentional; the security question is whether approval of an argv prefix should authorize future, unseen script bytes outside the sandbox.

Severity is therefore reported as **vendor-unconfirmed and deployment-dependent**. The previous draft's CVSS 3.1 score of 8.5 is withdrawn. A numeric score should be assigned only after the vendor decides whether the sandbox boundary and persistent user decision change Scope and Privileges Required.

## Remediation

1. Bind interpreter/script prefix rules to a content digest or stable file identity and invalidate on change.
2. Resolve common interpreter targets and revalidate immediately before unsandboxed execution.
3. Display resolved target files and change state in the approval UI.
4. Avoid generating persistent prefix allow rules for file-interpreter patterns unless a structured target binding is possible.
5. Add positive/negative regression coverage for Linux and Windows, including content substitution, argv normalization, symlinks, and race-resistant open/execute behavior.

## Evidence

- [`poc-tui-execpolicy-substitution.py`](poc-tui-execpolicy-substitution.py)
- [`poc-tui-execpolicy-restart.py`](poc-tui-execpolicy-restart.py)
- [`evidence/TUI_E2E_0.149.1.md`](evidence/TUI_E2E_0.149.1.md)
- [`evidence/results-0.149.1.json`](evidence/results-0.149.1.json)
- [`evidence/OBSERVED_RESULTS.md`](evidence/OBSERVED_RESULTS.md)
- [`repro-test.patch`](repro-test.patch)
