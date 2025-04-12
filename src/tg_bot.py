#! /usr/bin/env python3 
import nest_asyncio
import asyncio
import logging
import random
import os
from pathlib import Path
from functools import partial
import json
import aiosqlite # type: ignore
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import BadRequest 
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    CallbackContext
)
# тестировочный тег видео: BAACAgIAAxkBAAMDZ9wPRzeP1WZuKtSvvUWdHajDfKgAAgpnAALm0-hKoF7kuBm7AAH4NgQ
nest_asyncio.apply()

BASE_DIR = Path(__file__).resolve().parent.parent
TOKEN_PATH = BASE_DIR / "token" / "config.txt"
DB_PATH = BASE_DIR / "data" / "ratings.db"
LOG_DIR = BASE_DIR / "logs"

# Автоматическое создание директорий
for path in [DB_PATH.parent, LOG_DIR, TOKEN_PATH.parent]:
    path.mkdir(parents=True, exist_ok=True)

# Настройка логов
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler(LOG_DIR / "bot.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Чтение токена с обработкой ошибок
try:
    with open(TOKEN_PATH, "r") as f:
        BOT_TOKEN = f.read().strip()
except FileNotFoundError:
    logging.critical(f"❌ Файл с токеном не найден: {TOKEN_PATH}")
    exit(1)
except Exception as e:
    logging.critical(f"❌ Ошибка чтения токена: {str(e)}")
    exit(1)

DB_NAME = str(DB_PATH)  # Для совместимости с aiosqlite

# Человеко-читаемые названия
VIDEO_NAMES = {
    "BAACAgIAAxkBAAIJhGf6hWz6Tf4UzrfUzQzVmA4uQEaBAAK9bwACrIbQS4ODBoPbU0kWNgQ": "Робототехника - Человеческий",
    "BAACAgIAAxkBAAIJhmf6hYP7qB-f2nuwvg9FDaGofHMzAAK-bwACrIbQS7U72c2RicaGNgQ": "Робототехника - Сгенерированный",
    "BAACAgIAAxkBAAIJiGf6hY39rfGimXYyxRrFFI7-YJTaAAK_bwACrIbQS7UX2rFb1Sp3NgQ": "Робототехника - Сгенерированный+",
    "BAACAgIAAxkBAAIJimf6hagbHeQgOb_EEZYz00u72p4pAALBbwACrIbQSzP-35GDsrVfNgQ": "Кто живет в Антарктиде? - Человеческий",
    "BAACAgIAAxkBAAIJjGf6hbx_L4QTiT1LIl5gL62GyhS0AALEbwACrIbQS7OJU7yemkUJNgQ": "Кто живет в Антарктиде? - Сгенерированный",
    "BAACAgIAAxkBAAIJlmf6h_aTQQ7T2CUF99_Yl0nW1wmgAAL3bwACrIbQS6IJn7l8ajYgNgQ": "Кто живет в Антарктиде? - Сгенерированный+",
    "BAACAgIAAxkBAAIJkGf6hd4QqdiDb9CzNVCWT7iGtQ9jAALIbwACrIbQS7_QaCaZeO7PNgQ": "Кто побывал в космосе? - Человеческий",
    "BAACAgIAAxkBAAIJkmf6hfQzUpF2V5fcvG5zfv--99IOAALKbwACrIbQS50Y8yKJKRujNgQ": "Кто побывал в космосе? - Сгенерированный",
    "BAACAgIAAxkBAAIJlGf6hgW5MCA1OC_pf7cxjCac4JRdAALLbwACrIbQS0TChyBosMQLNgQ": "Кто побывал в космосе? - Сгенерированный+"
}

THEMES = {
    "Робототехника": [
        "BAACAgIAAxkBAAIJhGf6hWz6Tf4UzrfUzQzVmA4uQEaBAAK9bwACrIbQS4ODBoPbU0kWNgQ",
        "BAACAgIAAxkBAAIJhmf6hYP7qB-f2nuwvg9FDaGofHMzAAK-bwACrIbQS7U72c2RicaGNgQ",
        "BAACAgIAAxkBAAIJiGf6hY39rfGimXYyxRrFFI7-YJTaAAK_bwACrIbQS7UX2rFb1Sp3NgQ"
    ],
    "Кто живет в Антарктиде?": [
        "BAACAgIAAxkBAAIJimf6hagbHeQgOb_EEZYz00u72p4pAALBbwACrIbQSzP-35GDsrVfNgQ",
        "BAACAgIAAxkBAAIJjGf6hbx_L4QTiT1LIl5gL62GyhS0AALEbwACrIbQS7OJU7yemkUJNgQ",
        "BAACAgIAAxkBAAIJlmf6h_aTQQ7T2CUF99_Yl0nW1wmgAAL3bwACrIbQS6IJn7l8ajYgNgQ"
    ],
    "Кто побывал в космосе?": [
        "BAACAgIAAxkBAAIJkGf6hd4QqdiDb9CzNVCWT7iGtQ9jAALIbwACrIbQS7_QaCaZeO7PNgQ",
        "BAACAgIAAxkBAAIJkmf6hfQzUpF2V5fcvG5zfv--99IOAALKbwACrIbQS50Y8yKJKRujNgQ",
        "BAACAgIAAxkBAAIJlGf6hgW5MCA1OC_pf7cxjCac4JRdAALLbwACrIbQS0TChyBosMQLNgQ"
    ]
}

# 5 критериев
CRITERIA = [
    "Логичность",
    "Информативность",
    "Интересность",
    "Естественность",
    "Согласованность невербальных сигналов"
]

# Интерпретации шкалы для каждого критерия
CRITERIA_HINTS = [
    "«Текст хаотичен» → «Текст логичен».",
    "«Текст поверхностен» → «Текст информативен».",
    "«Текст звучит сухо» → «Текст интересный».",
    "«Текст механический» → «Текст естественный».",
    "«Действия в тексте случайны» → «Действия полностью дополняют контекст»."
]

async def init_db():
    """Инициализация базы данных"""
    os.makedirs(os.path.dirname(DB_NAME), exist_ok=True)
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute('''CREATE TABLE IF NOT EXISTS progress (
                          user_id INTEGER PRIMARY KEY,
                          theme TEXT,
                          videos TEXT,
                          video_index INTEGER,
                          current_criterion INTEGER,
                          current_score TEXT)''')
        
        await db.execute('''CREATE TABLE IF NOT EXISTS completed_themes (
                          user_id INTEGER,
                          theme TEXT,
                          PRIMARY KEY(user_id, theme))''')
        
        await db.execute('''CREATE TABLE IF NOT EXISTS best_videos (
                          user_id INTEGER,
                          theme TEXT,
                          video_id TEXT,
                          reason TEXT,
                          PRIMARY KEY(user_id, theme))''')
        
        await db.execute('''CREATE TABLE IF NOT EXISTS ratings (
                          user_id INTEGER,
                          theme TEXT,
                          video_id TEXT,
                          criterion TEXT,
                          score INTEGER)''')
        await db.commit()


async def start(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /start."""
    user = update.effective_user
    user_id = user.id

    # Единая проверка прогресса
    progress = await get_progress(user_id)
    if progress:
        await continue_progress(update, context, progress)
        return

    # Только если прогресса нет, начинаем новую тему
    completed_themes = await get_completed_themes(user_id)

    # Какие темы ещё не пройдены
    all_themes = list(THEMES.keys())
    unfinished = [t for t in all_themes if t not in completed_themes]

    if not unfinished:
        await update.message.reply_text(
            f"Здравствуй, {user.first_name}! Вы уже прошли все темы.\n"
            "Спасибо вам за это большое!"
        )
        return
    
    # Проверяем незавершенную сессию
    progress = await get_progress(user_id)
    if progress:
        await continue_progress(update, context, progress)
        return
    
    # Начинаем новую сессию
    # Берём одну случайную тему из непройденных
    chosen_theme = random.choice(unfinished)

    # Перемешиваем 3 видео этой темы
    videos = THEMES[chosen_theme][:]
    random.shuffle(videos)

    context.user_data.update({
        'current_theme': chosen_theme,
        'videos': videos,
        'video_index': 0,
        'current_criterion': 0,
        'current_score': {},
        'scores_for_this_theme': [],
        'favorite_video': None,
        'waiting_for_best_reason': False
    })

    await update.message.reply_text(
        f"Здравствуй, {user.first_name}!\n"
        f"Тебе выпала тема: {chosen_theme}\n"
        "Сейчас покажу 3 видео. Каждое видео нужно будет оценить по 5 критериям: логичность, информативность, интересность и естественность текста, а также степень согласованности невербальных сигналов содержанию текста.\n"
        "В конце нужно будет выбрать лучшее видео, представившее данную тему, и сказать почему.\n\n"
        f"Всего тем: {len(all_themes)}, вы прошли: {len(completed_themes)}, осталось: {len(unfinished)}."
    )

    # Отправляем первое видео
    await send_video(update, context)


async def send_video(update: Update, context: CallbackContext) -> None:
    data = context.user_data
    # Убедимся, что у нас есть нужные ключи
    if "current_theme" not in data or "videos" not in data:
        await update.message.reply_text("Ошибка: данные сессии не найдены.")
        return

    idx = data["video_index"]
    videos = data["videos"]

    if idx >= len(videos):
        # все видео закончились
        await ask_favorite_video(update, context)
        return

    current_video_id = videos[idx]
    await context.bot.send_video(
        chat_id=update.effective_chat.id,
        video=current_video_id,
        caption=(
            f"Тема: {data['current_theme']}\n"
            f"Видео {idx+1} из {len(videos)}\n"
            f"Критерий №{data['current_criterion']+1}: {CRITERIA[data['current_criterion']]}"
        )
    )

    if data["current_criterion"] >= len(CRITERIA):
        # Если уже всё оценили для данного видео
        # переход к следующему
        data["video_index"] += 1
        data["current_criterion"] = 0
        await send_video(update, context)
        return

    # Спрашиваем конкретный критерий
    await ask_criterion(update, context)


async def ask_criterion(update: Update, context: CallbackContext) -> None:
    """
    Выводит кнопки 1..5 для текущего критерия. 
    """
    data = context.user_data
    c_idx = data["current_criterion"]
    if c_idx >= len(CRITERIA):
        await update.message.reply_text("Все критерии пройдены.")
        return

    criterion = CRITERIA[c_idx]
    hint_text = CRITERIA_HINTS[c_idx]
    keyboard = [
        [
            InlineKeyboardButton(f"{i}", callback_data=f"rating-{i}") 
            for i in range(1, 6)
        ]
    ]
    markup = InlineKeyboardMarkup(keyboard)
    await update.effective_chat.send_message(
        text=f"{criterion}\n{hint_text}\nВыберите оценку от 1 до 5:",
        reply_markup=markup
    )

async def handle_rating(update: Update, context: CallbackContext) -> None:
    """Обработка нажатия кнопок rating-X."""
    try:
        query = update.callback_query
        await query.answer()

        data = context.user_data
        
        # Инициализация отсутствующих ключей
        data.setdefault('current_criterion', 0)
        data.setdefault('video_index', 0)
        data.setdefault('videos', [])
        data.setdefault('current_score', {})

        if not query.data.startswith("rating-"):
            return

        rating_str = query.data.split('-')[1]
        rating = int(rating_str)

        # Выключаем кнопки
        await query.edit_message_reply_markup(reply_markup=None)

        data = context.user_data
        c_idx = data['current_criterion']
        criterion = CRITERIA[c_idx]

        # Сохраняем оценку
        await save_rating(
            user_id=query.from_user.id,
            theme=data['current_theme'],
            video_id=data['videos'][data['video_index']],
            criterion=criterion,
            score=rating
        )

        # После сохранения оценки:
        if data['current_criterion'] >= len(CRITERIA):
            data['video_index'] += 1
            data['current_criterion'] = 0  # Сброс перед сохранением
        
        else:
            data['current_criterion'] += 1
        
        await save_progress(data, query.from_user.id)  # Обновить прогресс

        if data['current_criterion'] < len(CRITERIA):
            await query.message.reply_text("Спасибо! Следующий критерий:")
            await ask_criterion(update, context)
        else:
            data['video_index'] += 1
            data['current_criterion'] = 0  # Сброс критерия для нового видео

            if data['video_index'] < len(data['videos']):
                await query.message.reply_text("Спасибо! Переходим к следующему видео.")
                await send_video(update, context)
            else:
                await query.message.reply_text(
                    f"Все 3 видео по теме {data['current_theme']} просмотрены.\n"
                    "Теперь выберите, какое понравилось больше всего:"
                )
                await ask_favorite_video(update, context)

    except BadRequest as e:
        if "Query is too old" in str(e):
            # Убираем дублирующее сообщение
            progress = await get_progress(update.effective_user.id)
            if progress:
                await continue_progress(update, context, progress)
            else:
                await start(update, context)
        else:
            logger.error(f"BadRequest: {e}")


async def save_rating(user_id: int, theme: str, video_id: str, criterion: str, score: int):
    """Сохранение оценки в БД"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO ratings VALUES (?, ?, ?, ?, ?)",
            (user_id, theme, video_id, criterion, score)
        )
        await db.commit()


async def save_progress(data: dict, user_id: int):
    """Сохранение прогресса в БД"""
    try:
        # Проверяем обязательные ключи
        required_keys = ['current_theme', 'videos', 'video_index', 'current_criterion', 'current_score']
        if not all(key in data for key in required_keys):
            raise ValueError("Invalid data structure")
        
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("BEGIN"):
                # Удаляем старый прогресс
                await db.execute("DELETE FROM progress WHERE user_id = ?", (user_id,))
                # Добавляем новый
                await db.execute(
                    "INSERT INTO progress VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        user_id,
                        data['current_theme'],
                        json.dumps(data['videos']),
                        data['video_index'],
                        data['current_criterion'],
                        json.dumps(data['current_score'])
                    )
                )
                await db.commit()
    except Exception as e:
        logger.error(f"Save progress error: {e}", exc_info=True)    


