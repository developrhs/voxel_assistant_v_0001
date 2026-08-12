"""Gestor compatível de perfis, mapeamentos e gatilhos do VOXEL.

Mantém a nomenclatura atual ``controler_config``/``tb_*controler*`` e aceita
os aliases do estudo ``configuracao_controle``/``tb_*controle*`` no JSON.
A captura física de eventos permanece opcional; este módulo fornece a camada
segura de carregamento, filtragem e resolução para listeners ou para a GUI.
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any


class ControlerConfig:
    TRIGGER_MODES = ("TECLA_UNICA", "HOTKEY", "SEQUENCIA")

    def __init__(self, project_root: str | Path | None = None, db_path: str | Path | None = None, json_path: str | Path | None = None):
        root = Path(project_root) if project_root else Path(__file__).resolve().parents[1]
        self.db_path = Path(db_path) if db_path else root / "config" / "database" / "db" / "db_virtual_assistant.db"
        self.json_path = Path(json_path) if json_path else root / "config" / "database" / "database_general.json"
        self.buffer: list[str] = []
        self.last_trigger_at = 0.0
        self.ensure_schema()
        self._ensure_active_profile()

    def _connect(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def ensure_schema(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS tb_perfil_controler (
                    tb_perfil_controler_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tb_perfil_controler_name TEXT NOT NULL UNIQUE,
                    tb_perfil_controler_description TEXT DEFAULT '',
                    tb_perfil_controler_type TEXT DEFAULT 'keyboard',
                    tb_perfil_controler_status TEXT DEFAULT 'active',
                    tb_perfil_controler_created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS tb_perfil_controler_map (
                    tb_perfil_controler_map_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tb_perfil_controler_id INTEGER NOT NULL,
                    tb_perfil_controler_input_type TEXT NOT NULL,
                    tb_perfil_controler_input_key TEXT NOT NULL,
                    tb_perfil_controler_command_id INTEGER NOT NULL,
                    tb_perfil_controler_action TEXT DEFAULT '',
                    tb_perfil_controler_status TEXT DEFAULT 'active',
                    tb_perfil_controler_trigger_mode TEXT DEFAULT 'TECLA_UNICA',
                    tb_perfil_controler_trigger TEXT DEFAULT '',
                    tb_perfil_controler_parameters TEXT DEFAULT '',
                    tb_perfil_controler_timeout_seconds REAL DEFAULT 3.0,
                    UNIQUE(tb_perfil_controler_id, tb_perfil_controler_input_type, tb_perfil_controler_input_key),
                    FOREIGN KEY(tb_perfil_controler_id) REFERENCES tb_perfil_controler(tb_perfil_controler_id),
                    FOREIGN KEY(tb_perfil_controler_command_id) REFERENCES tb_command(tb_command_id)
                );
            """)
            existing = {row[1] for row in connection.execute("PRAGMA table_info(tb_perfil_controler_map)")}
            migrations = {
                "tb_perfil_controler_trigger_mode": "TEXT DEFAULT 'TECLA_UNICA'",
                "tb_perfil_controler_trigger": "TEXT DEFAULT ''",
                "tb_perfil_controler_parameters": "TEXT DEFAULT ''",
                "tb_perfil_controler_timeout_seconds": "REAL DEFAULT 3.0",
            }
            for column, definition in migrations.items():
                if column not in existing:
                    connection.execute(f"ALTER TABLE tb_perfil_controler_map ADD COLUMN {column} {definition}")
            connection.execute("UPDATE tb_perfil_controler_map SET tb_perfil_controler_trigger=tb_perfil_controler_input_key WHERE COALESCE(tb_perfil_controler_trigger, '')=''")
            connection.execute("INSERT OR IGNORE INTO tb_perfil_controler (tb_perfil_controler_name, tb_perfil_controler_description, tb_perfil_controler_type) VALUES ('Padrão', 'Perfil inicial de controlos do VOXEL', 'keyboard')")

    def _ensure_active_profile(self) -> None:
        data = self.read_settings()
        current = dict(data.get('controler_config') or {})
        study = dict(data.get('configuracao_controle') or {})
        if current.get('active_profile_id') or study.get('perfil_ativo_id'):
            return
        profile = next((item for item in self.profiles() if item.get('tb_perfil_controler_status', 'active') == 'active'), None)
        if not profile:
            return
        current['active_profile_id'] = profile['tb_perfil_controler_id']
        current['active_profile_name'] = profile['tb_perfil_controler_name']
        self._save_settings(current)

    def read_settings(self) -> dict[str, Any]:
        try:
            return json.loads(self.json_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def settings(self) -> dict[str, Any]:
        data = self.read_settings()
        current = dict(data.get("controler_config") or {})
        study = dict(data.get("configuracao_controle") or {})
        aliases = {
            "enabled": ("controle_ativo", True),
            "active_profile_id": ("perfil_ativo_id", None),
            "active_profile_name": ("perfil_ativo_nome", "Padrão"),
            "joystick_device": ("dispositivo_joystick_id", None),
            "joystick_deadzone": ("deadzone_joystick", 0.15),
            "block_system_keys": ("bloquear_teclas_sistema", False),
            "combo_timeout_seconds": ("combo_timeout_segundos", 3.0),
        }
        for current_key, (study_key, default) in aliases.items():
            if current.get(current_key) is None and study.get(study_key) is not None:
                current[current_key] = study[study_key]
            current.setdefault(current_key, default)
        current.setdefault("keyboard_enabled", study.get("teclado_ativo", True))
        current.setdefault("joystick_enabled", study.get("joystick_ativo", False))
        current.setdefault("input_mode", study.get("modo_entrada", "keyboard"))
        current.setdefault("trigger_precedence", ["SEQUENCIA", "HOTKEY", "TECLA_UNICA"])
        return current

    def _save_settings(self, current: dict[str, Any]) -> None:
        data = self.read_settings()
        data["controler_config"] = current
        data["configuracao_controle"] = {
            "controle_ativo": bool(current.get("enabled", True)),
            "perfil_ativo_id": current.get("active_profile_id"),
            "perfil_ativo_nome": current.get("active_profile_name", "Padrão"),
            "dispositivo_joystick_id": current.get("joystick_device"),
            "dispositivo_joystick_opcoes": data.get("configuracao_controle", {}).get("dispositivo_joystick_opcoes", []),
            "deadzone_joystick": float(current.get("joystick_deadzone", 0.15)),
            "bloquear_teclas_sistema": bool(current.get("block_system_keys", False)),
            "combo_timeout_segundos": float(current.get("combo_timeout_seconds", 3.0)),
            "modo_entrada": current.get("input_mode", "keyboard"),
            "teclado_ativo": bool(current.get("keyboard_enabled", True)),
            "joystick_ativo": bool(current.get("joystick_enabled", False)),
            "precedencia_gatilhos": current.get("trigger_precedence", ["SEQUENCIA", "HOTKEY", "TECLA_UNICA"]),
        }
        self.json_path.write_text(json.dumps(data, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")

    def settings_update(self, **values) -> dict[str, Any]:
        current = self.settings()
        current.update(values)
        self._save_settings(current)
        return current

    def profiles(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            return [dict(row) for row in connection.execute("SELECT * FROM tb_perfil_controler ORDER BY tb_perfil_controler_id")]

    def mappings(self, profile_id: int | None = None) -> list[dict[str, Any]]:
        query = """SELECT m.*, p.tb_perfil_controler_name, c.tb_command_key, c.tb_command_file
                   FROM tb_perfil_controler_map m
                   JOIN tb_perfil_controler p ON p.tb_perfil_controler_id=m.tb_perfil_controler_id
                   JOIN tb_command c ON c.tb_command_id=m.tb_perfil_controler_command_id"""
        params: tuple[Any, ...] = ()
        if profile_id:
            query += " WHERE m.tb_perfil_controler_id=?"
            params = (profile_id,)
        query += " ORDER BY m.tb_perfil_controler_map_id"
        with self._connect() as connection:
            return [dict(row) for row in connection.execute(query, params)]

    def create_profile(self, name: str, description: str = '', control_type: str = 'keyboard') -> int:
        with self._connect() as connection:
            cursor = connection.execute("INSERT INTO tb_perfil_controler (tb_perfil_controler_name, tb_perfil_controler_description, tb_perfil_controler_type) VALUES (?, ?, ?)", (name.strip(), description.strip(), control_type))
            return int(cursor.lastrowid)

    def update_profile(self, profile_id: int, name: str, description: str, control_type: str, status: str = 'active') -> bool:
        with self._connect() as connection:
            cursor = connection.execute("UPDATE tb_perfil_controler SET tb_perfil_controler_name=?, tb_perfil_controler_description=?, tb_perfil_controler_type=?, tb_perfil_controler_status=? WHERE tb_perfil_controler_id=?", (name.strip(), description.strip(), control_type, status, profile_id))
            return cursor.rowcount > 0

    def delete_profile(self, profile_id: int) -> bool:
        with self._connect() as connection:
            connection.execute("DELETE FROM tb_perfil_controler_map WHERE tb_perfil_controler_id=?", (profile_id,))
            cursor = connection.execute("DELETE FROM tb_perfil_controler WHERE tb_perfil_controler_id=?", (profile_id,))
            return cursor.rowcount > 0

    def create_mapping(self, profile_id: int, input_type: str, input_key: str, command_id: int, action: str = '', trigger_mode: str = 'TECLA_UNICA', trigger: str | None = None, parameters: str = '', timeout_seconds: float | None = None) -> int:
        trigger_mode = trigger_mode.upper().strip()
        if trigger_mode not in self.TRIGGER_MODES:
            raise ValueError(f"Modo de gatilho inválido: {trigger_mode}")
        trigger = (trigger if trigger is not None else input_key).strip()
        timeout = float(timeout_seconds if timeout_seconds is not None else self.settings().get('combo_timeout_seconds', 3.0))
        with self._connect() as connection:
            cursor = connection.execute("""INSERT INTO tb_perfil_controler_map
                (tb_perfil_controler_id, tb_perfil_controler_input_type, tb_perfil_controler_input_key, tb_perfil_controler_command_id, tb_perfil_controler_action, tb_perfil_controler_trigger_mode, tb_perfil_controler_trigger, tb_perfil_controler_parameters, tb_perfil_controler_timeout_seconds)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", (profile_id, input_type.strip(), input_key.strip(), command_id, action.strip(), trigger_mode, trigger, parameters.strip(), timeout))
            return int(cursor.lastrowid)

    def update_mapping(self, mapping_id: int, profile_id: int, input_type: str, input_key: str, command_id: int, action: str = '', status: str = 'active', trigger_mode: str = 'TECLA_UNICA', trigger: str | None = None, parameters: str = '', timeout_seconds: float | None = None) -> bool:
        trigger_mode = trigger_mode.upper().strip()
        if trigger_mode not in self.TRIGGER_MODES:
            raise ValueError(f"Modo de gatilho inválido: {trigger_mode}")
        trigger = (trigger if trigger is not None else input_key).strip()
        timeout = float(timeout_seconds if timeout_seconds is not None else self.settings().get('combo_timeout_seconds', 3.0))
        with self._connect() as connection:
            cursor = connection.execute("""UPDATE tb_perfil_controler_map SET tb_perfil_controler_id=?, tb_perfil_controler_input_type=?, tb_perfil_controler_input_key=?, tb_perfil_controler_command_id=?, tb_perfil_controler_action=?, tb_perfil_controler_status=?, tb_perfil_controler_trigger_mode=?, tb_perfil_controler_trigger=?, tb_perfil_controler_parameters=?, tb_perfil_controler_timeout_seconds=? WHERE tb_perfil_controler_map_id=?""", (profile_id, input_type.strip(), input_key.strip(), command_id, action.strip(), status, trigger_mode, trigger, parameters.strip(), timeout, mapping_id))
            return cursor.rowcount > 0

    def delete_mapping(self, mapping_id: int) -> bool:
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM tb_perfil_controler_map WHERE tb_perfil_controler_map_id=?", (mapping_id,))
            return cursor.rowcount > 0

    def set_active_profile(self, profile_id: int) -> dict[str, Any] | None:
        profile = next((item for item in self.profiles() if item["tb_perfil_controler_id"] == profile_id), None)
        if not profile:
            return None
        current = self.settings()
        current.update(active_profile_id=profile_id, active_profile_name=profile["tb_perfil_controler_name"])
        self._save_settings(current)
        return profile

    @staticmethod
    def _normalize_input(input_type: str, input_key: str) -> tuple[str, str]:
        return str(input_type or '').strip().lower(), str(input_key or '').strip().upper()

    def _active_profile_id(self):
        return self.settings().get('active_profile_id')

    def resolve_action(self, input_type: str, input_key: str) -> dict[str, Any] | None:
        settings = self.settings()
        if not settings.get("enabled", True):
            return None
        input_type, input_key = self._normalize_input(input_type, input_key)
        if input_type == "keyboard" and not settings.get("keyboard_enabled", True):
            return None
        if input_type == "joystick" and not settings.get("joystick_enabled", False):
            return None
        profile_id = self._active_profile_id()
        if not profile_id:
            return None
        with self._connect() as connection:
            row = connection.execute("""SELECT m.*, c.tb_command_key, c.tb_command_file, c.tb_command_response
                FROM tb_perfil_controler_map m JOIN tb_command c ON c.tb_command_id=m.tb_perfil_controler_command_id
                WHERE m.tb_perfil_controler_id=? AND lower(m.tb_perfil_controler_input_type)=lower(?)
                AND (upper(m.tb_perfil_controler_input_key)=upper(?) OR upper(m.tb_perfil_controler_trigger)=upper(?))
                AND m.tb_perfil_controler_status='active' AND c.tb_command_status='ativo' LIMIT 1""", (profile_id, input_type, input_key, input_key)).fetchone()
            return dict(row) if row else None

    def resolve_trigger(self, input_type: str, trigger: str, now: float | None = None) -> dict[str, Any] | None:
        """Resolve tecla única, hotkey ou sequência respeitando timeout e precedência."""
        now = time.monotonic() if now is None else float(now)
        settings = self.settings()
        timeout = float(settings.get('combo_timeout_seconds', 3.0))
        if self.last_trigger_at and now - self.last_trigger_at > timeout:
            self.buffer.clear()
        self.last_trigger_at = now
        normalized = str(trigger or '').strip().upper()
        if not normalized:
            return None
        self.buffer.append(normalized)
        profile_id = self._active_profile_id()
        if not profile_id:
            return None
        mappings = self.mappings(profile_id)
        precedence = settings.get('trigger_precedence', ['SEQUENCIA', 'HOTKEY', 'TECLA_UNICA'])
        candidates = []
        sequence = ','.join(self.buffer)
        for item in mappings:
            mode = str(item.get('tb_perfil_controler_trigger_mode') or 'TECLA_UNICA').upper()
            key = str(item.get('tb_perfil_controler_trigger') or item.get('tb_perfil_controler_input_key') or '').upper()
            if mode == 'SEQUENCIA' and key.replace(' ', '') == sequence.replace(' ', ''):
                candidates.append((precedence.index(mode) if mode in precedence else 99, item))
            elif mode == 'HOTKEY' and key == normalized:
                candidates.append((precedence.index(mode) if mode in precedence else 99, item))
            elif mode == 'TECLA_UNICA' and key == normalized:
                candidates.append((precedence.index(mode) if mode in precedence else 99, item))
        if candidates:
            candidates.sort(key=lambda pair: pair[0])
            self.buffer.clear()
            return candidates[0][1]
        max_size = max([len(str(item.get('tb_perfil_controler_trigger') or '').split(',')) for item in mappings if str(item.get('tb_perfil_controler_trigger_mode') or '').upper() == 'SEQUENCIA'] or [1])
        if len(self.buffer) > max_size:
            self.buffer = self.buffer[-max_size:]
        return None

    def filter_input(self, input_type: str, input_key: str) -> dict[str, Any] | None:
        if not input_type or not input_key:
            return None
        return self.resolve_action(input_type, input_key)


ControllerConfig = ControlerConfig
