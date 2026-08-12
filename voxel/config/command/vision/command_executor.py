"""Execução de comandos associados a perfis de visão."""

from __future__ import annotations

import time
from typing import Any


def execute_command(command: Any, config: dict[str, Any]) -> None:
    command_type = command["tb_command_type"]
    hold_seconds = max(0, int(command["tb_command_hold_ms"])) / 1000
    if command_type == "keyboard":
        if not config["input"].get("keyboard_enabled", True):
            return
        try:
            import pyautogui
        except ImportError as error:
            raise RuntimeError("Instale o backend de teclado: py -m pip install pyautogui") from error
        key = command["tb_command_key_code"]
        if not key:
            raise ValueError("Comando de teclado sem tb_command_key_code.")
        pyautogui.keyDown(key)
        time.sleep(hold_seconds)
        pyautogui.keyUp(key)
        return
    if command_type == "joystick":
        if not config["input"].get("joystick_enabled", False):
            return
        try:
            import vgamepad as vg
        except ImportError as error:
            raise RuntimeError("Instale o backend de joystick: py -m pip install vgamepad") from error
        gamepad = vg.VX360Gamepad()
        button = int(command["tb_command_joystick_button"])
        gamepad.press_button(button=button)
        gamepad.update()
        time.sleep(hold_seconds)
        gamepad.release_button(button=button)
        gamepad.update()