async def get_progress(user_id: int) -> dict:
    """Получение прогресса из БД"""
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            cursor = await db.execute("SELECT * FROM progress WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            return {
                'current_theme': row[1],
                'videos': json.loads(row[2]),
                'video_index': row[3],
                'current_criterion': row[4],
                'current_score': json.loads(row[5])
            } if row else None
    except Exception as e:
        logging.error(f"Get progress error: {e}")
        return None


async def ask_favorite_video(update: Update, context: CallbackContext) -> None:
    """Спрашивает, какое из 3 видео было лучшим."""
    data = context.user_data
    videos = data['videos']

    keyboard = [
        [InlineKeyboardButton(f"Видео {i+1}", callback_data=f"best-{i}") for i in range(len(videos))]
    ]
    markup = InlineKeyboardMarkup(keyboard)

    await update.effective_chat.send_message(
        text="Какое видео было лучшим?",
        reply_markup=markup
    )


async def continue_progress(update: Update, context: CallbackContext, progress: dict):
    data = context.user_data
    data.clear()
    try:
        # Проверяем наличие всех необходимых ключей
        required_keys = ['current_theme', 'videos', 'video_index', 'current_criterion']
        if not all(key in progress for key in required_keys):
            raise ValueError("Invalid progress structure")

        # Восстанавливаем videos даже если сессия была на этапе выбора лучшего
        if 'videos' not in progress:
            progress['videos'] = THEMES.get(progress['current_theme'], [])

        # Корректируем индексы
        progress['video_index'] = min(progress['video_index'], len(progress['videos']) - 1)
        progress['current_criterion'] = min(progress['current_criterion'], len(CRITERIA) - 1)

        # Восстанавливаем данные
        data.update({
            "current_theme": progress["current_theme"],
            "videos": progress["videos"],
            "video_index": progress["video_index"],
            "current_criterion": progress["current_criterion"],
            "current_score": progress.get("current_score", {}),
            "waiting_for_best_reason": progress.get("waiting_for_best_reason", False)
        })

        # Если сессия была на этапе выбора лучшего видео
        if data["video_index"] >= len(data["videos"]):
            # Если сессия была прервана НА ЭТАПЕ ВЫБОРА ЛУЧШЕГО ВИДЕО
            await update.effective_chat.send_message(
                "🔄 Восстанавливаем сессию: Выбор лучшего видео"
            )
            await ask_favorite_video(update, context)  # Отправляем НОВЫЕ кнопки
            return

        # Если сессия была на этапе ввода причины
        if data.get('waiting_for_best_reason'):
            await update.effective_chat.send_message("Продолжаем ввод причины...")
            return

        # Восстанавливаем видео и критерий
        await update.effective_chat.send_message(
            f"🔄 Восстанавливаем сессию: Тема {data['current_theme']}, "
            f"Видео {data['video_index']+1}, Критерий {data['current_criterion']+1}"
        )
        await send_video(update, context)

    except Exception as e:
        logger.error(f"Ошибка восстановления: {e}")
        await clear_progress(update.effective_user.id)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Не удалось восстановить сессию. Начинаем новую тему."
        )
        await start(update, context)


