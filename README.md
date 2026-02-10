# Power Outage Telegram Bot

Production-ready Telegram бот для відстеження змін у графіках відключення електроенергії на сайті poweron.loe.lviv.ua.

## Функціональність

- ✅ Автоматична перевірка сайту кожні 10 хвилин
- ✅ Парсинг графіків по групах (1.1-4.4)
- ✅ Сповіщення тільки при зміні графіка вибраної групи
- ✅ Збереження даних локально у JSON
- ✅ Обробка помилок та fallback-логіка
- ✅ Docker підтримка

## Команди бота

- `/start` - Привітання та вибір групи
- `/group` - Змінити групу
- `/status` - Показати поточний графік
- `/check` - Примусова перевірка

## Встановлення

### Локально

1. Клонуйте репозиторій:
```bash
git clone <repository-url>
cd windsurf-project
```

2. Створіть віртуальне середовище:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# або
venv\Scripts\activate  # Windows
```

3. Встановіть залежності:
```bash
pip install -r requirements.txt
```

4. Створіть файл `.env`:
```bash
cp .env.example .env
```

5. Додайте ваш Telegram Bot Token до `.env`:
```
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
```

6. Запустіть бота:
```bash
python bot.py
```

### Docker

1. Зберіть образ:
```bash
docker build -t power-outage-bot .
```

2. Запустіть контейнер:
```bash
docker run -d \
  --name power-outage-bot \
  --restart unless-stopped \
  -e TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here \
  -v $(pwd)/user_data.json:/app/user_data.json \
  power-outage-bot
```

Або використовуйте docker-compose:

```yaml
version: '3.8'
services:
  bot:
    build: .
    restart: unless-stopped
    environment:
      - TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
    volumes:
      - ./user_data.json:/app/user_data.json
```

## Структура проекту

```
windsurf-project/
├── bot.py              # Основний файл бота
├── config.py           # Конфігурація
├── parser.py           # Парсер сайту
├── scheduler.py        # Моніторинг змін
├── data_manager.py     # Управління даними
├── requirements.txt    # Залежності Python
├── Dockerfile         # Docker конфігурація
├── .dockerignore      # Файли для ігнорування в Docker
├── .env.example       # Приклад змінних середовища
└── README.md          # Документація
```

## Технічні деталі

### Парсинг

- Використовує BeautifulSoup4 + lxml
- Регулярні вирази для парсингу часових інтервалів
- Нормалізація формату часу (HH:MM)

### Надійність

- Retry стратегія для HTTP запитів
- User-Agent як у браузера
- Обробка HTTP 429/5xx помилок
- Fallback логіка при недоступності сайту

### Зберігання даних

```json
{
  "chat_id": {
    "group": "1.1",
    "last_schedule": [
      ["00:00", "05:30"],
      ["09:00", "14:00"]
    ]
  }
}
```

### Моніторинг

- Перевірка кожні 10 хвилин (налаштовується)
- Порівняння структур даних, а не сирого тексту
- Сповіщення тільки при реальних змінах

## Створення бота

1. Знайдіть @BotFather в Telegram
2. Використайте команду `/newbot`
3. Отримайте token і додайте його до `.env`

## Логування

Бот логує всі важливі події:
- Запуски/зупинки моніторингу
- Помилки запитів до сайту
- Помилки надсилання повідомлень
- Зміни в графіках

## Ліцензія

MIT License
