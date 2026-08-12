import json
from pathlib import Path


class ConfigStatus:
    def __init__(self, project_root=None):
        self.project_root = Path(project_root) if project_root else Path(__file__).resolve().parents[1]
        self.config_path = self.project_root / "config" / "database" / "database_general.json"
        self.configuration = {}
        self.update_settings()

    def update_settings(self):
        with self.config_path.open("r", encoding="utf-8") as file:
            self.configuration = json.load(file)
        return self.configuration

    def get(self, name, default=None):
        return self.configuration.get(name, default)

    def set(self, name, value, save=True):
        self.configuration[name] = value
        if save:
            self.save()
        return value

    def get_selected(self, section):
        value = self.configuration.get(section, {})
        if isinstance(value, dict):
            return value.get("selected", value.get("status"))
        return value

    def set_selected(self, section, selected, save=True):
        value = self.configuration.setdefault(section, {})
        if not isinstance(value, dict):
            raise ValueError(f"A seção {section} não possui formato de configuração.")
        options = value.get("options")
        if options and selected not in options:
            raise ValueError(f"Valor inválido para {section}: {selected}")
        value["selected"] = selected
        if save:
            self.save()
        return selected

    def get_status_summary(self):
        return {
            "keyword_status": self.get("keyword_status", False),
            "awaiting_duration_status": self.get("awaiting_duration_status", False),
            "chatbot_output": self.get_selected("chatbot_output"),
            "user_input": self.get_selected("user_input"),
            "status_chatbot": self.get_selected("status_chatbot"),
            "status_ai": self.get_selected("status_ai"),
        }

    def save(self):
        with self.config_path.open("w", encoding="utf-8") as file:
            json.dump(self.configuration, file, ensure_ascii=False, indent=4)
        return self.config_path