async def handle_favorite_video(update: Update, context: CallbackContext) -> None:
    """Обрабатывает нажатие best-X."""
    try:
        query = update.callback_query
        await query.answer()
        
        data = context.user_data
        
        if 'videos' not in data or not data['videos']:
            await query.message.reply_text("❌ Сессия устарела. Начните заново с /start.")
            await clear_progress(query.from_user.id)
            return

        best_idx = int(query.data.split('-')[1])
        videos = data['videos']

        # Проверка корректности индекса
        if best_idx < 0 or best_idx >= len(videos):
            await query.message.reply_text("❌ Ошибка выбора видео")
            return
        
        best_video_id = videos[best_idx]

        # Сохраняем выбор
        await save_best_video(
            user_id=query.from_user.id,
            theme=data['current_theme'],
            video_id=best_video_id
        )

        # Просим указать причину
        data['waiting_for_best_reason'] = True
        await save_progress(data, query.from_user.id)
        await query.message.reply_text(
            "Почему вам показалось это видео самым удачным?\n"
            "Введите ваш ответ сообщением в чат."
        )

    except BadRequest as e:
        if "Query is too old" in str(e):
            # Удаляем устаревшие кнопки и предлагаем начать заново
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="🕒 Сессия устарела. Для продолжения нажмите /start"
            )
            await clear_progress(query.from_user.id)
            context.user_data.clear()
        else:
            logger.error(f"BadRequest: {e}")

    except Exception as e:
        logger.error(f"Favorite video error: {e}")
        await clear_progress(query.from_user.id)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Критическая ошибка. Начните заново с /start."
        )

