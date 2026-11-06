import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from store import Store, validate

class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name)/'test.db')

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_application_lifecycle_and_history(self):
        ident = self.store.save({'company':'Example','role':'Engineer','status':'Applied','applied':'2026-11-06'})
        self.store.save({**self.store.get(ident),'status':'Interview','interview':'2026-11-12'},ident)
        self.store.log(ident,'Call with recruiter')
        self.assertEqual(self.store.get(ident)['status'],'Interview')
        self.assertEqual(len(self.store.history(ident)),3)
        self.store.delete(ident)
        self.assertEqual(self.store.all(),[])
        self.assertEqual(self.store.history(ident),[])

    def test_validation(self):
        for data in ({'company':'','role':'Engineer'}, {'company':'A','role':'B','interview':'2026-02-30'}, {'company':'A','role':'B','status':'Invalid'}):
            with self.assertRaises(ValueError):
                validate(data)

    def test_csv_round_trip_and_formula_safety(self):
        self.store.save({'company':'=Acme','role':'Développeur, senior','notes':'First line\nSecond line','salary':'-100'})
        path = Path(self.tmp.name)/'export.csv'
        self.store.export_csv(path)
        self.assertIn("'=Acme",path.read_text(encoding='utf-8-sig'))
        self.assertEqual(self.store.import_csv(path),1)
        rows=self.store.all()
        self.assertEqual(rows[0]['company'],rows[1]['company'])
        self.assertEqual(rows[0]['notes'],rows[1]['notes'])

    def test_invalid_import_is_atomic(self):
        path = Path(self.tmp.name)/'bad.csv'
        path.write_text('company,role,applied\nGood,Engineer,2026-11-06\nBad,Engineer,not-a-date\n',encoding='utf-8')
        with self.assertRaises(ValueError):
            self.store.import_csv(path)
        self.assertEqual(self.store.all(),[])

    def test_backup_is_complete_and_persistent(self):
        ident=self.store.save({'company':'Acme','role':'Analyst'})
        self.store.log(ident,'Sent portfolio')
        path=Path(self.tmp.name)/'backup.db'
        self.store.backup(path)
        copy=Store(path)
        try:
            self.assertEqual(copy.all(),self.store.all())
            self.assertEqual(copy.history(ident),self.store.history(ident))
        finally:
            copy.close()
        with self.assertRaises(ValueError):
            self.store.backup(self.store.path)

if __name__=='__main__':
    unittest.main()
