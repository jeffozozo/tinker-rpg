#!/usr/bin/env python3
"""
Tinker RPG Editor - Main Application with Enhanced Trigger System
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
from dataclasses import asdict

from data_classes import Tile, GameObject, Trigger, Area, Game
from tile_manager import TileManager
from editor_methods import EditorMethods
from file_manager import FileManager
from dialog_tools import DialogTools

class TinkerEditor(EditorMethods, FileManager, DialogTools):
    def __init__(self, root):
        self.root = root
        self.root.title("Tinker RPG Editor")
        self.root.geometry("1400x800")
        
        self.tile_manager = TileManager()
        self.current_game = Game()
        self.current_area = Area()
        self.current_area_file = None
        self.current_game_file = None
        self.cursor_x = 0
        self.cursor_y = 0
        self.selected_tile = list(self.tile_manager.get_tile_names())[0] if self.tile_manager.get_tile_names() else "empty"
        self.selected_mode = "tile"
        self.tile_size = 32
        
        # Initialize trigger system
        self.selected_trigger_index = 0
        self.trigger_colors = {
            "teleport": "#0066CC",      # Blue
            "inventory": "#009900",     # Green
            "tile_update": "#FFCC00",   # Yellow
            "area_object": "#FF6600",   # Orange
            "game_end": "#9900CC",      # Purple
            "show_dialog": "#00CCCC",   # Cyan
            "custom": "#CC0000"         # Red
        }
        
        self.create_directories()
        self.setup_ui()
        self.bind_events()
        self.show_startup_message()
        
    def create_directories(self):
        """Create necessary directories if they don't exist"""
        directories = ["tiles", "npcs", "objects", "triggers", "areas"]
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)
                
    def setup_ui(self):
        # Menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Game menu
        game_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Game", menu=game_menu)
        game_menu.add_command(label="New Game", command=self.new_game)
        game_menu.add_command(label="Open Game", command=self.open_game)
        game_menu.add_command(label="Save Game", command=self.save_game)
        game_menu.add_command(label="Save Game As", command=self.save_game_as)
        game_menu.add_separator()
        game_menu.add_command(label="Save All", command=self.save_all)
        game_menu.add_separator()
        game_menu.add_command(label="Game Properties", command=self.show_game_properties)
        
        # Area menu
        area_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Area", menu=area_menu)
        area_menu.add_command(label="New Area", command=self.new_area)
        area_menu.add_command(label="Open Area", command=self.open_area)
        area_menu.add_command(label="Save Area", command=self.save_area)
        area_menu.add_command(label="Save Area As", command=self.save_area_as)
        area_menu.add_separator()
        area_menu.add_command(label="Add Area to Game", command=self.add_area_to_game)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Reload Assets", command=self.reload_assets)
        tools_menu.add_command(label="Resize Canvas...", command=self.show_resize_dialog)
        tools_menu.add_command(label="Crop Canvas to Room", command=self.crop_canvas_to_room)
        tools_menu.add_separator()
        tools_menu.add_command(label="Update Game Assets", command=self.update_game_assets)
        
        # File menu (legacy support)
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.setup_tile_panel(main_frame)
        self.setup_area_panel(main_frame)
        self.setup_properties_panel(main_frame)

    def setup_tile_panel(self, parent):
        self.tile_frame = ttk.LabelFrame(parent, text="Toolbox", width=250)
        self.tile_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        self.tile_frame.pack_propagate(False)
        
        # Mode selection
        mode_frame = ttk.Frame(self.tile_frame)
        mode_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.mode_var = tk.StringVar(value="tile")
        ttk.Radiobutton(mode_frame, text="Tiles", variable=self.mode_var, 
                       value="tile", command=self.on_mode_change).pack(anchor=tk.W)
        ttk.Radiobutton(mode_frame, text="Objects", variable=self.mode_var, 
                       value="object", command=self.on_mode_change).pack(anchor=tk.W)
        ttk.Radiobutton(mode_frame, text="NPCs", variable=self.mode_var, 
                       value="npc", command=self.on_mode_change).pack(anchor=tk.W)
        ttk.Radiobutton(mode_frame, text="Triggers", variable=self.mode_var, 
                       value="trigger", command=self.on_mode_change).pack(anchor=tk.W)
        
        # Tile canvas
        canvas_frame = ttk.Frame(self.tile_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.tile_canvas = tk.Canvas(canvas_frame, bg="white", width=200)
        tile_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.tile_canvas.yview)
        self.tile_canvas.configure(yscrollcommand=tile_scrollbar.set)
        
        self.tile_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tile_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tile_canvas.bind('<Button-1>', self.on_tile_canvas_click)
        self.tile_canvas.configure(takefocus=True)

    def setup_area_panel(self, parent):
        self.area_frame = ttk.LabelFrame(parent, text="Area Editor")
        self.area_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Area info
        info_frame = ttk.Frame(self.area_frame)
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Game name
        ttk.Label(info_frame, text="Game:").pack(side=tk.LEFT)
        self.game_name_label = ttk.Label(info_frame, text=self.current_game.name, foreground="blue")
        self.game_name_label.pack(side=tk.LEFT, padx=(5, 15))
        
        # Area name
        ttk.Label(info_frame, text="Area:").pack(side=tk.LEFT)
        self.area_name_var = tk.StringVar(value=self.current_area.name)
        name_entry = ttk.Entry(info_frame, textvariable=self.area_name_var, width=20)
        name_entry.pack(side=tk.LEFT, padx=(5, 0))
        name_entry.bind('<KeyRelease>', self.on_area_name_change)
        
        self.cursor_label = ttk.Label(info_frame, text=f"Cursor: ({self.cursor_x}, {self.cursor_y})")
        self.cursor_label.pack(side=tk.RIGHT)
        
        self.selected_tile_label = ttk.Label(info_frame, text=f"Selected: {self.selected_tile}")
        self.selected_tile_label.pack(side=tk.RIGHT, padx=(0, 10))
        
        # Canvas
        canvas_frame = ttk.Frame(self.area_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.canvas = tk.Canvas(canvas_frame, bg="white")
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.configure(yscrollcommand=v_scrollbar.set)
        
        h_scrollbar = ttk.Scrollbar(self.area_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X, padx=5)
        self.canvas.configure(xscrollcommand=h_scrollbar.set)
        
        self.canvas.configure(takefocus=True)
        self.canvas.bind('<Button-1>', self.on_canvas_click)
        
        self.draw_area()
        self.update_tile_display()

    def setup_properties_panel(self, parent):
        props_frame = ttk.LabelFrame(parent, text="Properties", width=300)
        props_frame.pack(side=tk.RIGHT, fill=tk.Y)
        props_frame.pack_propagate(False)
        
        # Walkable controls
        walkable_frame = ttk.LabelFrame(props_frame, text="Walkable Settings")
        walkable_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.global_walkable_label = ttk.Label(walkable_frame, text="Global default: Unknown")
        self.global_walkable_label.pack(padx=5, pady=2)
        
        self.walkable_override_var = tk.StringVar(value="default")
        ttk.Radiobutton(walkable_frame, text="Use default", 
                       variable=self.walkable_override_var, value="default",
                       command=self.on_walkable_change).pack(anchor=tk.W, padx=5)
        ttk.Radiobutton(walkable_frame, text="Force walkable", 
                       variable=self.walkable_override_var, value="walkable",
                       command=self.on_walkable_change).pack(anchor=tk.W, padx=5)
        ttk.Radiobutton(walkable_frame, text="Force blocked", 
                       variable=self.walkable_override_var, value="not_walkable",
                       command=self.on_walkable_change).pack(anchor=tk.W, padx=5)
        
        # Properties text
        ttk.Label(props_frame, text="Details:").pack(padx=5, pady=(10,0))
        self.properties_text = tk.Text(props_frame, height=15, width=35, state='disabled')
        self.properties_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def bind_events(self):
        self.root.bind('<Key>', self.on_key_press)
        self.root.after(100, self.canvas.focus_set)

    def show_startup_message(self):
        """Show a consolidated startup message about what was loaded"""
        loaded_assets = self.tile_manager.loaded_assets
        
        message_parts = []
        
        # Show loaded assets
        if loaded_assets:
            message_parts.append("loaded: " + ", ".join(loaded_assets))
        
        # Show no areas at startup (since none are loaded initially)
        message_parts.append("loaded areas: none")
        message_parts.append("loaded game: " + self.current_game.name)
        
        if message_parts:
            messagebox.showinfo("Tinker RPG Editor", "\n".join(message_parts))
    
    def show_load_message(self, loaded_assets=None, loaded_areas=None, game_name=None):
        """Show a consolidated message about what was loaded"""
        message_parts = []
        
        # Show loaded assets
        if loaded_assets:
            message_parts.append("loaded: " + ", ".join(loaded_assets))
        
        # Show loaded areas
        if loaded_areas:
            message_parts.append("loaded areas: " + ", ".join(loaded_areas))
        else:
            message_parts.append("loaded areas: none")
        
        # Show loaded game
        if game_name:
            message_parts.append("loaded game: " + game_name)
        
        if message_parts:
            messagebox.showinfo("Load Complete", "\n".join(message_parts))

    # Asset management
    def reload_assets(self):
        self.tile_manager = TileManager()
        if self.tile_manager.get_tile_names():
            self.selected_tile = self.tile_manager.get_tile_names()[0]
        elif self.selected_mode == "trigger":
            self.selected_tile = "teleport"
        self.update_tile_display()
        self.draw_area()
        
        # Show consolidated reload message
        self.show_load_message(loaded_assets=self.tile_manager.loaded_assets)

def main():
    try:
        from PIL import Image, ImageTk
    except ImportError:
        print("Error: PIL (Pillow) required. Install with: pip install Pillow")
        return
    
    root = tk.Tk()
    editor = TinkerEditor(root)
    root.mainloop()

if __name__ == "__main__":
    main()