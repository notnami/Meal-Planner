"""Thin wrapper around a local Ollama server (plain HTTP, no extra dependency)."""
import json
import os
import re

import requests

DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "gemma3")
HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")


def ollama_ready(model):
    """Return (ready, problem_message)."""
    try:
        resp = requests.get(f"{HOST}/api/tags", timeout=3)
        resp.raise_for_status()
    except requests.RequestException:
        return False, "Ollama isn't running. Open the Ollama app or run `ollama serve`, then reload."
    names = [m.get("name", "") for m in resp.json().get("models", [])]
    wanted = model if ":" in model else f"{model}:latest"
    if wanted not in names and model not in names:
        return False, f"Model '{model}' isn't installed. Run `ollama pull {model}` in a terminal."
    return True, ""


def chat(prompt, model, temperature=0.2, json_mode=False):
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": temperature},
    }
    if json_mode:
        payload["format"] = "json"
    resp = requests.post(f"{HOST}/api/chat", json=payload, timeout=300)
    resp.raise_for_status()
    return resp.json()["message"]["content"].strip()


def chat_json(prompt, model, retries=2):
    """Ask for JSON and return a dict. Retries if the model returns something unparseable."""
    for _ in range(retries + 1):
        text = chat(prompt, model, temperature=0.1, json_mode=True)
        candidates = [text]
        match = re.search(r"\{.*\}", text, re.S)
        if match:
            candidates.append(match.group(0))
        for attempt in candidates:
            try:
                data = json.loads(attempt)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                return data
    raise RuntimeError("The model didn't return valid JSON. Try again, or try a larger model such as gemma3:12b.")
