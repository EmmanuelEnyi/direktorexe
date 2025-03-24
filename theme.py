"""
theme.py - Theme management for Direktor EXE Scrabble Tournament Manager

This module provides theming functionality for the application, allowing
for consistent visual styling across all windows and components.
"""

import customtkinter as ctk

# Define color schemes
LIGHT_MODE = {
    "primary": "#3B82F6",  # Blue
    "secondary": "#10B981",  # Green
    "accent": "#8B5CF6",  # Purple
    "background": "#F9FAFB",
    "card": "#FFFFFF",
    "text": "#1F2937",
    "text_secondary": "#6B7280",
    "border": "#E5E7EB",
    "error": "#EF4444",
    "success": "#10B981",
    "warning": "#F59E0B",
}

DARK_MODE = {
    "primary": "#3B82F6",  # Blue
    "secondary": "#10B981",  # Green
    "accent": "#8B5CF6",  # Purple
    "background": "#111827",
    "card": "#1F2937",
    "text": "#F9FAFB",
    "text_secondary": "#9CA3AF",
    "border": "#374151",
    "error": "#EF4444",
    "success": "#10B981",
    "warning": "#F59E0B",
}

current_theme = LIGHT_MODE

def set_theme_mode(mode="system"):
    """
    Set the application theme mode.
    
    Args:
        mode (str): "light", "dark", or "system"
    """
    global current_theme
    
    if mode == "light":
        ctk.set_appearance_mode("light")
        current_theme = LIGHT_MODE
    elif mode == "dark":
        ctk.set_appearance_mode("dark")
        current_theme = DARK_MODE
    else:  # system
        ctk.set_appearance_mode("system")
        # Determine if system is in dark mode
        if ctk.get_appearance_mode() == "Dark":
            current_theme = DARK_MODE
        else:
            current_theme = LIGHT_MODE

def apply_theme(app):
    """
    Apply the current theme to the application.
    
    Args:
        app: The main application instance
    """
    # Set the color theme for CustomTkinter
    ctk.set_default_color_theme("blue")
    
    # Configure specific widget colors if needed
    # This is minimal as CustomTkinter handles most theming automatically
    
    # You can customize specific widgets here if needed
    # For example:
    # app.configure(fg_color=current_theme["background"])
    
    # Return the current theme for reference
    return current_theme

def get_button_colors():
    """Get the appropriate button colors based on current theme."""
    return {
        "fg_color": current_theme["primary"],
        "hover_color": current_theme["accent"],
        "text_color": "#FFFFFF"
    }

def get_entry_colors():
    """Get the appropriate entry field colors based on current theme."""
    return {
        "fg_color": current_theme["card"],
        "border_color": current_theme["border"],
        "text_color": current_theme["text"]
    }

def get_label_colors():
    """Get the appropriate label colors based on current theme."""
    return {
        "text_color": current_theme["text"]
    }

def get_frame_colors():
    """Get the appropriate frame colors based on current theme."""
    return {
        "fg_color": current_theme["card"],
        "border_color": current_theme["border"]
    }

