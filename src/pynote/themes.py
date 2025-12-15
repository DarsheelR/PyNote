# src/pynote/themes.py
"""
Theme definitions for PyNote editor.
"""

import os
import json


LIGHT_THEME = {
    'bg': '#FFFFFF',
    'fg': '#000000',
    'select_bg': '#316AC5',
    'select_fg': '#FFFFFF',
    'insert_bg': '#000000',
    'gutter_bg': '#F0F0F0',
    'gutter_fg': '#666666',
    'status_bg': '#E0E0E0',
    'status_fg': '#000000',
}

DARK_THEME = {
    'bg': '#1E1E1E',
    'fg': '#D4D4D4',
    'select_bg': '#264F78',
    'select_fg': '#FFFFFF',
    'insert_bg': '#FFFFFF',
    'gutter_bg': '#252526',
    'gutter_fg': '#858585',
    'status_bg': '#007ACC',
    'status_fg': '#FFFFFF',
}


def get_theme(name='light'):
    """
    Get theme configuration by name.
    
    Args:
        name: Theme name ('light' or 'dark')
    
    Returns:
        dict: Theme configuration
    """
    if name.lower() == 'dark':
        return DARK_THEME.copy()
    return LIGHT_THEME.copy()


def apply_theme(widget, theme):
    """
    Apply theme to a text widget.
    
    Args:
        widget: Tkinter Text widget
        theme: Theme dictionary
    """
    widget.configure(
        bg=theme['bg'],
        fg=theme['fg'],
        selectbackground=theme['select_bg'],
        selectforeground=theme['select_fg'],
        insertbackground=theme['insert_bg'],
    )


_CONFIG_PATH = os.path.join(os.path.expanduser('~'), '.pynote_config.json')


def load_theme_pref():
    """Load saved theme preference from config file.

    Returns:
        str: 'light' or 'dark' (default 'light')
    """
    try:
        if os.path.exists(_CONFIG_PATH):
            with open(_CONFIG_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            name = data.get('theme', 'light')
            if name.lower() in ('light', 'dark'):
                return name.lower()
    except Exception:
        pass
    return 'light'


def save_theme_pref(name='light'):
    """Save theme preference to config file."""
    try:
        data = {'theme': name}
        with open(_CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f)
    except Exception:
        pass

