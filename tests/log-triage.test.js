import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import { analyzeLog, SIGNATURES } from "../src/log-triage.js";

test("ships a focused, uniquely coded signature set", () => {
  assert.ok(SIGNATURES.length >= 15);
  assert.equal(new Set(SIGNATURES.map(({ code }) => code)).size, SIGNATURES.length);
});

test("matches npm lockfile drift and links the focused guide", () => {
  const result = analyzeLog([
    "npm ERR! code EUSAGE",
    "npm ci can only install packages when package.json and package-lock.json are in sync.",
    "Process completed with exit code 1",
  ].join("\n"));

  assert.deepEqual(result.findings.map(({ code }) => code), ["LOG105"]);
  assert.match(result.findings[0].guide, /npm-ci-lockfile-github-actions\.html$/);
});

test("does not call unrelated npm EUSAGE lockfile drift", () => {
  const result = analyzeLog("npm ERR! code EUSAGE\nnpm ERR! Usage: npm publish <package>\n");

  assert.ok(!result.findings.some(({ code }) => code === "LOG105"));
  assert.ok(result.findings.some(({ code }) => code === "LOG199"));
});

test("matches a missing monorepo lockfile separately", () => {
  const result = analyzeLog([
    "npm ERR! The npm ci command can only install with an existing package-lock.json",
    "npm ERR! enoent Could not read package-lock.json in /repo/packages/app",
  ].join("\n"));

  assert.deepEqual(result.findings.map(({ code }) => code), ["LOG114"]);
  assert.match(result.findings[0].guide, /package-lock-monorepo-github-actions\.html$/);
});

test("matches pytest no-collection without classifying an unrelated exit five", () => {
  const pytest = analyzeLog("============================= no tests ran in 0.01s =============================\n");
  const unrelated = analyzeLog("Custom compiler stopped\nProcess completed with exit code 5\n");

  assert.deepEqual(pytest.findings.map(({ code }) => code), ["LOG106"]);
  assert.ok(!unrelated.findings.some(({ code }) => code === "LOG106"));
  assert.ok(unrelated.findings.some(({ code }) => code === "LOG199"));
});

test("matches an empty artifact pattern and retains an independent unknown failure", () => {
  const result = analyzeLog([
    "No files were found with the provided path: dist/**",
    "Process completed with exit code 2",
  ].join("\n"));

  assert.deepEqual(new Set(result.findings.map(({ code }) => code)), new Set(["LOG112", "LOG199"]));
});

test("matches the operating-system argument limit", () => {
  const result = analyzeLog("/usr/bin/jq: Argument list too long\nProcess completed with exit code 126\n");

  assert.deepEqual(result.findings.map(({ code }) => code), ["LOG115"]);
  assert.match(result.findings[0].remediation, /--rawfile/);
});

test("does not echo private log text in evidence", () => {
  const marker = "PRIVATE_BUILD_VALUE";
  const result = analyzeLog(`${marker}: command not found\n`);
  const rendered = result.findings.map(({ evidence }) => evidence).join(" ");

  assert.doesNotMatch(rendered, new RegExp(marker));
  assert.match(rendered, /line\(s\): 1/);
});

test("clean log has no findings", () => {
  assert.deepEqual(analyzeLog("Build complete\nAll tests passed\n").findings, []);
});

test("rejects oversized text", () => {
  assert.throws(() => analyzeLog("x".repeat(500_001)), RangeError);
});

test("browser source contains no outbound network primitive", async () => {
  const source = await readFile(new URL("../src/log-triage.js", import.meta.url), "utf8");

  assert.doesNotMatch(source, /\bfetch\s*\(/);
  assert.doesNotMatch(source, /XMLHttpRequest/);
  assert.doesNotMatch(source, /WebSocket/);
  assert.doesNotMatch(source, /sendBeacon/);
});

test("browser source contains no persistence or HTML injection primitive", async () => {
  const source = await readFile(new URL("../src/log-triage.js", import.meta.url), "utf8");

  assert.doesNotMatch(source, /localStorage/);
  assert.doesNotMatch(source, /sessionStorage/);
  assert.doesNotMatch(source, /indexedDB/);
  assert.doesNotMatch(source, /document\.cookie/);
  assert.doesNotMatch(source, /innerHTML/);
  assert.doesNotMatch(source, /insertAdjacentHTML/);
});
