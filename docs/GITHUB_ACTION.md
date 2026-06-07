# GitHub Action Usage

ChangeGuard can run as a pull-request risk gate.

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
.github/workflows/changeguard.yml
```

Example:

```yaml
name: ChangeGuard

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
      CHANGEGUARD_INSTALL: "git+https://github.com/pedroluna-gh/changeguard.git@main"
      CHANGEGUARD_SERVICES: services.yaml
      CHANGEGUARD_CHANGE: change.yaml
      CHANGEGUARD_TERRAFORM: tfplan.txt
      CHANGEGUARD_K8S: k8s.yaml
      CHANGEGUARD_REPORT: changeguard-report.md

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install ChangeGuard
        run: pip install "$CHANGEGUARD_INSTALL"

      - name: Run ChangeGuard risk assessment
        id: changeguard
        run: |
          set -uo pipefail

          args=(--services "$CHANGEGUARD_SERVICES" --change "$CHANGEGUARD_CHANGE")

          if [ -n "${CHANGEGUARD_TERRAFORM:-}" ] && [ -f "$CHANGEGUARD_TERRAFORM" ]; then
            args+=(--terraform "$CHANGEGUARD_TERRAFORM")
          fi

          if [ -n "${CHANGEGUARD_K8S:-}" ] && [ -f "$CHANGEGUARD_K8S" ]; then
            args+=(--k8s "$CHANGEGUARD_K8S")
          fi

          args+=(--output "$CHANGEGUARD_REPORT")

          set +e
          changeguard "${args[@]}"
          exit_code=$?
          set -e

          echo "exit_code=$exit_code" >> "$GITHUB_OUTPUT"

      - name: Upload risk report
        if: always() && hashFiles(env.CHANGEGUARD_REPORT) != ''
        uses: actions/upload-artifact@v4
        with:
          name: changeguard-report
          path: ${{ env.CHANGEGUARD_REPORT }}

      - name: Comment risk report on pull request
        if: always() && github.event_name == 'pull_request' && hashFiles(env.CHANGEGUARD_REPORT) != ''
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const marker = '<!-- changeguard-report -->';
            const body = `${marker}\n` + fs.readFileSync(process.env.CHANGEGUARD_REPORT, 'utf8');

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
          if [ "${{ steps.changeguard.outputs.exit_code }}" != "0" ]; then
            echo "ChangeGuard reported CRITICAL risk."
            exit 1
          fi

          echo "ChangeGuard risk check passed."
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

For early adoption, use ChangeGuard as an advisory comment first.

After teams trust the scoring model, enable blocking behavior for `CRITICAL` risk.

Recommended rollout:

1. Week 1: report only.
2. Week 2: fail on CRITICAL.
3. Later: fail on HIGH for tier-0 services.
