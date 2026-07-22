import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import { analyzeWorkflow, extractUses, KNOWN_ACTIONS, REFERENCE_DATE } from "../src/node24-checker.js";

test("reference snapshot separates Node 24 floors from latest releases", () => {
  assert.equal(REFERENCE_DATE, "2026-07-22");
  assert.deepEqual(KNOWN_ACTIONS, {
    "actions/checkout": { node24Major: 5, node24Release: "v5.0.0", latestMajor: 7, latestRelease: "v7.0.1" },
    "actions/setup-node": { node24Major: 5, node24Release: "v5.0.0", latestMajor: 7, latestRelease: "v7.0.0" },
    "actions/setup-python": { node24Major: 6, node24Release: "v6.0.0", latestMajor: 7, latestRelease: "v7.0.0" },
    "actions/upload-artifact": { node24Major: 6, node24Release: "v6.0.0", latestMajor: 7, latestRelease: "v7.0.1", githubDotComOnly: true },
  });
});

test("extracts quoted and unquoted uses entries without commented examples", () => {
  const uses = extractUses([
    "# - uses: actions/checkout@v4",
    "steps:",
    "  - uses: actions/checkout@v7 # reviewed",
    "  - uses: 'actions/setup-node@v7' # pinned by policy",
    "  - { name: Python, uses: actions/setup-python@v6 }",
  ].join("\n"));

  assert.deepEqual(uses, [
    { line: 3, target: "actions/checkout@v7" },
    { line: 4, target: "actions/setup-node@v7" },
    { line: 5, target: "actions/setup-python@v6" },
  ]);
});

test("flags an older known major without claiming its bundled runtime", () => {
  const result = analyzeWorkflow("steps:\n  - uses: actions/checkout@v4\n");

  assert.equal(result.warningCount, 1);
  assert.equal(result.findings[0].code, "ACT005");
  assert.match(result.findings[0].summary, /review/i);
  assert.doesNotMatch(result.findings[0].summary, /runs on Node 20/i);
});

test("recognizes each current official major", () => {
  const workflow = Object.keys(KNOWN_ACTIONS).map((action) => `- uses: ${action}@v7`).join("\n");
  const result = analyzeWorkflow(workflow);

  assert.equal(result.actionCount, 4);
  assert.equal(result.node24RecognizedCount, 4);
  assert.equal(result.warningCount, 0);
  assert.ok(result.findings.every(({ code }) => code === "ACT006"));
});

test("recognizes verified Node 24 floors without forcing the latest major", () => {
  const result = analyzeWorkflow([
    "- uses: actions/checkout@v5",
    "- uses: actions/setup-node@v5.0.0",
    "- uses: actions/setup-python@v6",
    "- uses: actions/upload-artifact@v6.0.0",
  ].join("\n"));

  assert.equal(result.node24RecognizedCount, 4);
  assert.equal(result.warningCount, 0);
  assert.match(result.findings[0].summary, /not required solely for the Node 24 migration/i);
  assert.match(result.findings[3].summary, /GitHub Enterprise Server/i);
});

test("does not bless an unverified same-major patch tag", () => {
  const result = analyzeWorkflow("- uses: actions/checkout@v7.999.999\n");

  assert.equal(result.node24RecognizedCount, 0);
  assert.equal(result.manualReviewCount, 1);
  assert.equal(result.warningCount, 1);
  assert.equal(result.findings[0].code, "ACT007");
});

test("does not bless future, wrong-case, or noncanonical bare-major refs", () => {
  for (const ref of ["v8", "v999", "V5", "V5.0.0", "v05", "v07", "v0000007"]) {
    const result = analyzeWorkflow(`- uses: actions/checkout@${ref}\n`);
    assert.equal(result.node24RecognizedCount, 0, ref);
    assert.equal(result.manualReviewCount, 1, ref);
    assert.equal(result.warningCount, 1, ref);
    assert.equal(result.findings[0].code, "ACT007", ref);
  }
});

