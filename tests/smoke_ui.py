"""Exercise real Tk widgets against a temporary database, without changing user data."""
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from store import Store
from app import App
with tempfile.TemporaryDirectory() as tmp:
    store=Store(Path(tmp)/'ui.db')
    app=App(store)
    app.update()
    assert not app.tree.get_children()
    ident=store.save({'company':'Example Company','role':'Software Engineer','status':'Interview','follow_up':'2020-01-01','interview':'2026-12-01'})
    app.refresh()
    app.update()
    assert len(app.tree.get_children())==1
    assert app.stats['Follow-ups due']['text']=='1'
    for view in ('Follow-ups','Interviews','Companies','All applications'):
        app.navigate(view)
        app.update()
        assert len(app.tree.get_children())==1
    app.search.set('no match')
    assert len(app.tree.get_children())==0
    app.search.set('example')
    app.edit(ident)
    app.update()
    dialogs=[w for w in app.winfo_children() if w.winfo_class()=='Toplevel']
    assert len(dialogs)==1
    dialogs[0].destroy()
    app.shutdown()
print('UI smoke checks passed')
