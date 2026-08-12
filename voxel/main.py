import json
import sqlite3
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk

ROOT = Path(__file__).resolve().parent

try:
    from config.database_manager import DatabaseManager
except Exception:
    DatabaseManager = None

try:
    from config.config_chatbot import ChatbotConfig
except Exception:
    ChatbotConfig = None


class VoxelDatabase:
    def __init__(self):
        self.db_path = ROOT / "config" / "database" / "db" / "db_virtual_assistant.db"
        self.json_path = ROOT / "config" / "database" / "database_general.json"
        self.db = DatabaseManager(project_root=ROOT) if DatabaseManager else None

    def connect(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def user(self):
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM tb_user WHERE tb_user_status='ativo' LIMIT 1").fetchone()
            return dict(row) if row else {}

    def commands(self):
        with self.connect() as connection:
            return [dict(row) for row in connection.execute("SELECT * FROM tb_command ORDER BY tb_command_id")]

    def chats(self):
        with self.connect() as connection:
            return [dict(row) for row in connection.execute("SELECT * FROM tb_chat ORDER BY tb_chat_id DESC")]

    def insert_command(self, key, file_name, response):
        with self.connect() as connection:
            connection.execute("INSERT INTO tb_command (tb_command_key,tb_command_file,tb_command_response,tb_command_status) VALUES (?,?,?,'ativo')", (key, file_name, response))

    def update_user(self, user_id, first_name, last_name, email):
        with self.connect() as connection:
            connection.execute("UPDATE tb_user SET tb_user_first_name=?, tb_user_last_name=?, tb_user_email=? WHERE tb_user_id=?", (first_name, last_name, email, user_id))

    def read_config(self):
        with self.json_path.open("r", encoding="utf-8") as stream:
            return json.load(stream)

    def save_config(self, data):
        temporary = self.json_path.with_suffix(".tmp")
        with temporary.open("w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=4)
        temporary.replace(self.json_path)


class VoxelApp(tk.Tk):
    COLORS = {"bg": "#0b1220", "panel": "#111c2e", "panel2": "#16243a", "line": "#243957", "text": "#e8eef7", "muted": "#91a4bd", "accent": "#35c7a3", "blue": "#4b8cfb", "warning": "#f2b84b", "danger": "#e36b7a"}

    def __init__(self):
        super().__init__()
        self.title("VOXEL System")
        self.geometry("1440x900")
        self.minsize(1100, 700)
        self.configure(bg=self.COLORS["bg"])
        self.db = VoxelDatabase()
        self.user_data = self.db.user()
        self.chatbot = None
        self._setup_style()
        self._build_shell()
        self.show_home()

    def _setup_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=self.COLORS["bg"])
        style.configure("TLabel", background=self.COLORS["bg"], foreground=self.COLORS["text"], font=("Segoe UI", 10))
        style.configure("Title.TLabel", background=self.COLORS["bg"], foreground=self.COLORS["text"], font=("Segoe UI", 22, "bold"))
        style.configure("TButton", background=self.COLORS["panel2"], foreground=self.COLORS["text"], borderwidth=0, padding=(12, 8), font=("Segoe UI", 10))
        style.map("TButton", background=[("active", self.COLORS["blue"])])
        style.configure("Accent.TButton", background=self.COLORS["accent"], foreground="#06131a", font=("Segoe UI", 10, "bold"))
        style.configure("Treeview", background=self.COLORS["panel"], fieldbackground=self.COLORS["panel"], foreground=self.COLORS["text"], rowheight=30, borderwidth=0)
        style.configure("Treeview.Heading", background=self.COLORS["panel2"], foreground=self.COLORS["muted"], relief="flat")
        style.configure("TEntry", fieldbackground="#0e192a", foreground=self.COLORS["text"], insertcolor=self.COLORS["text"])

    def _build_shell(self):
        self.header = tk.Frame(self, bg=self.COLORS["panel"], height=72); self.header.pack(fill="x"); self.header.pack_propagate(False)
        tk.Label(self.header, text="VOXEL", bg=self.COLORS["panel"], fg=self.COLORS["accent"], font=("Segoe UI", 21, "bold")).pack(side="left", padx=28)
        tk.Label(self.header, text="Virtual Assistant Environment", bg=self.COLORS["panel"], fg=self.COLORS["muted"], font=("Segoe UI", 10)).pack(side="left")
        tk.Label(self.header, text="●  Sistema pronto", bg=self.COLORS["panel"], fg=self.COLORS["accent"], font=("Segoe UI", 10)).pack(side="right", padx=28)
        self.body = tk.Frame(self, bg=self.COLORS["bg"]); self.body.pack(fill="both", expand=True)
        self.sidebar = tk.Frame(self.body, bg=self.COLORS["panel"], width=220); self.sidebar.pack(side="left", fill="y"); self.sidebar.pack_propagate(False)
        tk.Label(self.sidebar, text="NAVEGAÇÃO", bg=self.COLORS["panel"], fg=self.COLORS["muted"], font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=22, pady=(28, 12))
        for text, command in (("⌂   Início", self.show_home), ("◉   Assistente", self.show_assistant), ("⌘   Comandos", self.show_commands), ("⚙   Configurações", self.show_config), ("♙   Utilizador", self.show_user)):
            self._nav_button(text, command)
        tk.Frame(self.sidebar, bg=self.COLORS["line"], height=1).pack(fill="x", padx=18, pady=22)
        tk.Label(self.sidebar, text="AMBIENTE", bg=self.COLORS["panel"], fg=self.COLORS["muted"], font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=22, pady=(0, 10))
        tk.Label(self.sidebar, text="●  SQLite conectado\n●  Configuração carregada", justify="left", bg=self.COLORS["panel"], fg=self.COLORS["muted"], font=("Segoe UI", 9), anchor="w").pack(anchor="w", padx=22)
        self.content = tk.Frame(self.body, bg=self.COLORS["bg"]); self.content.pack(side="left", fill="both", expand=True, padx=28, pady=24)
        self.footer = tk.Frame(self, bg=self.COLORS["panel"], height=34); self.footer.pack(fill="x"); self.footer.pack_propagate(False)
        tk.Label(self.footer, text="VOXEL  •  Terminal GUI  •  " + datetime.now().strftime("%d/%m/%Y"), bg=self.COLORS["panel"], fg=self.COLORS["muted"], font=("Segoe UI", 9)).pack(side="left", padx=24)
        tk.Label(self.footer, text="v0.1.0  |  Ambiente local", bg=self.COLORS["panel"], fg=self.COLORS["muted"], font=("Segoe UI", 9)).pack(side="right", padx=24)

    def _nav_button(self, text, command):
        tk.Button(self.sidebar, text=text, command=command, anchor="w", relief="flat", bd=0, bg=self.COLORS["panel"], fg=self.COLORS["muted"], activebackground=self.COLORS["blue"], activeforeground="white", font=("Segoe UI", 11), padx=22, pady=11).pack(fill="x")

    def _clear(self):
        for widget in self.content.winfo_children(): widget.destroy()

    def _heading(self, title, subtitle):
        tk.Label(self.content, text=title, bg=self.COLORS["bg"], fg=self.COLORS["text"], font=("Segoe UI", 23, "bold")).pack(anchor="w")
        tk.Label(self.content, text=subtitle, bg=self.COLORS["bg"], fg=self.COLORS["muted"], font=("Segoe UI", 10)).pack(anchor="w", pady=(4, 22))

    def _card(self, parent, title, subtitle=None):
        card = tk.Frame(parent, bg=self.COLORS["panel"], highlightbackground=self.COLORS["line"], highlightthickness=1)
        tk.Label(card, text=title, bg=self.COLORS["panel"], fg=self.COLORS["text"], font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=18, pady=(16, 2))
        if subtitle: tk.Label(card, text=subtitle, bg=self.COLORS["panel"], fg=self.COLORS["muted"], font=("Segoe UI", 9)).pack(anchor="w", padx=18, pady=(0, 12))
        return card

    def show_home(self):
        self._clear(); self._heading("VOXEL System", "Ambiente central de controlo do assistente virtual")
        hero = tk.Frame(self.content, bg=self.COLORS["panel"], highlightbackground=self.COLORS["line"], highlightthickness=1); hero.pack(fill="x", pady=(0, 24))
        tk.Label(hero, text="UNDER CONSTRUCTION", bg=self.COLORS["panel"], fg=self.COLORS["accent"], font=("Segoe UI", 30, "bold")).pack(pady=(55, 8))
        tk.Label(hero, text="A fundação do sistema está pronta. Abra o Assistente para iniciar uma sessão.", bg=self.COLORS["panel"], fg=self.COLORS["muted"], font=("Segoe UI", 12)).pack(pady=(0, 32))
        ttk.Button(hero, text="Abrir Assistente", style="Accent.TButton", command=self.show_assistant).pack(pady=(0, 55))
        grid = tk.Frame(self.content, bg=self.COLORS["bg"]); grid.pack(fill="x")
        values = (("Utilizador ativo", self.user_data.get("tb_user_first_name", "Não definido"), self.COLORS["blue"]), ("Comandos registados", str(len(self.db.commands())), self.COLORS["accent"]), ("Conversas", str(len(self.db.chats())), self.COLORS["warning"]))
        for i, (title, value, color) in enumerate(values):
            card = self._card(grid, title); card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 12, 0)); tk.Label(card, text=value, bg=self.COLORS["panel"], fg=color, font=("Segoe UI", 19, "bold")).pack(anchor="w", padx=18, pady=(5, 20)); grid.columnconfigure(i, weight=1)

    def show_assistant(self):
        self._clear(); self._heading("Assistente", "Chat visual, histórico de conversas e estado do processamento")
        layout = tk.Frame(self.content, bg=self.COLORS["bg"]); layout.pack(fill="both", expand=True)
        left = self._card(layout, "Conversas", "Histórico SQLite"); left.pack(side="left", fill="y", padx=(0, 14))
        self.chat_list = tk.Listbox(left, width=25, height=22, bg="#0e192a", fg=self.COLORS["text"], selectbackground=self.COLORS["blue"], relief="flat", bd=0, highlightthickness=0); self.chat_list.pack(padx=14, pady=8, fill="both", expand=True)
        for chat in self.db.chats(): self.chat_list.insert("end", f"#{chat.get('tb_chat_id')}  {chat.get('tb_chat_title') or 'Sem título'}")
        ttk.Button(left, text="+ Nova conversa", command=self._new_chat).pack(fill="x", padx=14, pady=(4, 14))
        center = tk.Frame(layout, bg=self.COLORS["panel"], highlightbackground=self.COLORS["line"], highlightthickness=1); center.pack(side="left", fill="both", expand=True, padx=(0, 14))
        tk.Label(center, text="Chat VOXEL", bg=self.COLORS["panel"], fg=self.COLORS["text"], font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=18, pady=16)
        self.chat_output = tk.Text(center, bg="#0e192a", fg=self.COLORS["text"], insertbackground=self.COLORS["text"], relief="flat", bd=0, wrap="word", state="disabled", font=("Segoe UI", 10)); self.chat_output.pack(fill="both", expand=True, padx=14, pady=(0, 12))
        composer = tk.Frame(center, bg=self.COLORS["panel"]); composer.pack(fill="x", padx=14, pady=(0, 14)); self.chat_entry = ttk.Entry(composer); self.chat_entry.pack(side="left", fill="x", expand=True, ipady=8); self.chat_entry.bind("<Return>", lambda _event: self._send_message()); ttk.Button(composer, text="Enviar", style="Accent.TButton", command=self._send_message).pack(side="left", padx=(8, 0))
        right = self._card(layout, "Estado em tempo real", "Saúde dos módulos"); right.pack(side="right", fill="y")
        self.status_text = tk.Text(right, width=26, height=20, bg=self.COLORS["panel"], fg=self.COLORS["muted"], relief="flat", bd=0, state="disabled", font=("Segoe UI", 9)); self.status_text.pack(fill="both", expand=True, padx=14, pady=8); self._refresh_status()

    def _refresh_status(self):
        if not hasattr(self, "status_text"): return
        if self.chatbot is None and ChatbotConfig:
            try: self.chatbot = ChatbotConfig(project_root=ROOT, output_printer=lambda *_args, **_kwargs: None)
            except Exception: self.chatbot = None
        status = self.chatbot.get_initialization_status() if self.chatbot else {"is_local_ai_ready": False, "is_online_ai_ready": False, "chat_id": None}
        lines = ["MICROFONE     pronto", "ASSISTENTE     pronto", f"IA LOCAL      {'online' if status.get('is_local_ai_ready') else 'indisponível'}", f"IA ONLINE      {'online' if status.get('is_online_ai_ready') else 'indisponível'}", "", f"Sessão: {status.get('chat_id') or '—'}"]
        self.status_text.configure(state="normal"); self.status_text.delete("1.0", "end"); self.status_text.insert("1.0", "\n".join(lines)); self.status_text.configure(state="disabled")

    def _send_message(self):
        prompt = self.chat_entry.get().strip()
        if not prompt: return
        self.chat_entry.delete(0, "end"); self._append_chat("Você", prompt)
        try:
            if self.chatbot is None: self.chatbot = ChatbotConfig(project_root=ROOT, output_printer=lambda *_args, **_kwargs: None) if ChatbotConfig else None
            result = self.chatbot.process_message(prompt) if self.chatbot else {"emissor": "VOXEL", "resposta": "Chatbot indisponível."}; self._append_chat(result.get("emissor", "VOXEL"), result.get("resposta", ""))
        except Exception as error: self._append_chat("VOXEL", f"Erro controlado: {error}")
        self._refresh_status()

    def _append_chat(self, owner, text):
        self.chat_output.configure(state="normal"); self.chat_output.insert("end", f"[{datetime.now():%H:%M:%S}]  {owner}\n{text}\n\n"); self.chat_output.see("end"); self.chat_output.configure(state="disabled")

    def _new_chat(self):
        self.chat_output.configure(state="normal"); self.chat_output.delete("1.0", "end"); self.chat_output.configure(state="disabled"); self.chat_list.insert(0, "Nova conversa")

    def show_commands(self):
        self._clear(); self._heading("Comandos", "Registo e manutenção dos comandos disponíveis")
        card = self._card(self.content, "Comandos do Assistente", "Tabela tb_command"); card.pack(fill="both", expand=True)
        columns = ("id", "key", "file", "response", "status"); tree = ttk.Treeview(card, columns=columns, show="headings")
        for col, label in zip(columns, ("ID", "Chave", "Arquivo", "Resposta", "Status")): tree.heading(col, text=label); tree.column(col, width=120 if col != "response" else 360)
        tree.pack(fill="both", expand=True, padx=16, pady=12)
        for row in self.db.commands(): tree.insert("", "end", values=(row.get("tb_command_id"), row.get("tb_command_key"), row.get("tb_command_file"), row.get("tb_command_response"), row.get("tb_command_status")))
        form = tk.Frame(card, bg=self.COLORS["panel"]); form.pack(fill="x", padx=16, pady=(0, 16)); entries = []
        for label in ("Chave", "Arquivo", "Resposta"):
            tk.Label(form, text=label, bg=self.COLORS["panel"], fg=self.COLORS["muted"]).pack(side="left", padx=(0, 6)); entry = ttk.Entry(form, width=18); entry.pack(side="left", padx=(0, 12)); entries.append(entry)
        def add():
            if entries[0].get().strip(): self.db.insert_command(*(entry.get().strip() for entry in entries)); self.show_commands()
        ttk.Button(form, text="Adicionar comando", style="Accent.TButton", command=add).pack(side="left")

    def show_config(self):
        self._clear(); self._heading("Configurações", "Preferências gerais ligadas ao database_general.json")
        card = self._card(self.content, "Configuração rápida", "Edite os valores principais do ambiente"); card.pack(fill="both", expand=True)
        data = self.db.read_config(); fields = (("status_chatbot", "Modo do chatbot"), ("status_ai", "Modo de IA"), ("user_input", "Entrada"), ("chatbot_output", "Saída"), ("keyword_master", "Palavra mestre")); widgets = []
        for key, label in fields:
            row = tk.Frame(card, bg=self.COLORS["panel"]); row.pack(fill="x", padx=22, pady=9); tk.Label(row, text=label, width=24, anchor="w", bg=self.COLORS["panel"], fg=self.COLORS["muted"]).pack(side="left"); value = data.get(key, {}); value = value.get("selected", "") if isinstance(value, dict) else value; entry = ttk.Entry(row); entry.insert(0, str(value)); entry.pack(side="left", fill="x", expand=True); widgets.append((key, entry))
        def save():
            for key, entry in widgets:
                if isinstance(data.get(key), dict): data[key]["selected"] = entry.get()
                else: data[key] = entry.get()
            self.db.save_config(data); messagebox.showinfo("VOXEL", "Configurações guardadas com sucesso.")
        ttk.Button(card, text="Guardar alterações", style="Accent.TButton", command=save).pack(anchor="e", padx=22, pady=20)

    def show_user(self):
        self._clear(); self._heading("Utilizador", "Perfil ativo carregado da tabela tb_user")
        card = self._card(self.content, "Perfil ativo", "Dados persistidos no SQLite"); card.pack(fill="x")
        fields = (("tb_user_first_name", "Nome"), ("tb_user_last_name", "Apelido"), ("tb_user_email", "E-mail")); widgets = []
        for key, label in fields:
            row = tk.Frame(card, bg=self.COLORS["panel"]); row.pack(fill="x", padx=22, pady=9); tk.Label(row, text=label, width=24, anchor="w", bg=self.COLORS["panel"], fg=self.COLORS["muted"]).pack(side="left"); entry = ttk.Entry(row); entry.insert(0, str(self.user_data.get(key, ""))); entry.pack(side="left", fill="x", expand=True); widgets.append(entry)
        def save():
            self.db.update_user(self.user_data.get("tb_user_id"), *(entry.get().strip() for entry in widgets)); self.user_data = self.db.user(); messagebox.showinfo("VOXEL", "Perfil atualizado.")
        ttk.Button(card, text="Guardar perfil", style="Accent.TButton", command=save).pack(anchor="e", padx=22, pady=20)


if __name__ == "__main__":
    VoxelApp().mainloop()
