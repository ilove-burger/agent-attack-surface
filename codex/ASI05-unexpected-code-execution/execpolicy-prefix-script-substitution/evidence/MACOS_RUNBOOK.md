# macOS actual-TUI validation runbook

## Status

The `0.149.1` macOS npm artifacts and binaries are hash-pinned, but they have
not yet been executed on a macOS host. A Linux host cannot provide evidence for
the macOS Seatbelt sandbox or the native TUI startup path.

The runner uses a fresh fake `HOME` and `CODEX_HOME`, a dummy API key, a
loopback-only deterministic model endpoint, and synthetic marker files. Do not
run it with real credentials in the environment.

## 1. Obtain the architecture-specific package

Apple Silicon:

```sh
mkdir -p /tmp/codex-macos-0.149.1-arm64
cd /tmp/codex-macos-0.149.1-arm64
npm pack '@openai/codex@0.149.1-darwin-arm64'
shasum -a 256 openai-codex-0.149.1-darwin-arm64.tgz
tar -xzf openai-codex-0.149.1-darwin-arm64.tgz
chmod +x package/vendor/aarch64-apple-darwin/bin/codex
```

Expected archive SHA-256:

```text
151f8b96af0529c1267e7438d2cbc6d26213922fa017b96540abaf5f07d792d2
```

Expected binary SHA-256:

```text
f0d8762236594359b60cfbe17f4c7e945a3ce8d1c91e74778838c968d250fb6c
```

Intel Mac:

```sh
mkdir -p /tmp/codex-macos-0.149.1-x64
cd /tmp/codex-macos-0.149.1-x64
npm pack '@openai/codex@0.149.1-darwin-x64'
shasum -a 256 openai-codex-0.149.1-darwin-x64.tgz
tar -xzf openai-codex-0.149.1-darwin-x64.tgz
chmod +x package/vendor/x86_64-apple-darwin/bin/codex
```

Expected archive SHA-256:

```text
e53ee6a57a81998a2661a8159fb0ea478491f28f517d992a6f75fadcb38a9eca
```

Expected binary SHA-256:

```text
19ad079130409e2d32cbb4b02b3d622ab44e7de93a2898ce58908a0f2f5d7a06
```

## 2. Verify prerequisites

```sh
python3 --version
git --version
python3 -c 'import pexpect; print(pexpect.__version__)'
```

If `pexpect` is absent, install it into a disposable test user rather than a
production Python environment.

## 3. Run the three-case matrix

From this finding directory, on Apple Silicon:

```sh
bash ./run-macos-matrix.sh \
  /tmp/codex-macos-0.149.1-arm64/package/vendor/aarch64-apple-darwin/bin/codex \
  /tmp/codex-execpolicy-macos-0.149.1
```

On Intel, substitute the x64 binary path. The runner refuses a binary whose
SHA-256 does not match the pinned `0.149.1` value.

## 4. Acceptance criteria

The final three summary lines must show:

```text
positive: pass=True classification=CONFIRMED prompts=1 marker=True
approve-once-control: pass=True classification=CONFIRMED prompts=2 marker=False
argv-change-control: pass=True classification=CONFIRMED prompts=2 marker=False
```

Each case must also have `target_os: macos`, `observed_sandbox_mode:
workspace-write`, `bypass_flag_used: false`, and a complete `MANIFEST.sha256`.

If the TUI wording or startup flow differs, retain the entire run directory and
classify the run as inconclusive; do not manually create or edit marker files.

## 5. Evidence to return

Return the following without credentials or unrelated user data:

- all three `result.json` and `summary.md` files;
- all three `MANIFEST.sha256` files;
- the package archive and binary SHA-256 values;
- `uname -a`, `sw_vers`, and `uname -m` output;
- a redacted TUI screenshot of the first prefix approval and the positive
  completion screen.
