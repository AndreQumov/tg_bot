import psycopg2
from psycopg2 import sql
from tabulate import tabulate  # Для красивого вывода таблицы

# Конфигурация подключения
DB_CONFIG = {
    "dbname": "telegram_contacts",
    "user": "postgres",
    "password": "12345",
    "host": "localhost",
    "port": 5432
}

def fetch_contacts():
    try:
        # Подключение к базе данных
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Выполнение SQL-запроса
        query = "SELECT * FROM contacts;"
        cursor.execute(query)
        
        # Получение данных
        rows = cursor.fetchall()
        headers = [desc[0] for desc in cursor.description]  # Заголовки колонок
        
        if rows:
            print("Содержимое таблицы 'contacts':")
            print(tabulate(rows, headers=headers, tablefmt="grid"))
        else:
            print("Таблица 'contacts' пуста.")
        
        # Закрытие курсора и соединения
        cursor.close()
        conn.close()
    
    except Exception as e:
        print(f"Ошибка при работе с базой данных: {e}")

if __name__ == "__main__":
    fetch_contacts()