async def save_best_video(user_id: int, theme: str, video_id: str):
    """Сохраняет выбор лучшего видео в БД"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO best_videos (user_id, theme, video_id) VALUES (?, ?, ?)",
            (user_id, theme, video_id)
        )
        await db.commit()

async def handle_best_reason_message(update: Update, context: CallbackContext) -> None:
    data = context.user_data
    if data.get('waiting_for_best_reason'):
        try:
            reason = update.message.text
            user_id = update.effective_user.id
            theme = data['current_theme']
            
            if not theme or not reason:
                raise ValueError("Недостаточно данных")

            await save_best_reason(user_id, theme, reason)
            await mark_theme_completed(user_id, theme)
            await clear_progress(user_id)
            data.clear()

            await update.message.reply_text("✅ Спасибо! Ответ сохранён. Используйте /start для новых тем.")

        except Exception as e:
            logger.error(f"Ошибка сохранения причины: {e}")
            await update.message.reply_text("❌ Ошибка. Попробуйте снова.")


async def save_best_reason(user_id: int, theme: str, reason: str):
    """Обновляет запись с лучшим видео, добавляя причину"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """UPDATE best_videos 
            SET reason = ? 
            WHERE user_id = ? AND theme = ?""",
            (reason, user_id, theme)
        )
        await db.commit()


async def mark_theme_completed(user_id: int, theme: str):
    """Помечает тему как завершенную"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO completed_themes VALUES (?, ?)",
            (user_id, theme)
        )
        await db.commit()

