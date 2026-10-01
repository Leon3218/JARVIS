
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button


class JarvisApp(App):

    def build(self):
        layout = BoxLayout(
            orientation="vertical",
            padding=20,
            spacing=15
        )

        titulo = Label(
            text="🤖 JARVIS",
            font_size=32
        )

        resposta = Label(
            text="Olá, Edrin!\nComo posso ajudar?",
            font_size=22
        )

        entrada = TextInput(
            hint_text="Digite seu comando...",
            multiline=False,
            font_size=20
        )

        botao = Button(
            text="ENVIAR",
            font_size=20,
            size_hint_y=None,
            height=60
        )

        def responder(instance):
            mensagem = entrada.text
            resposta.text = "🤖 JARVIS:\n" + mensagem
            entrada.text = ""

        botao.bind(on_press=responder)

        layout.add_widget(titulo)
        layout.add_widget(resposta)
        layout.add_widget(entrada)
        layout.add_widget(botao)

        return layout


if __name__ == "__main__":
    JarvisApp().run()
