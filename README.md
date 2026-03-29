# ⚡ Operator: Autonomous AI-OS Core

**Operator** — это автономный AI-агент (Stateless CLI-демон) системного уровня. Он работает как интеллектуальная прослойка между естественным языком человека и аппаратным обеспечением (ноутбуки на Linux, серверы, робототехника вроде Unitree или ROS-совместимых устройств).

Проект разработан в рамках хакатона **Decentrathon 5.0 (Трек: alem+)**.

---

## 🧠 Идея и Философия (Vibe-Coding for Hardware)
Сегодня AI-кодинг заперт в браузерах и IDE. Operator выводит его в физический мир.
Вы не пишете код руками. Вы отдаете команду голосом или текстом (на русском или казахском), агент анализирует аппаратную телеметрию вашего Linux-хоста (CPU, RAM, OS), разбивает задачу на логические шаги (Chain-of-Thought) и мгновенно генерирует и выполняет Bash/Python скрипты. 

**Ключевая особенность: STATELESS-архитектура.** Агент не имеет долгосрочной сессионной памяти. Принцип работы: *Получил команду -> Выполнил -> Обнулился*. Это полностью исключает риск ИИ-галлюцинаций, экономит токены и делает систему абсолютно предсказуемой для управления критическим железом.

---

## 🚀 Ключевые возможности MVP

* **Мультимодальный ввод:** Поддержка текстовых команд, голосового управления и визуального анализа экрана/камер.
* **Глубокое понимание системы:** Агент автоматически считывает `lscpu`, `free -h`, `lspci` и понимает, на каком "железе" он запущен.
* **Chain-of-Thought выполнение:** Агент не просто выдает скрипт, он разбивает сложную задачу на JSON-план и выполняет шаги последовательно, проверяя ошибки.
* **Безопасное прерывание:** Поддержка умного `Ctrl+C` — отмена текущего долгого скрипта без полного отключения "мозга" агента.
* **3 режима работы:** `Text` (дебаг), `Voice` (push-to-talk) и `Autonomous` (цикличное прослушивание).

---

## ⚙️ AI-Движок: Выбор моделей (Powered by alem.plus)

Ядро системы построено на API платформы **alem.plus**, объединяя сразу 3 мощные модели в единый пайплайн:

1. **Мозг (Logic & Planning): `GPT-OSS 117B`**
   * *Почему:* Несмотря на общий объем в 117 млрд параметров, модель использует архитектуру Mixture of Experts (MoE), активируя всего ~5.1B параметров при запросе. Это дает **феноменальную скорость (low-latency)**, необходимую для управления роботами в real-time. Модель идеально соблюдает сложные JSON-схемы (CoT-планирование) и генерирует чистый bash/python код.
2. **Зрение (Context Vision): `Qwen 3.5 27B Vision`**
   * *Почему:* На платформе также доступна Gemma 3 27B, однако мы осознанно выбрали Qwen 3.5. В бенчмарках сложного мультимодального понимания (MMMU и MMMU Pro) Qwen показывает более высокие результаты. Для нашего агента критически важно безошибочно распознавать элементы интерфейса ОС на скриншотах и физические препятствия с камер робота.
3. **Слух (Voice Input): `Speech-to-Text Kazakh`**
   * *Почему:* Обеспечивает высокоточную транскрибацию речи на казахском и русском языках. Глубокое понимание локального контекста спасает от ошибок распознавания при сильном аппаратном шуме (кулеры, сервоприводы робота).

---

## 🏗 Архитектура системы (Data Flow)

Архитектура построена по принципу направленного потока данных (от триггера к исполнению), подчеркивая Stateless-природу.

```mermaid
graph LR
    classDef trigger fill:#10B981,stroke:#047857,stroke-width:2px,color:#fff,rx:10px,ry:10px;
    classDef alem fill:#6366F1,stroke:#4338CA,stroke-width:2px,color:#fff,rx:10px,ry:10px;
    classDef core fill:#3B82F6,stroke:#1D4ED8,stroke-width:2px,color:#fff,rx:10px,ry:10px;
    classDef execute fill:#F59E0B,stroke:#B45309,stroke-width:2px,color:#fff,rx:10px,ry:10px;

    subgraph Inputs ["1. Triggers (User Input)"]
        T_Voice["🎤 Voice (STT)"]:::trigger
        T_Text["⌨️ Text (CLI)"]:::trigger
        T_Vision["📸 Screen/Cam"]:::trigger
    end

    subgraph AlemCloud ["2. AI Brain (alem.plus)"]
        M_STT["🔊 STT-KK"]:::alem
        M_Brain["🧠 GPT-OSS 117B"]:::alem
        M_Vision["👁️ Qwen 3.5 Vision"]:::alem
    end

    subgraph Engine ["3. Operator Core (Stateless)"]
        E_Router{"engine.py (Router)"}:::core
    end

    subgraph Execution ["4. Execution (Linux OS)"]
        X_Bash["⚡ Bash Scripts"]:::execute
        X_Python["🐍 Python / SDK"]:::execute
        X_GUI["🌐 Web/GUI (xdg-open)"]:::execute
    end

    T_Voice -->|"Audio"| M_STT
    M_STT -->|"Text"| E_Router
    T_Text -->|"Text"| E_Router
    
    E_Router -->|"Prompt + HW Context"| M_Brain
    T_Vision -.->|"Auto-Trigger"| E_Router
    E_Router -->|"Image Base64"| M_Vision
    M_Vision -->|"Context String"| M_Brain
    
    M_Brain -->|"JSON Plan"| E_Router
    E_Router -->|"Code Execution"| X_Bash
    E_Router -->|"Code Execution"| X_Python
    E_Router -->|"Code Execution"| X_GUI
