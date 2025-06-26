"""
Tile and Asset Manager for the Tinker RPG Editor
"""

import os
import glob
from PIL import Image, ImageTk

class TileManager:
    """Manages loading tiles from PNG files and their properties"""
    
    def __init__(self):
        self.tiles = {}
        self.npcs = {}
        self.objects = {}
        self.triggers = {}
        self.loaded_assets = self.load_all_assets()
    
    def load_all_assets(self):
        loaded_assets = []
        
        if self.load_tiles():
            loaded_assets.append("tiles")
        if self.load_npcs():
            loaded_assets.append("npcs")
        if self.load_objects():
            loaded_assets.append("objects")
        if self.load_triggers():
            loaded_assets.append("triggers")
        
        return loaded_assets
    
    def load_tiles(self):
        tiles_dir = "tiles"
        if not os.path.exists(tiles_dir):
            os.makedirs(tiles_dir)
            self._create_default_tile()
            return False
        
        png_files = glob.glob(os.path.join(tiles_dir, "*.png"))
        if not png_files:
            self._create_default_tile()
            return False
        
        loaded_any = False
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
                loaded_any = True
            except Exception as e:
                print(f"Error loading {png_file}: {e}")
        
        if not loaded_any:
            self._create_default_tile()
            return False
        
        return True
    
    def load_npcs(self):
        npcs_dir = "npcs"
        if not os.path.exists(npcs_dir):
            os.makedirs(npcs_dir)
            return False
        
        png_files = glob.glob(os.path.join(npcs_dir, "*.png"))
        loaded_any = False
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
                loaded_any = True
            except Exception as e:
                print(f"Error loading NPC {png_file}: {e}")
        
        return loaded_any
    
    def load_objects(self):
        objects_dir = "objects"
        if not os.path.exists(objects_dir):
            os.makedirs(objects_dir)
            return False
        
        png_files = glob.glob(os.path.join(objects_dir, "*.png"))
        loaded_any = False
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
                loaded_any = True
            except Exception as e:
                print(f"Error loading object {png_file}: {e}")
        
        return loaded_any
    
    def load_triggers(self):
        triggers_dir = "triggers"
        if not os.path.exists(triggers_dir):
            os.makedirs(triggers_dir)
            return False
        
        py_files = glob.glob(os.path.join(triggers_dir, "*.py"))
        loaded_any = False
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
                loaded_any = True
            except Exception as e:
                print(f"Error loading trigger {py_file}: {e}")
        
        return loaded_any
    
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