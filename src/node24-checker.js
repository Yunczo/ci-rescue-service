const MAX_CHARACTERS = 300_000;

export const REFERENCE_DATE = "2026-07-22";

const CACHE_ACTION = Object.freeze({ node24Major: 5, node24Release: "v5.0.0", latestMajor: 6, latestRelease: "v6.1.0" });

export const KNOWN_ACTIONS = Object.freeze({
  "actions/checkout": Object.freeze({ node24Major: 5, node24Release: "v5.0.0", latestMajor: 7, latestRelease: "v7.0.1" }),
  "actions/cache": CACHE_ACTION,
  "actions/cache/restore": CACHE_ACTION,
  "actions/cache/save": CACHE_ACTION,
  "actions/download-artifact": Object.freeze({
    node24Major: 7,
    node24Release: "v7.0.0",
    latestMajor: 8,
    latestRelease: "v8.0.1",
    githubDotComOnly: true,
    ghesNote: "GitHub Enterprise Server does not support download-artifact@v4+; current official guidance points to v3 (Node 16) or v3-node20 (Node 20), not a Node 24 release line.",
  }),
  "actions/setup-node": Object.freeze({ node24Major: 5, node24Release: "v5.0.0", latestMajor: 7, latestRelease: "v7.0.0" }),
  "actions/setup-python": Object.freeze({ node24Major: 6, node24Release: "v6.0.0", latestMajor: 7, latestRelease: "v7.0.0" }),
  "actions/upload-artifact": Object.freeze({
    node24Major: 6,
    node24Release: "v6.0.0",
    latestMajor: 7,
    latestRelease: "v7.0.1",
    githubDotComOnly: true,
    ghesNote: "GitHub Enterprise Server has a separate official upload-artifact@v3.2.2 Node 24 path.",
  }),
});

function makeFinding(code, severity, title, summary, line, action = "", ref = "") {
  return Object.freeze({ code, severity, title, summary, line, action, ref });
}

function stripYamlValue(rawValue) {
  const value = rawValue.trim().replace(/\s+#.*$/, "").trim();
  if (!value) return "";
  if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
    return value.slice(1, -1).trim();
  }
  return value;
}

export function extractUses(text) {
  if (typeof text !== "string") throw new TypeError("Workflow input must be text.");
  return text.split(/\r?\n/).flatMap((line, index) => {
    if (/^\s*#/.test(line)) return [];
    const match = line.match(/^\s*(?:-\s*)?uses\s*:\s*(.*?)\s*$/i)
      ?? line.match(/^\s*-\s*\{[^}]*?\buses\s*:\s*([^,}]+)[^}]*\}\s*(?:#.*)?$/i);
    if (!match) return [];
    const target = stripYamlValue(match[1]);
    if (!target) return [];
    return [{ line: index + 1, target }];
  });
}

function parseAction(target) {
  if (target.startsWith("./")) return { kind: "local", action: target, ref: "" };
  if (target.startsWith("docker://")) return { kind: "docker", action: target, ref: "" };
  const separator = target.lastIndexOf("@");
  if (separator < 1 || separator === target.length - 1) {
    return { kind: "missing-ref", action: target, ref: "" };
  }
  return {
    kind: "remote",
    action: target.slice(0, separator).toLowerCase(),
    ref: target.slice(separator + 1),
  };
}

function isFullSha(ref) {
  return /^[0-9a-f]{40}$/i.test(ref);
}

function majorFromRef(ref) {
  const match = ref.match(/^v(\d+)(?:\.\d+(?:\.\d+)?)?$/i);
  return match ? Number(match[1]) : null;
}

function isBareMajorRef(ref) {
  return /^v(?:0|[1-9]\d*)$/.test(ref);
}

