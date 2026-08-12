"""Painel gráfico principal do command_vision.

Executar no Windows:
    py main_vision.py
"""

from __future__ import annotations

import json
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any

from vision.config_vision import detect_gpu_and_display, load_config, save_config
from vision.db.vision_database import SQLITE_FILE, connect, initialize_database
from vision.vision_scope import run_vision_scope


class MainVision(tk.Tk):
    """Painel de controle visual do sistema Vision."""

    COLORS = {
        "bg": "#111827",
        "panel": "#1f2937",
        "panel_light": "#273449",
        "accent": "#22c55e",
        "accent_dark": "#15803d",
        "text": "#f3f4f6",
        "muted": "#9ca3af",
        "border": "#374151",
        "warning": "#f59e0b",
    }

    def __init__(self) -> None:
        super().__init__()
        self.config_data = load_config()
        self.variables: dict[str, tk.Variable] = {}
        self.title("COMMAND VISION  |  Painel de Controle")
        self.geometry("1120x720")
        self.minsize(960, 620)
        self.configure(bg=self.COLORS["bg"])
        self._setup_style()
        self._build_header()
        self._build_body()
        self._build_footer()
        self.refresh_status()

    def _setup_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("App.TFrame", background=self.COLORS["bg"])
        style.configure("Panel.TFrame", background=self.COLORS["panel"])
        style.configure("Card.TFrame", background=self.COLORS["panel_light"])
        style.configure("Title.TLabel", background=self.COLORS["bg"], foreground=self.COLORS["text"], font=("Segoe UI", 20, "bold"))
        style.configure("Subtitle.TLabel", background=self.COLORS["bg"], foreground=self.COLORS["muted"], font=("Segoe UI", 9))
        style.configure("PanelTitle.TLabel", background=self.COLORS["panel"], foreground=self.COLORS["text"], font=("Segoe UI", 12, "bold"))
        style.configure("Label.TLabel", background=self.COLORS["panel"], foreground=self.COLORS["muted"], font=("Segoe UI", 9))
        style.configure("Value.TLabel", background=self.COLORS["panel"], foreground=self.COLORS["text"], font=("Segoe UI", 10, "bold"))
        style.configure("TNotebook", background=self.COLORS["bg"], borderwidth=0)
        style.configure("TNotebook.Tab", background=self.COLORS["panel"], foreground=self.COLORS["muted"], padding=(18, 10), font=("Segoe UI", 9, "bold"))
        style.map("TNotebook.Tab", background=[("selected", self.COLORS["accent_dark"])], foreground=[("selected", "white")])
        style.configure("TButton", background=self.COLORS["panel_light"], foreground=self.COLORS["text"], padding=(12, 7), borderwidth=0, font=("Segoe UI", 9, "bold"))
        style.map("TButton", background=[("active", self.COLORS["accent_dark"])])
        style.configure("Accent.TButton", background=self.COLORS["accent"], foreground="#07130b", padding=(16, 8), font=("Segoe UI", 9, "bold"))
        style.map("Accent.TButton", background=[("active", "#4ade80")])
        style.configure("TEntry", fieldbackground="#111827", foreground=self.COLORS["text"], insertcolor="white", bordercolor=self.COLORS["border"])
        style.configure("TCheckbutton", background=self.COLORS["panel"], foreground=self.COLORS["text"], font=("Segoe UI", 9))
        style.configure("Treeview", background="#111827", fieldbackground="#111827", foreground=self.COLORS["text"], rowheight=28, borderwidth=0)
        style.configure("Treeview.Heading", background=self.COLORS["panel_light"], foreground=self.COLORS["text"], font=("Segoe UI", 9, "bold"))

    def _build_header(self) -> None:
        header = ttk.Frame(self, style="App.TFrame", padding=(28, 22, 28, 12))
        header.pack(fill="x")
        left = ttk.Frame(header, style="App.TFrame")
        left.pack(side="left")
        ttk.Label(left, text="COMMAND VISION", style="Title.TLabel").pack(anchor="w")
        ttk.Label(left, text="Painel de controle · visão computacional e automação por sensor", style="Subtitle.TLabel").pack(anchor="w", pady=(3, 0))
        self.system_badge = tk.Label(header, text="●  SISTEMA PRONTO", bg=self.COLORS["accent_dark"], fg="white", padx=14, pady=7, font=("Segoe UI", 9, "bold"))
        self.system_badge.pack(side="right", pady=4)

    def _build_body(self) -> None:
        container = ttk.Frame(self, style="App.TFrame", padding=(28, 0, 28, 12))
        container.pack(fill="both", expand=True)
        self.notebook = ttk.Notebook(container)
        self.notebook.pack(fill="both", expand=True)
        self._build_dashboard_tab()
        self._build_aim_tab()
        self._build_hardware_tab()
        self._build_input_tab()
        self._build_database_tab()
        self._build_profiles_tab()
        self._build_captures_tab()
        self._build_history_tab()

    def _tab(self, title: str) -> ttk.Frame:
        frame = ttk.Frame(self.notebook, style="Panel.TFrame", padding=24)
        self.notebook.add(frame, text=title)
        return frame

    def _build_dashboard_tab(self) -> None:
        tab = self._tab("  Visão geral  ")
        ttk.Label(tab, text="Centro de controle", style="PanelTitle.TLabel").pack(anchor="w")
        ttk.Label(tab, text="Acompanhe o estado do ambiente e acesse rapidamente os recursos do Vision.", style="Label.TLabel").pack(anchor="w", pady=(4, 20))
        cards = ttk.Frame(tab, style="Panel.TFrame")
        cards.pack(fill="x")
        self.card_values: dict[str, tk.Label] = {}
        for key, title, value in [("display", "TELA", "Não detectada"), ("gpu", "GPU", "Não detectada"), ("aim", "MIRA", "Configurada"), ("database", "BANCO", "SQLite")]:
            card = tk.Frame(cards, bg=self.COLORS["panel_light"], padx=18, pady=16)
            card.pack(side="left", fill="both", expand=True, padx=(0, 12))
            tk.Label(card, text=title, bg=self.COLORS["panel_light"], fg=self.COLORS["muted"], font=("Segoe UI", 8, "bold")).pack(anchor="w")
            label = tk.Label(card, text=value, bg=self.COLORS["panel_light"], fg=self.COLORS["text"], font=("Segoe UI", 13, "bold"))
            label.pack(anchor="w", pady=(8, 0))
            self.card_values[key] = label
        actions = ttk.Frame(tab, style="Panel.TFrame")
        actions.pack(fill="x", pady=(28, 0))
        ttk.Button(actions, text="⟳  Atualizar diagnóstico", command=self.refresh_hardware).pack(side="left", padx=(0, 10))
        ttk.Button(actions, text="◎  Abrir mira", style="Accent.TButton", command=self.open_scope).pack(side="left")
        self.status_text = tk.Text(tab, height=10, bg="#111827", fg=self.COLORS["muted"], insertbackground="white", relief="flat", padx=14, pady=12, font=("Consolas", 9), state="disabled")
        self.status_text.pack(fill="both", expand=True, pady=(24, 0))

    def _build_aim_tab(self) -> None:
        tab = self._tab("  Mira circular  ")
        ttk.Label(tab, text="Configuração da mira", style="PanelTitle.TLabel").pack(anchor="w")
        ttk.Label(tab, text="A mira acompanha o cursor e captura o interior do círculo ao receber o clique configurado.", style="Label.TLabel").pack(anchor="w", pady=(4, 18))
        grid = ttk.Frame(tab, style="Panel.TFrame")
        grid.pack(anchor="w", fill="x")
        self._add_entry(grid, "aim", "diameter", "Diâmetro (px)", 0, 0)
        self._add_entry(grid, "aim", "border_width", "Espessura da borda", 0, 2)
        self._add_entry(grid, "aim", "opacity", "Opacidade", 1, 0)
        self._add_entry(grid, "aim", "hide_before_capture_ms", "Atraso antes da captura (ms)", 1, 2)
        self._add_entry(grid, "aim", "border_color", "Cor da borda", 2, 0)
        self._add_entry(grid, "aim", "crosshair_color", "Cor da mira", 2, 2)
        self._add_check(grid, "aim", "show", "Mostrar mira", 3, 0)
        self._add_check(grid, "aim", "crosshair", "Mostrar linhas internas", 3, 2)
        ttk.Button(tab, text="Salvar configurações da mira", style="Accent.TButton", command=self.save_settings).pack(anchor="w", pady=(25, 0))

    def _build_hardware_tab(self) -> None:
        tab = self._tab("  Tela e GPU  ")
        ttk.Label(tab, text="Ambiente gráfico", style="PanelTitle.TLabel").pack(anchor="w")
        ttk.Label(tab, text="Informações utilizadas para determinar o campo de visão e a posição das capturas.", style="Label.TLabel").pack(anchor="w", pady=(4, 18))
        grid = ttk.Frame(tab, style="Panel.TFrame")
        grid.pack(anchor="w", fill="x")
        for row, (section, key, label) in enumerate([("display", "monitor_index", "Monitor"), ("display", "width", "Largura"), ("display", "height", "Altura"), ("display", "left", "Origem X"), ("display", "top", "Origem Y"), ("gpu", "name", "Placa de vídeo"), ("gpu", "driver", "Driver"), ("gpu", "memory_mb", "Memória (MB)")]):
            self._add_entry(grid, section, key, label, row // 2, (row % 2) * 2)
        ttk.Button(tab, text="Detectar hardware novamente", command=self.refresh_hardware).pack(anchor="w", pady=(25, 0))

    def _build_input_tab(self) -> None:
        tab = self._tab("  Entrada  ")
        ttk.Label(tab, text="Teclado e joystick", style="PanelTitle.TLabel").pack(anchor="w")
        ttk.Label(tab, text="Controle os backends que poderão ser acionados pelos perfis ativos.", style="Label.TLabel").pack(anchor="w", pady=(4, 18))
        grid = ttk.Frame(tab, style="Panel.TFrame")
        grid.pack(anchor="w")
        self._add_check(grid, "input", "keyboard_enabled", "Permitir comandos de teclado", 0, 0)
        self._add_check(grid, "input", "joystick_enabled", "Permitir comandos de joystick", 1, 0)
        self._add_entry(grid, "input", "keyboard_backend", "Backend do teclado", 2, 0)
        self._add_entry(grid, "input", "joystick_backend", "Backend do joystick", 3, 0)
        ttk.Button(tab, text="Salvar configurações de entrada", style="Accent.TButton", command=self.save_settings).pack(anchor="w", pady=(25, 0))

    def _build_database_tab(self) -> None:
        tab = self._tab("  Banco SQLite  ")
        ttk.Label(tab, text="Estrutura de dados", style="PanelTitle.TLabel").pack(anchor="w")
        ttk.Label(tab, text=str(SQLITE_FILE), style="Label.TLabel").pack(anchor="w", pady=(4, 14))
        self.table_tree = ttk.Treeview(tab, columns=("table", "rows"), show="headings", height=10)
        self.table_tree.heading("table", text="Tabela")
        self.table_tree.heading("rows", text="Registros")
        self.table_tree.column("table", width=320)
        self.table_tree.column("rows", width=120)
        self.table_tree.pack(fill="both", expand=True)
        ttk.Button(tab, text="Inicializar / atualizar tabelas", command=self.refresh_database).pack(anchor="w", pady=(15, 0))
        self.refresh_database()
        if hasattr(self, "profiles_tree"):
            self.refresh_profiles()
            self.refresh_capture_data()
            self.refresh_history()

    def _build_profiles_tab(self) -> None:
        tab = self._tab("  Perfis  ")
        ttk.Label(tab, text="Perfis cadastrados", style="PanelTitle.TLabel").pack(anchor="w")
        ttk.Label(tab, text="Visualize quais perfis estão ativos e quais áreas, cores e comandos estão associados.", style="Label.TLabel").pack(anchor="w", pady=(4, 14))
        columns = ("id", "name", "active", "debounce", "captures", "colors", "commands")
        self.profiles_tree = self._create_tree(tab, columns, ("ID", "Nome", "Ativo", "Debounce (ms)", "Capturas", "Cores", "Comandos"), (60, 180, 70, 110, 90, 70, 90))
        ttk.Button(tab, text="Atualizar perfis", command=self.refresh_profiles).pack(anchor="w", pady=(15, 0))
        self.refresh_profiles()

    def _build_captures_tab(self) -> None:
        tab = self._tab("  Capturas  ")
        ttk.Label(tab, text="Áreas e características visuais", style="PanelTitle.TLabel").pack(anchor="w")
        ttk.Label(tab, text="Aqui aparecem as áreas da tela, cores de referência e comandos cadastrados no banco.", style="Label.TLabel").pack(anchor="w", pady=(4, 14))
        self.captures_tree = self._create_tree(tab, ("id", "name", "region", "monitor", "description"), ("ID", "Nome", "Área (x, y, largura, altura)", "Monitor", "Descrição"), (60, 180, 230, 90, 280))
        self.captures_tree.pack(fill="both", expand=True, pady=(0, 12))
        self.colors_tree = self._create_tree(tab, ("id", "name", "rgb", "tolerance", "minimum"), ("ID", "Cor", "RGB", "Tolerância", "Pixels mínimos"), (60, 180, 140, 100, 120))
        self.colors_tree.pack(fill="both", expand=True, pady=(0, 12))
        self.commands_tree = self._create_tree(tab, ("id", "name", "type", "key", "button", "enabled"), ("ID", "Nome", "Tipo", "Tecla", "Botão", "Ativo"), (60, 180, 110, 120, 100, 70))
        self.commands_tree.pack(fill="both", expand=True)
        ttk.Button(tab, text="Atualizar capturas, cores e comandos", command=self.refresh_capture_data).pack(anchor="w", pady=(15, 0))
        self.refresh_capture_data()

    def _build_history_tab(self) -> None:
        tab = self._tab("  Histórico  ")
        ttk.Label(tab, text="Histórico de detecções", style="PanelTitle.TLabel").pack(anchor="w")
        ttk.Label(tab, text="Registros de quando um perfil foi avaliado e se houve correspondência visual.", style="Label.TLabel").pack(anchor="w", pady=(4, 14))
        self.history_tree = self._create_tree(tab, ("id", "profile", "match", "pixels", "created"), ("ID", "Perfil", "Correspondência", "Pixels compatíveis", "Data/hora"), (60, 180, 150, 150, 220))
        self.history_tree.pack(fill="both", expand=True)
        ttk.Button(tab, text="Atualizar histórico", command=self.refresh_history).pack(anchor="w", pady=(15, 0))
        self.refresh_history()

    def _create_tree(self, parent: ttk.Frame, columns: tuple[str, ...], headings: tuple[str, ...], widths: tuple[int, ...]) -> ttk.Treeview:
        tree = ttk.Treeview(parent, columns=columns, show="headings", height=7)
        for column, heading, width in zip(columns, headings, widths):
            tree.heading(column, text=heading)
            tree.column(column, width=width, minwidth=50, anchor="w")
        tree.pack(fill="both", expand=True, pady=(0, 12))
        return tree

    def _clear_tree(self, tree: ttk.Treeview) -> None:
        for item in tree.get_children():
            tree.delete(item)

    def refresh_profiles(self) -> None:
        self._clear_tree(self.profiles_tree)
        with connect() as connection:
            rows = connection.execute("""
                SELECT p.tb_profile_id, p.tb_profile_name, p.tb_profile_active, p.tb_profile_debounce_ms,
                       COUNT(DISTINCT pc.tb_profile_tb_capture_id), COUNT(DISTINCT pco.tb_profile_tb_color_id),
                       COUNT(DISTINCT pca.tb_profile_tb_command_id)
                FROM tb_profile p
                LEFT JOIN tb_profile_tb_capture pc ON pc.tb_profile_tb_capture_tb_profile_id = p.tb_profile_id
                LEFT JOIN tb_profile_tb_color pco ON pco.tb_profile_tb_color_tb_profile_id = p.tb_profile_id
                LEFT JOIN tb_profile_tb_command pca ON pca.tb_profile_tb_command_tb_profile_id = p.tb_profile_id
                GROUP BY p.tb_profile_id ORDER BY p.tb_profile_name
            """).fetchall()
        for row in rows:
            self.profiles_tree.insert("", "end", values=(row[0], row[1], "SIM" if row[2] else "NÃO", row[3], row[4], row[5], row[6]))

    def refresh_capture_data(self) -> None:
        for tree in (self.captures_tree, self.colors_tree, self.commands_tree):
            self._clear_tree(tree)
        with connect() as connection:
            captures = connection.execute("SELECT tb_capture_id, tb_capture_name, tb_capture_x, tb_capture_y, tb_capture_width, tb_capture_height, tb_capture_monitor, COALESCE(tb_capture_description, '') FROM tb_capture ORDER BY tb_capture_name").fetchall()
            colors = connection.execute("SELECT tb_color_id, tb_color_name, tb_color_r, tb_color_g, tb_color_b, tb_color_tolerance, tb_color_minimum_pixels FROM tb_color ORDER BY tb_color_name").fetchall()
            commands = connection.execute("SELECT tb_command_id, tb_command_name, tb_command_type, COALESCE(tb_command_key_code, ''), COALESCE(tb_command_joystick_button, ''), tb_command_enabled FROM tb_command ORDER BY tb_command_name").fetchall()
        for row in captures:
            self.captures_tree.insert("", "end", values=(row[0], row[1], f"({row[2]}, {row[3]}, {row[4]}, {row[5]})", row[6], row[7]))
        for row in colors:
            self.colors_tree.insert("", "end", values=(row[0], row[1], f"({row[2]}, {row[3]}, {row[4]})", row[5], row[6]))
        for row in commands:
            self.commands_tree.insert("", "end", values=(row[0], row[1], row[2], row[3], row[4], "SIM" if row[5] else "NÃO"))

    def refresh_history(self) -> None:
        self._clear_tree(self.history_tree)
        with connect() as connection:
            rows = connection.execute("""
                SELECT d.tb_detection_id, COALESCE(p.tb_profile_name, 'Perfil removido'),
                       d.tb_detection_match, d.tb_detection_matching_pixels, d.tb_detection_created_at
                FROM tb_detection d LEFT JOIN tb_profile p ON p.tb_profile_id = d.tb_detection_tb_profile_id
                ORDER BY d.tb_detection_id DESC LIMIT 500
            """).fetchall()
        for row in rows:
            self.history_tree.insert("", "end", values=(row[0], row[1], "SIM" if row[2] else "NÃO", row[3], row[4]))

    def _add_entry(self, parent: ttk.Frame, section: str, key: str, label: str, row: int, column: int) -> None:
        wrapper = ttk.Frame(parent, style="Panel.TFrame")
        wrapper.grid(row=row, column=column, padx=(0, 30), pady=9, sticky="w")
        ttk.Label(wrapper, text=label, style="Label.TLabel").pack(anchor="w")
        variable = tk.StringVar(value=str(self.config_data.get(section, {}).get(key, "")))
        self.variables[f"{section}.{key}"] = variable
        ttk.Entry(wrapper, textvariable=variable, width=28).pack(anchor="w", pady=(5, 0))

    def _add_check(self, parent: ttk.Frame, section: str, key: str, label: str, row: int, column: int) -> None:
        variable = tk.BooleanVar(value=bool(self.config_data.get(section, {}).get(key, False)))
        self.variables[f"{section}.{key}"] = variable
        ttk.Checkbutton(parent, text=label, variable=variable).grid(row=row, column=column, padx=(0, 30), pady=10, sticky="w")

    def _set_status(self, text: str) -> None:
        self.status_text.configure(state="normal")
        self.status_text.delete("1.0", "end")
        self.status_text.insert("1.0", text)
        self.status_text.configure(state="disabled")

    def refresh_status(self) -> None:
        display = self.config_data.get("display", {})
        gpu = self.config_data.get("gpu", {})
        self.card_values["display"].configure(text=f"{display.get('width') or '—'} × {display.get('height') or '—'}")
        self.card_values["gpu"].configure(text=str(gpu.get("name") or "Não detectada"))
        self.card_values["aim"].configure(text=f"Ø {self.config_data.get('aim', {}).get('diameter', 120)} px")
        self._set_status(json.dumps(self.config_data, ensure_ascii=False, indent=2))

    def save_settings(self) -> None:
        for path, variable in self.variables.items():
            section, key = path.split(".", 1)
            value: Any = variable.get()
            original = self.config_data.get(section, {}).get(key)
            if isinstance(original, bool):
                value = bool(variable.get())
            elif isinstance(original, (int, float)):
                try:
                    value = type(original)(value)
                except (TypeError, ValueError):
                    messagebox.showerror("Valor inválido", f"Confira o valor de {key}.")
                    return
            self.config_data.setdefault(section, {})[key] = value
        save_config(self.config_data)
        self.refresh_status()
        messagebox.showinfo("Configurações salvas", "As configurações foram gravadas em database_vision.json.")

    def refresh_hardware(self) -> None:
        self.config_data = detect_gpu_and_display()
        self.refresh_status()
        messagebox.showinfo("Diagnóstico concluído", "As informações disponíveis da tela e da GPU foram atualizadas.")

    def refresh_database(self) -> None:
        initialize_database()
        for item in self.table_tree.get_children():
            self.table_tree.delete(item)
        with connect() as connection:
            tables = connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'tb_%' ORDER BY name").fetchall()
            for table in tables:
                name = table[0]
                count = connection.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
                self.table_tree.insert("", "end", values=(name, count))

    def open_scope(self) -> None:
        self.withdraw()
        def run() -> None:
            try:
                run_vision_scope()
            except Exception as error:
                self.after(0, lambda: messagebox.showerror("Mira", str(error)))
            finally:
                self.after(0, self.deiconify)
        threading.Thread(target=run, daemon=True).start()


if __name__ == "__main__":
    MainVision().mainloop()
