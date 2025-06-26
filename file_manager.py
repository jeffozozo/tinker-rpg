"""
File management methods for the Tinker RPG Editor
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
from dataclasses import asdict

class FileManager:
    """Mixin class containing file management methods"""
    
    # Game management methods
    def new_game(self):
        if messagebox.askyesno("New Game", "Create new game? Unsaved changes will be lost."):
            from data_classes import Game, Area
            self.current_game = Game()
            self.current_area = Area()
            self.current_area_file = None
            self.current_game_file = None
            self.cursor_x = self.cursor_y = 0
            self.area_name_var.set(self.current_area.name)
            self.game_name_label.config(text=self.current_game.name)
            self.draw_area()
            self.update_properties_display()
    
    def save_game(self):
        if self.current_game_file:
            self._save_game_to_file(self.current_game_file)
        else:
            self.save_game_as()
    
    def save_game_as(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("Game files", "*.json"), ("All files", "*.*")],
            title="Save Game As"
        )
        if filename:
            self._save_game_to_file(filename)
            self.current_game_file = filename
    
    def _save_game_to_file(self, filename):
        try:
            with open(filename, 'w') as f:
                json.dump(asdict(self.current_game), f, indent=2)
            messagebox.showinfo("Save Game", f"Game saved to {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save game: {e}")
    
    def open_game(self):
        filename = filedialog.askopenfilename(
            initialdir="games",
            filetypes=[("Game files", "*.json"), ("All files", "*.*")],
            title="Open Game"
        )
        if filename:
            try:
                with open(filename, 'r') as f:
                    game_dict = json.load(f)
                
                from data_classes import Game
                self.current_game = Game(**game_dict)
                self.current_game_file = filename
                self.game_name_label.config(text=self.current_game.name)
                
                loaded_areas = []
                
                # Load the first area if available
                if self.current_game.areas:
                    first_area_file = os.path.join("areas", self.current_game.areas[0])
                    if os.path.exists(first_area_file):
                        self._load_area_from_file(first_area_file, show_message=False)
                        loaded_areas = [os.path.splitext(area)[0] for area in self.current_game.areas 
                                      if os.path.exists(os.path.join("areas", area))]
                
                # Show consolidated load message
                self.show_load_message(
                    loaded_areas=loaded_areas,
                    game_name=self.current_game.name
                )
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open game: {e}")
    
    def save_all(self):
        """Save both the current area and the current game"""
        saved_items = []
        errors = []
        
        # Save current area first
        if self.current_area:
            try:
                if self.current_area_file:
                    self._save_area_to_file(self.current_area_file)
                    saved_items.append(f"Area: {os.path.basename(self.current_area_file)}")
                else:
                    # Need to prompt for area filename
                    area_filename = filedialog.asksaveasfilename(
                        defaultextension=".json",
                        filetypes=[("Area files", "*.json"), ("All files", "*.*")],
                        initialdir="areas",
                        title="Save Area As"
                    )
                    if area_filename:
                        self._save_area_to_file(area_filename)
                        self.current_area_file = area_filename
                        saved_items.append(f"Area: {os.path.basename(area_filename)}")
                        
                        # Auto-add to game if not already included
                        area_basename = os.path.basename(area_filename)
                        if area_basename not in self.current_game.areas:
                            self.current_game.areas.append(area_basename)
                    else:
                        errors.append("Area save cancelled by user")
            except Exception as e:
                errors.append(f"Failed to save area: {e}")
        
        # Update game assets based on current state
        try:
            self.update_game_assets_silent()
            saved_items.append("Game assets updated")
        except Exception as e:
            errors.append(f"Failed to update game assets: {e}")
        
        # Save current game
        if self.current_game:
            try:
                if self.current_game_file:
                    self._save_game_to_file(self.current_game_file)
                    saved_items.append(f"Game: {os.path.basename(self.current_game_file)}")
                else:
                    # Need to prompt for game filename
                    game_filename = filedialog.asksaveasfilename(
                        defaultextension=".json",
                        filetypes=[("Game files", "*.json"), ("All files", "*.*")],
                        title="Save Game As"
                    )
                    if game_filename:
                        self._save_game_to_file(game_filename)
                        self.current_game_file = game_filename
                        saved_items.append(f"Game: {os.path.basename(game_filename)}")
                    else:
                        errors.append("Game save cancelled by user")
            except Exception as e:
                errors.append(f"Failed to save game: {e}")
        
        # Show results to user
        if saved_items and not errors:
            messagebox.showinfo("Save All", f"Successfully saved:\n" + "\n".join(f"• {item}" for item in saved_items))
        elif saved_items and errors:
            messagebox.showwarning("Save All", 
                f"Partially successful:\n\nSaved:\n" + "\n".join(f"• {item}" for item in saved_items) +
                f"\n\nErrors:\n" + "\n".join(f"• {error}" for error in errors))
        else:
            messagebox.showerror("Save All", f"Save failed:\n" + "\n".join(f"• {error}" for error in errors))
    
    # Area management methods
    def new_area(self):
        if messagebox.askyesno("New Area", "Create new area? Unsaved changes will be lost."):
            from data_classes import Area
            self.current_area = Area()
            self.current_area_file = None
            self.cursor_x = self.cursor_y = 0
            self.area_name_var.set(self.current_area.name)
            self.draw_area()
            self.update_properties_display()
    
    def save_area(self):
        if self.current_area_file:
            self._save_area_to_file(self.current_area_file)
        else:
            self.save_area_as()
    
    def save_area_as(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("Area files", "*.json"), ("All files", "*.*")],
            initialdir="areas",
            title="Save Area As"
        )
        if filename:
            self._save_area_to_file(filename)
            self.current_area_file = filename
    
    def _save_area_to_file(self, filename):
        try:
            with open(filename, 'w') as f:
                json.dump(asdict(self.current_area), f, indent=2)
            messagebox.showinfo("Save Area", f"Area saved to {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save area: {e}")
    
    def open_area(self):
        filename = filedialog.askopenfilename(
            filetypes=[("Area files", "*.json"), ("All files", "*.*")],
            initialdir="areas",
            title="Open Area"
        )
        if filename:
            self._load_area_from_file(filename)
    
    def _load_area_from_file(self, filename, show_message=True):
        try:
            with open(filename, 'r') as f:
                area_dict = json.load(f)
            
            from data_classes import Area, Tile, GameObject, Trigger
            self.current_area = Area(**area_dict)
            
            # Reconstruct tile objects
            for y, row in enumerate(self.current_area.tiles):
                for x, tile_data in enumerate(row):
                    if isinstance(tile_data, dict):
                        self.current_area.tiles[y][x] = Tile(**tile_data)
            
            self.current_area.objects = [GameObject(**obj) for obj in self.current_area.objects]
            self.current_area.triggers = [Trigger(**trig) for trig in self.current_area.triggers]
            
            self.current_area_file = filename
            self.cursor_x = self.cursor_y = 0
            self.area_name_var.set(self.current_area.name)
            self.draw_area()
            self.update_properties_display()
            
            if show_message:
                area_name = os.path.splitext(os.path.basename(filename))[0]
                self.show_load_message(loaded_areas=[area_name])
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open area: {e}")
    
    def add_area_to_game(self):
        if not self.current_area_file:
            messagebox.showwarning("Add Area", "Please save the area first before adding it to the game.")
            return
        
        area_filename = os.path.basename(self.current_area_file)
        if area_filename not in self.current_game.areas:
            self.current_game.areas.append(area_filename)
            messagebox.showinfo("Add Area", f"Area '{area_filename}' added to game '{self.current_game.name}'")
        else:
            messagebox.showinfo("Add Area", f"Area '{area_filename}' is already in the game.")
    
    def update_game_assets_silent(self):
        """Update the game's asset lists without showing a message box"""
        used_tiles = set()
        used_objects = set()
        used_npcs = set()
        used_triggers = set()
        
        # Scan current area
        for row in self.current_area.tiles:
            for tile in row:
                if tile.type != "empty":
                    used_tiles.add(tile.type)
        
        for obj in self.current_area.objects:
            if obj.type in self.tile_manager.get_npc_names():
                used_npcs.add(obj.type)
            else:
                used_objects.add(obj.type)
        
        for trigger in self.current_area.triggers:
            used_triggers.add("trigger")  # Generic trigger type
        
        # Scan all areas in game
        for area_filename in self.current_game.areas:
            area_path = os.path.join("areas", area_filename)
            if os.path.exists(area_path):
                try:
                    with open(area_path, 'r') as f:
                        area_dict = json.load(f)
                    
                    # Scan tiles
                    for row in area_dict.get('tiles', []):
                        for tile_data in row:
                            if isinstance(tile_data, dict):
                                tile_type = tile_data.get('type', 'empty')
                            else:
                                tile_type = 'empty'
                            if tile_type != "empty":
                                used_tiles.add(tile_type)
                    
                    # Scan objects
                    for obj_data in area_dict.get('objects', []):
                        obj_type = obj_data.get('type', '')
                        if obj_type in self.tile_manager.get_npc_names():
                            used_npcs.add(obj_type)
                        else:
                            used_objects.add(obj_type)
                    
                    # Scan triggers
                    if area_dict.get('triggers', []):
                        used_triggers.add("trigger")
                        
                except Exception as e:
                    print(f"Error scanning area {area_filename}: {e}")
        
        # Update game asset lists
        self.current_game.used_tiles = list(used_tiles)
        self.current_game.used_objects = list(used_objects)
        self.current_game.used_npcs = list(used_npcs)
        self.current_game.used_triggers = list(used_triggers)
    
    def update_game_assets(self):
        """Update the game's asset lists based on what's used in all areas"""
        self.update_game_assets_silent()
        
        messagebox.showinfo("Update Assets", f"Game assets updated:\n"
                          f"Tiles: {len(self.current_game.used_tiles)}\n"
                          f"Objects: {len(self.current_game.used_objects)}\n"
                          f"NPCs: {len(self.current_game.used_npcs)}\n"
                          f"Triggers: {len(self.current_game.used_triggers)}")