function lineWithoutComment(line) {
  return line.replace(/\s+#.*$/, "").trimEnd();
}

function selfHostedLineNumbers(lines) {
  const matches = new Set();
  let blockIndent = null;
  lines.forEach((rawLine, index) => {
    const line = lineWithoutComment(rawLine);
    if (!line.trim()) return;
    const indent = line.match(/^\s*/)?.[0].length ?? 0;
    if (blockIndent !== null && indent <= blockIndent) blockIndent = null;

    const runsOn = line.match(/^(\s*)runs-on\s*:\s*(.*)$/i);
    if (runsOn) {
      const value = runsOn[2].trim();
      blockIndent = value ? null : runsOn[1].length;
      if (/(?:^|[\[,\s])["']?self-hosted["']?(?:$|[\],\s])/i.test(value)) matches.add(index + 1);
      return;
    }
    if (blockIndent !== null && /^\s*-\s*["']?self-hosted["']?\s*$/i.test(line)) matches.add(index + 1);
  });
  return matches;
}

export function analyzeWorkflow(text) {
  if (typeof text !== "string") throw new TypeError("Workflow input must be text.");
  if (text.length > MAX_CHARACTERS) throw new RangeError(`Workflow input exceeds ${MAX_CHARACTERS.toLocaleString("en-US")} characters.`);

  const lines = text.split(/\r?\n/);
  const uses = extractUses(text);
  const findings = [];
  let node24RecognizedCount = 0;
  let manualReviewCount = 0;
  const selfHostedLines = selfHostedLineNumbers(lines);

  lines.forEach((line, index) => {
    const code = lineWithoutComment(line);
    if (/^\s*#/.test(line)) return;
    if (/^\s*["']?ACTIONS_ALLOW_USE_UNSECURE_NODE_VERSION["']?\s*:\s*["']?true["']?\s*$/i.test(code)) {
      findings.push(makeFinding(
        "CFG001",
        "warning",
        "Temporary Node 20 opt-out is enabled",
        "GitHub says this escape hatch works only until Node 20 is removed from the runner later in fall 2026. Remove it after compatible actions and runners are verified.",
        index + 1,
      ));
    }
    if (/^\s*["']?FORCE_JAVASCRIPT_ACTIONS_TO_NODE24["']?\s*:\s*["']?true["']?\s*$/i.test(code)) {
      findings.push(makeFinding(
        "CFG002",
        "info",
        "Node 24 test mode is explicit",
        "This flag is useful test evidence, but a passing run and reviewed action release notes are still required.",
        index + 1,
      ));
    }
    if (selfHostedLines.has(index + 1)) {
      findings.push(makeFinding(
        "RUN001",
        "warning",
        "Self-hosted runner needs a compatibility check",
        "Use Actions Runner v2.327.1 or later, verify the host OS and architecture, and test Node 24. GitHub notes that Node 24 does not support ARM32 and is incompatible with macOS 13.4 or earlier.",
        index + 1,
      ));
    }
  });

  uses.forEach(({ line, target }) => {
    const parsed = parseAction(target);
    if (parsed.kind === "docker") return;
    if (parsed.kind === "local") {
      manualReviewCount += 1;
      findings.push(makeFinding(
        "ACT008",
        "info",
        "Local action needs metadata review",
        "Inspect the local action.yml or action.yaml. A local JavaScript action can declare node20 or node24; a composite or Docker action has a different runtime boundary.",
        line,
        parsed.action,
      ));
      return;
    }
    if (parsed.kind === "missing-ref") {
      manualReviewCount += 1;
      findings.push(makeFinding(
        "ACT001",
        "warning",
        "Remote action has no reviewable ref",
        "Add an intentional release ref or immutable commit SHA according to the repository's dependency policy.",
        line,
        parsed.action,
      ));
      return;
    }

    const known = KNOWN_ACTIONS[parsed.action];
    if (isFullSha(parsed.ref)) {
      manualReviewCount += 1;
      findings.push(makeFinding(
        "ACT002",
        "info",
        "Pinned SHA needs release mapping",
        known
          ? `The ref is immutable, but this offline checker cannot infer whether it corresponds to the Node 24 floor ${known.node24Release}. Map it to official release metadata and inspect action.yml before changing it.`
          : "The ref is immutable, but this offline checker cannot infer its bundled runtime. Map it to official release metadata and inspect action.yml.",
        line,
        parsed.action,
        parsed.ref,
      ));
      return;
    }

    if (!known) {
      manualReviewCount += 1;
      findings.push(makeFinding(
        "ACT003",
        "info",
        "Third-party action needs metadata review",
        "Inspect the referenced release and its action.yml runs.using value. This checker does not make runtime claims about third-party actions.",
        line,
        parsed.action,
        parsed.ref,
      ));
      return;
    }

    const major = majorFromRef(parsed.ref);
    if (major === null) {
      manualReviewCount += 1;
      findings.push(makeFinding(
        "ACT004",
        "warning",
        "Official action uses a non-release ref",
        `The ${parsed.ref} ref cannot be compared with the Node 24 floor ${known.node24Release} or latest snapshot ${known.latestRelease}. Review official release metadata and choose a ref under the repository's dependency policy.`,
        line,
        parsed.action,
        parsed.ref,
      ));
    } else if (major < known.node24Major) {
      manualReviewCount += 1;
      findings.push(makeFinding(
        "ACT005",
        "warning",
        `Ref predates this action's Node 24 floor`,
        `This workflow uses major v${major}; the verified Node 24 release line begins at ${known.node24Release}. Review every intervening release note for breaking changes, preserve required inputs and permissions, use Actions Runner v2.327.1 or later, then test the hosted workflow.`,
        line,
        parsed.action,
        parsed.ref,
      ));
    } else if ((isBareMajorRef(parsed.ref) && major <= known.latestMajor) || parsed.ref === known.node24Release || parsed.ref === known.latestRelease) {
      node24RecognizedCount += 1;
      const latestNote = major === known.latestMajor
        ? `It also matches this checker's latest major snapshot (${known.latestRelease}).`
        : `The latest snapshot is ${known.latestRelease}, but a latest-major upgrade is not required solely for the Node 24 migration.`;
      const platformNote = known.githubDotComOnly
        ? ` This recommendation is for GitHub.com. ${known.ghesNote}`
        : "";
      findings.push(makeFinding(
        "ACT006",
        "pass",
        "Verified Node 24 action generation recognized",
        `${parsed.action} uses a verified Node 24-capable official release line. ${latestNote}${platformNote} Review its release notes and run the workflow; this is not a pass guarantee.`,
        line,
        parsed.action,
        parsed.ref,
      ));
    } else {
      manualReviewCount += 1;
      findings.push(makeFinding(
        "ACT007",
        "warning",
        "Exact release is not in this offline snapshot",
        `The ${parsed.ref} ref is not one of this checker's verified refs. Confirm that the tag exists, inspect its official action.yml runtime, and review its release notes. Do not downgrade automatically.`,
        line,
        parsed.action,
        parsed.ref,
      ));
    }
  });

  if (uses.length === 0) {
    findings.push(makeFinding(
      "YML001",
      "warning",
      "No uses entries were found",
      text.trim()
        ? "Paste a complete workflow or the steps containing action references. Reusable workflows and generated YAML may require separate inspection."
        : "Paste a sanitized workflow or the steps containing action references.",
      0,
    ));
  }

  const warningCount = findings.filter(({ severity }) => severity === "warning").length;
  return Object.freeze({
    actionCount: uses.length,
    node24RecognizedCount,
    manualReviewCount,
    warningCount,
    findings: Object.freeze(findings),
  });
}

function appendText(parent, tag, text, className = "") {
  const element = document.createElement(tag);
  if (className) element.className = className;
  element.textContent = text;
  parent.append(element);
  return element;
}

function renderResult(container, result) {
  container.replaceChildren();
  result.findings.forEach((finding) => {
    const article = document.createElement("article");
    article.className = `finding finding-${finding.severity}`;
    const heading = appendText(article, "div", "", "finding-heading");
    appendText(heading, "strong", finding.title);
    appendText(heading, "span", `${finding.code}${finding.line ? ` · line ${finding.line}` : ""}`, "finding-code");
    if (finding.action) appendText(article, "code", `${finding.action}${finding.ref ? `@${finding.ref}` : ""}`, "action-ref");
    appendText(article, "p", finding.summary);
    container.append(article);
  });

  if (result.findings.length === 0) {
    appendText(container, "p", "No findings. A blank or local-action-only result is not a compatibility guarantee.", "empty-result");
  }
}

function initializeBrowser() {
  const form = document.querySelector("#node24-form");
  const input = document.querySelector("#workflow-input");
  const status = document.querySelector("#node24-status");
  const results = document.querySelector("#node24-results");
  const counter = document.querySelector("#workflow-counter");
  const sampleButton = document.querySelector("#load-node24-sample");
  const clearButton = document.querySelector("#clear-workflow");
  if (!form || !input || !status || !results || !counter || !sampleButton || !clearButton) return;

  const updateCounter = () => {
    const lines = input.value ? input.value.split(/\r?\n/).length : 0;
    counter.textContent = `${input.value.length.toLocaleString("en-US")} / ${MAX_CHARACTERS.toLocaleString("en-US")} characters · ${lines.toLocaleString("en-US")} lines`;
  };

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    try {
      const result = analyzeWorkflow(input.value);
      renderResult(results, result);
      results.hidden = false;
      status.dataset.state = result.warningCount || result.manualReviewCount || result.node24RecognizedCount === 0 ? "warning" : "ready";
      status.textContent = `${result.actionCount} action reference${result.actionCount === 1 ? "" : "s"} inspected · ${result.node24RecognizedCount} verified Node 24 generation${result.node24RecognizedCount === 1 ? "" : "s"} recognized · ${result.manualReviewCount} manual review item${result.manualReviewCount === 1 ? "" : "s"} · ${result.warningCount} warning${result.warningCount === 1 ? "" : "s"}.`;
    } catch (error) {
      results.replaceChildren();
      results.hidden = true;
      status.dataset.state = "warning";
      status.textContent = error instanceof Error ? error.message : "The workflow could not be analyzed.";
    }
  });

  input.addEventListener("input", updateCounter);
  sampleButton.addEventListener("click", () => {
    input.value = `name: CI\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    env:\n      ACTIONS_ALLOW_USE_UNSECURE_NODE_VERSION: true\n    steps:\n      - uses: actions/checkout@v4\n      - uses: actions/setup-node@v7\n        with:\n          node-version: 24\n      - uses: vendor/example-action@v2\n      - run: npm ci && npm test\n`;
    updateCounter();
    input.focus();
  });
  clearButton.addEventListener("click", () => {
    input.value = "";
    results.replaceChildren();
    results.hidden = true;
    status.dataset.state = "idle";
    status.textContent = "Nothing checked yet.";
    updateCounter();
    input.focus();
  });
  updateCounter();
}

if (typeof document !== "undefined") initializeBrowser();
