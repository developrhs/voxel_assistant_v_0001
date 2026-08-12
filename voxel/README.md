2026-08-12 - 12:34:52 - v_0001
2026-08-12 - 12:46:26 - v_0002
2026-08-12 - 12:53:03 - v_0003
2026-08-12 - 12:55:46 - v_0004
2026-08-12 - 12:57:27 - v_0005
2026-08-12 - 12:58:07 - v_0006
2026-08-12 - 12:58:46 - v_0007
2026-08-12 - 12:59:32 - v_0008
2026-08-12 - 13:00:00 - v_0009
2026-08-12 - 13:00:34 - v_0010
2026-08-12 - 13:01:16 - v_0011
2026-08-12 - 13:02:16 - v_0012
2026-08-12 - 13:02:45 - v_0013
2026-08-12 - 13:03:23 - v_0014
2026-08-12 - 13:04:00 - v_0015
2026-08-12 - 13:13:13 - v_0016
2026-08-12 - 13:13:51 - v_0017
2026-08-12 - 13:14:49 - v_0018
2026-08-12 - 13:15:39 - v_0019
2026-08-12 - 13:16:34 - v_0020
2026-08-12 - 13:17:57 - v_0021
2026-08-12 - 13:32:28 - v_0022
2026-08-12 - 13:36:58 - v_0023
2026-08-12 - 13:39:29 - v_0024
2026-08-12 - 13:46:58 - v_0025
2026-08-12 - 14:08:31 - VOXEL_virtual_assistant_v_0026
2026-08-12 - 14:12:39 - VOXEL_virtual_assistant_v_0027
2026-08-12 - 14:23:38 - VOXEL_virtual_assistant_v_0028
2026-08-12 - 14:28:39 - VOXEL_virtual_assistant_v_0029
2026-08-12 - 14:35:03 - VOXEL_virtual_assistant_v_0030
2026-08-12 - 14:44:42 - VOXEL_virtual_assistant_v_0031
2026-08-12 - 17:52:08 - v_0032
2026-08-12 - 18:18:49 - v_0033
2026-08-12 - 18:31:27 - v_0034
2026-08-12 - 18:46:16 - VOXEL_virtual_assistant_v_0035
Revisão do chat e integração completa de Texto em Voz, Voz em Texto, IA Local, IA Online e uso de comandos pelo Assistente; envio assíncrono, histórico SQLite, sessões reais, controlos de voz, resolução de comandos com argumentos e execução dos módulos command_ validados.
2026-08-12 - 18:53:05 - VOXEL_virtual_assistant_v_0036
Implementada sessão persistente opcional neste computador com token local protegido, hash na base de dados, expiração diária, auto-login, opção Lembrar neste computador e botão Sair; palavra-passe não é armazenada no ficheiro de sessão; testes de login manual, auto-login e remoção concluídos.
2026-08-12 - 19:12:02 - VOXEL_virtual_assistant_v_0037
Revisão do INFO.txt e adaptação do suporte legado para config/support; diagnósticos e correção de captura de áudio, calibração, Voz em Texto, Texto em Voz, IA Local e IA Online; botão Ferramenta de correção integrado em Configurações; resultados persistidos em support_diagnostics no database_general.json; testes funcionais e GUI validados.
2026-08-12 - 19:43:46 - VOXEL_virtual_assistant_v_0038
Corrigida a seleção Assistant, Artificial Intelligence e Both e adicionados os seletores correspondentes em Configurações. Implementada a rota de decisão comando → IA Online → IA Local conforme o modo escolhido. Criadas ferramentas de suporte individualizadas para entrada de áudio, saída de áudio, IA Local, IA Online e Assistente, com rastreio persistente no database_general.json.
2026-08-12 - 19:51:33 - VOXEL_virtual_assistant_v_0039
Migração compatível do estudo INFO_config_controller.txt: aliases sincronizados para controler_config/configuracao_controle e video_config/configuracao_video; novos campos de timeout, precedência, bloqueio e modo de gatilho; migração automática das tabelas de mapeamento; suporte a TECLA_UNICA, HOTKEY e SEQUENCIA; perfil padrão automático e testes de preservação e resolução concluídos.
