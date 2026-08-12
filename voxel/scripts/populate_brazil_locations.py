from __future__ import annotations

import csv
import io
import json
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "config" / "database" / "db" / "db_virtual_assistant.db"
IBGE_BASE = "https://servicodados.ibge.gov.br/api/v1/localidades"
FALLBACK_CSV = "https://raw.githubusercontent.com/kelvins/municipios-brasileiros/master/csv/municipios.csv"
UF_BY_CODE = {11: "RO", 12: "AC", 13: "AM", 14: "RR", 15: "PA", 16: "AP", 17: "TO", 21: "MA", 22: "PI", 23: "CE", 24: "RN", 25: "PB", 26: "PE", 27: "AL", 28: "SE", 29: "BA", 31: "MG", 32: "ES", 33: "RJ", 35: "SP", 41: "PR", 42: "SC", 43: "RS", 50: "MS", 51: "MT", 52: "GO", 53: "DF"}


def fetch_json(url: str):
    request = Request(url, headers={"User-Agent": "VOXEL/1.0"})
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")


def ensure_schema(connection: sqlite3.Connection) -> None:
    connection.execute("""
        CREATE TABLE IF NOT EXISTS tb_local (
            tb_local_id INTEGER PRIMARY KEY AUTOINCREMENT,
            tb_local_city TEXT NOT NULL,
            tb_local_state TEXT NOT NULL,
            tb_local_ibge_url TEXT NOT NULL,
            UNIQUE(tb_local_city, tb_local_state)
        )
    """)
    columns = {row[1] for row in connection.execute("PRAGMA table_info(tb_user)")}
    if "tb_user_photo_path" not in columns:
        connection.execute("ALTER TABLE tb_user ADD COLUMN tb_user_photo_path TEXT")


def seed_locations(connection: sqlite3.Connection) -> int:
    inserted = 0
    try:
        states = fetch_json(f"{IBGE_BASE}/estados?orderBy=nome")
        rows = []
        for state in states:
            municipalities = fetch_json(f"{IBGE_BASE}/estados/{state['id']}/municipios?orderBy=nome")
            rows.extend((municipality["nome"], state["sigla"], f"{IBGE_BASE}/municipios/{municipality['id']}") for municipality in municipalities)
    except Exception as error:
        print(f"VOXEL: API IBGE indisponível ({error}); usando CSV de referência com códigos IBGE.")
        request = Request(FALLBACK_CSV, headers={"User-Agent": "VOXEL/1.0"})
        with urlopen(request, timeout=60) as response:
            reader = csv.DictReader(io.TextIOWrapper(response, encoding="utf-8"))
            rows = []
            for row in reader:
                code = int(row["codigo_ibge"])
                uf = UF_BY_CODE[code // 100000]
                rows.append((row["nome"], uf, f"{IBGE_BASE}/municipios/{code}"))
    for name, uf, api_url in rows:
        before = connection.total_changes
        connection.execute("INSERT OR IGNORE INTO tb_local (tb_local_city, tb_local_state, tb_local_ibge_url) VALUES (?, ?, ?)", (name, uf, api_url))
        if connection.total_changes > before:
            inserted += 1
    return inserted


def seed_user(connection: sqlite3.Connection) -> int:
    values = {
        "tb_user_salutation": "senhor",
        "tb_user_first_name": "Rodrigo",
        "tb_user_last_name": "Honório da Silva",
        "tb_user_username": "honorio.rhs",
        "tb_user_nationality": "Brasileiro",
        "tb_user_place_of_birth": "São Paulo-SP",
        "tb_user_city": "Rio Quente",
        "tb_user_state": "GO",
        "tb_user_email": "honorio.rhs@gmail.com",
        "tb_user_whatsapp": "(64) 99272-0965",
        "tb_user_status": "active",
        "tb_user_photo_path": str(ROOT / "arquivos" / "honorio.rhs" / "img"),
    }
    columns = ", ".join(values)
    placeholders = ", ".join("?" for _ in values)
    existing = connection.execute("SELECT tb_user_id FROM tb_user WHERE tb_user_username=?", (values["tb_user_username"],)).fetchone()
    if existing:
        assignments = ", ".join(f"{column}=?" for column in values)
        connection.execute(f"UPDATE tb_user SET {assignments} WHERE tb_user_id=?", (*values.values(), existing[0]))
        return int(existing[0])
    cursor = connection.execute(f"INSERT INTO tb_user ({columns}) VALUES ({placeholders})", tuple(values.values()))
    return int(cursor.lastrowid)


def main() -> int:
    print("VOXEL: a preparar tb_local e dados de utilizador...")
    with sqlite3.connect(DB_PATH) as connection:
        ensure_schema(connection)
        inserted = seed_locations(connection)
        user_id = seed_user(connection)
        connection.commit()
    image_dir = ROOT / "arquivos" / "honorio.rhs" / "img"
    image_dir.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        total = connection.execute("SELECT COUNT(*) FROM tb_local").fetchone()[0]
    print(f"VOXEL: {inserted} municípios novos; {total} municípios totais em tb_local.")
    print(f"VOXEL: utilizador honório.rhs disponível com id {user_id}.")
    print(f"VOXEL: pasta de fotografia: {image_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
