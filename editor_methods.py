"""
Updated editor_methods.py with enhanced trigger system
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
from dataclasses import asdict

class EditorMethods:
    """Mixin class containing all editor interaction methods"""
    
    def __init__(self):
        # Add trigger selection tracking
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
            elif key in ['1', '2', '3', '4', '5', '6']:
                self.select_trigger(int(key))
                return "break"
            elif key == 'return':  # Enter key
                self.edit_selected_trigger()
                return "break"
    
    def select_trigger(self, trigger_number):
        """Select a specific trigger at the current location"""
        triggers_here = [trig for trig in self.current_area.triggers 
                        if trig.x == self.cursor_x and trig.y == self.cursor_y]
        if triggers_here and 1 <= trigger_number <= len(triggers_here):
            self.selected_trigger_index = trigger_number - 1
            self.update_properties_display()
    
    def edit_selected_trigger(self):
        """Open edit dialog for the currently selected trigger"""
        triggers_here = [trig for trig in self.current_area.triggers 
                        if trig.x == self.cursor_x and trig.y == self.cursor_y]
        if triggers_here and 0 <= self.selected_trigger_index < len(triggers_here):
            trigger = triggers_here[self.selected_trigger_index]
            self.show_trigger_edit_dialog(trigger)
    
    def get_next_trigger_name(self):
        """Generate the next available trigger name (trigger_1, trigger_2, etc.)"""
        existing_names = [trig.name for trig in self.current_area.triggers]
        counter = 1
        while f"trigger_{counter}" in existing_names:
            counter += 1
        return f"trigger_{counter}"
    
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
            # Check if we can add more triggers (max 6)
            triggers_here = [trig for trig in self.current_area.triggers 
                           if trig.x == self.cursor_x and trig.y == self.cursor_y]
            if len(triggers_here) >= 6:
                messagebox.showwarning("Max Triggers", "Maximum 6 triggers allowed per location")
                return
            
            from data_classes import Trigger
            new_trigger = Trigger(
                x=self.cursor_x, 
                y=self.cursor_y,
                trigger_type=self.selected_tile,  # selected_tile now holds trigger type
                name=self.get_next_trigger_name()
            )
            self.current_area.triggers.append(new_trigger)
            self.selected_trigger_index = len(triggers_here)  # Select the new trigger
            
            # Open edit dialog immediately for new trigger
            self.show_trigger_edit_dialog(new_trigger)
        
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
            triggers_here = [trig for trig in self.current_area.triggers 
                           if trig.x == self.cursor_x and trig.y == self.cursor_y]
            if triggers_here and 0 <= self.selected_trigger_index < len(triggers_here):
                trigger_to_remove = triggers_here[self.selected_trigger_index]
                self.current_area.triggers.remove(trigger_to_remove)
                # Adjust selected index if needed
                remaining_triggers = [trig for trig in self.current_area.triggers 
                                    if trig.x == self.cursor_x and trig.y == self.cursor_y]
                if not remaining_triggers:
                    self.selected_trigger_index = 0
                elif self.selected_trigger_index >= len(remaining_triggers):
                    self.selected_trigger_index = len(remaining_triggers) - 1
        
        self.draw_area()
        self.update_properties_display()
    
    def move_cursor(self, direction):
        if direction == 'up' and self.cursor_y > 0:
            self.cursor_y -= 1
        elif direction == 'down' and self.cursor_y < self.current_area.height - 1:
            self.cursor_y += 1
        elif direction == 'left' and self.cursor_x > 0:
            self.cursor_x -= 1
        elif direction == 'right' and self.cursor_x < self.current_area.width - 1:
            self.cursor_x += 1
        
        # Reset trigger selection when moving to new location
        self.selected_trigger_index = 0
        self.update_cursor_display()
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
            self.selected_trigger_index = 0  # Reset trigger selection
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
                self.selected_tile = tag[8:]  # trigger type (e.g., "teleport")
                self.update_tile_display()
                break
    
    def on_mode_change(self):
        self.selected_mode = self.mode_var.get()
        # Set default selection for trigger mode
        if self.selected_mode == "trigger":
            self.selected_tile = "teleport"
        elif self.selected_mode == "tile" and self.tile_manager.get_tile_names():
            self.selected_tile = list(self.tile_manager.get_tile_names())[0]
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
        
        # Draw triggers with new color system
        trigger_locations = {}
        for trigger in self.current_area.triggers:
            key = (trigger.x, trigger.y)
            if key not in trigger_locations:
                trigger_locations[key] = []
            trigger_locations[key].append(trigger)
        
        for (x, y), triggers in trigger_locations.items():
            x1, y1 = x * self.tile_size, y * self.tile_size
            x2, y2 = x1 + self.tile_size, y1 + self.tile_size
            center_x, center_y = (x1 + x2) / 2, (y1 + y2) / 2
            
            if len(triggers) == 1:
                # Single trigger - use type color
                color = self.trigger_colors.get(triggers[0].trigger_type, "#CC0000")
                self.canvas.create_polygon(center_x, y1 + 4, x2 - 4, center_y, center_x, y2 - 4, x1 + 4, center_y,
                                         fill=color, outline="black", width=2)
            else:
                # Multiple triggers - dark gray with white number
                self.canvas.create_polygon(center_x, y1 + 4, x2 - 4, center_y, center_x, y2 - 4, x1 + 4, center_y,
                                         fill="#444444", outline="black", width=2)
                self.canvas.create_text(center_x, center_y, text=str(len(triggers)), 
                                      fill="white", font=("Arial", 10, "bold"))
        
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
            trigger_types = ["teleport", "inventory", "tile_update", "area_object", "game_end", "show_dialog", "custom"]
            trigger_names = {
                "teleport": "Teleport",
                "inventory": "Inventory",
                "tile_update": "Tile Update",
                "area_object": "Area Object", 
                "game_end": "Game End",
                "show_dialog": "Show Dialog",
                "custom": "Custom Script"
            }
            
            for i, trigger_type in enumerate(trigger_types):
                y = i * 40 + 10
                color = self.trigger_colors[trigger_type]
                
                # Draw colored diamond preview
                center_x, center_y = 25, y + 20
                self.tile_canvas.create_polygon(center_x, y + 5, 40, center_y, center_x, y + 35, 10, center_y, 
                                              fill=color, outline="black", tags=f"trigger_{trigger_type}")
                self.tile_canvas.create_text(50, y + 20, text=trigger_names[trigger_type], anchor=tk.W)
                
                if trigger_type == self.selected_tile:
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
            info += f"Triggers: ({len(triggers_here)})\n"
            for i, trigger in enumerate(triggers_here):
                selected_marker = "● " if i == self.selected_trigger_index else "  "
                info += f"{selected_marker}{i+1}. {trigger.name} ({trigger.get_description()})\n"
            info += f"\nPress {1 if len(triggers_here) == 1 else '1-' + str(len(triggers_here))} to select, Enter to edit\n"
        
        self.properties_text.insert(1.0, info)
        self.properties_text.configure(state='disabled')
    
    def show_trigger_edit_dialog(self, trigger):
        """Open the edit dialog for a specific trigger"""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Edit {trigger.trigger_type.title()} Trigger")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Name field (always first)
        name_frame = ttk.Frame(dialog)
        name_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(name_frame, text="Name:").pack(side=tk.LEFT)
        name_var = tk.StringVar(value=trigger.name)
        ttk.Entry(name_frame, textvariable=name_var, width=30).pack(side=tk.LEFT, padx=(5,0))
        
        # Parameters based on trigger type
        params_frame = ttk.LabelFrame(dialog, text="Parameters")
        params_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        param_vars = {}
        
        if trigger.trigger_type == "teleport":
            # Area dropdown
            ttk.Label(params_frame, text="Area:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
            area_var = tk.StringVar(value=trigger.parameters.get("area", ""))
            area_combo = ttk.Combobox(params_frame, textvariable=area_var, width=20)
            area_combo['values'] = [os.path.splitext(area)[0] for area in self.current_game.areas]
            area_combo.grid(row=0, column=1, padx=5, pady=2)
            param_vars['area'] = area_var
            
            # X coordinate
            ttk.Label(params_frame, text="X:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
            x_var = tk.StringVar(value=str(trigger.parameters.get("x", 0)))
            ttk.Entry(params_frame, textvariable=x_var, width=10).grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
            param_vars['x'] = x_var
            
            # Y coordinate
            ttk.Label(params_frame, text="Y:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
            y_var = tk.StringVar(value=str(trigger.parameters.get("y", 0)))
            ttk.Entry(params_frame, textvariable=y_var, width=10).grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
            param_vars['y'] = y_var
            
        elif trigger.trigger_type == "inventory":
            # Add item dropdown
            ttk.Label(params_frame, text="Add Item:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
            add_var = tk.StringVar(value=trigger.parameters.get("add", ""))
            add_combo = ttk.Combobox(params_frame, textvariable=add_var, width=20)
            add_combo['values'] = [""] + self.current_game.used_objects
            add_combo.grid(row=0, column=1, padx=5, pady=2)
            param_vars['add'] = add_var
            
            # Remove item dropdown
            ttk.Label(params_frame, text="Remove Item:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
            remove_var = tk.StringVar(value=trigger.parameters.get("remove", ""))
            remove_combo = ttk.Combobox(params_frame, textvariable=remove_var, width=20)
            remove_combo['values'] = [""] + self.current_game.used_objects
            remove_combo.grid(row=1, column=1, padx=5, pady=2)
            param_vars['remove'] = remove_var
            
        elif trigger.trigger_type == "tile_update":
            # X coordinate
            ttk.Label(params_frame, text="X:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
            x_var = tk.StringVar(value=str(trigger.parameters.get("x", 0)))
            ttk.Entry(params_frame, textvariable=x_var, width=10).grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
            param_vars['x'] = x_var
            
            # Y coordinate
            ttk.Label(params_frame, text="Y:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
            y_var = tk.StringVar(value=str(trigger.parameters.get("y", 0)))
            ttk.Entry(params_frame, textvariable=y_var, width=10).grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
            param_vars['y'] = y_var
            
            # Tile type dropdown
            ttk.Label(params_frame, text="Tile:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
            tile_var = tk.StringVar(value=trigger.parameters.get("tile", ""))
            tile_combo = ttk.Combobox(params_frame, textvariable=tile_var, width=20)
            tile_combo['values'] = self.current_game.used_tiles
            tile_combo.grid(row=2, column=1, padx=5, pady=2)
            param_vars['tile'] = tile_var
            
            # Walkable checkbox
            walkable_var = tk.BooleanVar(value=trigger.parameters.get("walkable", True))
            ttk.Checkbutton(params_frame, text="Walkable", variable=walkable_var).grid(row=3, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
            param_vars['walkable'] = walkable_var
            
        elif trigger.trigger_type == "area_object":
            # Area dropdown
            ttk.Label(params_frame, text="Area:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
            area_var = tk.StringVar(value=trigger.parameters.get("area", ""))
            area_combo = ttk.Combobox(params_frame, textvariable=area_var, width=20)
            area_combo['values'] = [os.path.splitext(area)[0] for area in self.current_game.areas]
            area_combo.grid(row=0, column=1, padx=5, pady=2)
            param_vars['area'] = area_var
            
            # Object dropdown
            ttk.Label(params_frame, text="Object:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
            object_var = tk.StringVar(value=trigger.parameters.get("object", ""))
            object_combo = ttk.Combobox(params_frame, textvariable=object_var, width=20)
            object_combo['values'] = self.current_game.used_objects
            object_combo.grid(row=1, column=1, padx=5, pady=2)
            param_vars['object'] = object_var
            
        elif trigger.trigger_type == "game_end":
            # Win/Lose dropdown
            ttk.Label(params_frame, text="Result:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
            result_var = tk.StringVar(value=trigger.parameters.get("win_lose", "win"))
            result_combo = ttk.Combobox(params_frame, textvariable=result_var, width=20)
            result_combo['values'] = ["win", "lose"]
            result_combo.grid(row=0, column=1, padx=5, pady=2)
            param_vars['win_lose'] = result_var
            
            # Message text
            ttk.Label(params_frame, text="Message:").grid(row=1, column=0, sticky=tk.NW, padx=5, pady=2)
            message_text = tk.Text(params_frame, width=40, height=5)
            message_text.grid(row=1, column=1, padx=5, pady=2)
            message_text.insert(1.0, trigger.parameters.get("message", ""))
            param_vars['message'] = message_text
            
        elif trigger.trigger_type == "show_dialog":
            # Message text
            ttk.Label(params_frame, text="Message:").grid(row=0, column=0, sticky=tk.NW, padx=5, pady=2)
            message_text = tk.Text(params_frame, width=40, height=8)
            message_text.grid(row=0, column=1, padx=5, pady=2)
            message_text.insert(1.0, trigger.parameters.get("message", ""))
            param_vars['message'] = message_text
            
        elif trigger.trigger_type == "custom":
            # Code text with helper comments
            ttk.Label(params_frame, text="Python Code:").grid(row=0, column=0, sticky=tk.NW, padx=5, pady=2)
            code_text = tk.Text(params_frame, width=50, height=15, font=("Consolas", 10))
            code_text.grid(row=0, column=1, padx=5, pady=2)
            
            default_code = '''# Available game variables:
# game.player_x, game.player_y - Player position
# game.player_inventory - List of items player has
# game.current_area - Current area name
# game.set_area(area_name, x, y) - Teleport to area
# game.add_item(item_name) - Add item to inventory
# game.remove_item(item_name) - Remove item from inventory
# game.show_dialog(message) - Show dialog to player
# game.end_game(win=True, message="") - End the game

# Your code here:
'''
            code_text.insert(1.0, trigger.parameters.get("code", default_code))
            param_vars['code'] = code_text
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def save_trigger():
            # Update trigger name
            trigger.name = name_var.get()
            
            # Update parameters based on type
            for param_name, param_var in param_vars.items():
                if isinstance(param_var, tk.Text):
                    trigger.parameters[param_name] = param_var.get(1.0, tk.END).strip()
                elif isinstance(param_var, tk.BooleanVar):
                    trigger.parameters[param_name] = param_var.get()
                else:
                    value = param_var.get()
                    # Convert coordinates to integers
                    if param_name in ['x', 'y']:
                        try:
                            trigger.parameters[param_name] = int(value)
                        except ValueError:
                            trigger.parameters[param_name] = 0
                    else:
                        trigger.parameters[param_name] = value
            
            dialog.destroy()
            self.update_properties_display()
            self.draw_area()
        
        ttk.Button(button_frame, text="Save", command=save_trigger).pack(side=tk.RIGHT, padx=(5,0))
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT)