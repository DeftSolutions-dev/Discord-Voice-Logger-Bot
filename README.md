# Discord Voice Logger Bot

![Discord Bot](https://img.shields.io/badge/discord-%237289DA.svg?logo=discord&logoColor=white)
![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)

## Описание

**Discord Voice Logger Bot** — это бот для Discord, который отслеживает голосовую активность пользователей на сервере. Он записывает события присоединения, покидания и переключения голосовых каналов, сохраняя их в базе данных и отправляя логи в указанный канал. Администраторы могут просматривать логи с помощью встроенных команд.

## Основные возможности

- **Отслеживание голосовых действий**: Вход, выход и переключение голосовых каналов пользователей.
- **Сохранение логов**: Все события сохраняются в базе данных SQLite.
- **Просмотр логов**: Команда `/log` позволяет просматривать логи по пользователям и датам.
- **Удобный интерфейс**: Использование кнопок для выбора даты и навигации по логам.

![image](https://github.com/user-attachments/assets/c6314c7f-483d-415a-908a-d0c3f076c89f)



## Требования

- **Python** версии 3.8 или выше. Скачайте Python с [официального сайта](https://www.python.org/downloads/).
- Необходимые библиотеки Python:
  - `py-cord`
  - `aiosqlite`
  - `python-dotenv`
```bash
pip install py-cord
```
```bash
pip install aiosqlite
```
```bash
pip install python-dotenv
```
## Установка

### 1. Установите Python

Если у вас еще не установлен Python, скачайте его с [официального сайта](https://www.python.org/downloads/) и следуйте инструкциям по установке. **Важно:** Во время установки поставьте галочку "Add Python to PATH", чтобы иметь возможность запускать Python из командной строки.

### 2. Клонируйте репозиторий

```bash
git clone https://github.com/yourusername/discord-voice-logger-bot.git
cd discord-voice-logger-bot
```

### 3. Создайте и активируйте виртуальное окружение (опционально)

Создание виртуального окружения поможет изолировать зависимости проекта.

```bash
python3 -m venv venv
```

- **Для Windows:**

  ```bash
  venv\Scripts\activate
  ```

- **Для macOS и Linux:**

  ```bash
  source venv/bin/activate
  ```

### 4. Установите зависимости

```bash
pip install -r requirements.txt
```

### 5. Настройте конфигурацию

Создайте файл `.env` в корне проекта и добавьте следующие переменные:

```env
TOKEN=Ваш_Discord_Token
DATABASE_PATH=voice_logs.db
LOG_CHANNEL_ID=ID_канала_для_логов
GUILD_ID=ID_вашего_сервера
```

- `TOKEN`: Токен вашего Discord бота.
- `DATABASE_PATH`: Путь к файлу базы данных SQLite (по умолчанию `voice_logs.db`).
- `LOG_CHANNEL_ID`: ID канала, куда будут отправляться логи.
- `GUILD_ID`: ID вашего Discord сервера (гильдии).

## Настройка

### 1. Создайте Discord бота и получите токен

- Перейдите на [Discord Developer Portal](https://discord.com/developers/applications).
- Создайте новое приложение и добавьте бота.
- Скопируйте токен бота и вставьте его в файл `.env`.

### 2. Пригласите бота на сервер

Для успешной работы бота необходимо предоставить ему определённые права. Следуйте инструкциям ниже, чтобы создать ссылку приглашения с нужными правами:

1. **Перейдите в раздел OAuth2** вашего приложения на [Discord Developer Portal](https://discord.com/developers/applications).
2. **Выберите "URL Generator"**.
3. **Настройте параметры OAuth2** следующим образом:
   - **Scopes**:
     - `bot`
     - `applications.commands`
   - **Bot Permissions**:
     - `View Channels` (Просмотр каналов)
     - `Send Messages` (Отправка сообщений)
     - `Embed Links` (Встраивание ссылок)
     - `Connect` (Подключение к голосовым каналам)
     - `Speak` (Голосовая связь)
     - `Read Message History` (Чтение истории сообщений)
     - `Use Slash Commands` (Использование слеш-команд)

4. **Скопируйте сгенерированную ссылку** и откройте её в браузере, чтобы пригласить бота на ваш сервер.

**Пример ссылки приглашения:**

```
https://discord.com/api/oauth2/authorize?client_id=CLIENT_ID&permissions=384320&scope=bot%20applications.commands
```

> **Примечание:** Убедитесь, что вы заменили `CLIENT_ID` на реальный ID приложения.

### 3. Настройте базу данных

При первом запуске бот автоматически создаст таблицы и индексы в базе данных `voice_logs.db`.

## Использование

### 1. Запустите бота

```bash
python bot.py
```

### 2. Основные команды бота

- **/log**: Просмотр голосовых логов.

  **Параметры:**
  - `member` (опционально): Укажите пользователя для фильтрации логов.
  - `date` (опционально): Укажите дату в формате `DD/MM/YYYY` для фильтрации логов.

  **Примеры использования:**
  - `/log`: Показать последние 25 голосовых логов на сервере.
  - `/log member:@User`: Показать доступные даты для выбранного пользователя.
  - `/log member:@User date:27/04/2024`: Показать голосовые логи выбранного пользователя за указанную дату.
  - `/log date:27/04/2024`: Показать голосовые логи за указанную дату.

## Структура базы данных

Таблица `voice_logs` хранит информацию о голосовых событиях:

| Поле             | Тип      | Описание                                      |
|------------------|----------|-----------------------------------------------|
| `id`             | INTEGER  | Первичный ключ, автоинкремент                |
| `user_id`        | INTEGER  | ID пользователя                               |
| `username`       | TEXT     | Имя пользователя                              |
| `event_type`     | TEXT     | Тип события (`join`, `leave`, `switch`)       |
| `channel_before` | TEXT     | Название канала до события (если применимо)    |
| `channel_after`  | TEXT     | Название канала после события (если применимо) |
| `timestamp`      | TEXT     | Время события (в формате `YYYY-MM-DD HH:MM:SS`) |
| `duration`       | TEXT     | Продолжительность пребывания в канале (если применимо) |

## Примеры логов

### Присоединение к голосовому каналу

![Присоединение](https://github.com/user-attachments/assets/4612fbc6-9e6e-4a95-9c51-9835cd0e409e)

### Покидание голосового канала

![Покидание](https://github.com/user-attachments/assets/e94907b7-ad41-4926-9120-b16bf96f2d49)

### Переключение голосовых каналов

![Переключение](https://github.com/user-attachments/assets/047760fb-4ab7-48ea-8226-07e8fc8190b1)



## Контакты

Если у вас есть вопросы или предложения, свяжитесь со мной через [GitHub Issues](https://github.com/DeftSolutions-dev/Discord-Voice-Logger-Bot/issues) или по Telegram: [@desirepro](https://t.me/desirepro)
