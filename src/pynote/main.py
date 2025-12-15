# PyNote — main application
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import importlib.util
import os

try:
    from spellchecker import SpellChecker
except ImportError:
    SpellChecker = None

try:
    from pynote.ui import AboutDialog
except Exception:
    try:
        from ui import AboutDialog
    except Exception:
        # Fallback: load by file path
        base = os.path.dirname(__file__)
        path = os.path.join(base, 'ui.py')
        if os.path.exists(path):
            spec = importlib.util.spec_from_file_location('pynote.ui', path)
            ui_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(ui_module)  # type: ignore
            AboutDialog = ui_module.AboutDialog
        else:
            AboutDialog = None


def _load_themes_module():
    import importlib

    candidates = ['pynote.themes', 'src.pynote.themes', 'themes']
    for name in candidates:
        try:
            return importlib.import_module(name)
        except Exception:
            continue

    # fallback: load by file path next to this file
    base = os.path.dirname(__file__)
    path = os.path.join(base, 'themes.py')
    if os.path.exists(path):
        spec = importlib.util.spec_from_file_location('pynote.themes', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore
        return module

    raise ImportError('Could not import themes module')


themes = _load_themes_module()

APP_TITLE = "PyNote"


class PyNoteApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry('800x600')
        self.filepath = None
        # theme preference
        self.theme_name = themes.load_theme_pref()
        # tab width setting
        self.tab_width = themes.load_tab_width()
        # spell check
        self.spell_check_enabled = themes.load_spell_check_pref()
        self.spell_checker = SpellChecker() if SpellChecker else None
        self.misspelled = set()

        self._create_widgets()
        self._create_menu()
        self._bind_shortcuts()
        # apply theme after widgets/menu created
        self._apply_theme()
        # refresh recent files menu
        self._update_recent_menu()
        self._check_spelling()

    def _create_widgets(self):
        # Editor area
        editor_frame = tk.Frame(self)
        editor_frame.pack(side='top', fill='both', expand=True)
        
        # Gutter (line numbers)
        self.line_numbers = tk.Text(editor_frame, width=4, padx=5, takefocus=0,
                                     border=0, bg='#f0f0f0', fg='#666')
        self.line_numbers.pack(side='left', fill='y')
        
        # Main text area with scrollbar
        self.text = tk.Text(editor_frame, wrap='word', undo=True)
        self.vsb = ttk.Scrollbar(editor_frame, orient='vertical', command=self.text.yview)
        self.text.configure(yscrollcommand=self._on_text_scroll)
        self.text.pack(side='left', fill='both', expand=True)
        self.vsb.pack(side='right', fill='y')
        
        # Underline tag for misspelled words
        self.text.tag_configure('misspelled', underline=True, foreground='red')
        self.text.bind('<Button-3>', self._on_right_click)

        # Status bar
        self.status = tk.StringVar()
        self.status.set('Ln 1, Col 0')
        self.status_bar = tk.Label(self, textvariable=self.status, anchor='w')
        self.status_bar.pack(side='bottom', fill='x')

        # Bind events
        self.text.bind('<KeyRelease>', self._update_status)
        self.text.bind('<ButtonRelease>', self._update_status)
        self.text.bind('<Configure>', self._update_line_numbers)
        self._update_line_numbers()

    def _create_menu(self):
        menu = tk.Menu(self)
        filemenu = tk.Menu(menu, tearoff=0)
        filemenu.add_command(label='🆕 New', command=self.new_file, accelerator='Ctrl+N')
        filemenu.add_command(label='📂 Open', command=self.open_file, accelerator='Ctrl+O')
        filemenu.add_command(label='💾 Save', command=self.save_file, accelerator='Ctrl+S')
        filemenu.add_command(label='💾 Save As', command=self.save_as, accelerator='Ctrl+Shift+S')
        filemenu.add_separator()
        # Recent files
        self.recent_menu = tk.Menu(filemenu, tearoff=0)
        filemenu.add_cascade(label='Recent Files', menu=self.recent_menu)
        filemenu.add_separator()
        filemenu.add_command(label='Exit', command=self.quit)
        menu.add_cascade(label='File', menu=filemenu)
        # View menu
        viewmenu = tk.Menu(menu, tearoff=0)
        self._dark_var = tk.BooleanVar(value=(self.theme_name == 'dark'))
        viewmenu.add_checkbutton(label='Dark Theme', onvalue=True, offvalue=False,
                                 variable=self._dark_var, command=self._on_toggle_theme)
        viewmenu.add_separator()
        # Spell check toggle
        self.spell_check_var = tk.BooleanVar(value=self.spell_check_enabled)
        viewmenu.add_checkbutton(label='Spell Check', onvalue=True, offvalue=False,
                                 variable=self.spell_check_var, command=self._on_toggle_spell_check,
                                 state='normal' if SpellChecker else 'disabled')
        viewmenu.add_separator()
        # Tab width
        self.tab_var = tk.IntVar(value=self.tab_width)
        tabmenu = tk.Menu(viewmenu, tearoff=0)
        tabmenu.add_radiobutton(label='2 spaces', variable=self.tab_var, value=2,
                    command=lambda: self._set_tab_width(2))
        tabmenu.add_radiobutton(label='4 spaces', variable=self.tab_var, value=4,
                    command=lambda: self._set_tab_width(4))
        tabmenu.add_radiobutton(label='8 spaces', variable=self.tab_var, value=8,
                    command=lambda: self._set_tab_width(8))
        viewmenu.add_cascade(label='Tab Width', menu=tabmenu)
        menu.add_cascade(label='View', menu=viewmenu)
        # Help menu
        helpmenu = tk.Menu(menu, tearoff=0)
        helpmenu.add_command(label='About', command=self._show_about)
        menu.add_cascade(label='Help', menu=helpmenu)
        self.config(menu=menu)

        # keep menu references
        self.menu = menu
        self.file_menu = filemenu
        self.view_menu = viewmenu
        self.help_menu = helpmenu

# Keyboard shortcuts
    def _bind_shortcuts(self):
        self.bind('<Control-s>', lambda e: self.save_file())
        self.bind('<Control-o>', lambda e: self.open_file())
        self.bind('<Control-n>', lambda e: self.new_file())
        self.bind('<Control-Shift-S>', lambda e: self.save_as())
        self.bind('<Control-z>', lambda e: self.text.event_generate('<<Undo>>'))
        self.bind('<Control-y>', lambda e: self.text.event_generate('<<Redo>>'))
        # Tab inserts spaces
        self.text.bind('<Tab>', self._insert_tab)
        # Find (Ctrl+F)
        self.bind('<Control-f>', lambda e: self.show_find_dialog())

    def _apply_theme(self):
        theme = themes.get_theme(self.theme_name)
        # root/background
        try:
            self.configure(bg=theme['bg'])
        except Exception:
            pass
        # text widget
        try:
            themes.apply_theme(self.text, theme)
        except Exception:
            pass
        # status bar
        try:
            self.status_bar.configure(bg=theme['status_bg'], fg=theme['status_fg'])
        except Exception:
            pass
        # menus
        try:
            self.menu.configure(bg=theme['gutter_bg'], fg=theme['fg'])
            self.file_menu.configure(bg=theme['gutter_bg'], fg=theme['fg'])
            self.view_menu.configure(bg=theme['gutter_bg'], fg=theme['fg'])
            self.help_menu.configure(bg=theme['gutter_bg'], fg=theme['fg'])
        except Exception:
            pass

    def _on_toggle_theme(self):
        self.theme_name = 'dark' if self._dark_var.get() else 'light'
        themes.save_theme_pref(self.theme_name)
        self._apply_theme()

    def _show_about(self):
        if AboutDialog:
            AboutDialog(self)

    def _update_recent_menu(self):
        """Update Recent Files menu with current list."""
        self.recent_menu.delete(0, tk.END)
        files = themes.load_recent_files()
        if not files:
            self.recent_menu.add_command(label='(No recent files)', state='disabled')
        else:
            for i, filepath in enumerate(files, 1):
                filename = os.path.basename(filepath)
                self.recent_menu.add_command(
                    label=f'{i}. {filename}',
                    command=lambda p=filepath: self._open_recent(p)
                )

    def _open_recent(self, filepath):
        """Open a recent file."""
        if not self._confirm_discard():
            return
        if not os.path.exists(filepath):
            messagebox.showerror('Error', f'File not found: {filepath}')
            return
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = f.read()
            self.text.delete('1.0', tk.END)
            self.text.insert('1.0', data)
            self.filepath = filepath
            self.title(f"{APP_TITLE} - {filepath}")
            themes.add_recent_file(filepath)
            self._update_recent_menu()
        except Exception as e:
            messagebox.showerror('Error', f'Failed to open file: {str(e)}')

    def _insert_tab(self, event=None):
        """Insert spaces instead of tab character."""
        self.text.insert(tk.INSERT, ' ' * self.tab_width)
        return 'break'  # Prevent default tab behavior

    def _set_tab_width(self, width):
        """Change tab width setting."""
        self.tab_width = width
        themes.save_tab_width(width)

    def new_file(self):
        if self._confirm_discard():
            self.text.delete('1.0', tk.END)
            self.filepath = None
            self.title(APP_TITLE)

    def open_file(self):
        if not self._confirm_discard():
            return
        path = filedialog.askopenfilename(
            filetypes=[('Text Files', '*.txt;*.md;*.py'), ('All Files', '*.*')]
        )
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = f.read()
                self.text.delete('1.0', tk.END)
                self.text.insert('1.0', data)
                self.filepath = path
                self.title(f"{APP_TITLE} - {path}")
                themes.add_recent_file(path)
                self._update_recent_menu()
            except Exception as e:
                messagebox.showerror('Error', f'Failed to open file: {str(e)}')

    def save_file(self):
        if self.filepath:
            try:
                with open(self.filepath, 'w', encoding='utf-8') as f:
                    f.write(self.text.get('1.0', tk.END))
                self.text.edit_modified(False)
                messagebox.showinfo('Saved', 'File saved successfully')
            except Exception as e:
                messagebox.showerror('Error', f'Failed to save file: {str(e)}')
        else:
            self.save_as()

    def save_as(self):
        path = filedialog.asksaveasfilename(
            defaultextension='.txt',
            filetypes=[('Text Files', '*.txt;*.md;*.py'), ('All Files', '*.*')]
        )
        if path:
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(self.text.get('1.0', tk.END))
                self.filepath = path
                self.title(f"{APP_TITLE} - {path}")
                self.text.edit_modified(False)
                messagebox.showinfo('Saved', f'File saved as: {path}')
            except Exception as e:
                messagebox.showerror('Error', f'Failed to save file: {str(e)}')

    def _update_status(self, event=None):
        idx = self.text.index(tk.INSERT).split('.')
        line = idx[0]
        col = idx[1]
        
        # Count words and characters
        text = self.text.get('1.0', tk.END)
        chars = len(text) - 1  # Exclude trailing newline
        words = len(text.split()) if text.strip() else 0
        
        self.status.set(f'Ln {line}, Col {col} | Words: {words} | Chars: {chars}')
        self._update_line_numbers()
        self._check_spelling()

    def _update_line_numbers(self, event=None):
        lines = self.text.get('1.0', tk.END).count('\n')
        line_nums = '\n'.join(str(i) for i in range(1, lines + 1))
        
        self.line_numbers.config(state='normal')
        self.line_numbers.delete('1.0', tk.END)
        self.line_numbers.insert('1.0', line_nums)
        self.line_numbers.config(state='disabled')

    def _on_text_scroll(self, first, last):
        self.vsb.set(first, last)
        self._update_line_numbers()

    def _confirm_discard(self):
        if self.text.edit_modified():
            resp = messagebox.askyesnocancel(
                'Unsaved changes',
                'You have unsaved changes. Save before continuing?'
            )
            if resp is None:
                return False
            if resp:
                self.save_file()
        return True
    
    def show_find_dialog(self):
        from tkinter import simpledialog
        query = simpledialog.askstring('Find', 'Search text:')
        if query:
            self._find_text(query)

#issue 10, basic find functionality
    def _find_text(self, query):
        self.text.tag_remove('found', '1.0', tk.END)
        
        if not query:
            return
        
        pos = '1.0'
        count = 0
        while True:
            pos = self.text.search(query, pos, nocase=True, stopindex=tk.END)
            if not pos:
                break
            end_pos = f'{pos}+{len(query)}c'
            self.text.tag_add('found', pos, end_pos)
            count += 1
            pos = end_pos
        
        self.text.tag_config('found', background='yellow', foreground='black')
        
        if count > 0:
            messagebox.showinfo('Find', f'Found {count} match(es)')
        else:
            messagebox.showinfo('Find', 'No matches found')

    def _on_toggle_spell_check(self):
        self.spell_check_enabled = self.spell_check_var.get()
        themes.save_spell_check_pref(self.spell_check_enabled)
        self._check_spelling()

    def _check_spelling(self):
        self.text.tag_remove('misspelled', '1.0', tk.END)
        if not self.spell_check_enabled or not self.spell_checker:
            return
        
        text = self.text.get('1.0', tk.END)
        words = text.split()
        self.misspelled = self.spell_checker.unknown(words)
        
        for word in self.misspelled:
            pos = '1.0'
            while True:
                pos = self.text.search(r'\b' + word + r'\b', pos, nocase=True, 
                                      regexp=True, stopindex=tk.END)
                if not pos:
                    break
                end_pos = f'{pos}+{len(word)}c'
                self.text.tag_add('misspelled', pos, end_pos)
                pos = end_pos

    def _on_right_click(self, event):
        if not self.spell_check_enabled or not self.spell_checker:
            return
        
        pos = self.text.index(f'@{event.x},{event.y}')
        word_start = self.text.search(r'\b', pos, backwards=True, regexp=True)
        if not word_start:
            word_start = '1.0'
        word_end = self.text.search(r'\b', pos, regexp=True, stopindex=tk.END)
        if not word_end:
            word_end = tk.END
        
        word = self.text.get(word_start, word_end).strip()
        if not word or word not in self.misspelled:
            return
        
        suggestions = self.spell_checker.candidates(word)
        if not suggestions:
            messagebox.showinfo('Spell Check', f'No suggestions for "{word}"')
            return
        
        menu = tk.Menu(self, tearoff=True)
        for suggestion in list(suggestions)[:5]:
            menu.add_command(label=suggestion,
                           command=lambda s=suggestion, w=word: self._replace_word(w, s))
        menu.add_separator()
        menu.add_command(label=f'Add "{word}" to dictionary',
                        command=lambda w=word: self._add_to_dictionary(w))
        menu.post(event.x_root, event.y_root)

    def _replace_word(self, old_word, new_word):
        text_content = self.text.get('1.0', tk.END)
        new_content = text_content.replace(old_word, new_word, 1)
        self.text.delete('1.0', tk.END)
        self.text.insert('1.0', new_content)
        self._check_spelling()

    def _add_to_dictionary(self, word):
        if self.spell_checker:
            self.spell_checker.word_probability[word] = 1
            self.misspelled.discard(word)
            self._check_spelling()
            messagebox.showinfo('Spell Check', f'Added "{word}" to dictionary')



if __name__ == '__main__':
    app = PyNoteApp()
    app.mainloop()

