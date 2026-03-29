import os
import time
import requests
import subprocess
import sounddevice as sd
from scipy.io.wavfile import write
import json
import base64
import sys
from dotenv import load_dotenv

# Загружаем переменные окружения из файла .env
load_dotenv()

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

# --- API КЛЮЧИ БЕРЕМ ИЗ .ENV ---
STT_URL = "https://llm.alem.ai/v1/audio/transcriptions"
STT_TOKEN = os.getenv("ALEM_STT_TOKEN")

LLM_URL = "https://llm.alem.ai/chat/completions"
LLM_TOKEN = os.getenv("ALEM_LLM_TOKEN")

VISION_URL = "https://llm.alem.ai/v1/chat/completions"
VISION_TOKEN = os.getenv("ALEM_VISION_TOKEN")

class OperatorEngine:
    def __init__(self, telemetry):
        self.telemetry = telemetry
        self.fs = 16000
        self.duration = 4
        self.audio_file = "vibe_command.wav"
        
        # Проверка наличия ключей при старте
        if not all([STT_TOKEN, LLM_TOKEN, VISION_TOKEN]):
            print(f"{Colors.FAIL}[FATAL] API-ключи не найдены! Убедитесь, что файл .env существует и заполнен.{Colors.ENDC}")
            sys.exit(1)

    def record_audio(self):
        print(f"\n{Colors.WARNING}[MIC] Ожидание команды ({self.duration} сек). Говорите...{Colors.ENDC}")
        recording = sd.rec(int(self.duration * self.fs), samplerate=self.fs, channels=1, dtype='int16')
        sd.wait()
        write(self.audio_file, self.fs, recording)
        print(f"{Colors.OKGREEN}[MIC] Запись завершена.{Colors.ENDC}")

    def transcribe(self):
        print(f"{Colors.OKBLUE}[NETWORK] STT-KK: Распознавание речи...{Colors.ENDC}")
        headers = {'Authorization': f'Bearer {STT_TOKEN}'}
        try:
            with open(self.audio_file, 'rb') as f:
                files = {'file': (self.audio_file, f, 'audio/wav'), 'model': (None, 'speech-to-text-kk')}
                response = requests.post(STT_URL, headers=headers, files=files)
            if response.status_code == 200:
                return response.json().get('text', '')
        except Exception as e:
            print(f"{Colors.FAIL}[ERROR STT]: {e}{Colors.ENDC}")
        return None

    def vision_analyze(self, image_path):
        """Отправляет изображение в Qwen 3.5 27B Vision"""
        print(f"{Colors.HEADER}[VISION] Подключение к Qwen 3.5 27B...{Colors.ENDC}")
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')

        headers = {
            "Authorization": f"Bearer {VISION_TOKEN}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "qwen3",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Опиши подробно, что ты видишь на этом скриншоте. Отвечай кратко и по делу."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ]
        }
        try:
            response = requests.post(VISION_URL, headers=headers, json=payload)
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            else:
                print(f"{Colors.FAIL}[ERROR QWEN]: {response.text}{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.FAIL}[ERROR VISION]: {e}{Colors.ENDC}")
        return None

    def think(self, command_text):
        headers = {'Authorization': f'Bearer {LLM_TOKEN}', 'Content-Type': 'application/json'}
        system_prompt = f"""
        Ты автономный AI-агент 'Operator', управляющий операционной системой.
        Твоя текущая оболочка: OS {self.telemetry['os']} {self.telemetry['release']}
        
        Задача: Проанализируй команду пользователя, разбей её на логические шаги и верни команды bash.
        
        ПРАВИЛА:
        1. Верни ТОЛЬКО валидный JSON. Формат: {{"thought": "...", "complexity": "...", "steps": ["..."]}}
        2. ГРАФИКА: Для открытия сайтов/программ используй `xdg-open "URL_ИЛИ_ФАЙЛ"`.
        3. ПОИСК: Для поиска инфы используй `w3m -dump "https://lite.duckduckgo.com/lite/?q=ЗАПРОС" | head -n 40`. НЕ пиши парсеры через curl.
        4. ЗРЕНИЕ (VISION): Если пользователь просит "посмотри на экран", "что ты видишь", "анализируй экран" — НЕ пиши скрипты для скриншотов. Просто верни ОДИН шаг в массиве steps: "VISION_CAPTURE". Движок сам активирует модуль зрения.
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": command_text}
        ]
        
        payload = {"model": "gpt-oss", "messages": messages, "temperature": 0.1}
        
        print(f"{Colors.HEADER}[BRAIN] GPT-OSS: Анализ команды (Stateless)...{Colors.ENDC}")
        response = requests.post(LLM_URL, headers=headers, json=payload)
        
        if response.status_code == 200:
            raw_response = response.json()['choices'][0]['message']['content']
            raw_response = raw_response.replace('```json', '').replace('```', '').strip()
            try:
                return json.loads(raw_response)
            except json.JSONDecodeError:
                 return None
        return None

    def execute_plan(self, plan):
        print(f"\n{Colors.OKBLUE}" + "="*50)
        print(f"🧠 [ПЛАН ДЕЙСТВИЙ]")
        print(f"   Мысль: {plan.get('thought', 'Нет рассуждений')}")
        print("="*50 + f"{Colors.ENDC}")
        
        steps = plan.get('steps', [])
        if not steps:
            return

        for i, step_code in enumerate(steps, 1):
            if step_code.strip() == "VISION_CAPTURE":
                print(f"\n{Colors.OKCYAN}📸 [КАМЕРА] Захват экрана...{Colors.ENDC}")
                
                subprocess.run("command -v scrot >/dev/null || sudo apt-get install -y scrot", shell=True, stderr=subprocess.DEVNULL)
                subprocess.run("scrot /tmp/vision_frame.jpg", shell=True)
                
                if os.path.exists("/tmp/vision_frame.jpg"):
                    vision_result = self.vision_analyze("/tmp/vision_frame.jpg")
                    if vision_result:
                        print(f"\n{Colors.OKGREEN}👁️ [QWEN VISION ГОВОРИТ]:\n{vision_result}{Colors.ENDC}\n")
                else:
                    print(f"{Colors.FAIL}[ERROR] Не удалось сделать снимок (scrot).{Colors.ENDC}")
                continue
            
            print(f"\n{Colors.OKGREEN}⚡ [ШАГ {i}/{len(steps)}] Выполняю код:{Colors.ENDC}\n{step_code}")
            try:
                process = subprocess.Popen(step_code, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                while True:
                    output = process.stdout.readline()
                    if output == '' and process.poll() is not None:
                        break
                    if output:
                        print(f"[STDOUT]: {output.strip()}")
                err = process.stderr.read()
                if err:
                     print(f"{Colors.WARNING}[STDERR]:\n{err.strip()}{Colors.ENDC}")
            except KeyboardInterrupt:
                print(f"\n{Colors.FAIL}[⚠️ ОТМЕНА] Выполнение шага прервано (Ctrl+C).{Colors.ENDC}")
                process.terminate()
                break 
            except Exception as e:
                 print(f"{Colors.FAIL}[FATAL] Ошибка: {e}{Colors.ENDC}")
                 break

    def run(self, mode='text'):
        print(f"\n{Colors.OKGREEN}[OK] Нейронный движок запущен. Режим: {mode.upper()} (Stateless){Colors.ENDC}")
        exit_requested = False
        while True:
            try:
                text = ""
                if mode == 'text':
                    text = input(f"\n{Colors.BOLD}[⌨️ TEXT] Введите команду: {Colors.ENDC}")
                    if text.lower() in ['exit', 'quit']: break
                    if not text.strip(): continue
                elif mode == 'voice':
                    input(f"\n{Colors.BOLD}[🎤 VOICE] Нажмите Enter для записи...{Colors.ENDC}")
                    self.record_audio()
                    text = self.transcribe()
                    if not text: continue
                    print(f"🗣️ [Распознано]: {text}")
                elif mode == 'autonomous':
                    print(f"\n{Colors.BOLD}[🤖 AUTO] Слушаю окружение...{Colors.ENDC}")
                    self.record_audio()
                    text = self.transcribe()
                    if not text or len(text.strip()) < 4: continue
                    print(f"🗣️ [Распознано]: {text}")

                plan = self.think(text)
                if plan: self.execute_plan(plan)
                exit_requested = False 
                
            except KeyboardInterrupt:
                if exit_requested:
                    print(f"\n{Colors.FAIL}[STOP] Оператор отключен.{Colors.ENDC}")
                    break
                else:
                    print(f"\n{Colors.WARNING}[⚠️ ВНИМАНИЕ] Нажмите Ctrl+C еще раз для полного выхода.{Colors.ENDC}")
                    exit_requested = True
