import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const root = new URL("../", import.meta.url);

test("Node 24 pages are linked from the homepage, sitemap, llms file, and README", async () => {
  const resources = await Promise.all(
    ["docs/index.html", "docs/sitemap.xml", "docs/llms.txt", "README.md"].map((path) =>
      readFile(new URL(path, root), "utf8"),
    ),
  );

  for (const resource of resources) {
    assert.match(resource, /github-actions-node24-checker\.html/);
    assert.match(resource, /github-actions-node24-migration\.html/);
    assert.match(resource, /github-actions-node24-migration-proof\.html/);
  }
});

test("checker page has a blocking CSP and conservative privacy copy", async () => {
  const page = await readFile(new URL("docs/tools/github-actions-node24-checker.html", root), "utf8");

  assert.match(page, /connect-src 'none'/);
  assert.match(page, /form-action 'none'/);
  assert.match(page, /src="\.\.\/assets\/node24-checker\.js"/);
  assert.match(page, /Reference snapshot: July 22, 2026/);
  assert.match(page, /cannot prove runtime compatibility/i);
  assert.doesNotMatch(page, /Google Analytics|googletagmanager|plausible\.io/i);
});

test("migration guide cites only official GitHub sources and keeps payment behind scope", async () => {
  const guide = await readFile(new URL("docs/guides/github-actions-node24-migration.html", root), "utf8");

  assert.match(guide, /github\.blog\/changelog\/2025-09-19-deprecation-of-node-20/);
  assert.match(guide, /github\.com\/actions\/checkout\/releases\/tag\/v7\.0\.1/);
  assert.match(guide, /github\.com\/actions\/cache\/releases\/tag\/v6\.1\.0/);
  assert.match(guide, /github\.com\/actions\/download-artifact\/releases\/tag\/v8\.0\.1/);
  assert.match(guide, /github\.com\/actions\/setup-node\/releases\/tag\/v7\.0\.0/);
  assert.match(guide, /github\.com\/actions\/setup-python\/releases\/tag\/v7\.0\.0/);
  assert.match(guide, /github\.com\/actions\/upload-artifact\/releases\/tag\/v7\.0\.1/);
  assert.match(guide, /confirmed in writing before payment/i);
  assert.doesNotMatch(guide, /guarantee(?:d|s)? (?:a )?(?:pass|fix|result)/i);
});

test("synthetic proof maps every change to primary evidence and narrows the hosted-run claim", async () => {
  const [proof, home, checker, guide] = await Promise.all(
    [
      "docs/guides/github-actions-node24-migration-proof.html",
      "docs/index.html",
      "docs/tools/github-actions-node24-checker.html",
      "docs/guides/github-actions-node24-migration.html",
    ].map((path) => readFile(new URL(path, root), "utf8")),
  );

  assert.match(proof, /Synthetic example — not client work/);
  assert.match(proof, /Synthetic BEFORE/);
  assert.match(proof, /Synthetic AFTER/);
  assert.match(proof, /Reviewable synthetic workflow diff/);
  assert.match(proof, /ACTIONS_ALLOW_USE_UNSECURE_NODE_VERSION/);
  assert.match(proof, /actions\/checkout@v4/);
  assert.match(proof, /actions\/checkout@v7/);
  assert.match(proof, /actions\/setup-node@v4/);
  assert.match(proof, /actions\/setup-node@v7/);

  assert.match(proof, /github\.blog\/changelog\/2025-09-19-deprecation-of-node-20/);
  assert.match(proof, /github\.com\/actions\/checkout\/releases\/tag\/v5\.0\.0/);
  assert.match(proof, /github\.com\/actions\/checkout\/releases\/tag\/v7\.0\.1/);
  assert.match(proof, /github\.com\/actions\/setup-node\/releases\/tag\/v5\.0\.0/);
  assert.match(proof, /github\.com\/actions\/setup-node\/releases\/tag\/v7\.0\.0/);

  assert.match(proof, /actions\/runs\/29933717773/);
  assert.match(proof, /blob\/a3420d0e514369d51e10e40e876951e85d7e3e9d\/\.github\/workflows\/site-check\.yml/);
  assert.match(proof, /That is the entire claim/);
  assert.match(proof, /selected project Node 22—not Node 24/);
  assert.match(proof, /does not prove another workflow, matrix, runner, repository, or service will pass/);

  assert.match(proof, /\$49-equivalent-in-Bitcoin scope/);
  assert.match(proof, /href="\.\.\/\?request=node24#anonymous-intake"/);
  assert.match(proof, /Scope and the exact BTC amount are confirmed in writing before payment/);
  assert.match(proof, /not a paid-client result/i);

  for (const referringPage of [home, checker, guide]) {
    assert.match(referringPage, /github-actions-node24-migration-proof\.html/);
  }
});
