# Codex 0.149.1 actual TUI evidence

## Release identity

Registry lookup date: 2026-08-26. Stable `@openai/codex` dist-tag: `0.149.1`.

| Artifact | SHA-256 | Runtime |
|---|---|---|
| npm meta archive | `1616304fd7883b46d8887cf336496e2ae0cdf9a637b7bdf8824baa98c22c5b7b` | n/a |
| Linux x64 archive | `734f865ed62d8be68796e7913651bbc69ad7c63a8c01ee28524ad69b4c9ab401` | extracted |
| Linux x64 binary | `73dc5888888f411c1f0fa7b81d866e721dcc86b527ce8e3b2cf4708661e823ba` | `codex-cli 0.149.1` |
| Windows x64 archive | `513bde2e7a1fe31e9b7ab2c9ec1dc87e54eb93d3adc5ae579452a7f0c09e9ed2` | extracted |
| Windows x64 binary | `a395030b56b126f608f2403036dddb654a9c063213e9c2b5f85d954cf490ebe6` | `codex-cli 0.149.1` |
| macOS x64 archive | `e53ee6a57a81998a2661a8159fb0ea478491f28f517d992a6f75fadcb38a9eca` | not executed |
| macOS x64 binary | `19ad079130409e2d32cbb4b02b3d622ab44e7de93a2898ce58908a0f2f5d7a06` | not executed |
| macOS arm64 archive | `151f8b96af0529c1267e7438d2cbc6d26213922fa017b96540abaf5f07d792d2` | not executed |
| macOS arm64 binary | `f0d8762236594359b60cfbe17f4c7e945a3ce8d1c91e74778838c968d250fb6c` | not executed |

## Harness invariants

- fresh local Git clone for every run
- fake `HOME` and fake `CODEX_HOME`
- environment built from an allowlist; no inherited credentials
- synthetic dummy API key whose value is omitted from results
- deterministic model server bound to `127.0.0.1`
- non-loopback proxy variables point to closed `127.0.0.1:9`
- no bypass or danger-full-access flag
- actual startup TUI keyboard decisions
- result JSON, UI log, captured requests, and SHA-256 manifest per run

## Linux full prompt-injection chain

Run directory:

```text
$HARNESS_WORK/codex-execpolicy-script-substitution-ui-0.149.1-full-injection-positive-v1
```

Result summary:

```json
{
  "classification": "CONFIRMED",
  "target_os": "linux",
  "observed_sandbox_mode": "workspace-write",
  "first_approval_decision": "approved_execpolicy_prefix",
  "command_approval_prompts": 1,
  "execpolicy_rules": "prefix_rule(pattern=[\"bash\", \"approved.sh\"], decision=\"allow\")",
  "marker_observed": true,
  "execution_log": "BEFORE_APPROVAL_CONTENT\nAFTER_APPROVAL_ATTACKER_CONTENT\n",
  "pass": true
}
```

Model/tool sequence:

```text
cat ATTACK.md
bash approved.sh                       # require_escalated, user selects p
apply_patch approved.sh                # recognized workspace edit route
bash approved.sh                       # same argv, no second command approval
```

The model request stream contains the injected file content and successful tool outputs. `approved.sh` is the only changed worktree file. Its SHA-256 changes before the second execution, and the outside marker is created under the Codex session user.

Three earlier positive repetitions using a sandboxed shell mutation also passed 3/3. One-time approval and argv-change controls both stopped at a second approval prompt without creating a marker.

## Linux cross-process restart persistence

Run directory:

```text
$HARNESS_WORK/codex-execpolicy-restart-persistence-0.149.1-v2
```

The first actual TUI process stored the following rule after the user selected
`p` and completed the benign execution:

```text
prefix_rule(pattern=["bash", "approved.sh"], decision="allow")
```

The driver terminated that Codex process, replaced only `approved.sh`, and
started a new actual TUI process with the same isolated `CODEX_HOME`. The new
process received the same `bash approved.sh` request and completed without a
command approval screen.

