import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import { updateIntakeStatus } from "../src/intake-status.js";

const root = new URL("../", import.meta.url);

function fakeStatus({ hidden = true } = {}) {
  return {
    dataset: {},
    focusCalls: [],
    hidden,
    scrollCalls: [],
    textContent: "",
    focus(options) {
      this.focusCalls.push(options);
    },
    scrollIntoView(options) {
      this.scrollCalls.push(options);
    },
  };
}

test("Node 24 intake context is query-gated and repeats the accepted scope", async () => {
  const [home, source, terms] = await Promise.all(
    ["docs/index.html", "src/nostr-intake.js", "SERVICE_TERMS.md"].map((path) =>
      readFile(new URL(path, root), "utf8"),
    ),
  );

  assert.match(home, /id="node24-intake-summary" hidden/);
  assert.match(home, /US\$49 equivalent in Bitcoin/);
  assert.match(home, /one GitHub Actions workflow/);
  assert.match(home, /one defined Node 24 migration goal/);
  assert.match(home, /one focused patch or unified diff/);
  assert.match(home, /a short root-cause and verification report/);
  assert.match(home, /one revision addressing the accepted goal/);
  assert.match(home, /scope response is normally posted within 24 hours/i);
  assert.match(home, /Default delivery is within 48 hours/);
  assert.match(home, /exact BTC amount, payment address, quote expiry, and delivery window/);
  assert.match(home, /Hosted-run success is not guaranteed/);

  for (const phrase of [
    "one GitHub Actions workflow",
    "one defined Node 24 migration goal",
    "one focused patch or unified diff",
    "short root-cause and verification report",
  ]) {
    assert.match(terms, new RegExp(phrase));
  }

  assert.match(
    source,
    /if \(requestType === "node24"\) \{\s*node24OfferSummary\.hidden = false;/,
  );
  assert.equal(source.match(/node24OfferSummary\.hidden = false/g)?.length, 1);
});

test("submission outcomes use one live region and move focus only when actionable", () => {
  const ticketStatus = fakeStatus({ hidden: false });
  const submissionStatus = fakeStatus();

  updateIntakeStatus(ticketStatus, submissionStatus, "Checking replies…");
  assert.equal(ticketStatus.textContent, "Checking replies…");
  assert.equal(ticketStatus.dataset.state, "neutral");
  assert.equal(submissionStatus.hidden, true);
  assert.equal(submissionStatus.focusCalls.length, 0);
  assert.equal(submissionStatus.scrollCalls.length, 0);

  updateIntakeStatus(
    ticketStatus,
    submissionStatus,
    "Complete the required fields.",
    "error",
    { useSubmission: true, focusSubmission: true },
  );
  assert.equal(ticketStatus.textContent, "Checking replies…");
  assert.equal(ticketStatus.dataset.state, "neutral");
  assert.equal(submissionStatus.hidden, false);
  assert.equal(submissionStatus.textContent, "Complete the required fields.");
  assert.equal(submissionStatus.dataset.state, "error");
  assert.deepEqual(submissionStatus.focusCalls, [{ preventScroll: true }]);
  assert.deepEqual(submissionStatus.scrollCalls, [{ block: "nearest" }]);
});

test("intake markup and source keep ticket status while adding local accessible feedback", async () => {
  const [home, source, bundle] = await Promise.all(
    ["docs/index.html", "src/nostr-intake.js", "docs/assets/nostr-intake.js"].map((path) =>
      readFile(new URL(path, root), "utf8"),
    ),
  );

  assert.match(
    home,
    /<form class="intake-form" id="anonymous-intake-form" novalidate>/,
  );
  assert.match(
    home,
    /<button type="submit">[^<]+<\/button>\s*<div class="intake-submit-status" id="anonymous-intake-submit-status" role="status" aria-live="polite" aria-atomic="true" tabindex="-1" hidden><\/div>/,
  );
  assert.match(home, /id="anonymous-intake-status" role="status" aria-live="polite"/);
  assert.match(source, /updateIntakeStatus\(status, submissionStatus, message, state, options\)/);
  assert.match(source, /!form\.checkValidity\(\)/);
  assert.equal(source.match(/focusSubmission: true/g)?.length, 3);
  assert.match(source, /useSubmission: true/);
  assert.doesNotMatch(source, /mirrorSubmission/);
  assert.doesNotMatch(source, /submissionStatus\.innerHTML/);

  for (const marker of [
    "anonymous-intake-submit-status",
    "node24-intake-summary",
    "scrollIntoView",
    "GitHub Actions Node 24 migration review",
  ]) {
    assert.match(bundle, new RegExp(marker));
  }
});

test("proof repeats the paid CTA immediately after hosted-run evidence", async () => {
  const proof = await readFile(
    new URL("docs/guides/github-actions-node24-migration-proof.html", root),
    "utf8",
  );
  const hostedRun = proof.indexOf("Inspect successful hosted run 29933717773");
  const repeatedCta = proof.indexOf("Have one workflow? Open the $49-equivalent Node 24 scope review");
  const limits = proof.indexOf("<h2>Limits and non-generalization.</h2>");

  assert.ok(hostedRun >= 0);
  assert.ok(repeatedCta > hostedRun);
  assert.ok(limits > repeatedCta);
  assert.equal(proof.match(/href="\.\.\/\?request=node24#anonymous-intake"/g)?.length, 2);
  assert.match(proof, /no payment yet/);
});
