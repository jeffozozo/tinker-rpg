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
            "show_message": "#00CCCC",   # Cyan
            "custom": "#CC0000"         # Red
        }
    
    def on_key_press(self, event):
        key = event.keysym.lower()
        if getattr(self, "_trigger_position_picker", None) is not None:
            if key == "escape":
                self._trigger_position_picker = None
                self.update_cursor_display()
            return "break"
        if self.root.focus_get() == self.canvas:
            if self.selected_mode in ("messages", "editor_help"):
                return "break"
            if key in ['up', 'down', 'left', 'right']:
                self.move_cursor(key)
                return "break"
            elif key == 'space':
                self.place_tile()
                return "break"
            elif key == 'delete' or key == 'backspace':
                self.remove_tile()
                return "break"
            elif key in ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0']:
                self.select_trigger(10 if key == "0" else int(key))
                return "break"
            elif key == 'return':  # Enter key
                self.edit_selected_trigger()
                return "break"
    
    def select_trigger(self, trigger_number):
        """Select a specific trigger at the current location"""
        triggers_here = [trig for trig in self.current_area.triggers 
                        if trig.x == self.cursor_x and trig.y == self.cursor_y]
        if triggers_here and 1 <= trigger_number <= len(triggers_here):
            self.select_trigger_index(trigger_number - 1)

    def select_trigger_index(self, index):
        triggers_here = self._triggers_at_cursor()
        if not triggers_here or not 0 <= index < len(triggers_here):
            return False
        if index == self.selected_trigger_index:
            return True
        if not self.save_selected_trigger(show_error=True, refresh=False):
            return False
        self.selected_trigger_index = index
        self.refresh_trigger_editor()
        self.update_properties_display()
        self.draw_area()
        return True

    def edit_selected_trigger(self):
        """Focus the selected trigger editor in the properties panel."""
        self.refresh_trigger_editor()
    
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
            triggers_here = [trig for trig in self.current_area.triggers 
                           if trig.x == self.cursor_x and trig.y == self.cursor_y]
            if self.selected_mode == "trigger" and not self.save_selected_trigger(
                show_error=True, refresh=False
            ):
                return
            if len(triggers_here) >= 10:
                messagebox.showwarning("Max Triggers", "Maximum 10 triggers allowed per location")
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
            self.refresh_trigger_editor()
        self.draw_area()
        self.update_properties_display()

    def fill_empty_tiles(self):
        if self.selected_mode != "tile":
            messagebox.showwarning(
                "Fill Empty Tiles", "Select Tiles mode before filling the area."
            )
            return 0

        from data_classes import Tile
        filled_count = 0
        for row in self.current_area.tiles:
            for x, tile in enumerate(row):
                if tile.type == "empty":
                    row[x] = Tile(type=self.selected_tile)
                    filled_count += 1

        if filled_count:
            self.draw_area()
            self.update_properties_display()
        return filled_count
    
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
            self.delete_selected_trigger(confirm=False)
        
        self.draw_area()
        self.update_properties_display()
    
    def move_cursor(self, direction):
        if self.selected_mode == "trigger" and not self.save_selected_trigger(
            show_error=True, refresh=False
        ):
            return
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
        self.refresh_trigger_editor()
        self.update_properties_display()
    
    def on_canvas_click(self, event):
        position_picker = getattr(self, "_trigger_position_picker", None)
        if position_picker is not None:
            canvas_x = self.canvas.canvasx(event.x)
            canvas_y = self.canvas.canvasy(event.y)
            grid_x = int(canvas_x // self.tile_size)
            grid_y = int(canvas_y // self.tile_size)
            if (0 <= grid_x < self.current_area.width and
                    0 <= grid_y < self.current_area.height):
                position_picker["x_var"].set(str(grid_x))
                position_picker["y_var"].set(str(grid_y))
                self._trigger_position_picker = None
                self.update_cursor_display()
            self.canvas.focus_set()
            return "break"

        if self.selected_mode in ("messages", "editor_help"):
            return

        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        grid_x = int(canvas_x // self.tile_size)
        grid_y = int(canvas_y // self.tile_size)

        trigger_variables = getattr(self, "_trigger_editor_vars", {})
        if (
            self.selected_mode == "trigger"
            and getattr(self, "_trigger_editor_trigger", None) is not None
            and getattr(self, "_trigger_editor_draft_type", None) == "tile_update"
            and "x" in trigger_variables
            and "y" in trigger_variables
        ):
            if (
                0 <= grid_x < self.current_area.width
                and 0 <= grid_y < self.current_area.height
            ):
                trigger_variables["x"].set(str(grid_x))
                trigger_variables["y"].set(str(grid_y))
                self.mouse_position_label.config(
                    text=f"Mouse: ({grid_x}, {grid_y})"
                )
            else:
                self.mouse_position_label.config(text="Mouse: --")
            self.canvas.focus_set()
            return "break"

        if self.selected_mode == "trigger" and not self.save_selected_trigger(
            show_error=True, refresh=False
        ):
            return "break"
        self.canvas.focus_set()
        
        if (0 <= grid_x < self.current_area.width and 0 <= grid_y < self.current_area.height):
            self.cursor_x = grid_x
            self.cursor_y = grid_y
            self.selected_trigger_index = 0  # Reset trigger selection
            self.update_cursor_display()
            self.refresh_trigger_editor()
            self.update_properties_display()

    def on_canvas_right_click(self, event):
        if (getattr(self, "_trigger_position_picker", None) is not None or
                self.selected_mode in ("messages", "editor_help")):
            return "break"

        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        grid_x = int(canvas_x // self.tile_size)
        grid_y = int(canvas_y // self.tile_size)
        if not (0 <= grid_x < self.current_area.width and
                0 <= grid_y < self.current_area.height):
            return "break"

        if self.selected_mode == "trigger" and not self.save_selected_trigger(
            show_error=True, refresh=False
        ):
            return "break"
        self.canvas.focus_set()
        self.cursor_x = grid_x
        self.cursor_y = grid_y
        self.selected_trigger_index = 0
        self.update_cursor_display()
        self.refresh_trigger_editor()
        self.update_properties_display()
        self.place_tile()
        return "break"

    def on_canvas_motion(self, event):
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        grid_x = int(canvas_x // self.tile_size)
        grid_y = int(canvas_y // self.tile_size)
        if (0 <= grid_x < self.current_area.width and
                0 <= grid_y < self.current_area.height):
            self.mouse_position_label.config(text=f"Mouse: ({grid_x}, {grid_y})")
        else:
            self.mouse_position_label.config(text="Mouse: --")

    def on_canvas_leave(self, _event=None):
        self.mouse_position_label.config(text="Mouse: --")

    def on_tile_canvas_click(self, event):
        clicked = self.tile_canvas.find_closest(event.x, event.y)[0]
        tags = self.tile_canvas.gettags(clicked)
        for tag in tags:
            if tag.startswith("message_"):
                self.edit_game_message(tag[8:])
                break
            if tag.startswith("tile_"):
                self.selected_tile = tag[5:]
                self.update_tile_display()
                break
            elif tag.startswith("obj_"):
                self.selected_tile = tag[4:]
                self.update_tile_display()
                self.load_object_definition_editor()
                self.update_properties_display()
                break
            elif tag.startswith("npc_"):
                self.selected_tile = tag[4:]
                self.update_tile_display()
                break
            elif tag.startswith("trigger_"):
                self.selected_tile = tag[8:]  # trigger type (e.g., "teleport")
                self.update_tile_display()
                self.update_properties_display()
                break
    
    def on_mode_change(self):
        previous_mode = getattr(self, "selected_mode", None)
        if previous_mode == "trigger" and not self.save_selected_trigger(
            show_error=True, refresh=False
        ):
            self.mode_var.set(previous_mode)
            return

        self.selected_mode = self.mode_var.get()
        if self.selected_mode == "trigger":
            self.selected_tile = "teleport"
        elif self.selected_mode == "tile" and self.tile_manager.get_tile_names():
            self.selected_tile = list(self.tile_manager.get_tile_names())[0]
        elif self.selected_mode == "object":
            self.selected_tile = (self.tile_manager.get_object_names() or
                                  ["item", "lever", "fountain", "chest", "barrel"])[0]
        elif self.selected_mode == "npc":
            self.selected_tile = (self.tile_manager.get_npc_names() or
                                  ["guard", "merchant", "villager", "wizard", "knight"])[0]
        if hasattr(self, "trigger_editor_frame"):
            if self.selected_mode == "trigger":
                self.tile_walkable_frame.pack_forget()
                self.object_definition_frame.pack_forget()
                self.details_label.pack_forget()
                self.properties_text.pack_forget()
                self.trigger_editor_frame.pack(
                    fill=tk.BOTH, expand=True, padx=5, pady=5
                )
            else:
                self.trigger_editor_frame.pack_forget()
                self.details_label.pack(padx=5, pady=(10, 0))
                self.properties_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        if hasattr(self, "object_definition_frame"):
            if self.selected_mode == "object":
                self.tile_walkable_frame.pack_forget()
                self.object_definition_frame.pack(
                    before=self.details_label, fill=tk.X, padx=5, pady=5
                )
                self.load_object_definition_editor()
            elif self.selected_mode == "trigger" and not hasattr(
                self, "trigger_editor_frame"
            ):
                self.object_definition_frame.pack_forget()
                self.tile_walkable_frame.pack_forget()
            elif self.selected_mode != "trigger":
                self.object_definition_frame.pack_forget()
                self.tile_walkable_frame.pack(
                    before=self.details_label, fill=tk.X, padx=5, pady=5
                )
        self.update_tile_display()
        if hasattr(self, "trigger_listbox"):
            self.refresh_trigger_editor()
        self.update_properties_display()

    def load_object_definition_editor(self):
        if self.selected_mode != "object":
            return
        definition = self.current_game.get_object_definition(self.selected_tile)
        self.object_gettable_var.set(definition["gettable"])
        self.object_walkable_var.set(definition["walkable"])
        self.object_effect_mode_var.set(definition["effect_mode"])
        for stat, value_var in self.object_effect_vars.items():
            value_var.set(str(definition["effects"].get(stat, 0)))
        self.on_object_gettable_change()

    def on_object_gettable_change(self):
        if self.object_gettable_var.get():
            self.object_effects_frame.pack(fill=tk.X, padx=5, pady=3)
        else:
            self.object_effects_frame.pack_forget()

    def save_object_definition_changes(self):
        object_type = self.selected_tile
        if self.selected_mode != "object":
            return

        if self.object_gettable_var.get():
            try:
                effects = {
                    stat: int(value_var.get())
                    for stat, value_var in self.object_effect_vars.items()
                }
            except ValueError:
                messagebox.showerror("Invalid Effect", "Stat effects must be whole numbers.")
                return
        else:
            effects = {stat: 0 for stat in self.object_effect_vars}

        self.current_game.object_definitions[object_type] = {
            "gettable": self.object_gettable_var.get(),
            "walkable": self.object_walkable_var.get(),
            "effect_mode": self.object_effect_mode_var.get(),
            "effects": effects,
        }
        self.draw_area()
        self.update_properties_display()

    def get_trigger_type_description(self, trigger_type):
        descriptions = {
            "teleport": "Moves the player to another area.",
            "inventory": "Adds or removes an item from the player's inventory.",
            "tile_update": "Changes a tile in the current area.",
            "area_object": "Adds an object to an area.",
            "game_end": "Ends the game with a win or loss.",
            "show_message": "Displays a message to the player.",
            "custom": "Runs a custom script.",
        }
        return descriptions.get(trigger_type, "Unknown trigger type.")

    def edit_game_message(self, message_type):
        message_fields = {
            "intro": ("Intro Message", "intro_message"),
            "instructions": ("Help / Instructions Message", "instructions_message"),
            "game_end": ("Game End Message", "game_end_message"),
        }
        if message_type not in message_fields:
            return

        title, field_name = message_fields[message_type]
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.geometry("500x350")
        dialog.transient(self.root)

        button_frame = ttk.Frame(dialog)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 10))
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT)

        message_text = tk.Text(dialog, wrap=tk.WORD)
        message_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        message_text.insert("1.0", getattr(self.current_game, field_name))

        def save_message():
            setattr(self.current_game, field_name, message_text.get("1.0", tk.END).rstrip("\n"))
            dialog.destroy()

        ttk.Button(button_frame, text="Save", command=save_message).pack(side=tk.RIGHT, padx=(5, 0))
    
    def on_area_name_change(self, event):
        self.current_area.name = self.area_name_var.get()

    def on_game_name_change(self, *_args):
        self.current_game.name = self.game_name_var.get()
    
    def on_walkable_change(self):
        if self.selected_mode in ("messages", "editor_help"):
            return

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
        
        npc_names = set(self.tile_manager.get_npc_names())
        for obj in self.current_area.objects:
            if obj.x == x and obj.y == y:
                if obj.type in npc_names:
                    if obj.properties.get("walkable", False) is False:
                        return True
                else:
                    walkable = self.current_game.get_object_definition(obj.type)["walkable"]
                    if obj.properties.get("walkable", walkable) is False:
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
            
            top_trigger = triggers[0]
            if (x, y) == (self.cursor_x, self.cursor_y) and \
                    0 <= self.selected_trigger_index < len(triggers):
                top_trigger = triggers[self.selected_trigger_index]
            color = self.trigger_colors.get(top_trigger.trigger_type, "#CC0000")
            self.canvas.create_polygon(center_x, y1 + 4, x2 - 4, center_y, center_x, y2 - 4, x1 + 4, center_y,
                                     fill=color, outline="black", width=2)
            if len(triggers) > 1:
                marker_number = len(triggers)
                if (x, y) == (self.cursor_x, self.cursor_y):
                    marker_number = self.selected_trigger_index + 1
                number_color = (
                    "black"
                    if top_trigger.trigger_type in ("tile_update", "show_message")
                    else "white"
                )
                self.canvas.create_text(center_x, center_y, text=str(marker_number),
                                      fill=number_color, font=("Arial", 10, "bold"))
        
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
            trigger_types = ["teleport", "inventory", "tile_update", "area_object", "game_end", "show_message", "custom"]
            trigger_names = {
                "teleport": "Teleport",
                "inventory": "Inventory",
                "tile_update": "Tile Update",
                "area_object": "Area Object", 
                "game_end": "Game End",
                "show_message": "Show Message",
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

        elif self.selected_mode == "messages":
            message_entries = [
                ("intro", "Intro Message"),
                ("instructions", "Help / Instructions Message"),
                ("game_end", "Game End Message"),
            ]
            for i, (message_type, label) in enumerate(message_entries):
                y = i * 55 + 15
                self.tile_canvas.create_text(
                    10,
                    y,
                    text=label,
                    anchor=tk.NW,
                    width=190,
                    tags=f"message_{message_type}",
                )
                self.tile_canvas.create_text(
                    10,
                    y + 22,
                    text="Click to edit",
                    anchor=tk.NW,
                    fill="gray",
                    tags=f"message_{message_type}",
                )

        elif self.selected_mode == "editor_help":
            help_text = (
                "EDITOR HELP\n\n"
                "Tiles, Objects, and NPCs:\n"
                "Choose an item, then use Space or right-click to place it at the cursor/map cell.\n\n"
                "Triggers:\n"
                "Choose a trigger and use Space or right-click to add it at a map cell. "
                "Select stacked triggers "
                "in the right panel (or use 1-9 and 0 for the first ten). "
                "Edit fields in the right panel; Save commits them, and Delete "
                "removes the selected trigger.\n\n"
                "Map navigation (in editing modes):\n"
                "Click a map cell or use the arrow keys to move the cursor. "
                "Messages and Editor Help modes pause map editing.\n\n"
                "Area tools:\n"
                "Use the Area and Tools menus to save, resize, crop, and manage assets."
            )
            self.tile_canvas.create_text(
                10,
                10,
                text=help_text,
                anchor=tk.NW,
                width=190,
                tags="editor_help",
            )
        
        self.tile_canvas.configure(scrollregion=self.tile_canvas.bbox("all"))
        if hasattr(self, 'selected_tile_label'):
            if self.selected_mode == "messages":
                self.selected_tile_label.config(text="Choose a message to edit")
            elif self.selected_mode == "editor_help":
                self.selected_tile_label.config(text="Editor help")
            else:
                self.selected_tile_label.config(text=f"Selected: {self.selected_tile}")
    
    def update_properties_display(self):
        self.properties_text.configure(state='normal')
        self.properties_text.delete(1.0, tk.END)
        
        tile = self.current_area.tiles[self.cursor_y][self.cursor_x]
        objects_here = [obj for obj in self.current_area.objects if obj.x == self.cursor_x and obj.y == self.cursor_y]
        triggers_here = [trig for trig in self.current_area.triggers if trig.x == self.cursor_x and trig.y == self.cursor_y]
        
        info = ""
        if triggers_here and 0 <= self.selected_trigger_index < len(triggers_here):
            selected_trigger = triggers_here[self.selected_trigger_index]
            info += f"Selected trigger: {selected_trigger.get_description()}\n\n"
        elif self.selected_mode == "trigger":
            info += (
                f"Trigger type: {self.get_trigger_type_description(self.selected_tile)}\n\n"
            )
        elif self.selected_mode == "object":
            definition = self.current_game.get_object_definition(self.selected_tile)
            info += f"Object definition: {self.selected_tile}\n"
            info += f"Gettable: {definition['gettable']}\n"
            info += f"Walkable: {definition['walkable']}\n"
            if definition["gettable"]:
                info += f"Effect mode: {definition['effect_mode']}\n"
                info += f"Effects: {self._format_object_effects(definition['effects'])}\n\n"
            else:
                info += "Inventory effects: none (object is not gettable)\n\n"

        info += f"Position: ({self.cursor_x}, {self.cursor_y})\n\n"
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
                if obj.type not in set(self.tile_manager.get_npc_names()):
                    definition = self.current_game.get_object_definition(obj.type)
                    info += f"  Gettable: {definition['gettable']}, Walkable: {definition['walkable']}\n"
                    if definition["gettable"]:
                        info += (
                            f"  Effect mode: {definition['effect_mode']}, "
                            f"Effects: {self._format_object_effects(definition['effects'])}\n"
                        )
        
        if triggers_here:
            info += f"Triggers: ({len(triggers_here)})\n"
            for i, trigger in enumerate(triggers_here):
                selected_marker = "● " if i == self.selected_trigger_index else "  "
                info += f"{selected_marker}{i+1}. {trigger.name} ({trigger.get_description()})\n"
            info += "\nSelect a trigger in the right panel or use number keys 1-9, 0\n"
        
        self.properties_text.insert(1.0, info)
        self.properties_text.configure(state='disabled')

    @staticmethod
    def _format_object_effects(effects):
        active_effects = [
            f"{stat} {value:+d}"
            for stat, value in effects.items()
            if value
        ]
        return ", ".join(active_effects) if active_effects else "none"

    def _triggers_at_cursor(self):
        return [
            trigger for trigger in self.current_area.triggers
            if trigger.x == self.cursor_x and trigger.y == self.cursor_y
        ]

    def add_trigger_at_cursor(self):
        if self.selected_mode != "trigger":
            self.mode_var.set("trigger")
            self.on_mode_change()
        self.place_tile()

    def cycle_selected_trigger(self, direction):
        triggers_here = self._triggers_at_cursor()
        if triggers_here:
            next_index = (self.selected_trigger_index + direction) % len(triggers_here)
            self.select_trigger_index(next_index)

    def on_trigger_list_select(self, _event=None):
        if getattr(self, "_refreshing_trigger_list", False):
            return
        selection = self.trigger_listbox.curselection()
        if selection and not self.select_trigger_index(selection[0]):
            self.trigger_listbox.selection_clear(0, tk.END)
            self.trigger_listbox.selection_set(self.selected_trigger_index)

    def refresh_trigger_editor(self):
        if not hasattr(self, "trigger_listbox"):
            return

        triggers_here = self._triggers_at_cursor()
        self.selected_trigger_index = min(
            self.selected_trigger_index, max(0, len(triggers_here) - 1)
        )
        self._refreshing_trigger_list = True
        self.trigger_listbox.delete(0, tk.END)
        for index, trigger in enumerate(triggers_here):
            label = f"{index + 1}. {trigger.name} - {trigger.trigger_type.replace('_', ' ').title()}"
            self.trigger_listbox.insert(tk.END, label)
            self.trigger_listbox.itemconfig(
                index,
                foreground=self.trigger_colors.get(trigger.trigger_type, "#CC0000"),
            )
        if triggers_here:
            self.trigger_listbox.selection_set(self.selected_trigger_index)
            self.trigger_listbox.activate(self.selected_trigger_index)
            self.trigger_listbox.see(self.selected_trigger_index)
        self._refreshing_trigger_list = False

        for child in self.trigger_form_frame.winfo_children():
            child.destroy()
        self._trigger_editor_vars = {}
        self._trigger_editor_tile_labels = {}
        if triggers_here:
            self._build_trigger_editor(triggers_here[self.selected_trigger_index])
        else:
            ttk.Label(
                self.trigger_form_frame,
                text="Select a trigger tool, then click the map or Add.",
                wraplength=245,
            ).pack(anchor=tk.W, pady=5)

    def _change_trigger_editor_type(self, trigger, trigger_type, name):
        if trigger_type == getattr(self, "_trigger_editor_draft_type", trigger.trigger_type):
            return
        for child in self.trigger_form_frame.winfo_children():
            child.destroy()
        self._trigger_editor_vars = {}
        self._trigger_editor_tile_labels = {}
        self._build_trigger_editor(
            trigger, trigger_type=trigger_type, parameters={}, name=name
        )

    def _build_trigger_editor(self, trigger, trigger_type=None, parameters=None, name=None):
        form = self.trigger_form_frame
        self._trigger_editor_trigger = trigger
        trigger_type = trigger_type or trigger.trigger_type
        self._trigger_editor_draft_type = trigger_type
        params = trigger.parameters if parameters is None else parameters
        trigger_types = (
            "teleport",
            "inventory",
            "tile_update",
            "area_object",
            "game_end",
            "show_message",
            "custom",
        )
        self._trigger_editor_type_labels = {
            trigger_type.replace("_", " ").title(): trigger_type
            for trigger_type in trigger_types
        }
        trigger_type_var = tk.StringVar(
            value=trigger_type.replace("_", " ").title()
        )
        self._trigger_editor_vars["trigger_type"] = trigger_type_var
        type_row = ttk.Frame(form)
        type_row.pack(fill=tk.X, pady=2)
        ttk.Label(type_row, text="Type:", width=10).pack(side=tk.LEFT)
        type_combo = ttk.Combobox(
            type_row,
            textvariable=trigger_type_var,
            values=tuple(self._trigger_editor_type_labels),
            state="readonly",
        )
        type_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        type_combo.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._change_trigger_editor_type(
                trigger, trigger_type_var.get(), name_var.get()
            ),
        )

        name_var = tk.StringVar(value=trigger.name if name is None else name)
        self._trigger_editor_vars["name"] = name_var
        name_row = ttk.Frame(form)
        name_row.pack(fill=tk.X, pady=2)
        ttk.Label(name_row, text="Name:", width=10).pack(side=tk.LEFT)
        ttk.Entry(name_row, textvariable=name_var).pack(side=tk.LEFT, fill=tk.X, expand=True)

        def add_entry(key, label, value="", width=16):
            row = ttk.Frame(form)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=label, width=10).pack(side=tk.LEFT)
            variable = tk.StringVar(value=str(value))
            ttk.Entry(row, textvariable=variable, width=width).pack(
                side=tk.LEFT, fill=tk.X, expand=True
            )
            self._trigger_editor_vars[key] = variable
            return variable

        def add_combo(key, label, values, value="", state="readonly"):
            row = ttk.Frame(form)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=label, width=10).pack(side=tk.LEFT)
            variable = tk.StringVar(value=value)
            ttk.Combobox(
                row, textvariable=variable, values=values, state=state, width=16
            ).pack(side=tk.LEFT, fill=tk.X, expand=True)
            self._trigger_editor_vars[key] = variable
            return variable

        def add_text(key, label, value="", height=4):
            ttk.Label(form, text=label).pack(anchor=tk.W, pady=(4, 0))
            text = tk.Text(form, height=height, wrap=tk.WORD)
            text.pack(fill=tk.X, expand=False)
            text.insert("1.0", value)
            self._trigger_editor_vars[key] = text
            return text

        def add_coordinate_picker(x_var, y_var):
            def start_pick():
                self._trigger_position_picker = {
                    "x_var": x_var,
                    "y_var": y_var,
                }
                self.cursor_label.config(text="Click target cell (Esc to cancel)")
                self.canvas.focus_set()

            ttk.Button(form, text="Pick coordinates on map", command=start_pick).pack(
                anchor=tk.W, pady=3
            )

        if trigger_type == "teleport":
            area_names = [os.path.splitext(area)[0] for area in self.current_game.areas]
            add_combo("area", "Area:", area_names, params.get("area", ""))
            x_var = add_entry("x", "Target X:", params.get("x", 0))
            y_var = add_entry("y", "Target Y:", params.get("y", 0))
            add_coordinate_picker(x_var, y_var)
        elif trigger_type == "inventory":
            items = [""] + self.current_game.used_objects
            add_combo("add", "Add item:", items, params.get("add", ""))
            add_combo("remove", "Remove item:", items, params.get("remove", ""))
        elif trigger_type == "tile_update":
            x_var = add_entry("x", "Target X:", params.get("x", 0))
            y_var = add_entry("y", "Target Y:", params.get("y", 0))
            tile_name = params.get("tile", "")
            tile_values = {}
            for name in self.tile_manager.get_tile_names():
                display = self.tile_manager.get_tile_info(name).get("display_name", name)
                label = display if display not in tile_values else f"{display} ({name})"
                tile_values[label] = name
            if tile_name and tile_name not in tile_values.values():
                tile_values[tile_name] = tile_name
            selected_label = next(
                (label for label, name in tile_values.items() if name == tile_name), ""
            )
            add_combo("tile", "Change to:", list(tile_values), selected_label)
            self._trigger_editor_tile_labels = tile_values
            current_tile_label = ttk.Label(form, text="")
            current_tile_label.pack(anchor=tk.W, pady=2)

            def update_current_tile(*_args):
                try:
                    target_x, target_y = int(x_var.get()), int(y_var.get())
                except ValueError:
                    current_tile_label.config(text="Current tile: invalid coordinates")
                    return
                if not (0 <= target_x < self.current_area.width and
                        0 <= target_y < self.current_area.height):
                    current_tile_label.config(text="Current tile: outside this area")
                    return
                current_name = self.current_area.tiles[target_y][target_x].type
                display_name = self.tile_manager.get_tile_info(current_name).get(
                    "display_name", current_name
                )
                current_tile_label.config(text=f"Current tile: {display_name}")

            x_var.trace_add("write", update_current_tile)
            y_var.trace_add("write", update_current_tile)
            update_current_tile()
            ttk.Label(
                form,
                text="Click a map tile to set the target coordinates.",
                wraplength=245,
            ).pack(anchor=tk.W, pady=3)
            walkable_var = tk.BooleanVar(value=params.get("walkable", True))
            ttk.Checkbutton(form, text="Walkable", variable=walkable_var).pack(anchor=tk.W)
            self._trigger_editor_vars["walkable"] = walkable_var
        elif trigger_type == "area_object":
            area_names = [os.path.splitext(area)[0] for area in self.current_game.areas]
            add_combo("area", "Area:", area_names, params.get("area", ""))
            add_combo(
                "object", "Object:", self.current_game.used_objects, params.get("object", "")
            )
        elif trigger_type == "game_end":
            add_combo("win_lose", "Result:", ("win", "lose"), params.get("win_lose", "win"))
            add_text("message", "Message:", params.get("message", ""), height=3)
        elif trigger_type == "show_message":
            add_text("message", "Message:", params.get("message", ""), height=5)
        elif trigger_type == "custom":
            default_code = '''# Available game variables:
# game.player_x, game.player_y - Player position
# game.player_inventory - List of items player has
# game.current_area - Current area name
# game.set_area(area_name, x, y) - Teleport to area
# game.add_item(item_name) - Add item to inventory
# game.remove_item(item_name) - Remove item from inventory
# game.show_message(message) - Show a message to the player
# game.end_game(win=True, message="") - End the game

# Your code here:
'''
            add_text(
                "code",
                "Python Code:",
                params.get("code", default_code),
                height=7,
            )

    def save_selected_trigger(self, show_error=True, refresh=True):
        if getattr(self, "selected_mode", "trigger") != "trigger":
            return True
        trigger = getattr(self, "_trigger_editor_trigger", None)
        variables = getattr(self, "_trigger_editor_vars", {})
        if trigger is None or not variables:
            return True

        parameters = {}
        for name, variable in variables.items():
            if name in ("name", "trigger_type"):
                continue
            if isinstance(variable, tk.Text):
                parameters[name] = variable.get("1.0", tk.END).rstrip("\n")
            elif isinstance(variable, tk.BooleanVar):
                parameters[name] = variable.get()
            else:
                value = variable.get()
                if name in ("x", "y"):
                    try:
                        value = int(value)
                    except ValueError:
                        if show_error:
                            messagebox.showerror(
                                "Invalid Coordinates",
                                f"{name.upper()} must be a whole number.",
                            )
                        return False
                parameters[name] = value

        trigger_type = self._trigger_editor_type_labels.get(
            variables["trigger_type"].get()
        )
        if trigger_type is None:
            if show_error:
                messagebox.showerror("Invalid Trigger Type", "Choose a valid trigger type.")
            return False
        if trigger_type == "tile_update":
            selected_tile = self._trigger_editor_tile_labels.get(
                parameters.get("tile", "")
            )
            if not selected_tile:
                if show_error:
                    messagebox.showerror(
                        "Select a Tile", "Choose the tile to change the target to."
                    )
                return False
            parameters["tile"] = selected_tile

        coordinate_error = self._trigger_coordinate_error(trigger_type, parameters)
        if coordinate_error:
            if show_error:
                messagebox.showerror("Invalid Coordinates", coordinate_error)
            return False

        trigger.name = variables["name"].get()
        trigger.trigger_type = trigger_type
        trigger.parameters = parameters
        if refresh:
            self.refresh_trigger_editor()
            self.update_properties_display()
            self.draw_area()
        return True

    def delete_selected_trigger(self, confirm=False):
        triggers_here = self._triggers_at_cursor()
        if not triggers_here or not 0 <= self.selected_trigger_index < len(triggers_here):
            return False
        if confirm and not messagebox.askyesno(
            "Delete Trigger", "Delete the selected trigger?"
        ):
            return False

        trigger = triggers_here[self.selected_trigger_index]
        self.current_area.triggers.remove(trigger)
        remaining = self._triggers_at_cursor()
        self.selected_trigger_index = min(
            self.selected_trigger_index, max(0, len(remaining) - 1)
        )
        self._trigger_editor_trigger = None
        self._trigger_editor_vars = {}
        self.refresh_trigger_editor()
        self.update_properties_display()
        self.draw_area()
        return True

    def _trigger_coordinate_error(self, trigger_type, parameters):
        if trigger_type == "teleport":
            selected_area = parameters.get("area", "")
            area_filename = next(
                (area for area in self.current_game.areas
                 if os.path.splitext(os.path.basename(area))[0] == selected_area),
                None
            )
            if not area_filename:
                return "Select a destination area that belongs to this game."
            area_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "areas", area_filename
            )
            if (self.current_area_file and
                    os.path.realpath(self.current_area_file) == os.path.realpath(area_path)):
                destination_width = self.current_area.width
                destination_height = self.current_area.height
            else:
                try:
                    with open(area_path, 'r') as f:
                        destination_area = json.load(f)
                    destination_width = int(destination_area["width"])
                    destination_height = int(destination_area["height"])
                except (OSError, KeyError, TypeError, ValueError) as e:
                    return f"Could not read destination area dimensions: {e}"
        elif trigger_type == "tile_update":
            destination_width = self.current_area.width
            destination_height = self.current_area.height
        else:
            return None
        x, y = parameters["x"], parameters["y"]
        if not (0 <= x < destination_width and 0 <= y < destination_height):
            return (
                "Coordinates must be within the destination area "
                f"(X: 0-{destination_width - 1}, Y: 0-{destination_height - 1})."
            )
        return None
