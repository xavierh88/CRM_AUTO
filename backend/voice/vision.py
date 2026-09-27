import base64
import os

import httpx


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = os.getenv("OPENROUTER_VISION_MODEL", "openrouter/free")


class VisionError(Exception):
    pass


async def analyze_image(
    image_bytes: bytes,
    mime_type: str,
    prompt: str,
) -> str:
    api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:
        raise VisionError("OPENROUTER_API_KEY is not configured")

    if not mime_type.startswith("image/"):
        raise VisionError("The supplied file is not an image")

    instruction = (prompt or "").strip()

    if not instruction:
        instruction = (
            "Analiza esta imagen cuidadosamente. "
            "Describe lo que contiene y transcribe cualquier texto legible. "
            "Responde en el mismo idioma que use el usuario."
        )

    encoded = base64.b64encode(image_bytes).decode("ascii")
    data_url = f"data:{mime_type};base64,{encoded}"

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": instruction
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": data_url
                        }
                    }
                ]
            }
        ]
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                OPENROUTER_URL,
                headers=headers,
                json=payload,
            )
    except httpx.HTTPError as exc:
        raise VisionError(
            f"OpenRouter connection failed: {type(exc).__name__}"
        ) from exc

    if response.status_code >= 400:
        try:
            upstream = response.json()
            error = upstream.get("error") or {}
            message = error.get("message") or f"HTTP {response.status_code}"
        except Exception:
            message = f"HTTP {response.status_code}"

        raise VisionError(
            f"OpenRouter Vision error: {message}"
        )

    try:
        data = response.json()

        choices = data.get("choices") or []

        if not choices:
            raise VisionError("OpenRouter returned no analysis")

        content = (
            choices[0]
            .get("message", {})
            .get("content", "")
        )

        if isinstance(content, str):
            result = content.strip()
        elif isinstance(content, list):
            result = "\n".join(
                item.get("text", "")
                for item in content
                if isinstance(item, dict) and item.get("text")
            ).strip()
        else:
            result = ""

        if not result:
            raise VisionError(
                "OpenRouter returned an empty image analysis"
            )

        return result

    except VisionError:
        raise
    except Exception as exc:
        raise VisionError(
            "OpenRouter returned an unexpected response"
        ) from exc
