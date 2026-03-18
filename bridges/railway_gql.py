# KAIROS SKY — Railway API Bridge (GQL Client)
# Gerado pelo agente Railway + adaptado para o KAIROS
# Usa gql (GraphQL client proper) ao invés de httpx raw
# Deploy: Railway (Docker) | Port 3002
#
# pip install gql[requests] gql[aiohttp] pydantic python-dotenv httpx

from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
import os
from dotenv import load_dotenv
from typing import Optional
import json
from datetime import datetime
import logging

load_dotenv()
logger = logging.getLogger("kairos.railway_gql")


class RailwayAPIClient:
    """GraphQL client for Railway API — O Cérebro do Polvo."""

    def __init__(self, token: str, token_type: str = "account"):
        self.token = token
        self.token_type = token_type
        self.endpoint = "https://backboard.railway.app/graphql/v2"

        if token_type == "project":
            self.headers = {
                "Project-Access-Token": token,
                "Content-Type": "application/json",
            }
        else:
            self.headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }

        self.transport = RequestsHTTPTransport(
            url=self.endpoint,
            headers=self.headers,
            verify=True,
            retries=3,
        )
        self.client = Client(transport=self.transport, execute_timeout=30)

    # ════════════════════════════════════════════════════════
    # PROJECT QUERIES
    # ════════════════════════════════════════════════════════

    def get_project(self, project_id: str) -> dict[str, object]:
        query = gql("""
            query GetProject($id: String!) {
                project(id: $id) { id name description createdAt updatedAt }
            }
        """)
        result = self.client.execute(query, variable_values={"id": project_id})
        return result.get("project", {})

    def list_projects(self) -> list[dict[str, object]]:
        query = gql("""
            query ListProjects {
                projects(first: 100) {
                    edges { node { id name description createdAt } }
                }
            }
        """)
        result = self.client.execute(query)
        return [edge["node"] for edge in result.get("projects", {}).get("edges", [])]

    # ════════════════════════════════════════════════════════
    # ENVIRONMENT QUERIES
    # ════════════════════════════════════════════════════════

    def list_environments(self, project_id: str) -> list[dict[str, object]]:
        query = gql("""
            query ListEnvironments($projectId: String!) {
                environments(projectId: $projectId, first: 100) {
                    edges { node { id name createdAt } }
                }
            }
        """)
        result = self.client.execute(query, variable_values={"projectId": project_id})
        return [edge["node"] for edge in result.get("environments", {}).get("edges", [])]

    # ════════════════════════════════════════════════════════
    # SERVICE QUERIES
    # ════════════════════════════════════════════════════════

    def get_service(self, service_id: str) -> dict[str, object]:
        query = gql("""
            query GetService($id: String!) {
                service(id: $id) {
                    id name createdAt updatedAt
                    deployments(first: 10) {
                        edges { node { id status createdAt } }
                    }
                }
            }
        """)
        result = self.client.execute(query, variable_values={"id": service_id})
        return result.get("service", {})

    def list_services(self, project_id: str, env_id: str) -> list[dict[str, object]]:
        query = gql("""
            query ListServices($projectId: String!, $envId: String!) {
                services(projectId: $projectId, environmentId: $envId, first: 100) {
                    edges { node { id name createdAt } }
                }
            }
        """)
        result = self.client.execute(
            query, variable_values={"projectId": project_id, "envId": env_id}
        )
        return [edge["node"] for edge in result.get("services", {}).get("edges", [])]

    # ════════════════════════════════════════════════════════
    # DEPLOYMENT QUERIES
    # ════════════════════════════════════════════════════════

    def get_deployment(self, deployment_id: str) -> dict[str, object]:
        query = gql("""
            query GetDeployment($id: String!) {
                deployment(id: $id) {
                    id status createdAt updatedAt
                    service { id name }
                }
            }
        """)
        result = self.client.execute(query, variable_values={"id": deployment_id})
        return result.get("deployment", {})

    def list_deployments(self, service_id: str, limit: int = 50) -> list[dict[str, object]]:
        query = gql("""
            query ListDeployments($serviceId: String!, $first: Int!) {
                deployments(serviceId: $serviceId, first: $first) {
                    edges { node { id status createdAt updatedAt } }
                }
            }
        """)
        result = self.client.execute(
            query, variable_values={"serviceId": service_id, "first": limit}
        )
        return [edge["node"] for edge in result.get("deployments", {}).get("edges", [])]

    # ════════════════════════════════════════════════════════
    # VARIABLE QUERIES
    # ════════════════════════════════════════════════════════

    def get_variables(self, service_id: str) -> dict[str, str]:
        query = gql("""
            query GetVariables($serviceId: String!) {
                variables(serviceId: $serviceId, first: 100) {
                    edges { node { id name value } }
                }
            }
        """)
        result = self.client.execute(query, variable_values={"serviceId": service_id})
        variables: dict[str, str] = {}
        for edge in result.get("variables", {}).get("edges", []):
            node = edge["node"]
            variables[str(node["name"])] = str(node["value"])
        return variables

    # ════════════════════════════════════════════════════════
    # VOLUME QUERIES
    # ════════════════════════════════════════════════════════

    def list_volumes(self, project_id: str) -> list[dict[str, object]]:
        query = gql("""
            query ListVolumes($projectId: String!) {
                volumes(projectId: $projectId, first: 100) {
                    edges { node { id name size createdAt } }
                }
            }
        """)
        result = self.client.execute(query, variable_values={"projectId": project_id})
        return [edge["node"] for edge in result.get("volumes", {}).get("edges", [])]

    # ════════════════════════════════════════════════════════
    # MUTATIONS: SERVICES
    # ════════════════════════════════════════════════════════

    def create_service(
        self, project_id: str, env_id: str, name: str, source: dict[str, object]
    ) -> dict[str, object]:
        mutation = gql("""
            mutation CreateService($projectId: String!, $envId: String!, $name: String!, $source: ServiceSourceInput!) {
                serviceCreate(input: {projectId: $projectId, environmentId: $envId, name: $name, source: $source}) {
                    service { id name createdAt }
                }
            }
        """)
        result = self.client.execute(mutation, variable_values={
            "projectId": project_id, "envId": env_id, "name": name, "source": source,
        })
        return result.get("serviceCreate", {}).get("service", {})

    def update_service_config(self, service_id: str, config: dict[str, object]) -> dict[str, object]:
        mutation = gql("""
            mutation UpdateServiceConfig($serviceId: String!, $config: ServiceConfigInput!) {
                serviceUpdate(input: {id: $serviceId, config: $config}) {
                    service { id name updatedAt }
                }
            }
        """)
        result = self.client.execute(mutation, variable_values={"serviceId": service_id, "config": config})
        return result.get("serviceUpdate", {}).get("service", {})

    def delete_service(self, service_id: str) -> bool:
        mutation = gql("""
            mutation DeleteService($id: String!) {
                serviceDelete(input: {id: $id}) { success }
            }
        """)
        result = self.client.execute(mutation, variable_values={"id": service_id})
        return bool(result.get("serviceDelete", {}).get("success", False))

    # ════════════════════════════════════════════════════════
    # MUTATIONS: DEPLOYMENTS
    # ════════════════════════════════════════════════════════

    def deploy_service(self, service_id: str, commit_sha: Optional[str] = None) -> dict[str, object]:
        mutation = gql("""
            mutation Deploy($serviceId: String!, $commitSha: String) {
                deploymentCreate(input: {serviceId: $serviceId, commitSha: $commitSha}) {
                    deployment { id status createdAt }
                }
            }
        """)
        result = self.client.execute(mutation, variable_values={"serviceId": service_id, "commitSha": commit_sha})
        return result.get("deploymentCreate", {}).get("deployment", {})

    def restart_deployment(self, deployment_id: str) -> dict[str, object]:
        mutation = gql("""
            mutation Restart($id: String!) {
                deploymentRestart(input: {id: $id}) {
                    deployment { id status createdAt }
                }
            }
        """)
        result = self.client.execute(mutation, variable_values={"id": deployment_id})
        return result.get("deploymentRestart", {}).get("deployment", {})

    # ════════════════════════════════════════════════════════
    # MUTATIONS: VARIABLES
    # ════════════════════════════════════════════════════════

    def set_variable(self, service_id: str, name: str, value: str) -> dict[str, object]:
        mutation = gql("""
            mutation SetVariable($serviceId: String!, $name: String!, $value: String!) {
                variableSet(input: {serviceId: $serviceId, name: $name, value: $value}) {
                    variable { id name value }
                }
            }
        """)
        result = self.client.execute(mutation, variable_values={
            "serviceId": service_id, "name": name, "value": value,
        })
        return result.get("variableSet", {}).get("variable", {})

    def delete_variable(self, variable_id: str) -> bool:
        mutation = gql("""
            mutation DeleteVariable($id: String!) {
                variableDelete(input: {id: $id}) { success }
            }
        """)
        result = self.client.execute(mutation, variable_values={"id": variable_id})
        return bool(result.get("variableDelete", {}).get("success", False))

    # ════════════════════════════════════════════════════════
    # MUTATIONS: VOLUMES
    # ════════════════════════════════════════════════════════

    def create_volume(self, project_id: str, name: str, size_gb: int) -> dict[str, object]:
        mutation = gql("""
            mutation CreateVolume($projectId: String!, $name: String!, $sizeGb: Int!) {
                volumeCreate(input: {projectId: $projectId, name: $name, sizeGb: $sizeGb}) {
                    volume { id name size createdAt }
                }
            }
        """)
        result = self.client.execute(mutation, variable_values={
            "projectId": project_id, "name": name, "sizeGb": size_gb,
        })
        return result.get("volumeCreate", {}).get("volume", {})

    def delete_volume(self, volume_id: str) -> bool:
        mutation = gql("""
            mutation DeleteVolume($id: String!) {
                volumeDelete(input: {id: $id}) { success }
            }
        """)
        result = self.client.execute(mutation, variable_values={"id": volume_id})
        return bool(result.get("volumeDelete", {}).get("success", False))

    # ════════════════════════════════════════════════════════
    # MUTATIONS: DOMAINS
    # ════════════════════════════════════════════════════════

    def create_domain(self, service_id: str, domain: str, port: Optional[int] = None) -> dict[str, object]:
        mutation = gql("""
            mutation CreateDomain($serviceId: String!, $domain: String!, $port: Int) {
                domainCreate(input: {serviceId: $serviceId, domain: $domain, port: $port}) {
                    domain { id domain createdAt }
                }
            }
        """)
        result = self.client.execute(mutation, variable_values={
            "serviceId": service_id, "domain": domain, "port": port,
        })
        return result.get("domainCreate", {}).get("domain", {})

    def delete_domain(self, domain_id: str) -> bool:
        mutation = gql("""
            mutation DeleteDomain($id: String!) {
                domainDelete(input: {id: $id}) { success }
            }
        """)
        result = self.client.execute(mutation, variable_values={"id": domain_id})
        return bool(result.get("domainDelete", {}).get("success", False))


# ═══════════════════════════════════════════════════════════════
# CONVENIENCE: Status do Projeto
# ═══════════════════════════════════════════════════════════════

def get_hydra_status() -> dict[str, object]:
    """Quick status check for the entire Hydra ecosystem."""
    token = os.environ.get("RAILWAY_API_TOKEN", "")
    project_id = os.environ.get("RAILWAY_PROJECT_ID", "")
    env_id = os.environ.get("RAILWAY_ENV_ID", "")

    if not token or not project_id:
        return {"status": "unconfigured", "missing": ["RAILWAY_API_TOKEN", "RAILWAY_PROJECT_ID"]}

    try:
        client = RailwayAPIClient(token)
        project = client.get_project(project_id)
        services = client.list_services(project_id, env_id) if env_id else []
        volumes = client.list_volumes(project_id)

        return {
            "status": "connected",
            "project": project.get("name", "?"),
            "services_count": len(services),
            "services": [{"name": s.get("name"), "id": s.get("id")} for s in services],
            "volumes_count": len(volumes),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
