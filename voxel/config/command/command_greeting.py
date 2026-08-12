import sqlite3
from datetime import datetime
from pathlib import Path


class CommandGreeting:
    def __init__(self, project_root=None):
        self.project_root = Path(project_root) if project_root else Path(__file__).resolve().parents[2]
        self.database_path = self.project_root / "config" / "database" / "db" / "db_virtual_assistant.db"

    def get_user(self):
        with sqlite3.connect(self.database_path) as connection:
            return connection.execute(
                """
                SELECT tb_user_salutation, tb_user_first_name
                FROM tb_user
                ORDER BY tb_user_id
                LIMIT 1
                """
            ).fetchone()

    @staticmethod
    def get_greeting(hour):
        hour = int(hour)
        if 6 <= hour < 12:
            return "Bom dia", ""
        if 12 <= hour < 18:
            return "Boa tarde", ""
        if 18 <= hour <= 23:
            return "Boa noite", ""
        return "Boa noite", "Está de madrugada, seria bom descansar um pouco!"

    def execute(self, now=None):
        user = self.get_user()
        if user is None:
            return {"status": "USER_NOT_FOUND", "message": "Usuário não encontrado."}

        now = now or datetime.now()
        greeting, addition = self.get_greeting(now.hour)
        message = f"{greeting} {user[0]} {user[1]}, são {now:%H:%M:%S}"
        if addition:
            message += f". {addition}"

        return {
            "status": "SUCCESS",
            "message": message,
            "hour": now.strftime("%H:%M:%S"),
            "greeting": greeting,
            "addition_response": addition,
        }

    def run(self, now=None):
        return self.execute(now)
