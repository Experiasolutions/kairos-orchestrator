-- Experia MCP Server — Database Schema
-- Run: psql -U postgres -d experia -f init_db.sql

-- Workflows
CREATE TABLE IF NOT EXISTS workflows (
    id SERIAL PRIMARY KEY,
    workflow_id UUID UNIQUE NOT NULL,
    client_id UUID,
    name VARCHAR(255) NOT NULL,
    n8n_id VARCHAR(255),
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Workflow executions
CREATE TABLE IF NOT EXISTS workflow_executions (
    id SERIAL PRIMARY KEY,
    workflow_id UUID NOT NULL,
    client_id UUID,
    execution_id VARCHAR(255),
    status VARCHAR(50),
    result JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Clients
CREATE TABLE IF NOT EXISTS clients (
    id SERIAL PRIMARY KEY,
    client_id UUID UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50),
    admin_email VARCHAR(255),
    status VARCHAR(50),
    cpu_cores INT DEFAULT 2,
    memory_gb INT DEFAULT 4,
    storage_gb INT DEFAULT 50,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Backups
CREATE TABLE IF NOT EXISTS backups (
    id SERIAL PRIMARY KEY,
    backup_name VARCHAR(255) NOT NULL,
    client_id UUID,
    file_path VARCHAR(500),
    size_mb FLOAT,
    format VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Webhooks
CREATE TABLE IF NOT EXISTS webhooks (
    id SERIAL PRIMARY KEY,
    webhook_id UUID UNIQUE NOT NULL,
    client_id UUID,
    event VARCHAR(255),
    target_url VARCHAR(500),
    secret VARCHAR(255),
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- API logs
CREATE TABLE IF NOT EXISTS api_logs (
    id SERIAL PRIMARY KEY,
    client_id UUID,
    endpoint VARCHAR(255),
    method VARCHAR(10),
    status_code INT,
    response_time_ms INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_workflows_client_id ON workflows(client_id);
CREATE INDEX IF NOT EXISTS idx_executions_workflow_id ON workflow_executions(workflow_id);
CREATE INDEX IF NOT EXISTS idx_clients_status ON clients(status);
CREATE INDEX IF NOT EXISTS idx_api_logs_client_id ON api_logs(client_id);
