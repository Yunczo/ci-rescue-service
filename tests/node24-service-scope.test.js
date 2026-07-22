import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const root = new URL("../", import.meta.url);

test("the paid scope accepts proactive Node 24 migration without implying guaranteed success", async () => {
  const [home, checker, terms, intake, readme, llms, issueTemplate] = await Promise.all(
    [
      "docs/index.html",
      "docs/tools/github-actions-node24-checker.html",
      "SERVICE_TERMS.md",
      "src/nostr-intake.js",
      "README.md",
      "docs/llms.txt",
      ".github/ISSUE_TEMPLATE/service-request.yml",
    ].map((path) => readFile(new URL(path, root), "utf8")),
  );

  assert.match(home, /Repair one workflow—or migrate it to Node 24/);
  assert.match(home, /Failure or migration summary/);
  assert.match(terms, /one failing job path or one defined proactive Node 24 migration goal/i);
  assert.match(terms, /revision addressing the originally accepted failure or migration goal/i);
  assert.match(checker, /action-ref inventory/);
  assert.match(checker, /hosted success is not guaranteed/i);
  assert.match(checker, /\.\.\/\?request=node24#anonymous-intake/);
  assert.match(intake, /requestType === "node24"/);
  assert.match(intake, /GitHub Actions Node 24 migration review/);
  assert.match(readme, /one defined proactive Node 24 migration goal/i);
  assert.match(readme, /GitHub Actions repair or Node 24 migration/i);
  assert.match(llms, /one defined proactive Node 24 migration goal/i);
  assert.match(issueTemplate, /Proactive Node 24 migration/);
  assert.match(issueTemplate, /workflow is not failing yet/i);
  assert.doesNotMatch(issueTemplate, /id: failure_area/);
});
