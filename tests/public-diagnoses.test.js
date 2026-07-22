import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const root = new URL("../", import.meta.url);

test("public diagnoses are inspectable and cannot be mistaken for client proof", async () => {
  const html = await readFile(new URL("docs/index.html", root), "utf8");

  for (const commentId of [
    "5041701408",
    "5041445939",
    "5041263313",
    "5047406455",
  ]) {
    assert.match(html, new RegExp(`issuecomment-${commentId}`));
  }

  assert.match(html, /unpaid, unsolicited diagnoses/i);
  assert.match(html, /not client work, endorsements, or proof of a hosted fix/i);
});
