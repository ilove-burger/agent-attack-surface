# Verification status for this submission bundle

> Updated: 2026-08-21
> Source: `711a5f8b3a6eb40134146ae9ec22fdcdda5e3170`

## Completed in the packaging session

| Check | Result |
|---|---|
| `full-chain/verify_fixture.py` synthetic three-principal self-check | PASS |
| live provenance test: Resource read leaves `memory_mode=enabled` and is claimable | PASS |
| Python syntax checks | PASS |
| Bash syntax checks | PASS |
| test patch apply/reverse cleanup | PASS; target files clean |

## Not completed in the packaging session

The combined runner was stopped after the live test to avoid spending additional time compiling three
more Rust test variants. The hardening build was interrupted before a test result, and phase-1/phase-2
tests were not rerun in this packaging session.

Their patches and earlier sanitized observations are included:

- call-time hardening: `proposed-hardening.patch` + `hardening-regression-test.patch`
- phase-1: `phase1-persistence-test.patch`
- phase-2: `phase2-consolidation-test.patch`
- prior normal-TUI and full-chain results: the other files in this `evidence/` directory

Therefore the newly observed result is only the live primitive test plus the fixture self-check. The
pipeline and hardening claims retain their prior evidence status; this file must not be read as a new
four-test pass.

