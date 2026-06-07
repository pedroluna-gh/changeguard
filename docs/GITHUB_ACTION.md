# GitHub Action Usage

PreflightOps can run as a pull-request risk gate.

It can:

- read a service catalog;
- read a change request;
- optionally scan a Terraform plan;
- optionally scan Kubernetes manifests;
- generate a Markdown report;
- upload the report as an artifact;
- comment the report on the pull request;
- fail the workflow when risk is `CRITICAL`.

---

## Example workflow

Create this file:

```text
.github/workflows/preflightops.yml
```

Example:

```yaml
name: PreflightOps

on:
  pull_request:
    branches:
      - main

permissions:
  contents: read
  pull-requests: write

jobs:
  risk-review:
    name: Risk review
    runs-on: ubuntu-latest

    env:
      PREFLIGHTOPS_INSTALL: "git+https://github.com/pedroluna-gh/preflightops.git@main"
      PREFLIGHTOPS_SERVICES: services.yaml
      PREFLIGHTOPS_CHANGE: change.yaml
      PREFLIGHTOPS_TERRAFORM: tfplan.txt
      PREFLIGHTOPS_K8S: k8s.yaml
      PREFLIGHTOPS_REPORT: preflightops-report.md

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install PreflightOps
        run: pip install "$PREFLIGHTOPS_INSTALL"

      - name: Run PreflightOps risk assessment
        id: preflightops
        run: |
          set -uo pipefail

          args=(--services "$PREFLIGHTOPS_SERVICES" --change "$PREFLIGHTOPS_CHANGE")

          if [ -n "${PREFLIGHTOPS_TERRAFORM:-}" ] && [ -f "$PREFLIGHTOPS_TERRAFORM" ]; then
            args+=(--terraform "$PREFLIGHTOPS_TERRAFORM")
          fi

          if [ -n "${PREFLIGHTOPS_K8S:-}" ] && [ -f "$PREFLIGHTOPS_K8S" ]; then
            args+=(--k8s "$PREFLIGHTOPS_K8S")
          fi

          args+=(--output "$PREFLIGHTOPS_REPORT")

          set +e
          preflightops "${args[@]}"
          exit_code=$?
          set -e

          echo "exit_code=$exit_code" >> "$GITHUB_OUTPUT"

      - name: Upload risk report
        if: always() && hashFiles(env.PREFLIGHTOPS_REPORT) != ''
        uses: actions/upload-artifact@v4
        with:
          name: preflightops-report
          path: ${{ env.PREFLIGHTOPS_REPORT }}

      - name: Comment risk report on pull request
        if: always() && github.event_name == 'pull_request' && hashFiles(env.PREFLIGHTOPS_REPORT) != ''
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const marker = '<!-- preflightops-report -->';
            const body = `${marker}\n` + fs.readFileSync(process.env.PREFLIGHTOPS_REPORT, 'utf8');

            const { owner, repo } = context.repo;
            const issue_number = context.issue.number;

            const comments = await github.paginate(
              github.rest.issues.listComments,
              { owner, repo, issue_number },
            );

            const existing = comments.find((c) => c.body && c.body.includes(marker));

            if (existing) {
              await github.rest.issues.updateComment({
                owner,
                repo,
                comment_id: existing.id,
                body,
              });
            } else {
              await github.rest.issues.createComment({
                owner,
                repo,
                issue_number,
                body,
              });
            }

      - name: Fail on CRITICAL risk
        if: always()
        run: |
          if [ "${{ steps.preflightops.outputs.exit_code }}" != "0" ]; then
            echo "PreflightOps reported CRITICAL risk."
            exit 1
          fi

          echo "PreflightOps risk check passed."
```

---

## Recommended repository files

Your application repository should include:

```text
services.yaml
change.yaml
tfplan.txt      # optional
k8s.yaml        # optional
```

---

## Exit codes

| Exit code | Meaning |
|---:|---|
| 0 | Risk level is not CRITICAL. |
| 1 | Risk level is CRITICAL. |
| 2 | Input, YAML, or runtime error. |

---

## Recommended workflow behavior

For early adoption, use PreflightOps as an advisory comment first.

After teams trust the scoring model, enable blocking behavior for `CRITICAL` risk.

Recommended rollout:

1. Week 1: report only.
2. Week 2: fail on CRITICAL.
3. Later: fail on HIGH for tier-0 services.
