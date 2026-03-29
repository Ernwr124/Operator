import platform
import os
import sys
import subprocess
from engine import OperatorEngine, Colors

def print_banner():
    banner = f"""{Colors.OKCYAN}{Colors.BOLD}
  ___  ____  ____  ____   __  ____  ___  ____ 
 / _ \(  _ \(  __)(  _ \ / _\(_  _)/ _ \(  _ \\
( (_) )) __/ ) _)  )   //    \ )( ( (_) ))   /
 \___/(__)  (____)(__\_)\_/\_/(__) \___/(__\_)
    {Colors.ENDC}"""
    print(banner)

def get_cmd_output(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL).strip()
    except:
        return "Неизвестно"

def deep_hardware_scan():
    print(f"{Colors.WARNING}[SCAN] Глубокий анализ аппаратного обеспечения...{Colors.ENDC}")
    cpu = get_cmd_output("cat /proc/cpuinfo | grep 'model name' | uniq | cut -d ':' -f 2").strip()
    ram = get_cmd_output("free -h | awk '/^Mem:/ {print $2}'")
    gpu = get_cmd_output("lspci | grep -i 'vga\\|3d\\|2d' | cut -d ':' -f 3").strip()
    return {
        "os": platform.system(),
        "release": platform.release(),
        "node": platform.node(),
        "machine": platform.machine(),
        "user": os.getlogin(),
        "cpu": cpu if cpu else "Unknown CPU",
        "ram": ram if ram else "Unknown RAM",
        "gpu": gpu if gpu else "Unknown GPU"
    }

def main():
    os.system('clear' if os.name == 'posix' else 'cls')
    print_banner()
    
    if platform.system() != "Linux":
        print(f"{Colors.FAIL}[FATAL] Ошибка: Operator AI работает только на Linux.{Colors.ENDC}")
        sys.exit(1)

    telemetry = deep_hardware_scan()
    print(f"\n{Colors.OKGREEN}[ТЕЛЕМЕТРИЯ СИСТЕМЫ]{Colors.ENDC}")
    print(f" ▻ Хост: {telemetry['node']} | ОС: {telemetry['os']} {telemetry['release']}")
    print(f" ▻ CPU:  {telemetry['cpu']}")
    print(f" ▻ RAM:  {telemetry['ram']}")
    print(f" ▻ GPU:  {telemetry['gpu']}")
    print("=========================================")
    
    engine = OperatorEngine(telemetry)
    
    print(f"\n{Colors.BOLD}[ВЫБОР РЕЖИМА]{Colors.ENDC}")
    print(" 1 - Автономный (непрерывное прослушивание микрофона)")
    print(" 2 - Текстовый (ввод команд с клавиатуры — идеально для тестов)")
    print(" 3 - Голосовой (активация записи по Enter)")
    
    # Жесткий цикл защиты ввода
    while True:
        choice = input(f"\n{Colors.OKCYAN}Выберите режим (1/2/3): {Colors.ENDC}").strip()
        if choice in ['1', '2', '3']:
            break
        print(f"{Colors.FAIL}Ошибка! Введите только цифру 1, 2 или 3.{Colors.ENDC}")
    
    if choice == '1':
        engine.run(mode='autonomous')
    elif choice == '2':
        engine.run(mode='text')
    else:
        engine.run(mode='voice')

if __name__ == "__main__":
    main()
