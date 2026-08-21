# Codex 0.147.0 ancestor-relocation to stdio MCP PoC

This disposable Docker PoC demonstrates the following chain with harmless marker files:

1. A normal Codex workspace-write sandbox cannot modify the project's protected `.codex` directory.
2. A first sandbox renames the writable `/tmp` ancestor and creates a decoy at the original path.
3. A second sandbox protects the decoy path while the moved real project remains writable through `/tmp`.
4. The second sandbox installs a project-local stdio MCP command in the moved real `.codex/config.toml` and restores the original path.
5. A fresh `codex exec` session eagerly starts the injected MCP command outside the command sandbox, creating `/root/codex-mcp-host-rce` in the container. The baseline verifies that the ordinary workspace-write sandbox cannot write this path.

Run from this directory:

```sh
chmod +x run.sh
./run.sh
```

For repeatability testing with fresh containers:

```sh
TRIALS=10 ./run.sh
```

The image pins `@openai/codex@0.147.0`. The container requires `--privileged` because bubblewrap needs namespace and mount capabilities in this Docker environment. Everything occurs inside the disposable container. The payload only writes diagnostic process metadata to `/root/codex-mcp-host-rce`; it does not escape Docker.

## Scope and prerequisites

- This is a **Codex command-sandbox escape**, not a Docker/container escape.
- The project must be trusted so that project-local configuration is loaded.
- A writable ancestor of the project must be renameable by sandboxed code. This PoC uses `/tmp`.
- A second Codex tool/sandbox invocation is required after relocation. In this environment, a nested `codex sandbox` from the first invocation exits before stage two because the inner bubblewrap cannot create its network namespace (`Failed to create NETLINK_ROUTE socket`). Independently, the first sandbox's original read-only bind remains part of its mount namespace after the path is renamed; a fresh outer invocation is what rebuilds protection against the decoy path.
- Triggering the injected stdio MCP requires a new session (or another operation that rebuilds MCP configuration).

## UID note

The PoC runs Codex as root only to make bubblewrap work inside Docker on this particular host. The host has `kernel.apparmor_restrict_unprivileged_userns=1`; both a UID-1000 container probe and the host's ordinary-user `codex sandbox` fail before executing a command because bubblewrap cannot configure its namespace. The vulnerable path-relocation logic itself does not depend on UID 0, but a clean non-root Docker demonstration requires a host that permits unprivileged user namespaces or an appropriate AppArmor profile.
