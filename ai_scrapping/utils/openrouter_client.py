"""
OpenRouter API Client & Free Model Discovery
Fetches live freely-available models and handles chat completions.
"""

import os
import requests
from typing import List, Dict, Any, Optional

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Priority ranking for the best known free models on OpenRouter
TOP_RECOMMENDED_FREE_MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemini-2.0-flash-exp:free",
    "deepseek/deepseek-r1:free",
    "qwen/qwen-2.5-coder-32b-instruct:free",
    "meta-llama/llama-3.1-70b-instruct:free",
    "meta-llama/llama-3.1-8b-instruct:free",
    "mistralai/mistral-7b-instruct:free",
    "minimax/minimax-m3.1-flash:free",
    "nvidia/nemotron-3.5-lightning:free",
    "liquid/lfm-2.5-2.6b:free"
]

def fetch_openrouter_free_models() -> List[Dict[str, Any]]:
    """
    Queries OpenRouter's live API to return all currently available free models,
    ranked with top-performing instruction & reasoning models first.
    """
    free_models = []
    try:
        resp = requests.get(f"{OPENROUTER_BASE_URL}/models", timeout=10)
        if resp.status_code == 200:
            data = resp.json().get("data", [])
            for m in data:
                model_id = m.get("id", "")
                pricing = m.get("pricing", {})
                is_free = (
                    ":free" in model_id or
                    (str(pricing.get("prompt", "")).strip() in ["0", "0.0"] and
                     str(pricing.get("completion", "")).strip() in ["0", "0.0"])
                )
                if is_free:
                    free_models.append({
                        "id": model_id,
                        "name": m.get("name", model_id),
                        "context_length": m.get("context_length", 8192),
                        "description": m.get("description", "")
                    })
    except Exception as e:
        print(f"[OPENROUTER] Error fetching live models: {e}")

    # Fallback to known top free models if network/API temporarily unavailable
    if not free_models:
        for model_id in TOP_RECOMMENDED_FREE_MODELS:
            free_models.append({
                "id": model_id,
                "name": model_id.split("/")[-1].replace(":free", "").title(),
                "context_length": 8192,
                "description": "High performance instruction model (Free Tier)"
            })

    # Sort so top recommended models appear first
    def sort_key(m):
        m_id = m["id"]
        for idx, rec in enumerate(TOP_RECOMMENDED_FREE_MODELS):
            if rec == m_id:
                return idx
        return 999

    free_models.sort(key=sort_key)
    return free_models

def ask_openrouter(
    messages: List[Dict[str, str]],
    model: str,
    api_key: str,
    temperature: float = 0.4
) -> str:
    """Sends a chat completion request to OpenRouter."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/ScrapeGraphAI/Scrapegraph-ai",
        "X-Title": "B2B Lead Mining Agent"
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature
    }

    try:
        resp = requests.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=45
        )
        if resp.status_code == 200:
            res_json = resp.json()
            choices = res_json.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "").strip()
        else:
            return f"[Error from OpenRouter: HTTP {resp.status_code} - {resp.text[:200]}]"
    except Exception as e:
        return f"[Connection error contacting OpenRouter: {e}]"

    return ""
