from datetime import datetime
import ast
import operator as op
import webbrowser
from urllib.parse import quote_plus

from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.graphics import Color, RoundedRectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput


# ============================================================
# CALCULADORA SEGURA
# ============================================================

OPERADORES = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.FloorDiv: op.floordiv,
    ast.Mod: op.mod,
    ast.Pow: op.pow,
    ast.USub: op.neg,
    ast.UAdd: op.pos,
}


def calcular(expressao):

    expressao = expressao.replace(",", ".").strip()

    def visitar(no):

        if isinstance(no, ast.Expression):
            return visitar(no.body)

        if isinstance(no, ast.Constant):
            if isinstance(no.value, (int, float)):
                return no.value

        if isinstance(no, ast.UnaryOp):
            if type(no.op) in OPERADORES:
                return OPERADORES[type(no.op)](
                    visitar(no.operand)
                )

        if isinstance(no, ast.BinOp):
            if type(no.op) in OPERADORES:

                esquerda = visitar(no.left)
                direita = visitar(no.right)

                if isinstance(no.op, ast.Pow):
                    if abs(direita) > 10:
                        raise ValueError

                resultado = OPERADORES[type(no.op)](
                    esquerda,
                    direita
                )

                if abs(resultado) > 1000000000000:
                    raise ValueError

                return resultado

        raise ValueError

    arvore = ast.parse(expressao, mode="eval")

    return visitar(arvore)


# ============================================================
# APLICATIVO JARVIS
# ============================================================

class JarvisApp(App):

    def build(self):

        self.title = "JARVIS"

        raiz = BoxLayout(
            orientation="vertical",
            padding=dp(12),
            spacing=dp(10)
        )

        # FUNDO
        with raiz.canvas.before:
            Color(0.02, 0.03, 0.05, 1)

            self.fundo = RoundedRectangle(
                pos=raiz.pos,
                size=raiz.size
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
            height=dp(65)
        )

        titulo = Label(
            text="[b]JARVIS[/b]",
            markup=True,
            font_size=dp(28),
            color=(0.4, 0.8, 1, 1),
            halign="left",
            valign="middle"
        )

        titulo.bind(
            size=lambda obj, value:
            setattr(obj, "text_size", value)
        )

        status = Label(
            text="● ONLINE  •  Assistente local",
            font_size=dp(12),
            color=(0.3, 0.9, 0.5, 1),
            halign="left"
        )

        status.bind(
            size=lambda obj, value:
            setattr(obj, "text_size", value)
        )

        cabecalho.add_widget(titulo)
        cabecalho.add_widget(status)

        raiz.add_widget(cabecalho)

        # ====================================================
        # HISTÓRICO
        # ====================================================

        self.scroll = ScrollView(
            do_scroll_x=False,
            bar_width=dp(4)
        )

        self.historico = BoxLayout(
            orientation="vertical",
            spacing=dp(8),
            padding=dp(3),
            size_hint_y=None
        )

        self.historico.bind
