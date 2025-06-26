"""
Data classes for the Tinker RPG Editor
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