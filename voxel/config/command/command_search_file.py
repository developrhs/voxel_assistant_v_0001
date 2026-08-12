import os
import sqlite3
import subprocess
from pathlib import Path


class CommandSearchFile:
    def __init__(self, project_root=None, opener=None):
        self.project_root = Path(project_root) if project_root else Path(__file__).resolve().parents[2]
        self.database_path = self.project_root / "config" / "database" / "db" / "db_virtual_assistant.db"
        self.opener = opener
        self.condition_response = ""
        self.user = None
        self.current_path = None
        self.history = []
        self.items = []

    def find_configuration(self, keyword):
        with sqlite3.connect(self.database_path) as connection:
            condition = connection.execute(
                """
                SELECT tb_condition_response
                FROM tb_condition
                WHERE LOWER(tb_condition_key) = LOWER(?)
                  AND tb_condition_status = 'ativo'
                LIMIT 1
                """,
                (str(keyword).strip(),),
            ).fetchone()
            user = connection.execute(
                """
                SELECT tb_user_salutation, tb_user_first_name
                FROM tb_user
                ORDER BY tb_user_id
                LIMIT 1
                """
            ).fetchone()
        return condition, user

    @staticmethod
    def available_drives():
        if os.name == "nt":
            return [f"{letter}:" for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ" if Path(f"{letter}:/").exists()]
        return [str(Path.cwd().anchor or "/")]

    def start(self, keyword):
        condition, user = self.find_configuration(keyword)
        if condition is None:
            return {"status": "CONDITION_NOT_FOUND", "message": "Comando de pesquisa não encontrado."}
        self.condition_response = condition[0]
        self.user = user
        drives = self.available_drives()
        salutation, first_name = user or ("", "")
        options = "\n".join(f"{index}. Diretório {drive}" for index, drive in enumerate(drives, 1))
        return {
            "status": "WAITING_FOR_DIRECTORY",
            "message": f"{salutation} {first_name}, em qual diretório deseja procurar?\n{options}",
            "available_drives": drives,
        }

    def select_directory(self, choice):
        drives = self.available_drives()
        value = str(choice).strip().upper().replace("DIRETÓRIO ", "")
        if value.isdigit():
            index = int(value) - 1
            if index < 0 or index >= len(drives):
                return {"status": "INVALID_DIRECTORY", "message": "Diretório inválido."}
            value = drives[index]
        if not value.endswith(":") and len(value) == 1:
            value += ":"
        if value not in drives:
            return {"status": "INVALID_DIRECTORY", "message": "Diretório inválido."}
        self.current_path = Path(value + "\\") if os.name == "nt" else Path(value)
        self.history = [self.current_path]
        return self._directory_prompt()

    def _directory_prompt(self):
        drive = str(self.current_path)
        return {
            "status": "WAITING_FOR_DIRECTORY_ACTION",
            "message": f"Certo, vamos procurar no Diretório {drive}:\nVocê deseja abrir a pasta ou listar os arquivos?\n1. Abrir pasta\n2. Listar arquivos",
            "path": drive,
        }

    def list_current(self):
        if self.current_path is None:
            return {"status": "DIRECTORY_NOT_SELECTED", "message": "Nenhum diretório selecionado."}
        try:
            entries = sorted(self.current_path.iterdir(), key=lambda item: item.name.lower())
        except OSError as error:
            return {"status": "DIRECTORY_ERROR", "message": str(error)}
        folders = [item for item in entries if item.is_dir()]
        files = [item for item in entries if item.is_file()]
        self.items = folders + files
        lines = ["Pastas:"]
        lines.extend(f"{index}. {item.name}" for index, item in enumerate(folders, 1))
        lines.append("Arquivos:")
        lines.extend(f"{index}. {item.name}" for index, item in enumerate(files, len(folders) + 1))
        salutation, first_name = self.user or ("", "")
        lines.append(f"{salutation} {first_name}, no Diretório {self.current_path}: temos:")
        lines.append("O que deseja fazer?\n1. Abrir pasta ou arquivo (fale o número ou nome)\n2. Parar e abrir esta pasta no Explorer\n3. Cancelar")
        return {"status": "FILES_LISTED", "message": "\n".join(lines), "folders": [item.name for item in folders], "files": [item.name for item in files]}

    def _open(self, path):
        if self.opener:
            self.opener(path)
        elif os.name == "nt":
            if path.is_dir():
                subprocess.Popen(["explorer.exe", str(path)])
            else:
                os.startfile(str(path))
        else:
            raise OSError("A abertura pelo sistema está disponível apenas no Windows.")

    def handle_action(self, choice):
        command = str(choice).strip().lower()
        if command in {"cancelar", "3"}:
            return {"status": "CANCELLED", "message": "Busca cancelada"}
        if command in {"voltar", "back"}:
            if len(self.history) > 1:
                self.history.pop()
                self.current_path = self.history[-1]
            return self._directory_prompt()
        if command in {"parar e abrir esta pasta", "2"}:
            self._open(self.current_path)
            return {"status": "SUCCESS", "message": f"Abrindo {self.current_path}"}
        if command in {"abrir pasta", "1"}:
            self._open(self.current_path)
            return {"status": "SUCCESS", "message": self.condition_response}
        if command in {"listar arquivos", "listar", "2"}:
            return self.list_current()
        if not self.items:
            return {"status": "ITEM_NOT_FOUND", "message": "Nenhum item foi listado."}

        selected = None
        if command.isdigit() and 1 <= int(command) <= len(self.items):
            selected = self.items[int(command) - 1]
        else:
            selected = next((item for item in self.items if item.name.lower() == command), None)
        if selected is None:
            return {"status": "ITEM_NOT_FOUND", "message": "Pasta ou arquivo não encontrado."}
        if selected.is_dir():
            self.current_path = selected
            self.history.append(selected)
            return self._directory_prompt()
        self._open(selected)
        return {"status": "SUCCESS", "message": f"Abrindo arquivo {selected.name}", "path": str(selected)}

    def execute(self, keyword, directory=None, action=None):
        if directory is None:
            return self.start(keyword)
        result = self.select_directory(directory)
        if action is not None:
            return self.handle_action(action)
        return result

    def run(self, keyword, directory=None, action=None):
        return self.execute(keyword, directory, action)
