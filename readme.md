# MiniDB

Учебная файловая мини-СУБД на чистом Python (без SQLite, Pandas и других сторонних библиотек). Реализована в рамках Лабораторной работы №1. Выполнил: Кононюк Владислав 25ТИДИ

## Возможности
- **Формат хранения:** плоские текстовые файлы (`.db`), разделитель `|`. Состояние сохраняется между запусками.
- **CRUD:** полная поддержка `INSERT`, `SELECT`, `UPDATE`, `DELETE` через консольный интерфейс (CLI).
- **Связи и ограничения (PK/FK):**
  - Запрет дубликатов Primary Key.
  - Строгая проверка Foreign Key: запрет вставки несуществующих ключей, защита от "висячих ссылок" при удалении или изменении ID родителя.
- **Типизация:** строгая конвертация типов для столбцов (`int`, `str`, `float`).
- **Фильтрация:** `SELECT` с поддержкой операторов сравнения (`=`, `!=`, `>`, `<`, `>=`, `<=`).

## Схема БД
Реализовано 3 связанные таблицы:
- `datasets` (id, name, task, size)
- `models` (id, name, version)
- `experiments` (id, dataset_id, model_id, accuracy, status)

Отношения: `experiments.dataset_id -> datasets.id`, `experiments.model_id -> models.id`.

## Запуск
Требования: Python 3.x.
```bash
python main.py
```
*При первом запуске автоматически создадутся файлы `.db` и сгенерируется тестовый набор данных (5 датасетов, 5 моделей, 20 экспериментов).*

## CLI и примеры запросов

**Синтаксис команд:**
```text
select <table> [<field> <op> <value>]
insert <table> <val1> <val2> ...
update <table> <id> <field> <value>
delete <table> <id>
exit
```

**Примеры:**
```bash
# Получить все записи
select experiments

# Отфильтровать данные
select experiments accuracy > 0.8
select datasets task = Clf

# Добавить запись (порядок значений строго по колонкам)
insert datasets 6 ImageNet Clf 1400000

# Обновить поле у записи
update experiments 1 status failed

# Удалить запись
delete models 5
```