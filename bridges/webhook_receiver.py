"""
Webhook Receiver — Recebe eventos externos no KAIROS SKY.

Do RP-20260218-LOCAL-BRIDGE + RP-20260309-CLOUD-MVP:
  Bridge que recebe webhooks de n8n, ClickUp, WhatsApp (Evolution API),
  e registra na task_queue do Supabase para processamento.

  Roda como thread HTTP dentro do main.py (Railway).
  Endpoint: POST /webhook
"""
import json
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import TypedDict

import supabase_client as db


logger = logging.getLogger("kairos.webhook")

WEBHOOK_PORT = 8080  # Railway é HTTP, não precisa de ngrok


class WebhookPayload(TypedDict, total=False):
    """Estrutura esperada do payload webhook."""
    source: str        # n8n | clickup | whatsapp | custom
    event: str         # new_task | notification | message | etc
    title: str         # título da task a criar
    category: str      # categoria para routing
    priority: int      # 1-10
    data: dict[str, object]  # payload completo


# Token simples para autenticação (configurar via env)
WEBHOOK_TOKEN: str = ""


def set_webhook_token(token: str) -> None:
    """Define o token de autenticação do webhook."""
    global WEBHOOK_TOKEN
    WEBHOOK_TOKEN = token


class WebhookHandler(BaseHTTPRequestHandler):
    """Handler HTTP para webhooks."""

    def do_POST(self) -> None:
        """Processa POST /webhook."""
        if self.path != "/webhook":
            self._respond(404, {"error": "not_found"})
            return

        # Autenticação via header
        if WEBHOOK_TOKEN:
            auth = self.headers.get("Authorization", "")
            expected = f"Bearer {WEBHOOK_TOKEN}"
            if auth != expected:
                self._respond(401, {"error": "unauthorized"})
                return

        # Ler body
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            self._respond(400, {"error": "empty_body"})
            return

        try:
            body = self.rfile.read(content_length)
            payload = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            self._respond(400, {"error": f"invalid_json: {e}"})
            return

        # Processar payload
        result = _process_webhook(payload)
        self._respond(200, result)

    def do_GET(self) -> None:
        """Health check: GET /."""
        if self.path == "/" or self.path == "/health":
            self._respond(200, {
                "status": "ok",
                "service": "KAIROS SKY Webhook Receiver",
                "version": "1.0",
            })
        else:
            self._respond(404, {"error": "not_found"})

    def _respond(self, code: int, data: dict[str, object]) -> None:
        """Envia resposta JSON."""
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def log_message(self, fmt: str, *args: object) -> None:
        """Redireciona log do HTTP server para o logger do KAIROS."""
        logger.info(fmt, *args)


def _process_webhook(payload: dict[str, object]) -> dict[str, object]:
    """
    Processa um payload de webhook e registra na task_queue.
    """
    source = str(payload.get("source", "unknown"))
    event = str(payload.get("event", "generic"))
    title = str(payload.get("title", f"Webhook: {source}/{event}"))
    category = str(payload.get("category", "webhook"))
    priority = int(payload.get("priority", 5))
    data = payload.get("data", {})

    # Salvar como task na fila
    try:
        input_data: dict[str, object] = {
            "source": source,
            "event": event,
            "webhook_data": data,
        }
        task = db.add_task(
            title=title,
            category=category,
            priority=priority,
            input_data=input_data,
            created_by=f"webhook:{source}",
        )
        task_id = ""
        if task and hasattr(task, "data") and task.data:
            task_id = task.data[0].get("id", "") if isinstance(task.data, list) else ""

        logger.info(
            "📥 Webhook recebido: [%s/%s] %s → task_queue (pri: %d)",
            source, event, title[:50], priority,
        )
        return {
            "status": "queued",
            "task_id": task_id,
            "source": source,
            "event": event,
        }
    except Exception as e:
        logger.error("Erro ao processar webhook: %s", e)
        return {"status": "error", "message": str(e)}


def start_webhook_server(port: int = WEBHOOK_PORT, token: str = "") -> threading.Thread:
    """
    Inicia o servidor webhook em uma thread daemon.
    Chamado pelo main.py durante startup.
    """
    if token:
        set_webhook_token(token)

    server = HTTPServer(("0.0.0.0", port), WebhookHandler)

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    logger.info("📡 Webhook receiver ativo na porta %d", port)
    return thread
