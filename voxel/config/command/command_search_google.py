import sqlite3
import webbrowser
from pathlib import Path
from urllib.parse import quote_plus


class CommandSearchGoogle:
    BASE_URL = "https://www.google.com/search?q="

    def __init__(self, project_root=None, browser_opener=None):
        self.project_root = Path(project_root) if project_root else Path(__file__).resolve().parents[2]
        self.database_path = self.project_root / "config" / "database" / "db" / "db_virtual_assistant.db"
        self.browser_opener = browser_opener or webbrowser.open

    def find_condition(self, keyword):
        with sqlite3.connect(self.database_path) as connection:
            return connection.execute(
                """
                SELECT tb_condition_question, tb_condition_response
                FROM tb_condition
                WHERE LOWER(tb_condition_key) = LOWER(?)
                  AND tb_condition_status = 'ativo'
                LIMIT 1
                """,
                (str(keyword).strip(),),
            ).fetchone()

    def search(self, keyword, search_term=None):
        condition = self.find_condition(keyword)
        if condition is None:
            return {"status": "CONDITION_NOT_FOUND", "message": "Comando de pesquisa não encontrado."}

        question, response = condition
        if search_term is None or not str(search_term).strip():
            return {
                "status": "WAITING_FOR_SEARCH_TERM",
                "question": question,
            }

        term = str(search_term).strip()
        url = self.BASE_URL + quote_plus(term)
        opened = self.browser_opener(url)
        if not opened:
            return {"status": "BROWSER_ERROR", "message": "Não foi possível abrir o navegador.", "url": url}

        return {
            "status": "SUCCESS",
            "message": str(response).replace("[search_term]", term),
            "search_term": term,
            "url": url,
        }

    def execute(self, keyword, search_term=None):
        return self.search(keyword, search_term)

    def run(self, keyword, search_term=None):
        return self.search(keyword, search_term)
