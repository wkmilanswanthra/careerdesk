import datetime as dt
import os
import sys
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import ttk, messagebox, filedialog, simpledialog
from urllib.parse import urlparse
from store import Store, STATUSES, FIELDS, CLOSED

BG = '#f3f5fa'
INK = '#17243b'
MUTED = '#64748b'
BLUE = '#315cde'

class App(tk.Tk):
    def __init__(self, store=None):
        super().__init__()
        self.title('CareerDesk — Your job search, organized')
        self.geometry('1280x820')
        self.minsize(1000, 660)
        self.configure(bg=BG)
        self.store = store or Store()
        self.view = 'All applications'
        self.search = tk.StringVar()
        self.status_filter = tk.StringVar(value='All statuses')
        self.setup_style()
        self.build()
        self.search.trace_add('write', lambda *_: self.refresh())
        self.bind('<Control-n>', lambda e: self.edit())
        self.bind('<Control-f>', lambda e: self.search_entry.focus_set())
        self.protocol('WM_DELETE_WINDOW', self.shutdown)
        self.refresh()

    def setup_style(self):
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('.', font=('Segoe UI', 10), background=BG, foreground=INK)
        style.configure('TButton', padding=(13, 8), background='#e5eaf5', borderwidth=0)
        style.map('TButton', background=[('active', '#d4def4')])
        style.configure('Accent.TButton', background=BLUE, foreground='white')
        style.map('Accent.TButton', background=[('active', '#264bc1')])
        style.configure('TEntry', padding=7, fieldbackground='white')
        style.configure('TCombobox', padding=6, fieldbackground='white')
        style.configure('Treeview', background='white', fieldbackground='white', rowheight=40, borderwidth=0, font=('Segoe UI', 10))
        style.configure('Treeview.Heading', background='#e8edf6', font=('Segoe UI Semibold', 10), padding=10)
        style.map('Treeview', background=[('selected', '#dce6ff')], foreground=[('selected', INK)])

    def build(self):
        sidebar = tk.Frame(self, bg=INK, width=205)
        sidebar.pack(side='left', fill='y')
        sidebar.pack_propagate(False)
        tk.Label(sidebar, text='◈  CareerDesk', font=('Segoe UI', 18, 'bold'), fg='white', bg=INK).pack(anchor='w', padx=18, pady=(30, 4))
        tk.Label(sidebar, text='MAKE YOUR NEXT MOVE', font=('Segoe UI', 8, 'bold'), fg='#96a8c7', bg=INK).pack(anchor='w', padx=23, pady=(0, 35))
        self.nav = {}
        for name in ('All applications', 'Follow-ups', 'Interviews', 'Companies'):
            b = tk.Button(sidebar, text=name, anchor='w', command=lambda n=name: self.navigate(n), bg=INK, fg='#c6d2e8', activebackground='#2a3b58', activeforeground='white', bd=0, padx=22, pady=13, font=('Segoe UI', 11), cursor='hand2')
            b.pack(fill='x', padx=8, pady=3)
            self.nav[name] = b
        tk.Label(sidebar, text='LOCAL & PRIVATE\nYour data stays on this PC.', justify='left', bg=INK, fg='#96a8c7', font=('Segoe UI', 9)).pack(side='bottom', anchor='w', padx=22, pady=25)
        area = tk.Frame(self, bg=BG)
        area.pack(side='left', fill='both', expand=True, padx=28, pady=24)
        top = tk.Frame(area, bg=BG)
        top.pack(fill='x')
        self.heading = tk.Label(top, text='Your next chapter starts here.', font=('Segoe UI', 23, 'bold'), bg=BG, fg=INK)
        self.heading.pack(side='left')
        ttk.Button(top, text='+ New application', style='Accent.TButton', command=self.edit).pack(side='right')
        tk.Label(area, text='A clear view of your search. One step closer to the right opportunity.', bg=BG, fg=MUTED, font=('Segoe UI', 10)).pack(anchor='w', pady=(6, 23))
        cards = tk.Frame(area, bg=BG)
        cards.pack(fill='x')
        self.stats = {}
        for i, label in enumerate(('Applications', 'Active pipeline', 'Interviews', 'Offers', 'Follow-ups due')):
            cards.columnconfigure(i, weight=1)
            card = tk.Frame(cards, bg='white', padx=16, pady=13, highlightbackground='#e3e8f2', highlightthickness=1)
            card.grid(row=0, column=i, sticky='ew', padx=(0, 10 if i<4 else 0))
            tk.Label(card, text=label, bg='white', fg=MUTED, font=('Segoe UI', 9)).pack(anchor='w')
            val = tk.Label(card, text='0', bg='white', fg=BLUE if i==4 else INK, font=('Segoe UI', 27, 'bold'))
            val.pack(anchor='w')
            self.stats[label] = val
        toolbar = tk.Frame(area, bg=BG)
        toolbar.pack(fill='x', pady=(24, 12))
        self.search_entry = ttk.Entry(toolbar, textvariable=self.search, width=33)
        self.search_entry.pack(side='left')
        tk.Label(toolbar, text='Search company, role, notes', fg=MUTED, bg=BG, font=('Segoe UI', 9)).pack(side='left', padx=10)
        filt = ttk.Combobox(toolbar, textvariable=self.status_filter, values=('All statuses',)+STATUSES, state='readonly', width=16)
        filt.pack(side='right')
        filt.bind('<<ComboboxSelected>>', lambda e: self.refresh())
        self.context = tk.Label(area, text='', bg=BG, fg=MUTED, anchor='w')
        self.context.pack(fill='x', pady=(0, 8))
        table = tk.Frame(area, bg='white')
        table.pack(fill='both', expand=True)
        columns = ('company', 'role', 'status', 'applied', 'follow_up', 'interview')
        self.tree = ttk.Treeview(table, columns=columns, show='headings', selectmode='browse', height=4)
        for key, label, width in zip(columns, ('Company', 'Job title', 'Stage', 'Applied', 'Follow-up', 'Interview'), (160, 220, 110, 100, 100, 100)):
            self.tree.heading(key, text=label, command=lambda k=key: self.sort(k))
            self.tree.column(key, width=width, minwidth=80)
        self.tree.tag_configure('due', foreground='#b45309')
        self.tree.tag_configure('closed', foreground='#8a95a5')
        scroll = ttk.Scrollbar(table, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        self.tree.pack(fill='both', expand=True)
        self.tree.bind('<Double-1>', lambda e: self.edit_selected())
        self.tree.bind('<Return>', lambda e: self.edit_selected())
        self.empty = tk.Label(table, text='Your search starts with one opportunity.\n\nClick + New application to add your first job.', bg='white', fg=MUTED, font=('Segoe UI', 12), justify='center')
        actions = tk.Frame(area, bg=BG)
        actions.pack(fill='x', pady=(14, 0))
        for label, cmd in (('Open / edit', self.edit_selected), ('Open job post', self.open_job), ('Delete', self.delete_selected)):
            ttk.Button(actions, text=label, command=cmd).pack(side='left', padx=(0, 7))
        ttk.Button(actions, text='Data & backups', command=self.data_menu).pack(side='right')
        self.footer = tk.Label(area, text='', bg=BG, fg=MUTED, anchor='w', font=('Segoe UI', 9))
        self.footer.pack(fill='x', pady=(12, 0))

    def navigate(self, name):
        self.view = name
        self.refresh()

    def refresh(self):
        rows = self.store.all()
        today = dt.date.today().isoformat()
        active = [r for r in rows if r['status'] not in CLOSED]
        due = [r for r in active if r['follow_up'] and r['follow_up']<=today]
        counts = (len(rows), len([r for r in active if r['status']!='Saved']), len([r for r in rows if r['status']=='Interview']), len([r for r in rows if r['status'] in ('Offer','Accepted')]), len(due))
        for label, count in zip(self.stats, counts):
            self.stats[label].configure(text=str(count))
        for name,b in self.nav.items():
            b.configure(bg='#2a3b58' if name==self.view else INK, fg='white' if name==self.view else '#c6d2e8')
        q = self.search.get().casefold().strip()
        shown = [r for r in rows if (not q or q in ' '.join(str(r.get(k) or '') for k in FIELDS).casefold()) and (self.status_filter.get()=='All statuses' or r['status']==self.status_filter.get())]
        hint = 'Double-click an application to see details, notes and activity. Click column titles to sort.'
        if self.view=='Follow-ups':
            shown = [r for r in shown if r['status'] not in CLOSED and r['follow_up']]
            shown.sort(key=lambda r:r['follow_up'])
            hint = 'All scheduled follow-ups, soonest first. Amber rows are due today or overdue.'
        elif self.view=='Interviews':
            shown = [r for r in shown if r['status'] not in CLOSED and (r['interview'] or r['status']=='Interview')]
            shown.sort(key=lambda r:r['interview'] or '9999')
            hint = 'Interview-stage applications and scheduled interviews. Add time and meeting links in notes.'
        elif self.view=='Companies':
            shown.sort(key=lambda r:(r['company'].casefold(), r['role'].casefold()))
            hint = f'{len(set(r["company"].casefold() for r in shown))} companies · Applications grouped alphabetically by company.'
        selected = self.tree.selection()
        self.tree.delete(*self.tree.get_children())
        for r in shown:
            tag = 'closed' if r['status'] in CLOSED else 'due' if r['follow_up'] and r['follow_up']<=today else ''
            self.tree.insert('', 'end', iid=str(r['id']), values=tuple(r[k] or '—' for k in self.tree['columns']), tags=(tag,))
        if selected and self.tree.exists(selected[0]):
            self.tree.selection_set(selected[0])
        self.context.configure(text=f'{self.view}  ·  {len(shown)} results')
        self.heading.configure(text='Your next chapter starts here.' if self.view=='All applications' else self.view)
        self.footer.configure(text=hint)
        if shown:
            self.empty.place_forget()
        else:
            self.empty.configure(text='Your search starts with one opportunity.\n\nClick + New application to add your first job.' if not rows else 'No applications match this view.\n\nTry another search or status filter.')
            self.empty.place(relx=.5, rely=.5, anchor='center')

    def sort(self, column):
        reverse = getattr(self, '_last_sort', None)==(column, False)
        items = sorted(self.tree.get_children(), key=lambda i:self.tree.set(i,column).casefold(), reverse=reverse)
        for n,item in enumerate(items):
            self.tree.move(item,'',n)
        self._last_sort = (column,reverse)

    def selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo('Select an application', 'Select an application in the list first.', parent=self)
            return None
        return int(sel[0])

    def edit_selected(self):
        ident = self.selected()
        if ident:
            self.edit(ident)

    def open_job(self):
        ident = self.selected()
        if ident:
            self.launch(self.store.get(ident)['url'])

    def launch(self, url):
        if not url:
            messagebox.showinfo('No job link', 'Add a job post URL in the application details.', parent=self)
            return
        if urlparse(url).scheme not in ('http','https') or not urlparse(url).netloc:
            messagebox.showerror('Invalid link', 'Use a full https:// or http:// web address.', parent=self)
            return
        webbrowser.open(url)

    def delete_selected(self):
        ident = self.selected()
        if ident:
            row = self.store.get(ident)
            if messagebox.askyesno('Delete application?', f'Delete {row["role"]} at {row["company"]} and its activity history? This cannot be undone.', parent=self):
                self.store.delete(ident)
                self.refresh()

    def edit(self, ident=None):
        row = self.store.get(ident) if ident else {}
        win = tk.Toplevel(self)
        win.title('Application details' if ident else 'New application')
        win.geometry('820x740')
        win.minsize(740, 740)
        win.configure(bg=BG)
        win.transient(self)
        win.grab_set()
        outer = ttk.Frame(win, padding=22)
        outer.pack(fill='both', expand=True)
        tk.Label(outer, text='Keep your next move in focus.', bg=BG, fg=INK, font=('Segoe UI', 19, 'bold')).pack(anchor='w', pady=(0,16))
        tabs = ttk.Notebook(outer)
        tabs.pack(fill='both', expand=True)
        details = ttk.Frame(tabs, padding=16)
        activity = ttk.Frame(tabs, padding=16)
        tabs.add(details, text='  Details & notes  ')
        tabs.add(activity, text='  Activity history  ')
        vars = {}
        fields = (('company','Company *'),('role','Job title *'),('status','Stage'),('work_mode','Work arrangement'),('location','Location'),('salary','Salary / range (include currency)'),('applied','Applied · YYYY-MM-DD'),('follow_up','Follow-up · YYYY-MM-DD'),('interview','Interview · YYYY-MM-DD'),('contact','Contact name / email'),('url','Job post URL'))
        for n,(key,label) in enumerate(fields):
            col = n%2
            rr = (n//2)*2
            ttk.Label(details, text=label).grid(row=rr, column=col, sticky='w', pady=(4,4))
            default = 'Saved' if key=='status' else ''
            vars[key] = tk.StringVar(value=row.get(key,default))
            if key in ('status','work_mode'):
                widget = ttk.Combobox(details, textvariable=vars[key], values=STATUSES if key=='status' else ('','Remote','Hybrid','On-site'), state='readonly')
            else:
                widget = ttk.Entry(details, textvariable=vars[key])
            widget.grid(row=rr+1,column=col,sticky='ew',padx=(0,14) if col==0 else 0,pady=(0,6))
            if n==0:
                widget.focus_set()
        details.columnconfigure(0,weight=1)
        details.columnconfigure(1,weight=1)
        ttk.Label(details, text='Notes · job description, interview times, preparation, next steps').grid(row=12,column=0,columnspan=2,sticky='w',pady=(8,4))
        notesframe = ttk.Frame(details)
        notesframe.grid(row=13,column=0,columnspan=2,sticky='nsew')
        details.rowconfigure(13,weight=1)
        notes = tk.Text(notesframe, height=5, wrap='word',font=('Segoe UI',10),bd=1,relief='solid',undo=True)
        ns = ttk.Scrollbar(notesframe,command=notes.yview)
        notes.configure(yscrollcommand=ns.set)
        ns.pack(side='right',fill='y')
        notes.pack(fill='both',expand=True)
        notes.insert('1.0',row.get('notes',''))
        history = tk.Text(activity, wrap='word',font=('Segoe UI',10),bg='white',bd=0,padx=12,pady=12)
        history.pack(fill='both',expand=True)
        def refresh_history():
            history.configure(state='normal')
            history.delete('1.0','end')
            events = self.store.history(ident) if ident else []
            history.insert('end','\n\n'.join(f'{e["occurred"].replace("T","  ")}\n{e["message"]}' for e in events) or 'Save this application to start its activity history.')
            history.configure(state='disabled')
        refresh_history()
        def add_event():
            text = simpledialog.askstring('Add activity','What happened? (email, call, interview, next step)',parent=win)
            if text and text.strip():
                self.store.log(ident,text.strip())
                refresh_history()
                self.refresh()
        if ident:
            ttk.Button(activity,text='+ Log an update',command=add_event).pack(anchor='w',pady=(12,0))
        bottom = ttk.Frame(outer)
        bottom.pack(fill='x',pady=(16,0))
        def payload():
            return {**{k:v.get() for k,v in vars.items()},'notes':notes.get('1.0','end-1c')}
        initial = payload()
        def close():
            if payload()!=initial and not messagebox.askyesno('Discard changes?','Close without saving your changes?',parent=win):
                return
            win.destroy()
        def save():
            try:
                new_id = self.store.save(payload(),ident)
            except (ValueError, OSError) as e:
                messagebox.showerror('Check application',str(e),parent=win)
                return
            win.destroy()
            self.refresh()
            if self.tree.exists(str(new_id)):
                self.tree.selection_set(str(new_id))
                self.tree.see(str(new_id))
        ttk.Button(bottom,text='Cancel',command=close).pack(side='right',padx=(8,0))
        ttk.Button(bottom,text='Save application',style='Accent.TButton',command=save).pack(side='right')
        ttk.Button(bottom,text='Open job link',command=lambda:self.launch(vars['url'].get())).pack(side='left')
        win.protocol('WM_DELETE_WINDOW',close)
        win.bind('<Control-s>',lambda e:save())
        win.bind('<Escape>',lambda e:close())

    def data_menu(self):
        menu = tk.Menu(self,tearoff=False)
        for label,cmd in (('Export applications to CSV…',self.export),('Import applications from CSV…',self.import_data),('Back up database…',self.backup),('Restore database backup…',self.restore),('Open data folder',lambda:os.startfile(self.store.path.parent)),('About / help',self.help)):
            menu.add_command(label=label,command=cmd)
        menu.tk_popup(self.winfo_pointerx(),self.winfo_pointery())

    def export(self):
        path = filedialog.asksaveasfilename(parent=self,defaultextension='.csv',initialfile=f'CareerDesk-{dt.date.today()}.csv',filetypes=[('CSV','*.csv')])
        if path:
            try:
                self.store.export_csv(path)
                messagebox.showinfo('Export complete',f'Exported {len(self.store.all())} applications.',parent=self)
            except Exception as e:
                messagebox.showerror('Export failed',str(e),parent=self)

    def import_data(self):
        path = filedialog.askopenfilename(parent=self,filetypes=[('CSV','*.csv')])
        if path and messagebox.askyesno('Import applications','Import adds new records, including duplicates. Continue?',parent=self):
            try:
                count = self.store.import_csv(path)
                self.refresh()
                messagebox.showinfo('Import complete',f'Added {count} applications.',parent=self)
            except Exception as e:
                messagebox.showerror('Import failed',str(e),parent=self)

    def backup(self):
        path = filedialog.asksaveasfilename(parent=self,defaultextension='.db',initialfile=f'CareerDesk-backup-{dt.date.today()}.db',filetypes=[('Database backup','*.db')])
        if path:
            try:
                self.store.backup(path)
                messagebox.showinfo('Backup saved','Your applications and activity history have been backed up.',parent=self)
            except Exception as e:
                messagebox.showerror('Backup failed',str(e),parent=self)

    def restore(self):
        import sqlite3
        path = filedialog.askopenfilename(parent=self,filetypes=[('CareerDesk database backup','*.db')])
        if not path:
            return
        source = None
        try:
            if Path(path).resolve()==self.store.path.resolve():
                raise ValueError('Select a backup, not the currently open database.')
            source = sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True)
            if source.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
                raise ValueError('The backup is damaged.')
            for table,required in (('applications',set(FIELDS)|{'id','created','updated'}),('activity',{'id','application_id','occurred','message'})):
                actual = {r[1] for r in source.execute(f'PRAGMA table_info({table})')}
                if actual!=required:
                    raise ValueError('This is not a compatible CareerDesk backup.')
            for record in source.execute('SELECT '+','.join(FIELDS)+' FROM applications'):
                from store import validate
                validate(dict(zip(FIELDS,record)))
            if not messagebox.askyesno('Replace current data?','Restore replaces all current applications and history. A safety backup will be created first. Continue?',parent=self):
                return
            safety = self.store.path.with_name('before-restore-'+dt.datetime.now().strftime('%Y%m%d-%H%M%S')+'.db')
            self.store.backup(safety)
            source.backup(self.store.db)
            self.refresh()
            messagebox.showinfo('Restored',f'Backup restored. Previous data saved to:\n{safety}',parent=self)
        except Exception as e:
            messagebox.showerror('Restore failed',str(e),parent=self)
        finally:
            if source:
                source.close()

    def help(self):
        messagebox.showinfo('CareerDesk', 'CareerDesk 1.0\n\nA private, offline job search workspace.\n\nCtrl+N: new application\nCtrl+F: search\nCtrl+S: save application details\nDouble-click: edit application\n\nDates use YYYY-MM-DD. Follow-ups due today or earlier appear in amber. Reminders are shown inside the app; it must be opened to review them.\n\nCSV exports contain application details; database backups also include activity history.\n\nData location:\n'+str(self.store.path),parent=self)

    def shutdown(self):
        self.store.close()
        self.destroy()

if __name__=='__main__':
    try:
        if '--self-test' in sys.argv:
            import tempfile
            with tempfile.TemporaryDirectory() as directory:
                store = Store(Path(directory)/'test.db')
                ident = store.save({'company':'Packaging test','role':'Engineer','status':'Interview'})
                app = App(store)
                app.update()
                assert len(app.tree.get_children()) == 1
                app.edit(ident)
                app.update()
                for widget in app.winfo_children():
                    if isinstance(widget, tk.Toplevel):
                        widget.destroy()
                app.shutdown()
        else:
            App().mainloop()
    except Exception:
        import traceback
        folder = Path(os.environ.get('LOCALAPPDATA',Path.home()))/'CareerDesk'
        folder.mkdir(parents=True,exist_ok=True)
        (folder/'error.log').write_text(traceback.format_exc(),encoding='utf-8')
        if '--self-test' not in sys.argv:
            messagebox.showerror('CareerDesk could not start','See the error log at:\n'+str(folder/'error.log'))
        sys.exit(1)
