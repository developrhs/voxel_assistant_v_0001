import os
import sqlite3
import subprocess
from pathlib import Path


class CommandRun:
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

    def run_program(self, keyword):
        condition = self.find_condition(keyword)
        if condition is None:
            return {"status": "CONDITION_NOT_FOUND", "message": "Programa não encontrado."}

        executable, response = condition
        executable_path = Path(executable).expanduser()
        if executable_path.suffix.lower() != ".exe":
            return {
                "status": "INVALID_EXECUTABLE",
                "message": "O arquivo configurado não é um programa .exe.",
                "path": str(executable_path),
            }
        if not executable_path.is_file():
            return {
                "status": "FILE_NOT_FOUND",
                "message": "O programa configurado não foi encontrado.",
                "path": str(executable_path),
            }
        if os.name != "nt":
            raise OSError("A execução de programas .exe está disponível apenas no Windows.")

        subprocess.Popen([str(executable_path)])
        return {
            "status": "SUCCESS",
            "message": response,
            "path": str(executable_path),
        }

    def execute(self, keyword):
        return self.run_program(keyword)

    def run(self, keyword):
        return self.run_program(keyword)
