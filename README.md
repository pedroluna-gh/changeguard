# ChangeGuard

> **Stop risky production changes before they become incidents.**

ChangeGuard is built from real-world SRE, cloud operations, ITSM, and change-governance experience in mission-critical 24/7 environments.
It is designed for teams that need more production discipline than a simple checklist, but less overhead than a full enterprise ITSM platform.

ChangeGuard is a pre-deployment risk assessment tool for SRE, DevOps, and Platform Engineering teams. It turns a service catalog and a proposed change into a clear **0–100 risk score**, a **risk level** (`LOW` / `MEDIUM` / `HIGH` / `CRITICAL`), a plain-English recommendation, and an actionable list of the exact gaps to fix — *before* the change ships.

It runs as a **Streamlit web app** for interactive reviews and as a **CLI / GitHub Action** for automated pull-request gates. No database, no login, no external APIs, no AI — everything runs locally.

[![CI](https://img.shields.io/badge/tests-pytest-0a7?logo=pytest)](#running-the-tests)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-3776ab?logo=python&logoColor=white)](#requirements)

<!-- Add a hero screenshot of the Streamlit app here, e.g.: -->
<!-- ![ChangeGuard web app](docs/screenshots/app-overview.png) -->

---

## The problem

Most production incidents are triggered by **changes** — deployments, config updates, and infrastructure edits. Teams invest heavily in CI/CD, Terraform, Kubernetes, and observability, yet the decision *"is this change safe to ship?"* is still made by gut feel in a rushed review:

- Rollback plans are missing, vague, or untested.
- Critical services lack runbooks or a named owner.
- Monitoring and post-deploy validation are afterthoughts.
- Risky Terraform (IAM, destroy/delete, security groups) and Kubernetes (exposed Secrets, missing probes, `replicas: 0`) changes slip through review.

ChangeGuard makes that judgement **explicit, consistent, and auditable**. It encodes change-governance and production-readiness checks as transparent rules so every change gets the same scrutiny — and so reviewers can focus on the findings that actually matter.

## What it checks

- Production changes without a valid rollback plan
- Critical / high-criticality services
- Missing service ownership, runbooks, and business impact
- Incomplete monitoring plans and missing post-deploy validation
- Risky Terraform signals: IAM/role changes, security groups, firewalls, DNS, KMS, database instances, public IP exposure, and `destroy` / `delete` actions
- Risky Kubernetes signals: Ingress, Secret, NetworkPolicy, StatefulSet, LoadBalancer exposure, `replicas: 0`, and Deployments missing readiness / liveness probes

## Quick demo

Try it in under a minute without writing any YAML:

```bash
# 1. Install (with the web UI extras)
pip install -e ".[app]"     # run from the changeguard/ directory

# 2. Launch the web app
streamlit run app.py
```

Then in the browser: click **Low / High / Critical Risk Example** to load a ready-made scenario, hit **Run Risk Assessment**, and explore the score, the per-category breakdown, the triggered rules, and the downloadable Markdown / JSON reports. Edit the YAML to match your own change and re-run.

Prefer the terminal? Score one of the bundled examples directly:

```bash
changeguard \
  --services examples/services-high-risk.yaml \
  --change examples/change-high-risk.yaml \
  --output report.md
```

<!-- Add a screenshot of the risk results / score breakdown here, e.g.: -->
<!-- ![Risk assessment results](docs/screenshots/results.png) -->

## Installation

Install ChangeGuard and its `changeguard` CLI with a single command:

```bash
pip install git+https://github.com/pedroluna-gh/changeguard.git@main
```

> Replace the URL with your own fork/repo. Once published to PyPI, this becomes `pip install changeguard`.

To also run the Streamlit web UI, add the optional `app` extras:

```bash
pip install "changeguard[app] @ git+https://github.com/pedroluna-gh/changeguard.git@main"
```

### Develop from a clone

```bash
git clone https://github.com/pedroluna-gh/changeguard.git
cd changeguard
pip install -e ".[app]"      # editable install with the web UI extras
```

`requirements.txt` does this for you: `pip install -r requirements.txt`.

### Requirements

- Python 3.9+
- Core dependency: `pyyaml`. The web UI extras add `streamlit` and `pandas`.

## Usage

### Web app

```bash
streamlit run app.py
```

Load an example, edit the **Service Catalog** and **Change Request** YAML, optionally paste a **Terraform plan** and a **Kubernetes manifest**, and click **Run Risk Assessment**. Download the result as Markdown or JSON.

### Command line

```bash
changeguard \
  --services examples/services-critical-risk.yaml \
  --change examples/change-critical-risk.yaml \
  --terraform examples/terraform-critical.txt \
  --k8s examples/k8s-risk.yaml \
  --output report.md \
  --json-output report.json
```

(The equivalent `python -m changeguard.cli ...` also works.)

The CLI prints the score and level, writes a Markdown report to `--output` (and an optional JSON report to `--json-output`), and **exits with code `1` when the risk level is `CRITICAL`** (otherwise `0`) — so you can fail a pipeline on critical risk.

### GitHub Action (PR risk gate)

ChangeGuard ships with a ready-to-use workflow at [`.github/workflows/changeguard.yml`](.github/workflows/changeguard.yml). On every pull request it scores the change, posts the Markdown report as a PR comment (updated in place), uploads it as a build artifact, and **fails the check when the risk level is `CRITICAL`**.

Point the workflow at your input files via the `env` block at the top of the file:

```yaml
env:
  CHANGEGUARD_INSTALL: "git+https://github.com/pedroluna-gh/changeguard.git@main"
  CHANGEGUARD_SERVICES: services.yaml   # required: service catalog
  CHANGEGUARD_CHANGE: change.yaml       # required: change request
  CHANGEGUARD_TERRAFORM: tfplan.txt     # optional: Terraform plan/diff
  CHANGEGUARD_K8S: k8s.yaml             # optional: Kubernetes manifest
  CHANGEGUARD_REPORT: changeguard-report.md
```

Optional inputs are skipped automatically when the file is absent. The workflow needs `pull-requests: write` permission to post the comment (already declared in the example file).

## Example output

A `HIGH`-risk production deployment produces a report like this:

```markdown
# ChangeGuard Risk Report

## Summary

Service: checkout-api
Environment: production
Change Type: deployment
Risk Score: 80/100
Risk Level: HIGH

## Recommendation

Senior review recommended before deployment. Address missing controls before proceeding.

## Score Breakdown

### Service Controls — +80 pts (100%, 4 findings)

- production-change | medium | +20 | Change targets production environment
- critical-service | high | +25 | Service is marked as high or critical
- missing-monitoring-plan | medium | +20 | No monitoring plan defined
- missing-validation-plan | medium | +15 | Post-deploy validation plan is missing

## Missing Controls

- monitoring_plan
- validation_plan

## Business Impact

Customers may be unable to complete checkout
```

The JSON report (`--json-output`) contains the same data plus a grouped `score_breakdown` summary, ready for tooling and auditing.

## How scoring works

ChangeGuard sums the points from every triggered rule and scanner finding, capping the total at 100:

| Score   | Level      | What it means                                                        |
| ------- | ---------- | ------------------------------------------------------------------- |
| 0–30    | `LOW`      | Proceed with the normal deployment process.                         |
| 31–60   | `MEDIUM`   | Proceed with caution; ensure owner review and post-deploy checks.   |
| 61–80   | `HIGH`     | Senior review recommended; address missing controls first.          |
| 81–100  | `CRITICAL` | Block until rollback, monitoring, ownership, or validation gaps close. |

Findings are grouped by source — **Service Controls**, **Change Type**, **Terraform**, and **Kubernetes** — so you can see exactly where the risk comes from.

## Project structure

```
changeguard/
├── app.py                     # Streamlit web app (UI, example loader, results)
├── changeguard/               # Core package
│   ├── risk_engine.py         # Rules, scoring, levels, recommendations
│   ├── validators.py          # Rollback / monitoring / validation plan checks
│   ├── scanners.py            # Terraform & Kubernetes keyword risk scanners
│   ├── report.py              # Markdown & JSON report generators
│   ├── sample_data.py         # Built-in low/high/critical scenarios
│   └── cli.py                 # Command-line entry point (exit 1 on CRITICAL)
├── examples/                  # Example YAML / text inputs for each scenario
├── tests/                     # pytest suite (engine, validators, scanners, CLI, UI)
├── .github/workflows/         # Ready-to-use PR risk-gate Action
├── pyproject.toml             # Packaging + console script + optional extras
└── requirements.txt           # Editable install for local development
```

## Running the tests

ChangeGuard ships with a `pytest` suite covering the risk-engine rules, the rollback/monitoring/validation validators, the Terraform/Kubernetes scanners (including the readiness/liveness probe checks), the CLI and report generators, the web UI, and the documented LOW / HIGH / CRITICAL scenarios.

```bash
pip install -r requirements.txt
pytest
```

Run from the `changeguard/` directory. Tests live under `tests/`.

## Contributing

Contributions are welcome — bug reports, new risk rules, scanner signals, and docs all help.

1. Fork the repo and create a feature branch.
2. Make your change and **add or update tests** under `tests/`.
3. Run `pytest` and make sure the full suite passes.
4. Keep the project's constraints intact: **no database, no login, no external API calls, no AI.**
5. Open a pull request with a clear description of the change and the risk it addresses.

New risk rules should be transparent and explainable: a stable rule id, a severity, a point value, and a human-readable description. Please open an issue first for larger changes so we can align on direction.

## Security

ChangeGuard is a **local, offline** tool: it makes no outbound network calls, stores no data, and requires no credentials. Your service catalogs, change requests, Terraform plans, and Kubernetes manifests never leave your machine or CI runner.

- Treat any input you paste as sensitive — Terraform plans and Kubernetes manifests can contain infrastructure details. The bundled examples use placeholder data only.
- ChangeGuard is a **decision-support aid, not a security boundary.** It surfaces risk signals to inform human review; it does not guarantee a change is safe.
- Found a vulnerability? Please report it privately via a GitHub security advisory rather than a public issue.

## Roadmap

- Real Terraform plan JSON parser
- Real Kubernetes YAML object parser
- ServiceNow / Jira integration
- PagerDuty / Opsgenie incident-history connector
- Datadog / Grafana dashboard link validation
- Static HTML dashboard export
- Policy-as-code approval workflows

## Suggested GitHub topics

When publishing, add topics like:

`sre` · `devops` · `platform-engineering` · `site-reliability-engineering` · `change-management` · `risk-assessment` · `production-readiness` · `rollback` · `observability` · `terraform` · `kubernetes` · `ci-cd` · `pre-deployment` · `streamlit` · `python`

## License

Released under the [MIT License](LICENSE).

---

_Built for SRE, DevOps, Platform Engineering and Cloud Operations teams._
