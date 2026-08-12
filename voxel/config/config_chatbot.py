import importlib.util
import json
from datetime import datetime
from pathlib import Path


class ChatbotConfig:
    def __init__(self, project_root=None, input_provider=None, output_printer=print, command_executor=None):
        self.project_root = Path(project_root) if project_root else Path(__file__).resolve().parents[1]
        self.input_provider = input_provider or input
        self.output_printer = output_printer
        self.command_executor = command_executor
        self.initialization_log = []
        self.is_local_ai_ready = False
        self.is_online_ai_ready = False
        self._load_modules()
        self._initialize()

    def _load_class(self, filename, class_name):
        path = self.project_root / "config" / filename
        try:
            spec = importlib.util.spec_from_file_location(class_name, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return getattr(module, class_name)(project_root=self.project_root)
        except Exception as error:
            self.initialization_log.append(f"{filename}: {error}")
            return None

    def _load_modules(self):
        self.database = self._load_class("database_manager.py", "DatabaseManager")
        self.assistant = self._load_class("config_assistant.py", "AssistantConfig")
        self.audio_input = self._load_class("config_audio_input.py", "AudioInputConfig")
        self.audio_output = self._load_class("config_audio_output.py", "AudioOutputConfig")
        self.local_ai = self._load_class("config_local_ai.py", "LocalAIConfig")
        self.online_ai = self._load_class("config_online_ai.py", "OnlineAIConfig")

    def _initialize(self):
        self.configuration = self.database.get_json_config() if self.database else {}
        self.user = self.database.get_active_user() if self.database else {}
        self.username = self.user.get("tb_user_username", "user")
        self.chat_id = None
        if self.database:
            try:
                self.chat_id = self.database.create_chat_session(self.user.get("tb_user_id", 0), "VOXEL Chat")
            except Exception as error:
                self.initialization_log.append(f"chat_session: {error}")
        self.is_local_ai_ready = bool(self.local_ai and self.local_ai.check_availability())
        if not self.is_local_ai_ready:
            self.initialization_log.append("IA local indisponível; o sistema continuará em modo resiliente.")
        if self.online_ai:
            try:
                self.is_online_ai_ready = self.online_ai.check_online_status().get("status") == "READY"
            except Exception as error:
                self.initialization_log.append(f"IA online: {error}")
        if not self.is_online_ai_ready:
            self.initialization_log.append("IA online indisponível; o sistema continuará em modo resiliente.")
        self._prepare_log_path()

    def _prepare_log_path(self):
        date_text = datetime.now().strftime("%Y-%m-%d")
        self.log_directory = self.project_root / "arquivos" / self.username / "log"
        self.log_directory.mkdir(parents=True, exist_ok=True)
        self.log_path = self.log_directory / f"{date_text}_chat_{self.chat_id or 'session'}.txt"

    def capture_user_input(self):
        selected = self.configuration.get("user_input", {}).get("selected", "Keyboard")
        if selected in {"Keyboard", "Both"}:
            return str(self.input_provider()).strip()
        if selected == "Voice" and self.audio_input:
            return str(self.audio_input.get_text_from_mic()).strip()
        return ""

    @staticmethod
    def _timestamp():
        return datetime.now().strftime("%d/%m/%Y - %H:%M:%S")

    def _format_block(self, owner, text):
        return "------------------------------------------------------------------\n" f"[{self._timestamp()}] - [{owner}]\n" f"{text}\n"

    def write_to_daily_log(self, content):
        with self.log_path.open("a", encoding="utf-8") as file:
            file.write(content if content.endswith("\n") else content + "\n")

    def _execute_command(self, result, prompt):
        if self.command_executor:
            return self.command_executor(result, prompt)
        command_file = result.get("script_file")
        if result.get("conditions"):
            return result["conditions"][0].get("response") or result.get("message", "Comando executado.")
        if command_file:
            return result.get("message", f"Comando {command_file} identificado.")
        return result.get("message", "Comando executado.")

    def _assistant_response(self, prompt):
        if not self.assistant:
            return None
        try:
            result = self.assistant.process_input(prompt)
        except Exception as error:
            self.initialization_log.append(f"assistente: {error}")
            return None
        if result.get("status") == "SUCCESS":
            return self._execute_command(result, prompt)
        return None

    def _ai_response(self, prompt):
        selected = self.configuration.get("status_ai", {}).get("selected", "Offline AI")
        if selected in {"Online AI", "Both"} and self.is_online_ai_ready and self.online_ai:
            response = self.online_ai.get_online_response(prompt)
            if response not in {"NO_INTERNET_CONNECTION", "MISSING_API_KEY", "ONLINE_AI_TIMEOUT", "ONLINE_AI_ERROR"}:
                return response, "IA Online"
        if selected in {"Offline AI", "Both"} and self.is_local_ai_ready and self.local_ai:
            response = self.local_ai.get_local_response(prompt)
            if response != "LOCAL_AI_NOT_AVAILABLE":
                return response, "IA Local"
        if selected == "Online AI":
            return "Online IA configurações incorretas", "VOXEL"
        if selected == "Offline AI":
            return "Offline IA configurações incorretas", "VOXEL"
        return "Online IA configurações incorretas\nOffline IA configurações incorretas", "VOXEL"

    def process_message(self, prompt_text):
        prompt = str(prompt_text or "").strip()
        if not prompt:
            return {"emissor": "VOXEL", "resposta": ""}
        user_block = self._format_block(self.username, prompt)
        self.write_to_daily_log(user_block)
        mode = self.configuration.get("status_chatbot", {}).get("selected", "Both")
        response = None
        emitter = "VOXEL"
        if mode in {"Assistant", "Both"}:
            response = self._assistant_response(prompt)
            if response is not None:
                emitter = "Assistente VOXEL"
        if response is None and mode in {"Artificial Intelligence", "Both"}:
            response, emitter = self._ai_response(prompt)
        if response is None:
            response = "Desculpe, comando não reconhecido. O modo Inteligência Artificial está desativado."
        result = {"emissor": emitter, "resposta": str(response)}
        self.send_response_output(emitter, result["resposta"])
        return result

    def send_response_output(self, emitter, response_text):
        block = self._format_block(emitter, response_text)
        self.write_to_daily_log(block)
        selected = self.configuration.get("chatbot_output", {}).get("selected", "Both")
        if selected in {"Text", "Both"}:
            self.output_printer(block, end="")
        if selected in {"Voice", "Both"} and self.audio_output:
            self.audio_output.speak_text(response_text)
        return block

    def start_chat_session(self, max_messages=None):
        greeting = self.user.get("tb_user_salutation", "")
        first_name = self.user.get("tb_user_first_name", "")
        if greeting or first_name:
            self.send_response_output("Assistente VOXEL", f"{greeting} {first_name}".strip())
        messages = 0
        while max_messages is None or messages < max_messages:
            prompt = self.capture_user_input()
            if prompt.lower() in {"sair", "encerrar chat", "encerrar", "exit", "quit"}:
                self.write_to_daily_log(self._format_block(self.username, "Sessão encerrada."))
                break
            self.process_message(prompt)
            messages += 1

    def get_initialization_status(self):
        return {
            "is_local_ai_ready": self.is_local_ai_ready,
            "is_online_ai_ready": self.is_online_ai_ready,
            "chat_id": self.chat_id,
            "log_path": str(self.log_path),
            "warnings": list(self.initialization_log),
        }
