"""Suporte específico para a decisão Assistente/IA do chatbot."""
from datetime import datetime

from .support_manager import SupportManager


class AssistantSupport:
    MODES = ("Assistant", "Artificial Intelligence", "Both")
    AI_MODES = ("Online AI", "Offline AI", "Both")

    def __init__(self, project_root=None):
        self.manager = SupportManager(project_root)

    def validate_configuration(self):
        config = self.manager.load_config()
        chatbot = config.get("status_chatbot", {})
        ai = config.get("status_ai", {})
        chatbot_mode = chatbot.get("selected", "")
        ai_mode = ai.get("selected", "")
        valid_chatbot = chatbot_mode in self.MODES
        valid_ai = ai_mode in self.AI_MODES
        result = self.manager._status(valid_chatbot and valid_ai, "Modos do chatbot válidos." if valid_chatbot and valid_ai else "Configuração de modos inválida.", chatbot_mode=chatbot_mode, ai_mode=ai_mode, available_chatbot_modes=list(self.MODES), available_ai_modes=list(self.AI_MODES))
        return self.manager._record("assistant_modes", result)

    def trace_decision(self, chatbot_mode, ai_mode, command_found=False, online_ready=False, local_ready=False):
        if chatbot_mode == "Assistant":
            route = "assistant_command" if command_found else "assistant_unknown_command"
        elif chatbot_mode == "Artificial Intelligence":
            route = "ai_flow"
        elif chatbot_mode == "Both":
            route = "assistant_command" if command_found else "ai_flow"
        else:
            route = "invalid_chatbot_mode"
        if route == "ai_flow":
            if ai_mode == "Online AI": provider = "online" if online_ready else "online_unavailable"
            elif ai_mode == "Offline AI": provider = "local" if local_ready else "local_unavailable"
            elif ai_mode == "Both": provider = "online" if online_ready else ("local" if local_ready else "both_unavailable")
            else: provider = "invalid_ai_mode"
            route = f"{route}:{provider}"
        result = self.manager._status(not route.startswith("invalid"), "Rota de decisão calculada.", route=route, chatbot_mode=chatbot_mode, ai_mode=ai_mode, command_found=command_found, online_ready=online_ready, local_ready=local_ready, traced_at=datetime.now().isoformat(timespec="seconds"))
        return self.manager._record("assistant_decision", result)
