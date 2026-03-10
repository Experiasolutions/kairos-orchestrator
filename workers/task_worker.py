# Task Worker — executor da task_queue
import logging
import google.generativeai as genai
from groq import Groq
from model_router import route_model
from key_rotator import rotator
import supabase_client as db
from config import GROQ_API_KEY

logger = logging.getLogger("kairos.worker")


def _call_google(prompt: str, model_name: str) -> str:
    """Chama Google AI Studio com rotação de keys."""
    key = rotator.get_google_key()
    if not key:
        raise RuntimeError("Nenhuma key Google disponível")

    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        error_str = str(e).lower()
        if "rate" in error_str or "quota" in error_str or "429" in error_str:
            rotator.report_error(key, "rate_limit")
        else:
            rotator.report_error(key, "error")
        raise


def _call_groq(prompt: str) -> str:
    """Chama Groq como fallback."""
    if not GROQ_API_KEY:
        raise RuntimeError("Key Groq não configurada")

    client = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4096,
    )
    return response.choices[0].message.content or ""


def call_model(prompt: str, category: str = "", title: str = "", model_override: str | None = None) -> str:
    """Chama o modelo apropriado com fallback automático."""
    model = model_override or route_model(category, title)

    # Tentar Google primeiro
    if model != "groq":
        for attempt in range(3):  # 3 tentativas com rotação
            try:
                return _call_google(prompt, model)
            except Exception as e:
                logger.warning("Tentativa %d falhou para %s: %s", attempt + 1, model, e)

        # Fallback para Groq
        logger.info("Google esgotado — fallback para Groq")
        try:
            return _call_groq(prompt)
        except Exception as e:
            logger.error("Groq também falhou: %s", e)
            return f"⚠️ Todos os modelos falharam: {e}"

    # Groq direto
    return _call_groq(prompt)


def process_task(task: dict) -> dict:
    """Processa uma task da fila."""
    task_id = task["id"]
    title = task.get("title", "")
    category = task.get("category", "general")
    input_data = task.get("input_data", {})
    model_override = task.get("model_override")

    logger.info("Processando task: %s [%s]", title, category)
    db.update_task_status(task_id, "processing")

    try:
        # Montar prompt
        prompt = input_data.get("prompt", title)
        if input_data.get("context"):
            prompt = f"Contexto: {input_data['context']}\n\nTask: {prompt}"

        # Executar
        result = call_model(prompt, category, title, model_override)

        # Salvar resultado
        db.update_task_status(task_id, "completed", output={"result": result})
        logger.info("Task concluída: %s", title)
        return {"status": "completed", "result": result}

    except Exception as e:
        error_msg = str(e)
        db.update_task_status(task_id, "failed", error=error_msg)
        logger.error("Task falhou: %s — %s", title, error_msg)
        return {"status": "failed", "error": error_msg}


def process_pending_tasks(limit: int = 5) -> list[dict]:
    """Processa todas as tasks pendentes."""
    tasks = db.get_pending_tasks(limit)
    if not tasks:
        logger.debug("Nenhuma task pendente")
        return []

    results = []
    for task in tasks:
        result = process_task(task)
        results.append(result)

    logger.info("Processadas %d tasks", len(results))
    return results
