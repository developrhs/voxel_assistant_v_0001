"""Mira circular interativa para seleção e captura de visão."""

from __future__ import annotations

import time
from typing import Any, Callable

from .config_vision import load_config
from .vision_capture import capture_area, extract_dominant_color


class VisionScope:
    """Desenha uma mira sobre a tela e captura seu interior ao clicar."""

    def __init__(self, on_capture: Callable[[dict[str, Any]], None] | None = None) -> None:
        try:
            import tkinter as tk
        except ImportError as error:
            raise RuntimeError("Instale o Tkinter para habilitar a mira gráfica. No Windows, use uma instalação completa do Python.") from error
        self.tk = tk
        self.config = load_config()
        self.options = self.config["aim"]
        self.diameter = max(20, int(self.options.get("diameter", 120)))
        self.radius = self.diameter // 2
        self.on_capture = on_capture
        self.root = self.tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", float(self.options.get("opacity", 0.35)))
        self.transparent = "#010203"
        try:
            self.root.configure(bg=self.transparent)
            self.root.attributes("-transparentcolor", self.transparent)
        except self.tk.TclError:
            self.root.configure(bg="black")
        self.canvas = self.tk.Canvas(self.root, width=self.diameter, height=self.diameter, highlightthickness=0, bg=self.transparent)
        self.canvas.pack()
        self._draw()
        button = str(self.options.get("capture_button", "left"))
        self.root.bind(f"<{button.title()}>", self._capture_click)
        self.root.bind("<Escape>", lambda _event: self.close())
        self.root.after(20, self._follow_mouse)

    def _draw(self) -> None:
        border = self.options.get("border_color", "#00ff00")
        width = max(1, int(self.options.get("border_width", 3)))
        self.canvas.create_oval(width, width, self.diameter - width, self.diameter - width, outline=border, width=width)
        if self.options.get("crosshair", True):
            color = self.options.get("crosshair_color", "#ffffff")
            cross_width = max(1, int(self.options.get("crosshair_width", 1)))
            center = self.radius
            self.canvas.create_line(center, 0, center, self.diameter, fill=color, width=cross_width)
            self.canvas.create_line(0, center, self.diameter, center, fill=color, width=cross_width)

    def _follow_mouse(self) -> None:
        if self.root.winfo_exists():
            x = self.root.winfo_pointerx() - self.radius
            y = self.root.winfo_pointery() - self.radius
            self.root.geometry(f"{self.diameter}x{self.diameter}+{x}+{y}")
            self.root.after(20, self._follow_mouse)

    def _capture_click(self, _event: Any) -> str:
        x = self.root.winfo_pointerx()
        y = self.root.winfo_pointery()
        self.root.withdraw()
        delay = max(0, int(self.options.get("hide_before_capture_ms", 150)))
        self.root.after(delay, lambda: self._capture_at(x, y))
        return "break"

    def _capture_at(self, x: int, y: int) -> None:
        try:
            result = capture_area(x - self.radius, y - self.radius, self.diameter, self.diameter, self.options.get("capture_name", "aim_capture"))
            result["dominant_color"] = extract_dominant_color(result["image"])
            result["center_x"] = x
            result["center_y"] = y
            result["diameter"] = self.diameter
            if self.on_capture:
                self.on_capture(result)
        finally:
            if self.options.get("show", True):
                self.root.deiconify()

    def run(self) -> None:
        if not self.options.get("show", True):
            raise RuntimeError("A mira está desativada em database_vision.json: aim.show=false")
        self.root.mainloop()

    def close(self) -> None:
        try:
            self.root.destroy()
        except self.tk.TclError:
            pass


def run_vision_scope() -> None:
    def report(result: dict[str, Any]) -> None:
        color = result.get("dominant_color", {})
        print(f"Captura realizada em ({result['center_x']}, {result['center_y']}), cor média RGB: {color}")

    VisionScope(on_capture=report).run()
