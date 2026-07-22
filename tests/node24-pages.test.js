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
  assert.match(guide, /github\.com\/actions\/setup-node\/releases\/tag\/v7\.0\.0/);
  assert.match(guide, /github\.com\/actions\/setup-python\/releases\/tag\/v7\.0\.0/);
  assert.match(guide, /github\.com\/actions\/upload-artifact\/releases\/tag\/v7\.0\.1/);
  assert.match(guide, /confirmed in writing before payment/i);
  assert.doesNotMatch(guide, /guarantee(?:d|s)? (?:a )?(?:pass|fix|result)/i);
});
