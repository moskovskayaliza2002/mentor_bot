import sqlite3
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "ratings.db"
EXCEL_PATH = BASE_DIR / "data" / "results.xlsx"

# Константы из кода бота
CRITERIA = [
    "Логичность",
    "Информативность",
    "Интересность",
    "Естественность",
    "Согласованность невербальных сигналов"
]

THEMES = {
    "Робототехника": 3,
    "Кто живет в Антарктиде?": 3,
    "Кто побывал в космосе?": 3
}

VIDEO_NAMES = {
    "BAACAgIAAxkBAAICd2fu0op2FHJKi1m7QGpVVdvKWTDRAAJWdwACZQl5S_llkb0_CmGJNgQ": "Робототехника - Человеческий",
    "BAACAgIAAxkBAAICeWfu0viUdwFlNZzSdae69xGgI90uAAJgdwACZQl5SwF6kl6EP6sXNgQ": "Робототехника - Сгенерированный",
    "BAACAgIAAxkBAAICe2fu0zeZAhxuI3k-VGGRhhtQY0ZgAAJkdwACZQl5S1sLnwKesL77NgQ": "Робототехника - Сгенерированный+",
    "BAACAgIAAxkBAAICfWfu03duP7DAGcwrN3cCOqOF7dqfAAJqdwACZQl5S88OE6dAP5I9NgQ": "Кто живет в Антарктиде? - Человеческий",
    "BAACAgIAAxkBAAICf2fu1BYe1Vw3VoUdOcRpNDwg7I9sAAJ3dwACZQl5S3o5xoU0FVwbNgQ": "Кто живет в Антарктиде? - Сгенерированный",
    "BAACAgIAAxkBAAICgWfu1FtO9Octp6vsrYBV5yfJL-DjAAJ-dwACZQl5S59QIpq9JsPXNgQ": "Кто живет в Антарктиде? - Сгенерированный+",
    "BAACAgIAAxkBAAICg2fu1J12-JorEkz5B7qVXPkP8BOJAAKLdwACZQl5S4nTlKsAAUvKITYE": "Кто побывал в космосе? - Человеческий",
    "BAACAgIAAxkBAAIChWfu1NOaYhKlhXIGArjXcN0a1eMcAAKYdwACZQl5S_CivLrQ9MOwNgQ": "Кто побывал в космосе? - Сгенерированный",
    "BAACAgIAAxkBAAICh2fu1RjzLDI9OeIQ7elA2L6oEAK9AAKpdwACZQl5S2cPjv9IVz8cNgQ": "Кто побывал в космосе? - Сгенерированный+"
}
def get_human_name(video_id: str) -> str:
    return VIDEO_NAMES.get(video_id, video_id)

def export_to_excel():
    try:
        conn = sqlite3.connect(DB_PATH)
        
        # Лист 1: Оценки по критериям
        ratings_df = pd.read_sql("SELECT * FROM ratings", conn)
        ratings_pivot = ratings_df.pivot_table(
            index=['user_id', 'theme', 'video_id'],
            columns='criterion',
            values='score',
            aggfunc='first'
        ).reset_index()
        ratings_pivot['video_name'] = ratings_pivot['video_id'].apply(get_human_name)
        ratings_pivot = ratings_pivot.drop('video_id', axis=1)

        # Лист 2: Статусы тем с прогрессом
        status_query = """
            SELECT 
                p.user_id,
                p.theme,
                'in progress' AS status,
                p.video_index + 1 AS current_video,
                p.current_criterion + 1 AS current_criterion,
                json_extract(p.videos, '$') AS videos_json
            FROM progress p
            UNION ALL
            SELECT 
                ct.user_id,
                ct.theme,
                'completed' AS status,
                NULL AS current_video,
                NULL AS current_criterion,
                NULL AS videos_json
            FROM completed_themes ct
        """
        status_df = pd.read_sql(status_query, conn)
        status_df['total_videos'] = status_df['theme'].map(THEMES)
        status_df['total_criteria'] = len(CRITERIA)
        status_df['progress'] = status_df.apply(
            lambda x: (
                f"Видео {int(x.current_video)}/{int(x.total_videos)}, "
                f"критерий {int(x.current_criterion)}/{int(x.total_criteria)}"
            ) if x.status == 'in progress' else 'Завершено', 
            axis=1
        )

        # Лист 3: Лучшие видео
        best_df = pd.read_sql("SELECT * FROM best_videos", conn)
        best_df['video_name'] = best_df['video_id'].apply(get_human_name)
        best_df = best_df.drop('video_id', axis=1)

        # Экспорт в Excel
        with pd.ExcelWriter(EXCEL_PATH, engine='openpyxl') as writer:
            ratings_pivot.to_excel(writer, sheet_name='Ratings', index=False)
            status_df[['user_id', 'theme', 'status', 'progress']].to_excel(
                writer, sheet_name='Theme Status', index=False
            )
            best_df.to_excel(writer, sheet_name='Best Videos', index=False)

        print(f"Данные успешно экспортированы в {EXCEL_PATH}")

    except Exception as e:
        print(f"Ошибка: {str(e)}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    export_to_excel()