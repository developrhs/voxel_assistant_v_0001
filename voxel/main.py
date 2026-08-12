import hashlib
import json
import os
import queue
import secrets
import shutil
import sqlite3
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
try:
    from PIL import Image, ImageTk
except Exception:
    Image = ImageTk = None

ROOT = Path(__file__).resolve().parent

try:
    from config.database_manager import DatabaseManager
except Exception:
    DatabaseManager = None

try:
    from config.config_chatbot import ChatbotConfig
except Exception:
    ChatbotConfig = None

try:
    from config.config_controler import ControlerConfig
except Exception:
    ControlerConfig = None

try:
    from config.support import SupportManager, AudioInputSupport, AudioOutputSupport, LocalAISupport, OnlineAISupport, AssistantSupport
except Exception:
    SupportManager = AudioInputSupport = AudioOutputSupport = LocalAISupport = OnlineAISupport = AssistantSupport = None


class VoxelDatabase:
    # (backend inalterado)
    def __init__(self):
        self.db_path = ROOT / "config" / "database" / "db" / "db_virtual_assistant.db"
        self.json_path = ROOT / "config" / "database" / "database_general.json"
        self.db = DatabaseManager(project_root=ROOT) if DatabaseManager else None
        self.controler = ControlerConfig(project_root=ROOT) if ControlerConfig else None
        with self.connect() as connection:
            columns = {row[1] for row in connection.execute("PRAGMA table_info(tb_user)")}
            if "tb_user_password" not in columns:
                connection.execute("ALTER TABLE tb_user ADD COLUMN tb_user_password TEXT DEFAULT ''")
            if "tb_user_profile" not in columns:
                connection.execute("ALTER TABLE tb_user ADD COLUMN tb_user_profile TEXT DEFAULT 'Padrão'")
            connection.execute("UPDATE tb_user SET tb_user_password='admin123', tb_user_profile='Administrador' WHERE lower(tb_user_username)='honorio.rhs'")
            connection.execute("CREATE TABLE IF NOT EXISTS tb_device_session (tb_device_session_id INTEGER PRIMARY KEY AUTOINCREMENT, tb_device_session_user_id INTEGER NOT NULL, tb_device_session_token_hash TEXT NOT NULL UNIQUE, tb_device_session_created_at TEXT NOT NULL, tb_device_session_expires_at TEXT NOT NULL, tb_device_session_active INTEGER NOT NULL DEFAULT 1)")

    def connect(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def user(self):
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM tb_user WHERE lower(tb_user_status) IN ('ativo', 'active') ORDER BY tb_user_id LIMIT 1").fetchone()
            return dict(row) if row else {}

    def authenticate(self, username, password):
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM tb_user WHERE lower(tb_user_username)=lower(?) AND tb_user_password=? AND lower(tb_user_status) IN ('ativo','active') LIMIT 1", (username, password)).fetchone()
            return dict(row) if row else None

    def commands(self):
        with self.connect() as connection:
            return [dict(row) for row in connection.execute("SELECT * FROM tb_command ORDER BY tb_command_id")]

    def chats(self):
        with self.connect() as connection:
            return [dict(row) for row in connection.execute("SELECT * FROM tb_chat ORDER BY tb_chat_id DESC")]

    def chat(self, chat_id):
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM tb_chat WHERE tb_chat_id=?", (chat_id,)).fetchone()
            return dict(row) if row else {}

    def create_chat(self, user_id, title="VOXEL Chat"):
        now = datetime.now()
        date_text, time_text = now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S")
        with self.connect() as connection:
            cursor = connection.execute("INSERT INTO tb_chat (tb_chat_tb_user_id,tb_chat_title,tb_chat_create_date,tb_chat_create_time,tb_chat_modify_date,tb_chat_modify_time,tb_chat_log_text) VALUES (?,?,?,?,?,?,?)", (user_id, title, date_text, time_text, date_text, time_text, ""))
            return cursor.lastrowid

    def insert_command(self, key, file_name, response):
        with self.connect() as connection:
            cursor = connection.execute("INSERT INTO tb_command (tb_command_key,tb_command_file,tb_command_response,tb_command_status) VALUES (?,?,?,'ativo')", (key, file_name, response))
            return cursor.lastrowid

    def update_command(self, command_id, key, file_name, response, status):
        with self.connect() as connection:
            connection.execute("UPDATE tb_command SET tb_command_key=?,tb_command_file=?,tb_command_response=?,tb_command_status=? WHERE tb_command_id=?", (key, file_name, response, status, command_id))

    def delete_command(self, command_id):
        with self.connect() as connection:
            connection.execute("DELETE FROM tb_condition WHERE tb_condition_tb_command_id=?", (command_id,))
            connection.execute("DELETE FROM tb_command WHERE tb_command_id=?", (command_id,))

    def conditions(self):
        with self.connect() as connection:
            return [dict(row) for row in connection.execute("SELECT * FROM tb_condition ORDER BY tb_condition_id")]

    def insert_condition(self, command_id, key, question, file_name, response, status):
        with self.connect() as connection:
            cursor = connection.execute("INSERT INTO tb_condition (tb_condition_tb_command_id,tb_condition_key,tb_condition_question,tb_condition_file,tb_condition_response,tb_condition_status) VALUES (?,?,?,?,?,?)", (command_id, key, question, file_name, response, status))
            return cursor.lastrowid

    def update_condition(self, condition_id, command_id, key, question, file_name, response, status):
        with self.connect() as connection:
            connection.execute("UPDATE tb_condition SET tb_condition_tb_command_id=?,tb_condition_key=?,tb_condition_question=?,tb_condition_file=?,tb_condition_response=?,tb_condition_status=? WHERE tb_condition_id=?", (command_id, key, question, file_name, response, status, condition_id))

    def delete_condition(self, condition_id):
        with self.connect() as connection:
            connection.execute("DELETE FROM tb_condition WHERE tb_condition_id=?", (condition_id,))

    def users(self):
        with self.connect() as connection:
            return [dict(row) for row in connection.execute("SELECT * FROM tb_user ORDER BY tb_user_id")]

    def local_states(self):
        with self.connect() as connection:
            return [row[0] for row in connection.execute("SELECT DISTINCT tb_local_state FROM tb_local ORDER BY tb_local_state")]

    def local_cities(self, state):
        with self.connect() as connection:
            return [row[0] for row in connection.execute("SELECT tb_local_city FROM tb_local WHERE tb_local_state=? ORDER BY tb_local_city", (state,))]

    def create_user(self, values):
        columns = ("tb_user_salutation", "tb_user_first_name", "tb_user_last_name", "tb_user_username", "tb_user_password", "tb_user_profile", "tb_user_nationality", "tb_user_place_of_birth", "tb_user_city", "tb_user_state", "tb_user_email", "tb_user_whatsapp", "tb_user_status", "tb_user_photo_path")
        with self.connect() as connection:
            cursor = connection.execute(f"INSERT INTO tb_user ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})", tuple(values.get(column, '') for column in columns))
            return cursor.lastrowid

    def update_user_full(self, user_id, values):
        columns = ("tb_user_salutation", "tb_user_first_name", "tb_user_last_name", "tb_user_username", "tb_user_password", "tb_user_profile", "tb_user_nationality", "tb_user_place_of_birth", "tb_user_city", "tb_user_state", "tb_user_email", "tb_user_whatsapp", "tb_user_status", "tb_user_photo_path")
        assignments = ', '.join(f"{column}=?" for column in columns)
        with self.connect() as connection:
            connection.execute(f"UPDATE tb_user SET {assignments} WHERE tb_user_id=?", tuple(values.get(column, '') for column in columns) + (user_id,))

    def delete_user(self, user_id):
        with self.connect() as connection:
            connection.execute("DELETE FROM tb_user WHERE tb_user_id=?", (user_id,))

    def read_config(self):
        with self.json_path.open("r", encoding="utf-8") as stream:
            return json.load(stream)

    def save_config(self, data):
        temporary = self.json_path.with_suffix(".tmp")
        with temporary.open("w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=4)
        temporary.replace(self.json_path)


class VoxelApp(tk.Tk):
    COLORS = {
        "bg": "#0b1220", "panel": "#111c2e", "panel2": "#16243a", "line": "#243957",
        "text": "#e8eef7", "muted": "#91a4bd", "accent": "#35c7a3", "blue": "#4b8cfb",
        "warning": "#f2b84b", "danger": "#e36b7a"
    }

    # Layout: apenas tamanhos, espaçamentos e proporções
    LAYOUT = {
        "outer_padx": 26,         # respiro lateral do conteúdo
        "outer_pady": 16,         # respiro vertical do conteúdo
        "card_padx": 20,          # padding interno do cartão
        "card_pady": 16,
        "row_pady": 6,            # espaçamento entre linhas de formulário
        "header_height": 72,
        "footer_height": 36,
        "sidebar_width": 240,
        "entry_ipady": 6,         # altura extra dos campos de texto
        "button_pady": 6,
    }

    def __init__(self):
        super().__init__()
        self.title("VOXEL System")
        self.geometry("1440x900")
        self.minsize(1100, 700)   # mínimo maior para melhor acomodação
        self.resizable(True, True)
        self.configure(bg=self.COLORS["bg"])
        self.db = VoxelDatabase()
        self.controler = self.db.controler
        self.support = SupportManager(ROOT) if SupportManager else None
        self.support_audio_input = AudioInputSupport(ROOT) if AudioInputSupport else None
        self.support_audio_output = AudioOutputSupport(ROOT) if AudioOutputSupport else None
        self.support_local_ai = LocalAISupport(ROOT) if LocalAISupport else None
        self.support_online_ai = OnlineAISupport(ROOT) if OnlineAISupport else None
        self.support_assistant = AssistantSupport(ROOT) if AssistantSupport else None
        self.user_data = {}
        self.chatbot = None
        self.session_path = ROOT / "arquivos" / ".voxel_device_session"
        self.session_path.parent.mkdir(parents=True, exist_ok=True)
        self._setup_style()
        self.show_login()

    def _setup_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=self.COLORS["bg"])
        style.configure("TLabel", background=self.COLORS["bg"], foreground=self.COLORS["text"], font=("Segoe UI", 10))
        style.configure("Title.TLabel", background=self.COLORS["bg"], foreground=self.COLORS["text"], font=("Segoe UI", 22, "bold"))
        style.configure("TButton", background=self.COLORS["panel2"], foreground=self.COLORS["text"], borderwidth=0, padding=(8, 4), font=("Segoe UI", 10))
        style.map("TButton", background=[("active", self.COLORS["blue"])])
        style.configure("Accent.TButton", background=self.COLORS["accent"], foreground="#06131a", font=("Segoe UI", 10, "bold"))
        style.configure("Treeview", background=self.COLORS["panel"], fieldbackground=self.COLORS["panel"], foreground=self.COLORS["text"], rowheight=24, borderwidth=0)
        style.configure("Treeview.Heading", background=self.COLORS["panel2"], foreground=self.COLORS["muted"], relief="flat")
        style.configure("TEntry", fieldbackground="#0e192a", foreground=self.COLORS["text"], insertcolor=self.COLORS["text"], padding=5)
        style.configure("TCombobox", fieldbackground="#0e192a", foreground=self.COLORS["text"], padding=4)
        style.map("TCombobox", fieldbackground=[("readonly", "#0e192a")], foreground=[("readonly", self.COLORS["text"])])
        style.configure("TNotebook", background=self.COLORS["bg"], borderwidth=0, tabmargins=(0, 0, 0, 0))
        style.configure("TNotebook.Tab", background=self.COLORS["panel2"], foreground=self.COLORS["muted"], padding=(12, 6), font=("Segoe UI", 10, "bold"))
        style.map("TNotebook.Tab", background=[("selected", self.COLORS["accent"])], foreground=[("selected", "#06131a")])

    # ------------------------------------------------------------
    # Helpers de layout
    # ------------------------------------------------------------
    def _card(self, parent, title, subtitle=None):
        """Cria cartão com cabeçalho e corpo padronizados."""
        card = tk.Frame(parent, bg=self.COLORS["panel"], highlightbackground=self.COLORS["line"], highlightthickness=1)
        header = tk.Frame(card, bg=self.COLORS["panel"])
        header.pack(fill="x", padx=self.LAYOUT["card_padx"], pady=(self.LAYOUT["card_pady"], 8))
        tk.Label(header, text=title, bg=self.COLORS["panel"], fg=self.COLORS["text"], font=("Segoe UI", 12, "bold")).pack(anchor="w")
        if subtitle:
            tk.Label(header, text=subtitle, bg=self.COLORS["panel"], fg=self.COLORS["muted"], font=("Segoe UI", 9)).pack(anchor="w", pady=(2, 0))
        body = tk.Frame(card, bg=self.COLORS["panel"])
        body.pack(fill="both", expand=True, padx=self.LAYOUT["card_padx"], pady=(0, self.LAYOUT["card_pady"]))
        return card, body

    def _clear(self):
        for widget in self.content.winfo_children():
            widget.destroy()

    def _heading(self, title, subtitle):
        tk.Label(self.content, text=title, bg=self.COLORS["bg"], fg=self.COLORS["text"], font=("Segoe UI", 23, "bold")).pack(anchor="w")
        tk.Label(self.content, text=subtitle, bg=self.COLORS["bg"], fg=self.COLORS["muted"], font=("Segoe UI", 10)).pack(anchor="w", pady=(6, 26))

    # ------------------------------------------------------------
    # Autenticação
    # ------------------------------------------------------------
    def _hash_session_token(self, token):
        return hashlib.sha256(str(token).encode("utf-8")).hexdigest()

    def _load_saved_session(self):
        if not self.session_path.exists():
            return None
        try:
            payload = json.loads(self.session_path.read_text(encoding="utf-8"))
            token = str(payload.get("token", ""))
            token_hash = self._hash_session_token(token)
            with self.db.connect() as connection:
                row = connection.execute(
                    "SELECT tb_device_session_user_id, tb_device_session_expires_at FROM tb_device_session WHERE tb_device_session_token_hash=? AND tb_device_session_active=1",
                    (token_hash,)
                ).fetchone()
                if not row or datetime.fromisoformat(row[1]) <= datetime.now():
                    self._clear_saved_session()
                    return None
                account = connection.execute("SELECT * FROM tb_user WHERE tb_user_id=? AND lower(tb_user_status) IN ('ativo','active')", (row[0],)).fetchone()
                if not account:
                    self._clear_saved_session()
                    return None
                connection.execute(
                    "UPDATE tb_device_session SET tb_device_session_expires_at=? WHERE tb_device_session_token_hash=?",
                    (datetime.now().replace(hour=23, minute=59, second=59, microsecond=0).isoformat(), token_hash)
                )
                return dict(account)
        except (OSError, ValueError, json.JSONDecodeError, sqlite3.Error):
            self._clear_saved_session()
            return None

    def _save_device_session(self, account):
        token = secrets.token_urlsafe(48)
        token_hash = self._hash_session_token(token)
        now = datetime.now()
        expires = now.replace(hour=23, minute=59, second=59, microsecond=0)
        with self.db.connect() as connection:
            connection.execute("UPDATE tb_device_session SET tb_device_session_active=0 WHERE tb_device_session_user_id=?", (account["tb_user_id"],))
            connection.execute(
                "INSERT INTO tb_device_session (tb_device_session_user_id,tb_device_session_token_hash,tb_device_session_created_at,tb_device_session_expires_at,tb_device_session_active) VALUES (?,?,?,?,1)",
                (account["tb_user_id"], token_hash, now.isoformat(), expires.isoformat())
            )
        self.session_path.write_text(json.dumps({"token": token, "user_id": account["tb_user_id"], "created_at": now.isoformat()}, ensure_ascii=False), encoding="utf-8")
        try:
            os.chmod(self.session_path, 0o600)
        except OSError:
            pass

    def _clear_saved_session(self):
        try:
            payload = json.loads(self.session_path.read_text(encoding="utf-8")) if self.session_path.exists() else {}
            token_hash = self._hash_session_token(payload.get("token", "")) if payload.get("token") else ""
            if token_hash:
                with self.db.connect() as connection:
                    connection.execute("UPDATE tb_device_session SET tb_device_session_active=0 WHERE tb_device_session_token_hash=?", (token_hash,))
            self.session_path.unlink(missing_ok=True)
        except (OSError, json.JSONDecodeError, sqlite3.Error):
            pass

    def logout(self):
        self._clear_saved_session()
        self.user_data = {}
        self.chatbot = None
        self.show_login()

    def show_login(self):
        if not getattr(self, "_login_screen_shown", False):
            self._login_screen_shown = True
            account = self._load_saved_session()
            if account:
                self.user_data = account
                self._build_shell()
                self.show_home()
                return
        for widget in self.winfo_children():
            widget.destroy()
        self.configure(bg=self.COLORS["bg"])

        wrapper = tk.Frame(self, bg=self.COLORS["bg"])
        wrapper.pack(fill="both", expand=True)

        card = tk.Frame(wrapper, bg=self.COLORS["panel"], highlightbackground=self.COLORS["line"], highlightthickness=1,
                        width=580, height=560)
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.pack_propagate(False)

        tk.Label(card, text="VOXEL", bg=self.COLORS["panel"], fg=self.COLORS["accent"], font=("Segoe UI", 32, "bold")).pack(pady=(68, 4))
        tk.Label(card, text="Virtual Assistant Environment", bg=self.COLORS["panel"], fg=self.COLORS["muted"], font=("Segoe UI", 11)).pack(pady=(0, 38))

        form = tk.Frame(card, bg=self.COLORS["panel"])
        form.pack(fill="x", padx=86)

        tk.Label(form, text="Utilizador", bg=self.COLORS["panel"], fg=self.COLORS["muted"], font=("Segoe UI", 10)).pack(anchor="w")
        username = ttk.Entry(form)
        username.pack(fill="x", ipady=8, pady=(6, 18))

        tk.Label(form, text="Palavra-passe", bg=self.COLORS["panel"], fg=self.COLORS["muted"], font=("Segoe UI", 10)).pack(anchor="w")
        password = ttk.Entry(form, show="•")
        password.pack(fill="x", ipady=8, pady=(6, 10))

        feedback = tk.Label(form, text="Use as credenciais do utilizador cadastrado.",
                            bg=self.COLORS["panel"], fg=self.COLORS["muted"], font=("Segoe UI", 9))
        feedback.pack(anchor="w", pady=(0, 10))

        remember_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(form, text="Lembrar neste computador", variable=remember_var).pack(anchor="w", pady=(0, 16))

        def login(_event=None):
            account = self.db.authenticate(username.get().strip(), password.get())
            if not account:
                feedback.configure(text="Utilizador ou palavra-passe inválidos.", fg=self.COLORS["danger"])
                password.delete(0, "end")
                return
            self.user_data = account
            if remember_var.get():
                self._save_device_session(account)
            else:
                self._clear_saved_session()
            self._build_shell()
            self.show_home()

        ttk.Button(form, text="Entrar no sistema", style="Accent.TButton", command=login).pack(fill="x", ipady=6)
        password.bind("<Return>", login)
        username.focus_set()

        tk.Label(card, text="Acesso protegido • VOXEL", bg=self.COLORS["panel"], fg=self.COLORS["muted"],
                 font=("Segoe UI", 9)).pack(side="bottom", pady=32)

    # ------------------------------------------------------------
    # Shell principal
    # ------------------------------------------------------------
    def _build_shell(self):
        for widget in self.winfo_children():
            widget.destroy()

        # Header
        self.header = tk.Frame(self, bg=self.COLORS["panel"], height=self.LAYOUT["header_height"])
        self.header.pack(fill="x")
        self.header.pack_propagate(False)
        tk.Label(self.header, text="VOXEL", bg=self.COLORS["panel"], fg=self.COLORS["accent"],
                 font=("Segoe UI", 21, "bold")).pack(side="left", padx=32)
        tk.Label(self.header, text="Virtual Assistant Environment", bg=self.COLORS["panel"], fg=self.COLORS["muted"],
                 font=("Segoe UI", 10)).pack(side="left")
        ttk.Button(self.header, text="Sair", command=self.logout).pack(side="right", padx=(8, 24), pady=14)
        tk.Label(self.header, text="●  Sistema pronto", bg=self.COLORS["panel"], fg=self.COLORS["accent"],
                 font=("Segoe UI", 10)).pack(side="right", padx=8)

        # Corpo: sidebar + viewport
        self.body = tk.Frame(self, bg=self.COLORS["bg"])
        self.body.pack(fill="both", expand=True)

        # Sidebar
        self.sidebar = tk.Frame(self.body, bg=self.COLORS["panel"], width=self.LAYOUT["sidebar_width"])
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        tk.Label(self.sidebar, text="NAVEGAÇÃO", bg=self.COLORS["panel"], fg=self.COLORS["muted"],
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=28, pady=(32, 14))
        for text_value, command in (
            ("⌂   Início", self.show_home),
            ("◉   Assistente", self.show_assistant),
            ("⌘   Comandos", self.show_commands),
            ("⚙   Configurações", self.show_config),
            ("♙   Utilizador", self.show_user)
        ):
            self._nav_button(text_value, command)

        tk.Frame(self.sidebar, bg=self.COLORS["line"], height=1).pack(fill="x", padx=24, pady=24)

        tk.Label(self.sidebar, text="AMBIENTE", bg=self.COLORS["panel"], fg=self.COLORS["muted"],
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=28, pady=(0, 12))
        tk.Label(self.sidebar, text="●  SQLite conectado\n●  Configuração carregada",
                 justify="left", bg=self.COLORS["panel"], fg=self.COLORS["muted"], font=("Segoe UI", 9), anchor="w").pack(anchor="w", padx=28)

        # Viewport com canvas e scrollbar
        viewport = tk.Frame(self.body, bg=self.COLORS["bg"])
        viewport.pack(side="left", fill="both", expand=True,
                      padx=self.LAYOUT["outer_padx"], pady=0)

        self.content_canvas = tk.Canvas(viewport, bg=self.COLORS["bg"], highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(viewport, orient="vertical", command=self.content_canvas.yview)
        self.content_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.content_canvas.pack(side="left", fill="both", expand=True)

        self.content = tk.Frame(self.content_canvas, bg=self.COLORS["bg"])
        self.content_window = self.content_canvas.create_window((0, 0), window=self.content, anchor="nw")
        self.content.bind("<Configure>", lambda _e: self.content_canvas.configure(scrollregion=self.content_canvas.bbox("all")))
        self.content_canvas.bind("<Configure>", lambda e: self.content_canvas.itemconfigure(self.content_window, width=e.width))
        self.content_canvas.bind_all("<MouseWheel>", lambda e: self.content_canvas.yview_scroll(int(-e.delta/120), "units"))

        # Footer
        self.footer = tk.Frame(self, bg=self.COLORS["panel"], height=self.LAYOUT["footer_height"])
        self.footer.pack(fill="x")
        self.footer.pack_propagate(False)
        tk.Label(self.footer, text="VOXEL  •  Terminal GUI  •  " + datetime.now().strftime("%d/%m/%Y"),
                 bg=self.COLORS["panel"], fg=self.COLORS["muted"], font=("Segoe UI", 9)).pack(side="left", padx=28)
        tk.Label(self.footer, text="v0.1.0  |  Ambiente local",
                 bg=self.COLORS["panel"], fg=self.COLORS["muted"], font=("Segoe UI", 9)).pack(side="right", padx=28)

    def _nav_button(self, text, command):
        tk.Button(
            self.sidebar, text=text, command=command, anchor="w", relief="flat", bd=0,
            bg=self.COLORS["panel"], fg=self.COLORS["muted"],
            activebackground=self.COLORS["blue"], activeforeground="white",
            font=("Segoe UI", 11), padx=26, pady=8
        ).pack(fill="x")

    # ------------------------------------------------------------
    # Tela inicial
    # ------------------------------------------------------------
    def show_home(self):
        self._clear()
        self._heading("VOXEL System", "Ambiente central de controlo do assistente virtual")

        # Hero
        hero = tk.Frame(self.content, bg=self.COLORS["panel"],
                        highlightbackground=self.COLORS["line"], highlightthickness=1)
        hero.pack(fill="x", pady=(0, 26))
        hero_content = tk.Frame(hero, bg=self.COLORS["panel"])
        hero_content.pack(fill="both", expand=True, padx=24, pady=28)
        tk.Label(hero_content, text="UNDER CONSTRUCTION", bg=self.COLORS["panel"],
                 fg=self.COLORS["accent"], font=("Segoe UI", 30, "bold")).pack(pady=(12, 8))
        tk.Label(hero_content, text="A fundação do sistema está pronta. Abra o Assistente para iniciar uma sessão.",
                 bg=self.COLORS["panel"], fg=self.COLORS["muted"], font=("Segoe UI", 12)).pack(pady=(0, 18))
        ttk.Button(hero_content, text="Abrir Assistente", style="Accent.TButton",
                   command=self.show_assistant).pack(pady=(0, 12))

        # Cards de resumo
        grid = tk.Frame(self.content, bg=self.COLORS["bg"])
        grid.pack(fill="x")
        values = (
            ("Utilizador ativo", self.user_data.get("tb_user_first_name", "Não definido"), self.COLORS["blue"]),
            ("Comandos registados", str(len(self.db.commands())), self.COLORS["accent"]),
            ("Conversas", str(len(self.db.chats())), self.COLORS["warning"]),
        )
        for i, (title, value, color) in enumerate(values):
            card, body = self._card(grid, title)
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 14, 0))
            tk.Label(body, text=value, bg=self.COLORS["panel"], fg=color,
                     font=("Segoe UI", 19, "bold")).pack(anchor="w", pady=(6, 8))
            grid.columnconfigure(i, weight=1)

    # ------------------------------------------------------------
    # Assistente
    # ------------------------------------------------------------
    def show_assistant(self):
        self._clear()
        layout = tk.Frame(self.content, bg=self.COLORS["bg"])
        layout.pack(fill="both", expand=True)

        # Coluna esquerda: conversas
        left_card, left_body = self._card(layout, "Conversas", "Histórico SQLite")
        left_card.pack(side="left", fill="y", padx=(0, 12))
        left_card.configure(width=230)
        left_card.pack_propagate(False)

        self.chat_list = tk.Listbox(
            left_body, width=20, height=18, bg="#0e192a", fg=self.COLORS["text"],
            selectbackground=self.COLORS["blue"], relief="flat", bd=0, highlightthickness=0
        )
        self.chat_list.pack(fill="both", expand=True, pady=(0, 8))
        for chat in self.db.chats():
            self.chat_list.insert("end", f"#{chat.get('tb_chat_id')}  {chat.get('tb_chat_title') or 'Sem título'}")
        self.chat_list.bind("<<ListboxSelect>>", self._load_chat_history)
        ttk.Button(left_body, text="+ Nova conversa", command=self._new_chat).pack(fill="x", pady=(0, 4))

        # Coluna central: chat
        center = tk.Frame(layout, bg=self.COLORS["panel"],
                          highlightbackground=self.COLORS["line"], highlightthickness=1)
        center.pack(side="left", fill="both", expand=True, padx=(0, 12))

        tk.Label(center, text="Chat VOXEL", bg=self.COLORS["panel"], fg=self.COLORS["text"],
                 font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=18, pady=(16, 10))

        self.chat_output = tk.Text(
            center, bg="#0e192a", fg=self.COLORS["text"], insertbackground=self.COLORS["text"],
            relief="flat", bd=0, wrap="word", state="disabled", font=("Segoe UI", 10)
        )
        self.chat_output.pack(fill="both", expand=True, padx=18, pady=(0, 14))

        composer = tk.Frame(center, bg=self.COLORS["panel"])
        composer.pack(fill="x", padx=18, pady=(0, 10))
        self.chat_entry = ttk.Entry(composer)
        self.chat_entry.pack(side="left", fill="x", expand=True, ipady=8)
        self.chat_entry.bind("<Return>", lambda _e: self._send_message())
        self.chat_send_button = ttk.Button(composer, text="Enviar", style="Accent.TButton", command=self._send_message)
        self.chat_send_button.pack(side="left", padx=(8, 0))
        self.chat_voice_button = ttk.Button(composer, text="Ouvir", command=self._capture_voice)
        self.chat_voice_button.pack(side="left", padx=(6, 0))
        self.chat_stop_button = ttk.Button(composer, text="Parar voz", command=self._stop_voice)
        self.chat_stop_button.pack(side="left", padx=(6, 0))

        self.chat_status_label = tk.Label(
            center, text="Pronto para receber uma mensagem.", bg=self.COLORS["panel"],
            fg=self.COLORS["muted"], anchor="w", font=("Segoe UI", 9)
        )
        self.chat_status_label.pack(fill="x", padx=18, pady=(0, 12))

        self.chat_queue = queue.Queue()
        self.after(100, self._poll_chat_queue)

        # Coluna direita: estado
        right_card, right_body = self._card(layout, "Estado em tempo real", "Saúde dos módulos")
        right_card.pack(side="right", fill="y")
        right_card.configure(width=210)
        right_card.pack_propagate(False)

        self.status_text = tk.Text(
            right_body, width=20, height=16, bg=self.COLORS["panel"], fg=self.COLORS["muted"],
            relief="flat", bd=0, state="disabled", font=("Segoe UI", 9)
        )
        self.status_text.pack(fill="both", expand=True, pady=(0, 4))
        self._refresh_status()

    # (demais métodos do assistente permanecem iguais, apenas com pequenos ajustes de espaçamento)
    def _refresh_status(self):
        if not hasattr(self, "status_text"): return
        if self.chatbot is None and ChatbotConfig:
            try:
                self.chatbot = ChatbotConfig(project_root=ROOT, output_printer=lambda *a, **k: None)
            except Exception:
                self.chatbot = None
        status = self.chatbot.get_initialization_status() if self.chatbot else {"is_local_ai_ready": False, "is_online_ai_ready": False, "chat_id": None}
        lines = [
            "MICROFONE     pronto",
            "ASSISTENTE     pronto",
            f"IA LOCAL      {'online' if status.get('is_local_ai_ready') else 'indisponível'}",
            f"IA ONLINE      {'online' if status.get('is_online_ai_ready') else 'indisponível'}",
            "",
            f"Sessão: {status.get('chat_id') or '—'}"
        ]
        self.status_text.configure(state="normal")
        self.status_text.delete("1.0", "end")
        self.status_text.insert("1.0", "\n".join(lines))
        self.status_text.configure(state="disabled")

    def _send_message(self):
        prompt = self.chat_entry.get().strip()
        if not prompt or getattr(self, "chat_busy", False): return
        self.chat_entry.delete(0, "end")
        self._append_chat("Você", prompt)
        self.chat_busy = True
        self.chat_send_button.configure(state="disabled")
        self.chat_status_label.configure(text="A processar a mensagem…")

        def worker():
            try:
                if self.chatbot is None:
                    self.chatbot = ChatbotConfig(project_root=ROOT, output_printer=lambda *a, **k: None) if ChatbotConfig else None
                result = self.chatbot.process_message(prompt) if self.chatbot else {"emissor": "VOXEL", "resposta": "Chatbot indisponível."}
            except Exception as error:
                result = {"emissor": "VOXEL", "resposta": f"Erro controlado: {error}"}
            self.chat_queue.put(("message", result))
        threading.Thread(target=worker, daemon=True).start()

    def _poll_chat_queue(self):
        if not hasattr(self, "chat_queue"): return
        try:
            while True:
                event, payload = self.chat_queue.get_nowait()
                if event == "message":
                    self._finish_chat_message(payload)
                elif event == "voice":
                    self._finish_voice_capture(payload)
        except queue.Empty:
            pass
        if self.winfo_exists():
            self.after(100, self._poll_chat_queue)

    def _finish_chat_message(self, result):
        self._append_chat(result.get("emissor", "VOXEL"), result.get("resposta", ""))
        self.chat_busy = False
        self.chat_send_button.configure(state="normal")
        self.chat_status_label.configure(text="Mensagem processada.")
        self._refresh_status()

    def _capture_voice(self):
        if getattr(self, "chat_busy", False): return
        self.chat_busy = True
        self.chat_voice_button.configure(state="disabled")
        self.chat_status_label.configure(text="A ouvir o microfone…")
        def worker():
            try:
                if self.chatbot is None:
                    self.chatbot = ChatbotConfig(project_root=ROOT, output_printer=lambda *a, **k: None) if ChatbotConfig else None
                text = self.chatbot.capture_user_input(prefer_voice=True) if self.chatbot else ""
            except Exception as error:
                text = f"[Erro de voz: {error}]"
            self.chat_queue.put(("voice", text))
        threading.Thread(target=worker, daemon=True).start()

    def _finish_voice_capture(self, text):
        self.chat_entry.delete(0, "end")
        if text and not str(text).startswith("["):
            self.chat_entry.insert(0, str(text))
            self.chat_status_label.configure(text="Voz convertida em texto; confirme com Enviar.")
        else:
            self.chat_status_label.configure(text="Não foi possível converter a voz em texto.")
        self.chat_busy = False
        self.chat_voice_button.configure(state="normal")

    def _stop_voice(self):
        try:
            if self.chatbot and self.chatbot.audio_output:
                self.chatbot.audio_output.stop_speaking()
                self.chat_status_label.configure(text="Reprodução de voz interrompida.")
        except Exception as error:
            self.chat_status_label.configure(text=f"Controlo de voz indisponível: {error}")

    def _append_chat(self, owner, text):
        self.chat_output.configure(state="normal")
        self.chat_output.insert("end", f"[{datetime.now():%H:%M:%S}]  {owner}\n{text}\n\n")
        self.chat_output.see("end")
        self.chat_output.configure(state="disabled")

    def _load_chat_history(self, _event=None):
        selected = self.chat_list.curselection()
        if not selected: return
        label = self.chat_list.get(selected[0])
        try:
            chat_id = int(str(label).split("#", 1)[1].split()[0])
            chat = self.db.chat(chat_id)
            text = chat.get("tb_chat_log_text", "")
            self.chat_output.configure(state="normal")
            self.chat_output.delete("1.0", "end")
            self.chat_output.insert("1.0", text)
            self.chat_output.see("end")
            self.chat_output.configure(state="disabled")
            self.chat_status_label.configure(text=f"Histórico da sessão #{chat_id} carregado.")
        except (ValueError, IndexError):
            pass

    def _new_chat(self):
        user_id = self.user_data.get("tb_user_id", 0) if self.user_data else 0
        chat_id = self.db.create_chat(user_id, "VOXEL Chat")
        self.chat_output.configure(state="normal")
        self.chat_output.delete("1.0", "end")
        self.chat_output.configure(state="disabled")
        self.chat_list.insert(0, f"#{chat_id}  Nova conversa")
        self.chat_list.selection_clear(0, "end")
        self.chat_list.selection_set(0)
        self.chat_status_label.configure(text=f"Nova sessão #{chat_id} criada.")

    # ------------------------------------------------------------
    # Comandos e Condições
    # ------------------------------------------------------------
    def show_commands(self):
        self._clear()
        notebook = ttk.Notebook(self.content)
        notebook.pack(fill="both", expand=True)
        commands_tab = tk.Frame(notebook, bg=self.COLORS["bg"])
        conditions_tab = tk.Frame(notebook, bg=self.COLORS["bg"])
        notebook.add(commands_tab, text="Comandos")
        notebook.add(conditions_tab, text="Condições ligadas")

        # ---- Aba de Comandos ----
        cmd_card, cmd_body = self._card(commands_tab, "tb_command", "Cada arquivo command possui uma chave e uma resposta")
        cmd_card.pack(fill="both", expand=True)

        tree_cmd = ttk.Treeview(cmd_body, columns=("id", "key", "file", "response", "status"), show="headings")
        for col, label, width in (("id", "ID", 50), ("key", "Chave", 140), ("file", "Arquivo", 160), ("response", "Resposta", 280), ("status", "Status", 80)):
            tree_cmd.heading(col, text=label)
            tree_cmd.column(col, width=width, anchor="w")
        tree_cmd.pack(fill="both", expand=True, pady=(0, 8))

        entries_cmd = {}
        form_cmd = tk.Frame(cmd_body, bg=self.COLORS["panel"])
        form_cmd.pack(fill="x", pady=(0, 8))

        # Formulário em grid
        labels_cmd = (("key", "Chave", 14), ("file", "Arquivo", 16), ("response", "Resposta", 24), ("status", "Status", 8))
        for i, (key, label, width) in enumerate(labels_cmd):
            tk.Label(form_cmd, text=label, bg=self.COLORS["panel"], fg=self.COLORS["muted"]).grid(row=0, column=i, sticky="w", padx=(0, 8), pady=(0, 2))
            entry = ttk.Entry(form_cmd, width=width)
            entry.grid(row=1, column=i, sticky="ew", padx=(0, 8), pady=(0, 2))
            form_cmd.columnconfigure(i, weight=1 if key in ("file", "response") else 0)
            entries_cmd[key] = entry

        actions_cmd = tk.Frame(cmd_body, bg=self.COLORS["panel"])
        actions_cmd.pack(fill="x")

        selected_cmd = tk.IntVar(value=0)

        def refresh_tree_cmd():
            tree_cmd.delete(*tree_cmd.get_children())
            for row in self.db.commands():
                tree_cmd.insert("", "end", values=(
                    row.get("tb_command_id"), row.get("tb_command_key"), row.get("tb_command_file"),
                    row.get("tb_command_response"), row.get("tb_command_status")
                ))

        def load_cmd(_e=None):
            sel = tree_cmd.selection()
            if not sel: return
            values = tree_cmd.item(sel[0], "values")
            selected_cmd.set(int(values[0]))
            for key, val in zip(("key", "file", "response", "status"), values[1:]):
                entries_cmd[key].delete(0, "end")
                entries_cmd[key].insert(0, val)

        def clear_cmd():
            selected_cmd.set(0)
            for entry in entries_cmd.values(): entry.delete(0, "end")
            entries_cmd["status"].insert(0, "ativo")

        def create_cmd():
            if not entries_cmd["key"].get().strip() or not entries_cmd["file"].get().strip():
                messagebox.showwarning("VOXEL", "Informe a chave e o arquivo do comando.")
                return
            self.db.insert_command(entries_cmd["key"].get().strip(), entries_cmd["file"].get().strip(), entries_cmd["response"].get().strip())
            refresh_tree_cmd()
            clear_cmd()

        def update_cmd():
            if not selected_cmd.get():
                messagebox.showwarning("VOXEL", "Selecione um comando.")
                return
            self.db.update_command(selected_cmd.get(), *(entries_cmd[k].get().strip() for k in ("key", "file", "response", "status")))
            refresh_tree_cmd()

        def delete_cmd():
            if selected_cmd.get() and messagebox.askyesno("VOXEL", "Deletar o comando e as condições ligadas?"):
                self.db.delete_command(selected_cmd.get())
                refresh_tree_cmd()
                clear_cmd()
                refresh_cond_options()

        tree_cmd.bind("<<TreeviewSelect>>", load_cmd)

        ttk.Button(actions_cmd, text="Novo", command=clear_cmd).pack(side="left")
        ttk.Button(actions_cmd, text="Criar", style="Accent.TButton", command=create_cmd).pack(side="left", padx=6)
        ttk.Button(actions_cmd, text="Alterar", command=update_cmd).pack(side="left")
        ttk.Button(actions_cmd, text="Deletar", command=delete_cmd).pack(side="left", padx=6)

        refresh_tree_cmd()

        # ---- Aba de Condições ----
        cond_card, cond_body = self._card(conditions_tab, "tb_condition", "Cada condição aponta para um comando-pai através da chave estrangeira")
        cond_card.pack(fill="both", expand=True)

        tree_cond = ttk.Treeview(cond_body, columns=("id", "command", "key", "question", "file", "response", "status"), show="headings")
        for col, label, width in (("id", "ID", 45), ("command", "Comando", 120), ("key", "Chave", 110), ("question", "Pergunta", 180), ("file", "Arquivo/URL", 180), ("response", "Resposta", 180), ("status", "Status", 70)):
            tree_cond.heading(col, text=label)
            tree_cond.column(col, width=width, anchor="w")
        tree_cond.pack(fill="both", expand=True, pady=(0, 8))

        entries_cond = {}
        selected_cond = tk.IntVar(value=0)
        cond_command = tk.StringVar()
        command_map = {}

        top_form = tk.Frame(cond_body, bg=self.COLORS["panel"])
        top_form.pack(fill="x", pady=(0, 4))
        bottom_form = tk.Frame(cond_body, bg=self.COLORS["panel"])
        bottom_form.pack(fill="x", pady=(0, 8))

        tk.Label(top_form, text="Comando-pai", bg=self.COLORS["panel"], fg=self.COLORS["muted"]).grid(row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 2))
        command_combo = ttk.Combobox(top_form, textvariable=cond_command, state="readonly", width=16)
        command_combo.grid(row=0, column=1, sticky="ew", padx=(0, 8), pady=(0, 2))
        top_form.columnconfigure(1, weight=1)

        for i, (key, label, width) in enumerate((("key", "Chave", 10), ("question", "Pergunta", 16), ("file", "Arquivo/URL", 16))):
            tk.Label(top_form, text=label, bg=self.COLORS["panel"], fg=self.COLORS["muted"]).grid(row=1, column=i, sticky="w", padx=(0, 8), pady=(0, 2))
            entry = ttk.Entry(top_form, width=width)
            entry.grid(row=2, column=i, sticky="ew", padx=(0, 8), pady=(0, 2))
            top_form.columnconfigure(i, weight=1)
            entries_cond[key] = entry

        for i, (key, label, width) in enumerate((("response", "Resposta", 18), ("status", "Status", 7))):
            tk.Label(bottom_form, text=label, bg=self.COLORS["panel"], fg=self.COLORS["muted"]).grid(row=0, column=i, sticky="w", padx=(0, 8), pady=(0, 2))
            entry = ttk.Entry(bottom_form, width=width)
            entry.grid(row=1, column=i, sticky="ew", padx=(0, 8), pady=(0, 2))
            bottom_form.columnconfigure(i, weight=1 if key == "response" else 0)
            entries_cond[key] = entry

        actions_cond = tk.Frame(cond_body, bg=self.COLORS["panel"])
        actions_cond.pack(fill="x")

        def refresh_cond_options():
            nonlocal command_map
            command_map = {f"{row['tb_command_id']} | {row['tb_command_key']}": row['tb_command_id'] for row in self.db.commands()}
            command_combo["values"] = list(command_map)

        def refresh_tree_cond():
            tree_cond.delete(*tree_cond.get_children())
            keys = {row['tb_command_id']: row['tb_command_key'] for row in self.db.commands()}
            for row in self.db.conditions():
                tree_cond.insert("", "end", values=(
                    row.get("tb_condition_id"), keys.get(row.get("tb_condition_tb_command_id"), ""),
                    row.get("tb_condition_key"), row.get("tb_condition_question"),
                    row.get("tb_condition_file"), row.get("tb_condition_response"),
                    row.get("tb_condition_status")
                ))

        def load_cond(_e=None):
            sel = tree_cond.selection()
            if not sel: return
            values = tree_cond.item(sel[0], "values")
            selected_cond.set(int(values[0]))
            cond_command.set(next((label for label, cid in command_map.items() if label.endswith(f" | {values[1]}")), ""))
            for key, val in zip(("key", "question", "file", "response", "status"), values[2:]):
                entries_cond[key].delete(0, "end")
                entries_cond[key].insert(0, val)

        def clear_cond():
            selected_cond.set(0)
            cond_command.set("")
            for entry in entries_cond.values(): entry.delete(0, "end")
            entries_cond["status"].insert(0, "ativo")

        def cond_values():
            command_id = command_map.get(cond_command.get())
            return command_id, *(entries_cond[k].get().strip() for k in ("key", "question", "file", "response", "status"))

        def create_cond():
            command_id, key, question, file_name, response, status = cond_values()
            if not command_id or not key:
                messagebox.showwarning("VOXEL", "Selecione o comando-pai e informe a chave.")
                return
            self.db.insert_condition(command_id, key, question, file_name, response, status or "ativo")
            refresh_tree_cond()
            clear_cond()

        def update_cond():
            if not selected_cond.get():
                messagebox.showwarning("VOXEL", "Selecione uma condição.")
                return
            command_id, key, question, file_name, response, status = cond_values()
            self.db.update_condition(selected_cond.get(), command_id, key, question, file_name, response, status)
            refresh_tree_cond()

        def delete_cond():
            if selected_cond.get() and messagebox.askyesno("VOXEL", "Deletar a condição selecionada?"):
                self.db.delete_condition(selected_cond.get())
                refresh_tree_cond()
                clear_cond()

        tree_cond.bind("<<TreeviewSelect>>", load_cond)

        ttk.Button(actions_cond, text="Novo", command=clear_cond).pack(side="left")
        ttk.Button(actions_cond, text="Criar", style="Accent.TButton", command=create_cond).pack(side="left", padx=6)
        ttk.Button(actions_cond, text="Alterar", command=update_cond).pack(side="left")
        ttk.Button(actions_cond, text="Deletar", command=delete_cond).pack(side="left", padx=6)

        refresh_cond_options()
        refresh_tree_cond()

    # ------------------------------------------------------------
    # Ferramentas de suporte
    # ------------------------------------------------------------
    def _run_support_test(self, title, operation, output_widget):
        if self.support is None:
            output_widget.configure(text="Camada de suporte indisponível.", fg=self.COLORS["danger"])
            return
        output_widget.configure(text=f"A executar: {title}...", fg=self.COLORS["warning"])
        def worker():
            try:
                result = operation()
            except Exception as error:
                result = {"status": "ERROR", "message": str(error)}
            self.after(0, lambda: output_widget.configure(
                text=f"{title}: {result.get('status')} — {result.get('message', '')}",
                fg=self.COLORS["accent"] if result.get("status") == "OK" else self.COLORS["warning"]
            ))
        threading.Thread(target=worker, daemon=True).start()

    def _open_support_panel(self, focus=None):
        panel = tk.Toplevel(self)
        panel.title("VOXEL — Ferramenta de correção")
        panel.geometry("680x480")
        panel.minsize(600, 420)
        panel.configure(bg=self.COLORS["bg"])

        tk.Label(panel, text="Ferramenta de correção e diagnóstico", bg=self.COLORS["bg"],
                 fg=self.COLORS["text"], font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=28, pady=(22, 4))
        tk.Label(panel, text="Execute os testes no seu computador e guarde os resultados no database_general.json.",
                 bg=self.COLORS["bg"], fg=self.COLORS["muted"], wraplength=620, justify="left").pack(anchor="w", padx=28, pady=(0, 18))

        output = tk.Label(panel, text="Nenhum teste executado.", bg=self.COLORS["panel"],
                          fg=self.COLORS["muted"], anchor="w", justify="left", wraplength=620, padx=16, pady=12)
        output.pack(fill="x", padx=28, pady=(0, 18))

        actions = tk.Frame(panel, bg=self.COLORS["bg"])
        actions.pack(fill="x", padx=28)

        tests = [
            ("Áudio de entrada", self.support_audio_input.test_devices if self.support_audio_input else lambda: {}),
            ("Texto em Voz", self.support_audio_output.test_engines if self.support_audio_output else lambda: {}),
            ("IA Local", self.support_local_ai.check if self.support_local_ai else lambda: {}),
            ("IA Online", self.support_online_ai.check if self.support_online_ai else lambda: {}),
            ("Assistente", self.support_assistant.validate_configuration if self.support_assistant else lambda: {}),
        ]
        for label, operation in tests:
            ttk.Button(actions, text=f"Testar {label}",
                       command=lambda l=label, op=operation: self._run_support_test(l, op, output)).pack(fill="x", pady=4)

        ttk.Button(actions, text="Calibrar áudio com amostras de teste",
                   command=lambda: self._run_support_test("Calibração de áudio", lambda: self.support.calibrate_audio_input([0.01, 0.02, 0.015, 0.01]), output)
                   ).pack(fill="x", pady=(16, 4))

        runtime_actions = tk.Frame(panel, bg=self.COLORS["bg"])
        runtime_actions.pack(fill="x", padx=28, pady=(14, 0))
        tk.Label(runtime_actions, text="Testes funcionais — dependem do seu ambiente", bg=self.COLORS["bg"],
                 fg=self.COLORS["muted"], font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 6))
        runtime_tests = [
            ("Capturar Voz em Texto", self.support_audio_input.capture if self.support_audio_input else lambda: {}),
            ("Executar Texto em Voz", self.support_audio_output.speak_test if self.support_audio_output else lambda: {}),
            ("Executar IA Local", self.support_local_ai.run_test if self.support_local_ai else lambda: {}),
            ("Executar IA Online", self.support_online_ai.run_test if self.support_online_ai else lambda: {}),
        ]
        for label, operation in runtime_tests:
            ttk.Button(runtime_actions, text=label,
                       command=lambda l=label, op=operation: self._run_support_test(l, op, output)
                       ).pack(side="left", padx=(0, 8))

        if focus:
            aliases = {
                "Ferramenta de correção": ("Áudio de entrada", self.support_audio_input.test_devices),
                "Testar Texto em Voz": ("Texto em Voz", self.support_audio_output.test_engines),
                "Testar IA Local": ("IA Local", self.support_local_ai.check),
                "Testar IA Online": ("IA Online", self.support_online_ai.check),
                "Testar modos do Assistente": ("Assistente", self.support_assistant.validate_configuration),
            }
            label, operation = aliases.get(focus, (None, None))
            if operation:
                self._run_support_test(label, operation, output)

    # ------------------------------------------------------------
    # Configurações
    # ------------------------------------------------------------
    def show_config(self):
        self._clear()
        notebook = ttk.Notebook(self.content)
        notebook.pack(fill="both", expand=True, pady=(0, 8))
        data = self.db.read_config()
        bindings = []

        def add_field(parent, section, key, label, value, options=None, secret=False):
            row = tk.Frame(parent, bg=self.COLORS["panel"])
            row.pack(fill="x", pady=4)
            row.columnconfigure(0, minsize=200)
            row.columnconfigure(1, weight=1)
            tk.Label(row, text=label, width=24, anchor="w", bg=self.COLORS["panel"], fg=self.COLORS["muted"]
                     ).grid(row=0, column=0, sticky="w", padx=(0, 12))
            variable = tk.StringVar(value=str(value if value is not None else ""))
            if options:
                widget = ttk.Combobox(row, textvariable=variable, values=[str(o) for o in options], state="readonly", width=26)
            else:
                widget = ttk.Entry(row, textvariable=variable, show="•" if secret else "")
            widget.grid(row=0, column=1, sticky="ew")
            bindings.append((section, key, variable))

        def section_value(section, key):
            if section is None:
                return data.get(key, "")
            return data.get(section, {}).get(key, "")

        def make_tab(title, subtitle, fields, support_label=None):
            tab = tk.Frame(notebook, bg=self.COLORS["bg"])
            notebook.add(tab, text=title)
            card, body = self._card(tab, title, subtitle)
            card.pack(fill="both", expand=True, padx=2, pady=2)
            for section, key, label, options, secret in fields:
                add_field(body, section, key, label, section_value(section, key), options, secret)
            if support_label:
                support_bar = tk.Frame(body, bg=self.COLORS["panel"])
                support_bar.pack(fill="x", pady=(12, 4))
                ttk.Button(support_bar, text=support_label,
                           command=lambda: self._open_support_panel(support_label)).pack(side="left")
                tk.Label(support_bar, text="Os resultados são guardados em support_diagnostics.",
                         bg=self.COLORS["panel"], fg=self.COLORS["muted"], font=("Segoe UI", 9)
                         ).pack(side="left", padx=12)
            return tab

        make_tab("Configurações Gerais", "Preferências de uso", [
            (None, "keyword_master", "Palavra mestre", None, False),
            (None, "awaiting_duration", "Tempo de espera", None, False),
            (None, "language", "Idioma do sistema", ("pt-BR", "en-US", "es-ES"), False),
            ("status_chatbot", "selected", "Modo do chatbot", ("Assistant", "Artificial Intelligence", "Both"), False),
            ("status_ai", "selected", "Modo de IA", ("Online AI", "Offline AI", "Both"), False),
            ("system_preferences", "theme", "Tema visual", ("dark", "light", "system"), False),
            ("system_preferences", "font_size", "Tamanho da fonte", ("10", "11", "12", "14", "16", "18"), False),
            ("system_preferences", "notifications", "Notificações", ("True", "False"), False),
            ("system_preferences", "notification_sound", "Som de notificações", ("True", "False"), False),
            ("system_preferences", "auto_start_chat", "Iniciar chat automaticamente", ("True", "False"), False),
        ], "Testar modos do Assistente")

        make_tab("Configuração de Entrada", "Voz em texto", [
            (None, "user_input", "Tipo de entrada", ("Keyboard", "Voice", "Both"), False),
            ("microphone_config", "samplerate", "Taxa de amostragem", ("16000", "22050", "44100", "48000"), False),
            ("microphone_config", "channels", "Canais", ("1", "2"), False),
            ("microphone_config", "threshold_volume", "Limite de volume", None, False),
            ("microphone_config", "silence_time", "Tempo de silêncio", ("1.0", "2.0", "3.0", "5.0", "10.0"), False),
            ("microphone_config", "recognition_engine", "Motor de reconhecimento", ("google", "sphinx", "wit", "azure"), False),
            ("microphone_config", "recognition_language", "Idioma de reconhecimento", ("pt-BR", "en-US", "es-ES", "fr-FR"), False),
            ("microphone_config", "normalize_audio", "Normalizar áudio", ("True", "False"), False),
        ], "Ferramenta de correção")

        make_tab("Configuração de Saída", "Texto em voz", [
            (None, "chatbot_output", "Tipo de saída", ("Text", "Voice", "Both"), False),
            ("voice_config", "primary_engine", "Motor principal", ("google_tts", "pyttsx3", "edge_tts"), False),
            ("voice_config", "fallback_engine", "Motor de fallback", ("google_tts", "pyttsx3", "edge_tts"), False),
            ("voice_config", "use_fallback", "Usar fallback", ("True", "False"), False),
            ("voice_config", "voice_language", "Idioma da voz", ("pt", "en", "es", "fr"), False),
            ("voice_config", "voice_gender", "Género da voz", ("female", "male"), False),
            ("voice_config", "voice_volume", "Volume", None, False),
            ("voice_config", "conversation_tone", "Tom da conversa", ("professional", "casual", "friendly", "formal", "fun"), False),
        ], "Testar Texto em Voz")

        make_tab("Configurações de IA Local", "Modelos, histórico e parâmetros de geração", [
            ("local_ai_config", "default_model", "Modelo padrão", ("echo", "simple", "gpt4all", "llama_cpp", "ollama", "transformers"), False),
            ("local_ai_config", "temperature", "Temperatura", None, False),
            ("local_ai_config", "top_p", "Top P", None, False),
            ("local_ai_config", "max_tokens", "Máximo de tokens", ("100", "250", "500", "1000", "2000"), False),
            ("local_ai_config", "use_history", "Usar histórico", ("True", "False"), False),
            ("local_ai_config", "max_history", "Tamanho do histórico", ("10", "20", "50", "100"), False),
            ("local_ai_config", "auto_download_models", "Baixar modelos automaticamente", ("True", "False"), False),
        ], "Testar IA Local")

        make_tab("Configurações de IA Online", "Provedores, endpoint e limites de comunicação", [
            ("online_ai_config", "provider", "Provedor", ("none", "openai", "gemini", "claude", "deepseek", "grok"), False),
            ("online_ai_config", "api_key", "Chave API", None, True),
            ("online_ai_config", "online_model", "Modelo online", None, False),
            ("online_ai_config", "custom_endpoint", "Endpoint personalizado", None, False),
            ("online_ai_config", "use_proxy", "Usar proxy", ("True", "False"), False),
            ("online_ai_config", "proxy_url", "URL do proxy", None, False),
            ("online_ai_config", "request_timeout", "Timeout da requisição", ("10", "15", "30", "60", "120"), False),
            ("online_ai_config", "max_tokens_online", "Máximo de tokens", None, False),
            ("online_ai_config", "temperature_online", "Temperatura", None, False),
            ("online_ai_config", "local_fallback_mode", "Fallback para IA local", ("True", "False"), False),
        ], "Testar IA Online")

        make_tab("Configurações de Vídeo", "Captura de resolução, ecrã e gravação", [
            ("video_config", "capture_enabled", "Captura ativada", ("True", "False"), False),
            ("video_config", "capture_source", "Origem da captura", ("screen", "window", "region"), False),
            ("video_config", "capture_display", "Monitor", ("1", "2", "3"), False),
            ("video_config", "screen_resolution", "Resolução detetada", None, False),
            ("video_config", "capture_width", "Largura da captura", None, False),
            ("video_config", "capture_height", "Altura da captura", None, False),
            ("video_config", "capture_fps", "Frames por segundo", ("15", "24", "30", "60"), False),
            ("video_config", "capture_color_depth", "Profundidade de cor", ("16", "24", "32"), False),
            ("video_config", "capture_format", "Formato de captura", ("png", "jpg", "bmp", "mp4"), False),
            ("video_config", "capture_quality", "Qualidade", None, False),
            ("video_config", "fullscreen", "Ecrã inteiro", ("True", "False"), False),
            ("video_config", "vsync", "Sincronização vertical", ("True", "False"), False),
            ("video_config", "recording_enabled", "Gravação ativada", ("True", "False"), False),
            ("video_config", "recording_directory", "Pasta de gravações", None, False),
            ("video_config", "screenshot_hotkey", "Tecla de captura", None, False),
            ("video_config", "video_hotkey", "Tecla de gravação", None, False),
        ])

        # ---- Aba de Controlo ----
        control_tab = tk.Frame(notebook, bg=self.COLORS["bg"])
        notebook.add(control_tab, text="Controlo")
        control_card, control_body = self._card(control_tab, "Perfis de controlo",
                                                "Ligue cada tecla ou botão de joystick a um command_ registado")
        control_card.pack(fill="both", expand=True, padx=2, pady=2)

        for section, key, label, options, secret in (
            ("controler_config", "enabled", "Controlos ativados", ("True", "False"), False),
            ("controler_config", "input_mode", "Modo de entrada", ("keyboard", "joystick", "both"), False),
            ("controler_config", "keyboard_enabled", "Teclado ativado", ("True", "False"), False),
            ("controler_config", "joystick_enabled", "Joystick ativado", ("True", "False"), False),
            ("controler_config", "joystick_device", "Dispositivo joystick", None, False),
            ("controler_config", "filter_unknown_actions", "Filtrar ações desconhecidas", ("True", "False"), False),
            ("controler_config", "repeat_delay_ms", "Atraso de repetição (ms)", None, False),
            ("controler_config", "repeat_interval_ms", "Intervalo de repetição (ms)", None, False),
        ):
            add_field(control_body, section, key, label, section_value(section, key), options, secret)

        profile_bar = tk.Frame(control_body, bg=self.COLORS["panel"])
        profile_bar.pack(fill="x", pady=(12, 4))
        profile_var = tk.StringVar()
        profile_combo = ttk.Combobox(profile_bar, textvariable=profile_var, state="readonly", width=28)
        profile_combo.pack(side="left", padx=(0, 8))
        profile_ids = {}
        profile_name_entry = ttk.Entry(profile_bar, width=18)
        profile_name_entry.pack(side="left", padx=(0, 8))
        profile_name_entry.insert(0, "Novo perfil")
        profile_type = ttk.Combobox(profile_bar, values=("keyboard", "joystick", "both"), state="readonly", width=11)
        profile_type.set("keyboard")
        profile_type.pack(side="left", padx=(0, 8))

        mapping_tree = ttk.Treeview(control_body, columns=("id", "type", "input", "command", "action"),
                                    show="headings", height=8)
        for col, label, width in (("id", "ID", 45), ("type", "Entrada", 90), ("input", "Tecla/Botão", 120),
                                  ("command", "Command", 180), ("action", "Ação", 180)):
            mapping_tree.heading(col, text=label)
            mapping_tree.column(col, width=width, anchor="w")
        mapping_tree.pack(fill="both", expand=True, pady=(0, 8))

        mapping_selected = tk.IntVar(value=0)
        mapping_form = tk.Frame(control_body, bg=self.COLORS["panel"])
        mapping_form.pack(fill="x", pady=(0, 8))
        mapping_fields = tk.Frame(mapping_form, bg=self.COLORS["panel"])
        mapping_fields.pack(fill="x", pady=(0, 4))
        mapping_actions = tk.Frame(mapping_form, bg=self.COLORS["panel"])
        mapping_actions.pack(fill="x")

        input_type = ttk.Combobox(mapping_fields, values=("keyboard", "joystick"), state="readonly", width=11)
        input_type.set("keyboard")
        input_type.pack(side="left", padx=(0, 8))
        input_key = ttk.Entry(mapping_fields, width=15)
        input_key.pack(side="left", padx=(0, 8))
        command_var = tk.StringVar()
        command_map = {}
        command_combo = ttk.Combobox(mapping_fields, textvariable=command_var, state="readonly", width=24)
        command_combo.pack(side="left", padx=(0, 8))
        action_entry = ttk.Entry(mapping_fields, width=22)
        action_entry.pack(side="left", padx=(0, 8))

        def refresh_profiles():
            profiles = self.controler.profiles() if self.controler else []
            profile_ids.clear()
            profile_ids.update({f"{p['tb_perfil_controler_id']} | {p['tb_perfil_controler_name']}": p['tb_perfil_controler_id'] for p in profiles})
            profile_combo['values'] = list(profile_ids)
            active_id = data.get('controler_config', {}).get('active_profile_id')
            chosen = next((label for label, pid in profile_ids.items() if pid == active_id), next(iter(profile_ids), ""))
            profile_var.set(chosen)
            refresh_mapping_tree()

        def refresh_mapping_tree():
            mapping_tree.delete(*mapping_tree.get_children())
            profile_id = profile_ids.get(profile_var.get())
            if not profile_id or not self.controler:
                return
            for row in self.controler.mappings(profile_id):
                mapping_tree.insert("", "end", values=(
                    row['tb_perfil_controler_map_id'], row['tb_perfil_controler_input_type'],
                    row['tb_perfil_controler_input_key'], row['tb_command_key'],
                    row['tb_perfil_controler_action']
                ))

        def refresh_command_options():
            command_map.clear()
            command_map.update({f"{c['tb_command_id']} | {c['tb_command_key']}": c['tb_command_id'] for c in self.db.commands()})
            command_combo['values'] = list(command_map)

        def active_profile():
            profile_id = profile_ids.get(profile_var.get())
            if profile_id and self.controler:
                self.controler.set_active_profile(profile_id)
                data['controler_config']['active_profile_id'] = profile_id
                data['controler_config']['active_profile_name'] = profile_var.get().split(' | ', 1)[-1]
                refresh_profiles()

        def create_profile():
            name = profile_name_entry.get().strip()
            if not name:
                messagebox.showwarning("VOXEL", "Informe o nome do perfil.")
                return
            try:
                self.controler.create_profile(name, control_type=profile_type.get())
                refresh_profiles()
            except sqlite3.IntegrityError:
                messagebox.showwarning("VOXEL", "Já existe um perfil com esse nome.")

        def clear_mapping():
            mapping_selected.set(0)
            input_key.delete(0, 'end')
            action_entry.delete(0, 'end')
            command_var.set('')
            input_type.set('keyboard')

        def load_mapping(_e=None):
            sel = mapping_tree.selection()
            if not sel: return
            values = mapping_tree.item(sel[0], 'values')
            mapping_selected.set(int(values[0]))
            input_type.set(values[1])
            input_key.delete(0, 'end')
            input_key.insert(0, values[2])
            command_var.set(next((label for label in command_map if label.endswith(f" | {values[3]}")), ''))
            action_entry.delete(0, 'end')
            action_entry.insert(0, values[4])

        def create_mapping():
            profile_id = profile_ids.get(profile_var.get())
            command_id = command_map.get(command_var.get())
            if not profile_id or not input_key.get().strip() or not command_id:
                messagebox.showwarning("VOXEL", "Selecione o perfil, a entrada e o command_.")
                return
            try:
                self.controler.create_mapping(profile_id, input_type.get(), input_key.get(), command_id, action_entry.get())
                refresh_mapping_tree()
                clear_mapping()
            except sqlite3.IntegrityError:
                messagebox.showwarning("VOXEL", "Essa entrada já está mapeada neste perfil.")

        def update_mapping():
            profile_id = profile_ids.get(profile_var.get())
            command_id = command_map.get(command_var.get())
            if not mapping_selected.get() or not profile_id or not command_id:
                messagebox.showwarning("VOXEL", "Selecione um mapeamento válido.")
                return
            self.controler.update_mapping(mapping_selected.get(), profile_id, input_type.get(), input_key.get(), command_id, action_entry.get())
            refresh_mapping_tree()

        def delete_mapping():
            if mapping_selected.get() and messagebox.askyesno("VOXEL", "Deletar o mapeamento selecionado?"):
                self.controler.delete_mapping(mapping_selected.get())
                refresh_mapping_tree()
                clear_mapping()

        mapping_tree.bind("<<TreeviewSelect>>", load_mapping)
        profile_combo.bind("<<ComboboxSelected>>", lambda _e: refresh_mapping_tree())

        ttk.Button(profile_bar, text="Ativar perfil", style="Accent.TButton", command=active_profile).pack(side="left", padx=(0, 8))
        ttk.Button(profile_bar, text="Criar perfil", command=create_profile).pack(side="left")

        ttk.Button(mapping_actions, text="Novo", command=clear_mapping).pack(side="left", padx=(0, 6))
        ttk.Button(mapping_actions, text="Criar", style="Accent.TButton", command=create_mapping).pack(side="left", padx=(0, 6))
        ttk.Button(mapping_actions, text="Alterar", command=update_mapping).pack(side="left", padx=(0, 6))
        ttk.Button(mapping_actions, text="Deletar", command=delete_mapping).pack(side="left")

        refresh_command_options()
        refresh_profiles()

        def save_all():
            for section, key, variable in bindings:
                value = variable.get()
                if value in ("True", "False"):
                    value = value == "True"
                if section is None:
                    data[key] = value
                else:
                    data.setdefault(section, {})[key] = value
            self.db.save_config(data)
            messagebox.showinfo("VOXEL", "Configurações guardadas com sucesso.")

        ttk.Button(self.content, text="Guardar todas as configurações", style="Accent.TButton",
                   command=save_all).pack(anchor="e", pady=(6, 0))

    # ------------------------------------------------------------
    # Utilizador
    # ------------------------------------------------------------
    def show_user(self):
        self._clear()
        page = tk.Frame(self.content, bg=self.COLORS["bg"])
        page.pack(fill="both", expand=True)

        current = dict(self.user_data)
        widgets = {}
        selected_id = tk.IntVar(value=int(current.get("tb_user_id", 0) or 0))
        is_admin = str(self.user_data.get("tb_user_profile", "")).lower() == "administrador"

        form_card, form_body = self._card(page, "Perfil de utilizador", "Atualize os dados e a imagem do perfil")
        form_card.pack(fill="x", padx=0, pady=(0, 10))

        # Perfil destacado
        profile_card = tk.Frame(form_body, bg=self.COLORS["panel2"],
                                highlightbackground=self.COLORS["line"], highlightthickness=1)
        profile_card.pack(fill="x", pady=(0, 10))
        avatar = tk.Label(profile_card, text="◎", width=7, height=3, bg=self.COLORS["blue"], fg="white",
                          font=("Segoe UI", 22, "bold"))
        avatar.pack(side="left", padx=14, pady=10)
        profile_text = tk.Frame(profile_card, bg=self.COLORS["panel2"])
        profile_text.pack(side="left", fill="x", expand=True, pady=10)
        profile_name = tk.Label(profile_text, text="Perfil de utilizador", bg=self.COLORS["panel2"],
                                fg=self.COLORS["text"], font=("Segoe UI", 16, "bold"))
        profile_name.pack(anchor="w")
        profile_meta = tk.Label(profile_text, text="", bg=self.COLORS["panel2"], fg=self.COLORS["muted"],
                                font=("Segoe UI", 10))
        profile_meta.pack(anchor="w", pady=(2, 0))

        # Campos do formulário
        fields = (
            ("tb_user_salutation", "Tratamento"),
            ("tb_user_first_name", "Nome"),
            ("tb_user_last_name", "Apelido"),
            ("tb_user_username", "Username"),
            ("tb_user_password", "Palavra-passe"),
            ("tb_user_nationality", "Nacionalidade"),
            ("tb_user_place_of_birth", "Local de nascimento"),
            ("tb_user_email", "E-mail"),
            ("tb_user_whatsapp", "WhatsApp"),
        )
        for key, label in fields:
            row = tk.Frame(form_body, bg=self.COLORS["panel"])
            row.pack(fill="x", pady=3)
            row.columnconfigure(0, minsize=200)
            row.columnconfigure(1, weight=1)
            tk.Label(row, text=label, width=23, anchor="w", bg=self.COLORS["panel"], fg=self.COLORS["muted"]
                     ).grid(row=0, column=0, sticky="w", padx=(0, 12))
            entry = ttk.Entry(row, show="•" if key == "tb_user_password" else "")
            entry.insert(0, str(current.get(key, "")))
            entry.grid(row=0, column=1, sticky="ew")
            widgets[key] = entry

        # Perfil / Estado
        profile_row = tk.Frame(form_body, bg=self.COLORS["panel"])
        profile_row.pack(fill="x", pady=3)
        profile_row.columnconfigure(0, minsize=200)
        profile_row.columnconfigure(1, weight=1)
        tk.Label(profile_row, text="Perfil / Estado", width=23, anchor="w", bg=self.COLORS["panel"],
                 fg=self.COLORS["muted"]).grid(row=0, column=0, sticky="w", padx=(0, 12))
        profile_var = tk.StringVar(value=str(current.get("tb_user_profile", "Padrão")))
        profile_combo = ttk.Combobox(profile_row, textvariable=profile_var,
                                     values=("Administrador", "Padrão", "Visitante"), state="readonly", width=18)
        profile_combo.grid(row=0, column=1, sticky="w", padx=(0, 8))
        status_var = tk.StringVar(value=str(current.get("tb_user_status", "active")))
        status_combo = ttk.Combobox(profile_row, textvariable=status_var,
                                    values=("active", "inactive"), state="readonly", width=12)
        status_combo.grid(row=0, column=2, sticky="w")
        widgets["tb_user_profile"] = profile_var
        widgets["tb_user_status"] = status_var
        if not is_admin:
            profile_combo.configure(state="disabled")
            status_combo.configure(state="disabled")

        # Localização
        location_row = tk.Frame(form_body, bg=self.COLORS["panel"])
        location_row.pack(fill="x", pady=3)
        location_row.columnconfigure(0, minsize=200)
        location_row.columnconfigure(1, weight=1)
        tk.Label(location_row, text="Estado / Cidade", width=23, anchor="w", bg=self.COLORS["panel"],
                 fg=self.COLORS["muted"]).grid(row=0, column=0, sticky="w", padx=(0, 12))
        state_var = tk.StringVar(value=str(current.get("tb_user_state", "")))
        city_var = tk.StringVar(value=str(current.get("tb_user_city", "")))
        state_combo = ttk.Combobox(location_row, textvariable=state_var, values=self.db.local_states(),
                                   state="readonly", width=10)
        state_combo.grid(row=0, column=1, sticky="w", padx=(0, 8))
        city_combo = ttk.Combobox(location_row, textvariable=city_var, state="readonly", width=30)
        city_combo.grid(row=0, column=2, sticky="ew")
        location_row.columnconfigure(2, weight=1)

        def refresh_cities(_e=None):
            city_combo["values"] = self.db.local_cities(state_var.get())
            if city_var.get() not in city_combo["values"]:
                city_var.set("")
        state_combo.bind("<<ComboboxSelected>>", refresh_cities)
        widgets["tb_user_state"] = state_var
        widgets["tb_user_city"] = city_var
        refresh_cities()

        # Fotografia
        photo_var = tk.StringVar(value=str(current.get("tb_user_photo_path", "")))
        photo_row = tk.Frame(form_body, bg=self.COLORS["panel"])
        photo_row.pack(fill="x", pady=3)
        photo_row.columnconfigure(0, minsize=200)
        photo_row.columnconfigure(1, weight=1)
        tk.Label(photo_row, text="Fotografia", width=23, anchor="w", bg=self.COLORS["panel"],
                 fg=self.COLORS["muted"]).grid(row=0, column=0, sticky="w", padx=(0, 12))
        ttk.Entry(photo_row, textvariable=photo_var, state="readonly").grid(row=0, column=1, sticky="ew", padx=(0, 8))
        ttk.Button(photo_row, text="Selecionar e guardar",
                   command=lambda: choose_photo()).grid(row=0, column=2, sticky="e")

        def render_photo(path_value):
            if Image and path_value and Path(path_value).is_file():
                try:
                    image = Image.open(path_value).convert("RGB")
                    image.thumbnail((78, 78))
                    avatar.image = ImageTk.PhotoImage(image)
                    avatar.configure(image=avatar.image, text="")
                    return
                except Exception:
                    pass
            avatar.configure(image="", text="◎")

        def choose_photo():
            selected = filedialog.askopenfilename(
                title="Selecionar fotografia",
                filetypes=(("Imagens", "*.png *.jpg *.jpeg *.gif *.bmp"), ("Todos", "*.*"))
            )
            if not selected:
                return
            username = widgets["tb_user_username"].get().strip() or "novo_utilizador"
            target_dir = ROOT / "arquivos" / username / "img"
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / Path(selected).name
            shutil.copy2(selected, target)
            photo_var.set(str(target))
            render_photo(target)

        def values():
            data = {key: widget.get().strip() for key, widget in widgets.items()}
            data["tb_user_photo_path"] = photo_var.get().strip()
            return data

        def refresh_profile():
            name = f"{widgets['tb_user_first_name'].get().strip()} {widgets['tb_user_last_name'].get().strip()}".strip() or "Novo utilizador"
            profile_name.configure(text=name)
            profile_meta.configure(text=f"@{widgets['tb_user_username'].get().strip() or 'username'}  •  {profile_var.get() or 'Padrão'}")

        # Tabela de utilizadores
        table_card, table_body = self._card(page, "Registos de utilizadores",
                                            "Selecione uma linha para editar o perfil")
        table_card.pack(fill="both", expand=True, padx=0, pady=(0, 0))

        table_frame = tk.Frame(table_body, bg=self.COLORS["panel"])
        table_frame.pack(fill="both", expand=True, pady=(0, 6))
        tree_scroll = ttk.Scrollbar(table_frame, orient="vertical")
        tree = ttk.Treeview(table_frame, columns=("id", "name", "profile", "city", "state"),
                            show="headings", height=10, yscrollcommand=tree_scroll.set)
        tree_scroll.configure(command=tree.yview)
        for col, title in zip(("id", "name", "profile", "city", "state"), ("ID", "Nome", "Perfil", "Cidade", "UF")):
            tree.heading(col, text=title)
            tree.column(col, width={"id": 48, "name": 250, "profile": 150, "city": 210, "state": 55}[col], anchor="w")
        tree.pack(side="left", fill="both", expand=True)
        tree_scroll.pack(side="right", fill="y")

        count_label = tk.Label(table_body, text="0 registro(s)", bg=self.COLORS["panel"],
                               fg=self.COLORS["accent"], font=("Segoe UI", 9, "bold"))
        count_label.pack(anchor="e", pady=(0, 4))

        # Funções de manipulação
        def refresh_users():
            tree.delete(*tree.get_children())
            records = self.db.users() if is_admin else [u for u in self.db.users() if u.get("tb_user_id") == self.user_data.get("tb_user_id")]
            for user in records:
                tree.insert("", "end", values=(
                    user.get("tb_user_id"),
                    f"{user.get('tb_user_first_name','')} {user.get('tb_user_last_name','')}",
                    user.get("tb_user_profile", "Padrão"),
                    user.get("tb_user_city", ""),
                    user.get("tb_user_state", "")
                ))
            count_label.configure(text=f"{len(records)} registro(s)")

        def load_selected(_e=None):
            item = tree.selection()
            if not item:
                return
            selected_key = tree.item(item[0], "values")[0]
            row = next((user for user in self.db.users() if str(user.get("tb_user_id")) == str(selected_key)), None)
            if not row:
                return
            selected_id.set(row["tb_user_id"])
            for key, widget in widgets.items():
                widget.set(str(row.get(key, "")))
            photo_var.set(str(row.get("tb_user_photo_path", "")))
            refresh_cities()
            refresh_profile()
            render_photo(photo_var.get())

        tree.bind("<<TreeviewSelect>>", load_selected)

        def clear_form():
            selected_id.set(0)
            for widget in widgets.values():
                widget.set("")
            profile_var.set("Padrão")
            status_var.set("active")
            photo_var.set("")
            refresh_profile()
            render_photo("")

        def create_record():
            data = values()
            data["tb_user_status"] = data.get("tb_user_status") or "active"
            data["tb_user_password"] = data.get("tb_user_password") or "admin123"
            self.db.create_user(data)
            refresh_users()
            messagebox.showinfo("VOXEL", "Novo perfil criado.")

        def update_record():
            if not selected_id.get():
                messagebox.showwarning("VOXEL", "Selecione um perfil para alterar.")
                return
            if not is_admin and selected_id.get() != self.user_data.get("tb_user_id"):
                messagebox.showwarning("VOXEL", "O perfil comum só pode alterar o próprio cadastro.")
                return
            self.db.update_user_full(selected_id.get(), values())
            if selected_id.get() == self.user_data.get("tb_user_id"):
                self.user_data = values() | {"tb_user_id": selected_id.get()}
            refresh_users()
            refresh_profile()
            messagebox.showinfo("VOXEL", "Perfil alterado.")

        def delete_record():
            if not is_admin:
                messagebox.showwarning("VOXEL", "Apenas Administrador pode deletar utilizadores.")
                return
            if selected_id.get() and messagebox.askyesno("VOXEL", "Deletar o perfil selecionado?"):
                self.db.delete_user(selected_id.get())
                clear_form()
                refresh_users()

        # Ações do formulário
        actions = tk.Frame(form_body, bg=self.COLORS["panel"])
        actions.pack(fill="x", pady=(8, 0))
        ttk.Button(actions, text="Novo perfil", command=clear_form).pack(side="left")
        ttk.Button(actions, text="Criar", style="Accent.TButton", command=create_record).pack(side="left", padx=6)
        ttk.Button(actions, text="Alterar", command=update_record).pack(side="left")
        ttk.Button(actions, text="Deletar", command=delete_record).pack(side="left", padx=6)

        refresh_users()
        refresh_profile()
        render_photo(photo_var.get())


if __name__ == "__main__":
    VoxelApp().mainloop()