"""
File management methods for the Tinker RPG Editor
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
from dataclasses import asdict

from project_paths import project_root

MAX_RECENT_GAMES = 10


class FileManager:
    """Mixin class containing file management methods"""

    @staticmethod
    def _editor_form_values(variables):
        return tuple(variable.get("1.0", "end-1c") if isinstance(variable, tk.Text)
                     else variable.get() for variable in variables)

    def remember_editor_form(self, name, variables):
        if not hasattr(self, "_editor_form_baselines"):
            self._editor_form_baselines = {}
        variables = tuple(variables)
        self._editor_form_baselines[name] = (variables, self._editor_form_values(variables))

    def pending_editor_forms(self):
        pending = set()
        for name, (variables, baseline) in getattr(self, "_editor_form_baselines", {}).items():
            try:
                if self._editor_form_values(variables) != baseline:
                    pending.add(name)
            except tk.TclError:
                # A form has been destroyed while changing the selected tool.
                continue
        return pending

    def has_unsaved_changes(self):
        return (
            asdict(self.current_game) != self._saved_game_state
            or asdict(self.current_area) != self._saved_area_state
            or bool(self.pending_editor_forms())
        )

    def close_editor(self):
        if self.has_unsaved_changes():
            answer = messagebox.askyesnocancel(
                "Unsaved Changes",
                "Save changes to the game and area before closing?",
                parent=self.root,
            )
            if answer is None:
                return
            if answer:
                if ("object" in self.pending_editor_forms()
                        and not self.save_object_definition_changes()):
                    return
                self.save_all()
                if self.has_unsaved_changes():
                    return
        self.root.destroy()

    def _project_path(self, *parts):
        return os.path.join(project_root(), *parts)

    def _recent_games_path(self):
        return os.path.join(
            os.path.expanduser("~"), ".tinker-rpg", "recent_games.json"
        )

    def create_open_recent_menu(self, parent):
        self.recent_games_menu = tk.Menu(parent, tearoff=0)
        self.recent_games = self._read_recent_games()
        self.recent_games_menu.configure(postcommand=self.refresh_open_recent_menu)
        return self.recent_games_menu

    def _read_recent_games(self):
        filename = self._recent_games_path()
        if not os.path.exists(filename):
            return []
        try:
            with open(filename, "r", encoding="utf-8") as recent_file:
                paths = json.load(recent_file)
        except (OSError, json.JSONDecodeError) as error:
            messagebox.showwarning(
                "Open Recent",
                f"Could not read the recent games list: {error}",
            )
            return []
        if not isinstance(paths, list) or any(
            not isinstance(path, str) for path in paths
        ):
            messagebox.showwarning(
                "Open Recent",
                "The recent games list is invalid and will be ignored.",
            )
            return []
        existing_paths = []
        for path in paths:
            normalized = os.path.abspath(os.path.expanduser(path))
            if os.path.isfile(normalized) and normalized not in existing_paths:
                existing_paths.append(normalized)
        return existing_paths[:MAX_RECENT_GAMES]

    def _write_recent_games(self):
        filename = self._recent_games_path()
        try:
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            with open(filename, "w", encoding="utf-8") as recent_file:
                json.dump(self.recent_games[:MAX_RECENT_GAMES], recent_file, indent=2)
        except OSError as error:
            messagebox.showwarning(
                "Open Recent",
                f"Could not save the recent games list: {error}",
            )

    def refresh_open_recent_menu(self):
        self.recent_games = [
            path for path in self.recent_games if os.path.isfile(path)
        ][:MAX_RECENT_GAMES]
        self.recent_games_menu.delete(0, tk.END)
        if self.recent_games:
            for path in self.recent_games:
                filename = os.path.basename(path)
                directory = os.path.basename(os.path.dirname(path))
                label = f"{filename} ({directory})" if directory else filename
                self.recent_games_menu.add_command(
                    label=label,
                    command=lambda recent_path=path: self.open_game(recent_path),
                )
            self.recent_games_menu.add_separator()
            self.recent_games_menu.add_command(
                label="Clear Recent",
                command=self.clear_recent_games,
            )
        else:
            self.recent_games_menu.add_command(
                label="No Recent Games",
                state=tk.DISABLED,
            )

    def _remember_recent_game(self, filename):
        path = os.path.abspath(os.path.expanduser(filename))
        self.recent_games = [
            path,
            *[recent for recent in self.recent_games if recent != path],
        ][:MAX_RECENT_GAMES]
        self._write_recent_games()

    def clear_recent_games(self):
        self.recent_games = []
        self._write_recent_games()
        self.refresh_open_recent_menu()

    def _is_project_area(self, filename):
        area_dir = os.path.realpath(self._project_path("areas"))
        return os.path.dirname(os.path.realpath(filename)) == area_dir

    def _confirm_area_overwrite(self, filename):
        if not os.path.exists(filename):
            return True
        area_name = os.path.splitext(os.path.basename(filename))[0]
        return messagebox.askyesno(
            "Area Already Exists",
            f"An area named '{area_name}' already exists. Do you want to overwrite it?",
        )

    @staticmethod
    def _normalize_save_filename(filename):
        directory, basename = os.path.split(filename)
        return os.path.join(directory, basename.replace(" ", "_"))

    def refresh_game_areas_list(self):
        if not hasattr(self, "game_areas_listbox"):
            return
        self.game_areas_listbox.delete(0, tk.END)
        if self.current_game.areas:
            for area_filename in self.current_game.areas:
                area_name = os.path.splitext(os.path.basename(area_filename))[0]
                if area_filename == self.current_game.properties.get("start_area"):
                    area_name += " (Start)"
                self.game_areas_listbox.insert(tk.END, area_name)
        else:
            self.game_areas_listbox.insert(tk.END, "(No areas in this game)")

    def load_selected_game_area(self, _event=None):
        if not hasattr(self, "game_areas_listbox"):
            return
        selection = self.game_areas_listbox.curselection()
        if not selection or selection[0] >= len(self.current_game.areas):
            return
        area_filename = self.current_game.areas[selection[0]]
        area_path = self._project_path("areas", area_filename)
        self._load_area_from_file(area_path, show_message=False)
    
    # Game management methods
    def new_game(self):
        if messagebox.askyesno("New Game", "Create new game? Unsaved changes will be lost."):
            if hasattr(self, "save_selected_trigger") and not self.save_selected_trigger():
                return
            if hasattr(self, "save_enemy_definition") and not self.save_enemy_definition():
                return
            from data_classes import Game, Area
            self.current_game = Game()
            if hasattr(self, "ensure_example_enemy_definitions"):
                self.ensure_example_enemy_definitions()
            self.current_area = Area()
            self.current_area_file = None
            self.current_game_file = None
            self.cursor_x = self.cursor_y = 0
            self.area_name_var.set(self.current_area.name)
            self.refresh_game_areas_list()
            self.game_name_var.set(self.current_game.name)
            self.refresh_player_setup()
            if hasattr(self, "refresh_enemy_editor"):
                self.selected_enemy_id = None
                self.refresh_enemy_editor()
            self.draw_area()
            if hasattr(self, "refresh_trigger_editor"):
                self.refresh_trigger_editor()
            self.update_properties_display()
            self._saved_game_state = asdict(self.current_game)
            self._saved_area_state = asdict(self.current_area)
    
    def save_game(self):
        if self.current_game_file:
            self._save_game_to_file(self.current_game_file)
        else:
            self.save_game_as()
    
    def save_game_as(self):
        filename = filedialog.asksaveasfilename(
            initialdir=self._project_path("games"),
            defaultextension=".json",
            filetypes=[("Game files", "*.json"), ("All files", "*.*")],
            initialfile=f"{self.current_game.name.replace(' ', '_')}.json",
            title="Save Game As"
        )
        if filename:
            filename = self._normalize_save_filename(filename)
            if self._save_game_to_file(filename):
                self.current_game_file = filename

    def _save_game_to_file(self, filename, show_message=True):
        try:
            if ("object" in self.pending_editor_forms()
                    and not self.save_object_definition_changes()):
                return False
            if (hasattr(self, "save_enemy_definition") and
                    not self.save_enemy_definition()):
                return False
            if (hasattr(self, "player_stat_vars") and
                    not self.save_player_setup()):
                return False
            with open(filename, 'w') as f:
                json.dump(asdict(self.current_game), f, indent=2)
            self._saved_game_state = asdict(self.current_game)
            if show_message:
                messagebox.showinfo("Save Game", f"Game saved to {filename}")
            return True
        except Exception as e:
            if show_message:
                messagebox.showerror("Error", f"Failed to save game: {e}")
            return False
    
    def open_game(self, filename=None):
        if filename is None:
            filename = filedialog.askopenfilename(
                initialdir=self._project_path("games"),
                filetypes=[("Game files", "*.json"), ("All files", "*.*")],
                title="Open Game"
            )
        if filename:
            try:
                filename = os.path.abspath(os.path.expanduser(filename))
                with open(filename, 'r') as f:
                    game_dict = json.load(f)
                
                from data_classes import Game
                self.current_game = Game(**game_dict)
                if hasattr(self, "ensure_example_enemy_definitions"):
                    self.ensure_example_enemy_definitions()
                self.current_game_file = filename
                self.game_name_var.set(self.current_game.name)
                self.refresh_game_areas_list()
                self.refresh_player_setup()
                if hasattr(self, "refresh_enemy_editor"):
                    self.selected_enemy_id = None
                    self.refresh_enemy_editor()
                
                loaded_areas = []
                
                # Open the explicit start area, with a fallback for older games.
                from data_classes import Area
                self.current_area = Area()
                self.current_area_file = None
                self._saved_area_state = asdict(self.current_area)
                start_area = self.current_game.properties.get("start_area")
                if self.current_game.areas or start_area:
                    first_area_file = self._project_path(
                        "areas", start_area or self.current_game.areas[0]
                    )
                    if os.path.exists(first_area_file):
                        self._load_area_from_file(first_area_file, show_message=False)
                        loaded_areas = [
                            os.path.splitext(area)[0] for area in self.current_game.areas
                            if os.path.exists(self._project_path("areas", area))
                        ]
                
                self._saved_game_state = asdict(self.current_game)
                self.area_name_var.set(self.current_area.name)
                self.draw_area()
                self.update_properties_display()

                # Show consolidated load message
                self.show_load_message(
                    loaded_areas=loaded_areas,
                    game_name=self.current_game.name
                )
                self._remember_recent_game(filename)
                
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
                    if self._save_area_to_file(self.current_area_file, show_message=False):
                        saved_items.append(f"Area: {os.path.basename(self.current_area_file)}")
                    else:
                        errors.append(f"Failed to save area: {os.path.basename(self.current_area_file)}")
                else:
                    # Need to prompt for area filename
                    area_filename = filedialog.asksaveasfilename(
                        defaultextension=".json",
                        filetypes=[("Area files", "*.json"), ("All files", "*.*")],
                        initialdir=self._project_path("areas"),
                        initialfile=f"{self.current_area.name.replace(' ', '_')}.json",
                        title="Save Area As"
                    )
                    if area_filename:
                        area_filename = self._normalize_save_filename(area_filename)
                        if not self._is_project_area(area_filename):
                            errors.append("Area must be saved inside the project's areas/ folder")
                        elif not self._confirm_area_overwrite(area_filename):
                            errors.append(
                                f"Area overwrite cancelled: {os.path.basename(area_filename)}"
                            )
                        elif self._save_area_to_file(area_filename, show_message=False):
                            self.current_area_file = area_filename
                            saved_items.append(f"Area: {os.path.basename(area_filename)}")

                            area_basename = os.path.basename(area_filename)
                            if area_basename not in self.current_game.areas:
                                self.current_game.areas.append(area_basename)
                                self.refresh_game_areas_list()
                        else:
                            errors.append(f"Failed to save area: {os.path.basename(area_filename)}")
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
                    if self._save_game_to_file(self.current_game_file, show_message=False):
                        saved_items.append(f"Game: {os.path.basename(self.current_game_file)}")
                    else:
                        errors.append(f"Failed to save game: {os.path.basename(self.current_game_file)}")
                else:
                    # Need to prompt for game filename
                    game_filename = filedialog.asksaveasfilename(
                        initialdir=self._project_path("games"),
                        defaultextension=".json",
                        filetypes=[("Game files", "*.json"), ("All files", "*.*")],
                        initialfile=f"{self.current_game.name.replace(' ', '_')}.json",
                        title="Save Game As"
                    )
                    if game_filename:
                        game_filename = self._normalize_save_filename(game_filename)
                        if self._save_game_to_file(game_filename, show_message=False):
                            self.current_game_file = game_filename
                            saved_items.append(f"Game: {os.path.basename(game_filename)}")
                        else:
                            errors.append(f"Failed to save game: {os.path.basename(game_filename)}")
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
            if hasattr(self, "save_selected_trigger") and not self.save_selected_trigger():
                return
            from data_classes import Area
            self.current_area = Area()
            self.current_area_file = None
            self.cursor_x = self.cursor_y = 0
            self.area_name_var.set(self.current_area.name)
            self._saved_area_state = asdict(self.current_area)
            self.draw_area()
            if hasattr(self, "refresh_trigger_editor"):
                self.refresh_trigger_editor()
            self.update_properties_display()
    
    def save_trigger_and_area(self):
        if not self.save_selected_trigger():
            return False
        return self.save_area(save_trigger=False)

    def save_area(self, save_trigger=True):
        if self.current_area_file:
            if save_trigger:
                return self._save_area_to_file(self.current_area_file)
            return self._save_area_to_file(
                self.current_area_file, save_trigger=False
            )
        if save_trigger:
            return self.save_area_as()
        return self.save_area_as(save_trigger=False)
    
    def save_area_as(self, save_trigger=True):
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("Area files", "*.json"), ("All files", "*.*")],
            initialdir=self._project_path("areas"),
            initialfile=f"{self.current_area.name.replace(' ', '_')}.json",
            title="Save Area As"
        )
        if filename:
            filename = self._normalize_save_filename(filename)
            if not self._is_project_area(filename):
                messagebox.showerror("Save Area", "Area files must be saved inside the project's areas/ folder.")
                return False
            elif not self._confirm_area_overwrite(filename):
                return False
            elif (
                self._save_area_to_file(filename)
                if save_trigger
                else self._save_area_to_file(filename, save_trigger=False)
            ):
                self.current_area_file = filename
                return True
        return False

    def _save_area_to_file(self, filename, save_trigger=True, show_message=True):
        try:
            if (save_trigger and hasattr(self, "save_selected_trigger") and
                    not self.save_selected_trigger()):
                return False
            if hasattr(self, "sync_enemy_instances"):
                self.sync_enemy_instances()
            with open(filename, 'w') as f:
                json.dump(asdict(self.current_area), f, indent=2)
            self._saved_area_state = asdict(self.current_area)
            if show_message:
                messagebox.showinfo("Save Area", f"Area saved to {filename}")
            return True
        except Exception as e:
            if show_message:
                messagebox.showerror("Error", f"Failed to save area: {e}")
            return False
    
    def open_area(self):
        filename = filedialog.askopenfilename(
            filetypes=[("Area files", "*.json"), ("All files", "*.*")],
            initialdir=self._project_path("areas"),
            title="Open Area"
        )
        if filename:
            self._load_area_from_file(filename)
    
    def _load_area_from_file(self, filename, show_message=True):
        try:
            if (hasattr(self, "save_selected_trigger") and
                    not self.save_selected_trigger()):
                return False
            self.current_area = self._read_area_file(filename)
            if hasattr(self, "sync_enemy_instances"):
                self.sync_enemy_instances()
            
            self.current_area_file = filename
            self._saved_area_state = asdict(self.current_area)
            self.cursor_x = self.cursor_y = 0
            self.area_name_var.set(self.current_area.name)
            self.draw_area()
            if hasattr(self, "refresh_trigger_editor"):
                self.refresh_trigger_editor()
            self.update_properties_display()
            
            if show_message:
                area_name = os.path.splitext(os.path.basename(filename))[0]
                self.show_load_message(loaded_areas=[area_name])
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open area: {e}")

    @staticmethod
    def _read_area_file(filename):
        with open(filename, "r", encoding="utf-8") as area_file:
            area_dict = json.load(area_file)

        from data_classes import Area, Tile, GameObject, Trigger, MAX_AREA_DIMENSION
        width, height = area_dict.get("width"), area_dict.get("height")
        if (type(width) is not int or type(height) is not int or
                not (1 <= width <= MAX_AREA_DIMENSION and
                     1 <= height <= MAX_AREA_DIMENSION)):
            raise ValueError(
                f"Area width and height must each be between 1 and "
                f"{MAX_AREA_DIMENSION}."
            )

        area = Area(**area_dict)
        if not area.name or not area.name.strip() or area.name == "Untitled Area":
            area.name = os.path.splitext(os.path.basename(filename))[0]
        if (len(area.tiles) != height or
                any(not isinstance(row, list) or len(row) != width
                    for row in area.tiles)):
            raise ValueError("Area tile data does not match its dimensions.")
        for y, row in enumerate(area.tiles):
            for x, tile_data in enumerate(row):
                if isinstance(tile_data, dict):
                    area.tiles[y][x] = Tile(**tile_data)
        area.objects = [GameObject(**obj) for obj in area.objects]
        area.triggers = [Trigger(**trigger) for trigger in area.triggers]
        return area
    
    def add_area_to_game(self):
        if not self.current_area_file:
            messagebox.showwarning("Add Area", "Please save the area first before adding it to the game.")
            return
        
        if not self._is_project_area(self.current_area_file):
            messagebox.showwarning("Add Area", "Game areas must be saved inside the project's areas/ folder.")
            return
        area_filename = os.path.basename(self.current_area_file)
        if area_filename not in self.current_game.areas:
            self.current_game.areas.append(area_filename)
            self.refresh_game_areas_list()
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

        enemy_definitions = self.current_game.properties.get("enemies", {})
        if isinstance(enemy_definitions, dict):
            for definition in enemy_definitions.values():
                sprite = definition.get("sprite")
                if sprite:
                    used_npcs.add(sprite)
        
        # Scan all areas in game
        for area_filename in self.current_game.areas:
            area_path = self._project_path("areas", area_filename)
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