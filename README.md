# CI Rescue — focused GitHub Actions repair

One failing GitHub Actions workflow, one focused diagnosis, and one reviewable patch.

## Fixed-scope offer

**US$49 equivalent in Bitcoin · delivery within 2 days · one revision**

The service covers one workflow and one failing job path. I review the workflow plus the smallest relevant sanitized log excerpt, identify the first actionable cause, produce an in-scope patch, and return a concise delivery report with verification evidence.

[Open a service-request issue](../../issues/new?template=service-request.yml) to confirm scope before paying. GitHub issues are public: remove secrets, tokens, private URLs, personal data, and proprietary source. A redacted minimal reproduction is preferred.

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

Payment is requested only after the public intake issue has been reviewed and the scope has been accepted.

- Bitcoin mainnet: `1AHjXAgf9DEErm21HVjr59uwSoZSoT9qre`
- [Open a wallet payment request](bitcoin:1AHjXAgf9DEErm21HVjr59uwSoZSoT9qre?label=CI%20Rescue%20Service&message=One%20workflow%20repair)
- [Verify receipts independently](https://mempool.space/address/1AHjXAgf9DEErm21HVjr59uwSoZSoT9qre)

Before sending, the buyer must post the intended amount and transaction ID in the accepted intake issue. Bitcoin payments are irreversible. Do not send funds until scope and the BTC amount are confirmed in that issue.

## Proof, not invented client claims

- [Synthetic before/after example](examples/before-after.md)
- [Actual analyzer output for that synthetic example](examples/sample-report.md)
- The underlying release passed 38 automated tests, a 5,000-input fuzz smoke, a clean offline install, and a large-workflow performance check.

These examples contain no client data and are not represented as paid-client results.

## Delivery boundary

The deliverable can diagnose and patch an inspectable problem. It cannot promise that hosted runners, third-party services, credentials, or infrastructure outside the supplied evidence will behave correctly. See [service terms](SERVICE_TERMS.md).
