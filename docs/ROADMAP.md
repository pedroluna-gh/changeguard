# ChangeGuard Roadmap

  This roadmap describes the planned direction for ChangeGuard. It is intentionally
  ambitious but constrained by the project's core principles: **no database, no
  login, no external API calls at runtime, and no AI.** Everything must keep
  running locally and remain transparent and explainable.

  Priorities and timing may change based on community feedback — open an issue to
  suggest or upvote an item.

  ## v0.1 — Initial release (current)

  - Rule-based risk engine with a `0–100` score and four risk levels.
  - Service-control, change-type, Terraform, and Kubernetes rules.
  - Markdown + JSON reports with a per-source score breakdown.
  - Streamlit web app and `changeguard` CLI.
  - Composite GitHub Action and PR risk-gate workflow.

  ## v0.2 — Real Terraform plan parsing

  - Parse `terraform show -json` plan output instead of keyword matching.
  - Distinguish create / update / delete / replace per resource.
  - Map provider resource types to risk weights.

  ## v0.3 — Real Kubernetes object parsing

  - Parse Kubernetes manifests as objects (multi-document YAML).
  - Inspect probes, resource limits, replicas, and exposure per workload.
  - Detect risky `kind` + field combinations more precisely.

  ## v0.4 — Configurable policy

  - User-supplied rule weights and thresholds via a config file.
  - Enable / disable individual rules.
  - Per-environment policy (e.g. stricter rules for `production`).

  ## v0.5 — Reporting & export

  - Static HTML dashboard export.
  - Historical trend view across multiple assessments.
  - SARIF output for code-scanning integrations.

  ## v0.6 — Ecosystem integrations (optional, opt-in)

  - ServiceNow / Jira change-record linking.
  - PagerDuty / Opsgenie incident-history context.
  - Datadog / Grafana dashboard link validation.

  > Integrations will be **opt-in** and must never become a hard runtime
  > dependency — ChangeGuard always works fully offline.

  ## Future / under consideration

  - Policy-as-code approval workflows.
  - Additional cloud providers and IaC tools (Pulumi, CloudFormation).
  - Pre-commit hook packaging.
  - PyPI distribution (`pip install changeguard`).

  ## Out of scope

  - AI / ML scoring models.
  - Acting as a security boundary or a replacement for human review.
  - Storing assessment data in a hosted backend.
  