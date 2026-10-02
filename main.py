# -*- coding: utf-8 -*-
"""
JARVIS V7.1 DEFINITIVO
Android/Kivy HUD inspired by the supplied 16-panel JARVIS reference.
No API key is embedded in the project.
"""
import os, json, sqlite3, threading, urllib.parse, urllib.request, webbrowser, math
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle, Line, Ellipse

try:
    from android.runnable import run_on_ui_thread
except Exception:
    def run_on_ui_thread(fn): return fn

try:
    from jnius import autoclass, PythonJavaClass, java_method
    PYJNIUS = True
except Exception:
    PYJNIUS = False
    PythonJavaClass = object
    def java_method(_signature):
        return lambda fn: fn

APP_NAME = "JARVIS"
VERSION = "7.1"
BG = (0.003, 0.008, 0.016, 1)
PANEL = (0.006, 0.025, 0.042, 0.98)
CYAN = (0.04, 0.82, 1.0, 1)
CYAN2 = (0.10, 0.55, 0.75, 1)
WHITE = (0.78, 0.94, 1.0, 1)
DIM = (0.30, 0.65, 0.76, 1)

class DB:
    def __init__(self, path):
        self.lock = threading.RLock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY, role TEXT, text TEXT, created TEXT)")
        self.db.execute("CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY, text TEXT, done INTEGER DEFAULT 0, created TEXT)")
        self.db.commit()

    def add_message(self, role, text):
        with self.lock:
            self.db.execute("INSERT INTO messages(role,text,created) VALUES(?,?,?)",
                            (role, str(text), datetime.now().isoformat(timespec="seconds")))
            self.db.commit()

    def history(self, n=20):
        with self.lock:
            rows = self.db.execute(
                "SELECT role,text FROM messages ORDER BY id DESC LIMIT ?", (int(n),)
            ).fetchall()
        return list(reversed(rows))

    def add_task(self, text):
        with self.lock:
            self.db.execute("INSERT INTO tasks(text) VALUES(?)", (text,))
            self.db.commit()

    def tasks(self):
        with self.lock:
            return self.db.execute("SELECT id,text,done FROM tasks ORDER BY id DESC LIMIT 50").fetchall()

    def toggle_task(self, task_id):
        with self.lock:
            self.db.execute("UPDATE tasks SET done=CASE done WHEN 0 THEN 1 ELSE 0 END WHERE id=?", (task_id,))
            self.db.commit()

    def close(self):
        try:
            self.db.close()
        except Exception:
            pass

class Android:
    tts = None
    tts_listener = None
    tts_ready = False
    tts_lock = threading.RLock()

    @staticmethod
    def activity():
        return autoclass("org.kivy.android.PythonActivity").mActivity if PYJNIUS else None

    @staticmethod
    def speak(text):
        if not PYJNIUS:
            return
        try:
            T = autoclass("android.speech.tts.TextToSpeech")
            with Android.tts_lock:
                if Android.tts is None:
                    class Listener(PythonJavaClass):
                        __javainterfaces__ = ["android/speech/tts/TextToSpeech$OnInitListener"]
                        __javacontext__ = "app"
                        @java_method("(I)V")
                        def onInit(self, status):
                            try:
                                Android.tts.setLanguage(autoclass("java.util.Locale")("pt", "BR"))
                                Android.tts_ready = status == 0
                            except Exception:
                                Android.tts_ready = False
                    Android.tts_listener = Listener()
                    Android.tts = T(Android.activity(), Android.tts_listener)
                if Android.tts_ready:
                    Android.tts.speak(str(text), T.QUEUE_FLUSH, None, "jarvis")
        except Exception:
            pass

    @staticmethod
    def open_url(url):
        try:
            if PYJNIUS:
                I = autoclass("android.content.Intent")
                U = autoclass("android.net.Uri")
                Android.activity().startActivity(I(I.ACTION_VIEW, U.parse(url)))
            else:
                webbrowser.open(url)
            return True
        except Exception:
            return False

    @staticmethod
    def launch(pkg):
        if not PYJNIUS:
            return False
        try:
            a = Android.activity()
            intent = a.getPackageManager().getLaunchIntentForPackage(pkg)
            if intent:
                a.startActivity(intent)
                return True
        except Exception:
            pass
        return False

    @staticmethod
    def intent(action, data=None, mime=None, category=None):
        if not PYJNIUS:
            return False
        try:
            I = autoclass("android.content.Intent")
            i = I(action)
            if data:
                U = autoclass("android.net.Uri")
                i.setData(U.parse(data))
            if mime:
                i.setType(mime)
            if category:
                i.addCategory(category)
            Android.activity().startActivity(i)
            return True
        except Exception:
            return False

    @staticmethod
    def battery():
        if not PYJNIUS:
            return None
        try:
            I = autoclass("android.content.Intent")
            F = autoclass("android.content.IntentFilter")
            b = Android.activity().registerReceiver(None, F("android.intent.action.BATTERY_CHANGED"))
            level = b.getIntExtra("level", -1)
            scale = b.getIntExtra("scale", -1)
            return int(level * 100 / scale) if level >= 0 and scale > 0 else None
        except Exception:
            return None

    @staticmethod
    def flashlight(on=True):
        if not PYJNIUS:
            return False
        try:
            a = Android.activity()
            camera_perm = "android.permission.CAMERA"
            if int(a.checkSelfPermission(camera_perm)) != 0:
                a.requestPermissions([camera_perm], 7002)
                return False
            cm = a.getSystemService("camera")
            CC = autoclass("android.hardware.camera2.CameraCharacteristics")
            CM = autoclass("android.hardware.camera2.CameraMetadata")
            for cid in cm.getCameraIdList():
                try:
                    c = cm.getCameraCharacteristics(cid)
                    if c.get(CC.LENS_FACING) == CM.LENS_FACING_BACK and c.get(CC.FLASH_INFO_AVAILABLE):
                        cmgr = cm
                        cmgr.setTorchMode(cid, on)
                        return True
                except Exception:
                    continue
        except Exception:
            pass
        return False

    @staticmethod
    def system_memory():
        if not PYJNIUS:
            return None
        try:
            AM = autoclass("android.app.ActivityManager")
            info = AM.MemoryInfo()
            Android.activity().getSystemService("activity").getMemoryInfo(info)
            total = int(info.totalMem / (1024**3))
            avail = int(info.availMem / (1024**3))
            return total, avail
        except Exception:
            return None

    @staticmethod
    def share_text(text):
        if not PYJNIUS:
            return False
        try:
            I = autoclass("android.content.Intent")
            i = I(I.ACTION_SEND)
            i.setType("text/plain")
            i.putExtra(I.EXTRA_TEXT, str(text))
            Android.activity().startActivity(I.createChooser(i, "Compartilhar com JARVIS"))
            return True
        except Exception:
            return False

    @staticmethod
    def dial(number=""):
        data = "tel:" + urllib.parse.quote(str(number).strip()) if str(number).strip() else None
        return Android.intent("android.intent.action.DIAL", data)

    @staticmethod
    def sms(number=""):
        data = "smsto:" + urllib.parse.quote(str(number).strip()) if str(number).strip() else "smsto:"
        return Android.intent("android.intent.action.SENDTO", data)

    @staticmethod
    def app_details():
        if not PYJNIUS:
            return False
        try:
            a = Android.activity()
            I = autoclass("android.content.Intent")
            U = autoclass("android.net.Uri")
            a.startActivity(I("android.settings.APPLICATION_DETAILS_SETTINGS", U.parse("package:" + str(a.getPackageName()))))
            return True
        except Exception:
            return False

