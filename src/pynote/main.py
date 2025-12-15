# src/pynote/main.py
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import importlib.util
import os

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
    """Robustly load the `themes` module whether running as package or script.

    Tries several strategies: package import, relative import, loading by file path,
    then plain import. Raises the last exception if none succeed.
    """
    # 1) package import
    try:
        from pynote import themes as themes_mod
        return themes_mod
    except Exception:
        pass

    # 2) relative import (when executed as package)
    try:
        from . import themes as themes_mod  # type: ignore
        return themes_mod
    except Exception:
        pass

    # 3) load by file path next to this file
    try:
        base = os.path.dirname(__file__)
        path = os.path.join(base, 'themes.py')
        if os.path.exists(path):
            spec = importlib.util.spec_from_file_location('pynote.themes', path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)  # type: ignore
            return module
    except Exception:
        pass

    # 4) plain import as last resort
    try:
        import themes as themes_mod
        return themes_mod
    except Exception as e:
        raise e


themes = _load_themes_module()

APP_TITLE = "PyNote"


class PyNoteApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry('800x600')
        self._filepath = None
        # theme name loaded from persisted config
        self.theme_name = themes.load_theme_pref()

        self._create_widgets()
        self._create_menu()
        self._bind_shortcuts()
        # apply theme after widgets/menu created
        self._apply_theme()

    def _create_widgets(self):
        # Frame to hold line numbers and text
        editor_frame = tk.Frame(self)
        editor_frame.pack(side='top', fill='both', expand=True)
        
        # Line numbers widget
        self.line_numbers = tk.Text(editor_frame, width=4, padx=5, takefocus=0,
                                     border=0, bg='#f0f0f0', fg='#666')
        self.line_numbers.pack(side='left', fill='y')
        
        # Text widget with scrollbar
        self.text = tk.Text(editor_frame, wrap='word', undo=True)
        self.vsb = ttk.Scrollbar(editor_frame, orient='vertical', command=self.text.yview)
        self.text.configure(yscrollcommand=self._on_text_scroll)
        self.text.pack(side='left', fill='both', expand=True)
        self.vsb.pack(side='right', fill='y')

        # status bar (use tk.Label so colors can be adjusted)
        self.status = tk.StringVar()
        self.status.set('Ln 1, Col 0')
        self._status_bar = tk.Label(self, textvariable=self.status, anchor='w')
        self._status_bar.pack(side='bottom', fill='x')

        # update cursor position and line numbers
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
        filemenu.add_command(label='Exit', command=self.quit)
        menu.add_cascade(label='File', menu=filemenu)
        # View menu with theme toggle
        viewmenu = tk.Menu(menu, tearoff=0)
        self._dark_var = tk.BooleanVar(value=(self.theme_name == 'dark'))
        viewmenu.add_checkbutton(label='Dark Theme', onvalue=True, offvalue=False,
                                 variable=self._dark_var, command=self._on_toggle_theme)
        menu.add_cascade(label='View', menu=viewmenu)
        # Help menu with About
        helpmenu = tk.Menu(menu, tearoff=0)
        helpmenu.add_command(label='About', command=self._show_about)
        menu.add_cascade(label='Help', menu=helpmenu)
        self.config(menu=menu)

        # keep references for theme updates
        self._menu = menu
        self._filemenu = filemenu
        self._viewmenu = viewmenu
        self._helpmenu = helpmenu

#keyboard shortcuts
    def _bind_shortcuts(self):
        self.bind('<Control-s>', lambda e: self.save_file())
        self.bind('<Control-o>', lambda e: self.open_file())
        self.bind('<Control-n>', lambda e: self.new_file())
        self.bind('<Control-Shift-S>', lambda e: self.save_as())
        self.bind('<Control-z>', lambda e: self.text.event_generate('<<Undo>>'))
        self.bind('<Control-y>', lambda e: self.text.event_generate('<<Redo>>'))

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
            self._status_bar.configure(bg=theme['status_bg'], fg=theme['status_fg'])
        except Exception:
            pass
        # menus
        try:
            self._menu.configure(bg=theme['gutter_bg'], fg=theme['fg'])
            self._filemenu.configure(bg=theme['gutter_bg'], fg=theme['fg'])
            self._viewmenu.configure(bg=theme['gutter_bg'], fg=theme['fg'])
            self._helpmenu.configure(bg=theme['gutter_bg'], fg=theme['fg'])
        except Exception:
            pass

    def _on_toggle_theme(self):
        self.theme_name = 'dark' if self._dark_var.get() else 'light'
        themes.save_theme_pref(self.theme_name)
        self._apply_theme()

    def _show_about(self):
        if AboutDialog:
            AboutDialog(self)

    def new_file(self):
        if self._confirm_discard():
            self.text.delete('1.0', tk.END)
            self._filepath = None
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
                self._filepath = path
                self.title(f"{APP_TITLE} - {path}")
            except Exception as e:
                messagebox.showerror('Error', f'Failed to open file: {str(e)}')

    def save_file(self):
        if self._filepath:
            try:
                with open(self._filepath, 'w', encoding='utf-8') as f:
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
                self._filepath = path
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


if __name__ == '__main__':
    app = PyNoteApp()
    app.mainloop()

