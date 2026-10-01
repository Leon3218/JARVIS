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

        if isinstance(no, ast.Constant) and isinstance(no.value, (int, float)):
            return no.value

        if isinstance(no, ast.UnaryOp) and type(no.op) in OPERADORES:
            return OPERADORES[type(no.op)](visitar(no.operand))

        if isinstance(no, ast.BinOp) and type(no.op) in OPERADORES:
            esquerda = visitar(no.left)
            direita = visitar(no.right)

            if isinstance(no.op, ast.Pow) and abs(direita) > 10:
                raise ValueError("Potência muito grande.")

            resultado = OPERADORES[type(no.op)](esquerda, direita)

            if abs(resultado) > 1000000000000:
                raise ValueError("Resultado muito grande.")

            return resultado

        raise ValueError("Expressão inválida.")

    return visitar(ast.parse(expressao, mode="eval"))


class JarvisApp(App):
    def build(self):
        self.title = "JARVIS"

        raiz = BoxLayout(
            orientation="vertical",
            padding=dp(12),
            spacing=dp(10),
        )

        with raiz.canvas.before:
            Color(0.02, 0.03, 0.06, 1)
            self.fundo = RoundedRectangle(
                pos=raiz.pos,
                size=raiz.size,
                radius=[dp(18)],
            )

        raiz.bind(pos=self.atualizar_fundo, size=self.atualizar_fundo)

        cabecalho = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=dp(75),
        )

        titulo = Label(
            text="[b]JARVIS[/b]",
            markup=True,
            font_size=dp(28),
            color=(0.35, 0.8, 1, 1),
            halign="left",
            valign="middle",
        )
        titulo.bind(size=lambda obj, value: setattr(obj, "text_size", value))

        status = Label(
            text="● ONLINE  •  Assistente local",
            font_size=dp(12),
            color=(0.3, 0.9, 0.5, 1),
            halign="left",
            valign="middle",
        )
        status.bind(size=lambda obj, value: setattr(obj, "text_size", value))

        cabecalho.add_widget(titulo)
        cabecalho.add_widget(status)
        raiz.add_widget(cabecalho)

        self.scroll = ScrollView(
            do_scroll_x=False,
            bar_width=dp(4),
        )

        self.historico = BoxLayout(
            orientation="vertical",
            spacing=dp(8),
            padding=dp(4),
            size_hint_y=None,
        )
        self.historico.bind(
            minimum_height=self.historico.setter("height")
        )

        self.scroll.add_widget(self.historico)
        raiz.add_widget(self.scroll)

        entrada_linha = BoxLayout(
            size_hint_y=None,
            height=dp(55),
            spacing=dp(8),
        )

        self.entrada = TextInput(
            hint_text="Digite um comando...",
            multiline=False,
            font_size=dp(16),
            padding=[dp(12), dp(15)],
            background_color=(0.08, 0.10, 0.14, 1),
            foreground_color=(1, 1, 1, 1),
            cursor_color=(0.35, 0.8, 1, 1),
        )
        self.entrada.bind(on_text_validate=self.enviar)

        enviar = Button(
            text="ENVIAR",
            size_hint_x=None,
            width=dp(105),
            font_size=dp(14),
            background_normal="",
            background_color=(0.1, 0.45, 0.75, 1),
        )
        enviar.bind(on_release=self.enviar)

        entrada_linha.add_widget(self.entrada)
        entrada_linha.add_widget(enviar)
        raiz.add_widget(entrada_linha)

        atalhos = BoxLayout(
            size_hint_y=None,
            height=dp(42),
            spacing=dp(6),
        )

        for texto, comando in [
            ("HORAS", "que horas são"),
            ("DATA", "qual a data"),
            ("AJUDA", "ajuda"),
        ]:
            botao = Button(
                text=texto,
                font_size=dp(12),
                background_normal="",
                background_color=(0.12, 0.14, 0.19, 1),
            )
            botao.bind(
                on_release=lambda btn, cmd=comando: self.comando_atalho(cmd)
            )
            atalhos.add_widget(botao)

        raiz.add_widget(atalhos)

        self.adicionar_mensagem(
            "JARVIS",
            "Olá! Estou online. Digite um comando para começar.",
        )

        return raiz

    def atualizar_fundo(self, widget, *args):
        self.fundo.pos = widget.pos
        self.fundo.size = widget.size

    def comando_atalho(self, comando):
        self.entrada.text = comando
        self.enviar()

    def enviar(self, *args):
        texto = self.entrada.text.strip()
        if not texto:
            return

        self.adicionar_mensagem("VOCÊ", texto)
        self.entrada.text = ""

        resposta = self.processar_comando(texto)
        self.adicionar_mensagem("JARVIS", resposta)

    def adicionar_mensagem(self, autor, texto):
        cor = (0.15, 0.18, 0.24, 1) if autor == "VOCÊ" else (0.07, 0.12, 0.17, 1)

        caixa = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            padding=dp(10),
            spacing=dp(3),
        )

        with caixa.canvas.before:
            Color(*cor)
            fundo = RoundedRectangle(
                pos=caixa.pos,
                size=caixa.size,
                radius=[dp(12)],
            )

        caixa.bind(
            pos=lambda obj, value, bg=fundo: setattr(bg, "pos", value),
            size=lambda obj, value, bg=fundo: setattr(bg, "size", value),
        )

        cab = Label(
            text=f"[b]{autor}[/b]",
            markup=True,
            font_size=dp(11),
            color=(0.35, 0.8, 1, 1) if autor == "JARVIS" else (0.8, 0.8, 0.85, 1),
            size_hint_y=None,
            height=dp(20),
            halign="left",
        )
        cab.bind(size=lambda obj, value: setattr(obj, "text_size", value))

        msg = Label(
            text=texto,
            font_size=dp(15),
            color=(1, 1, 1, 1),
            halign="left",
            valign="top",
            size_hint_y=None,
        )

        def ajustar(label, size):
            label.text_size = (size[0], None)
            label.texture_update()
            label.height = label.texture_size[1] + dp(6)

        msg.bind(size=ajustar)
        msg.text_size = (dp(280), None)
        msg.texture_update()
        msg.height = msg.texture_size[1] + dp(6)

        caixa.add_widget(cab)
        caixa.add_widget(msg)

        self.historico.add_widget(caixa)
        Clock.schedule_once(
            lambda dt: setattr(self.scroll, "scroll_y", 0), 0.05
        )

    def processar_comando(self, texto):
        comando = texto.lower().strip()

        if comando in ("oi", "olá", "ola", "bom dia", "boa tarde", "boa noite"):
            hora = datetime.now().hour
            if hora < 12:
                periodo = "Bom dia"
            elif hora < 18:
                periodo = "Boa tarde"
            else:
                periodo = "Boa noite"
            return f"{periodo}! Como posso ajudar?"

        if "que horas" in comando or comando == "hora":
            return "Agora são " + datetime.now().strftime("%H:%M:%S") + "."

        if "data" in comando or "dia é hoje" in comando or "dia e hoje" in comando:
            return "Hoje é " + datetime.now().strftime("%d/%m/%Y") + "."

        if comando in ("ajuda", "help", "comandos", "menu"):
            return (
                "Comandos disponíveis:\n"
                "• que horas são\n"
                "• qual a data\n"
                "• calcule 25*4\n"
                "• pesquisar no Google ...\n"
                "• abrir YouTube\n"
                "• sair"
            )

        if comando.startswith(("calcule ", "calcular ", "quanto é ", "quanto e ")):
            expressao = comando.split(" ", 1)[1]
            try:
                resultado = calcular(expressao)
                return f"Resultado: {resultado:g}"
            except Exception:
                return "Não consegui calcular essa expressão."

        if comando.startswith(("pesquisar ", "pesquise ", "buscar ")):
            consulta = comando.split(" ", 1)[1].strip()
            if not consulta:
                return "Digite o que deseja pesquisar."
            webbrowser.open(
                "https://www.google.com/search?q=" + quote_plus(consulta)
            )
            return f"Pesquisando por: {consulta}"

        if "youtube" in comando:
            webbrowser.open("https://www.youtube.com")
            return "Abrindo o YouTube."

        if comando in ("sair", "fechar", "encerrar"):
            return "Comando recebido. Você pode fechar o aplicativo pelo sistema."

        try:
            resultado = calcular(comando)
            return f"Resultado: {resultado:g}"
        except Exception:
            return (
                "Ainda não conheço esse comando. Digite 'ajuda' para ver "
                "o que já posso fazer."
            )

return raiz
if __name__ == "__main__":
    JarvisApp().run()
        
