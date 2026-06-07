"""PreflightOps Streamlit application.

Run with:
    streamlit run app.py --server.port 5000
"""

import yaml
import streamlit as st

try:
    import pandas as pd

    HAS_PANDAS = True
except ImportError:  # pragma: no cover - pandas is in requirements
    HAS_PANDAS = False

from preflightops.risk_engine import assess_risk, SOURCE_ORDER
from preflightops.report import generate_markdown_report, generate_json_report
from preflightops import sample_data


# ---------------------------------------------------------------------------
# Default inputs (the checkout-api example from the spec)
# ---------------------------------------------------------------------------
DEFAULT_SERVICES_YAML = """services:
  - name: checkout-api
    description: Handles customer checkout flow
    owner: payments-team
    criticality: high
    tier: tier-1
    environment: production
    cloud_provider: aws
    runtime: kubernetes
    runbook: runbooks/checkout-api.md
    rollback_required: true
    monitoring_required: true
    approval_required: true
    dependencies:
      - auth-service
      - postgres
      - redis
    business_impact: Customers may be unable to complete checkout
"""

DEFAULT_CHANGE_YAML = """change:
  id: CHG-001
  title: Update checkout API deployment
  service: checkout-api
  environment: production
  change_type: deployment
  requested_by: pedro
  description: Deploy new checkout API version with payment timeout improvements
  rollback_plan: ""
  monitoring_plan:
    dashboards:
      - https://grafana.example.com/d/checkout
    alerts:
      - checkout-api-5xx-rate
    validation_window: 30 minutes
    success_criteria:
      - 5xx rate below 1%
      - p95 latency below 500ms
  validation_plan: []
"""


def _yaml_dump(data: dict) -> str:
    return yaml.safe_dump(data, sort_keys=False, default_flow_style=False)


def _load_example(kind: str) -> None:
    """Populate the editor session state from a built-in example scenario."""
    if kind == "low":
        st.session_state.services_input = _yaml_dump(sample_data.LOW_RISK_SERVICES)
        st.session_state.change_input = _yaml_dump(sample_data.LOW_RISK_CHANGE)
        st.session_state.terraform_input = ""
        st.session_state.k8s_input = ""
    elif kind == "high":
        st.session_state.services_input = _yaml_dump(sample_data.HIGH_RISK_SERVICES)
        st.session_state.change_input = _yaml_dump(sample_data.HIGH_RISK_CHANGE)
        st.session_state.terraform_input = ""
        st.session_state.k8s_input = ""
    elif kind == "critical":
        st.session_state.services_input = _yaml_dump(sample_data.CRITICAL_RISK_SERVICES)
        st.session_state.change_input = _yaml_dump(sample_data.CRITICAL_RISK_CHANGE)
        st.session_state.terraform_input = sample_data.CRITICAL_TERRAFORM_TEXT
        st.session_state.k8s_input = sample_data.RISKY_K8S_TEXT
    # Clear any stale result so the UI reflects the freshly loaded example.
    st.session_state.pop("result", None)


def _clear_result() -> None:
    """Drop a previous result whenever an input changes, to avoid drift."""
    st.session_state.pop("result", None)


LEVEL_RENDERERS = {
    "LOW": st.success,
    "MEDIUM": st.warning,
    "HIGH": st.warning,
    "CRITICAL": st.error,
}

LEVEL_COLORS = {
    "LOW": "#1a7f37",
    "MEDIUM": "#bf8700",
    "HIGH": "#d1242f",
    "CRITICAL": "#a40e26",
}

# Severity colors used for contribution bars and per-finding chips.
SEVERITY_COLORS = {
    "low": "#1a7f37",
    "medium": "#bf8700",
    "high": "#d1242f",
    "critical": "#a40e26",
}

# Order severities from most to least severe for sorting within a group.
SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _render_badge(level: str) -> None:
    color = LEVEL_COLORS.get(level, "#57606a")
    st.markdown(
        f"""
        <div style="display:inline-block;padding:6px 18px;border-radius:6px;
        background-color:{color};color:white;font-weight:700;font-size:18px;
        letter-spacing:1px;">{level}</div>
        """,
        unsafe_allow_html=True,
    )


