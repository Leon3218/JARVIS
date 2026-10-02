# JARVIS V7.1 — Launcher HUD

Projeto Android/Kivy evoluído a partir do JARVIS V7.1 Launcher e da referência visual de 16 setores fornecida pelo usuário.

## Interface

A tela inicial funciona como um painel HUD/launcher com 16 setores:
1. Sistema
2. Aplicativos
3. Internet / Navegador
4. Mídia / Player
5. Contatos
6. GPS / Mapas
7. Configurações
8. Segurança / Bloqueio
9. Câmera
10. Calendário / Agenda
11. Clima / Tempo
12. Tarefas / Lembretes
13. Assistente de voz
14. Arquivos / Documentos
15. Modo noturno
16. Ferramentas rápidas

## Recursos

- Home App/Launcher do Android.
- Comandos de voz em português do Brasil.
- Resposta por voz (TTS).
- Bateria e memória RAM.
- Abertura de apps instalados quando o pacote é conhecido.
- Pesquisa web, mapas e rotas.
- Discador, SMS, contatos e câmera.
- Agenda/eventos e seletor de arquivos.
- Lanterna, Wi-Fi, Bluetooth, tela e configurações do app.
- Tarefas persistentes em SQLite.
- Histórico local de conversas.
- Conector opcional de IA compatível com API OpenAI.

## Build

O workflow usa `ArtemSBulgakov/buildozer-action@v1`, baseado no container oficial do Buildozer, em vez do ambiente Python instalado diretamente no runner. O alvo inicial é `buildozer android debug`, gerando um APK instalável.

O projeto mantém `android.archs = arm64-v8a`, API 35, min API 24 e NDK 28c, alinhados aos padrões atuais do Buildozer/python-for-android.

## Limites do Android

`android.home_app = True` faz o JARVIS aparecer como aplicativo de tela inicial/launcher. Isso não transforma o app em um sistema operacional nem permite substituir componentes protegidos do Android.
