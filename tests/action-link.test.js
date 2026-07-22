import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const root = new URL("../", import.meta.url);
const ACTION_REPOSITORY = "https://github.com/Yunczo/ci-rescue-diagnostic-action";
const publicResources = [
  "README.md",
  "docs/index.html",
  "docs/llms.txt",
  "docs/guides/pytest-exit-code-5-no-tests-github-actions.html",
  "docs/guides/upload-artifact-no-files-found-github-actions.html",
  "docs/tools/github-actions-log-triage.html",
];

test("README and site recommend the dedicated Action reference", async () => {
  const [readme, site] = await Promise.all(
    ["README.md", "docs/index.html"].map((path) =>
      readFile(new URL(path, root), "utf8"),
    ),
  );

  for (const resource of [readme, site]) {
    assert.match(resource, /Yunczo\/ci-rescue-diagnostic-action@v1/);
    assert.match(resource, new RegExp(ACTION_REPOSITORY));
  }
});

test("public Action links no longer recommend the legacy service-repository path", async () => {
  const resources = await Promise.all(
    publicResources.map((path) => readFile(new URL(path, root), "utf8")),
  );

  for (const resource of resources) {
    assert.doesNotMatch(resource, /Yunczo\/ci-rescue-service@v1/);
    assert.doesNotMatch(
      resource,
      /github\.com\/Yunczo\/ci-rescue-service#run-the-free-diagnostic-action/,
    );
  }

  for (const resource of resources.slice(2)) {
    assert.match(resource, new RegExp(ACTION_REPOSITORY));
  }
});
