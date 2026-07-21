# CI Rescue demo: broken workflow to clean diagnostic

This is an included synthetic example, not a client result. It demonstrates how the tool's findings map to a focused workflow change.

## Before

The included `broken-workflow.yml` produces:

- 3 errors: unclosed expression, missing runner, and unknown job dependency
- 3 warnings: no timeout, ignored failure, and moving action branch

## Focused example patch

```diff
-    continue-on-error: true
+    timeout-minutes: 20
     steps:
-      - uses: actions/checkout@main
+      - uses: actions/checkout@v4
+      - uses: actions/setup-node@v4
+        with:
+          node-version: 22
+          cache: npm
       - run: npm ci
-      - run: npm test -- --reporter ${{ matrix.reporter
+      - run: npm test

   verify:
-    needs: [build, missing_job]
+    needs: build
+    runs-on: ubuntu-latest
+    timeout-minutes: 10
     steps:
-      - run: echo "This job has no runner"
+      - run: echo "Build completed"
```

## After

Running CI Rescue Kit against the included `fixed-workflow.yml` returns zero recognized findings and exit code 0 with `--fail-on warning`.

That result means only that none of the included diagnostic rules matched. It is not proof that npm dependencies, tests, external services, or the real GitHub Actions run will succeed. A real service delivery must still run the approved verification and record its result.
