import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def load_chatbot():
    from config.config_chatbot import ChatbotConfig
    return ChatbotConfig


def self_test():
    ChatbotConfig = load_chatbot()
    bot = ChatbotConfig(project_root=ROOT, output_printer=lambda text, end="\n": None)
    status = bot.get_initialization_status()
    required = {"is_local_ai_ready", "is_online_ai_ready", "chat_id", "log_path", "warnings"}
    missing = required.difference(status)
    if missing:
        raise RuntimeError(f"Campos de inicialização ausentes: {sorted(missing)}")
    result = bot.process_message("teste do sistema VOXEL")
    if "resposta" not in result or "emissor" not in result:
        raise RuntimeError("O processamento de mensagem não retornou a estrutura esperada.")
    print("[OK] Inicialização do chatbot concluída.")
    print(f"[OK] Sessão: {status['chat_id']}")
    print(f"[OK] Log: {status['log_path']}")
    print(f"[OK] Emissor do teste: {result['emissor']}")
    if status["warnings"]:
        print("[AVISO] Alguns serviços opcionais não estão disponíveis:")
        for warning in status["warnings"]:
            print(f"  - {warning}")
    return 0


def interactive():
    ChatbotConfig = load_chatbot()
    bot = ChatbotConfig(project_root=ROOT)
    print("VOXEL - teste pelo terminal")
    print("Digite 'sair' ou 'encerrar chat' para terminar.")
    status = bot.get_initialization_status()
    print(f"Sessão: {status['chat_id']}")
    try:
        bot.start_chat_session()
    except (KeyboardInterrupt, EOFError):
        print("\nSessão encerrada pelo utilizador.")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Executa o teste do assistente VOXEL no terminal.")
    parser.add_argument("--self-test", action="store_true", help="Executa um teste automático sem abrir o ciclo interativo.")
    args = parser.parse_args()
    try:
        return self_test() if args.self_test else interactive()
    except Exception as error:
        print(f"[ERRO] Falha no teste do VOXEL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
