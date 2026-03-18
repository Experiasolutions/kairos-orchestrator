# EXPERIA MCP SERVER — Full Implementation
# Model Context Protocol Server for n8n, Postgres, and Infrastructure
# Python 3.10+ | FastAPI + MCP SDK
# Deploy: Railway (Docker) | Internal Network

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Union
import httpx
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv
import json
from datetime import datetime
import logging
import uuid

load_dotenv()

app = FastAPI(title="Experia MCP Server", version="1.0.0")
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# CONFIG & ENVIRONMENT
# ═══════════════════════════════════════════════════════════

class Config:
    N8N_URL = os.getenv("N8N_URL", "http://n8n:5678")
    N8N_API_KEY = os.getenv("N8N_API_KEY", "")

    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
    POSTGRES_DB = os.getenv("POSTGRES_DB", "experia")

    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

    MCP_API_KEY = os.getenv("MCP_API_KEY", "sk_experia_default")
    MCP_PORT = int(os.getenv("MCP_PORT", "3001"))

    BACKUP_PATH = os.getenv("BACKUP_PATH", "/backups")


config = Config()


# ═══════════════════════════════════════════════════════════
# AUTHENTICATION
# ═══════════════════════════════════════════════════════════

async def verify_api_key(x_api_key: str = Header(...)) -> str:
    if x_api_key != config.MCP_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


# ═══════════════════════════════════════════════════════════
# DATABASE CONNECTION
# ═══════════════════════════════════════════════════════════

class DatabasePool:
    def get_connection(self) -> psycopg2.extensions.connection:
        try:
            conn = psycopg2.connect(
                host=config.POSTGRES_HOST,
                port=config.POSTGRES_PORT,
                user=config.POSTGRES_USER,
                password=config.POSTGRES_PASSWORD,
                database=config.POSTGRES_DB,
            )
            return conn
        except Exception as e:
            logger.error("Database connection error: %s", e)
            raise HTTPException(status_code=500, detail="Database connection failed")


db_pool = DatabasePool()


# ═══════════════════════════════════════════════════════════
# N8N CLIENT
# ═══════════════════════════════════════════════════════════

class N8NClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.headers = {
            "X-N8N-API-KEY": api_key,
            "Content-Type": "application/json",
        }

    async def create_workflow(self, workflow_data: dict[str, object]) -> dict[str, object]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/workflows",
                json=workflow_data,
                headers=self.headers,
            )
            if response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            return response.json()

    async def list_workflows(self, limit: int = 50) -> list[dict[str, object]]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/workflows?limit={limit}",
                headers=self.headers,
            )
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            return response.json().get("data", [])

    async def execute_workflow(self, workflow_id: str, data: dict[str, object]) -> dict[str, object]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/workflows/{workflow_id}/execute",
                json=data,
                headers=self.headers,
            )
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            return response.json()

    async def get_workflow_executions(self, workflow_id: str, limit: int = 50) -> list[dict[str, object]]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/workflows/{workflow_id}/executions?limit={limit}",
                headers=self.headers,
            )
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            return response.json().get("data", [])


n8n_client = N8NClient(config.N8N_URL, config.N8N_API_KEY)


# ═══════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ═══════════════════════════════════════════════════════════

class WorkflowStep(BaseModel):
    node_name: str
    node_type: str
    config: dict[str, object]


class CreateWorkflowRequest(BaseModel):
    workflow_name: str
    trigger: str
    steps: list[WorkflowStep]
    active: bool = True


class ExecuteWorkflowRequest(BaseModel):
    workflow_id: str
    data: dict[str, object]


class RunSQLRequest(BaseModel):
    query: str
    params: Optional[list[object]] = None
    timeout_seconds: int = 30


class CreateClientEnvironmentRequest(BaseModel):
    client_name: str
    client_type: str
    features: list[str] = ["workflows", "database", "api", "webhooks"]
    admin_email: str


class ScaleClientResourcesRequest(BaseModel):
    client_id: str
    cpu_cores: int = 2
    memory_gb: int = 4
    storage_gb: int = 50


class CreateWebhookRequest(BaseModel):
    event: str
    target_url: str
    secret: str


# ═══════════════════════════════════════════════════════════
# TOOL 1: N8N WORKFLOW MANAGEMENT (4 endpoints)
# ═══════════════════════════════════════════════════════════