class SpeechListener(PythonJavaClass):
    __javainterfaces__ = ["android/speech/RecognitionListener"]
    __javacontext__ = "app"
    def __init__(self, result, error):
        super().__init__()
        self.result_cb = result
        self.error_cb = error

    @java_method("(Landroid/os/Bundle;)V")
    def onReadyForSpeech(self, p): pass
    @java_method("()V")
    def onBeginningOfSpeech(self): pass
    @java_method("(F)V")
    def onRmsChanged(self, v): pass
    @java_method("([B)V")
    def onBufferReceived(self, b): pass
    @java_method("()V")
    def onEndOfSpeech(self): pass
    @java_method("(I)V")
    def onError(self, e):
        Clock.schedule_once(lambda *_: self.error_cb(e), 0)
    @java_method("(Landroid/os/Bundle;)V")
    def onResults(self, r):
        try:
            values = r.getStringArrayList("results_recognition")
            text = str(values.get(0)) if values and values.size() else ""
            Clock.schedule_once(lambda *_: self.result_cb(text), 0)
        except Exception:
            Clock.schedule_once(lambda *_: self.error_cb(8), 0)
    @java_method("(Landroid/os/Bundle;)V")
    def onPartialResults(self, p): pass
    @java_method("(ILandroid/os/Bundle;)V")
    def onEvent(self, e, p): pass

class Voice:
    def __init__(self, result, error):
        self.result_cb, self.error_cb = result, error
        self.recognizer = None
        self.listener = None

    def start(self):
        if not PYJNIUS:
            self.error_cb(0)
            return False
        try:
            a = Android.activity()
            perm = "android.permission.RECORD_AUDIO"
            if int(a.checkSelfPermission(perm)) != 0:
                a.requestPermissions([perm], 7001)
                return False
            SR = autoclass("android.speech.SpeechRecognizer")
            RI = autoclass("android.speech.RecognizerIntent")
            if not SR.isRecognitionAvailable(a):
                self.error_cb(9)
                return False
            self.listener = SpeechListener(self.result_cb, self.error_cb)
            self.recognizer = SR.createSpeechRecognizer(a)
            self.recognizer.setRecognitionListener(self.listener)
            I = autoclass("android.content.Intent")
            i = I(RI.ACTION_RECOGNIZE_SPEECH)
            i.putExtra(RI.EXTRA_LANGUAGE_MODEL, RI.LANGUAGE_MODEL_FREE_FORM)
            i.putExtra(RI.EXTRA_LANGUAGE, "pt-BR")
            i.putExtra(RI.EXTRA_MAX_RESULTS, 3)
            self.recognizer.startListening(i)
            return True
        except Exception:
            self.error_cb(10)
            return False

    def stop(self):
        try:
            if self.recognizer:
                self.recognizer.stopListening()
                self.recognizer.cancel()
                self.recognizer.destroy()
        except Exception:
            pass
        self.recognizer = None
        self.listener = None

class AIClient:
    """OpenAI-compatible connector. The key is stored only on the device."""
    def __init__(self, path):
        self.path = path
        self.settings = {
            "enabled": False,
            "endpoint": "https://api.openai.com/v1/chat/completions",
            "model": "gpt-4o-mini",
            "api_key": "",
            "system": "Você é JARVIS, assistente pessoal Android. Responda em português do Brasil. Seja útil, claro e nunca invente ações executadas."
        }
        self.load()

    def load(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                self.settings.update(json.load(f))
        except Exception:
            pass

    def save(self, values):
        self.settings.update(values)
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, ensure_ascii=False)
        os.replace(tmp, self.path)

    def ask(self, prompt, history):
        s = dict(self.settings)
        if not s.get("enabled") or not s.get("api_key"):
            return None
        endpoint = str(s.get("endpoint", "")).strip()
        if not endpoint.startswith("https://"):
            return "A IA exige um endpoint HTTPS."
        messages = [{"role": "system", "content": s.get("system", "")}]
        for role, text in history[-10:]:
            messages.append({"role": role if role in ("user", "assistant") else "user", "content": text[:2000]})
        messages.append({"role": "user", "content": str(prompt)[:4000]})
        payload = {
            "model": s.get("model", "gpt-4o-mini"),
            "messages": messages,
            "temperature": 0.2
        }
        try:
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode(),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + s.get("api_key", "")
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.loads(r.read(2_000_000).decode("utf-8", "replace"))
            return str(data.get("choices", [{}])[0].get("message", {}).get("content", "")).strip() or None
        except Exception:
            return None

