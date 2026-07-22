import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const ADDRESS = "1AHjXAgf9DEErm21HVjr59uwSoZSoT9qre";
const root = new URL("../", import.meta.url);

test("site and README expose the exact optional-tip address", async () => {
  const [html, readme] = await Promise.all([
    readFile(new URL("docs/index.html", root), "utf8"),
    readFile(new URL("README.md", root), "utf8"),
  ]);

  assert.match(html, new RegExp(ADDRESS));
  assert.match(readme, new RegExp(ADDRESS));
});

test("all public support copy makes tips optional and without consideration", async () => {
  const resources = await Promise.all(
    ["docs/index.html", "README.md", "SUPPORT.md"].map((path) =>
      readFile(new URL(path, root), "utf8"),
    ),
  );

  for (const resource of resources) {
    assert.match(resource, /Tips are optional and never required/i);
    assert.match(resource, /buy no service, diagnosis, response, delivery, (?:support, )?priority, refund, or other consideration/i);
  }
});
