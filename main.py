import ast
import operator
import webbrowser
from datetime import datetime
from urllib.parse import quote_plus

from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput


# ============================================================
# CALCULADORA SEGURA
# ============================================================

OPERADORES = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def calcular(expressao):
    expressao = expressao.replace("^", "**")

    def avaliar(no):
        if isinstance(no, ast.Constant):
            if isinstance(no.value, (int, float)):
                return no.value
            raise ValueError("Valor inválido")

        if isinstance(no, ast.Num):
            return no.n

        if isinstance(no, ast.BinOp):
            operador = OPERADORES.get(type(no.op))
            if operador is None:
                raise ValueError("Operador não permitido")

            esquerda = avaliar(no.left)
            direita = avaliar(no.right)

            if abs(direita) > 10**100:
                raise ValueError("Número muito grande")

            return operador(esquerda, direita)

        if isinstance(no, ast.UnaryOp):
            operador = OPERADORES.get(type(no.op))
            if operador is None:
                raise ValueError("Operador não permitido")
            return operador(avaliar(no.operand))

        raise ValueError("Expressão inválida")

    arvore = ast.parse(expressao, mode="eval")

    resultado = avaliar(arvore.body)

    if isinstance(resultado, float) and resultado.is_integer():
        resultado = int(resultado)

    return resultado


# ============================================================
# JARVIS
# ============================================================

