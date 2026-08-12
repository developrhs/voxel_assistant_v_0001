from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "config" / "database" / "db" / "db_virtual_assistant.db"

COMMANDS = [
    ("tocar música", "command_play.py", "Vou tocar a música solicitada."),
    ("clima", "command_weather.py", "Vou consultar o clima atual."),
    ("boletim meteorológico", "command_weather_full.py", "Vou preparar o boletim meteorológico completo."),
    ("saudação", "command_greeting.py", "Saudação personalizada pronta."),
    ("modo office", "command_mode_office.py", "Modo Office ativado."),
    ("abrir pasta", "command_open", "Abrindo a pasta configurada."),
    ("abrir site", "command_open_site.py", "Abrindo o site configurado."),
    ("executar programa", "command_run.py", "Abrindo o programa configurado."),
    ("pesquisar no google", "command_search_google.py", "Pesquisando [search_term] no Google."),
    ("pesquisar arquivo no computador", "command_search_file.py", "Iniciando a pesquisa de arquivos no computador."),
    ("pesquisar no mapa", "command_search_maps.py", "Procurando [search_term] no mapa."),
    ("pesquisar na wikipedia", "command_search_wikipedia.py", "Abrindo o artigo sobre [search_term] na Wikipedia."),
    ("pesquisar no youtube", "command_search_youtube.py", "Procurando [search_term] no YouTube."),
]

CONDITIONS = {
    "tocar música": {"question": "Qual música ou playlist você deseja tocar?", "file": "D:/assistant/voxel/files/user/music", "response": "Tocando [search_term]"},
    "clima": {"question": "Vou consultar o clima da sua cidade.", "file": "", "response": "Clima atual consultado."},
    "boletim meteorológico": {"question": "Vou consultar o boletim meteorológico da sua cidade.", "file": "", "response": "Boletim meteorológico gerado."},
    "saudação": {"question": "", "file": "", "response": "Saudação personalizada apresentada."},
    "modo office": {"question": "Deseja ativar o Modo Office?", "file": "", "response": "Modo Office ativado."},
    "abrir pasta": {"question": "Qual pasta configurada você deseja abrir?", "file": "", "response": "Abrindo a pasta configurada."},
    "abrir site": {"question": "Qual site configurado você deseja abrir?", "file": "https://gemini.google.com", "response": "Abrindo o site configurado."},
    "executar programa": {"question": "Qual programa configurado você deseja executar?", "file": "C:/Program Files/Notepad++/notepad++.exe", "response": "Abrindo o programa configurado."},
    "pesquisar no google": {"question": "O que você deseja pesquisar no Google?", "file": "https://www.google.com/search?q=", "response": "Pesquisando [search_term] no Google."},
    "pesquisar arquivo no computador": {"question": "Qual arquivo ou pasta você deseja pesquisar no computador?", "file": "", "response": "Pesquisa de arquivos iniciada."},
    "pesquisar no mapa": {"question": "Qual local você deseja procurar no mapa?", "file": "https://www.google.com/maps/search/", "response": "Procurando [search_term] no mapa."},
    "pesquisar na wikipedia": {"question": "O que você deseja pesquisar na Wikipedia?", "file": "https://pt.wikipedia.org/wiki/", "response": "Abrindo artigo sobre [search_term] na Wikipedia."},
    "pesquisar no youtube": {"question": "O que você deseja pesquisar no YouTube?", "file": "https://www.youtube.com/results?search_query=", "response": "Procurando [search_term] no YouTube."},
}


def seed() -> tuple[int, int]:
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        command_ids: dict[str, int] = {}
        for key, file_name, response in COMMANDS:
            existing = connection.execute("SELECT tb_command_id FROM tb_command WHERE tb_command_key=?", (key,)).fetchone()
            if existing:
                command_id = existing[0]
                connection.execute("UPDATE tb_command SET tb_command_file=?, tb_command_response=?, tb_command_status='ativo' WHERE tb_command_id=?", (file_name, response, command_id))
            else:
                cursor = connection.execute("INSERT INTO tb_command (tb_command_key,tb_command_file,tb_command_response,tb_command_status) VALUES (?,?,?,'ativo')", (key, file_name, response))
                command_id = cursor.lastrowid
            command_ids[key] = command_id
            connection.execute("DELETE FROM tb_condition WHERE tb_condition_tb_command_id=?", (command_id,))
            condition = CONDITIONS[key]
            connection.execute("INSERT INTO tb_condition (tb_condition_tb_command_id,tb_condition_key,tb_condition_question,tb_condition_file,tb_condition_response,tb_condition_status) VALUES (?,?,?,?,?,'ativo')", (command_id, key, condition["question"], condition["file"], condition["response"]))
        connection.commit()
        command_count = connection.execute("SELECT COUNT(*) FROM tb_command").fetchone()[0]
        condition_count = connection.execute("SELECT COUNT(*) FROM tb_condition").fetchone()[0]
    return command_count, condition_count


if __name__ == "__main__":
    commands, conditions = seed()
    print(f"VOXEL: {commands} comandos cadastrados.")
    print(f"VOXEL: {conditions} condições cadastradas e relacionadas.")
