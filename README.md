# Telegram Video Rating Bot
Бот для оценки видеозаписей по заданным критериям с экспортом результатов в Excel.
Сам бот находится тут: @mentorrating_bot
## Структура проекта
```bash
mentor_bot
├── src/
│ ├── tg_bot.py # Основной скрипт бота
│ └── read_db.py # Скрипт для экспорта данных
├── data/
│ ├── ratings.db # База данных (создается автоматически)
│ └── results.xlsx # Результаты (создается скриптом read_db.py)
├── token/
│ └── config.txt # Файл с токеном бота
├── logs/ # Директория для логов (создается автоматически )
├── requirements.txt # Зависимости
└── README.md
```

## Установка
1. Клонируйте репозиторий
```bash
git clone https://github.com/moskovskayaliza2002/mentor_bot.git
```
2. Установите зависимости:
```bash
pip install -r requirements.txt
```
3. Вставьте в дирректорию *token* файл *config.txt* с токеном вашего бота (получить можно от @BotFather)

Остальные директории и файлы создадутся автоматически при запуске
## Запуск скриптов
### Запуск бота (tg_bot.py)
Из дирректории проекта:
```bash
python3 src/tg_bot.py
```
### Экспорт данных (read_db.py)
```bash
python3 src/read_db.py
```
Результат:
Файл data/results.xlsx с 3 листами:
- Ratings - оценки по критериям
- Theme Status - прогресс по темам
- Best Videos - выбор лучших видео

## Устранение неполадок
Если бот не запускается:
1. Проверьте наличие токена в token/config.txt

Если не создается Excel-файл:
1. Остановите бота
2. Закройте файл results.xlsx перед запуском скрипта
3. Проверьте права на запись в директорию data/

## Автоматизация
Для работы в фоновом режиме на Linux:
```
nohup python3 src/tg_bot.py > bot.log 2>&1 &
```