class Reactor(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.phase = 0
        self.active = True
        self.ev = Clock.schedule_interval(self.tick, 1/18)
        self.bind(pos=self.draw, size=self.draw)

    def tick(self, dt):
        if self.active:
            self.phase = (self.phase + dt * 40) % 360
            self.draw()

    def draw(self, *_):
        self.canvas.clear()
        cx, cy = self.center
        r = min(self.width, self.height) * .40
        with self.canvas:
            Color(.02, .45, .65, .10)
            Ellipse(pos=(cx-r*1.35, cy-r*1.35), size=(r*2.7, r*2.7))
            for i in range(5):
                rr = r * (1 - i*.14)
                Color(.02, .65, .95, .65 - i*.08)
                Line(circle=(cx, cy, rr, self.phase+i*45, self.phase+275+i*45), width=1.2)
            Color(.10, .80, 1, .25)
            Ellipse(pos=(cx-r*.40, cy-r*.40), size=(r*.8, r*.8))
            Color(.60, .98, 1, 1)
            Ellipse(pos=(cx-r*.13, cy-r*.13), size=(r*.26, r*.26))

class NeonPanel(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self.draw, size=self.draw)
        self.draw()
    def draw(self, *_):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*PANEL)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(12)])
            Color(.02, .50, .75, .85)
            Line(rounded_rectangle=(self.x, self.y, self.width, self.height, dp(12)), width=1)