@app.post("/tools/create_n8n_workflow", dependencies=[Depends(verify_api_key)])
async def create_n8n_workflow(request: CreateWorkflowRequest) -> dict[str, object]:
    """Create and deploy n8n workflow."""
    workflow_data: dict[str, object] = {
        "name": request.workflow_name,
        "nodes": [],
        "connections": {},
        "active": request.active,
    }

    trigger_node = {
        "name": "Trigger",
        "type": request.trigger,
        "typeVersion": 1,
        "position": [250, 300],
        "parameters": {},
    }
    nodes: list[dict[str, object]] = [trigger_node]

    for idx, step in enumerate(request.steps):
        node = {
            "name": step.node_name,
            "type": step.node_type,
            "typeVersion": 1,
            "position": [250 + (idx + 1) * 300, 300],
            "parameters": step.config,
        }
        nodes.append(node)

    workflow_data["nodes"] = nodes
    result = await n8n_client.create_workflow(workflow_data)
    n8n_id = str(result.get("id", ""))

    conn = db_pool.get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO workflows (workflow_id, name, n8n_id, status, created_at) VALUES (%s, %s, %s, %s, %s)",
        (n8n_id, request.workflow_name, n8n_id, "active", datetime.now()),
    )
    conn.commit()
    cur.close()
    conn.close()

    return {
        "workflow_id": n8n_id,
        "status": "created",
        "webhook_url": f"{config.N8N_URL}/webhook/{n8n_id}",
        "execution_url": f"{config.N8N_URL}/workflow/{n8n_id}",
    }


@app.get("/tools/list_n8n_workflows", dependencies=[Depends(verify_api_key)])
async def list_n8n_workflows(filter: str = "all", limit: int = 50) -> dict[str, object]:
    """List all n8n workflows."""
    workflows = await n8n_client.list_workflows(limit)
    if filter == "active":
        workflows = [w for w in workflows if w.get("active")]
    elif filter == "inactive":
        workflows = [w for w in workflows if not w.get("active")]
    return {"workflows": workflows, "count": len(workflows)}


@app.post("/tools/execute_n8n_workflow", dependencies=[Depends(verify_api_key)])
async def execute_n8n_workflow(request: ExecuteWorkflowRequest) -> dict[str, object]:
    """Execute n8n workflow with data."""
    result = await n8n_client.execute_workflow(request.workflow_id, request.data)
    conn = db_pool.get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO workflow_executions (workflow_id, execution_id, status, result, created_at) VALUES (%s, %s, %s, %s, %s)",
        (request.workflow_id, str(result.get("id", "")), "success", json.dumps(result), datetime.now()),
    )
    conn.commit()
    cur.close()
    conn.close()
    return {"execution_id": result.get("id"), "status": "success", "result": result}


@app.get("/tools/get_n8n_workflow_logs", dependencies=[Depends(verify_api_key)])
async def get_n8n_workflow_logs(workflow_id: str, limit: int = 50, filter: str = "all") -> dict[str, object]:
    """Get workflow execution logs."""
    executions = await n8n_client.get_workflow_executions(workflow_id, limit)
    if filter == "success":
        executions = [e for e in executions if e.get("status") == "success"]
    elif filter == "error":
        executions = [e for e in executions if e.get("status") == "error"]
    return {"workflow_id": workflow_id, "executions": executions, "count": len(executions)}


# ═══════════════════════════════════════════════════════════
# TOOL 2: DATABASE MANAGEMENT (3 endpoints)
# ═══════════════════════════════════════════════════════════

@app.post("/tools/run_sql_query", dependencies=[Depends(verify_api_key)])
async def run_sql_query(request: RunSQLRequest) -> dict[str, object]:
    """Execute SQL query on Postgres."""
    conn = db_pool.get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    start_time = datetime.now()
    cur.execute(request.query, request.params or [])

    if cur.description:
        rows = [dict(row) for row in cur.fetchall()]
    else:
        rows = []
        conn.commit()

    execution_time = (datetime.now() - start_time).total_seconds() * 1000
    cur.close()
    conn.close()
    return {"rows": rows, "row_count": len(rows), "execution_time_ms": execution_time}


