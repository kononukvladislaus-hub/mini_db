import os
import operator

class Table:
    def __init__(self, db, name, columns, fk_constraints=None):
        self.db = db
        self.name = name
        self.filename = f"{name}.db"
        self.columns = columns
        self.fk_constraints = fk_constraints or {}
        
        if not os.path.exists(self.filename):
            open(self.filename, 'w').close()

    def get_all(self):
        records = []
        with open(self.filename, 'r', encoding='utf-8') as f:
            for line in filter(str.strip, f):
                vals = line.rstrip('\n').split('|')
                records.append({c['name']: c['type'](v) for c, v in zip(self.columns, vals)})
        return records

    def _rewrite(self, records):
        with open(self.filename, 'w', encoding='utf-8') as f:
            for r in records:
                f.write("|".join(str(r[c['name']]) for c in self.columns) + "\n")

    def insert(self, record):
        record['id'] = int(record['id'])
        
        if any(r['id'] == record['id'] for r in self.get_all()):
            raise ValueError(f"Дубликат PK id={record['id']}")

        for col, ref_table in self.fk_constraints.items():
            if col in record and not any(r['id'] == record[col] for r in self.db.tables[ref_table].get_all()):
                raise ValueError(f"FK ошибка: {col}={record[col]} отсутствует в {ref_table}")

        with open(self.filename, 'a', encoding='utf-8') as f:
            f.write("|".join(str(record[c['name']]) for c in self.columns) + "\n")

    def delete(self, record_id):
        records = self.get_all()
        if not any(r['id'] == record_id for r in records):
            raise ValueError("Запись не найдена")

        for child in self.db.tables.values():
            for col, ref_table in child.fk_constraints.items():
                if ref_table == self.name and any(r[col] == record_id for r in child.get_all()):
                    raise ValueError(f"Связанные данные существуют в {child.name}.{col}")

        self._rewrite([r for r in records if r['id'] != record_id])

    def update(self, record_id, field, value):
        records = self.get_all()
        target = next((r for r in records if r['id'] == record_id), None)
        if not target:
            raise ValueError("Запись не найдена")

        col_def = next((c for c in self.columns if c['name'] == field), None)
        if not col_def:
            raise ValueError("Поле не найдено")

        new_val = col_def['type'](value)
        if field == 'id':
            if any(r['id'] == new_val and r is not target for r in records):
                raise ValueError("Дубликат PK")
            for child in self.db.tables.values():
                for col, ref in child.fk_constraints.items():
                    if ref == self.name and any(r[col] == record_id for r in child.get_all()):
                        raise ValueError(f"Нельзя менять id: на {record_id} ссылается {child.name}.{col}")
        elif field in self.fk_constraints:
            ref = self.db.tables[self.fk_constraints[field]]
            if not any(r['id'] == new_val for r in ref.get_all()):
                raise ValueError("FK ошибка")

        target[field] = new_val
        self._rewrite(records)


class Database:
    def __init__(self):
        self.tables = {
            'datasets': Table(self, "datasets", [
                {'name': 'id', 'type': int}, {'name': 'name', 'type': str},
                {'name': 'task', 'type': str}, {'name': 'size', 'type': int}
            ]),
            'models': Table(self, "models", [
                {'name': 'id', 'type': int}, {'name': 'name', 'type': str},
                {'name': 'version', 'type': str}
            ]),
            'experiments': Table(self, "experiments", [
                {'name': 'id', 'type': int}, {'name': 'dataset_id', 'type': int},
                {'name': 'model_id', 'type': int}, {'name': 'accuracy', 'type': float},
                {'name': 'status', 'type': str}
            ], {'dataset_id': 'datasets', 'model_id': 'models'})
        }

    def seed_data(self):
        if self.tables['datasets'].get_all():
            return
        
        for i in range(1, 6):
            self.tables['datasets'].insert({'id': i, 'name': f'Data{i}', 'task': 'Clf', 'size': 100 * i})
            
        for i in range(1, 6):
            self.tables['models'].insert({'id': i, 'name': f'Model{i}', 'version': '1.0'})
            
        for i in range(1, 21):
            self.tables['experiments'].insert({
                'id': i, 'dataset_id': (i % 5) + 1, 'model_id': (i % 5) + 1,
                'accuracy': round(0.7 + (i % 10) / 50, 2), 'status': 'done' if i % 3 else 'running'
            })


def cli():
    db = Database()
    db.seed_data()
    ops = {'=': operator.eq, '!=': operator.ne, '>': operator.gt, '<': operator.lt, '>=': operator.ge, '<=': operator.le}

    while True:
        cmd = input("MiniDB> ").strip().split()
        if not cmd: continue
        action, *args = cmd
        
        if action == 'exit': break
        
        try:
            if action in ('insert', 'update', 'delete') and not args:
                raise ValueError("Укажите таблицу")

            tbl = db.tables.get(args[0]) if args else None
            if action in ('select', 'insert', 'update', 'delete') and not tbl:
                raise ValueError("Таблица не найдена")

            if action == 'select':
                records = tbl.get_all()
                if len(args) == 1:
                    pass
                elif len(args) == 4:
                    field, op_sym, val = args[1], args[2], args[3]
                    col_def = next((c for c in tbl.columns if c['name'] == field), None)
                    if not col_def:
                        raise ValueError(f"Нет поля '{field}' в {tbl.name}")
                    op_func = ops.get(op_sym)
                    if not op_func:
                        raise ValueError(f"Неизвестный оператор '{op_sym}'. Доступны: {', '.join(ops)}")
                    records = [r for r in records if op_func(r[field], col_def['type'](val))]
                else:
                    raise ValueError("Формат: select <table> [<field> <op> <value>]")
                for r in records: print(r)

            elif action == 'insert':
                vals = args[1:]
                if len(vals) != len(tbl.columns):
                    raise ValueError(f"Нужно {len(tbl.columns)} значений: {[c['name'] for c in tbl.columns]}")
                record = {c['name']: c['type'](v) for c, v in zip(tbl.columns, vals)}
                tbl.insert(record)
                print("ОК")

            elif action == 'update':
                if len(args) != 4:
                    raise ValueError("Формат: update <table> <id> <field> <value>")
                tbl.update(int(args[1]), args[2], args[3])
                print("ОК")

            elif action == 'delete':
                if len(args) != 2:
                    raise ValueError("Формат: delete <table> <id>")
                tbl.delete(int(args[1]))
                print("ОК")

        except Exception as e:
            print(f"Ошибка: {e}")

if __name__ == "__main__":
    cli()