async def clear_progress(user_id: int):
    """Удаляет запись о прогрессе"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "DELETE FROM progress WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()


async def get_completed_themes(user_id: int) -> list:
    """Получение завершенных тем"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT theme FROM completed_themes WHERE user_id = ?",
            (user_id,)
        )
        result = await cursor.fetchall()
        return [row[0] for row in result]


async def handle_video(update: Update, context: CallbackContext) -> None:
    """Если пользователь присылает видео, выводим file_id для справки."""
    if update.message.video:
        file_id = update.message.video.file_id
        await update.message.reply_text(f"Ваш file_id: {file_id}")
    else:
        await update.message.reply_text("Пожалуйста, отправьте видео.")

async def shutdown(application: Application):
    """Корректное завершение работы бота."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.close()
    await application.stop()
    await application.updater.stop()
    await application.update_queue.put(None)

async def error_handler(update: Update, context: CallbackContext) -> None:
    """Логируем ошибки без дублирующих сообщений"""
    logger.error(msg="Exception while handling update:", exc_info=context.error)
    
    # Отправляем сообщение только для определенных ошибок
    if update and not isinstance(context.error, BadRequest):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="⚠️ Для продолжения нажмите /start"
        )

def handle_shutdown(signum, loop, application):
    """Обработчик сигналов завершения"""
    logger.info(f"Received signal {signum}. Shutting down...")
    loop.create_task(shutdown(application))

async def main():
    """Запуск бота."""
    await init_db()
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_error_handler(error_handler)
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(handle_rating, pattern=r'^rating-\d$'))
    application.add_handler(CallbackQueryHandler(handle_favorite_video, pattern=r'^best-\d$'))
    # Обработка входящих видео (выдаём file_id)
    application.add_handler(MessageHandler(filters.VIDEO & ~filters.COMMAND, handle_video))

    # Обработка ответа пользователя "почему видео лучшее"
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_best_reason_message)
    )

    await application.run_polling()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logging.info("Бот остановлен пользователем.")
    finally:
        loop.close()