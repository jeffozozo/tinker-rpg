"""
Updated data_classes.py with enhanced trigger system
"""

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any

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
    trigger_type: str = "teleport"  # teleport, inventory, tile_update, area_object, game_end, show_dialog, custom
    name: str = ""  # User-entered name
    parameters: Dict[str, Any] = None  # Type-specific parameters
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}
        if not self.name:
            # Set default name - will be updated to trigger_1, trigger_2, etc.
            self.name = "trigger_1"
    
    def get_description(self):
        """Get a brief description of what this trigger does"""
        if self.trigger_type == "teleport":
            area = self.parameters.get("area", "")
            x = self.parameters.get("x", 0)
            y = self.parameters.get("y", 0)
            return f"Teleport to {area} ({x},{y})"
        elif self.trigger_type == "inventory":
            add_item = self.parameters.get("add", "")
            remove_item = self.parameters.get("remove", "")
            parts = []
            if add_item:
                parts.append(f"Add: {add_item}")
            if remove_item:
                parts.append(f"Remove: {remove_item}")
            return ", ".join(parts) if parts else "Inventory change"
        elif self.trigger_type == "tile_update":
            tile = self.parameters.get("tile", "")
            x = self.parameters.get("x", 0)
            y = self.parameters.get("y", 0)
            return f"Change tile at ({x},{y}) to {tile}"
        elif self.trigger_type == "area_object":
            area = self.parameters.get("area", "")
            obj = self.parameters.get("object", "")
            return f"Add {obj} to {area}"
        elif self.trigger_type == "game_end":
            result = self.parameters.get("win_lose", "win")
            return f"Game {result}"
        elif self.trigger_type == "show_dialog":
            message = self.parameters.get("message", "")[:30]
            return f"Dialog: \"{message}...\""
        elif self.trigger_type == "custom":
            return "Custom script"
        return "Unknown trigger"

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

@dataclass
class Game:
    """Represents a complete game project"""
    name: str = "Untitled Game"
    areas: List[str] = None  # List of area filenames
    used_tiles: List[str] = None  # Tiles used in this game
    used_npcs: List[str] = None  # NPCs used in this game
    used_objects: List[str] = None  # Objects used in this game
    used_triggers: List[str] = None  # Triggers used in this game
    properties: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.areas is None:
            self.areas = []
        if self.used_tiles is None:
            self.used_tiles = []
        if self.used_npcs is None:
            self.used_npcs = []
        if self.used_objects is None:
            self.used_objects = []
        if self.used_triggers is None:
            self.used_triggers = []
        if self.properties is None:
            self.properties = {}