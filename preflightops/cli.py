"""Command-line interface for PreflightOps.

Example
-------
    python -m preflightops.cli \\
        --services examples/services-critical-risk.yaml \\
        --change examples/change-critical-risk.yaml \\
        --terraform examples/terraform-critical.txt \\
        --k8s examples/k8s-risk.yaml \\
        --output report.md \\
        --json-output report.json

Exit codes
----------
    1  if the assessed risk level is CRITICAL
    0  otherwise
"""

import argparse
import sys

import yaml

from .risk_engine import assess_risk
from .report import generate_markdown_report, generate_json_report


def _load_yaml(path):
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _load_text(path):
    if not path:
        return ""
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="preflightops",
        description="Pre-deployment risk assessment for SRE and Platform teams.",
    )
    parser.add_argument("--services", required=True, help="Path to the service catalog YAML file")
    parser.add_argument("--change", required=True, help="Path to the change request YAML file")
    parser.add_argument("--terraform", default=None, help="Optional path to a Terraform plan/diff text file")
    parser.add_argument("--k8s", default=None, help="Optional path to a Kubernetes manifest YAML file")
    parser.add_argument("--output", default="report.md", help="Where to write the Markdown report")
    parser.add_argument(
        "--json-output",
        default=None,
        help="Optional path to also write the machine-readable JSON report",
    )

    args = parser.parse_args(argv)

    try:
        services = _load_yaml(args.services)
        change = _load_yaml(args.change)
        terraform_text = _load_text(args.terraform)
        k8s_text = _load_text(args.k8s)
    except (OSError, yaml.YAMLError) as exc:
        print(f"Error loading input files: {exc}", file=sys.stderr)
        return 2

    try:
        result = assess_risk(services, change, terraform_text, k8s_text)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    report = generate_markdown_report(result)

    try:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(report)
    except OSError as exc:
        print(f"Error writing report: {exc}", file=sys.stderr)
        return 2

    if args.json_output:
        json_report = generate_json_report(result)
        try:
            with open(args.json_output, "w", encoding="utf-8") as handle:
                handle.write(json_report)
        except OSError as exc:
            print(f"Error writing JSON report: {exc}", file=sys.stderr)
            return 2

    print(f"Service:     {result['service']}")
    print(f"Environment: {result['environment']}")
    print(f"Risk Score:  {result['risk_score']}/100")
    print(f"Risk Level:  {result['risk_level']}")
    print(f"Report written to: {args.output}")
    if args.json_output:
        print(f"JSON report written to: {args.json_output}")

    return 1 if result["risk_level"] == "CRITICAL" else 0


if __name__ == "__main__":
    sys.exit(main())
