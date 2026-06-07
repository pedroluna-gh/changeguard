"""Tests for the command-line entry point (``changeguard.cli``).

The CLI is what a CI pipeline runs: its exit code (1 on CRITICAL risk, 0
otherwise) gates the build, and it writes the Markdown report reviewers read.
These tests lock in the exit codes, the error codes for bad/missing input, and
the report-writing + summary behaviour.
"""

import os

import pytest
import yaml

from changeguard import cli
from changeguard import sample_data

EXAMPLES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "examples")


def _write_yaml(path, data):
    with open(path, "w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle)
    return str(path)


# ---------------------------------------------------------------------------
# Exit codes driven by risk level
# ---------------------------------------------------------------------------
class TestExitCodes:
    def test_low_risk_returns_zero(self, tmp_path, capsys):
        services = _write_yaml(tmp_path / "services.yaml", sample_data.LOW_RISK_SERVICES)
        change = _write_yaml(tmp_path / "change.yaml", sample_data.LOW_RISK_CHANGE)
        output = tmp_path / "report.md"
        code = cli.main(
            ["--services", services, "--change", change, "--output", str(output)]
        )
        assert code == 0

    def test_high_risk_returns_zero(self, tmp_path):
        # HIGH is not CRITICAL, so the build is not failed.
        services = _write_yaml(tmp_path / "services.yaml", sample_data.HIGH_RISK_SERVICES)
        change = _write_yaml(tmp_path / "change.yaml", sample_data.HIGH_RISK_CHANGE)
        output = tmp_path / "report.md"
        code = cli.main(
            ["--services", services, "--change", change, "--output", str(output)]
        )
        assert code == 0

    def test_critical_risk_returns_one(self, tmp_path):
        services = _write_yaml(
            tmp_path / "services.yaml", sample_data.CRITICAL_RISK_SERVICES
        )
        change = _write_yaml(tmp_path / "change.yaml", sample_data.CRITICAL_RISK_CHANGE)
        terraform = tmp_path / "tf.txt"
        terraform.write_text(sample_data.CRITICAL_TERRAFORM_TEXT, encoding="utf-8")
        k8s = tmp_path / "k8s.yaml"
        k8s.write_text(sample_data.RISKY_K8S_TEXT, encoding="utf-8")
        output = tmp_path / "report.md"
        code = cli.main(
            [
                "--services", services,
                "--change", change,
                "--terraform", str(terraform),
                "--k8s", str(k8s),
                "--output", str(output),
            ]
        )
        assert code == 1


# ---------------------------------------------------------------------------
# Report writing and console summary
# ---------------------------------------------------------------------------
class TestOutput:
    def test_writes_report_file(self, tmp_path):
        services = _write_yaml(tmp_path / "services.yaml", sample_data.HIGH_RISK_SERVICES)
        change = _write_yaml(tmp_path / "change.yaml", sample_data.HIGH_RISK_CHANGE)
        output = tmp_path / "report.md"
        cli.main(
            ["--services", services, "--change", change, "--output", str(output)]
        )
        assert output.exists()
        contents = output.read_text(encoding="utf-8")
        assert "# ChangeGuard Risk Report" in contents
        assert "Risk Level: HIGH" in contents

    def test_prints_score_and_level_summary(self, tmp_path, capsys):
        services = _write_yaml(tmp_path / "services.yaml", sample_data.HIGH_RISK_SERVICES)
        change = _write_yaml(tmp_path / "change.yaml", sample_data.HIGH_RISK_CHANGE)
        output = tmp_path / "report.md"
        cli.main(
            ["--services", services, "--change", change, "--output", str(output)]
        )
        out = capsys.readouterr().out
        assert "Service:     checkout-api" in out
        assert "Environment: production" in out
        assert "Risk Score:  80/100" in out
        assert "Risk Level:  HIGH" in out
        assert f"Report written to: {output}" in out

    def test_default_output_path(self, tmp_path, monkeypatch):
        # When --output is omitted, the report is written to report.md in cwd.
        services = _write_yaml(tmp_path / "services.yaml", sample_data.LOW_RISK_SERVICES)
        change = _write_yaml(tmp_path / "change.yaml", sample_data.LOW_RISK_CHANGE)
        monkeypatch.chdir(tmp_path)
        code = cli.main(["--services", services, "--change", change])
        assert code == 0
        assert (tmp_path / "report.md").exists()


# ---------------------------------------------------------------------------
# Error handling: bad and missing input files
# ---------------------------------------------------------------------------
class TestErrorCodes:
    def test_missing_services_file_returns_two(self, tmp_path, capsys):
        change = _write_yaml(tmp_path / "change.yaml", sample_data.LOW_RISK_CHANGE)
        output = tmp_path / "report.md"
        code = cli.main(
            [
                "--services", str(tmp_path / "does-not-exist.yaml"),
                "--change", change,
                "--output", str(output),
            ]
        )
        assert code == 2
        assert "Error loading input files" in capsys.readouterr().err
        assert not output.exists()

    def test_missing_change_file_returns_two(self, tmp_path, capsys):
        services = _write_yaml(tmp_path / "services.yaml", sample_data.LOW_RISK_SERVICES)
        code = cli.main(
            [
                "--services", services,
                "--change", str(tmp_path / "nope.yaml"),
                "--output", str(tmp_path / "report.md"),
            ]
        )
        assert code == 2
        assert "Error loading input files" in capsys.readouterr().err

    def test_malformed_yaml_returns_two(self, tmp_path, capsys):
        services = tmp_path / "services.yaml"
        services.write_text("this: : : not valid yaml\n  - [", encoding="utf-8")
        change = _write_yaml(tmp_path / "change.yaml", sample_data.LOW_RISK_CHANGE)
        code = cli.main(
            ["--services", str(services), "--change", change, "--output", str(tmp_path / "r.md")]
        )
        assert code == 2
        assert "Error loading input files" in capsys.readouterr().err

    def test_unknown_service_returns_two(self, tmp_path, capsys):
        # File loads fine, but assess_risk raises ValueError for an unknown service.
        services = _write_yaml(tmp_path / "services.yaml", sample_data.LOW_RISK_SERVICES)
        change = _write_yaml(
            tmp_path / "change.yaml", {"change": {"service": "ghost-service"}}
        )
        code = cli.main(
            ["--services", services, "--change", change, "--output", str(tmp_path / "r.md")]
        )
        assert code == 2
        assert "Error:" in capsys.readouterr().err

    def test_missing_required_arg_exits(self, capsys):
        # argparse exits with code 2 when a required argument is absent.
        with pytest.raises(SystemExit) as excinfo:
            cli.main(["--services", "only-services.yaml"])
        assert excinfo.value.code == 2


# ---------------------------------------------------------------------------
# The CLI also works against the shipped example files end to end
# ---------------------------------------------------------------------------
def test_cli_with_example_files(tmp_path):
    services = os.path.join(EXAMPLES_DIR, "services-critical-risk.yaml")
    change = os.path.join(EXAMPLES_DIR, "change-critical-risk.yaml")
    terraform = os.path.join(EXAMPLES_DIR, "terraform-critical.txt")
    k8s = os.path.join(EXAMPLES_DIR, "k8s-risk.yaml")
    output = tmp_path / "report.md"
    code = cli.main(
        [
            "--services", services,
            "--change", change,
            "--terraform", terraform,
            "--k8s", k8s,
            "--output", str(output),
        ]
    )
    assert code == 1
    assert output.exists()
    assert "Risk Level: CRITICAL" in output.read_text(encoding="utf-8")
