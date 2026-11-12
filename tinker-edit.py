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
from enemy_editor import EnemyEditor
from editor_methods import EditorMethods
from file_manager import FileManager
from dialog_tools import DialogTools
from item_rules import ITEM_TYPES
from project_paths import asset_root, project_root

class TinkerEditor(EnemyEditor, EditorMethods, FileManager, DialogTools):
    def __init__(self, root):
        self.root = root
        self.root.title("Tinker RPG Editor")
        self.root.geometry("1400x800")
        self.set_app_icon()
        
        self.tile_manager = TileManager()
        self.current_game = Game()
        self.ensure_example_enemy_definitions()
        self.current_area = Area()
        self.current_area_file = None
        self.current_game_file = None
        self.cursor_x = 0
        self.cursor_y = 0
        self.selected_tile = list(self.tile_manager.get_tile_names())[0] if self.tile_manager.get_tile_names() else "empty"
        self.selected_mode = "tile"
        self.selected_enemy_id = None
        self.tile_size = 32
        
        # Initialize trigger system
        self.selected_trigger_index = 0
        self.trigger_colors = {
            "teleport": "#0066CC",      # Blue
            "inventory": "#009900",     # Green
            "tile_update": "#FFCC00",   # Yellow
            "area_object": "#FF6600",   # Orange
            "game_end": "#9900CC",      # Purple
            "show_message": "#00CCCC",   # Cyan
            "custom": "#CC0000"         # Red
        }
        
        self.create_directories()
        self.setup_ui()
        self._saved_game_state = asdict(self.current_game)
        self._saved_area_state = asdict(self.current_area)
        self.root.protocol("WM_DELETE_WINDOW", self.close_editor)
        self.bind_events()
        self.show_startup_message()

    def set_app_icon(self):
        from PIL import Image, ImageTk

        icon_path = os.path.join(
            asset_root(),
            "objects",
            "gargoyle_object.png",
        )
        with Image.open(icon_path) as icon:
            icon = icon.convert("RGBA").resize((128, 128), Image.NEAREST)
        self.app_icon = ImageTk.PhotoImage(icon, master=self.root)
        self.root.iconphoto(True, self.app_icon)
        
    def create_directories(self):
        """Create necessary directories if they don't exist"""
        directories = ["areas", "games", "saves"]
        for directory in directories:
            path = os.path.join(project_root(), directory)
            if not os.path.exists(path):
                os.makedirs(path)
                
    def setup_ui(self):
        # Menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Game menu
        game_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Game", menu=game_menu)
        game_menu.add_command(label="New Game", command=self.new_game)
        game_menu.add_command(label="Open Game", command=self.open_game)
        game_menu.add_cascade(
            label="Open Recent", menu=self.create_open_recent_menu(game_menu)
        )
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
        file_menu.add_command(label="Exit", command=self.close_editor)
        
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.setup_tile_panel(main_frame)
        self.setup_area_panel(main_frame)
        self.setup_properties_panel(main_frame)
        self.refresh_game_areas_list()
        self.refresh_trigger_editor()
        self.update_properties_display()

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
        ttk.Radiobutton(mode_frame, text="Enemies", variable=self.mode_var,
                       value="enemy", command=self.on_mode_change).pack(anchor=tk.W)
        ttk.Radiobutton(mode_frame, text="Player", variable=self.mode_var,
                       value="player", command=self.on_mode_change).pack(anchor=tk.W)
        ttk.Radiobutton(mode_frame, text="Triggers", variable=self.mode_var, 
                       value="trigger", command=self.on_mode_change).pack(anchor=tk.W)
        ttk.Radiobutton(mode_frame, text="Messages", variable=self.mode_var,
                       value="messages", command=self.on_mode_change).pack(anchor=tk.W)
        ttk.Radiobutton(mode_frame, text="Editor Help", variable=self.mode_var,
                       value="editor_help", command=self.on_mode_change).pack(anchor=tk.W)

        ttk.Button(
            self.tile_frame,
            text="Fill Empty Tiles",
            command=self.fill_empty_tiles,
        ).pack(fill=tk.X, padx=5, pady=(0, 5))
        
        # Tile canvas
        canvas_frame = ttk.Frame(self.tile_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.tile_canvas_frame = canvas_frame
        
        self.tile_canvas = tk.Canvas(canvas_frame, bg="white", width=200)
        tile_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.tile_canvas.yview)
        self.tile_canvas.configure(yscrollcommand=tile_scrollbar.set)
        
        self.tile_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tile_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tile_canvas.bind('<Button-1>', self.on_tile_canvas_click)
        self.tile_canvas.configure(takefocus=True)
        self.setup_enemy_palette(self.tile_frame)
        self.setup_player_inventory(self.tile_frame)

    def setup_area_panel(self, parent):
        self.area_frame = ttk.LabelFrame(parent, text="Area Editor")
        self.area_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Area info
        info_frame = ttk.Frame(self.area_frame)
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Game name
        ttk.Label(info_frame, text="Game:").pack(side=tk.LEFT)
        self.game_name_var = tk.StringVar(value=self.current_game.name)
        self.game_name_var.trace_add("write", self.on_game_name_change)
        self.game_name_entry = ttk.Entry(
            info_frame, textvariable=self.game_name_var, width=20
        )
        self.game_name_entry.pack(side=tk.LEFT, padx=(5, 15))
        
        # Area name
        ttk.Label(info_frame, text="Area:").pack(side=tk.LEFT)
        self.area_name_var = tk.StringVar(value=self.current_area.name)
        name_entry = ttk.Entry(info_frame, textvariable=self.area_name_var, width=20)
        name_entry.pack(side=tk.LEFT, padx=(5, 0))
        name_entry.bind('<KeyRelease>', self.on_area_name_change)
        
        coordinate_frame = ttk.Frame(info_frame)
        coordinate_frame.pack(side=tk.RIGHT)
        self.cursor_label = ttk.Label(
            coordinate_frame, text=f"Cursor: ({self.cursor_x}, {self.cursor_y})"
        )
        self.cursor_label.pack(anchor=tk.E)
        self.mouse_position_label = ttk.Label(coordinate_frame, text="Mouse: --")
        self.mouse_position_label.pack(anchor=tk.E)
        
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
        self.canvas.bind('<Button-3>', self.on_canvas_right_click)
        self.canvas.bind('<Motion>', self.on_canvas_motion)
        self.canvas.bind('<Leave>', self.on_canvas_leave)
        
        self.draw_area()
        self.update_tile_display()

    def setup_properties_panel(self, parent):
        panel = ttk.Frame(parent, width=320)
        panel.pack(side=tk.RIGHT, fill=tk.Y)
        panel.pack_propagate(False)
        viewport = tk.Canvas(panel, width=300, highlightthickness=0)
        scrollbar = ttk.Scrollbar(panel, orient=tk.VERTICAL, command=viewport.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        viewport.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        viewport.configure(yscrollcommand=scrollbar.set)
        props_frame = ttk.LabelFrame(viewport, text="Properties")
        window = viewport.create_window((0, 0), window=props_frame, anchor=tk.NW)
        props_frame.bind("<Configure>", lambda event: viewport.configure(scrollregion=viewport.bbox("all")))
        viewport.bind("<Configure>", lambda event: viewport.itemconfigure(window, width=event.width))

        areas_frame = ttk.LabelFrame(props_frame, text="Areas in Game")
        areas_frame.pack(fill=tk.X, padx=5, pady=5)
        areas_list_frame = ttk.Frame(areas_frame)
        areas_list_frame.pack(fill=tk.X, padx=5, pady=5)
        self.game_areas_listbox = tk.Listbox(
            areas_list_frame, height=4, exportselection=False
        )
        areas_scrollbar = ttk.Scrollbar(
            areas_list_frame, orient=tk.VERTICAL, command=self.game_areas_listbox.yview
        )
        self.game_areas_listbox.configure(yscrollcommand=areas_scrollbar.set)
        self.game_areas_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        areas_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.game_areas_listbox.bind(
            "<<ListboxSelect>>", self.load_selected_game_area
        )

        self.setup_enemy_properties(props_frame)

        self.player_setup_frame = ttk.LabelFrame(props_frame, text="Player Setup")
        player = self.get_player_settings()
        self.player_start_area_label = ttk.Label(
            self.player_setup_frame,
            text=self._player_start_area_text(),
            wraplength=250,
        )
        self.player_start_area_label.pack(anchor=tk.W, padx=5, pady=(5, 2))
        self.player_start_position_label = ttk.Label(
            self.player_setup_frame,
            text=self._player_start_position_text(),
        )
        self.player_start_position_label.pack(anchor=tk.W, padx=5, pady=2)
        ttk.Label(
            self.player_setup_frame,
            text="Choose a sprite in the left panel, then click the map to set the start.",
            wraplength=250,
        ).pack(anchor=tk.W, padx=5, pady=2)
        self.player_stat_vars = {}
        stats = player["stats"]
        for key, label in (
            ("starting_health", "Starting health"),
            ("max_health", "Maximum health"),
            ("starting_energy", "Starting energy"),
            ("max_energy", "Maximum energy"),
            ("strength", "Strength"),
            ("intelligence", "Intelligence"),
            ("gold", "Starting $"),
        ):
            row = ttk.Frame(self.player_setup_frame)
            row.pack(fill=tk.X, padx=5, pady=2)
            ttk.Label(row, text=f"{label}:").pack(side=tk.LEFT)
            value = tk.StringVar(value=str(stats[key]))
            ttk.Entry(row, textvariable=value, width=8).pack(side=tk.RIGHT)
            self.player_stat_vars[key] = value
        ttk.Button(
            self.player_setup_frame,
            text="Apply Player Settings",
            command=self.save_player_setup,
        ).pack(anchor=tk.E, padx=5, pady=5)
        self.player_setup_frame.pack_forget()
        
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

        self.tile_walkable_frame = walkable_frame

        self.object_definition_frame = ttk.LabelFrame(
            props_frame, text="Object Definition"
        )
        self.object_definition_frame.pack(fill=tk.X, padx=5, pady=5)

        self.object_gettable_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            self.object_definition_frame,
            text="Gettable (can be added to inventory)",
            variable=self.object_gettable_var,
            command=self.on_object_gettable_change,
        ).pack(anchor=tk.W, padx=5, pady=3)

        self.object_walkable_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            self.object_definition_frame,
            text="Walkable (does not block movement)",
            variable=self.object_walkable_var,
        ).pack(anchor=tk.W, padx=5, pady=3)

        type_row = ttk.Frame(self.object_definition_frame)
        type_row.pack(fill=tk.X, padx=5, pady=3)
        ttk.Label(type_row, text="Item type:").pack(side=tk.LEFT)
        self.object_item_type_var = tk.StringVar(value="object")
        item_type_selector = ttk.Combobox(
            type_row, textvariable=self.object_item_type_var,
            values=ITEM_TYPES, state="readonly", width=13,
        )
        item_type_selector.pack(side=tk.RIGHT)
        item_type_selector.bind("<<ComboboxSelected>>", self.on_object_item_type_change)
        self.object_weapon_frame = ttk.Frame(self.object_definition_frame)
        ttk.Label(self.object_weapon_frame, text="Weapon damage bonus:").pack(side=tk.LEFT)
        self.object_weapon_damage_var = tk.StringVar(value="0")
        ttk.Entry(
            self.object_weapon_frame, textvariable=self.object_weapon_damage_var, width=8,
        ).pack(side=tk.RIGHT)
        ttk.Label(
            self.object_definition_frame,
            text="Equip items in the runner to activate them. Weapon damage adds to strength; armor reduces incoming damage.",
            wraplength=260,
        ).pack(anchor=tk.W, padx=5, pady=3)

        self.item_detail_vars = {}
        self.item_detail_frames = {}
        for group, fields in (
            ("weapon", (("ranged", "Ranged attack", ("no", "yes")),
                        ("attack_range", "Range (tiles)", None),
                        ("energy_cost", "Energy per shot", None),
                        ("ammo_item", "Ammo object ID (optional)", None))),
            ("armor", (("equipment_slot", "Armor slot", ("head", "offhand")),
                       ("armor_bonus", "Armor bonus", None))),
            ("readable", (("read_text", "Text to read", None),)),
        ):
            frame = ttk.Frame(self.object_definition_frame)
            self.item_detail_frames[group] = frame
            for key, label, choices in fields:
                row = ttk.Frame(frame)
                row.pack(fill=tk.X, padx=5, pady=2)
                ttk.Label(row, text=label).pack(anchor=tk.W)
                variable = tk.StringVar(value="")
                self.item_detail_vars[key] = variable
                if choices:
                    ttk.Combobox(row, textvariable=variable, values=choices, state="readonly").pack(fill=tk.X)
                else:
                    ttk.Entry(row, textvariable=variable).pack(fill=tk.X)

        self.object_effects_frame = ttk.Frame(self.object_definition_frame)
        effect_mode_frame = ttk.Frame(self.object_effects_frame)
        effect_mode_frame.pack(fill=tk.X, padx=5, pady=3)
        ttk.Label(effect_mode_frame, text="Effect mode:").pack(side=tk.LEFT)
        self.object_effect_mode_var = tk.StringVar(value="passive")
        ttk.Combobox(
            effect_mode_frame,
            textvariable=self.object_effect_mode_var,
            values=("passive", "consumable"),
            state="readonly",
            width=13,
        ).pack(side=tk.LEFT, padx=5)

        ttk.Label(
            self.object_effects_frame,
            text="Signed stat changes (e.g. 5 or -2):",
        ).pack(anchor=tk.W, padx=5, pady=(5, 2))
        self.object_effect_vars = {}
        for stat in ("health", "energy", "armor", "attack"):
            row = ttk.Frame(self.object_effects_frame)
            row.pack(fill=tk.X, padx=5, pady=2)
            ttk.Label(row, text=f"{stat.title()}:").pack(side=tk.LEFT)
            value_var = tk.StringVar(value="0")
            ttk.Entry(row, textvariable=value_var, width=10).pack(side=tk.RIGHT)
            self.object_effect_vars[stat] = value_var

        ttk.Label(
            self.object_effects_frame,
            text="Consumables change current health/energy and are consumed. Items have no effect when already full.",
            wraplength=260,
        ).pack(anchor=tk.W, padx=5, pady=5)
        self.object_effects_frame.pack(fill=tk.X, padx=5, pady=3)

        self.object_save_button = ttk.Button(
            self.object_definition_frame,
            text="Save Changes",
            command=self.save_object_definition_changes,
        )
        self.object_save_button.pack(anchor=tk.E, padx=5, pady=5)
        self.object_definition_frame.pack_forget()

        self.trigger_editor_frame = ttk.LabelFrame(props_frame, text="Triggers at Cursor")
        trigger_list_frame = ttk.Frame(self.trigger_editor_frame)
        trigger_list_frame.pack(fill=tk.X, padx=5, pady=5)
        self.trigger_listbox = tk.Listbox(trigger_list_frame, height=4, exportselection=False)
        trigger_list_scrollbar = ttk.Scrollbar(
            trigger_list_frame, orient=tk.VERTICAL, command=self.trigger_listbox.yview
        )
        self.trigger_listbox.configure(yscrollcommand=trigger_list_scrollbar.set)
        self.trigger_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        trigger_list_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.trigger_listbox.bind("<<ListboxSelect>>", self.on_trigger_list_select)

        navigation_frame = ttk.Frame(self.trigger_editor_frame)
        navigation_frame.pack(fill=tk.X, padx=5)
        ttk.Button(
            navigation_frame, text="Previous", command=lambda: self.cycle_selected_trigger(-1)
        ).pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Button(
            navigation_frame, text="Next", command=lambda: self.cycle_selected_trigger(1)
        ).pack(side=tk.LEFT, expand=True, fill=tk.X)

        order_frame = ttk.Frame(self.trigger_editor_frame)
        order_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(order_frame, text="Move Up", command=lambda: self.move_selected_trigger(-1)).pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Button(order_frame, text="Move Down", command=lambda: self.move_selected_trigger(1)).pack(side=tk.LEFT, expand=True, fill=tk.X)

        self.trigger_form_frame = ttk.Frame(self.trigger_editor_frame)
        self.trigger_form_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        trigger_actions = ttk.Frame(self.trigger_editor_frame)
        trigger_actions.pack(fill=tk.X, padx=5, pady=(0, 5))
        ttk.Button(trigger_actions, text="Add", command=self.add_trigger_at_cursor).pack(side=tk.LEFT)
        ttk.Button(
            trigger_actions, text="Delete", command=lambda: self.delete_selected_trigger(confirm=True)
        ).pack(side=tk.LEFT, padx=3)
        ttk.Button(
            trigger_actions,
            text="Save",
            command=self.save_trigger_and_area,
        ).pack(side=tk.RIGHT)
        self.trigger_editor_frame.pack_forget()
        
        # Properties text
        self.details_label = ttk.Label(props_frame, text="Details:")
        self.details_label.pack(padx=5, pady=(10,0))
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
        self.on_mode_change()
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