def _group_by_source(triggered: list) -> dict:
    """Group triggered findings by their ``source`` category, preserving order."""
    groups = {}
    for rule in triggered:
        source = rule.get("source", "Other")
        groups.setdefault(source, []).append(rule)

    # Order known sources first (per SOURCE_ORDER), then any extras.
    ordered = {}
    for source in SOURCE_ORDER:
        if source in groups:
            ordered[source] = groups[source]
    for source, rules in groups.items():
        if source not in ordered:
            ordered[source] = rules
    return ordered


def _dominant_severity(rules: list) -> str:
    """Return the most severe severity present in a list of findings."""
    severities = [(r.get("severity") or "medium").lower() for r in rules]
    severities.sort(key=lambda s: SEVERITY_RANK.get(s, 99))
    return severities[0] if severities else "medium"


def _severity_chip(severity: str) -> str:
    sev = (severity or "medium").lower()
    color = SEVERITY_COLORS.get(sev, "#57606a")
    return (
        f'<span style="display:inline-block;padding:1px 8px;border-radius:10px;'
        f'background-color:{color};color:white;font-size:11px;font-weight:700;'
        f'text-transform:uppercase;letter-spacing:0.5px;">{sev}</span>'
    )


def _render_score_breakdown(triggered: list) -> None:
    """Show how the score builds up: each source group's share of the total."""
    st.subheader("Score Breakdown")

    if not triggered:
        st.info("No findings contributed to the score.")
        return

    groups = _group_by_source(triggered)
    total = sum(rule.get("score", 0) for rule in triggered) or 1

    st.caption(
        "How the score was reached — each category's contribution to the total "
        "risk points (bar color reflects the most severe finding in the group)."
    )

    for source, rules in groups.items():
        group_score = sum(rule.get("score", 0) for rule in rules)
        share = group_score / total * 100
        color = SEVERITY_COLORS.get(_dominant_severity(rules), "#57606a")

        label_l, label_r = st.columns([3, 1])
        with label_l:
            st.markdown(f"**{source}** &nbsp; <span style='color:#57606a;'>"
                        f"({len(rules)} finding{'s' if len(rules) != 1 else ''})</span>",
                        unsafe_allow_html=True)
        with label_r:
            st.markdown(
                f"<div style='text-align:right;font-weight:700;'>{group_score} pts &nbsp;"
                f"<span style='color:#57606a;font-weight:400;'>"
                f"({share:.0f}%)</span></div>",
                unsafe_allow_html=True,
            )

        st.markdown(
            f"""
            <div style="background-color:#eaecef;border-radius:6px;height:14px;
            width:100%;margin-bottom:14px;overflow:hidden;">
              <div style="background-color:{color};height:100%;
              width:{share:.1f}%;border-radius:6px;"></div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_grouped_rules(triggered: list) -> None:
    """Render triggered findings grouped by source, with severity chips."""
    groups = _group_by_source(triggered)

    for source, rules in groups.items():
        group_score = sum(rule.get("score", 0) for rule in rules)
        st.markdown(f"#### {source} &nbsp; "
                    f"<span style='color:#57606a;font-size:14px;'>+{group_score} pts</span>",
                    unsafe_allow_html=True)

        ordered = sorted(
            rules, key=lambda r: SEVERITY_RANK.get((r.get("severity") or "").lower(), 99)
        )
        for rule in ordered:
            st.markdown(
                f"<div style='margin-bottom:6px;'>"
                f"{_severity_chip(rule.get('severity'))} &nbsp;"
                f"<strong>+{rule.get('score', 0)}</strong> &nbsp;"
                f"<code>{rule.get('id', '')}</code> &nbsp;— "
                f"{rule.get('description', '')}</div>",
                unsafe_allow_html=True,
            )
        st.markdown("<div style='margin-bottom:10px;'></div>", unsafe_allow_html=True)


def main() -> None:
    st.set_page_config(page_title="PreflightOps", page_icon="🛡️", layout="wide")

    # Initialize editor state.
    st.session_state.setdefault("services_input", DEFAULT_SERVICES_YAML)
    st.session_state.setdefault("change_input", DEFAULT_CHANGE_YAML)
    st.session_state.setdefault("terraform_input", "")
    st.session_state.setdefault("k8s_input", "")

    # ----- Header -----
    st.title("PreflightOps")
    st.subheader("Preflight checks for risky production changes")
    st.caption("Before production changes take off, check the operational risk.")

    st.write(
        "PreflightOps reviews service ownership, production criticality, rollback "
        "readiness, monitoring plans, validation steps, Terraform risk signals, and "
        "Kubernetes deployment risk before a change goes live."
    )

    # ----- Why this matters -----
    with st.expander("Why this matters", expanded=True):
        st.markdown(
            "Most production incidents are triggered by changes — deployments, "
            "config updates, and infrastructure edits. Teams often have CI/CD, "
            "Terraform, Kubernetes, and dashboards, yet still judge change risk "
            "by gut feel in a rushed review.\n\n"
            "**PreflightOps makes that judgement explicit.** It turns your service "
            "catalog and change request into a clear risk score, a risk level, and "
            "a list of the exact gaps to fix — *before* the change ships. The result "
            "is fewer surprise incidents, faster and more consistent change reviews, "
            "and a shared, auditable record of why a change was considered safe."
        )

    # ----- Example selector -----
    st.markdown("### Start here: load an example scenario")
    st.caption(
        "New to PreflightOps? Load a ready-made scenario to see how scoring works, "
        "then edit the inputs below to match your own change."
    )
    ex_low, ex_high, ex_critical = st.columns(3)
    ex_low.button(
        "Low Risk Example",
        use_container_width=True,
        on_click=_load_example,
        args=("low",),
    )
    ex_high.button(
        "High Risk Example",
        use_container_width=True,
        on_click=_load_example,
        args=("high",),
    )
    ex_critical.button(
        "Critical Risk Example",
        use_container_width=True,
        on_click=_load_example,
        args=("critical",),
    )

    st.divider()

    # ----- Two-column input layout -----
    left, right = st.columns(2)

    with left:
        st.markdown("### 1. Service Catalog")
        st.caption("Describe the service being changed and its operational controls.")
        st.text_area(
            "Service Catalog (YAML)",
            key="services_input",
            height=320,
            on_change=_clear_result,
            help=(
                "YAML with a top-level `services:` list. Each service should include "
                "fields like name, owner, criticality, environment, runbook, and "
                "business_impact. The change request below references one of these "
                "services by name."
            ),
        )
        st.markdown("### 2. Change Request")
        st.caption("Describe the change you intend to deploy.")
        st.text_area(
            "Change Request (YAML)",
            key="change_input",
            height=320,
            on_change=_clear_result,
            help=(
                "YAML with a top-level `change:` object. Include the target `service` "
                "(must match a service above), `environment`, `change_type`, plus the "
                "rollback_plan, monitoring_plan, and validation_plan that PreflightOps "
                "checks for completeness."
            ),
        )

    with right:
        st.markdown("### 3. Terraform Plan / Diff (optional)")
        st.caption("Paste plan output to catch risky infrastructure changes.")
        st.text_area(
            "Paste Terraform plan or diff text",
            key="terraform_input",
            height=320,
            placeholder="Paste `terraform plan` output or a diff here...",
            on_change=_clear_result,
            help=(
                "Free-form text from `terraform plan` or a diff. PreflightOps scans it "
                "for risky signals such as IAM changes, security groups, database "
                "instances, and destroy/delete actions."
            ),
        )
        st.markdown("### 4. Kubernetes Manifest (optional)")
        st.caption("Paste manifests to catch risky deployment changes.")
        st.text_area(
            "Paste Kubernetes manifest YAML",
            key="k8s_input",
            height=320,
            placeholder="Paste Kubernetes manifest YAML here...",
            on_change=_clear_result,
            help=(
                "Paste one or more Kubernetes manifests. PreflightOps scans for risky "
                "kinds (Ingress, Secret, NetworkPolicy, StatefulSet), LoadBalancer "
                "exposure, replicas set to zero, and Deployments missing readiness or "
                "liveness probes."
            ),
        )

    st.divider()

    if st.button("Run Risk Assessment", type="primary", use_container_width=True):
        _run_assessment()

    # ----- Results -----
    if "result" in st.session_state:
        _render_results(st.session_state["result"])

    # ----- Footer -----
    st.divider()
    st.markdown(
        "<div style='text-align:center;color:#57606a;font-size:14px;padding:8px 0;'>"
        "Built for SRE, DevOps, Platform Engineering and Cloud Operations teams."
        "</div>",
        unsafe_allow_html=True,
    )


def _run_assessment() -> None:
    # Parse the service catalog.
    try:
        services = yaml.safe_load(st.session_state.services_input)
    except yaml.YAMLError as exc:
        st.error(f"Service Catalog YAML is invalid: {exc}")
        st.session_state.pop("result", None)
        return

    # Parse the change request.
    try:
        change = yaml.safe_load(st.session_state.change_input)
    except yaml.YAMLError as exc:
        st.error(f"Change Request YAML is invalid: {exc}")
        st.session_state.pop("result", None)
        return

    # Non-fatal warnings for missing optional fields.
    _warn_missing_fields(change)

    try:
        result = assess_risk(
            services,
            change,
            st.session_state.terraform_input,
            st.session_state.k8s_input,
        )
    except ValueError as exc:
        st.error(str(exc))
        st.session_state.pop("result", None)
        return

    st.session_state["result"] = result


def _warn_missing_fields(change_doc) -> None:
    if not isinstance(change_doc, dict):
        return
    change = change_doc.get("change")
    if not isinstance(change, dict):
        return
    recommended = ["id", "title", "change_type", "requested_by", "description"]
    missing = [field for field in recommended if not change.get(field)]
    if missing:
        st.warning(
            "Change request is missing recommended fields: "
            + ", ".join(missing)
            + ". Proceeding with the assessment anyway."
        )


def _render_results(result: dict) -> None:
    st.divider()
    st.header("Risk Assessment Results")

    col_score, col_level = st.columns([1, 2])
    with col_score:
        st.metric("Risk Score", f"{result['risk_score']}/100")
    with col_level:
        st.markdown("**Risk Level**")
        _render_badge(result["risk_level"])

    # Recommendation, rendered with severity color.
    renderer = LEVEL_RENDERERS.get(result["risk_level"], st.info)
    renderer(result["recommendation"])

    triggered = result["triggered_rules"]

    # Score breakdown grouped by source.
    _render_score_breakdown(triggered)

    # Triggered rules, grouped by source.
    st.subheader("Triggered Rules")
    if triggered:
        _render_grouped_rules(triggered)
    else:
        st.info("No risk rules were triggered.")

    # Missing controls.
    st.subheader("Missing Controls")
    if result["missing_controls"]:
        for control in result["missing_controls"]:
            st.markdown(f"- {control}")
    else:
        st.success("No missing controls detected.")

    # Business impact.
    st.subheader("Business Impact")
    st.write(result["business_impact"] or "Not specified")

    # Markdown report preview + downloads.
    st.subheader("Report")
    markdown_report = generate_markdown_report(result)
    json_report = generate_json_report(result)

    with st.expander("Markdown report preview", expanded=False):
        st.markdown(markdown_report)
        st.code(markdown_report, language="markdown")

    dl_md, dl_json = st.columns(2)
    dl_md.download_button(
        "Download Markdown Report",
        data=markdown_report,
        file_name="preflightops-report.md",
        mime="text/markdown",
        use_container_width=True,
    )
    dl_json.download_button(
        "Download JSON Report",
        data=json_report,
        file_name="preflightops-report.json",
        mime="application/json",
        use_container_width=True,
    )


if __name__ == "__main__":
    main()