```json
{
  "classification": "CONFIRMED",
  "scenario": "cross-process-restart-persistence",
  "phase1": {
    "approval_prompt_seen": true,
    "decision": "approved_execpolicy_prefix",
    "completed": true
  },
  "phase2": {
    "command_approval_prompt_seen": false,
    "completed": true
  },
  "marker_observed": true,
  "execution_log": "BEFORE_APPROVAL_CONTENT\nAFTER_APPROVAL_ATTACKER_CONTENT\n",
  "pass": true
}
```

Both model requests reported `workspace-write`; no bypass flag was present.
This result separates the behavior from any in-memory approval cache and shows
that the on-disk execpolicy rule survives a full Codex process restart.

## Linux `git pull` delivery

Run directory:

```text
$HARNESS_WORK/codex-execpolicy-git-pull-0.149.1-positive-v1
```

After the benign command received `p`, the harness created a second commit in a
local publisher, pushed it to the harness-owned bare origin, and ran
`git pull --ff-only` in the victim clone. The delivery details were:

```json
{
  "before_commit": "9478d954b638060d765c0cdd509e06e0006d6a8b",
  "delivered_commit": "b46a967f3e880b613534dcaef582dce7042c3d61",
  "after_commit": "b46a967f3e880b613534dcaef582dce7042c3d61",
  "changed_files": ["approved.sh"],
  "push_returncode": 0,
  "pull_returncode": 0,
  "worktree_clean_after_pull": true
}
```

The full case passed with one command approval, different before/after script
SHA-256 values, no bypass flag, an outside marker, and an execution log
containing both `BEFORE_APPROVAL_CONTENT` and
`AFTER_APPROVAL_ATTACKER_CONTENT`.

## Windows native substitution chain

Positive run directory:

```text
C:\Users\<test-user>\codex-e2e-runs\execpolicy-native-cmd-substitution-0.149.1-positive-v1
```

Result summary:

```json
{
  "classification": "CONFIRMED",
  "target_os": "windows",
  "windows_sandbox_setup_choice": "non-admin sandbox",
  "observed_sandbox_mode": "workspace-write",
  "first_approval_decision": "approved_execpolicy_prefix",
  "command_approval_prompts": 1,
  "execpolicy_rules": "prefix_rule(pattern=[\"cmd.exe\", \"/d\", \"/c\", \"approved.cmd\"], decision=\"allow\")",
  "marker_observed": true,
  "execution_log": "BEFORE_APPROVAL_CONTENT\nAFTER_APPROVAL_ATTACKER_CONTENT\n",
  "pass": true
}
```

Sequence:

```text
cmd.exe /d /c approved.cmd             # require_escalated, user selects p
external attacker/delivery swaps approved.cmd
cmd.exe /d /c approved.cmd             # same argv, no second command approval
```

This is a native Windows command path. `whoami.txt` records the Windows user and a `C:\Users\...\project` working directory.

Controls:

| Scenario | Stored rule | Second prompt | Marker | Result |
|---|---:|---:|---:|---:|
| approve once (`y`) | no | yes | no | PASS |
| prefix approval + `approved.cmd`→`.\approved.cmd` | yes | yes | no | PASS |

The Windows TUI separately asked for file-edit approval when the model-driven apply-patch subvariant was attempted. Therefore only the external-delivery substitution chain is claimed as no-second-command-approval on Windows. The full prompt-injection chain is claimed on Linux.

## macOS status

Both official macOS archives and embedded binary hashes are fixed above. The shared Rust approval/execpolicy implementation has no macOS-only content binding in the reviewed paths, but no macOS host was available to execute the TUI. Runtime status remains **unverified**, not failed.

## Cleanup note

An early Windows probe failed to export fake `CODEX_HOME` through WSL interop and created one synthetic rule in the real Windows profile. The file contained only the harness-created rule and was removed immediately. All confirmed Windows runs use `WSLENV` path translation and isolated per-run `CODEX_HOME` directories.
