import sqlite3
import webbrowser
from pathlib import Path


class CommandOpenSite:
    def __init__(self, project_root=None, browser_opener=None):
        self.project_root = Path(project_root) if project_root else Path(__file__).resolve().parents[2]
        self.database_path = self.project_root / "config" / "database" / "db" / "db_virtual_assistant.db"
        self.browser_opener = browser_opener or webbrowser.open

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

    def open_site(self, keyword):
        condition = self.find_condition(keyword)
        if condition is None:
            return {
                "status": "CONDITION_NOT_FOUND",
                "message": "Site não encontrado.",
            }

        url, response = condition
        if not str(url).lower().startswith(("http://", "https://")):
            return {
                "status": "INVALID_URL",
                "message": "A URL cadastrada é inválida.",
                "url": url,
            }

        opened = self.browser_opener(url)
        if not opened:
            return {
                "status": "BROWSER_ERROR",
                "message": "Não foi possível abrir o navegador.",
                "url": url,
            }

        return {
            "status": "SUCCESS",
            "message": response,
            "url": url,
        }

    def execute(self, keyword):
        return self.open_site(keyword)

    def run(self, keyword):
        return self.open_site(keyword)
