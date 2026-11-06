import csv
import datetime as dt
import os
import sqlite3
from pathlib import Path

STATUSES = ('Saved', 'Applied', 'Screening', 'Interview', 'Offer', 'Accepted', 'Rejected', 'Withdrawn')
FIELDS = ('company', 'role', 'status', 'location', 'work_mode', 'salary', 'url', 'contact', 'applied', 'follow_up', 'interview', 'notes')
CLOSED = ('Accepted', 'Rejected', 'Withdrawn')

def validate(data):
    result = {k: str(data.get(k, '') or '').strip() for k in FIELDS}
    if not result['company'] or not result['role']:
        raise ValueError('Company and job title are required.')
    result['status'] = result['status'] or 'Saved'
    if result['status'] not in STATUSES:
        raise ValueError('Choose a valid status.')
    for key in ('applied', 'follow_up', 'interview'):
        if result[key]:
            try:
                day = dt.date.fromisoformat(result[key])
                if day.isoformat() != result[key]:
                    raise ValueError()
            except ValueError:
                raise ValueError(f'{key.replace("_", " ").title()} must use YYYY-MM-DD, for example {dt.date.today()}.')
    return result

class Store:
    def __init__(self, path=None):
        self.path = Path(path) if path else Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'CareerDesk' / 'careers.db'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY, company TEXT NOT NULL, role TEXT NOT NULL,
                status TEXT NOT NULL, location TEXT, work_mode TEXT, salary TEXT,
                url TEXT, contact TEXT, applied TEXT, follow_up TEXT, interview TEXT,
                notes TEXT, created TEXT NOT NULL, updated TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS activity (
                id INTEGER PRIMARY KEY, application_id INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
                occurred TEXT NOT NULL, message TEXT NOT NULL);
        ''')
        self.db.commit()

    def all(self):
        return [dict(r) for r in self.db.execute('SELECT * FROM applications ORDER BY updated DESC, id DESC')]

    def get(self, ident):
        row = self.db.execute('SELECT * FROM applications WHERE id=?', (ident,)).fetchone()
        return dict(row) if row else None

    def save(self, data, ident=None):
        data = validate(data)
        now = dt.datetime.now().isoformat(timespec='seconds')
        with self.db:
            if ident:
                old = self.get(ident)
                if not old:
                    raise ValueError('This application no longer exists.')
                self.db.execute('UPDATE applications SET ' + ','.join(f'{k}=?' for k in FIELDS) + ',updated=? WHERE id=?', (*data.values(), now, ident))
                change = f'Status: {old["status"]} → {data["status"]}' if old['status'] != data['status'] else 'Application updated'
            else:
                cur = self.db.execute('INSERT INTO applications (' + ','.join(FIELDS) + ',created,updated) VALUES (' + ','.join('?' for _ in range(len(FIELDS)+2)) + ')', (*data.values(), now, now))
                ident = cur.lastrowid
                change = f'Application created · {data["status"]}'
            self.db.execute('INSERT INTO activity(application_id,occurred,message) VALUES(?,?,?)', (ident, now, change))
        return ident

    def history(self, ident):
        return [dict(r) for r in self.db.execute('SELECT * FROM activity WHERE application_id=? ORDER BY id DESC', (ident,))]

    def log(self, ident, message):
        with self.db:
            now = dt.datetime.now().isoformat(timespec='seconds')
            self.db.execute('INSERT INTO activity(application_id,occurred,message) VALUES(?,?,?)', (ident, now, message))
            self.db.execute('UPDATE applications SET updated=? WHERE id=?', (now, ident))

    def delete(self, ident):
        with self.db:
            self.db.execute('DELETE FROM applications WHERE id=?', (ident,))

    def export_csv(self, path):
        with open(path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction='ignore')
            writer.writeheader()
            for row in self.all():
                writer.writerow({k: ("'" + row[k] if row[k] and row[k][0] in '=+@-\t\r' else row[k]) for k in FIELDS})

    def import_csv(self, path):
        with open(path, newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames or not {'company', 'role'}.issubset(reader.fieldnames):
                raise ValueError('CSV requires company and role headers. Export a CSV to see all supported columns.')
            rows = []
            for number, row in enumerate(reader, 2):
                try:
                    rows.append(validate({k: (v[1:] if v and v.startswith("'") and len(v)>1 and v[1] in '=+@-\t\r' else v) for k,v in row.items() if k in FIELDS}))
                except ValueError as e:
                    raise ValueError(f'Row {number}: {e}') from e
        # Validate the entire file before inserting anything; roll back all rows on failure.
        now = dt.datetime.now().isoformat(timespec='seconds')
        with self.db:
            for data in rows:
                cur = self.db.execute('INSERT INTO applications (' + ','.join(FIELDS) + ',created,updated) VALUES (' + ','.join('?' for _ in range(len(FIELDS)+2)) + ')', (*data.values(), now, now))
                self.db.execute('INSERT INTO activity(application_id,occurred,message) VALUES(?,?,?)', (cur.lastrowid, now, 'Imported from CSV'))
        return len(rows)

    def backup(self, path):
        if Path(path).resolve() == self.path.resolve():
            raise ValueError('Choose a location different from the active database.')
        target = sqlite3.connect(path)
        try:
            self.db.backup(target)
        finally:
            target.close()

    def close(self):
        self.db.close()
