"""Camada SQLite do command_vision."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from ..config_vision import SQLITE_FILE, ensure_directories

SCHEMA = """
CREATE TABLE IF NOT EXISTS tb_capture (
    tb_capture_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tb_capture_name TEXT NOT NULL UNIQUE,
    tb_capture_x INTEGER NOT NULL,
    tb_capture_y INTEGER NOT NULL,
    tb_capture_width INTEGER NOT NULL,
    tb_capture_height INTEGER NOT NULL,
    tb_capture_monitor INTEGER NOT NULL DEFAULT 1,
    tb_capture_description TEXT,
    tb_capture_created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS tb_color (
    tb_color_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tb_color_name TEXT NOT NULL UNIQUE,
    tb_color_r INTEGER NOT NULL,
    tb_color_g INTEGER NOT NULL,
    tb_color_b INTEGER NOT NULL,
    tb_color_tolerance INTEGER NOT NULL DEFAULT 20,
    tb_color_minimum_pixels INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS tb_profile (
    tb_profile_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tb_profile_name TEXT NOT NULL UNIQUE,
    tb_profile_active INTEGER NOT NULL DEFAULT 0,
    tb_profile_debounce_ms INTEGER NOT NULL DEFAULT 500,
    tb_profile_description TEXT
);
CREATE TABLE IF NOT EXISTS tb_profile_tb_capture (
    tb_profile_tb_capture_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tb_profile_tb_capture_tb_profile_id INTEGER NOT NULL,
    tb_profile_tb_capture_tb_capture_id INTEGER NOT NULL,
    UNIQUE(tb_profile_tb_capture_tb_profile_id, tb_profile_tb_capture_tb_capture_id),
    FOREIGN KEY(tb_profile_tb_capture_tb_profile_id) REFERENCES tb_profile(tb_profile_id),
    FOREIGN KEY(tb_profile_tb_capture_tb_capture_id) REFERENCES tb_capture(tb_capture_id)
);
CREATE TABLE IF NOT EXISTS tb_profile_tb_color (
    tb_profile_tb_color_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tb_profile_tb_color_tb_profile_id INTEGER NOT NULL,
    tb_profile_tb_color_tb_color_id INTEGER NOT NULL,
    UNIQUE(tb_profile_tb_color_tb_profile_id, tb_profile_tb_color_tb_color_id),
    FOREIGN KEY(tb_profile_tb_color_tb_profile_id) REFERENCES tb_profile(tb_profile_id),
    FOREIGN KEY(tb_profile_tb_color_tb_color_id) REFERENCES tb_color(tb_color_id)
);
CREATE TABLE IF NOT EXISTS tb_command (
    tb_command_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tb_command_name TEXT NOT NULL UNIQUE,
    tb_command_type TEXT NOT NULL CHECK(tb_command_type IN ('keyboard', 'joystick')),
    tb_command_key_code TEXT,
    tb_command_joystick_button INTEGER,
    tb_command_hold_ms INTEGER NOT NULL DEFAULT 100,
    tb_command_cooldown_ms INTEGER NOT NULL DEFAULT 1000,
    tb_command_enabled INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS tb_profile_tb_command (
    tb_profile_tb_command_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tb_profile_tb_command_tb_profile_id INTEGER NOT NULL,
    tb_profile_tb_command_tb_command_id INTEGER NOT NULL,
    UNIQUE(tb_profile_tb_command_tb_profile_id, tb_profile_tb_command_tb_command_id),
    FOREIGN KEY(tb_profile_tb_command_tb_profile_id) REFERENCES tb_profile(tb_profile_id),
    FOREIGN KEY(tb_profile_tb_command_tb_command_id) REFERENCES tb_command(tb_command_id)
);
CREATE TABLE IF NOT EXISTS tb_detection (
    tb_detection_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tb_detection_tb_profile_id INTEGER NOT NULL,
    tb_detection_match INTEGER NOT NULL,
    tb_detection_matching_pixels INTEGER NOT NULL,
    tb_detection_created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(tb_detection_tb_profile_id) REFERENCES tb_profile(tb_profile_id)
);
"""


def connect(path: Path = SQLITE_FILE) -> sqlite3.Connection:
    ensure_directories()
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database() -> Path:
    with connect() as connection:
        connection.executescript(SCHEMA)
    return SQLITE_FILE


def insert(table: str, values: dict[str, Any]) -> int:
    allowed = {key: value for key, value in values.items() if key.startswith(table + "_")}
    columns = ", ".join(allowed)
    placeholders = ", ".join("?" for _ in allowed)
    with connect() as connection:
        cursor = connection.execute(f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", tuple(allowed.values()))
        return int(cursor.lastrowid)