class Wave(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.t = 0
        self.active = False
        self.ev = Clock.schedule_interval(self.tick, 1/18)
    def tick(self, dt):
        if self.active:
            self.t += dt
            self.canvas.clear()
            with self.canvas:
                Color(.05, .75, 1, .9)
                pts = []
                for i in range(90):
                    x = self.x + i*self.width/89
                    y = self.center_y + math.sin(i*.48+self.t*7) * self.height*.34 * (0.3+0.7*math.sin(i*.19+self.t)**2)
                    pts += [x,y]
                Line(points=pts, width=1.2)

class JButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_color = (.006,.045,.075,1)
        self.color = CYAN
        self.font_size = dp(9)
        self.bold = True

class SectionScreen(Screen):
    def __init__(self, section, title, subtitle, **kwargs):
        super().__init__(**kwargs)
        self.section = section
        self.title_text = title
        self.subtitle = subtitle
        self.app = None
    def on_pre_enter(self, *args):
        if not self.app:
            self.app = App.get_running_app()
            self.build_ui()
    def build_ui(self):
        root = BoxLayout(orientation="vertical", padding=dp(7), spacing=dp(6))
        root.add_widget(self.app.header(self.title_text, self.subtitle))
        body = BoxLayout(spacing=dp(6))
        body.add_widget(self.app.sidebar(self.section))
        content = BoxLayout(orientation="vertical", spacing=dp(6))
        content.add_widget(self.content())
        root.add_widget(body)
        body.children[0]  # keep explicit layout reference
        body.children[-1]  # no-op for readability
        # replace body with sidebar + content
        body.clear_widgets()
        body.add_widget(self.app.sidebar(self.section))
        body.add_widget(content)
        root.children[0] = root.children[0]
        self.add_widget(root)
    def content(self):
        return Label(text=self.title_text, color=WHITE)

class JARVIS(App):
    title = "JARVIS V7.1"
    def build(self):
        Window.clearcolor = BG
        Window.softinput_mode = "below_target"
        self.db = DB(os.path.join(self.user_data_dir, "jarvis.db"))
        self.ai = AIClient(os.path.join(self.user_data_dir, "ai.json"))
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.voice = Voice(self.voice_result, self.voice_error)
        self.night = True
        self.listening = False
        self.sm = ScreenManager(transition=FadeTransition(duration=.12))
        self.screens = {}
        specs = [
            ("home","JARVIS","SEU ASSISTENTE INTELIGENTE",self.home_content),
            ("system","SISTEMA","MONITOR DO DISPOSITIVO",self.system_content),
            ("apps","APLICATIVOS","CENTRAL DE APLICATIVOS",self.apps_content),
            ("internet","INTERNET","WEB / NAVEGADOR",self.internet_content),
            ("media","MÍDIA","PLAYER / ENTRETENIMENTO",self.media_content),
            ("contacts","CONTATOS","PESSOAS / COMUNICAÇÃO",self.contacts_content),
            ("maps","MAPAS","GPS / ROTAS",self.maps_content),
            ("settings","CONFIGURAÇÕES","PREFERÊNCIAS DO JARVIS",self.settings_content),
            ("security","SEGURANÇA","PRIVACIDADE / DISPOSITIVO",self.security_content),
            ("camera","CÂMERA","CAPTURA DE FOTO E VÍDEO",self.camera_content),
            ("calendar","CALENDÁRIO","AGENDA / EVENTOS",self.calendar_content),
            ("weather","CLIMA","TEMPO / PREVISÃO",self.weather_content),
            ("tasks","TAREFAS","TAREFAS / LEMBRETES",self.tasks_content),
            ("voice","ASSISTENTE DE VOZ","ESCUTA / FALA",self.voice_content),
            ("files","ARQUIVOS","DOCUMENTOS / ARMAZENAMENTO",self.files_content),
            ("night","MODO NOTURNO","HUD / CONFORTO VISUAL",self.night_content),
            ("tools","FERRAMENTAS","AÇÕES RÁPIDAS",self.tools_content),
        ]
        for name,title,sub,fn in specs:
            screen = SectionScreen(name,title,sub,name=name)
            screen.content = fn
            self.screens[name] = screen
            self.sm.add_widget(screen)
        self.sm.current = "home"
        Clock.schedule_interval(self.refresh_top, 5)
        return self.sm

    def header(self, title, subtitle):
        b = BoxLayout(size_hint_y=None, height=dp(54), spacing=dp(6))
        home = JButton(text="⌂", size_hint_x=None, width=dp(38), font_size=dp(22))
        home.bind(on_release=lambda *_: self.go("home"))
        b.add_widget(home)
        mid = BoxLayout(orientation="vertical")
        mid.add_widget(Label(text=title, color=CYAN, font_size=dp(18), bold=True))
        mid.add_widget(Label(text=subtitle, color=DIM, font_size=dp(7)))
        b.add_widget(mid)
        b.add_widget(Label(text="● ONLINE", color=CYAN, size_hint_x=None, width=dp(72), font_size=dp(9)))
        return b

    def sidebar(self, current):
        items = [
            ("⌂","home"),("◈","system"),("▦","apps"),("⌕","internet"),
            ("♫","media"),("♙","contacts"),("⌖","maps"),("⚙","settings"),
            ("▣","security"),("◉","camera"),("▤","calendar"),("☁","weather"),
            ("✓","tasks"),("♟","voice"),("□","files"),("☾","night"),("✦","tools")
        ]
        s = BoxLayout(orientation="vertical", size_hint_x=None, width=dp(42), spacing=dp(3))
        for icon,name in items:
            btn = JButton(text=icon, font_size=dp(17))
            if name == current:
                btn.background_color = (.02,.30,.42,1)
            btn.bind(on_release=lambda _, n=name: self.go(n))
            s.add_widget(btn)
        return s

    def panel(self, title, content=None, height=None):
        holder = BoxLayout(orientation="vertical", padding=dp(9), spacing=dp(5), size_hint_y=None if height else 1)
        if height:
            holder.height = dp(height)
        holder.add_widget(Label(text=title, color=CYAN, font_size=dp(10), bold=True, size_hint_y=None, height=dp(22), halign="left"))
        if content:
            holder.add_widget(content)
        w = NeonPanel()
        # Widget cannot contain children in a useful BoxLayout way, so return a styled layout using canvas.
        holder.canvas.before.add(Color(*PANEL))
        holder.canvas.before.add(RoundedRectangle(pos=holder.pos,size=holder.size,radius=[dp(12)]))
        holder.bind(pos=lambda *_: None)
        return holder

    def card(self, title, text, action=None):
        box = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(4))
        box.add_widget(Label(text=title, color=CYAN, font_size=dp(11), bold=True, size_hint_y=None, height=dp(22)))
        box.add_widget(Label(text=text, color=WHITE, font_size=dp(10), halign="left", valign="top"))
        if action:
            btn = JButton(text=action[0], size_hint_y=None, height=dp(34))
            btn.bind(on_release=lambda *_: action[1]())
            box.add_widget(btn)
        box.canvas.before.add(Color(*PANEL))
        rr = RoundedRectangle(pos=box.pos, size=box.size, radius=[dp(12)])
        box.canvas.before.add(rr)
        box.bind(pos=lambda w,p: setattr(rr,"pos",p), size=lambda w,s: setattr(rr,"size",s))
        return box

    def content_grid(self, widgets, cols=2):
        g = GridLayout(cols=cols, spacing=dp(6), size_hint_y=None)
        g.bind(minimum_height=g.setter("height"))
        for w in widgets: g.add_widget(w)
        sv = ScrollView(do_scroll_x=False)
        sv.add_widget(g)
        return sv

    def go(self, name):
        if name in self.screens:
            self.sm.current = name

    # 1
    def home_content(self):
        modules = [
            ("⌂", "SISTEMA", "Monitor", "system"), ("▦", "APLICATIVOS", "Apps", "apps"),
            ("⌕", "INTERNET", "Navegador", "internet"), ("♫", "MÍDIA", "Player", "media"),
            ("♙", "CONTATOS", "Comunicação", "contacts"), ("⌖", "MAPAS", "GPS / Rotas", "maps"),
            ("⚙", "CONFIGURAÇÕES", "Android / IA", "settings"), ("▣", "SEGURANÇA", "Privacidade", "security"),
            ("◉", "CÂMERA", "Foto / Vídeo", "camera"), ("▤", "CALENDÁRIO", "Agenda", "calendar"),
            ("☁", "CLIMA", "Previsão", "weather"), ("✓", "TAREFAS", "Lembretes", "tasks"),
            ("♟", "VOZ", "Escutar / Falar", "voice"), ("□", "ARQUIVOS", "Documentos", "files"),
            ("☾", "NOTURNO", "HUD", "night"), ("✦", "FERRAMENTAS", "Ações rápidas", "tools"),
        ]
        root = BoxLayout(orientation="vertical", spacing=dp(6))
        status = BoxLayout(size_hint_y=None, height=dp(28), spacing=dp(6))
        self.home_clock = Label(text=datetime.now().strftime("%H:%M"), color=CYAN, font_size=dp(12), bold=True, size_hint_x=None, width=dp(58))
        self.home_status = Label(text="JARVIS ONLINE  •  LAUNCHER", color=DIM, font_size=dp(8), halign="left")
        self.home_battery = Label(text="BAT --%", color=WHITE, font_size=dp(9), size_hint_x=None, width=dp(58))
        status.add_widget(self.home_clock); status.add_widget(self.home_status); status.add_widget(self.home_battery); root.add_widget(status)

        hero = BoxLayout(size_hint_y=None, height=dp(125), spacing=dp(6))
        intro = self.card("JARVIS", "Olá. Eu sou o JARVIS.\nLauncher inteligente do seu Android.\n\nToque em um setor ou fale um comando.")
        reactor_box = BoxLayout(); reactor_box.add_widget(Reactor())
        hero.add_widget(intro); hero.add_widget(reactor_box); root.add_widget(hero)

        grid = GridLayout(cols=4, spacing=dp(4), size_hint_y=None, padding=dp(1))
        grid.bind(minimum_height=grid.setter("height"))
        for icon, title, sub, name in modules:
            b = JButton(text=f"{icon}\n{title}\n{sub}", font_size=dp(8))
            b.bind(on_release=lambda _, n=name: self.go(n))
            grid.add_widget(b)
        sv = ScrollView(do_scroll_x=False, bar_width=dp(2)); sv.add_widget(grid); root.add_widget(sv)

        self.home_wave = Wave(size_hint_y=None, height=dp(34)); root.add_widget(self.home_wave)
        self.home_log = Label(text="Sistema pronto. Aguardando comando...", color=WHITE, font_size=dp(9), halign="left", valign="middle", size_hint_y=None, height=dp(28))
        root.add_widget(self.home_log)
        inp = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(4))
        self.command = TextInput(hint_text="Fale ou digite um comando...", multiline=False, font_size=dp(10), background_normal="", background_color=(.01,.05,.08,1), foreground_color=WHITE)
        self.command.bind(on_text_validate=lambda *_: self.send())
        mic = JButton(text="🎙", size_hint_x=None, width=dp(44)); mic.bind(on_release=lambda *_: self.start_voice())
        send = JButton(text="➤", size_hint_x=None, width=dp(44)); send.bind(on_release=lambda *_: self.send())
        inp.add_widget(mic); inp.add_widget(self.command); inp.add_widget(send); root.add_widget(inp)
        return root

    def tools_content(self):
        return self.content_grid([
            self.card("LANTERNA", "Liga ou desliga a lanterna traseira.", ("ALTERNAR", lambda: self.toggle_flash())),
            self.card("TELEFONE", "Abre o discador do Android.", ("ABRIR", lambda: Android.dial())),
            self.card("MENSAGEM", "Abre o aplicativo de mensagens.", ("ABRIR", lambda: Android.sms())),
            self.card("COMPARTILHAR", "Compartilha uma mensagem do JARVIS.", ("COMPARTILHAR", lambda: Android.share_text("Enviado pelo JARVIS."))),
            self.card("CONFIGURAÇÕES DO APP", "Permissões e informações do JARVIS.", ("ABRIR", lambda: Android.app_details())),
            self.card("WI-FI", "Abra as configurações de Wi-Fi.", ("ABRIR", lambda: Android.intent("android.settings.WIFI_SETTINGS"))),
            self.card("BLUETOOTH", "Abra as configurações de Bluetooth.", ("ABRIR", lambda: Android.intent("android.settings.BLUETOOTH_SETTINGS"))),
            self.card("TELA", "Brilho, rotação e configurações de tela.", ("ABRIR", lambda: Android.intent("android.settings.DISPLAY_SETTINGS"))),
        ],2)

    def toggle_flash(self):
        self._flash_state = not getattr(self, "_flash_state", False)
        ok = Android.flashlight(self._flash_state)
        if not ok:
            self._flash_state = not self._flash_state
        if ok:
            self.notify("JARVIS: "+("Lanterna ligada." if self._flash_state else "Lanterna desligada."))
        else:
            self.notify("JARVIS: não consegui controlar a lanterna.")

    # 2
    def system_content(self):
        b = Android.battery()
        mem = Android.system_memory()
        total,avail = mem if mem else ("--","--")
        cards = [
            self.card("DISPOSITIVO", "Android\nArquitetura: arm64-v8a\nBateria: %s%%" % (b if b is not None else "--")),
            self.card("MEMÓRIA", "RAM total: %s GB\nRAM livre: %s GB" % (total,avail)),
            self.card("DIAGNÓSTICO", "JARVIS V7.1\nMotor local ativo\nConector de IA opcional"),
            self.card("AÇÕES", "Configurações do Android", ("ABRIR CONFIGURAÇÕES", lambda: Android.intent("android.settings.SETTINGS")))
        ]
        return self.content_grid(cards,2)

    # 3
    def apps_content(self):
        apps = [
            ("Play Store","com.android.vending"),("YouTube","com.google.android.youtube"),
            ("WhatsApp","com.whatsapp"),("Instagram","com.instagram.android"),
            ("Chrome","com.android.chrome"),("Gmail","com.google.android.gm"),
            ("Maps","com.google.android.apps.maps"),("Spotify","com.spotify.music"),
            ("Telegram","org.telegram.messenger"),("Câmera","camera")
        ]
        cards=[]
        for name,pkg in apps:
            action = (("ABRIR "+name.upper()), (lambda p=pkg,n=name:self.open_app(p,n)))
            cards.append(self.card(name, "Aplicativo Android", action))
        return self.content_grid(cards,2)

    def open_app(self,pkg,name):
        if pkg=="camera":
            Android.intent("android.media.action.IMAGE_CAPTURE")
        elif not Android.launch(pkg):
            self.notify("Não encontrei o aplicativo "+name+".")

    # 4
    def internet_content(self):
        cards=[
            self.card("GOOGLE","Pesquisar na web",("ABRIR GOOGLE",lambda:Android.open_url("https://www.google.com"))),
            self.card("YOUTUBE","Vídeos e pesquisa",("ABRIR YOUTUBE",lambda:Android.open_url("https://www.youtube.com"))),
            self.card("FACEBOOK","Rede social",("ABRIR FACEBOOK",lambda:Android.open_url("https://www.facebook.com"))),
            self.card("INSTAGRAM","Rede social",("ABRIR INSTAGRAM",lambda:Android.open_url("https://www.instagram.com"))),
            self.card("PESQUISA","Digite uma consulta na barra principal.",("PESQUISAR",self.search_popup))
        ]
        return self.content_grid(cards,2)

    def search_popup(self):
        inp=TextInput(hint_text="Pesquisar...",multiline=False)
        box=BoxLayout(orientation="vertical",padding=dp(8),spacing=dp(8)); box.add_widget(inp)
        p=Popup(title="JARVIS // PESQUISA",content=box,size_hint=(.9,.35))
        btn=JButton(text="PESQUISAR",size_hint_y=None,height=dp(40))
        btn.bind(on_release=lambda *_:(Android.open_url("https://www.google.com/search?q="+urllib.parse.quote(inp.text)),p.dismiss()))
        box.add_widget(btn);p.open()

    # 5
    def media_content(self):
        return self.content_grid([
            self.card("MÚSICAS","Abra seu player padrão.",("ABRIR MÚSICA",lambda:Android.intent("android.intent.action.MUSIC_PLAYER"))),
            self.card("YOUTUBE","Vídeos e música.",("ABRIR YOUTUBE",lambda:Android.open_url("https://music.youtube.com"))),
            self.card("SPOTIFY","Player de música.",("ABRIR SPOTIFY",lambda:self.open_app("com.spotify.music","Spotify"))),
            self.card("RÁDIO","Pesquisa por rádios.",("ABRIR RÁDIO",lambda:Android.open_url("https://radio.garden")))
        ],2)

    # 6
    def contacts_content(self):
        return self.content_grid([
            self.card("CONTATOS","Gerencie os contatos do Android.",("ABRIR CONTATOS",lambda:Android.intent("android.intent.action.VIEW", "content://contacts/people", mime="vnd.android.cursor.dir/contact"))),
            self.card("LIGAR","Abra o discador.",("ABRIR TELEFONE",lambda:Android.intent("android.intent.action.DIAL"))),
            self.card("MENSAGEM","Abra o app de SMS.",("ABRIR MENSAGENS",lambda:Android.intent("android.intent.action.MAIN"))),
            self.card("WHATSAPP","Abra suas conversas.",("ABRIR WHATSAPP",lambda:self.open_app("com.whatsapp","WhatsApp")))
        ],2)

    # 7
    def maps_content(self):
        return self.content_grid([
            self.card("MAPA","Mapa e localização.",("ABRIR MAPAS",lambda:Android.open_url("https://maps.google.com"))),
            self.card("ROTAS","Pesquise uma rota.",("NOVA ROTA",self.route_popup)),
            self.card("LOCAL","O Android controla a permissão de localização.",("CONFIGURAR LOCALIZAÇÃO",lambda:Android.intent("android.settings.LOCATION_SOURCE_SETTINGS"))),
            self.card("NAVEGAÇÃO","Abra navegação web do Maps.",("NAVEGAR",lambda:Android.open_url("https://www.google.com/maps/dir/")))
        ],2)

    def route_popup(self):
        inp=TextInput(hint_text="Destino",multiline=False)
        box=BoxLayout(orientation="vertical",padding=dp(8),spacing=dp(8));box.add_widget(inp)
        p=Popup(title="JARVIS // ROTA",content=box,size_hint=(.9,.35))
        btn=JButton(text="ABRIR ROTA",size_hint_y=None,height=dp(40))
        btn.bind(on_release=lambda *_:(Android.open_url("https://www.google.com/maps/dir/?api=1&destination="+urllib.parse.quote(inp.text)),p.dismiss()))
        box.add_widget(btn);p.open()

    # 8
    def settings_content(self):
        return self.content_grid([
            self.card("IA AVANÇADA","Conector compatível com API OpenAI.",("CONFIGURAR IA",self.ai_popup)),
            self.card("ANDROID","Som, tela, conexões e apps.",("CONFIGURAÇÕES ANDROID",lambda:Android.intent("android.settings.SETTINGS"))),
            self.card("IDIOMA","O reconhecimento de voz usa pt-BR.",("IDIOMA",lambda:Android.intent("android.settings.LOCALE_SETTINGS"))),
            self.card("PRIVACIDADE","Permissões ficam sob controle do Android.",("PERMISSÕES",lambda:Android.intent("android.settings.MANAGE_APPLICATIONS_SETTINGS")))
        ],2)

    def ai_popup(self):
        s=self.ai.settings
        fields=[]
        for label,key,password in [("Ativar IA","enabled",False),("Endpoint HTTPS","endpoint",False),("Modelo","model",False),("Chave API","api_key",True)]:
            w=TextInput(text=("1" if s.get(key) else "0") if key=="enabled" else str(s.get(key,"")),multiline=False,password=password)
            fields.append((label,key,w))
        box=BoxLayout(orientation="vertical",padding=dp(8),spacing=dp(5))
        for label,_,w in fields:
            box.add_widget(Label(text=label,color=CYAN,size_hint_y=None,height=dp(20)));box.add_widget(w)
        p=Popup(title="JARVIS // IA AVANÇADA",content=box,size_hint=(.94,.8))
        save=JButton(text="SALVAR",size_hint_y=None,height=dp(42))
        def do(*_):
            vals={k: w.text for _,k,w in fields}
            vals["enabled"]=vals["enabled"].strip()=="1"
            self.ai.save(vals);p.dismiss();self.notify("Configuração da IA salva no dispositivo.")
        save.bind(on_release=do);box.add_widget(save);p.open()

    # 9
    def security_content(self):
        return self.content_grid([
            self.card("BLOQUEIO","O bloqueio de tela é administrado pelo Android.",("SEGURANÇA DO ANDROID",lambda:Android.intent("android.settings.SECURITY_SETTINGS"))),
            self.card("PRIVACIDADE","Gerencie permissões do JARVIS.",("PERMISSÕES",lambda:Android.intent("android.settings.MANAGE_APPLICATIONS_SETTINGS"))),
            self.card("BIOMETRIA","Abra as opções biométricas do sistema.",("BIOMETRIA",lambda:Android.intent("android.settings.SECURITY_SETTINGS"))),
            self.card("DADOS","O JARVIS não embute chaves de API no APK.",("INFORMAÇÕES",lambda:self.notify("As credenciais da IA ficam no armazenamento privado do app.")))
        ],2)

    # 10
    def camera_content(self):
        return self.content_grid([
            self.card("CÂMERA","Foto pela câmera padrão.",("FOTO",lambda:Android.intent("android.media.action.IMAGE_CAPTURE"))),
            self.card("VÍDEO","Abra a câmera de vídeo.",("VÍDEO",lambda:Android.intent("android.media.action.VIDEO_CAPTURE"))),
            self.card("GALERIA","Veja suas imagens.",("GALERIA",lambda:Android.intent("android.intent.action.VIEW","content://media/external/images/media")))
        ],2)

    # 11
    def calendar_content(self):
        return self.content_grid([
            self.card("CALENDÁRIO","Agenda do Android.",("ABRIR AGENDA",lambda:Android.intent("android.intent.action.MAIN"))),
            self.card("NOVO EVENTO","Abra a tela de criação de evento.",("CRIAR EVENTO",lambda:Android.intent("android.intent.action.INSERT","content://com.android.calendar/events"))),
            self.card("HOJE",datetime.now().strftime("%d/%m/%Y"),None)
        ],2)

    # 12
    def weather_content(self):
        return self.content_grid([
            self.card("CLIMA","O JARVIS não finge uma localização. Informe a cidade para consultar a previsão.",("CONSULTAR CIDADE",self.weather_popup)),
            self.card("FONTE","Open-Meteo é usado somente quando você solicitar uma consulta.",("ABRIR SITE",lambda:Android.open_url("https://open-meteo.com"))),
            self.card("LOCALIZAÇÃO","A localização é controlada pelas permissões do Android.",("CONFIGURAR GPS",lambda:Android.intent("android.settings.LOCATION_SOURCE_SETTINGS")))
        ],2)

    def weather_popup(self):
        inp=TextInput(hint_text="Ex.: Salvador, Bahia",multiline=False)
        box=BoxLayout(orientation="vertical",padding=dp(8),spacing=dp(8));box.add_widget(inp)
        p=Popup(title="JARVIS // CLIMA",content=box,size_hint=(.9,.35))
        btn=JButton(text="PESQUISAR",size_hint_y=None,height=dp(40))
        def go(*_):
            city=inp.text.strip()
            if city: Android.open_url("https://www.google.com/search?q="+urllib.parse.quote("clima "+city))
            p.dismiss()
        btn.bind(on_release=go);box.add_widget(btn);p.open()

    # 13
    def tasks_content(self):
        g=GridLayout(cols=1,spacing=dp(5),size_hint_y=None);g.bind(minimum_height=g.setter("height"))
        for task_id,text,done in self.db.tasks():
            b=JButton(text=("☑ " if done else "☐ ")+text,size_hint_y=None,height=dp(42))
            b.bind(on_release=lambda _,i=task_id:self.toggle_task(i))
            g.add_widget(b)
        sv=ScrollView(do_scroll_x=False);sv.add_widget(g)
        add=JButton(text="+ NOVA TAREFA",size_hint_y=None,height=dp(42));add.bind(on_release=lambda *_:self.task_popup())
        box=BoxLayout(orientation="vertical",spacing=dp(5));box.add_widget(sv);box.add_widget(add);return box

    def task_popup(self):
        inp=TextInput(hint_text="Nome da tarefa",multiline=False)
        box=BoxLayout(orientation="vertical",padding=dp(8),spacing=dp(8));box.add_widget(inp)
        p=Popup(title="JARVIS // NOVA TAREFA",content=box,size_hint=(.9,.35))
        btn=JButton(text="SALVAR",size_hint_y=None,height=dp(40))
        def save(*_):
            if inp.text.strip():self.db.add_task(inp.text.strip());p.dismiss();self.rebuild("tasks")
        btn.bind(on_release=save);box.add_widget(btn);p.open()

    def toggle_task(self,i):
        self.db.toggle_task(i);self.rebuild("tasks")

    # 14
    def voice_content(self):
        self.voice_wave=Wave();self.voice_wave.active=self.listening
        box=BoxLayout(orientation="vertical",spacing=dp(8),padding=dp(15))
        box.add_widget(Label(text="ASSISTENTE DE VOZ",color=CYAN,font_size=dp(16),bold=True,size_hint_y=None,height=dp(30)))
        box.add_widget(self.voice_wave)
        box.add_widget(Label(text="Fale claramente com o JARVIS.\nO reconhecimento usa o serviço de voz do Android.",color=WHITE,font_size=dp(11),halign="center"))
        btn=JButton(text="🎙 INICIAR ESCUTA",size_hint_y=None,height=dp(48));btn.bind(on_release=lambda *_:self.start_voice())
        box.add_widget(btn)
        return box

    # 15
    def files_content(self):
        return self.content_grid([
            self.card("DOCUMENTOS","Abra o seletor de documentos do Android.",("ABRIR ARQUIVOS",lambda:Android.intent("android.intent.action.OPEN_DOCUMENT", mime="*/*", category="android.intent.category.OPENABLE"))),
            self.card("IMAGENS","Selecione uma imagem.",("ABRIR IMAGENS",lambda:Android.intent("android.intent.action.OPEN_DOCUMENT", mime="*/*", category="android.intent.category.OPENABLE"))),
            self.card("DOWNLOADS","Acesse o gerenciador de arquivos.",("ABRIR ARQUIVOS",lambda:Android.intent("android.intent.action.OPEN_DOCUMENT", mime="*/*", category="android.intent.category.OPENABLE"))),
            self.card("ARMAZENAMENTO","O Android controla o acesso aos arquivos.",("CONFIGURAÇÕES",lambda:Android.intent("android.settings.INTERNAL_STORAGE_SETTINGS")))
        ],2)

    # 16
    def night_content(self):
        text="Modo Noturno Ativado\nHUD em baixo brilho e alto contraste."
        btn=JButton(text="DESATIVAR" if self.night else "ATIVAR",size_hint_y=None,height=dp(44))
        btn.bind(on_release=lambda *_:self.toggle_night())
        box=BoxLayout(orientation="vertical",padding=dp(25),spacing=dp(10))
        box.add_widget(Reactor())
        box.add_widget(Label(text=text if self.night else "Modo claro ativo",color=WHITE,font_size=dp(13),halign="center"))
        box.add_widget(btn);return box

    def toggle_night(self):
        self.night=not self.night
        self.rebuild("night")

    def rebuild(self,name):
        old=self.screens[name]
        idx=self.sm.screens.index(old)
        self.sm.remove_widget(old)
        title=old.title_text;sub=old.subtitle
        new=SectionScreen(name,title,sub,name=name);new.content=getattr(self,name+"_content")
        self.screens[name]=new;self.sm.add_widget(new);self.sm.current=name

    def send(self):
        text=self.command.text.strip()
        self.command.text=""
        if text:self.process(text)

    def process(self,text):
        self.db.add_message("user",text)
        self.notify("VOCÊ: "+text)
        self.executor.submit(self._answer,text)

    def _answer(self,text):
        t=text.lower().strip()
        reply=None
        if t in ("oi","olá","ola","bom dia","boa tarde","boa noite"):
            reply="Olá. JARVIS online. Como posso ajudar?"
        elif "hora" in t:
            reply="Agora são "+datetime.now().strftime("%H:%M:%S")+"."
        elif "data" in t:
            reply="Hoje é "+datetime.now().strftime("%d/%m/%Y")+"."
        elif "bateria" in t:
            b=Android.battery();reply=("A bateria está em %s%%."%b) if b is not None else "Não consegui consultar a bateria."
        elif "lanterna" in t:
            on=not any(x in t for x in ("deslig","apagar","off"))
            reply=("Lanterna ligada." if on else "Lanterna desligada.") if Android.flashlight(on) else "Não consegui controlar a lanterna."
        elif t in ("sistema","abrir sistema"):
            Clock.schedule_once(lambda *_:self.go("system"),0);reply="Abrindo o sistema."
        elif "aplicativos" in t:
            Clock.schedule_once(lambda *_:self.go("apps"),0);reply="Abrindo aplicativos."
        elif "internet" in t or "navegador" in t:
            Clock.schedule_once(lambda *_:self.go("internet"),0);reply="Abrindo internet."
        elif t.startswith("abrir youtube"):
            Android.open_url("https://www.youtube.com");reply="Abrindo YouTube."
        elif t.startswith("abrir google"):
            Android.open_url("https://www.google.com");reply="Abrindo Google."
        elif "pesquise " in t or t.startswith("buscar "):
            q=text.split(" ",1)[1];Android.open_url("https://www.google.com/search?q="+urllib.parse.quote(q));reply="Pesquisando por "+q+"."
        elif "modo noturno" in t:
            self.night=True;Clock.schedule_once(lambda *_:self.go("night"),0);reply="Modo noturno ativado."
        elif "ajuda" in t:
            reply="Posso abrir os módulos do JARVIS, informar hora, data e bateria, pesquisar na web, controlar a lanterna, criar tarefas e conversar com uma IA conectada."
        if reply is None:
            reply=self.ai.ask(text,self.db.history(12)) or "Entendido. Esse comando ainda não está ligado a uma ação local. Você pode conectá-lo à IA avançada nas Configurações."
        self.db.add_message("assistant",reply)
        Clock.schedule_once(lambda *_:self.notify("JARVIS: "+reply),0)
        self.executor.submit(Android.speak,reply)

    def notify(self,text):
        try:
            if hasattr(self,"home_log"):
                self.home_log.text=text
        except Exception:
            pass

    def start_voice(self):
        self.listening=True
        if hasattr(self,"home_wave"): self.home_wave.active=True
        self.voice.start()
        if "voice" in self.screens and self.sm.current=="voice":
            self.rebuild("voice")

    def voice_result(self,text):
        self.voice.stop();self.listening=False
        if hasattr(self,"home_wave"):self.home_wave.active=False
        if text:
            if hasattr(self,"command"):self.command.text=text
            self.process(text)
        if self.sm.current=="voice":self.rebuild("voice")

    def voice_error(self,code):
        self.voice.stop();self.listening=False
        if hasattr(self,"home_wave"):self.home_wave.active=False
        self.notify("JARVIS: não consegui ouvir. Verifique a permissão do microfone.")
        if self.sm.current=="voice":self.rebuild("voice")

    def refresh_top(self,dt):
        try:
            if hasattr(self, "home_clock"):
                self.home_clock.text = datetime.now().strftime("%H:%M")
            if hasattr(self, "home_battery"):
                b = Android.battery()
                self.home_battery.text = "BAT %s%%" % b if b is not None else "BAT --%"
        except Exception:
            pass

    def on_stop(self):
        try:self.voice.stop();self.executor.shutdown(wait=False);self.db.close()
        except Exception:pass

if __name__ == "__main__":
    JARVIS().run()
