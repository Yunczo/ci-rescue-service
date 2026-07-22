# CI Rescue — focused GitHub Actions repair

[![Public proof](https://github.com/Yunczo/ci-rescue-service/actions/workflows/public-proof.yml/badge.svg)](https://github.com/Yunczo/ci-rescue-service/actions/workflows/public-proof.yml)
[![GitHub Action check](https://github.com/Yunczo/ci-rescue-service/actions/workflows/action-check.yml/badge.svg)](https://github.com/Yunczo/ci-rescue-service/actions/workflows/action-check.yml)

One failing GitHub Actions workflow, one focused diagnosis, and one reviewable patch.

## Try the free browser-only log triage

Paste a sanitized GitHub Actions excerpt into the [local log triage tool](https://yunczo.github.io/ci-rescue-service/tools/github-actions-log-triage.html). It matches focused failure signatures in the browser, makes no analyzer network request, stores nothing, and reports line numbers without reproducing raw log text. Sanitize first: browser extensions and the local device remain outside the page boundary.

## Check a workflow for the Node 24 migration

Paste sanitized GitHub.com workflow YAML into the [browser-only Node 24 workflow checker](https://yunczo.github.io/ci-rescue-service/tools/github-actions-node24-checker.html). It identifies temporary Node 20 opt-outs, self-hosted runner review points, and action refs that need release-note or metadata inspection. The checker has no network or storage code and never rewrites YAML. Its official-action snapshot is dated July 22, 2026; Node 24 release floors are tracked separately from latest releases, while pinned SHAs, local or third-party actions, and ambiguous refs are routed to manual review rather than guessed. The linked guide documents the separate GitHub Enterprise Server artifact path.

## Run the free diagnostic Action

Add the offline, read-only analyzer to a workflow after checkout:

```yaml
- uses: Yunczo/ci-rescue-diagnostic-action@v1
  with:
    workflow-path: .github/workflows/ci.yml
    fail-on: none
```

It reads one repository-relative workflow and, optionally, one saved sanitized log. It writes `ci-rescue-report.md`, adds the report to the job summary, never makes a network request, and never edits the inspected files. Existing report files are not overwritten. Oversized job summaries are truncated below GitHub's upload limit while the complete report file is preserved.

Optional inputs are `log-path`, `report-path`, and `fail-on` (`none`, `info`, `warning`, or `error`). Outputs are `report-path`, `finding-count`, and `highest-severity`. Upload the report in a later step if you want it as a run artifact. For maximum supply-chain assurance, pin the Action to a reviewed full commit SHA instead of a moving major tag.

The Action is tested on GitHub-hosted Linux, macOS, and Windows runners. A self-hosted runner needs Bash and Python 3.9 or newer.

The dedicated [CI Rescue Diagnostic Action repository](https://github.com/Yunczo/ci-rescue-diagnostic-action) is the recommended source for new workflows. The copy in this service repository remains available for existing references.

The rules cover common workflow structure, action-reference, lockfile, test-command, timeout, and artifact-path failures. A clean report means only that no bundled rule matched; it is not a guarantee that a hosted run will pass.

## Fixed-scope offer

**US$49 equivalent in Bitcoin · scope response within 24 hours · delivery within 2 days · one revision**

The service covers one workflow and one failing job path. I review the workflow plus the smallest relevant sanitized log excerpt, identify the first actionable cause, produce an in-scope patch, and return a concise delivery report with verification evidence.

[Open the no-account encrypted intake](https://yunczo.github.io/ci-rescue-service/#anonymous-intake) or [use a public service-request issue](../../issues/new?template=service-request.yml) to confirm scope before paying. In either channel, remove secrets, tokens, private URLs, personal data, proprietary source, and production details. A redacted minimal reproduction is preferred.

The no-account route creates a random ticket key in the buyer's browser and uses NIP-17 gift-wrapped messages over independent Nostr relays. The message payload is encrypted, but relay metadata is observable and browser storage is the only copy of the buyer's ticket key. See the [anonymous intake boundary](ANONYMOUS_INTAKE.md).

## Included

- Workflow YAML structure and job configuration
- Dependency-install and lockfile failures
- Test discovery and command-path problems
- Cache and artifact path mistakes
- Runner timeouts and action-reference reliability problems
- A focused patch plus a short root-cause report

## Excluded

- Security, vulnerability, credential, or access-control review
- Secret collection or production access
- Cloud-account administration and live infrastructure changes
- Multi-repository migrations or full CI/CD redesigns
- Guarantees that third-party services or the eventual hosted run will pass

## Payment

Payment is requested only after an intake request has been reviewed and the scope has been accepted in either a signed anonymous-inbox reply or a public GitHub issue reply.

- Bitcoin mainnet: `1AHjXAgf9DEErm21HVjr59uwSoZSoT9qre`
- Wallet URI to copy into a compatible wallet: `bitcoin:1AHjXAgf9DEErm21HVjr59uwSoZSoT9qre?label=CI%20Rescue%20Service&message=One%20workflow%20repair`
- [Verify receipts independently](https://mempool.space/address/1AHjXAgf9DEErm21HVjr59uwSoZSoT9qre)

Before sending, the buyer must confirm the intended amount in the accepted intake channel. After broadcasting, send the transaction ID in the same channel so the receipt can be verified. Bitcoin payments are irreversible. Do not send funds until scope and the exact BTC amount are confirmed in a reply signed by the service key or posted by `Yunczo` in this repository.

## Proof, not invented client claims

- [Synthetic before/after example](examples/before-after.md)
- [Actual analyzer output for that synthetic example](examples/sample-report.md)
- [Exact broken workflow](examples/broken-workflow.yml) and [corrected workflow](examples/fixed-workflow.yml)
- [Release verification record](RELEASE_VERIFICATION.md)
- [Download the free MIT-licensed offline toolkit](https://github.com/Yunczo/ci-rescue-service/releases/download/toolkit-v1.0.0/CI_Rescue_Kit_v1.0.0.zip) used for these synthetic proof artifacts
- [Run the free GitHub Action](https://github.com/Yunczo/ci-rescue-diagnostic-action) without downloading the toolkit
- The underlying release passed 38 automated tests, a 5,000-input fuzz smoke, a clean offline install, and a large-workflow performance check.

These examples contain no client data and are not represented as paid-client results.

## Free troubleshooting guides

- [Fix `npm ci` lockfile errors in GitHub Actions](https://yunczo.github.io/ci-rescue-service/guides/npm-ci-lockfile-github-actions.html)
- [Fix `package-lock.json` lookup in a monorepo workflow](https://yunczo.github.io/ci-rescue-service/guides/package-lock-monorepo-github-actions.html)
- [Fix `upload-artifact` “No files were found” warnings](https://yunczo.github.io/ci-rescue-service/guides/upload-artifact-no-files-found-github-actions.html)
- [Fix pytest exit code 5 when no tests are collected](https://yunczo.github.io/ci-rescue-service/guides/pytest-exit-code-5-no-tests-github-actions.html)
- [Migrate GitHub Actions workflows to Node 24](https://yunczo.github.io/ci-rescue-service/guides/github-actions-node24-migration.html)

## Support the free tools

If the free toolkit, Action, browser-only log triage, or troubleshooting guides saved you time, an optional Bitcoin tip is welcome at `1AHjXAgf9DEErm21HVjr59uwSoZSoT9qre`. Tips are optional and never required to use any free resource. They buy no service, diagnosis, response, delivery, priority, refund, or other consideration, and are separate from CI Rescue intake. See [the support boundary](SUPPORT.md).

## Delivery boundary

The deliverable can diagnose and patch an inspectable problem. It cannot promise that hosted runners, third-party services, credentials, or infrastructure outside the supplied evidence will behave correctly. See [service terms](SERVICE_TERMS.md).
