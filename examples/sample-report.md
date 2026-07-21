# CI Rescue Kit report

- Input: `broken-workflow.yml`
- Analyzer: `workflow`
- Findings: 3 error, 3 warning, 0 info

## WF003 · ERROR · Unbalanced GitHub expression

A `${{` expression is not followed by a matching `}}` delimiter.

**Recommended next step:** Close the incomplete expression or remove the unmatched delimiter.

**Confidence:** high

**Evidence**
- unclosed expression begins on line 14

## WF021 · ERROR · Job has no runner or reusable workflow

Job `verify` has neither `runs-on` nor a job-level `uses` field.

**Recommended next step:** Add `runs-on` and `steps`, or call a reusable workflow with job-level `uses`.

**Confidence:** high

**Evidence**
- job `verify` begins on line 16

## WF040 · ERROR · Job depends on an unknown job

Job `verify` declares `needs: missing_job`, but no matching job ID exists.

**Recommended next step:** Correct the job ID or add the missing job.

**Confidence:** high

**Evidence**
- line 17; known jobs: build, verify

## WF023 · WARNING · Job has no explicit timeout

Job `build` can consume runner time until GitHub's platform limit.

**Recommended next step:** Set a realistic `timeout-minutes` value for this job.

**Confidence:** high

**Evidence**
- job `build` begins on line 8

## WF030 · WARNING · Failure is explicitly ignored

`continue-on-error: true` can make a broken command look successful.

**Recommended next step:** Keep it only when the failure is expected, and add a later step that records or validates the outcome.

**Confidence:** high

**Evidence**
- job `build`, line 10

## WF032 · WARNING · Action uses a moving branch

`actions/checkout@main` can change without a workflow edit and make CI behavior drift.

**Recommended next step:** Use a documented release tag or commit accepted by your dependency policy.

**Confidence:** high

**Evidence**
- job `build`, line 12

---
Generated locally by CI Rescue Kit 1.0.0. Input content is not included in this report.
