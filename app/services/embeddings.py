import os
import json
import logging
from urllib import request as urllib_request
from urllib.error import URLError, HTTPError
from app.services.tls_http import format_tls_error

logger = logging.getLogger(__name__)

DEFAULT_EMBEDDING_MODEL = "openai/text-embedding-3-small"


def get_embedding_model(model_name: str | None = None) -> str:
    if model_name:
        return model_name
    return str(os.getenv("OPENROUTER_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)).strip()


def generate_embeddings(chunks: list[str], model_name: str | None = None) -> list[list[float]]:
    if not chunks:
        return []

    api_key = str(os.getenv("OPENROUTER_API_KEY", "")).strip()
    if not api_key:
        logger.warning("OPENROUTER_API_KEY is not set. Cannot generate embeddings.")
        return [[] for _ in chunks]

    if not model_name:
        model_name = get_embedding_model()

    payload = {
        "model": model_name,
        "input": chunks
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib_request.Request(
        "https://openrouter.ai/api/v1/embeddings",
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "python-requests/2.31.0",
        },
        method="POST"
    )

    try:
        with urllib_request.urlopen(req, timeout=30.0) as response:
            if response.status != 200:
                raise ValueError(f"OpenRouter embedding returned status {response.status}")
            
            body = json.loads(response.read().decode("utf-8"))
            data_list = body.get("data", [])
            # Sort data by its index to preserve input ordering
            data_list.sort(key=lambda x: x.get("index", 0))
            
            embeddings = [d.get("embedding", []) for d in data_list]
            # Ensure return list length matches input chunks
            if len(embeddings) < len(chunks):
                embeddings.extend([[] for _ in range(len(chunks) - len(embeddings))])
            return embeddings[:len(chunks)]
    except Exception as exc:
        logger.error("OpenRouter embedding generation failed: %s", exc)
        return [[] for _ in chunks]


def embedding_dimension(model_name: str | None = None) -> int:
    try:
        embeddings = generate_embeddings(["dimension probe"], model_name=model_name)
        if embeddings and embeddings[0]:
            return len(embeddings[0])
    except Exception:
        pass
    return 1536  # Default dimension for text-embedding-3-small
