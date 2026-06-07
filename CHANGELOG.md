# Changelog

All notable changes to ChangeGuard are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

- Nothing yet.

## [0.1.0] - 2026-06-07

Initial public release.

### Added

- **Risk engine** that turns a service catalog and a change request into a
  `0–100` risk score, a risk level (`LOW` / `MEDIUM` / `HIGH` / `CRITICAL`),
  a plain-English recommendation, the triggered rules, and a list of missing
  operational controls.
- **Service-control and change-type rules**: production change, critical
  service, missing owner / runbook / business impact, missing or vague rollback
  plan, incomplete monitoring plan, missing validation plan, and database /
  security / network / infrastructure change types.
- **Terraform scanner** for risky keywords (IAM, security groups, firewalls,
  databases, KMS, DNS, public IP exposure, and `destroy` / `delete` actions).
- **Kubernetes scanner** for risky signals (Ingress, Secret, NetworkPolicy,
  StatefulSet, LoadBalancer exposure, `replicas: 0`, and Deployments missing
  readiness / liveness probes).
- **Markdown and JSON reports** with a per-source score breakdown.
- **Streamlit web app** with built-in LOW / HIGH / CRITICAL example loaders.
- **`changeguard` CLI** that exits `1` on CRITICAL risk and `2` on input errors.
- **Composite GitHub Action** (`action.yml`) and a ready-to-use PR risk-gate
  workflow that comments the report on pull requests and uploads it as an artifact.
- **Documentation**: README, risk model, input schema, GitHub Action guide,
  roadmap, screenshots guide, plus `CONTRIBUTING.md` and `SECURITY.md`.
- **pytest suite** covering the engine, validators, scanners, reports, CLI,
  web app, and the documented example scenarios.

[Unreleased]: https://github.com/pedroluna-gh/changeguard/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/pedroluna-gh/changeguard/releases/tag/v0.1.0
