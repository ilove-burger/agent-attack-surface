# Safe policy-only PoC

This PoC demonstrates the execpolicy decision without asking sed to execute the appended command.

1. From the report directory, run:

   ```text
   codex execpolicy check --pretty \
     --rules poc/policy.rules \
     -- sed -n 1,260p /tmp/codex-sed-poc-input.txt \
     -e '1e /usr/bin/id'
   ```

2. Verify that the result is `allow` and that `matchedPrefix` stops before the appended `-e` arguments.

The check evaluates policy only. It does not execute sed or `/usr/bin/id`, so the path in the rule does not need to exist. `input.txt` is included only as a harmless fixture for an authorized end-to-end test.