class JarvisApp(App):

    def build(self):
        self.title = "JARVIS"

        raiz = BoxLayout(
            orientation="vertical",
            padding=dp(10),
            spacing=dp(8),
        )

        with raiz.canvas.before:
            Color(0.025, 0.03, 0.045, 1)
            self.fundo = RoundedRectangle(
                pos=raiz.pos,
                size=raiz.size,
                radius=[dp(18)],
            )

        raiz.bind(
            pos=self.atualizar_fundo,
            size=self.atualizar_fundo
        )

        # ====================================================
        # CABEÇALHO
        # ====================================================

        cabecalho = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=dp(75),
            padding=[dp(12), dp(8)],
        )

        titulo = Label(
            text="JARVIS",
            font_size="28sp",
            bold=True,
            halign="left",
            valign="middle",
        )

        titulo.bind(
            size=lambda instance, value:
            setattr(instance, "text_size", value)
        )

        status = Label(
            text="● ONLINE  •  Assistente local",
            font_size="13sp",
            halign="left",
            valign="middle",
        )

        status.bind(
            size=lambda instance, value:
            setattr(instance, "text_size", value)
        )

        cabecalho.add_widget(titulo)
        cabecalho.add_widget(status)

        raiz.add_widget(cabecalho)

        # ====================================================
        # ÁREA DE HISTÓRICO
        # ====================================================

        self.scroll = ScrollView(
            do_scroll_x=False,
            do_scroll_y=True,
        )

        self.historico = BoxLayout(
            orientation="vertical",
            spacing=dp(8),
            size_hint_y=None,
            padding=[dp(5), dp(5)],
        )

        self.historico.bind(
            minimum_height=self.historico.setter("height")
        )

        self.scroll.add_widget(self.historico)

        raiz.add_widget(self.scroll)

        # ====================================================
        # ÁREA DE TEXTO
        # ====================================================

        entrada_layout = BoxLayout(
            size_hint_y=None,
            height=dp(55),
            spacing=dp(8),
        )

        self.entrada = TextInput(
            hint_text="Digite um comando...",
            multiline=False,
            font_size="16sp",
            padding=[dp(12), dp(15)],
        )

        self.entrada.bind(
            on_text_validate=self.enviar
        )

        botao_enviar = Button(
            text="ENVIAR",
            size_hint_x=None,
            width=dp(95),
            font_size="14sp",
            bold=True,
        )

        botao_enviar.bind(
            on_release=self.enviar
        )

        entrada_layout.add_widget(self.entrada)
        entrada_layout.add_widget(botao_enviar)

        raiz.add_widget(entrada_layout)

        # ====================================================
        # BOTÕES RÁPIDOS
        # ====================================================

        atalhos = BoxLayout(
            size_hint_y=None,
            height=dp(48),
            spacing=dp(6),
        )

        for texto, comando in [
            ("HORAS", "que horas são"),
            ("DATA", "qual a data"),
            ("AJUDA", "ajuda"),
        ]:
            botao = Button(
                text=texto,
                font_size="13sp",
            )

            botao.bind(
                on_release=lambda instance,
                cmd=comando:
                self.comando_atalho(cmd)
            )

            atalhos.add_widget(botao)

        raiz.add_widget(atalhos)

        # ====================================================
        # PRIMEIRA MENSAGEM
        # ====================================================

        self.adicionar_mensagem(
            "JARVIS",
            "Olá. Eu sou o JARVIS. Como posso ajudar?"
        )

        # ====================================================
        # RETORNA A INTERFACE
        # ====================================================

        return raiz

    # ========================================================
    # FUNDO
    # ========================================================

    def atualizar_fundo(self, instance, value):
        self.fundo.pos = instance.pos
        self.fundo.size = instance.size

    # ========================================================
    # BOTÕES RÁPIDOS
    # ========================================================

    def comando_atalho(self, comando):
        self.entrada.text = comando
        self.enviar()

    # ========================================================
    # ENVIAR COMANDO
    # ========================================================

    def enviar(self, *args):
        comando = self.entrada.text.strip()

        if not comando:
            return

        self.adicionar_mensagem(
            "VOCÊ",
            comando
        )

        self.entrada.text = ""

        resposta = self.processar_comando(comando)

        self.adicionar_mensagem(
            "JARVIS",
            resposta
        )

    # ========================================================
    # ADICIONAR MENSAGEM
    # ========================================================

    def adicionar_mensagem(self, autor, texto):

        bloco = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            padding=[dp(10), dp(7)],
            spacing=dp(3),
        )

        titulo = Label(
            text=autor,
            font_size="12sp",
            bold=True,
            size_hint_y=None,
            height=dp(20),
            halign="left",
        )

        titulo.bind(
            size=lambda instance, value:
            setattr(instance, "text_size", value)
        )

        mensagem = Label(
            text=str(texto),
            font_size="15sp",
            size_hint_y=None,
            halign="left",
            valign="top",
        )

        mensagem.bind(
            texture_size=lambda instance, value:
            setattr(
                instance,
                "height",
                value[1] + dp(12)
            )
        )

        mensagem.bind(
            width=lambda instance, value:
            setattr(
                instance,
                "text_size",
                (value - dp(20), None)
            )
        )

        bloco.add_widget(titulo)
        bloco.add_widget(mensagem)

        bloco.height = dp(45)

        self.historico.add_widget(bloco)

        Clock.schedule_once(
            self.rolar_para_baixo,
            0.1
        )

    # ========================================================
    # ROLAR PARA BAIXO
    # ========================================================

    def rolar_para_baixo(self, *args):
        self.scroll.scroll_y = 0

    # ========================================================
    # PROCESSAR COMANDOS
    # ========================================================

    def processar_comando(self, comando):

        texto = comando.lower().strip()

        # -----------------------------------------------
        # SAUDAÇÕES
        # -----------------------------------------------

        if texto in [
            "oi",
            "olá",
            "ola",
            "hello",
            "hey",
            "e aí",
            "e ai",
        ]:
            return (
                "Olá! Estou online e pronto para executar "
                "seus comandos."
            )

        # -----------------------------------------------
        # IDENTIDADE
        # -----------------------------------------------

        if (
            "quem é você" in texto
            or "quem e voce" in texto
        ):
            return (
                "Eu sou o JARVIS, seu assistente pessoal."
            )

        # -----------------------------------------------
        # HORA
        # -----------------------------------------------

        if (
            "que horas" in texto
            or texto == "hora"
            or "horas são" in texto
            or "horas sao" in texto
        ):
            agora = datetime.now()

            return (
                "Agora são "
                + agora.strftime("%H:%M:%S")
                + "."
            )

        # -----------------------------------------------
        # DATA
        # -----------------------------------------------

        if (
            "qual a data" in texto
            or "que dia é hoje" in texto
            or "que dia e hoje" in texto
            or texto == "data"
        ):
            agora = datetime.now()

            return (
                "Hoje é "
                + agora.strftime("%d/%m/%Y")
                + "."
            )

        # -----------------------------------------------
        # AJUDA
        # -----------------------------------------------

        if (
            texto == "ajuda"
            or "o que você pode fazer" in texto
            or "o que voce pode fazer" in texto
        ):
            return (
                "Posso responder comandos básicos, "
                "informar hora e data, fazer cálculos, "
                "abrir pesquisas no Google e abrir o YouTube."
            )

        # -----------------------------------------------
        # CALCULADORA
        # -----------------------------------------------

        if texto.startswith("calcule "):
            expressao = texto[8:].strip()

            try:
                resultado = calcular(expressao)

                return (
                    f"O resultado é {resultado}."
                )

            except Exception:
                return (
                    "Não consegui calcular essa expressão."
                )

        if texto.startswith("quanto é "):
            expressao = texto[9:].strip()

            try:
                resultado = calcular(expressao)

                return (
                    f"O resultado é {resultado}."
                )

            except Exception:
                return (
                    "Não consegui calcular essa expressão."
                )

        # -----------------------------------------------
        # GOOGLE
        # -----------------------------------------------

        if texto.startswith("pesquise "):
            pesquisa = comando[9:].strip()

            if pesquisa:
                url = (
                    "https://www.google.com/search?q="
                    + quote_plus(pesquisa)
                )

                webbrowser.open(url)

                return (
                    "Abrindo uma pesquisa no Google sobre "
                    + pesquisa
                    + "."
                )

        if texto.startswith("pesquisar "):
            pesquisa = comando[10:].strip()

            if pesquisa:
                url = (
                    "https://www.google.com/search?q="
                    + quote_plus(pesquisa)
                )

                webbrowser.open(url)

                return (
                    "Abrindo uma pesquisa no Google sobre "
                    + pesquisa
                    + "."
                )

        # -----------------------------------------------
        # YOUTUBE
        # -----------------------------------------------

        if (
            "abrir youtube" in texto
            or texto == "youtube"
        ):
            webbrowser.open(
                "https://www.youtube.com"
            )

            return "Abrindo o YouTube."

        # -----------------------------------------------
        # GOOGLE
        # -----------------------------------------------

        if (
            "abrir google" in texto
            or texto == "google"
        ):
            webbrowser.open(
                "https://www.google.com"
            )

            return "Abrindo o Google."

        # -----------------------------------------------
        # ENCERRAR
        # -----------------------------------------------

        if texto in [
            "sair",
            "fechar",
            "encerrar",
        ]:
            return (
                "Comando recebido. "
                "O encerramento automático será "
                "implementado em uma próxima versão."
            )

        # -----------------------------------------------
        # COMANDO DESCONHECIDO
        # -----------------------------------------------

        return (
            "Ainda não conheço esse comando. "
            "Digite 'ajuda' para ver o que já posso fazer."
        )


# ============================================================
# INICIAR APLICATIVO
# ============================================================

if __name__ == "__main__":
    JarvisApp().run()
