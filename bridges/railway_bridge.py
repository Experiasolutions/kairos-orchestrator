# KAIROS SKY — Railway Bridge (OpenClaw Skills)
# 15 Skills | 4 Tiers | Full Environment Control
# O "Criador de Tentáculos" — Provisiona infraestrutura autônoma via Railway API
#
# Railway GraphQL API: https://docs.railway.com/reference/public-api
# Auth: Bearer Token via RAILWAY_API_TOKEN
#
import json
import logging
import os
from datetime import datetime, timezone
from typing import Union

logger = logging.getLogger("kairos.railway_bridge")

# ─── Configuração ──────────────────────────────────────────

RAILWAY_API_URL = "https://backboard.railway.com/graphql/v2"
RAILWAY_API_TOKEN = os.environ.get("RAILWAY_API_TOKEN", "")
RAILWAY_PROJECT_ID = os.environ.get("RAILWAY_PROJECT_ID", "")

_http_client_available = False

try:
    import httpx
    _http_client_available = True
except ImportError:
    logger.warning("httpx não instalado. Railway Bridge limitado. Run: pip install httpx")


# ─── HTTP Layer ────────────────────────────────────────────

def _gql(query: str, variables: dict[str, object] | None = None) -> dict[str, object]:
    """Executa uma query GraphQL na API do Railway."""
    if not _http_client_available:
        return {"error": "httpx não instalado. pip install httpx"}
    if not RAILWAY_API_TOKEN:
        return {"error": "RAILWAY_API_TOKEN não configurado"}

    headers = {
        "Authorization": f"Bearer {RAILWAY_API_TOKEN}",
        "Content-Type": "application/json",
    }
    payload: dict[str, object] = {"query": query}
    if variables:
        payload["variables"] = variables

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(RAILWAY_API_URL, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            if "errors" in data:
                logger.error("Railway GQL errors: %s", data["errors"])
                return {"error": str(data["errors"]), "data": data.get("data")}
            return data.get("data", {})
    except Exception as e:
        logger.error("Railway API call failed: %s", e)
        return {"error": str(e)}


# ═══════════════════════════════════════════════════════════
# TIER 1: DEPLOYMENT & SERVICE MANAGEMENT
# ═══════════════════════════════════════════════════════════

def deploy_service(
    name: str,
    source: str,
    service_type: str = "docker_image",
    variables: dict[str, str] | None = None,
    start_command: str = "",
    build_command: str = "",
    port: int = 3000,
    healthcheck_path: str = "/health",
) -> dict[str, object]:
    """
    Skill 1: Deploy a new service to Railway.
    service_type: 'docker_image' | 'github_repo' | 'template'
    """
    logger.info("🚀 Railway: deploying '%s' (%s) from %s", name, service_type, source[:60])

    project_id = RAILWAY_PROJECT_ID
    if not project_id:
        return {"status": "error", "error": "RAILWAY_PROJECT_ID não configurado"}

    # Step 1: Create the service
    create_q = """
    mutation($input: ServiceCreateInput!) {
      serviceCreate(input: $input) { id name }
    }
    """
    create_vars: dict[str, object] = {
        "input": {
            "name": name,
            "projectId": project_id,
        }
    }

    if service_type == "github_repo":
        create_vars["input"]["source"] = {"repo": source}

    result = _gql(create_q, create_vars)
    if "error" in result:
        return {"status": "error", "error": result["error"]}

    service_data = result.get("serviceCreate", {})
    service_id = service_data.get("id", "")

    # Step 2: Set environment variables
    if variables and service_id:
        _set_variables(service_id, variables)

    # Step 3: For Docker images, set the source
    if service_type == "docker_image" and service_id:
        img_q = """
        mutation($id: String!, $input: ServiceUpdateInput!) {
          serviceUpdate(id: $id, input: $input) { id }
        }
        """
        _gql(img_q, {
            "id": service_id,
            "input": {"source": {"image": source}},
        })

    return {
        "status": "deployed",
        "service_id": service_id,
        "name": name,
        "service_type": service_type,
        "source": source,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    }


def update_service_config(
    service_id: str,
    variables: dict[str, str] | None = None,
    start_command: str = "",
    build_command: str = "",
    healthcheck_path: str = "",
) -> dict[str, object]:
    """Skill 2: Update service configuration in real-time (no rebuild)."""
    logger.info("⚙️ Railway: updating config for service %s", service_id)

    updates: dict[str, object] = {}
    if start_command:
        updates["startCommand"] = start_command
    if build_command:
        updates["buildCommand"] = build_command
    if healthcheck_path:
        updates["healthcheckPath"] = healthcheck_path

    if updates:
        q = """
        mutation($id: String!, $input: ServiceUpdateInput!) {
          serviceUpdate(id: $id, input: $input) { id }
        }
        """
        _gql(q, {"id": service_id, "input": updates})

    if variables:
        _set_variables(service_id, variables)

    return {"status": "updated", "service_id": service_id, "updates": updates}


def restart_service(service_id: str) -> dict[str, object]:
    """Skill 3: Restart running service (no rebuild)."""
    logger.info("🔄 Railway: restarting service %s", service_id)
    q = """
    mutation($input: ServiceInstanceRedeployInput!) {
      serviceInstanceRedeploy(input: $input)
    }
    """
    result = _gql(q, {"input": {"serviceId": service_id}})
    return {"status": "restarted", "service_id": service_id, "result": result}


def remove_service(service_id: str, force: bool = False) -> dict[str, object]:
    """Skill 4: Remove service from environment."""
    logger.info("🗑️ Railway: removing service %s (force=%s)", service_id, force)
    q = """
    mutation($id: String!) {
      serviceDelete(id: $id)
    }
    """
    result = _gql(q, {"id": service_id})
    return {"status": "removed", "service_id": service_id, "result": result}


# ═══════════════════════════════════════════════════════════
# TIER 2: OBSERVABILITY & DIAGNOSTICS
# ═══════════════════════════════════════════════════════════

def get_service_status(service_id: str, include_deployments: bool = True) -> dict[str, object]:
    """Skill 5: Get real-time service status and deployment history."""
    q = """
    query($id: String!) {
      service(id: $id) {
        id name
        deployments(first: 5) {
          edges { node { id status createdAt } }
        }
      }
    }
    """
    data = _gql(q, {"id": service_id})
    service = data.get("service", {})
    deployments = []
    for edge in service.get("deployments", {}).get("edges", []):
        deployments.append(edge.get("node", {}))

    return {
        "service_id": service_id,
        "name": service.get("name", "?"),
        "deployments": deployments if include_deployments else [],
        "latest_status": deployments[0].get("status", "unknown") if deployments else "no_deployments",
    }


def get_logs(
    service_id: str,
    log_type: str = "runtime",
    limit: int = 50,
    deployment_id: str = "",
) -> dict[str, object]:
    """Skill 6: Search and retrieve service logs (build, runtime, HTTP)."""
    logger.info("📄 Railway: fetching %s logs for %s", log_type, service_id)

    # Railway doesn't expose logs via GraphQL natively for all types.
    # We use the deployment logs endpoint.
    if not deployment_id:
        status = get_service_status(service_id, include_deployments=True)
        deps = status.get("deployments", [])
        if deps:
            deployment_id = deps[0].get("id", "")

    if not deployment_id:
        return {"status": "error", "error": "No deployment found to fetch logs from"}

    q = """
    query($deploymentId: String!, $limit: Int) {
      deploymentLogs(deploymentId: $deploymentId, limit: $limit) {
        message timestamp severity
      }
    }
    """
    data = _gql(q, {"deploymentId": deployment_id, "limit": limit})
    logs = data.get("deploymentLogs", [])

    return {
        "service_id": service_id,
        "deployment_id": deployment_id,
        "log_type": log_type,
        "count": len(logs) if isinstance(logs, list) else 0,
        "logs": logs,
    }


def get_metrics(
    service_id: str,
    measurements: list[str] | None = None,
) -> dict[str, object]:
    """Skill 7: Retrieve performance metrics (CPU, memory, network, disk)."""
    if measurements is None:
        measurements = ["CPU_USAGE", "MEMORY_USAGE_GB"]

    q = """
    query($serviceId: String!, $measurements: [MetricMeasurement!]!) {
      metrics(serviceId: $serviceId, measurements: $measurements) {
        measurement values { date value }
      }
    }
    """
    data = _gql(q, {"serviceId": service_id, "measurements": measurements})
    return {
        "service_id": service_id,
        "metrics": data.get("metrics", []),
    }


def get_http_metrics(
    service_id: str,
    metric_type: str = "request_count",
) -> dict[str, object]:
    """Skill 8: Get HTTP metrics (requests, error rate, response time)."""
    # Railway's observability is done via their dashboard;
    # use generic metrics endpoint for HTTP-related data.
    return get_metrics(service_id, measurements=["HTTP_REQUEST_COUNT", "HTTP_ERROR_RATE"])


def diagnose_deployment(deployment_id: str) -> dict[str, object]:
    """Skill 9: Root cause analysis of failed deployments."""
    logger.info("🩺 Railway: diagnosing deployment %s", deployment_id)

    q = """
    query($id: String!) {
      deployment(id: $id) {
        id status
        meta { repo branch commitMessage }
      }
    }
    """
    data = _gql(q, {"id": deployment_id})
    deployment = data.get("deployment", {})
    status = deployment.get("status", "unknown")
    meta = deployment.get("meta", {})

    # Fetch logs for diagnosis
    log_q = """
    query($deploymentId: String!) {
      deploymentLogs(deploymentId: $deploymentId, limit: 20) {
        message timestamp severity
      }
    }
    """
    log_data = _gql(log_q, {"deploymentId": deployment_id})
    logs = log_data.get("deploymentLogs", [])

    error_logs = []
    if isinstance(logs, list):
        error_logs = [
            log for log in logs
            if isinstance(log, dict) and log.get("severity") in ("ERROR", "FATAL", "error")
        ]

    return {
        "deployment_id": deployment_id,
        "status": status,
        "context": meta,
        "error_logs": error_logs,
        "total_log_lines": len(logs) if isinstance(logs, list) else 0,
        "diagnosis": "FAILED" if status in ("FAILED", "CRASHED") else "OK",
    }


# ═══════════════════════════════════════════════════════════
# TIER 3: STORAGE & PERSISTENCE
# ═══════════════════════════════════════════════════════════

def manage_volumes(
    action: str,
    name: str = "",
    size_mb: int = 1000,
    mount_path: str = "/data",
    service_id: str = "",
    volume_id: str = "",
) -> dict[str, object]:
    """Skill 10: Create, update, or remove persistent volumes."""
    logger.info("💾 Railway: %s volume '%s'", action, name or volume_id)

    if action == "create":
        q = """
        mutation($input: VolumeCreateInput!) {
          volumeCreate(input: $input) { id name }
        }
        """
        result = _gql(q, {"input": {
            "projectId": RAILWAY_PROJECT_ID,
            "serviceId": service_id,
            "mountPath": mount_path,
        }})
        return {"status": "created", "volume": result.get("volumeCreate", {})}
    elif action == "remove":
        q = """
        mutation($id: String!) {
          volumeDelete(volumeId: $id)
        }
        """
        result = _gql(q, {"id": volume_id})
        return {"status": "removed", "volume_id": volume_id}
    else:
        return {"status": "error", "error": f"Ação desconhecida: {action}"}


def manage_buckets(
    action: str,
    name: str = "",
    bucket_id: str = "",
) -> dict[str, object]:
    """Skill 11: Create or remove S3-compatible object storage."""
    logger.info("🪣 Railway: %s bucket '%s'", action, name or bucket_id)
    # Railway object storage uses their Volumes or external S3
    # This is a placeholder for when Railway adds native bucket support
    return {
        "status": "planned",
        "note": "Railway doesn't have native S3 buckets yet. Use Volumes or external S3.",
        "action": action,
    }


def manage_variables(
    service_id: str,
    action: str = "set",
    variables: Union[dict[str, str], list[str], None] = None,
) -> dict[str, object]:
    """Skill 12: Set, update, or remove environment variables."""
    logger.info("🔑 Railway: %s variables for %s", action, service_id)

    if action == "set" and isinstance(variables, dict):
        return _set_variables(service_id, variables)
    elif action == "remove" and isinstance(variables, list):
        # Railway API: set variable to empty string to effectively remove
        empties = {k: "" for k in variables}
        return _set_variables(service_id, empties)
    else:
        return {"status": "error", "error": "Provide dict for 'set' or list for 'remove'"}


def _set_variables(service_id: str, variables: dict[str, str]) -> dict[str, object]:
    """Helper: set env vars on a Railway service."""
    q = """
    mutation($input: VariableCollectionUpsertInput!) {
      variableCollectionUpsert(input: $input)
    }
    """
    result = _gql(q, {"input": {
        "serviceId": service_id,
        "projectId": RAILWAY_PROJECT_ID,
        "variables": variables,
    }})
    return {"status": "set", "count": len(variables), "result": result}


# ═══════════════════════════════════════════════════════════
# TIER 4: ORCHESTRATION & DISCOVERY
# ═══════════════════════════════════════════════════════════

def search_environment(
    pattern: str = "*",
    resource_types: list[str] | None = None,
) -> dict[str, object]:
    """Skill 13: Find services, volumes, buckets by pattern."""
    logger.info("🔍 Railway: searching environment for '%s'", pattern)

    q = """
    query($projectId: String!) {
      project(id: $projectId) {
        services { edges { node { id name } } }
        volumes { edges { node { id name } } }
      }
    }
    """
    data = _gql(q, {"projectId": RAILWAY_PROJECT_ID})
    project = data.get("project", {})

    services = [
        edge.get("node", {})
        for edge in project.get("services", {}).get("edges", [])
    ]
    volumes = [
        edge.get("node", {})
        for edge in project.get("volumes", {}).get("edges", [])
    ]

    # Filter by pattern
    import fnmatch
    if pattern != "*":
        services = [s for s in services if fnmatch.fnmatch(s.get("name", ""), pattern)]
        volumes = [v for v in volumes if fnmatch.fnmatch(v.get("name", ""), pattern)]

    return {
        "pattern": pattern,
        "services": services,
        "volumes": volumes,
        "total": len(services) + len(volumes),
    }


def deploy_template(
    template_code: str,
    variables: dict[str, str] | None = None,
) -> dict[str, object]:
    """Skill 14: Deploy pre-built Railway templates (postgres, redis, n8n, etc)."""
    logger.info("📦 Railway: deploying template '%s'", template_code)

    q = """
    mutation($input: TemplateDeployInput!) {
      templateDeploy(input: $input) {
        projectId
        workflowId
      }
    }
    """
    input_data: dict[str, object] = {
        "projectId": RAILWAY_PROJECT_ID,
        "templateCode": template_code,
    }
    if variables:
        services_config: dict[str, object] = {}
        for key, val in variables.items():
            services_config[key] = val
        input_data["variables"] = services_config

    result = _gql(q, {"input": input_data})
    return {
        "status": "deploying",
        "template": template_code,
        "result": result,
    }


def create_reference_variable(
    source_service_id: str,
    target_service_id: str,
    variable_name: str,
    reference_expression: str,
) -> dict[str, object]:
    """
    Skill 15: Connect services via reference variables.
    Example: reference_expression = '${{Postgres.DATABASE_URL}}'
    """
    logger.info(
        "🔗 Railway: linking %s → %s via %s",
        source_service_id, target_service_id, variable_name,
    )
    return _set_variables(
        target_service_id,
        {variable_name: reference_expression},
    )


# ═══════════════════════════════════════════════════════════
# EXECUTION PATTERNS (High-Level Orchestration)
# ═══════════════════════════════════════════════════════════

def pattern_health_check() -> dict[str, object]:
    """Execution Pattern: Full environment health check."""
    logger.info("🏥 Railway: running full health check")
    env = search_environment("*")
    results = []
    for svc in env.get("services", []):
        svc_id = svc.get("id", "")
        if svc_id:
            status = get_service_status(svc_id)
            metrics = get_metrics(svc_id)
            results.append({
                "name": svc.get("name"),
                "status": status.get("latest_status"),
                "metrics": metrics.get("metrics"),
            })
    return {
        "pattern": "health_check",
        "total_services": len(env.get("services", [])),
        "results": results,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    }


def pattern_auto_heal(service_id: str) -> dict[str, object]:
    """Execution Pattern: Diagnose and attempt to fix a failing service."""
    logger.info("🩹 Railway: auto-healing service %s", service_id)

    status = get_service_status(service_id)
    latest = status.get("latest_status", "")

    if latest not in ("FAILED", "CRASHED"):
        return {"status": "healthy", "message": "Service is running fine."}

    deps = status.get("deployments", [])
    if not deps:
        return {"status": "error", "error": "No deployments to diagnose"}

    diagnosis = diagnose_deployment(deps[0].get("id", ""))

    # Attempt restart
    restart_result = restart_service(service_id)

    return {
        "pattern": "auto_heal",
        "diagnosis": diagnosis,
        "action_taken": "restart",
        "restart_result": restart_result,
    }


# ═══════════════════════════════════════════════════════════
# STATUS & REGISTRY
# ═══════════════════════════════════════════════════════════

RAILWAY_SKILLS_CATALOG = {
    "tier_1_deployment": [
        "deploy_service", "update_service_config",
        "restart_service", "remove_service",
    ],
    "tier_2_observability": [
        "get_service_status", "get_logs", "get_metrics",
        "get_http_metrics", "diagnose_deployment",
    ],
    "tier_3_storage": [
        "manage_volumes", "manage_buckets", "manage_variables",
    ],
    "tier_4_orchestration": [
        "search_environment", "deploy_template",
        "create_reference_variable",
    ],
    "execution_patterns": [
        "pattern_health_check", "pattern_auto_heal",
    ],
}


def get_status() -> dict[str, object]:
    """Retorna status completo do Railway Bridge."""
    return {
        "available": bool(RAILWAY_API_TOKEN),
        "api_token_configured": bool(RAILWAY_API_TOKEN),
        "project_id_configured": bool(RAILWAY_PROJECT_ID),
        "http_client": _http_client_available,
        "total_skills": 15,
        "total_patterns": 2,
        "tiers": list(RAILWAY_SKILLS_CATALOG.keys()),
        "install_command": "pip install httpx",
    }
