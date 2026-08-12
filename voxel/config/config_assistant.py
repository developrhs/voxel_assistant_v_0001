import json
import sqlite3
from datetime import datetime
from pathlib import Path


class AssistantConfig:
    def __init__(self, project_root=None):
        self.project_root = Path(project_root) if project_root else Path(__file__).resolve().parents[1]
        self.general_config_path = self.project_root / "config" / "database" / "database_general.json"
        self.database_path = self.project_root / "config" / "database" / "db" / "db_virtual_assistant.db"

        self.keyword_status = False
        self.keyword_master = ""
        self.awaiting_duration_status = False
        self.awaiting_duration = "0s"
        self.waiting_id_command = 0
        self.idle_counter = 0
        self.is_idle_running = False
        self.reload_settings()

    def reload_settings(self):
        with self.general_config_path.open("r", encoding="utf-8") as file:
            settings = json.load(file)

        self.keyword_status = bool(settings.get("keyword_status", False))
        self.keyword_master = str(settings.get("keyword_master", "")).strip()
        self.awaiting_duration_status = bool(settings.get("awaiting_duration_status", False))
        self.awaiting_duration = str(settings.get("awaiting_duration", "0s")).strip()
        self.waiting_id_command = int(settings.get("waiting_id_command", 0))
        return settings

    def parse_awaiting_duration(self):
        duration = self.awaiting_duration.strip().lower()
        if not duration:
            return 0

        unit = duration[-1]
        value = duration[:-1].strip()
        multipliers = {"s": 1, "m": 60, "h": 3600}
        if unit not in multipliers:
            raise ValueError("Formato de tempo de ociosidade inválido.")

        try:
            return int(value) * multipliers[unit]
        except ValueError as error:
            raise ValueError("Valor de tempo de ociosidade inválido.") from error

    def process_user_input(self, text):
        received_text = str(text or "").strip()
        comparison_text = received_text.lower()

        if self.keyword_status:
            keyword = self.keyword_master.strip()
            if not keyword or not comparison_text.startswith(keyword.lower()):
                return {"status": "INTERACTION_IGNORED"}
            command_text = received_text[len(keyword):].strip()
        else:
            command_text = received_text

        self.reset_idle_timer()
        return self._find_command(command_text)

    def process_input(self, text):
        return self.process_user_input(text)

    def _find_command(self, command_text):
        normalized = str(command_text or "").strip()
        with sqlite3.connect(self.database_path) as connection:
            command = connection.execute(
                """
                SELECT tb_command_id, tb_command_key, tb_command_file, tb_command_status
                FROM tb_command
                WHERE LOWER(tb_command_key) = LOWER(?)
                  AND tb_command_status = 'ativo'
                LIMIT 1
                """,
                (normalized,),
            ).fetchone()
            argument_text = ""
            if command is None and normalized:
                command = connection.execute(
                    """
                    SELECT tb_command_id, tb_command_key, tb_command_file, tb_command_status
                    FROM tb_command
                    WHERE tb_command_status = 'ativo'
                      AND LOWER(?) LIKE LOWER(tb_command_key) || '%'
                    ORDER BY LENGTH(tb_command_key) DESC
                    LIMIT 1
                    """,
                    (normalized,),
                ).fetchone()
                if command is not None:
                    argument_text = normalized[len(str(command[1])):].strip()

            if command is None:
                return {
                    "status": "COMMAND_NOT_FOUND",
                    "message": "Comando não encontrado. Diga 'ajuda' para ver a lista de comandos disponíveis.",
                }

            command_id, command_key, script_file, _command_status = command
            conditions = connection.execute(
                """
                SELECT tb_condition_key, tb_condition_question,
                       tb_condition_file, tb_condition_response
                FROM tb_condition
                WHERE tb_condition_tb_command_id = ?
                  AND tb_condition_status = 'ativo'
                """,
                (command_id,),
            ).fetchall()

        return {
            "status": "SUCCESS",
            "command_id": command_id,
            "command_key": command_key,
            "script_file": script_file,
            "argument_text": argument_text,
            "conditions": [
                {
                    "key": row[0],
                    "question": row[1],
                    "file": row[2],
                    "response": row[3],
                }
                for row in conditions
            ],
        }

    def tick_idle_timer(self):
        if not self.awaiting_duration_status:
            return None

        self.idle_counter += 1
        if self.idle_counter >= self.parse_awaiting_duration():
            self.idle_counter = 0
            self.is_idle_running = True
            return self.trigger_idle_command()

        return None

    def trigger_idle_command(self):
        with sqlite3.connect(self.database_path) as connection:
            command = connection.execute(
                """
                SELECT tb_command_file, tb_command_status
                FROM tb_command
                WHERE tb_command_id = ?
                  AND tb_command_status = 'ativo'
                """,
                (self.waiting_id_command,),
            ).fetchone()

        if command is not None:
            return {
                "status": "SUCCESS",
                "script_file": command[0],
            }

        now = datetime.now()
        return {
            "status": "IDLE_FALLBACK",
            "message": f"São {now:%H:%M} do dia {now:%d/%m/%Y}. Posso ajudar em algo?",
        }

    def reset_idle_timer(self):
        self.idle_counter = 0
        self.is_idle_running = False

    def update_timer(self):
        return self.tick_idle_timer()
