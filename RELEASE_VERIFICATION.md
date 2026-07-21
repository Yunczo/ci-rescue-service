# CI Rescue Kit 1.0.0 release verification

Verified on 2026-07-21. This is a reproducible QA record for the offline analyzer used to create the public synthetic example. It is not a client result.

## Release archive

- File: `CI_Rescue_Kit_v1.0.0.zip`
- SHA-256: `cf8f513c66b2951c5358f73f17ca759e9ee7471695c9406fab2f25960709c369`
- Archive integrity: `unzip -t` passed with no errors
- Cache/build artifacts: none found in the archive

## Extracted-product QA

- Automated tests: **38/38 passed**
- 10,000-job workflow benchmark (568,908 bytes): **0.165 seconds**
- [Broken workflow example](examples/broken-workflow.yml): produced the expected prioritized errors and warnings
- [Fixed workflow example](examples/fixed-workflow.yml): zero recognized findings and exit code 0 with `--fail-on warning`
- npm lockfile example: one high-confidence `LOG105` finding and exit code 1 with `--fail-on error`
- Same-file and hard-link output collision tests: passed
- Existing report overwrite protection and explicit `--force`: passed
- Full source-path redaction in text, Markdown, and JSON output: passed
- Deterministic fuzz smoke: 5,000 randomized inputs passed through both analyzers without an exception
- All included Python files parsed successfully using Python 3.9 grammar compatibility mode

## Clean installation QA

- Installed from a freshly extracted archive into a clean virtual environment
- Used `pip install --no-index --no-build-isolation`
- No third-party runtime or build packages were downloaded
- Installed command returned `ci-rescue 1.0.0`
- Installed command successfully analyzed the fixed workflow example

## Verification boundary

These results describe local automated checks of release 1.0.0. They do not prove that a buyer's hosted workflow, dependencies, credentials, or third-party services will pass.
