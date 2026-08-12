import os
import sqlite3
import subprocess
from pathlib import Path


AUDIO_EXTENSIONS = {".mp3", ".wma", ".wav", ".flac", ".aac", ".ogg"}


class CommandPlay:
    def __init__(self, project_root=None):
        self.project_root = Path(project_root) if project_root else Path(__file__).resolve().parents[2]
        self.database_path = self.project_root / "config" / "database" / "db" / "db_virtual_assistant.db"

    def find_condition(self, keyword):
        with sqlite3.connect(self.database_path) as connection:
            return connection.execute(
                """
                SELECT tb_condition_file, tb_condition_response
                FROM tb_condition
                WHERE LOWER(tb_condition_key) = LOWER(?)
                  AND tb_condition_status = 'ativo'
                LIMIT 1
                """,
                (str(keyword).strip(),),
            ).fetchone()

    def find_audio_files(self, music_folder):
        folder = Path(music_folder).expanduser()
        if not folder.is_dir():
            return []

        return sorted(
            (file for file in folder.iterdir() if file.is_file() and file.suffix.lower() in AUDIO_EXTENSIONS),
            key=lambda file: file.name.lower(),
        )

    def play(self, keyword):
        condition = self.find_condition(keyword)
        if condition is None:
            return {
                "status": "CONDITION_NOT_FOUND",
                "message": "Playlist não encontrada.",
                "files": [],
            }

        music_folder, response = condition
        audio_files = self.find_audio_files(music_folder)
        if not audio_files:
            return {
                "status": "AUDIO_FILES_NOT_FOUND",
                "message": "Nenhum arquivo de áudio encontrado na pasta configurada.",
                "files": [],
            }

        file_paths = [str(file) for file in audio_files]
        if os.name == "nt":
            subprocess.Popen(["wmplayer.exe", *file_paths])
        else:
            raise OSError("Windows Media Player está disponível apenas no Windows.")

        return {
            "status": "SUCCESS",
            "message": response,
            "files": file_paths,
        }

    def execute(self, keyword):
        return self.play(keyword)
