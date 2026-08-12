# Suporte do VOXEL

A pasta `config/support/` contém ferramentas de diagnóstico e correção controlada para os subsistemas de áudio e inteligência artificial.

`support_manager.py` disponibiliza verificações para captura de áudio, calibração de sensibilidade, Texto em Voz, IA Local e IA Online. Os resultados são guardados na secção `support_diagnostics` de `config/database/database_general.json`, juntamente com a data do último teste. As rotinas não instalam pacotes, não guardam palavras-passe e não alteram configurações sem registar a alteração.

`__init__.py` expõe `SupportManager` e as ferramentas individualizadas para utilização pela GUI e por testes automatizados.

| Ficheiro | Responsabilidade |
|---|---|
| `support_audio_input.py` | Dispositivos de microfone, calibração e captura Voz em Texto. |
| `support_audio_output.py` | Motores e teste funcional de Texto em Voz. |
| `support_local_ai.py` | Disponibilidade, modelo e teste da IA Local. |
| `support_online_ai.py` | Conectividade, provedor, credencial e teste da IA Online. |
| `support_assistant.py` | Modos Assistant, Artificial Intelligence e Both e rastreio da rota de decisão. |

Os testes dependentes de microfone, colunas, modelos locais, Internet ou chaves API devem ser executados pelo utilizador através da ferramenta de suporte da tela Configurações, porque o resultado depende do ambiente físico e das credenciais disponíveis.