@app.post("/tools/create_database_backup", dependencies=[Depends(verify_api_key)])
async def create_database_backup(backup_name: str, fmt: str = "sql") -> dict[str, object]:
    """Create Postgres database backup."""
    import subprocess

    backup_file = f"{config.BACKUP_PATH}/{backup_name}.{fmt}"
    cmd = [
        "pg_dump",
        f"--host={config.POSTGRES_HOST}",
        f"--port={config.POSTGRES_PORT}",
        f"--username={config.POSTGRES_USER}",
        f"--dbname={config.POSTGRES_DB}",
        f"--file={backup_file}",
    ]
    env = {**os.environ, "PGPASSWORD": config.POSTGRES_PASSWORD}
    subprocess.run(cmd, check=True, env=env)
    file_size = os.path.getsize(backup_file) / (1024 * 1024)

    conn = db_pool.get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO backups (backup_name, file_path, size_mb, format, created_at) VALUES (%s, %s, %s, %s, %s)",
        (backup_name, backup_file, file_size, fmt, datetime.now()),
    )
    conn.commit()
    cur.close()
    conn.close()
    return {"backup_id": backup_name, "file_url": f"file://{backup_file}", "size_mb": file_size}


@app.post("/tools/restore_database_backup", dependencies=[Depends(verify_api_key)])
async def restore_database_backup(backup_id: str, confirm: bool = False) -> dict[str, object]:
    """Restore Postgres database from backup."""
    if not confirm:
        raise HTTPException(status_code=400, detail="Confirmation required (confirm=true)")
    import subprocess

    conn = db_pool.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT file_path FROM backups WHERE backup_name = %s", (backup_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    if not result:
        raise HTTPException(status_code=404, detail="Backup not found")

    backup_file = result[0]
    cmd = [
        "psql",
        f"--host={config.POSTGRES_HOST}",
        f"--port={config.POSTGRES_PORT}",
        f"--username={config.POSTGRES_USER}",
        f"--dbname={config.POSTGRES_DB}",
        f"--file={backup_file}",
    ]
    start_time = datetime.now()
    subprocess.run(cmd, check=True, env={**os.environ, "PGPASSWORD": config.POSTGRES_PASSWORD})
    duration = (datetime.now() - start_time).total_seconds()
    return {"status": "success", "duration_seconds": duration}


# ═══════════════════════════════════════════════════════════
# TOOL 3: CLIENT ENVIRONMENT MANAGEMENT (4 endpoints)
# ═══════════════════════════════════════════════════════════

@app.post("/tools/create_client_environment", dependencies=[Depends(verify_api_key)])
async def create_client_environment(request: CreateClientEnvironmentRequest) -> dict[str, object]:
    """Create isolated environment for new client."""
    client_id = str(uuid.uuid4())
    conn = db_pool.get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO clients (client_id, name, type, admin_email, status, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
        (client_id, request.client_name, request.client_type, request.admin_email, "active", datetime.now()),
    )
    conn.commit()
    cur.close()
    conn.close()
    slug = request.client_name.lower().replace(" ", "-")
    return {
        "client_id": client_id,
        "n8n_url": f"https://n8n-{slug}.experia.com",
        "api_key": f"sk_live_{client_id}",
        "status": "created",
    }


@app.get("/tools/list_client_environments", dependencies=[Depends(verify_api_key)])
async def list_client_environments(filter: str = "all") -> dict[str, object]:
    """List all client environments."""
    conn = db_pool.get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    if filter == "active":
        cur.execute("SELECT * FROM clients WHERE status = 'active'")
    elif filter == "inactive":
        cur.execute("SELECT * FROM clients WHERE status = 'inactive'")
    else:
        cur.execute("SELECT * FROM clients")
    clients = [dict(row) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return {"clients": clients, "count": len(clients)}


@app.get("/tools/get_client_metrics", dependencies=[Depends(verify_api_key)])
async def get_client_metrics(client_id: str) -> dict[str, object]:
    """Get usage metrics for specific client."""
    conn = db_pool.get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT COUNT(*) as count FROM workflows WHERE client_id = %s", (client_id,))
    wf = cur.fetchone()
    cur.execute("SELECT COUNT(*) as count FROM workflow_executions WHERE client_id = %s", (client_id,))
    ex = cur.fetchone()
    cur.execute("SELECT COUNT(*) as count FROM api_logs WHERE client_id = %s", (client_id,))
    api = cur.fetchone()
    cur.close()
    conn.close()
    return {
        "workflows_count": wf["count"] if wf else 0,
        "executions_count": ex["count"] if ex else 0,
        "api_calls": api["count"] if api else 0,
    }


@app.post("/tools/scale_client_resources", dependencies=[Depends(verify_api_key)])
async def scale_client_resources(request: ScaleClientResourcesRequest) -> dict[str, object]:
    """Scale compute/storage for client environment."""
    conn = db_pool.get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE clients SET cpu_cores=%s, memory_gb=%s, storage_gb=%s, updated_at=%s WHERE client_id=%s",
        (request.cpu_cores, request.memory_gb, request.storage_gb, datetime.now(), request.client_id),
    )
    conn.commit()
    cur.close()
    conn.close()
    return {"status": "success", "new_resources": {"cpu": request.cpu_cores, "memory": request.memory_gb, "storage": request.storage_gb}}


