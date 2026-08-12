import json
import socket
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from pathlib import Path


class OnlineAIConfig:
    PROVIDER_ENDPOINTS = {
        "openai": "https://api.openai.com/v1/chat/completions",
        "groq": "https://api.groq.com/openai/v1/chat/completions",
        "google_gemini": "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
        "gemini": "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
        "claude": "https://api.anthropic.com/v1/messages",
    }

    def __init__(self, project_root=None, providers=None, local_fallback=None):
        self.project_root = Path(project_root) if project_root else Path(__file__).resolve().parents[1]
        self.config_path = self.project_root / "config" / "database" / "database_general.json"
        self.providers = providers or {}
        self.local_fallback = local_fallback
        self.online_history = []
        self.update_settings()

    def update_settings(self):
        with self.config_path.open("r", encoding="utf-8") as file:
            configuration = json.load(file)
        self.settings = configuration.get("online_ai_config", {})
        self.active_provider = self.settings.get("default_provider", self.settings.get("provider", "none"))
        self.api_keys = dict(self.settings.get("api_keys", {}))
        if self.settings.get("api_key") and self.active_provider not in self.api_keys:
            self.api_keys[self.active_provider] = self.settings["api_key"]
        self.temperature = float(self.settings.get("temperature", self.settings.get("temperature_online", 0.7)))
        self.max_tokens = int(self.settings.get("max_tokens", self.settings.get("max_tokens_online", 1000)))
        self.timeout = int(self.settings.get("timeout", self.settings.get("request_timeout", 30)))
        self.use_history = bool(self.settings.get("use_history", self.settings.get("save_history_online", True)))
        self.max_history = int(self.settings.get("max_history", 20))
        self.fallback_to_local = bool(self.settings.get("fallback_to_local", self.settings.get("local_fallback_mode", True)))
        return self.settings

    def _internet_available(self):
        try:
            with socket.create_connection(("8.8.8.8", 53), timeout=2):
                return True
        except OSError:
            try:
                urllib.request.urlopen("https://www.google.com", timeout=3)
                return True
            except Exception:
                return False

    def validate_connection_and_keys(self):
        if not self._internet_available():
            return {"status": "NO_INTERNET_CONNECTION"}
        key = self.api_keys.get(self.active_provider)
        if not key:
            for provider, candidate in self.api_keys.items():
                if candidate and provider in self.PROVIDER_ENDPOINTS:
                    self.active_provider = provider
                    return {"status": "READY", "provider": provider}
            return {"status": "MISSING_API_KEY"}
        return {"status": "READY", "provider": self.active_provider}

    def _build_messages(self, prompt):
        messages = []
        if self.use_history:
            messages.extend(self.online_history)
        messages.append({"role": "user", "content": str(prompt)})
        return messages

    def _provider_request(self, provider, prompt):
        key = self.api_keys[provider]
        messages = self._build_messages(prompt)
        endpoint = self.PROVIDER_ENDPOINTS[provider]
        if provider in {"openai", "groq"}:
            payload = {
                "model": self.settings.get("online_model", "gpt-3.5-turbo"),
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            }
            headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        elif provider in {"google_gemini", "gemini"}:
            text = "\n".join(message["content"] for message in messages)
            endpoint = f"{endpoint}?key={key}"
            payload = {"contents": [{"parts": [{"text": text}]}], "generationConfig": {"temperature": self.temperature, "maxOutputTokens": self.max_tokens}}
            headers = {"Content-Type": "application/json"}
        else:
            payload = {"model": self.settings.get("online_model", "claude-3-haiku-20240307"), "messages": messages, "max_tokens": self.max_tokens, "temperature": self.temperature}
            headers = {"x-api-key": key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"}
        request = urllib.request.Request(endpoint, data=json.dumps(payload).encode("utf-8"), headers=headers)
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        if provider in {"openai", "groq"}:
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")
        if provider in {"google_gemini", "gemini"}:
            return data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        return data.get("content", [{}])[0].get("text", "")

    def _call_provider(self, provider, prompt):
        handler = self.providers.get(provider)
        if handler is not None:
            return handler(prompt, self.settings, self.online_history)
        return self._provider_request(provider, prompt)

    def _save_history(self, prompt, response):
        if not self.use_history:
            self.online_history.clear()
            return
        self.online_history.extend([{"role": "user", "content": str(prompt)}, {"role": "assistant", "content": str(response)}])
        self.online_history = self.online_history[-self.max_history:]

    def generate_response(self, prompt_text):
        status = self.validate_connection_and_keys()
        if status["status"] != "READY":
            if self.fallback_to_local and self.local_fallback is not None:
                return self.local_fallback(prompt_text)
            return status["status"]
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self._call_provider, self.active_provider, str(prompt_text))
                response = future.result(timeout=self.timeout)
        except TimeoutError:
            return "ONLINE_AI_TIMEOUT"
        except (urllib.error.URLError, OSError, Exception):
            return "ONLINE_AI_ERROR"
        response = str(response or "").strip()
        self._save_history(prompt_text, response)
        return response

    def get_online_response(self, prompt):
        return self.generate_response(prompt)

    def check_online_status(self):
        return self.validate_connection_and_keys()

    def set_active_provider(self, provider_name):
        provider = str(provider_name).strip().lower()
        if provider not in self.PROVIDER_ENDPOINTS and provider not in self.providers:
            return {"status": "INVALID_PROVIDER", "provider": provider}
        self.active_provider = provider
        self.settings["default_provider"] = provider
        self.settings["provider"] = provider
        return {"status": "PROVIDER_CHANGED", "provider": provider}

    def clear_history(self):
        self.online_history.clear()
        return self.online_history