test("requires release mapping for immutable SHAs", () => {
  const sha = "0123456789abcdef0123456789abcdef01234567";
  const result = analyzeWorkflow(`- uses: actions/setup-python@${sha}\n`);

  assert.equal(result.manualReviewCount, 1);
  assert.equal(result.findings[0].code, "ACT002");
  assert.match(result.findings[0].summary, /cannot infer/i);
});

test("does not make compatibility claims for third-party actions", () => {
  const result = analyzeWorkflow("- uses: vendor/example@v99\n");

  assert.equal(result.manualReviewCount, 1);
  assert.equal(result.findings[0].code, "ACT003");
  assert.match(result.findings[0].summary, /action\.yml/);
});

test("flags the temporary opt-out and self-hosted review", () => {
  const result = analyzeWorkflow([
    "runs-on: [self-hosted, linux, arm]",
    "env:",
    "  ACTIONS_ALLOW_USE_UNSECURE_NODE_VERSION: true",
    "steps:",
    "  - uses: actions/checkout@v7",
  ].join("\n"));

  assert.deepEqual(new Set(result.findings.map(({ code }) => code)), new Set(["RUN001", "CFG001", "ACT006"]));
  assert.equal(result.warningCount, 2);
});

test("does not infer settings from comments or shell commands", () => {
  const result = analyzeWorkflow([
    "runs-on: ubuntu-latest # not self-hosted",
    "steps:",
    "  - run: echo ACTIONS_ALLOW_USE_UNSECURE_NODE_VERSION=true",
    "  - uses: actions/checkout@v5",
  ].join("\n"));

  assert.deepEqual(result.findings.map(({ code }) => code), ["ACT006"]);
});

test("recognizes a quoted self-hosted label in a block list", () => {
  const result = analyzeWorkflow([
    "runs-on:",
    "  - 'self-hosted'",
    "  - linux",
    "steps:",
    "  - uses: actions/checkout@v5",
  ].join("\n"));

  assert.ok(result.findings.some(({ code }) => code === "RUN001"));
});

test("recognizes explicit Node 24 test mode as evidence, not a guarantee", () => {
  const result = analyzeWorkflow("env:\n  FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: 'true'\n");

  assert.ok(result.findings.some(({ code }) => code === "CFG002"));
  assert.ok(result.findings.some(({ code }) => code === "YML001"));
});

test("routes local actions to metadata review and ignores Docker runtime migration", () => {
  const result = analyzeWorkflow("- uses: ./local-action\n- uses: docker://alpine:3.22\n");

  assert.equal(result.actionCount, 2);
  assert.equal(result.manualReviewCount, 1);
  assert.deepEqual(result.findings.map(({ code }) => code), ["ACT008"]);
});

test("flags missing and non-release refs", () => {
  const result = analyzeWorkflow("- uses: owner/action\n- uses: actions/upload-artifact@main\n");

  assert.deepEqual(result.findings.map(({ code }) => code), ["ACT001", "ACT004"]);
  assert.equal(result.warningCount, 2);
});

test("rejects oversized text", () => {
  assert.throws(() => analyzeWorkflow("x".repeat(300_001)), RangeError);
});

test("blank input is never a green result", () => {
  const result = analyzeWorkflow("");

  assert.equal(result.warningCount, 1);
  assert.equal(result.findings[0].code, "YML001");
});

test("browser source contains no network, persistence, or HTML injection primitives", async () => {
  const source = await readFile(new URL("../src/node24-checker.js", import.meta.url), "utf8");

  assert.doesNotMatch(source, /\bfetch\s*\(/);
  assert.doesNotMatch(source, /XMLHttpRequest/);
  assert.doesNotMatch(source, /WebSocket/);
  assert.doesNotMatch(source, /sendBeacon/);
  assert.doesNotMatch(source, /localStorage/);
  assert.doesNotMatch(source, /sessionStorage/);
  assert.doesNotMatch(source, /indexedDB/);
  assert.doesNotMatch(source, /document\.cookie/);
  assert.doesNotMatch(source, /innerHTML/);
  assert.doesNotMatch(source, /insertAdjacentHTML/);
});