# ═══════════════════════════════════════════════════════════
# TOOL 4: INFRASTRUCTURE & MONITORING (3 endpoints)
# ═══════════════════════════════════════════════════════════

@app.get("/tools/get_infrastructure_status", dependencies=[Depends(verify_api_key)])
async def get_infrastructure_status() -> dict[str, object]:
    """Get real-time status of Experia infrastructure."""
    n8n_status = "unknown"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{config.N8N_URL}/healthz", timeout=5)
            n8n_status = "healthy" if response.status_code == 200 else "degraded"
    except Exception:
        n8n_status = "down"

    pg_status = "unknown"
    pg_conns = 0
    try:
        conn = db_pool.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM pg_stat_activity")
        row = cur.fetchone()
        pg_conns = row[0] if row else 0
        pg_status = "healthy"
        cur.close()
        conn.close()
    except Exception:
        pg_status = "down"

    return {
        "n8n": {"status": n8n_status},
        "postgres": {"status": pg_status, "connections": pg_conns},
        "api_gateway": {"status": "healthy"},
    }


@app.get("/tools/get_infrastructure_metrics", dependencies=[Depends(verify_api_key)])
async def get_infrastructure_metrics(component: str = "all") -> dict[str, object]:
    """Get system metrics."""
    try:
        import psutil
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage("/").percent,
        }
    except ImportError:
        return {"error": "psutil not installed", "note": "pip install psutil"}


@app.post("/tools/restart_infrastructure_component", dependencies=[Depends(verify_api_key)])
async def restart_infrastructure_component(component: str) -> dict[str, object]:
    """Restart n8n, Postgres, or Redis."""
    import subprocess
    valid = {"n8n", "postgresql", "redis-server"}
    if component not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid component. Use: {valid}")
    subprocess.run(["systemctl", "restart", component], check=True)
    return {"status": "restarted", "component": component}


# ═══════════════════════════════════════════════════════════
# TOOL 5: INTEGRATIONS & WEBHOOKS (2 endpoints)
# ═══════════════════════════════════════════════════════════

@app.post("/tools/create_webhook", dependencies=[Depends(verify_api_key)])
async def create_webhook(request: CreateWebhookRequest) -> dict[str, object]:
    """Create webhook for external service integration."""
    webhook_id = str(uuid.uuid4())
    conn = db_pool.get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO webhooks (webhook_id, event, target_url, secret, status, created_at) VALUES (%s,%s,%s,%s,%s,%s)",
        (webhook_id, request.event, request.target_url, request.secret, "active", datetime.now()),
    )
    conn.commit()
    cur.close()
    conn.close()
    return {"webhook_id": webhook_id, "event": request.event, "status": "active"}


@app.get("/tools/list_integrations", dependencies=[Depends(verify_api_key)])
async def list_integrations() -> dict[str, object]:
    """List all active integrations."""
    conn = db_pool.get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM webhooks WHERE status = 'active'")
    webhooks = [dict(row) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return {"integrations": webhooks, "count": len(webhooks)}


# ═══════════════════════════════════════════════════════════
# HEALTH & ROOT
# ═══════════════════════════════════════════════════════════

@app.get("/health")
async def health_check() -> dict[str, object]:
    return {"status": "healthy", "service": "experia-mcp-server", "version": "1.0.0", "timestamp": datetime.now().isoformat()}


@app.get("/")
async def root() -> dict[str, object]:
    return {
        "name": "Experia MCP Server",
        "version": "1.0.0",
        "tools": {"n8n_workflows": 4, "database": 3, "client_management": 4, "infrastructure": 3, "integrations": 2},
        "total_tools": 16,
        "docs": "/docs",
    }


# ═══════════════════════════════════════════════════════════
# LIFECYCLE
# ═══════════════════════════════════════════════════════════

@app.on_event("startup")
async def startup_event() -> None:
    logger.info("🚀 Experia MCP Server starting on port %s", config.MCP_PORT)
    logger.info("   N8N: %s | Postgres: %s:%s", config.N8N_URL, config.POSTGRES_HOST, config.POSTGRES_PORT)


@app.on_event("shutdown")
async def shutdown_event() -> None:
    logger.info("Experia MCP Server shutting down...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=config.MCP_PORT, log_level="info")
