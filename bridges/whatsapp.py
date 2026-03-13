# WhatsApp Bridge — via Evolution API
# Parte do KAIROS SKY — Multi-Channel Bridges
import logging
import json
from typing import Optional

import httpx

logger = logging.getLogger("kairos.bridge.whatsapp")


class WhatsAppBridge:
    """Bridge para enviar/receber mensagens via Evolution API (WhatsApp)."""

    def __init__(
        self,
        api_url: str,
        api_key: str,
        instance_name: str = "kairos-sky",
    ) -> None:
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.instance_name = instance_name
        self.headers = {
            "Content-Type": "application/json",
            "apikey": self.api_key,
        }

    async def send_text(self, to: str, message: str) -> Optional[dict]:
        """Envia mensagem de texto para um número WhatsApp."""
        url = f"{self.api_url}/message/sendText/{self.instance_name}"
        payload = {
            "number": to,
            "text": message,
        }
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, json=payload, headers=self.headers)
                response.raise_for_status()
                result = response.json()
                logger.info("Mensagem enviada para %s", to)
                return result
        except httpx.HTTPStatusError as e:
            logger.error("Erro HTTP ao enviar WhatsApp: %s", e.response.text)
            return None
        except Exception as e:
            logger.error("Erro ao enviar WhatsApp: %s", e)
            return None

    async def send_media(
        self,
        to: str,
        media_url: str,
        caption: str = "",
        media_type: str = "image",
    ) -> Optional[dict]:
        """Envia mídia (imagem, vídeo, documento) via WhatsApp."""
        url = f"{self.api_url}/message/sendMedia/{self.instance_name}"
        payload = {
            "number": to,
            "mediatype": media_type,
            "media": media_url,
            "caption": caption,
        }
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(url, json=payload, headers=self.headers)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error("Erro ao enviar mídia WhatsApp: %s", e)
            return None

    async def check_instance(self) -> bool:
        """Verifica se a instância está conectada."""
        url = f"{self.api_url}/instance/connectionState/{self.instance_name}"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url, headers=self.headers)
                data = response.json()
                state = data.get("instance", {}).get("state", "unknown")
                logger.info("WhatsApp instance state: %s", state)
                return state == "open"
        except Exception as e:
            logger.error("Erro ao verificar instância WhatsApp: %s", e)
            return False

    def parse_webhook(self, payload: dict) -> Optional[dict]:
        """Parseia webhook da Evolution API e extrai mensagem."""
        event = payload.get("event", "")
        if event != "messages.upsert":
            return None

        data = payload.get("data", {})
        key = data.get("key", {})
        message_content = data.get("message", {})

        # Ignorar mensagens enviadas pelo bot
        if key.get("fromMe", False):
            return None

        # Extrair texto
        text = (
            message_content.get("conversation", "")
            or message_content.get("extendedTextMessage", {}).get("text", "")
        )

        if not text:
            return None

        sender = key.get("remoteJid", "").replace("@s.whatsapp.net", "")

        return {
            "sender": sender,
            "text": text,
            "message_id": key.get("id", ""),
            "timestamp": data.get("messageTimestamp", 0),
            "push_name": data.get("pushName", ""),
        }


# Exemplo de uso no main.py do SKY:
#
# from bridges.whatsapp import WhatsAppBridge
#
# bridge = WhatsAppBridge(
#     api_url=os.environ.get("EVOLUTION_API_URL", ""),
#     api_key=os.environ.get("EVOLUTION_API_KEY", ""),
# )
#
# No webhook handler (FastAPI/Flask):
# msg = bridge.parse_webhook(request.json())
# if msg:
#     response = await model_router.process(msg["text"])
#     await bridge.send_text(msg["sender"], response)
