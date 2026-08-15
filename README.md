# qwen-discord-bot

Discord-бот на `discord.py`, который генерирует изображения через API Qwen
(Tongyi Wanxiang / DashScope) по произвольному промпту пользователя.

## Команда

```
/imagine prompt:<текст> [negative_prompt] [size]
```

- **prompt** — описание изображения (обязательно, любой текст).
- **negative_prompt** — что исключить из изображения (опционально).
- **size** — размер, например `1024*1024`, `1280*720` (по умолчанию `1024*1024`).

## Установка

1. Клонируй репозиторий и установи зависимости:

   ```bash
   git clone https://github.com/JustDzot/qwen-discord-bot.git
   cd qwen-discord-bot
   python3 -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Скопируй `.env.example` в `.env` и впиши свои ключи:

   ```bash
   cp .env.example .env
   ```

   - `DISCORD_TOKEN` — токен бота из [Discord Developer Portal](https://discord.com/developers/applications).
   - `QWEN_API_KEY` — API-ключ DashScope (Alibaba Cloud), раздел Tongyi Wanxiang.

3. В Developer Portal у приложения включи intent `applications.commands`
   (slash-команды подключаются автоматически при первом запуске).

4. Запусти бота:

   ```bash
   python bot.py
   ```

## Как это работает

1. `/imagine` отправляет асинхронную задачу генерации в DashScope API
   (`text2image/image-synthesis`).
2. Бот опрашивает статус задачи (`GET /tasks/{task_id}`) до готовности.
3. Готовое изображение скачивается и отправляется в Discord как embed с картинкой.

## Замечания

- Промпт полностью свободный — задаётся пользователем в момент вызова команды,
  никакой конкретный персонаж в коде не зашит.
- Соблюдай правила использования Discord API, DashScope API и авторские права
  на любые генерируемые изображения (в т.ч. при промптах с отсылками
  на существующих персонажей — это ответственность того, кто вводит промпт).
