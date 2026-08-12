import json
import urllib.error
import urllib.request
from pathlib import Path


class LocalAIConfig:
    def __init__(self, project_root=None, engines=None):
        self.project_root = Path(project_root) if project_root else Path(__file__).resolve().parents[1]
        self.config_path = self.project_root / "config" / "database" / "database_general.json"
        self.engines = engines or {}
        self.local_history = []
        self.engine = None
        self.available = False
        self.update_ai_settings()
        self.initialize_local_engine()

    def update_ai_settings(self):
        with self.config_path.open("r", encoding="utf-8") as file:
            configuration = json.load(file)
        self.settings = configuration.get("local_ai_config", {})
        self.default_model = self.settings.get("default_model", "simple")
        self.temperature = float(self.settings.get("temperature", 0.7))
        self.top_p = float(self.settings.get("top_p", 0.9))
        self.max_tokens = int(self.settings.get("max_tokens", 500))
        self.use_history = bool(self.settings.get("use_history", True))
        self.max_history = int(self.settings.get("max_history", 50))
        self.system_prompt = self.settings.get("system_prompt", "Você é uma assistente virtual útil e objetiva.")
        return self.settings

    def initialize_local_engine(self):
        model = str(self.default_model).lower()
        self.engine = None
        self.available = False
        if model in {"echo", "simple"}:
            self.engine = self.engines.get(model, self._simple_engine)
            self.available = True
        elif model == "ollama":
            self.engine = self.engines.get(model, self._ollama_engine)
            self.available = self._ollama_available()
        elif model in self.engines:
            self.engine = self.engines[model]
            self.available = self.engine is not None
        else:
            try:
                if model == "gpt4all":
                    from gpt4all import GPT4All
                    model_name = self.settings.get("model_name") or self.settings.get("installed_model_info")
                    if model_name:
                        self.engine = GPT4All(model_name)
                elif model == "transformers":
                    from transformers import pipeline
                    model_name = self.settings.get("model_name") or self.settings.get("installed_model_info")
                    if model_name:
                        self.engine = pipeline("text-generation", model=model_name)
                elif model == "llama_cpp":
                    from llama_cpp import Llama
                    model_path = self.settings.get("model_path")
                    if model_path:
                        self.engine = Llama(model_path=model_path)
                self.available = self.engine is not None
            except Exception:
                self.engine = None
                self.available = False
        return {"status": "READY" if self.available else "LOCAL_AI_NOT_AVAILABLE", "model": model}

    def _ollama_available(self):
        try:
            with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=2) as response:
                return response.status == 200
        except (urllib.error.URLError, OSError):
            return False

    def _simple_engine(self, prompt, **kwargs):
        return f"Resposta local: {prompt.strip()}"

    def _ollama_engine(self, prompt, **kwargs):
        payload = json.dumps({
            "model": self.settings.get("model_name", "llama3"),
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "top_p": self.top_p,
                "num_predict": self.max_tokens,
            },
        }).encode("utf-8")
        request = urllib.request.Request(
            "http://127.0.0.1:11434/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8")).get("response", "")

    def _build_prompt(self, prompt):
        messages = [{"role": "system", "content": self.system_prompt}]
        if self.use_history:
            messages.extend(self.local_history)
        messages.append({"role": "user", "content": prompt})
        return "\n".join(f"{message['role']}: {message['content']}" for message in messages)

    def manage_history(self, user_prompt, ai_response):
        if not self.use_history:
            self.local_history.clear()
            return self.local_history
        self.local_history.extend([
            {"role": "user", "content": str(user_prompt)},
            {"role": "assistant", "content": str(ai_response)},
        ])
        self.local_history = self.local_history[-self.max_history:]
        return self.local_history

    def generate_response(self, prompt_text):
        if not self.available or self.engine is None:
            return "LOCAL_AI_NOT_AVAILABLE"
        prompt = self._build_prompt(str(prompt_text))
        try:
            if self.default_model in {"echo", "simple", "ollama"}:
                response = self.engine(prompt, temperature=self.temperature, top_p=self.top_p, max_tokens=self.max_tokens)
            elif callable(self.engine):
                response = self.engine(prompt, temperature=self.temperature, top_p=self.top_p, max_tokens=self.max_tokens)
            elif hasattr(self.engine, "generate"):
                response = self.engine.generate(prompt, max_new_tokens=self.max_tokens, temperature=self.temperature, top_p=self.top_p)
            elif hasattr(self.engine, "create_completion"):
                response = self.engine.create_completion(prompt, max_tokens=self.max_tokens, temperature=self.temperature, top_p=self.top_p)
            else:
                return "LOCAL_AI_NOT_AVAILABLE"
        except Exception:
            return "LOCAL_AI_NOT_AVAILABLE"
        if isinstance(response, dict):
            response = response.get("response") or response.get("text") or response.get("choices", [{}])[0].get("text", "")
        response = str(response).strip()
        self.manage_history(prompt_text, response)
        return response

    def get_local_response(self, prompt):
        return self.generate_response(prompt)

    def clear_history(self):
        self.local_history.clear()
        return self.local_history

    def check_availability(self):
        return bool(self.available)
