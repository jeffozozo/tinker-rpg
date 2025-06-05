#!/usr/bin/env python3
"""
Tinker RPG Editor - A no-code game editor for creating 2D adventure games
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
    type: str = "empty"  # The tile type name (matches PNG filename)
    walkable_override: Optional[bool] = None  # None = use default, True/False = override
    door_state: str = "closed"  # For doors: "locked", "closed", "open"
    properties: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.properties is None:
            self.properties = {}
    
    def is_walkable(self, tile_manager):
        """Get the effective walkable state (override or default)"""
        if self.walkable_override is not None:
            return self.walkable_override
        
        # Use filename-based default
        return tile_manager.get_default_walkable(self.type)
    
    def get_tile_category(self):
        """Determine tile category from filename"""
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
    type: str = "npc"  # npc, item, lever, fountain, etc.
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
    connections: Dict[str, str] = None  # direction -> area_name
    
    def __post_init__(self):
        if self.tiles is None:
            self.tiles = [[Tile() for _ in range(self.width)] for _ in range(self.height)]
        if self.objects is None:
            self.objects = []
        if self.triggers is None:
            self.triggers = []
        if self.connections is None:
            self.connections = {}

class TileManager:
    """Manages loading tiles from PNG files and their properties"""
    
    def __init__(self):
        self.tiles = {}  # tile_name -> {"image": PhotoImage, "category": str, "display_name": str}
        self.npcs = {}   # npc_name -> {"image": PhotoImage, "display_name": str}
        self.objects = {} # object_name -> {"image": PhotoImage, "display_name": str}
        self.triggers = {} # trigger_name -> {"code": str, "display_name": str}
        self.load_all_assets()
    
    def load_all_assets(self):
        """Load all assets from their respective directories"""
        self.load_tiles()
        self.load_npcs()
        self.load_objects()
        self.load_triggers()
    
    def load_tiles(self):
        """Load all PNG files from the tiles directory"""
        tiles_dir = "tiles"
        if not os.path.exists(tiles_dir):
            print(f"Warning: {tiles_dir} directory not found. Creating it...")
            os.makedirs(tiles_dir)
            self._create_default_tile()
            return
        
        # Find all PNG files
        png_files = glob.glob(os.path.join(tiles_dir, "*.png"))
        
        if not png_files:
            print(f"Warning: No PNG files found in {tiles_dir} directory")
            self._create_default_tile()
            return
        
        print(f"Loading {len(png_files)} tiles from {tiles_dir}...")
        
        for png_file in png_files:
            try:
                # Get tile name from filename (without extension)
                tile_name = os.path.splitext(os.path.basename(png_file))[0]
                
                # Load and resize image if needed
                pil_image = Image.open(png_file)
                
                # Ensure it's 32x32
                if pil_image.size != (32, 32):
                    pil_image = pil_image.resize((32, 32), Image.NEAREST)
                
                # Convert to PhotoImage for tkinter
                photo_image = ImageTk.PhotoImage(pil_image)
                
                # Create display name (replace underscores with spaces, title case)
                display_name = tile_name.replace('_', ' ').title()
                
                # Determine category from filename
                category = self._get_tile_category(tile_name)
                
                self.tiles[tile_name] = {
                    "image": photo_image,
                    "display_name": display_name,
                    "category": category
                }
                
                print(f"  Loaded: {tile_name} -> {display_name} ({category})")
                
            except Exception as e:
                print(f"Error loading {png_file}: {e}")
        
        if not self.tiles:
            self._create_default_tile()
    
    def load_npcs(self):
        """Load NPC assets from npcs directory"""
        npcs_dir = "npcs"
        if not os.path.exists(npcs_dir):
            print(f"Creating {npcs_dir} directory...")
            os.makedirs(npcs_dir)
            return
        
        png_files = glob.glob(os.path.join(npcs_dir, "*.png"))
        print(f"Loading {len(png_files)} NPCs from {npcs_dir}...")
        
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
                
                print(f"  Loaded NPC: {npc_name} -> {display_name}")
                
            except Exception as e:
                print(f"Error loading NPC {png_file}: {e}")
    
    def load_objects(self):
        """Load object assets from objects directory"""
        objects_dir = "objects"
        if not os.path.exists(objects_dir):
            print(f"Creating {objects_dir} directory...")
            os.makedirs(objects_dir)
            return
        
        png_files = glob.glob(os.path.join(objects_dir, "*.png"))
        print(f"Loading {len(png_files)} objects from {objects_dir}...")
        
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
                
                print(f"  Loaded object: {obj_name} -> {display_name}")
                
            except Exception as e:
                print(f"Error loading object {png_file}: {e}")
    
    def load_triggers(self):
        """Load trigger Python files from triggers directory"""
        triggers_dir = "triggers"
        if not os.path.exists(triggers_dir):
            print(f"Creating {triggers_dir} directory...")
            os.makedirs(triggers_dir)
            # Create example trigger
            example_trigger = '''def execute(player, area, trigger_x, trigger_y):
    """
    Example trigger function.
    
    Args:
        player: The player object
        area: The current area object
        trigger_x, trigger_y: Position of the trigger
    
    Returns:
        str: Message to display (optional)
    """
    return "You stepped on a trigger!"
'''
            try:
                with open(os.path.join(triggers_dir, "example_trigger.py"), 'w') as f:
                    f.write(example_trigger)
                print("Created example trigger file")
            except Exception as e:
                print(f"Error creating example trigger: {e}")
            return
        
        py_files = glob.glob(os.path.join(triggers_dir, "*.py"))
        print(f"Loading {len(py_files)} triggers from {triggers_dir}...")
        
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
                
                print(f"  Loaded trigger: {trigger_name} -> {display_name}")
                
            except Exception as e:
                print(f"Error loading trigger {py_file}: {e}")
    
    def _get_tile_category(self, tile_name):
        """Determine tile category from filename"""
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
        """Get default walkable state based on filename"""
        category = self._get_tile_category(tile_name)
        
        if category == "wall":
            return False
        elif category == "floor":
            return True
        elif category == "door":
            # Doors depend on their state, handled elsewhere
            return True  # Default assumption
        elif category == "stairs":
            return True
        else:
            return True  # Unknown tiles default to walkable
    
    def _create_default_tile(self):
        """Create a basic default tile when no tiles are found"""
        # Create a simple colored square
        pil_image = Image.new('RGB', (32, 32), color=(200, 200, 200))
        photo_image = ImageTk.PhotoImage(pil_image)
        
        self.tiles["empty"] = {
            "image": photo_image,
            "display_name": "Empty",
            "category": "floor"
        }
    
    def get_tile_names(self):
        """Get list of available tile names"""
        return list(self.tiles.keys())
    
    def get_npc_names(self):
        """Get list of available NPC names"""
        return list(self.npcs.keys())
    
    def get_object_names(self):
        """Get list of available object names"""
        return list(self.objects.keys())
    
    def get_trigger_names(self):
        """Get list of available trigger names"""
        return list(self.triggers.keys())
    
    def get_tile_info(self, tile_name):
        """Get tile information"""
        return self.tiles.get(tile_name, self.tiles.get("empty", {}))
    
    def get_npc_info(self, npc_name):
        """Get NPC information"""
        return self.npcs.get(npc_name, {})
    
    def get_object_info(self, obj_name):
        """Get object information"""
        return self.objects.get(obj_name, {})
    
    def get_trigger_info(self, trigger_name):
        """Get trigger information"""
        return self.triggers.get(trigger_name, {})

class TinkerEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Tinker RPG Editor")
        self.root.geometry("1400x800")
        
        # Initialize tile manager
        self.tile_manager = TileManager()
        
        # Current state
        self.current_area = Area()
        self.current_file = None
        self.cursor_x = 0
        self.cursor_y = 0
        self.selected_tile = list(self.tile_manager.get_tile_names())[0] if self.tile_manager.get_tile_names() else "empty"
        self.selected_mode = "tile"  # tile, object, npc, trigger
        self.tile_size = 32  # pixels per tile in editor (now matches actual tile size)
        
        self.setup_ui()
        self.bind_events()
        
    def setup_ui(self):
        """Setup the main UI layout"""
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
        file_menu.add_command(label="Reload Assets", command=self.reload_assets)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Reload Assets", command=self.reload_assets)
        
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel - Tile selector
        self.setup_tile_panel(main_frame)
        
        # Center panel - Area editor
        self.setup_area_panel(main_frame)
        
        # Right panel - Properties
        self.setup_properties_panel(main_frame)
        
    def setup_tile_panel(self, parent):
        """Setup the tile selection panel"""
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
        
        # Tile grid display
        canvas_frame = ttk.Frame(self.tile_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Scrollable tile canvas
        self.tile_canvas = tk.Canvas(canvas_frame, bg="white", width=200)
        tile_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.tile_canvas.yview)
        self.tile_canvas.configure(yscrollcommand=tile_scrollbar.set)
        
        self.tile_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tile_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind tile canvas clicks and focus events
        self.tile_canvas.bind('<Button-1>', self.on_tile_canvas_click)
        self.tile_canvas.bind('<FocusIn>', self.on_toolbox_focus_in)
        self.tile_canvas.bind('<FocusOut>', self.on_toolbox_focus_out)
        
        # Make the tile canvas focusable
        self.tile_canvas.configure(highlightthickness=2, highlightcolor="blue", takefocus=True)
        
    def setup_area_panel(self, parent):
        """Setup the main area editing panel"""
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
        
        # Cursor position and selected tile info
        self.cursor_label = ttk.Label(info_frame, text=f"Cursor: ({self.cursor_x}, {self.cursor_y})")
        self.cursor_label.pack(side=tk.RIGHT)
        
        self.selected_tile_label = ttk.Label(info_frame, text=f"Selected: {self.selected_tile}")
        self.selected_tile_label.pack(side=tk.RIGHT, padx=(0, 10))
        
        # Canvas for area editing
        canvas_frame = ttk.Frame(self.area_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.canvas = tk.Canvas(canvas_frame, bg="white")
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.configure(yscrollcommand=v_scrollbar.set)
        
        h_scrollbar = ttk.Scrollbar(self.area_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X, padx=5)
        self.canvas.configure(xscrollcommand=h_scrollbar.set)
        
        # Simple canvas configuration for focus
        self.canvas.configure(highlightthickness=2, highlightcolor="green", takefocus=True)
        
        # Bind canvas events  
        self.canvas.bind('<Button-1>', self.on_canvas_click)
        self.canvas.bind('<FocusIn>', self.on_area_focus_in)
        self.canvas.bind('<FocusOut>', self.on_area_focus_out)
        
        self.draw_area()
        
        # Now update tile display after all UI elements are created
        self.update_tile_display()
        
    def setup_properties_panel(self, parent):
        """Setup the properties panel"""
        props_frame = ttk.LabelFrame(parent, text="Properties", width=300)
        props_frame.pack(side=tk.RIGHT, fill=tk.Y)
        props_frame.pack_propagate(False)
        
        # Current tile info
        self.current_tile_label = ttk.Label(props_frame, text="No tile selected")
        self.current_tile_label.pack(padx=5, pady=5)
        
        # Walkable controls for current tile
        walkable_frame = ttk.LabelFrame(props_frame, text="Walkable Settings")
        walkable_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Show global default
        self.global_walkable_label = ttk.Label(walkable_frame, text="Global default: Unknown")
        self.global_walkable_label.pack(padx=5, pady=2)
        
        # Override options
        self.walkable_override_var = tk.StringVar(value="default")
        ttk.Radiobutton(walkable_frame, text="Use global default", 
                       variable=self.walkable_override_var, value="default",
                       command=self.on_walkable_override_change).pack(anchor=tk.W, padx=5)
        ttk.Radiobutton(walkable_frame, text="Force walkable", 
                       variable=self.walkable_override_var, value="walkable",
                       command=self.on_walkable_override_change).pack(anchor=tk.W, padx=5)
        ttk.Radiobutton(walkable_frame, text="Force not walkable", 
                       variable=self.walkable_override_var, value="not_walkable",
                       command=self.on_walkable_override_change).pack(anchor=tk.W, padx=5)
        
        # Door state controls (only show for door tiles)
        self.door_frame = ttk.LabelFrame(props_frame, text="Door State")
        
        self.door_state_var = tk.StringVar(value="closed")
        ttk.Radiobutton(self.door_frame, text="Locked", 
                       variable=self.door_state_var, value="locked",
                       command=self.on_door_state_change).pack(anchor=tk.W, padx=5)
        ttk.Radiobutton(self.door_frame, text="Closed", 
                       variable=self.door_state_var, value="closed",
                       command=self.on_door_state_change).pack(anchor=tk.W, padx=5)
        ttk.Radiobutton(self.door_frame, text="Open", 
                       variable=self.door_state_var, value="open",
                       command=self.on_door_state_change).pack(anchor=tk.W, padx=5)
        
        # Properties text area (read-only)
        ttk.Label(props_frame, text="Detailed Properties:").pack(padx=5, pady=(10,0))
        self.properties_text = tk.Text(props_frame, height=25, width=35, state='disabled')
        self.properties_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
    def bind_events(self):
        """Bind keyboard and mouse events"""
        # Bind keys to the root window
        self.root.bind('<Key>', self.on_key_press)
        self.root.bind('<Tab>', self.on_tab_press)
        
        # Start with canvas having focus after a short delay
        self.root.after(100, self.canvas.focus_set)
        
    def on_tab_press(self, event):
        """Handle Tab key to switch focus between panels"""
        focused_widget = self.root.focus_get()
        if focused_widget == self.canvas:
            # Area editor has focus, switch to toolbox
            self.tile_canvas.focus_set()
        else:
            # Something else has focus, switch to area editor
            self.canvas.focus_set()
        return "break"  # Prevent default Tab behavior
    
    def on_toolbox_focus_in(self, event):
        """Handle focus entering the toolbox"""
        pass
        
    def on_toolbox_focus_out(self, event):
        """Handle focus leaving the toolbox"""
        pass
        
    def on_area_focus_in(self, event):
        """Handle focus entering the area editor"""
        pass
        
    def on_area_focus_out(self, event):
        """Handle focus leaving the area editor"""
        pass
        
    def update_tile_display(self):
        """Update the tile selection display"""
        self.tile_canvas.delete("all")
        
        if self.selected_mode == "tile":
            # Show tiles in a grid
            tiles_per_row = 5
            tile_names = self.tile_manager.get_tile_names()
            
            for i, tile_name in enumerate(tile_names):
                row = i // tiles_per_row
                col = i % tiles_per_row
                x = col * 40 + 10
                y = row * 40 + 10
                
                tile_info = self.tile_manager.get_tile_info(tile_name)
                
                # Draw tile image
                self.tile_canvas.create_image(x, y, image=tile_info["image"], anchor=tk.NW, tags=f"tile_{tile_name}")
                
                # Highlight selected tile
                if tile_name == self.selected_tile:
                    self.tile_canvas.create_rectangle(x-2, y-2, x+34, y+34, outline="red", width=2, tags="selection")
                
                # Show walkable indicator based on default
                default_walkable = self.tile_manager.get_default_walkable(tile_name)
                if not default_walkable:
                    self.tile_canvas.create_text(x+16, y+28, text="X", fill="red", font=("Arial", 8, "bold"))
        
        elif self.selected_mode == "npc":
            # Show NPCs from npcs directory
            npc_names = self.tile_manager.get_npc_names()
            
            if not npc_names:
                # Fallback to hardcoded list if no NPC files found
                npc_names = ["guard", "merchant", "villager", "wizard", "knight", "enemy", "boss"]
            
            for i, npc_name in enumerate(npc_names):
                y = i * 40 + 10
                
                npc_info = self.tile_manager.get_npc_info(npc_name)
                if "image" in npc_info:
                    # Use actual NPC image
                    self.tile_canvas.create_image(10, y, image=npc_info["image"], anchor=tk.NW, tags=f"npc_{npc_name}")
                else:
                    # Fallback to colored circle
                    npc_colors = {
                        "guard": "#4169E1", "merchant": "#FFD700", "villager": "#90EE90",
                        "wizard": "#9370DB", "knight": "#C0C0C0", "enemy": "#DC143C", "boss": "#8B0000"
                    }
                    color = npc_colors.get(npc_name, "#FFD700")
                    self.tile_canvas.create_oval(10, y, 40, y + 30, fill=color, 
                                               outline="black", tags=f"npc_{npc_name}")
                
                display_name = npc_info.get("display_name", npc_name.title())
                self.tile_canvas.create_text(50, y + 15, text=display_name, anchor=tk.W)
                
                # Highlight selected NPC
                if npc_name == self.selected_tile:
                    if "image" in npc_info:
                        self.tile_canvas.create_rectangle(8, y-2, 42, y + 32, outline="red", width=2, tags="selection")
                    else:
                        self.tile_canvas.create_oval(8, y-2, 42, y + 32, outline="red", width=2, tags="selection")
        
        elif self.selected_mode == "object":
            # Show objects from objects directory
            obj_names = self.tile_manager.get_object_names()
            
            if not obj_names:
                # Fallback to hardcoded list if no object files found
                obj_names = ["item", "lever", "fountain", "chest", "barrel", "table", "door_switch"]
            
            for i, obj_name in enumerate(obj_names):
                y = i * 40 + 10
                
                obj_info = self.tile_manager.get_object_info(obj_name)
                if "image" in obj_info:
                    # Use actual object image
                    self.tile_canvas.create_image(10, y, image=obj_info["image"], anchor=tk.NW, tags=f"obj_{obj_name}")
                else:
                    # Fallback to colored rectangle
                    obj_colors = {
                        "item": "#32CD32", "lever": "#FF4500", "fountain": "#00CED1",
                        "chest": "#8B4513", "barrel": "#654321", "table": "#DEB887", "door_switch": "#FF6347"
                    }
                    color = obj_colors.get(obj_name, "#32CD32")
                    self.tile_canvas.create_rectangle(10, y, 40, y + 30, fill=color, 
                                                    outline="black", tags=f"obj_{obj_name}")
                
                display_name = obj_info.get("display_name", obj_name.title())
                self.tile_canvas.create_text(50, y + 15, text=display_name, anchor=tk.W)
                
                # Highlight selected object
                if obj_name == self.selected_tile:
                    self.tile_canvas.create_rectangle(8, y-2, 42, y + 32, outline="red", width=2, tags="selection")
        
        elif self.selected_mode == "trigger":
            # Show triggers from triggers directory
            trigger_names = self.tile_manager.get_trigger_names()
            
            if not trigger_names:
                # Show generic trigger option
                self.tile_canvas.create_polygon(25, 10, 40, 25, 25, 40, 10, 25, 
                                              fill="red", outline="black", tags="trigger")
                self.tile_canvas.create_text(50, 25, text="Generic Trigger", anchor=tk.W)
                
                # Highlight if selected
                if self.selected_tile == "trigger":
                    self.tile_canvas.create_polygon(27, 8, 42, 25, 27, 42, 8, 25, 
                                                  outline="red", width=2, tags="selection")
            else:
                # Show available trigger files
                for i, trigger_name in enumerate(trigger_names):
                    y = i * 40 + 10
                    
                    trigger_info = self.tile_manager.get_trigger_info(trigger_name)
                    
                    # Draw trigger as diamond
                    self.tile_canvas.create_polygon(25, y + 5, 40, y + 20, 25, y + 35, 10, y + 20, 
                                                  fill="red", outline="black", tags=f"trigger_{trigger_name}")
                    
                    display_name = trigger_info.get("display_name", trigger_name.title())
                    self.tile_canvas.create_text(50, y + 20, text=display_name, anchor=tk.W)
                    
                    # Highlight selected trigger
                    if trigger_name == self.selected_tile:
                        self.tile_canvas.create_polygon(27, y + 3, 42, y + 20, 27, y + 37, 8, y + 20, 
                                                      outline="red", width=2, tags="selection")
        
        # Update scroll region
        self.tile_canvas.configure(scrollregion=self.tile_canvas.bbox("all"))
        
        # Update selected tile label
        if self.selected_mode == "tile" and hasattr(self, 'selected_tile_label'):
            tile_info = self.tile_manager.get_tile_info(self.selected_tile)
            self.selected_tile_label.config(text=f"Selected: {tile_info.get('display_name', self.selected_tile)}")
        elif hasattr(self, 'selected_tile_label'):
            self.selected_tile_label.config(text=f"Mode: {self.selected_mode.title()} - {self.selected_tile.title()}")
    
    def on_tile_canvas_click(self, event):
        """Handle clicks on the tile selection canvas"""
        # Set focus to toolbox when clicked
        self.tile_canvas.focus_set()
        
        # Find what was clicked
        clicked = self.tile_canvas.find_closest(event.x, event.y)[0]
        tags = self.tile_canvas.gettags(clicked)
        
        for tag in tags:
            if tag.startswith("tile_"):
                self.selected_tile = tag[5:]  # Remove "tile_" prefix
                self.update_tile_display()
                break
            elif tag.startswith("obj_"):
                self.selected_tile = tag[4:]  # Remove "obj_" prefix
                self.update_tile_display()
                break
            elif tag.startswith("npc_"):
                self.selected_tile = tag[4:]  # Remove "npc_" prefix
                self.update_tile_display()
                break
            elif tag.startswith("trigger_"):
                self.selected_tile = tag[8:]  # Remove "trigger_" prefix
                self.update_tile_display()
                break
            elif tag == "trigger":
                self.selected_tile = "trigger"
                self.update_tile_display()
                break
    
    def on_key_press(self, event):
        """Handle keyboard input"""
        key = event.keysym.lower()
        
        # Check which widget has focus
        focused_widget = self.root.focus_get()
        
        if focused_widget == self.canvas:
            # Canvas has focus - handle area editor keys
            if key in ['up', 'down', 'left', 'right']:
                self.move_cursor(key)
                return "break"
            elif key == 'space':
                self.place_tile()
                return "break"
            elif key == 'delete' or key == 'backspace':
                self.remove_tile()
                return "break"
        
        # For all other cases, let default behavior handle it
            
    def move_cursor(self, direction):
        """Move the cursor in the specified direction"""
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
        """Place or toggle the selected item at cursor position (mode-aware)"""
        if self.selected_mode == "tile":
            current_tile = self.current_area.tiles[self.cursor_y][self.cursor_x]
            
            if current_tile.type == self.selected_tile:
                # Same tile - clear to empty
                self.current_area.tiles[self.cursor_y][self.cursor_x] = Tile(type="empty")
            else:
                # Different tile or empty - place/replace with selected tile
                self.current_area.tiles[self.cursor_y][self.cursor_x] = Tile(
                    type=self.selected_tile, 
                    walkable_override=None  # Use global default initially
                )
                
        elif self.selected_mode == "object":
            # Check if there's already an object at this position
            existing_objects = [obj for obj in self.current_area.objects 
                              if obj.x == self.cursor_x and obj.y == self.cursor_y]
            
            if existing_objects and existing_objects[0].type == self.selected_tile:
                # Same object type - remove it
                self.current_area.objects = [obj for obj in self.current_area.objects 
                                           if not (obj.x == self.cursor_x and obj.y == self.cursor_y)]
            else:
                # Different object or no object - remove existing and place new
                self.current_area.objects = [obj for obj in self.current_area.objects 
                                           if not (obj.x == self.cursor_x and obj.y == self.cursor_y)]
                self.current_area.objects.append(GameObject(
                    type=self.selected_tile, x=self.cursor_x, y=self.cursor_y
                ))
                
        elif self.selected_mode == "npc":
            # Check if there's already an NPC at this position
            # NPCs are stored as objects, so we need to check for NPC types specifically
            npc_types = set(self.tile_manager.get_npc_names())
            if not npc_types:
                # Fallback to hardcoded NPC types if no files found
                npc_types = {"guard", "merchant", "villager", "wizard", "knight", "enemy", "boss"}
            
            existing_npcs = [obj for obj in self.current_area.objects 
                           if (obj.x == self.cursor_x and obj.y == self.cursor_y and 
                               obj.type in npc_types)]
            
            if existing_npcs and existing_npcs[0].type == self.selected_tile:
                # Same NPC type - remove it
                self.current_area.objects = [obj for obj in self.current_area.objects 
                                           if not (obj.x == self.cursor_x and obj.y == self.cursor_y and 
                                                  obj.type in npc_types)]
            else:
                # Different NPC or no NPC - remove existing NPC and place new
                self.current_area.objects = [obj for obj in self.current_area.objects 
                                           if not (obj.x == self.cursor_x and obj.y == self.cursor_y and 
                                                  obj.type in npc_types)]
                self.current_area.objects.append(GameObject(
                    type=self.selected_tile, x=self.cursor_x, y=self.cursor_y
                ))
                
        elif self.selected_mode == "trigger":
            # Check if there's already a trigger at this position
            existing_triggers = [trig for trig in self.current_area.triggers 
                               if trig.x == self.cursor_x and trig.y == self.cursor_y]
            
            if existing_triggers:
                # Same trigger - remove it
                self.current_area.triggers = [trig for trig in self.current_area.triggers 
                                            if not (trig.x == self.cursor_x and trig.y == self.cursor_y)]
            else:
                # No trigger - place new trigger
                new_trigger = Trigger(x=self.cursor_x, y=self.cursor_y)
                
                # If we have a specific trigger selected (from files), store that info
                if self.selected_tile != "trigger" and self.selected_tile in self.tile_manager.get_trigger_names():
                    # Store the trigger type in the actions for now
                    new_trigger.actions = [{"type": "python_script", "script": self.selected_tile}]
                
                self.current_area.triggers.append(new_trigger)
            
        self.draw_area()
        self.update_properties_display()
        
    def remove_tile(self):
        """Remove item at cursor position (mode-aware)"""
        if self.selected_mode == "tile":
            # Clear tile to empty
            self.current_area.tiles[self.cursor_y][self.cursor_x] = Tile(type="empty")
            
        elif self.selected_mode == "object":
            # Remove only objects (not NPCs) at this position
            npc_types = set(self.tile_manager.get_npc_names())
            if not npc_types:
                # Fallback to hardcoded NPC types if no files found
                npc_types = {"guard", "merchant", "villager", "wizard", "knight", "enemy", "boss"}
            
            self.current_area.objects = [obj for obj in self.current_area.objects 
                                       if not (obj.x == self.cursor_x and obj.y == self.cursor_y and 
                                              obj.type not in npc_types)]
                                              
        elif self.selected_mode == "npc":
            # Remove only NPCs at this position
            npc_types = set(self.tile_manager.get_npc_names())
            if not npc_types:
                # Fallback to hardcoded NPC types if no files found
                npc_types = {"guard", "merchant", "villager", "wizard", "knight", "enemy", "boss"}
            
            self.current_area.objects = [obj for obj in self.current_area.objects 
                                       if not (obj.x == self.cursor_x and obj.y == self.cursor_y and 
                                              obj.type in npc_types)]
                                              
        elif self.selected_mode == "trigger":
            # Remove triggers at this position
            self.current_area.triggers = [trig for trig in self.current_area.triggers 
                                        if not (trig.x == self.cursor_x and trig.y == self.cursor_y)]
            
        self.draw_area()
        self.update_properties_display()
        
    def on_canvas_click(self, event):
        """Handle canvas clicks"""
        # Set focus to canvas when clicked
        self.canvas.focus_set()
        
        # Convert canvas coordinates to grid coordinates
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        grid_x = int(canvas_x // self.tile_size)
        grid_y = int(canvas_y // self.tile_size)
        
        if (0 <= grid_x < self.current_area.width and 
            0 <= grid_y < self.current_area.height):
            self.cursor_x = grid_x
            self.cursor_y = grid_y
            self.update_cursor_display()
            self.update_properties_display()
            
    def draw_area(self):
        """Draw the current area on the canvas"""
        self.canvas.delete("all")
        
        # Draw grid and tiles
        for y in range(self.current_area.height):
            for x in range(self.current_area.width):
                x1, y1 = x * self.tile_size, y * self.tile_size
                
                # Get tile
                tile = self.current_area.tiles[y][x]
                tile_info = self.tile_manager.get_tile_info(tile.type)
                
                # Draw tile image
                if "image" in tile_info:
                    self.canvas.create_image(x1, y1, image=tile_info["image"], anchor=tk.NW)
                else:
                    # Fallback to colored rectangle
                    self.canvas.create_rectangle(x1, y1, x1 + self.tile_size, y1 + self.tile_size, 
                                               fill="lightgray", outline="black")
                
                # Draw grid lines
                self.canvas.create_rectangle(x1, y1, x1 + self.tile_size, y1 + self.tile_size, 
                                           outline="gray", width=1)
                
                # Show walkable indicator on tiles that are not walkable
                tile = self.current_area.tiles[y][x]
                effective_walkable = tile.is_walkable(self.tile_manager)
                
                # For doors, check state too
                if tile.get_tile_category() == "door":
                    if tile.door_state in ["locked", "closed"] and tile.walkable_override is None:
                        effective_walkable = False
                    elif tile.door_state == "open" and tile.walkable_override is None:
                        effective_walkable = True
                
                if not effective_walkable:
                    self.canvas.create_text(x1 + 16, y1 + 16, text="✗", fill="red", 
                                          font=("Arial", 12, "bold"))
                
        # Draw objects and NPCs
        for obj in self.current_area.objects:
            x1, y1 = obj.x * self.tile_size, obj.y * self.tile_size
            
            # Check if we have an image for this object/NPC
            npc_info = self.tile_manager.get_npc_info(obj.type)
            obj_info = self.tile_manager.get_object_info(obj.type)
            
            if "image" in npc_info:
                # Use NPC image
                self.canvas.create_image(x1, y1, image=npc_info["image"], anchor=tk.NW)
            elif "image" in obj_info:
                # Use object image
                self.canvas.create_image(x1, y1, image=obj_info["image"], anchor=tk.NW)
            else:
                # Fallback to colored shapes
                x2, y2 = x1 + self.tile_size, y1 + self.tile_size
                
                if obj.type in ["guard", "merchant", "villager", "wizard", "knight", "enemy", "boss"]:
                    # NPCs - circles with specific colors
                    npc_colors = {
                        "guard": "#4169E1", "merchant": "#FFD700", "villager": "#90EE90",
                        "wizard": "#9370DB", "knight": "#C0C0C0", "enemy": "#DC143C", "boss": "#8B0000"
                    }
                    color = npc_colors.get(obj.type, "#FFD700")
                    self.canvas.create_oval(x1 + 4, y1 + 4, x2 - 4, y2 - 4, fill=color, outline="black", width=2)
                    # Add a small "N" to indicate NPC
                    self.canvas.create_text(x1 + 16, y1 + 16, text="N", fill="white", font=("Arial", 8, "bold"))
                else:
                    # Objects - rectangles with specific colors
                    obj_colors = {
                        "item": "#32CD32", "lever": "#FF4500", "fountain": "#00CED1",
                        "chest": "#8B4513", "barrel": "#654321", "table": "#DEB887", "door_switch": "#FF6347"
                    }
                    color = obj_colors.get(obj.type, "#32CD32")
                    self.canvas.create_rectangle(x1 + 4, y1 + 4, x2 - 4, y2 - 4, fill=color, outline="black", width=2)
            
        # Draw triggers
        for trigger in self.current_area.triggers:
            x1, y1 = trigger.x * self.tile_size, trigger.y * self.tile_size
            x2, y2 = x1 + self.tile_size, y1 + self.tile_size
            
            # Draw trigger as diamond
            center_x, center_y = (x1 + x2) / 2, (y1 + y2) / 2
            self.canvas.create_polygon(
                center_x, y1 + 4,  # top
                x2 - 4, center_y,  # right
                center_x, y2 - 4,  # bottom
                x1 + 4, center_y,  # left
                fill="#FF6347", outline="black", width=2
            )
            
        # Update canvas scroll region
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
        self.update_cursor_display()
        
    def update_cursor_display(self):
        """Update the cursor display on the canvas"""
        self.canvas.delete("cursor")
        
        x1, y1 = self.cursor_x * self.tile_size, self.cursor_y * self.tile_size
        x2, y2 = x1 + self.tile_size, y1 + self.tile_size
        
        # Draw cursor as thick border
        self.canvas.create_rectangle(x1, y1, x2, y2, outline="red", width=3, tags="cursor")
        
        # Update cursor label
        self.cursor_label.config(text=f"Cursor: ({self.cursor_x}, {self.cursor_y})")
        
    def update_properties_display(self):
        """Update the properties panel"""
        # Enable text widget to clear and update it
        self.properties_text.configure(state='normal')
        
        # Clear properties text
        self.properties_text.delete(1.0, tk.END)
        
        # Get current tile/object/trigger info
        tile = self.current_area.tiles[self.cursor_y][self.cursor_x]
        objects_here = [obj for obj in self.current_area.objects 
                       if obj.x == self.cursor_x and obj.y == self.cursor_y]
        triggers_here = [trig for trig in self.current_area.triggers 
                        if trig.x == self.cursor_x and trig.y == self.cursor_y]
        
        info = f"Position: ({self.cursor_x}, {self.cursor_y})\n\n"
        
        # Tile info
        tile_info = self.tile_manager.get_tile_info(tile.type)
        global_walkable = self.tile_manager.get_default_walkable(tile.type)
        effective_walkable = tile.is_walkable(self.tile_manager)
        tile_category = tile.get_tile_category()
        
        info += f"Tile: {tile_info.get('display_name', tile.type)}\n"
        info += f"Type: {tile.type}\n"
        info += f"Category: {tile_category}\n"
        info += f"Global walkable: {global_walkable}\n"
        info += f"Effective walkable: {effective_walkable}\n"
        
        if tile.walkable_override is not None:
            info += f"Override: {tile.walkable_override}\n"
        else:
            info += "Override: None (using global)\n"
        
        # Door-specific info
        if tile_category == "door":
            info += f"Door state: {tile.door_state}\n"
            
            # Door walkability depends on state
            if tile.door_state == "locked" or tile.door_state == "closed":
                door_walkable = False
            else:  # open
                door_walkable = True
            
            if tile.walkable_override is None:
                effective_walkable = door_walkable
            
            info += f"Door walkable: {door_walkable}\n"
        
        info += "\n"
        
        # Update walkable controls
        self.global_walkable_label.config(text=f"Global default: {global_walkable}")
        
        if tile.walkable_override is None:
            self.walkable_override_var.set("default")
        elif tile.walkable_override:
            self.walkable_override_var.set("walkable")
        else:
            self.walkable_override_var.set("not_walkable")
        
        # Show/hide door controls based on tile category
        if tile_category == "door":
            self.door_frame.pack(fill=tk.X, padx=5, pady=5)
            self.door_state_var.set(tile.door_state)
        else:
            self.door_frame.pack_forget()
        
        # Object info
        if objects_here:
            for obj in objects_here:
                info += f"Object: {obj.type.title()}\n"
                if obj.properties:
                    info += f"Properties: {obj.properties}\n"
                info += "\n"
                
        # Trigger info
        if triggers_here:
            for trigger in triggers_here:
                info += f"Trigger: {len(trigger.actions)} actions\n"
                for i, action in enumerate(trigger.actions):
                    info += f"  Action {i+1}: {action}\n"
                info += "\n"
                
        self.properties_text.insert(1.0, info)
        
        # Re-disable the text widget after updating
        self.properties_text.configure(state='disabled')
        
    def on_walkable_override_change(self):
        """Handle walkable override change"""
        tile = self.current_area.tiles[self.cursor_y][self.cursor_x]
        
        override_value = self.walkable_override_var.get()
        if override_value == "default":
            tile.walkable_override = None
        elif override_value == "walkable":
            tile.walkable_override = True
        elif override_value == "not_walkable":
            tile.walkable_override = False
            
        self.update_properties_display()
        self.draw_area()  # Redraw to show visual changes
    
    def on_door_state_change(self):
        """Handle door state change"""
        tile = self.current_area.tiles[self.cursor_y][self.cursor_x]
        tile.door_state = self.door_state_var.get()
        self.update_properties_display()
        self.draw_area()  # Redraw to show visual changes
        
    def on_mode_change(self):
        """Handle mode change (tile/object/trigger)"""
        self.selected_mode = self.mode_var.get()
        self.update_tile_display()
        
    def on_area_name_change(self, event):
        """Handle area name change"""
        self.current_area.name = self.area_name_var.get()
        
    def reload_assets(self):
        """Reload all assets from directories"""
        self.tile_manager = TileManager()
        if self.tile_manager.get_tile_names():
            self.selected_tile = self.tile_manager.get_tile_names()[0]
        self.update_tile_display()
        self.draw_area()
        messagebox.showinfo("Reload", "All assets reloaded successfully!")
        
    def new_area(self):
        """Create a new area"""
        if messagebox.askyesno("New Area", "Create a new area? Unsaved changes will be lost."):
            self.current_area = Area()
            self.current_file = None
            self.cursor_x = 0
            self.cursor_y = 0
            self.area_name_var.set(self.current_area.name)
            self.draw_area()
            self.update_properties_display()
            
    def save_area(self):
        """Save the current area"""
        if self.current_file:
            self._save_to_file(self.current_file)
        else:
            self.save_area_as()
            
    def save_area_as(self):
        """Save the current area with a new filename"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            self._save_to_file(filename)
            self.current_file = filename
            
    def _save_to_file(self, filename):
        """Save area data to file"""
        try:
            # Convert area to dictionary
            area_dict = asdict(self.current_area)
            
            with open(filename, 'w') as f:
                json.dump(area_dict, f, indent=2)
                
            messagebox.showinfo("Save", f"Area saved to {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save area: {str(e)}")
            
    def open_area(self):
        """Open an existing area"""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'r') as f:
                    area_dict = json.load(f)
                    
                # Reconstruct area object
                self.current_area = Area(**area_dict)
                
                # Reconstruct tile objects
                for y, row in enumerate(self.current_area.tiles):
                    for x, tile_data in enumerate(row):
                        if isinstance(tile_data, dict):
                            self.current_area.tiles[y][x] = Tile(**tile_data)
                            
                # Reconstruct object objects
                self.current_area.objects = [GameObject(**obj_data) for obj_data in self.current_area.objects]
                
                # Reconstruct trigger objects
                self.current_area.triggers = [Trigger(**trig_data) for trig_data in self.current_area.triggers]
                
                self.current_file = filename
                self.cursor_x = 0
                self.cursor_y = 0
                self.area_name_var.set(self.current_area.name)
                self.draw_area()
                self.update_properties_display()
                
                messagebox.showinfo("Open", f"Area loaded from {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open area: {str(e)}")


def main():
    # Check if PIL is available
    try:
        from PIL import Image, ImageTk
    except ImportError:
        print("Error: PIL (Pillow) is required for image support.")
        print("Install it with: pip install Pillow")
        return
    
    root = tk.Tk()
    editor = TinkerEditor(root)
    root.mainloop()

if __name__ == "__main__":
    main()
