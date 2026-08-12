"""Ponto de entrada do command_vision."""

from __future__ import annotations

import argparse
import json

from vision.config_vision import detect_gpu_and_display, load_config
from vision.db.vision_database import initialize_database
from vision.vision_scope import run_vision_scope


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Sistema de visão computacional configurável.")
    actions = root.add_mutually_exclusive_group(required=True)
    actions.add_argument("--init-db", action="store_true", help="Cria as tabelas do banco SQLite.")
    actions.add_argument("--detect-hardware", action="store_true", help="Detecta resolução e dados básicos da GPU.")
    actions.add_argument("--status", action="store_true", help="Exibe a configuração atual.")
    actions.add_argument("--aim", action="store_true", help="Exibe a mira e captura a área ao clicar.")
    return root


def main() -> int:
    args = parser().parse_args()
    if args.aim:
        run_vision_scope()
        return 0
    if args.init_db:
        print(f"Banco inicializado: {initialize_database()}")
        return 0
    if args.detect_hardware:
        print(json.dumps(detect_gpu_and_display(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps(load_config(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
