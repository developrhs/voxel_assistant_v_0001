import sqlite3
from pathlib import Path


class CommandModeOffice:
    CATEGORIES = {
        "texto": {
            "pular linha": "enter", "saltar linha": "enter", "ponto final": ".",
            "vírgula": ",", "ponto e vírgula": ";", "dois pontos": ":",
            "ponto de exclamação": "!", "ponto de interrogação": "?",
            "abre parênteses": "(", "fecha parênteses": ")", "abre aspas": '"',
            "fecha aspas": '"', "espaço": "space", "apagar": "delete",
            "deletar": "delete", "apagar tudo": "ctrl+a_delete", "desfazer": "ctrl+z",
            "refazer": "ctrl+y",
        },
        "seleção": {
            "selecionar tudo": "ctrl+a", "selecionar palavra": "ctrl+shift+left",
            "selecionar linha": "home_shift+end",
        },
        "formatação": {
            "negrito": "ctrl+b", "deixar negrito": "ctrl+b", "itálico": "ctrl+i",
            "deixar itálico": "ctrl+i", "sublinhado": "ctrl+u", "deixar sublinhado": "ctrl+u",
            "tachado": "strike", "deixar tachado": "strike", "aumentar fonte": "ctrl+shift+>",
            "diminuir fonte": "ctrl+shift+<", "maiúsculo": "upper", "minúsculo": "lower",
        },
        "alinhamento": {
            "alinhar à esquerda": "ctrl+l", "alinhar a esquerda": "ctrl+l",
            "alinhar à direita": "ctrl+r", "alinhar a direita": "ctrl+r",
            "centralizar": "ctrl+e", "alinhamento centralizado": "ctrl+e", "justificar": "ctrl+j",
        },
        "edição": {
            "copiar": "ctrl+c", "copiar conteúdo": "ctrl+c", "colar": "ctrl+v",
            "colar conteúdo": "ctrl+v", "recortar": "ctrl+x", "recortar conteúdo": "ctrl+x",
            "localizar": "ctrl+f", "buscar": "ctrl+f", "substituir": "ctrl+h",
        },
        "arquivo": {
            "salvar": "ctrl+s", "salvar arquivo": "ctrl+s", "salvar como": "f12",
            "salvar novo": "f12", "novo arquivo": "ctrl+n", "abrir arquivo": "ctrl+o",
            "fechar arquivo": "ctrl+w", "imprimir": "ctrl+p",
        },
        "revisão": {
            "correção ortográfica": "f7", "ortografia": "f7",
            "dicionário de sinônimos": "synonyms", "contar palavras": "word_count",
        },
        "lista": {
            "lista com marcadores": "bullets", "lista numerada": "numbering",
            "aumentar recuo": "tab", "diminuir recuo": "shift+tab",
        },
        "navegação": {
            "ir para o início": "ctrl+home", "ir para o fim": "ctrl+end",
            "próxima página": "pagedown", "página anterior": "pageup",
            "início da linha": "home", "fim da linha": "end",
        },
    }

    def __init__(self, project_root=None, keyboard_backend=None):
        self.project_root = Path(project_root) if project_root else Path(__file__).resolve().parents[2]
        self.database_path = self.project_root / "config" / "database" / "db" / "db_virtual_assistant.db"
        self.keyboard = keyboard_backend
        self.active = False

    def find_activation(self, keyword):
        with sqlite3.connect(self.database_path) as connection:
            return connection.execute(
                """
                SELECT tb_condition_response
                FROM tb_condition
                WHERE LOWER(tb_condition_key) = LOWER(?)
                  AND tb_condition_status = 'ativo'
                LIMIT 1
                """,
                (str(keyword).strip(),),
            ).fetchone()

    def activate(self, keyword):
        condition = self.find_activation(keyword)
        self.active = True
        return {
            "status": "OFFICE_MODE_ACTIVE",
            "message": condition[0] if condition else "Modo Office ativado.",
        }

    @staticmethod
    def _normalize(text):
        return " ".join(str(text).strip().lower().split())

    def help(self, category=None):
        if category:
            selected = {category: self.CATEGORIES.get(category, {})}
        else:
            selected = self.CATEGORIES
        lines = ["Comandos disponíveis no Modo Office:"]
        for name, commands in selected.items():
            if commands:
                lines.append(f"{name.title()}: " + ", ".join(sorted(commands)))
        lines.append("Deseja ouvir todos os comandos ou alguma categoria específica?")
        return "\n".join(lines)

    def _find_action(self, command):
        for category, commands in self.CATEGORIES.items():
            if command in commands:
                return category, commands[command]
        return None, None

    def _perform(self, action, text=None):
        if self.keyboard is None:
            return {"action": action, "text": text}
        if action == "enter":
            self.keyboard.press("enter")
        elif action == "space":
            self.keyboard.press("space")
        elif action == "delete":
            self.keyboard.press("delete")
        elif action == "ctrl+a_delete":
            self.keyboard.hotkey("ctrl", "a")
            self.keyboard.press("delete")
        elif "+" in action:
            self.keyboard.hotkey(*action.split("+"))
        elif action.startswith("ctrl+"):
            self.keyboard.hotkey("ctrl", action[-1])
        elif action in {"f7", "f12", "pagedown", "pageup", "home", "end", "tab", "shift+tab"}:
            self.keyboard.press(action)
        elif action == "write":
            self.keyboard.write(text or "")
        else:
            self.keyboard.write(text or "")
        return {"action": action, "text": text}

    def process(self, spoken_text):
        command = self._normalize(spoken_text)
        if command in {"desativar modo", "sair do modo office", "desativar modo office"}:
            self.active = False
            return {
                "status": "OFFICE_MODE_INACTIVE",
                "message": "Modo Office desativado. Comandos de voz restaurados",
            }
        if command in {"ajuda modo office", "ajuda office", "listar comandos"}:
            return {"status": "HELP", "message": self.help()}
        if not self.active:
            return {"status": "OFFICE_MODE_INACTIVE", "message": "Modo Office não está ativo."}

        category, action = self._find_action(command)
        if action is None:
            self._perform("write", spoken_text)
            return {"status": "TEXT_TYPED", "text": spoken_text}
        if action in {"upper", "lower", "strike", "synonyms", "word_count", "bullets", "numbering"}:
            return {"status": "OFFICE_ACTION", "category": category, "action": action}
        return {"status": "OFFICE_ACTION", "category": category, **self._perform(action)}

    def execute(self, spoken_text):
        return self.process(spoken_text)

    def run(self, spoken_text):
        return self.process(spoken_text)
