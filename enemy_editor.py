"""Enemy definition editing and reusable enemy-instance helpers."""

import math
import json
import os
import tkinter as tk
from copy import deepcopy
from tkinter import messagebox, ttk
from uuid import uuid4

from data_classes import GameObject
from enemy_examples import example_enemy_definitions


RANGED_ATTACKS = ("none", "flame", "lightning", "gun")


class EnemyEditor:
    """Mixin for editing game enemy definitions and placing them in areas."""

    def setup_enemy_palette(self, parent):
        self.enemy_controls_frame = ttk.Frame(parent)
        ttk.Label(
            self.enemy_controls_frame,
            text="Select a type, move the map cursor, and press Space to place it.",
            wraplength=220,
        ).pack(anchor=tk.W, padx=5, pady=(0, 5))

        buttons = ttk.Frame(self.enemy_controls_frame)
        buttons.pack(fill=tk.X, padx=5, pady=(0, 5))
        ttk.Button(
            buttons, text="Add Enemy", command=self.add_enemy_definition
        ).pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Button(
            buttons, text="Delete Enemy", command=self.delete_enemy_definition
        ).pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Button(
            self.enemy_controls_frame,
            text="Add Example Enemies",
            command=self.add_example_enemy_definitions,
        ).pack(fill=tk.X, padx=5, pady=(0, 5))
        self.enemy_controls_frame.pack_forget()

    def setup_enemy_properties(self, parent):
        self.enemy_properties_frame = ttk.LabelFrame(parent, text="Enemy Definition")

        self.enemy_name_var = tk.StringVar()
        self.enemy_sprite_var = tk.StringVar()
        self.enemy_health_var = tk.StringVar()
        self.enemy_speed_var = tk.StringVar()
        self.enemy_ranged_attack_var = tk.StringVar()
        self.enemy_behavior_var = tk.StringVar()
        self.enemy_damage_var = tk.StringVar()
        self.enemy_sprite_selector = None

        self._enemy_field("Name:", self.enemy_name_var)
        self.enemy_sprite_selector = self._enemy_choice(
            "Live icon:", self.enemy_sprite_var, self._available_enemy_sprites()
        )
        self._enemy_field("Health:", self.enemy_health_var)
        self._enemy_field("Movement speed (tiles/turn):", self.enemy_speed_var)
        self._enemy_choice("Behavior:", self.enemy_behavior_var, ("stationary", "chase"))
        self._enemy_field("Contact damage:", self.enemy_damage_var)
        self._enemy_choice(
            "Ranged attack:",
            self.enemy_ranged_attack_var,
            RANGED_ATTACKS,
        )
        ttk.Label(
            self.enemy_properties_frame,
            text="Defeated enemies disappear.",
            wraplength=260,
        ).pack(anchor=tk.W, padx=5, pady=2)
        ttk.Button(
            self.enemy_properties_frame,
            text="Save Enemy Changes",
            command=self.save_enemy_definition,
        ).pack(anchor=tk.E, padx=5, pady=5)
        self.enemy_properties_frame.pack_forget()

    def _enemy_field(self, label, variable):
        row = ttk.Frame(self.enemy_properties_frame)
        row.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(row, text=label).pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=variable, width=12).pack(side=tk.RIGHT)

    def _enemy_choice(self, label, variable, values):
        row = ttk.Frame(self.enemy_properties_frame)
        row.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(row, text=label).pack(side=tk.LEFT)
        selector = ttk.Combobox(
            row, textvariable=variable, values=values, state="readonly", width=13
        )
        selector.pack(side=tk.RIGHT)
        return selector

    def _available_enemy_sprites(self):
        return tuple(self.tile_manager.get_npc_names())

    def get_enemy_definitions(self):
        definitions = self.current_game.properties.setdefault("enemies", {})
        if not isinstance(definitions, dict):
            raise ValueError("Game enemy definitions must be stored as an object.")
        for definition in definitions.values():
            definition.pop("dead_sprite", None)
        return definitions

    def _enemy_definition(self, enemy_id):
        return self.get_enemy_definitions().get(enemy_id)

    def _next_enemy_id(self):
        definitions = self.get_enemy_definitions()
        enemy_id = f"enemy_{uuid4().hex}"
        while enemy_id in definitions:
            enemy_id = f"enemy_{uuid4().hex}"
        return enemy_id

    def add_enemy_definition(self):
        sprites = self._available_enemy_sprites()
        if not sprites:
            messagebox.showwarning(
                "Add Enemy", "Add at least one NPC image before creating an enemy."
            )
            return
        if self.selected_enemy_id and not self.save_enemy_definition():
            return

        enemy_id = self._next_enemy_id()
        number = len(self.get_enemy_definitions()) + 1
        self.get_enemy_definitions()[enemy_id] = {
            "id": enemy_id,
            "name": f"Enemy {number}",
            "sprite": sprites[0],
            "health": 10,
            "movement_speed": 1.0,
            "behavior": "chase",
            "contact_damage": 1,
            "ranged_attack": "none",
        }
        self.selected_enemy_id = enemy_id
        self.refresh_enemy_editor()

    def add_example_enemy_definitions(self):
        examples = example_enemy_definitions()
        available_sprites = set(self._available_enemy_sprites())
        missing_sprites = sorted({
            definition["sprite"]
            for definition in examples.values()
            if definition["sprite"] not in available_sprites
        })
        if missing_sprites:
            messagebox.showerror(
                "Example Enemies",
                "Missing enemy icons: " + ", ".join(missing_sprites),
            )
            return
        if self.selected_enemy_id and not self.save_enemy_definition():
            return

        definitions = self.get_enemy_definitions()
        existing_ids = set(definitions)
        self.ensure_example_enemy_definitions()
        added_ids = [enemy_id for enemy_id in definitions if enemy_id not in existing_ids]
        self.selected_enemy_id = added_ids[0] if added_ids else next(
            enemy_id
            for enemy_id, definition in definitions.items()
            if definition.get("starter_key") in examples
            or definition.get("id") in examples
        )
        self.refresh_enemy_editor()

    def ensure_example_enemy_definitions(self):
        definitions = self.get_enemy_definitions()
        available_sprites = set(self._available_enemy_sprites())
        examples = example_enemy_definitions()
        for starter_key, definition in examples.items():
            already_present = any(
                existing.get("starter_key") == starter_key
                or existing.get("id") == starter_key
                for existing in definitions.values()
            )
            if (
                not already_present
                and definition["sprite"] in available_sprites
            ):
                instance = deepcopy(definition)
                enemy_id = self._next_enemy_id()
                instance["id"] = enemy_id
                instance["starter_key"] = starter_key
                definitions[enemy_id] = instance
    def delete_enemy_definition(self):
        enemy_id = getattr(self, "selected_enemy_id", None)
        if not enemy_id:
            return
        if any(
            obj.properties.get("enemy_id") == enemy_id
            for obj in self.current_area.objects
        ):
            messagebox.showwarning(
                "Delete Enemy",
                "Remove this enemy's placed instances from the current area first.",
            )
            return
        if not messagebox.askyesno(
            "Delete Enemy",
            "Delete this enemy definition? Placed copies in other areas keep their saved data.",
        ):
            return
        self.get_enemy_definitions().pop(enemy_id, None)
        self.selected_enemy_id = None
        self.refresh_enemy_editor()

    def refresh_enemy_editor(self):
        definitions = self.get_enemy_definitions()
        if self.selected_enemy_id not in definitions:
            self.selected_enemy_id = next(iter(definitions), None)

        sprites = self._available_enemy_sprites()
        if getattr(self, "enemy_sprite_selector", None) is not None:
            self.enemy_sprite_selector.configure(values=sprites)
        if self.selected_enemy_id:
            self._load_enemy_fields(definitions[self.selected_enemy_id])
        elif hasattr(self, "enemy_name_var"):
            for variable in (
                self.enemy_name_var,
                self.enemy_sprite_var,
                self.enemy_health_var,
                self.enemy_speed_var,
                self.enemy_ranged_attack_var,
            ):
                variable.set("")
            if hasattr(self, "enemy_behavior_var"):
                self.enemy_behavior_var.set("")
                self.enemy_damage_var.set("")
        if hasattr(self, "tile_canvas"):
            self.update_tile_display()

    def _load_enemy_fields(self, definition):
        if not hasattr(self, "enemy_name_var"):
            return
        self.enemy_name_var.set(definition.get("name", ""))
        self.enemy_sprite_var.set(definition.get("sprite", ""))
        self.enemy_health_var.set(str(definition.get("health", 10)))
        if hasattr(self, "enemy_behavior_var"):
            self.enemy_behavior_var.set(definition.get("behavior", "stationary"))
            self.enemy_damage_var.set(str(definition.get("contact_damage", 1)))
        self.enemy_speed_var.set(
            format(float(definition.get("movement_speed", 1.0)), ".12g")
        )
        self.enemy_ranged_attack_var.set(
            definition.get("ranged_attack", "none")
        )
        if hasattr(self, "remember_editor_form"):
            self.remember_editor_form("enemy", [
                getattr(self, name) for name in (
                    "enemy_name_var", "enemy_sprite_var", "enemy_health_var", "enemy_speed_var",
                    "enemy_ranged_attack_var", "enemy_behavior_var", "enemy_damage_var",
                ) if hasattr(self, name)
            ])

    def select_enemy_definition(self, index):
        enemy_ids = list(self.get_enemy_definitions())
        if index < 0 or index >= len(enemy_ids):
            return
        next_enemy_id = enemy_ids[index]
        if next_enemy_id == self.selected_enemy_id:
            return
        if self.selected_enemy_id and not self.save_enemy_definition(refresh=False):
            return
        self.selected_enemy_id = next_enemy_id
        self._load_enemy_fields(
            self.get_enemy_definitions()[self.selected_enemy_id]
        )
        self.update_tile_display()

    def save_enemy_definition(self, refresh=True):
        enemy_id = getattr(self, "selected_enemy_id", None)
        if not enemy_id or not hasattr(self, "enemy_name_var"):
            return True
        definition = self._enemy_definition(enemy_id)
        if definition is None:
            return True

        name = self.enemy_name_var.get().strip()
        sprite = self.enemy_sprite_var.get()
        try:
            health = int(self.enemy_health_var.get())
            movement_speed = float(self.enemy_speed_var.get())
        except ValueError:
            messagebox.showerror(
                "Invalid Enemy Stats",
                "Health must be a whole number and movement speed must be numeric.",
            )
            return False
        if health < 1:
            messagebox.showerror("Invalid Enemy Stats", "Health must be at least 1.")
            return False
        if not math.isfinite(movement_speed) or movement_speed < 0:
            messagebox.showerror(
                "Invalid Enemy Stats",
                "Movement speed must be a finite number that is zero or greater.",
            )
            return False
        if not name:
            messagebox.showerror("Invalid Enemy", "Enemy name cannot be empty.")
            return False
        if sprite not in self._available_enemy_sprites():
            messagebox.showerror(
                "Invalid Enemy", "Choose a live icon from the available NPC images."
            )
            return False
        ranged_attack = self.enemy_ranged_attack_var.get()
        if ranged_attack not in RANGED_ATTACKS:
            messagebox.showerror(
                "Invalid Enemy", "Choose a valid ranged-attack type."
            )
            return False

        behavior = definition.get("behavior", "stationary")
        contact_damage = definition.get("contact_damage", 1)
        if hasattr(self, "enemy_behavior_var"):
            behavior = self.enemy_behavior_var.get()
            try:
                contact_damage = int(self.enemy_damage_var.get())
            except ValueError:
                messagebox.showerror("Invalid Enemy Stats", "Contact damage must be a whole number.")
                return False
        if behavior not in ("stationary", "chase") or type(contact_damage) is not int or contact_damage < 0:
            messagebox.showerror("Invalid Enemy Stats", "Choose a behavior and non-negative contact damage.")
            return False

        previous_definition = deepcopy(definition)
        definition.update({
            "id": enemy_id,
            "name": name,
            "sprite": sprite,
            "health": health,
            "movement_speed": movement_speed,
            "behavior": behavior,
            "contact_damage": contact_damage,
            "ranged_attack": ranged_attack,
        })
        self.sync_enemy_instances()
        try:
            self.sync_saved_enemy_instances(enemy_id, definition)
        except (OSError, ValueError, TypeError, AttributeError) as error:
            definition.clear()
            definition.update(previous_definition)
            self.sync_enemy_instances()
            messagebox.showerror(
                "Enemy Save Failed",
                f"Could not update every saved area for this enemy: {error}",
            )
            return False
        if hasattr(self, "remember_editor_form"):
            self.remember_editor_form("enemy", [
                getattr(self, name) for name in (
                    "enemy_name_var", "enemy_sprite_var", "enemy_health_var", "enemy_speed_var",
                    "enemy_ranged_attack_var", "enemy_behavior_var", "enemy_damage_var",
                ) if hasattr(self, name)
            ])
        if refresh:
            self.refresh_enemy_editor()
        if hasattr(self, "draw_area"):
            self.draw_area()
        if hasattr(self, "update_properties_display"):
            self.update_properties_display()
        return True

    def sync_saved_enemy_instances(self, enemy_id, definition):
        area_paths = [
            self._project_path("areas", filename)
            for filename in self.current_game.areas
        ]
        current_file = getattr(self, "current_area_file", None)
        if current_file and os.path.realpath(current_file) not in {
            os.path.realpath(path) for path in area_paths
        }:
            area_paths.append(current_file)

        updates = []
        for area_path in area_paths:
            if not os.path.isfile(area_path):
                continue
            with open(area_path, "r") as area_file:
                area_data = json.load(area_file)
            changed = False
            for instance in area_data.get("objects", []):
                properties = instance.get("properties") or {}
                if properties.get("enemy_id") != enemy_id:
                    continue
                instance["type"] = definition["sprite"]
                properties["enemy_data"] = deepcopy(definition)
                properties["walkable"] = False
                instance["properties"] = properties
                changed = True
            if changed:
                updates.append((area_path, area_data))

        for area_path, area_data in updates:
            with open(area_path, "w") as area_file:
                json.dump(area_data, area_file, indent=2)

    def sync_enemy_instances(self, area=None):
        definitions = self.get_enemy_definitions()
        area = area or self.current_area
        for obj in area.objects:
            enemy_id = obj.properties.get("enemy_id")
            enemy_data = obj.properties.get("enemy_data")
            if isinstance(enemy_data, dict):
                enemy_data.pop("dead_sprite", None)
            definition = definitions.get(enemy_id)
            if definition:
                obj.type = definition["sprite"]
                obj.properties["enemy_data"] = deepcopy(definition)
                obj.properties["walkable"] = False

    def enemy_definition_for_instance(self, obj):
        enemy_id = obj.properties.get("enemy_id")
        return (
            self.get_enemy_definitions().get(enemy_id)
            or obj.properties.get("enemy_data")
        )

    def is_enemy_instance(self, obj):
        return "enemy_id" in obj.properties or "enemy_data" in obj.properties

    def place_selected_enemy(self):
        definition = self._enemy_definition(
            getattr(self, "selected_enemy_id", None)
        )
        if not definition:
            messagebox.showwarning(
                "Place Enemy", "Create or select an enemy definition first."
            )
            return False
        if any(
            self.is_enemy_instance(obj)
            and obj.x == self.cursor_x
            and obj.y == self.cursor_y
            for obj in self.current_area.objects
        ):
            messagebox.showwarning(
                "Place Enemy", "Only one enemy can occupy a map tile."
            )
            return False
        enemy_data = deepcopy(definition)
        self.current_area.objects.append(GameObject(
            type=definition["sprite"],
            x=self.cursor_x,
            y=self.cursor_y,
            properties={
                "enemy_id": self.selected_enemy_id,
                "enemy_data": enemy_data,
                "walkable": False,
            },
        ))
        return True

    def remove_enemies_at_cursor(self):
        original_count = len(self.current_area.objects)
        self.current_area.objects = [
            obj for obj in self.current_area.objects
            if not (
                self.is_enemy_instance(obj)
                and obj.x == self.cursor_x
                and obj.y == self.cursor_y
            )
        ]
        return len(self.current_area.objects) != original_count
