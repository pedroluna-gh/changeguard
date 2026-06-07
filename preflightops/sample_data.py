"""Built-in example scenarios for PreflightOps.

These power the example buttons in the Streamlit UI and back the YAML/text
files in the ``examples/`` directory.
"""

# ---------------------------------------------------------------------------
# LOW RISK
# Staging deployment, medium-criticality service, all controls present.
# ---------------------------------------------------------------------------
LOW_RISK_SERVICES = {
    "services": [
        {
            "name": "reporting-api",
            "description": "Generates internal usage reports",
            "owner": "data-platform-team",
            "criticality": "medium",
            "tier": "tier-3",
            "environment": "staging",
            "cloud_provider": "aws",
            "runtime": "kubernetes",
            "runbook": "runbooks/reporting-api.md",
            "rollback_required": True,
            "monitoring_required": True,
            "approval_required": False,
            "dependencies": ["postgres"],
            "business_impact": "Internal reports may be delayed",
        }
    ]
}

LOW_RISK_CHANGE = {
    "change": {
        "id": "CHG-100",
        "title": "Update reporting API in staging",
        "service": "reporting-api",
        "environment": "staging",
        "change_type": "deployment",
        "requested_by": "pedro",
        "description": "Deploy new reporting API build to staging for validation",
        "rollback_plan": (
            "Redeploy previous container image reporting-api:1.4.2 via the staging "
            "pipeline if error rate exceeds 2% within the validation window. Owner: "
            "data-platform-team. Estimated rollback time: 5 minutes."
        ),
        "monitoring_plan": {
            "dashboards": ["https://grafana.example.com/d/reporting"],
            "alerts": ["reporting-api-error-rate"],
            "validation_window": "15 minutes",
            "success_criteria": ["error rate below 2%"],
        },
        "validation_plan": [
            "Confirm staging smoke tests pass",
            "Verify a sample report renders correctly",
        ],
    }
}

# ---------------------------------------------------------------------------
# HIGH RISK
# Production deployment, high-criticality service, valid rollback but
# incomplete monitoring and missing validation plan.
# ---------------------------------------------------------------------------
HIGH_RISK_SERVICES = {
    "services": [
        {
            "name": "checkout-api",
            "description": "Handles customer checkout flow",
            "owner": "payments-team",
            "criticality": "high",
            "tier": "tier-1",
            "environment": "production",
            "cloud_provider": "aws",
            "runtime": "kubernetes",
            "runbook": "runbooks/checkout-api.md",
            "rollback_required": True,
            "monitoring_required": True,
            "approval_required": True,
            "dependencies": ["auth-service", "postgres", "redis"],
            "business_impact": "Customers may be unable to complete checkout",
        }
    ]
}

HIGH_RISK_CHANGE = {
    "change": {
        "id": "CHG-200",
        "title": "Update checkout API deployment",
        "service": "checkout-api",
        "environment": "production",
        "change_type": "deployment",
        "requested_by": "pedro",
        "description": "Deploy new checkout API version with payment timeout improvements",
        "rollback_plan": (
            "Roll back to checkout-api:3.1.0 using the production deploy pipeline if "
            "the 5xx rate exceeds 1% in the first 30 minutes. Owner: payments-team. "
            "Estimated rollback time: 10 minutes."
        ),
        "monitoring_plan": {
            "dashboards": ["https://grafana.example.com/d/checkout"],
        },
        "validation_plan": [],
    }
}

# ---------------------------------------------------------------------------
# CRITICAL RISK
# Production critical service, missing rollback/validation/runbook, plus risky
# Terraform (IAM + destroy) and a Kubernetes Deployment without probes.
# ---------------------------------------------------------------------------
CRITICAL_RISK_SERVICES = {
    "services": [
        {
            "name": "payments-core",
            "description": "Authorizes and settles all customer payments",
            "owner": "payments-team",
            "criticality": "critical",
            "tier": "tier-0",
            "environment": "production",
            "cloud_provider": "aws",
            "runtime": "kubernetes",
            "runbook": "",
            "rollback_required": True,
            "monitoring_required": True,
            "approval_required": True,
            "dependencies": ["auth-service", "postgres", "kms"],
            "business_impact": "Customers cannot be charged and revenue stops immediately",
        }
    ]
}

CRITICAL_RISK_CHANGE = {
    "change": {
        "id": "CHG-300",
        "title": "Migrate payments-core to new IAM roles and database",
        "service": "payments-core",
        "environment": "production",
        "change_type": "infrastructure",
        "requested_by": "pedro",
        "description": "Apply Terraform changes for new IAM roles and replace the payments database instance",
        "rollback_plan": "",
        "monitoring_plan": {},
        "validation_plan": [],
    }
}

CRITICAL_TERRAFORM_TEXT = """# terraform plan output (excerpt)

  # aws_iam_policy.payments_admin will be created
  + resource "aws_iam_policy" "payments_admin" {
      + name = "payments-core-admin"
    }

  # aws_iam_role.payments_core will be updated in-place
  ~ resource "aws_iam_role" "payments_core" {
      ~ assume_role_policy = (known after apply)
    }

  # aws_db_instance.payments will be destroyed
  - resource "aws_db_instance" "payments" {
      - identifier = "payments-core-prod"
    }

Plan: 1 to add, 1 to change, 1 to destroy.
"""

RISKY_K8S_TEXT = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: payments-core
spec:
  replicas: 3
  template:
    spec:
      containers:
        - name: payments-core
          image: payments-core:4.0.0
          ports:
            - containerPort: 8080
---
apiVersion: v1
kind: Secret
metadata:
  name: payments-core-db
type: Opaque
data:
  password: c3VwZXJzZWNyZXQ=
"""
