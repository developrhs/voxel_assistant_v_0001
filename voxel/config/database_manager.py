import json
import os
import sqlite3
import threading
from datetime import datetime
from pathlib import Path


class DatabaseManager:
    def __init__(self, project_root=None, db_path=None, json_path=None):
        self.project_root = Path(project_root) if project_root else Path(__file__).resolve().parent
        self.db_path = Path(db_path) if db_path else self.project_root / "config" / "database" / "db" / "db_virtual_assistant.db"
        self.json_path = Path(json_path) if json_path else self.project_root / "config" / "database" / "database_general.json"
        self._lock = threading.RLock()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.json_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_database()

    def _ensure_database(self):
        if self.db_path.exists():
            return
        with self._lock, sqlite3.connect(self.db_path) as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS tb_user (
                    tb_user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tb_user_salutation TEXT, tb_user_first_name TEXT, tb_user_last_name TEXT,
                    tb_user_username TEXT, tb_user_nationality TEXT, tb_user_place_of_birth TEXT,
                    tb_user_city TEXT, tb_user_state TEXT, tb_user_email TEXT,
                    tb_user_whatsapp TEXT, tb_user_status TEXT
                );
                CREATE TABLE IF NOT EXISTS tb_command (
                    tb_command_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tb_command_key TEXT, tb_command_file TEXT, tb_command_response TEXT,
                    tb_command_status TEXT
                );
                CREATE TABLE IF NOT EXISTS tb_condition (
                    tb_condition_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tb_condition_tb_command_id INTEGER, tb_condition_key TEXT,
                    tb_condition_question TEXT, tb_condition_file TEXT,
                    tb_condition_response TEXT, tb_condition_status TEXT
                );
                CREATE TABLE IF NOT EXISTS tb_chat (
                    tb_chat_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tb_chat_tb_user_id INTEGER, tb_chat_title TEXT,
                    tb_chat_create_date TEXT, tb_chat_create_time TEXT,
                    tb_chat_modify_date TEXT, tb_chat_modify_time TEXT,
                    tb_chat_log_text TEXT
                );
            """)

    def _connection(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def read_general_json(self):
        with self._lock:
            with self.json_path.open("r", encoding="utf-8") as file:
                return json.load(file)

    def get_json_config(self, key_path=None):
        data = self.read_general_json()
        if key_path is None:
            return data
        value = data
        for key in str(key_path).split("."):
            if not isinstance(value, dict) or key not in value:
                return None
            value = value[key]
        return value

    def get_json_value(self, key_path):
        return self.get_json_config(key_path)

    def update_json_config(self, key_path, new_value):
        with self._lock:
            data = self.read_general_json()
            keys = str(key_path).split(".")
            current = data
            for key in keys[:-1]:
                if key not in current or not isinstance(current[key], dict):
                    current[key] = {}
                current = current[key]
            current[keys[-1]] = new_value
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            data["_last_modified"] = timestamp
            data["_ultima_modificacao"] = timestamp
            temporary = self.json_path.with_suffix(self.json_path.suffix + ".tmp")
            with temporary.open("w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=4)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary, self.json_path)
            return True

    def update_json_value(self, key_path, value):
        return self.update_json_config(key_path, value)

    @staticmethod
    def _row_to_dict(row):
        return dict(row) if row else {}

    def get_active_user(self):
        with self._lock, self._connection() as connection:
            row = connection.execute("SELECT * FROM tb_user WHERE tb_user_status = 'ativo' LIMIT 1").fetchone()
            return self._row_to_dict(row)

    def update_user(self, user_id, **kwargs):
        allowed = {"tb_user_salutation", "tb_user_first_name", "tb_user_last_name", "tb_user_username", "tb_user_nationality", "tb_user_place_of_birth", "tb_user_city", "tb_user_state", "tb_user_email", "tb_user_whatsapp", "tb_user_status"}
        fields = {key: value for key, value in kwargs.items() if key in allowed}
        if not fields:
            return False
        assignments = ", ".join(f"{key} = ?" for key in fields)
        with self._lock, self._connection() as connection:
            cursor = connection.execute(f"UPDATE tb_user SET {assignments} WHERE tb_user_id = ?", [*fields.values(), user_id])
            return cursor.rowcount > 0

    def get_command_by_key(self, keyword):
        with self._lock, self._connection() as connection:
            row = connection.execute("SELECT * FROM tb_command WHERE LOWER(tb_command_key) = LOWER(?) AND tb_command_status = 'ativo' LIMIT 1", (keyword,)).fetchone()
            return self._row_to_dict(row)

    def list_all_commands(self):
        with self._lock, self._connection() as connection:
            return [dict(row) for row in connection.execute("SELECT * FROM tb_command ORDER BY tb_command_id")]

    def get_conditions_by_command_id(self, command_id):
        with self._lock, self._connection() as connection:
            return [dict(row) for row in connection.execute("SELECT * FROM tb_condition WHERE tb_condition_tb_command_id = ? ORDER BY tb_condition_id", (command_id,))]

    def get_condition_by_key(self, keyword):
        with self._lock, self._connection() as connection:
            row = connection.execute("SELECT * FROM tb_condition WHERE LOWER(tb_condition_key) = LOWER(?) AND tb_condition_status = 'ativo' LIMIT 1", (keyword,)).fetchone()
            return self._row_to_dict(row)

    def create_chat_session(self, user_id, title="Novo Chat"):
        now = datetime.now()
        date_text, time_text = now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S")
        with self._lock, self._connection() as connection:
            cursor = connection.execute("""
                INSERT INTO tb_chat (tb_chat_tb_user_id, tb_chat_title, tb_chat_create_date,
                tb_chat_create_time, tb_chat_modify_date, tb_chat_modify_time, tb_chat_log_text)
                VALUES (?, ?, ?, ?, ?, ?, '')
            """, (user_id, title, date_text, time_text, date_text, time_text))
            return cursor.lastrowid

    def update_chat_log(self, chat_id, log_text):
        now = datetime.now()
        with self._lock, self._connection() as connection:
            cursor = connection.execute("""
                UPDATE tb_chat SET tb_chat_log_text = tb_chat_log_text || ?,
                tb_chat_modify_date = ?, tb_chat_modify_time = ? WHERE tb_chat_id = ?
            """, (str(log_text), now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"), chat_id))
            return cursor.rowcount > 0

    def append_chat_log(self, chat_id, new_log_text):
        return self.update_chat_log(chat_id, new_log_text)
