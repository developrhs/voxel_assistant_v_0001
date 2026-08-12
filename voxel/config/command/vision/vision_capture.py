"""Captura de áreas e reconhecimento simples por cor."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from .config_vision import load_config, resolve_capture_directory
from .db.vision_database import connect


def capture_area(x: int, y: int, width: int, height: int, name: str = "capture") -> dict[str, Any]:
    try:
        from PIL import ImageGrab
    except ImportError as error:
        raise RuntimeError("Instale Pillow: py -m pip install pillow") from error
    image = ImageGrab.grab(bbox=(x, y, x + width, y + height), all_screens=True)
    directory = resolve_capture_directory()
    path = directory / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    image.save(path, format="PNG")
    return {"path": str(path), "image": image, "x": x, "y": y, "width": width, "height": height}


def extract_dominant_color(image: Any) -> dict[str, int]:
    """Calcula a cor média da imagem usando amostragem para reduzir custo."""
    rgb = image.convert("RGB")
    pixels = list(rgb.resize((1, 1)).getdata())
    r, g, b = pixels[0]
    return {"r": int(r), "g": int(g), "b": int(b)}


def count_matching_pixels(image: Any, target: tuple[int, int, int], tolerance: int) -> int:
    rgb = image.convert("RGB")
    matches = 0
    for r, g, b in rgb.getdata():
        if max(abs(r - target[0]), abs(g - target[1]), abs(b - target[2])) <= tolerance:
            matches += 1
    return matches


def capture_configured_area(capture_id: int) -> dict[str, Any]:
    with connect() as connection:
        capture = connection.execute("SELECT * FROM tb_capture WHERE tb_capture_id = ?", (capture_id,)).fetchone()
    if capture is None:
        raise ValueError(f"Área de captura {capture_id} não encontrada.")
    result = capture_area(capture["tb_capture_x"], capture["tb_capture_y"], capture["tb_capture_width"], capture["tb_capture_height"], capture["tb_capture_name"])
    result["dominant_color"] = extract_dominant_color(result["image"])
    return result


def profile_matches(profile_id: int, image: Any) -> tuple[bool, int]:
    with connect() as connection:
        colors = connection.execute("""
            SELECT c.* FROM tb_color c
            JOIN tb_profile_tb_color pc ON pc.tb_profile_tb_color_tb_color_id = c.tb_color_id
            WHERE pc.tb_profile_tb_color_tb_profile_id = ?
        """, (profile_id,)).fetchall()
    total_matches = 0
    for color in colors:
        total_matches += count_matching_pixels(
            image,
            (color["tb_color_r"], color["tb_color_g"], color["tb_color_b"]),
            color["tb_color_tolerance"],
        )
    minimum = sum(row["tb_color_minimum_pixels"] for row in colors) if colors else 1
    return total_matches >= minimum, total_matches
