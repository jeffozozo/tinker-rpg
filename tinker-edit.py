#!/usr/bin/env python3
"""
Tinker RPG Editor - A no-code game editor for creating 2D adventure games
Simplified version with doors treated as regular tiles
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from PIL import Image, ImageTk
import glob

@dataclass
class Tile:
    """Represents a single tile in the game world"""
    type: str = "empty"
    walkable_override: Optional[bool] = None
    properties: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.properties is None:
            self.properties = {}
    
    def is_walkable(self, tile_manager):
        if self.walkable_override is not None:
            return self.walkable_override
        return tile_manager.get_default_walkable(self.type)
    
    def get_tile_category(self):
        if "_wall" in self.type:
            return "wall"
        elif "_floor" in self.type:
            return "floor"
        elif "_door_" in self.type:
            return "door"
        elif "_stairs" in self.type:
            return "stairs"
        else:
            return "unknown"

@dataclass
class GameObject:
    """Represents NPCs, items, or interactive objects"""
    type: str = "npc"
    x: int = 0
    y: int = 0
    properties: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.properties is None:
            self.properties = {}

@dataclass
class Trigger:
    """Represents a trigger tile that executes actions"""
    x: int = 0
    y: int = 0
    actions: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.actions is None:
            self.actions = []

@dataclass
class Area:
    """Represents a game area/map"""
    name: str = "Untitled Area"
    width: int = 20
    height: int = 15
    tiles: List[List[Tile]] = None
    objects: List[GameObject] = None
    triggers: List[Trigger] = None
    
    def __post_init__(self):
        if self.tiles is None:
            self.tiles = [[Tile() for _ in range(self.width)] for _ in range(self.height)]
        if self.objects is None:
            self.objects = []
        if self.triggers is None:
            self.triggers = []

class TileManager:
    """Manages loading tiles from PNG files and their properties"""
    
    def __init__(self):
        self.tiles = {}
        self.npcs = {}
        self.objects = {}
        self.triggers = {}
        self.load_all_assets()
    
    def load_all_assets(self):
        self.load_tiles()
        self.load_npcs()
        self.load_objects()
        self.load_triggers()
    
    def load_tiles(self):
        tiles_dir = "tiles"
        if not os.path.exists(tiles_dir):
            os.makedirs(tiles_dir)
            self._create_default_tile()
            return
        
        png_files = glob.glob(os.path.join(tiles_dir, "*.png"))
        if not png_files:
            self._create_default_tile()
            return
        
        for png_file in png_files:
            try:
                tile_name = os.path.splitext(os.path.basename(png_file))[0]
                pil_image = Image.open(png_file)
                if pil_image.size != (32, 32):
                    pil_image = pil_image.resize((32, 32), Image.NEAREST)
                photo_image = ImageTk.PhotoImage(pil_image)
                display_name = tile_name.replace('_', ' ').title()
                category = self._get_tile_category(tile_name)
                
                self.tiles[tile_name] = {
                    "image": photo_image,
                    "display_name": display_name,
                    "category": category
                }
            except Exception as e:
                print(f"Error loading {png_file}: {e}")
        
        if not self.tiles:
            self._create_default_tile()
    
    def load_npcs(self):
        npcs_dir = "npcs"
        if not os.path.exists(npcs_dir):
            os.makedirs(npcs_dir)
            return
        
        png_files = glob.glob(os.path.join(npcs_dir, "*.png"))
        for png_file in png_files:
            try:
                npc_name = os.path.splitext(os.path.basename(png_file))[0]
                pil_image = Image.open(png_file)
                if pil_image.size != (32, 32):
                    pil_image = pil_image.resize((32, 32), Image.NEAREST)
                photo_image = ImageTk.PhotoImage(pil_image)
                display_name = npc_name.replace('_', ' ').title()
                
                self.npcs[npc_name] = {
                    "image": photo_image,
                    "display_name": display_name
                }
            except Exception as e:
                print(f"Error loading NPC {png_file}: {e}")
    
    def load_objects(self):
        objects_dir = "objects"
        if not os.path.exists(objects_dir):
            os.makedirs(objects_dir)
            return
        
        png_files = glob.glob(os.path.join(objects_dir, "*.png"))
        for png_file in png_files:
            try:
                obj_name = os.path.splitext(os.path.basename(png_file))[0]
                pil_image = Image.open(png_file)
                if pil_image.size != (32, 32):
                    pil_image = pil_image.resize((32, 32), Image.NEAREST)
                photo_image = ImageTk.PhotoImage(pil_image)
                display_name = obj_name.replace('_', ' ').title()
                
                self.objects[obj_name] = {
                    "image": photo_image,
                    "display_name": display_name
                }
            except Exception as e:
                print(f"Error loading object {png_file}: {e}")
    
    def load_triggers(self):
        triggers_dir = "triggers"
        if not os.path.exists(triggers_dir):
            os.makedirs(triggers_dir)
            return
        
        py_files = glob.glob(os.path.join(triggers_dir, "*.py"))
        for py_file in py_files:
            try:
                trigger_name = os.path.splitext(os.path.basename(py_file))[0]
                with open(py_file, 'r') as f:
                    code = f.read()
                display_name = trigger_name.replace('_', ' ').title()
                
                self.triggers[trigger_name] = {
                    "code": code,
                    "display_name": display_name,
                    "file_path": py_file
                }
            except Exception as e:
                print(f"Error loading trigger {py_file}: {e}")
    
    def _get_tile_category(self, tile_name):
        if "_wall" in tile_name:
            return "wall"
        elif "_floor" in tile_name:
            return "floor"
        elif "_door_" in tile_name:
            return "door"
        elif "_stairs" in tile_name:
            return "stairs"
        else:
            return "unknown"
    
    def get_default_walkable(self, tile_name):
        category = self._get_tile_category(tile_name)
        return category in ["floor", "door", "stairs"]
    
    def _create_default_tile(self):
        pil_image = Image.new('RGB', (32, 32), color=(200, 200, 200))
        photo_image = ImageTk.PhotoImage(pil_image)
        self.tiles["empty"] = {
            "image": photo_image,
            "display_name": "Empty",
            "category": "floor"
        }
    
    def get_tile_names(self):
        return list(self.tiles.keys())
    
    def get_npc_names(self):
        return list(self.npcs.keys())
    
    def get_object_names(self):
        return list(self.objects.keys())
    
    def get_trigger_names(self):
        return list(self.triggers.keys())
    
    def get_tile_info(self, tile_name):
        return self.tiles.get(tile_name, self.tiles.get("empty", {}))
    
    def get_npc_info(self, npc_name):
        return self.npcs.get(npc_name, {})
    
    def get_object_info(self, obj_name):
        return self.objects.get(obj_name, {})
    
    def get_trigger_info(self, trigger_name):
        return self.triggers.get(trigger_name, {})

class TinkerEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Tinker RPG Editor")
        self.root.geometry("1400x800")
        
        self.tile_manager = TileManager()
        self.current_area = Area()
        self.current_file = None
        self.cursor_x = 0
        self.cursor_y = 0
        self.selected_tile = list(self.tile_manager.get_tile_names())[0] if self.tile_manager.get_tile_names() else "empty"
        self.selected_mode = "tile"
        self.tile_size = 32
        
        self.setup_ui()
        self.bind_events()
        
    def setup_ui(self):
        # Menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New", command=self.new_area)
        file_menu.add_command(label="Open", command=self.open_area)
        file_menu.add_command(label="Save", command=self.save_area)
        file_menu.add_command(label="Save As", command=self.save_area_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Reload Assets", command=self.reload_assets)
        tools_menu.add_command(label="Resize Canvas...", command=self.show_resize_dialog)
        tools_menu.add_command(label="Crop Canvas to Room", command=self.crop_canvas_to_room)
        
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
        
        ttk.Label(info_frame, text="Area Name:").pack(side=tk.LEFT)
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
        
    def on_key_press(self, event):
        key = event.keysym.lower()
        if self.root.focus_get() == self.canvas:
            if key in ['up', 'down', 'left', 'right']:
                self.move_cursor(key)
                return "break"
            elif key == 'space':
                self.place_tile()
                return "break"
            elif key == 'delete' or key == 'backspace':
                self.remove_tile()
                return "break"
    
    def move_cursor(self, direction):
        if direction == 'up' and self.cursor_y > 0:
            self.cursor_y -= 1
        elif direction == 'down' and self.cursor_y < self.current_area.height - 1:
            self.cursor_y += 1
        elif direction == 'left' and self.cursor_x > 0:
            self.cursor_x -= 1
        elif direction == 'right' and self.cursor_x < self.current_area.width - 1:
            self.cursor_x += 1
        self.update_cursor_display()
        self.update_properties_display()
    
    def place_tile(self):
        if self.selected_mode == "tile":
            current_tile = self.current_area.tiles[self.cursor_y][self.cursor_x]
            if current_tile.type == self.selected_tile:
                self.current_area.tiles[self.cursor_y][self.cursor_x] = Tile(type="empty")
            else:
                self.current_area.tiles[self.cursor_y][self.cursor_x] = Tile(type=self.selected_tile)
        
        elif self.selected_mode == "object":
            existing = [obj for obj in self.current_area.objects 
                       if obj.x == self.cursor_x and obj.y == self.cursor_y]
            if existing and existing[0].type == self.selected_tile:
                self.current_area.objects = [obj for obj in self.current_area.objects 
                                           if not (obj.x == self.cursor_x and obj.y == self.cursor_y)]
            else:
                self.current_area.objects = [obj for obj in self.current_area.objects 
                                           if not (obj.x == self.cursor_x and obj.y == self.cursor_y)]
                self.current_area.objects.append(GameObject(
                    type=self.selected_tile, x=self.cursor_x, y=self.cursor_y))
        
        elif self.selected_mode == "npc":
            npc_types = set(self.tile_manager.get_npc_names()) or {"guard", "merchant", "villager"}
            existing = [obj for obj in self.current_area.objects 
                       if obj.x == self.cursor_x and obj.y == self.cursor_y and obj.type in npc_types]
            if existing and existing[0].type == self.selected_tile:
                self.current_area.objects = [obj for obj in self.current_area.objects 
                                           if not (obj.x == self.cursor_x and obj.y == self.cursor_y and 
                                                  obj.type in npc_types)]
            else:
                self.current_area.objects = [obj for obj in self.current_area.objects 
                                           if not (obj.x == self.cursor_x and obj.y == self.cursor_y and 
                                                  obj.type in npc_types)]
                self.current_area.objects.append(GameObject(
                    type=self.selected_tile, x=self.cursor_x, y=self.cursor_y))
        
        elif self.selected_mode == "trigger":
            existing = [trig for trig in self.current_area.triggers 
                       if trig.x == self.cursor_x and trig.y == self.cursor_y]
            if existing:
                self.current_area.triggers = [trig for trig in self.current_area.triggers 
                                            if not (trig.x == self.cursor_x and trig.y == self.cursor_y)]
            else:
                self.current_area.triggers.append(Trigger(x=self.cursor_x, y=self.cursor_y))
        
        self.draw_area()
        self.update_properties_display()
    
    def remove_tile(self):
        if self.selected_mode == "tile":
            self.current_area.tiles[self.cursor_y][self.cursor_x] = Tile(type="empty")
        elif self.selected_mode == "object":
            npc_types = set(self.tile_manager.get_npc_names()) or {"guard", "merchant", "villager"}
            self.current_area.objects = [obj for obj in self.current_area.objects 
                                       if not (obj.x == self.cursor_x and obj.y == self.cursor_y and 
                                              obj.type not in npc_types)]
        elif self.selected_mode == "npc":
            npc_types = set(self.tile_manager.get_npc_names()) or {"guard", "merchant", "villager"}
            self.current_area.objects = [obj for obj in self.current_area.objects 
                                       if not (obj.x == self.cursor_x and obj.y == self.cursor_y and 
                                              obj.type in npc_types)]
        elif self.selected_mode == "trigger":
            self.current_area.triggers = [trig for trig in self.current_area.triggers 
                                        if not (trig.x == self.cursor_x and trig.y == self.cursor_y)]
        
        self.draw_area()
        self.update_properties_display()
    
    def on_canvas_click(self, event):
        self.canvas.focus_set()
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        grid_x = int(canvas_x // self.tile_size)
        grid_y = int(canvas_y // self.tile_size)
        
        if (0 <= grid_x < self.current_area.width and 0 <= grid_y < self.current_area.height):
            self.cursor_x = grid_x
            self.cursor_y = grid_y
            self.update_cursor_display()
            self.update_properties_display()
    
    def is_tile_blocked(self, x, y):
        tile = self.current_area.tiles[y][x]
        if not tile.is_walkable(self.tile_manager):
            return True
        
        # Check if any object on this tile blocks movement
        for obj in self.current_area.objects:
            if obj.x == x and obj.y == y:
                if obj.properties.get("walkable", True) is False:
                    return True
        
        # Check if any NPC blocks movement
        for obj in self.current_area.objects:
            if obj.x == x and obj.y == y:
                npc_names = set(self.tile_manager.get_npc_names())
                if obj.type in npc_names and obj.properties.get("walkable", False) is False:
                    return True
        
        return False

    def draw_area(self):
        self.canvas.delete("all")
        
        for y in range(self.current_area.height):
            for x in range(self.current_area.width):
                x1, y1 = x * self.tile_size, y * self.tile_size
                tile = self.current_area.tiles[y][x]
                tile_info = self.tile_manager.get_tile_info(tile.type)
                
                if "image" in tile_info:
                    self.canvas.create_image(x1, y1, image=tile_info["image"], anchor=tk.NW)
                else:
                    self.canvas.create_rectangle(x1, y1, x1 + self.tile_size, y1 + self.tile_size, 
                                               fill="lightgray", outline="black")
                
                self.canvas.create_rectangle(x1, y1, x1 + self.tile_size, y1 + self.tile_size, 
                                           outline="gray", width=1)
                
                # Show non-walkable tiles
                if tile.type != "empty" and self.is_tile_blocked(x, y):
                    self.canvas.create_text(x1 + 16, y1 + 16, text="✗", fill="red", 
                                          font=("Arial", 12, "bold"))
        
        # Draw objects and NPCs
        for obj in self.current_area.objects:
            x1, y1 = obj.x * self.tile_size, obj.y * self.tile_size
            npc_info = self.tile_manager.get_npc_info(obj.type)
            obj_info = self.tile_manager.get_object_info(obj.type)
            
            if "image" in npc_info:
                self.canvas.create_image(x1, y1, image=npc_info["image"], anchor=tk.NW)
            elif "image" in obj_info:
                self.canvas.create_image(x1, y1, image=obj_info["image"], anchor=tk.NW)
            else:
                x2, y2 = x1 + self.tile_size, y1 + self.tile_size
                if obj.type in ["guard", "merchant", "villager", "wizard", "knight", "enemy", "boss"]:
                    colors = {"guard": "#4169E1", "merchant": "#FFD700", "villager": "#90EE90",
                             "wizard": "#9370DB", "knight": "#C0C0C0", "enemy": "#DC143C", "boss": "#8B0000"}
                    color = colors.get(obj.type, "#FFD700")
                    self.canvas.create_oval(x1 + 4, y1 + 4, x2 - 4, y2 - 4, fill=color, outline="black", width=2)
                    self.canvas.create_text(x1 + 16, y1 + 16, text="N", fill="white", font=("Arial", 8, "bold"))
                else:
                    colors = {"item": "#32CD32", "lever": "#FF4500", "fountain": "#00CED1",
                             "chest": "#8B4513", "barrel": "#654321", "table": "#DEB887"}
                    color = colors.get(obj.type, "#32CD32")
                    self.canvas.create_rectangle(x1 + 4, y1 + 4, x2 - 4, y2 - 4, fill=color, outline="black", width=2)
        
        # Draw triggers
        for trigger in self.current_area.triggers:
            x1, y1 = trigger.x * self.tile_size, trigger.y * self.tile_size
            x2, y2 = x1 + self.tile_size, y1 + self.tile_size
            center_x, center_y = (x1 + x2) / 2, (y1 + y2) / 2
            self.canvas.create_polygon(center_x, y1 + 4, x2 - 4, center_y, center_x, y2 - 4, x1 + 4, center_y,
                                     fill="#FF6347", outline="black", width=2)
        
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.update_cursor_display()
    
    def update_cursor_display(self):
        self.canvas.delete("cursor")
        x1, y1 = self.cursor_x * self.tile_size, self.cursor_y * self.tile_size
        x2, y2 = x1 + self.tile_size, y1 + self.tile_size
        self.canvas.create_rectangle(x1, y1, x2, y2, outline="red", width=3, tags="cursor")
        self.cursor_label.config(text=f"Cursor: ({self.cursor_x}, {self.cursor_y})")
    
    def update_tile_display(self):
        self.tile_canvas.delete("all")
        
        if self.selected_mode == "tile":
            tiles_per_row = 5
            tile_names = self.tile_manager.get_tile_names()
            for i, tile_name in enumerate(tile_names):
                row, col = i // tiles_per_row, i % tiles_per_row
                x, y = col * 40 + 10, row * 40 + 10
                tile_info = self.tile_manager.get_tile_info(tile_name)
                self.tile_canvas.create_image(x, y, image=tile_info["image"], anchor=tk.NW, tags=f"tile_{tile_name}")
                if tile_name == self.selected_tile:
                    self.tile_canvas.create_rectangle(x-2, y-2, x+34, y+34, outline="red", width=2, tags="selection")
        
        elif self.selected_mode == "npc":
            npc_names = self.tile_manager.get_npc_names() or ["guard", "merchant", "villager", "wizard", "knight"]
            for i, npc_name in enumerate(npc_names):
                y = i * 40 + 10
                npc_info = self.tile_manager.get_npc_info(npc_name)
                if "image" in npc_info:
                    self.tile_canvas.create_image(10, y, image=npc_info["image"], anchor=tk.NW, tags=f"npc_{npc_name}")
                else:
                    colors = {"guard": "#4169E1", "merchant": "#FFD700", "villager": "#90EE90",
                             "wizard": "#9370DB", "knight": "#C0C0C0"}
                    color = colors.get(npc_name, "#FFD700")
                    self.tile_canvas.create_oval(10, y, 40, y + 30, fill=color, outline="black", tags=f"npc_{npc_name}")
                self.tile_canvas.create_text(50, y + 15, text=npc_name.title(), anchor=tk.W)
                if npc_name == self.selected_tile:
                    self.tile_canvas.create_rectangle(8, y-2, 200, y + 32, outline="red", width=2, tags="selection")
        
        elif self.selected_mode == "object":
            obj_names = self.tile_manager.get_object_names() or ["item", "lever", "fountain", "chest", "barrel"]
            for i, obj_name in enumerate(obj_names):
                y = i * 40 + 10
                obj_info = self.tile_manager.get_object_info(obj_name)
                if "image" in obj_info:
                    self.tile_canvas.create_image(10, y, image=obj_info["image"], anchor=tk.NW, tags=f"obj_{obj_name}")
                else:
                    colors = {"item": "#32CD32", "lever": "#FF4500", "fountain": "#00CED1",
                             "chest": "#8B4513", "barrel": "#654321"}
                    color = colors.get(obj_name, "#32CD32")
                    self.tile_canvas.create_rectangle(10, y, 40, y + 30, fill=color, outline="black", tags=f"obj_{obj_name}")
                self.tile_canvas.create_text(50, y + 15, text=obj_name.title(), anchor=tk.W)
                if obj_name == self.selected_tile:
                    self.tile_canvas.create_rectangle(8, y-2, 200, y + 32, outline="red", width=2, tags="selection")
        
        elif self.selected_mode == "trigger":
            trigger_names = self.tile_manager.get_trigger_names() or ["trigger"]
            for i, trigger_name in enumerate(trigger_names):
                y = i * 40 + 10
                self.tile_canvas.create_polygon(25, y + 5, 40, y + 20, 25, y + 35, 10, y + 20, 
                                              fill="red", outline="black", tags=f"trigger_{trigger_name}")
                self.tile_canvas.create_text(50, y + 20, text=trigger_name.title(), anchor=tk.W)
                if trigger_name == self.selected_tile:
                    self.tile_canvas.create_rectangle(8, y-2, 200, y + 32, outline="red", width=2, tags="selection")
        
        self.tile_canvas.configure(scrollregion=self.tile_canvas.bbox("all"))
        if hasattr(self, 'selected_tile_label'):
            self.selected_tile_label.config(text=f"Selected: {self.selected_tile}")
    
    def on_tile_canvas_click(self, event):
        clicked = self.tile_canvas.find_closest(event.x, event.y)[0]
        tags = self.tile_canvas.gettags(clicked)
        for tag in tags:
            if tag.startswith("tile_"):
                self.selected_tile = tag[5:]
                self.update_tile_display()
                break
            elif tag.startswith("obj_"):
                self.selected_tile = tag[4:]
                self.update_tile_display()
                break
            elif tag.startswith("npc_"):
                self.selected_tile = tag[4:]
                self.update_tile_display()
                break
            elif tag.startswith("trigger_"):
                self.selected_tile = tag[8:]
                self.update_tile_display()
                break
    
    def update_properties_display(self):
        self.properties_text.configure(state='normal')
        self.properties_text.delete(1.0, tk.END)
        
        tile = self.current_area.tiles[self.cursor_y][self.cursor_x]
        objects_here = [obj for obj in self.current_area.objects if obj.x == self.cursor_x and obj.y == self.cursor_y]
        triggers_here = [trig for trig in self.current_area.triggers if trig.x == self.cursor_x and trig.y == self.cursor_y]
        
        info = f"Position: ({self.cursor_x}, {self.cursor_y})\n\n"
        tile_info = self.tile_manager.get_tile_info(tile.type)
        global_walkable = self.tile_manager.get_default_walkable(tile.type)
        tile_category = tile.get_tile_category()
        
        info += f"Tile: {tile_info.get('display_name', tile.type)}\n"
        info += f"Category: {tile_category}\n"
        info += f"Walkable: {tile.is_walkable(self.tile_manager)}\n\n"
        
        self.global_walkable_label.config(text=f"Default: {global_walkable}")
        if tile.walkable_override is None:
            self.walkable_override_var.set("default")
        elif tile.walkable_override:
            self.walkable_override_var.set("walkable")
        else:
            self.walkable_override_var.set("not_walkable")
        
        if objects_here:
            for obj in objects_here:
                info += f"Object: {obj.type}\n"
        if triggers_here:
            for trigger in triggers_here:
                info += f"Trigger: {len(trigger.actions)} actions\n"
        
        self.properties_text.insert(1.0, info)
        self.properties_text.configure(state='disabled')
    
    def on_mode_change(self):
        self.selected_mode = self.mode_var.get()
        self.update_tile_display()
    
    def on_area_name_change(self, event):
        self.current_area.name = self.area_name_var.get()
    
    def on_walkable_change(self):
        tile = self.current_area.tiles[self.cursor_y][self.cursor_x]
        value = self.walkable_override_var.get()
        if value == "default":
            tile.walkable_override = None
        elif value == "walkable":
            tile.walkable_override = True
        else:
            tile.walkable_override = False
        self.update_properties_display()
        self.draw_area()
    
    # Canvas tools
    def show_resize_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Resize Canvas")
        dialog.geometry("300x150")
        dialog.transient(self.root)
        
        ttk.Label(dialog, text=f"Current: {self.current_area.width} x {self.current_area.height}").pack(pady=10)
        
        frame = ttk.Frame(dialog)
        frame.pack(pady=10)
        
        ttk.Label(frame, text="Width:").grid(row=0, column=0, padx=5)
        width_var = tk.StringVar(value=str(self.current_area.width))
        ttk.Entry(frame, textvariable=width_var, width=10).grid(row=0, column=1, padx=5)
        
        ttk.Label(frame, text="Height:").grid(row=0, column=2, padx=5)
        height_var = tk.StringVar(value=str(self.current_area.height))
        ttk.Entry(frame, textvariable=height_var, width=10).grid(row=0, column=3, padx=5)
        
        def apply():
            try:
                new_w, new_h = int(width_var.get()), int(height_var.get())
                if new_w > 0 and new_h > 0:
                    self.resize_canvas(new_w, new_h)
                    dialog.destroy()
            except ValueError:
                messagebox.showerror("Error", "Please enter valid numbers")
        
        ttk.Button(dialog, text="Apply", command=apply).pack(pady=10)
        ttk.Button(dialog, text="Cancel", command=dialog.destroy).pack()
    
    def resize_canvas(self, new_width, new_height):
        old_w, old_h = self.current_area.width, self.current_area.height
        new_tiles = [[Tile() for _ in range(new_width)] for _ in range(new_height)]
        
        copy_w, copy_h = min(old_w, new_width), min(old_h, new_height)
        for y in range(copy_h):
            for x in range(copy_w):
                new_tiles[y][x] = self.current_area.tiles[y][x]
        
        self.current_area.width, self.current_area.height = new_width, new_height
        self.current_area.tiles = new_tiles
        self.current_area.objects = [obj for obj in self.current_area.objects 
                                   if 0 <= obj.x < new_width and 0 <= obj.y < new_height]
        self.current_area.triggers = [trig for trig in self.current_area.triggers 
                                    if 0 <= trig.x < new_width and 0 <= trig.y < new_height]
        
        self.cursor_x = min(self.cursor_x, new_width - 1)
        self.cursor_y = min(self.cursor_y, new_height - 1)
        
        self.draw_area()
        self.update_properties_display()
        messagebox.showinfo("Resize", f"Canvas resized to {new_width}x{new_height}")
    
    def crop_canvas_to_room(self):
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')
        found_content = False
        
        for y in range(self.current_area.height):
            for x in range(self.current_area.width):
                if self.current_area.tiles[y][x].type != "empty":
                    min_x, max_x = min(min_x, x), max(max_x, x)
                    min_y, max_y = min(min_y, y), max(max_y, y)
                    found_content = True
        
        for obj in self.current_area.objects:
            min_x, max_x = min(min_x, obj.x), max(max_x, obj.x)
            min_y, max_y = min(min_y, obj.y), max(max_y, obj.y)
            found_content = True
        
        for trig in self.current_area.triggers:
            min_x, max_x = min(min_x, trig.x), max(max_x, trig.x)
            min_y, max_y = min(min_y, trig.y), max(max_y, trig.y)
            found_content = True
        
        if not found_content:
            messagebox.showinfo("Crop", "No content found to crop to.")
            return
        
        new_width, new_height = int(max_x - min_x + 1), int(max_y - min_y + 1)
        new_tiles = [[Tile() for _ in range(new_width)] for _ in range(new_height)]
        
        for y in range(int(min_y), int(max_y + 1)):
            for x in range(int(min_x), int(max_x + 1)):
                new_tiles[y - int(min_y)][x - int(min_x)] = self.current_area.tiles[y][x]
        
        for obj in self.current_area.objects:
            obj.x -= int(min_x)
            obj.y -= int(min_y)
        
        for trig in self.current_area.triggers:
            trig.x -= int(min_x)
            trig.y -= int(min_y)
        
        self.current_area.width, self.current_area.height = new_width, new_height
        self.current_area.tiles = new_tiles
        self.cursor_x = max(0, self.cursor_x - int(min_x))
        self.cursor_y = max(0, self.cursor_y - int(min_y))
        
        self.draw_area()
        self.update_properties_display()
        messagebox.showinfo("Crop", f"Canvas cropped to {new_width}x{new_height}")
    
    # File operations
    def reload_assets(self):
        self.tile_manager = TileManager()
        if self.tile_manager.get_tile_names():
            self.selected_tile = self.tile_manager.get_tile_names()[0]
        self.update_tile_display()
        self.draw_area()
        messagebox.showinfo("Reload", "Assets reloaded!")
    
    def new_area(self):
        if messagebox.askyesno("New", "Create new area? Unsaved changes will be lost."):
            self.current_area = Area()
            self.current_file = None
            self.cursor_x = self.cursor_y = 0
            self.area_name_var.set(self.current_area.name)
            self.draw_area()
            self.update_properties_display()
    
    def save_area(self):
        if self.current_file:
            self._save_to_file(self.current_file)
        else:
            self.save_area_as()
    
    def save_area_as(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            self._save_to_file(filename)
            self.current_file = filename
    
    def _save_to_file(self, filename):
        try:
            with open(filename, 'w') as f:
                json.dump(asdict(self.current_area), f, indent=2)
            messagebox.showinfo("Save", f"Area saved to {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {e}")
    
    def open_area(self):
        filename = filedialog.askopenfilename(filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if filename:
            try:
                with open(filename, 'r') as f:
                    area_dict = json.load(f)
                
                self.current_area = Area(**area_dict)
                
                # Reconstruct objects
                for y, row in enumerate(self.current_area.tiles):
                    for x, tile_data in enumerate(row):
                        if isinstance(tile_data, dict):
                            self.current_area.tiles[y][x] = Tile(**tile_data)
                
                self.current_area.objects = [GameObject(**obj) for obj in self.current_area.objects]
                self.current_area.triggers = [Trigger(**trig) for trig in self.current_area.triggers]
                
                self.current_file = filename
                self.cursor_x = self.cursor_y = 0
                self.area_name_var.set(self.current_area.name)
                self.draw_area()
                self.update_properties_display()
                messagebox.showinfo("Open", f"Area loaded from {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open: {e}")

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
