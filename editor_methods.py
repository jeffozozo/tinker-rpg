"""
Editor methods for the Tinker RPG Editor
This module contains all the interactive methods for the editor
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
from dataclasses import asdict

# Mixin class to add editor functionality
class EditorMethods:
    """Mixin class containing all editor interaction methods"""
    
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
                from data_classes import Tile
                self.current_area.tiles[self.cursor_y][self.cursor_x] = Tile(type="empty")
            else:
                from data_classes import Tile
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
                from data_classes import GameObject
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
                from data_classes import GameObject
                self.current_area.objects.append(GameObject(
                    type=self.selected_tile, x=self.cursor_x, y=self.cursor_y))
        
        elif self.selected_mode == "trigger":
            existing = [trig for trig in self.current_area.triggers 
                       if trig.x == self.cursor_x and trig.y == self.cursor_y]
            if existing:
                self.current_area.triggers = [trig for trig in self.current_area.triggers 
                                            if not (trig.x == self.cursor_x and trig.y == self.cursor_y)]
            else:
                from data_classes import Trigger
                self.current_area.triggers.append(Trigger(x=self.cursor_x, y=self.cursor_y))
        
        self.draw_area()
        self.update_properties_display()
    
    def remove_tile(self):
        if self.selected_mode == "tile":
            from data_classes import Tile
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
    
    def update_properties_display(self):
        self.properties_text.configure(state='normal')
        self.properties_text.delete(1.0, tk.END)
        
        tile = self.current_area.tiles[self.cursor_y][self.cursor_x]
        objects_here = [obj for obj in self.current_area.objects if obj.x == self.cursor_x and obj.y == self.cursor_y]
        triggers_here = [trig for trig in self.current_area.triggers if trig.x == self.cursor_x and trig.y == self.cursor_y]
        
        info = f"Position: ({self.cursor_x}, {self.cursor_y})\n\n"
        tile_info = self.tile_manager.get_tile_info(tile.type)
        global_walkable = self.tile_manager.get_default_walkable(tile.type)
        
        info += f"Tile: {tile_info.get('display_name', tile.type)}\n"
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