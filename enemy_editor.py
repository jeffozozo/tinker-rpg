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

        ttk.Button(self.enemy_controls_frame, text="Manage Enemies…", command=self.open_enemy_manager).pack(fill=tk.X, padx=5, pady=3)
        self.enemy_controls_frame.pack_forget()

    def setup_enemy_properties(self, parent):
        self.enemy_properties_frame = ttk.LabelFrame(parent, text="Enemy at Cursor")
        self.enemy_summary_label = ttk.Label(self.enemy_properties_frame, wraplength=260, justify=tk.LEFT)
        self.enemy_summary_label.pack(anchor=tk.W, padx=5, pady=5)
        ttk.Button(self.enemy_properties_frame, text="Edit Enemy Type…", command=self.edit_selected_enemy_type).pack(anchor=tk.W, padx=5, pady=3)
        self._enemy_loot_choices()
        self.enemy_instance_frame = ttk.LabelFrame(self.enemy_properties_frame, text="This instance")
        self.enemy_instance_frame.pack(fill=tk.X, padx=3, pady=3)
        self.enemy_instance_label = ttk.Label(self.enemy_instance_frame, text="Select a placed enemy with the map cursor.", wraplength=260)
        self.enemy_instance_label.pack(anchor=tk.W, padx=5, pady=3)
        self.enemy_instance_loot_var = tk.StringVar()
        self.enemy_instance_loot_selector = ttk.Combobox(
            self.enemy_instance_frame, textvariable=self.enemy_instance_loot_var,
            state="disabled", width=27)
        self.enemy_instance_loot_selector.pack(fill=tk.X, padx=5, pady=3)
        self.enemy_instance_loot_selector.bind("<<ComboboxSelected>>", self.save_enemy_instance_loot)
        ttk.Label(self.enemy_instance_frame, text="Use This Game to follow type changes. None means this enemy drops nothing. Instance changes are saved with the area.", wraplength=260).pack(anchor=tk.W, padx=5, pady=3)
        self.enemy_properties_frame.pack_forget()

    def setup_enemy_definition_fields(self, parent):
        self.enemy_properties_frame = parent
        self.enemy_global_frame = parent
        self.enemy_name_var = tk.StringVar()
        self.enemy_sprite_var = tk.StringVar()
        self.enemy_health_var = tk.StringVar()
        self.enemy_speed_var = tk.StringVar()
        # Retain old values for compatible saves; no unsupported control is shown.
        self.enemy_ranged_attack_var = tk.StringVar()
        self.enemy_behavior_var = tk.StringVar()
        self.enemy_damage_var = tk.StringVar()
        self.enemy_loot_var = tk.StringVar()
        self.enemy_sprite_selector = None

        self._enemy_field("Name:", self.enemy_name_var)
        self.enemy_sprite_selector = self._enemy_choice(
            "Live icon:", self.enemy_sprite_var, self._available_enemy_sprites()
        )
        self._enemy_field("Health:", self.enemy_health_var)
        self._enemy_field("Movement speed (tiles/turn):", self.enemy_speed_var)
        self._enemy_choice("Behavior:", self.enemy_behavior_var, ("stationary", "chase"))
        self._enemy_field("Contact damage:", self.enemy_damage_var)
        self.enemy_loot_selector = self._enemy_choice(
            "Loot object:", self.enemy_loot_var, self._enemy_loot_choices()
        )
        ttk.Label(
            self.enemy_global_frame,
            text="Defeated enemies leave this object where they fall. Applies to every instance of this enemy type in this game.",
            wraplength=260,
        ).pack(anchor=tk.W, padx=5, pady=2)
    def _enemy_field(self, label, variable):
        row = ttk.Frame(getattr(self, "enemy_global_frame", self.enemy_properties_frame))
        row.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(row, text=label).pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=variable, width=12).pack(side=tk.RIGHT)

    def _enemy_choice(self, label, variable, values):
        row = ttk.Frame(getattr(self, "enemy_global_frame", self.enemy_properties_frame))
        row.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(row, text=label).pack(side=tk.LEFT)
        selector = ttk.Combobox(
            row, textvariable=variable, values=values, state="readonly", width=13
        )
        selector.pack(side=tk.RIGHT)
        return selector

    def open_enemy_manager(self, enemy_id=None):
        manager = getattr(self, '_enemy_manager', None)
        if manager is not None and manager.window.winfo_exists():
            manager.window.lift()
            if enemy_id and manager.confirm_draft():
                manager.load(enemy_id)
            return
        from enemy_manager import EnemyManager
        self._enemy_manager = EnemyManager(self, enemy_id)

    def edit_selected_enemy_type(self):
        obj = self.enemy_at_cursor()
        enemy_id = obj.properties.get('enemy_id') if obj else self.selected_enemy_id
        self.open_enemy_manager(enemy_id)

    def finish_enemy_edit(self):
        manager = getattr(self, '_enemy_manager', None)
        return manager.close() if manager is not None and manager.window.winfo_exists() else True

    def refresh_enemy_summary(self):
        if not hasattr(self, 'enemy_summary_label'):
            return
        obj = self.enemy_at_cursor()
        definition = self.enemy_definition_for_instance(obj) if obj else self._enemy_definition(self.selected_enemy_id)
        if not definition:
            self.enemy_summary_label.configure(text='Select an enemy type to place, or select an enemy on the map.')
            return
        loot = definition.get('loot_object', '')
        label = next((label for label, value in self._enemy_loot_labels.items() if value == loot), loot or 'None')
        self.enemy_summary_label.configure(text=(
            f"{definition.get('name', 'Enemy')}\n"
            f"Health: {definition.get('health', 10)}   Damage: {definition.get('contact_damage', 1)}\n"
            f"Behavior: {definition.get('behavior', 'stationary')}\n"
            f"Speed: {definition.get('movement_speed', 1)} tiles/turn\n"
            f"Type loot: {label}\nEdit the type in Enemies → Manage Enemies…"))

    def enemy_definition_usage(self, enemy_id):
        from dataclasses import asdict
        current = getattr(self, 'current_area_file', None)
        sources = [(os.path.basename(current) if current else 'Current area', asdict(self.current_area))]
        for name in self.current_game.areas:
            path = self._project_path('areas', name)
            if current and os.path.realpath(path) == os.path.realpath(current):
                continue
            try:
                with open(path) as file:
                    sources.append((name, json.load(file)))
            except (OSError, ValueError):
                sources.append((name, {'objects': [{'x': '?', 'y': '?', 'properties': {'enemy_id': enemy_id}}]}))
        usages = [f"{name} ({obj['x']}, {obj['y']})" for name, area in sources
                  for obj in area.get('objects', []) if obj.get('properties', {}).get('enemy_id') == enemy_id]
        for name, area in sources:
            for trigger in area.get('triggers', []):
                if trigger.get('trigger_type') == 'enemy_placement' and trigger.get('parameters', {}).get('enemy_id') == enemy_id:
                    usages.append(f"{name}: Enemy Placement trigger")
        for definition in self.current_game.properties.get('trigger_definitions', {}).values():
            if definition.get('trigger_type') == 'enemy_placement' and definition.get('parameters', {}).get('enemy_id') == enemy_id:
                usages.append(f"{definition['name']}: named Enemy Placement trigger")
        return usages

    def _available_enemy_sprites(self):
        return tuple(self.tile_manager.get_npc_names())

    def _enemy_loot_choices(self):
        self._enemy_loot_labels = {"None": ""}
        for name in sorted(self.tile_manager.get_object_names()):
            label = name.removesuffix("_object").replace("_", " ").title()
            self._enemy_loot_labels[label] = name
        return tuple(self._enemy_loot_labels)

    def enemy_at_cursor(self):
        return next((obj for obj in self.current_area.objects
                     if (obj.x, obj.y) == (self.cursor_x, self.cursor_y)
                     and self.is_enemy_instance(obj)), None)

    def select_enemy_at_cursor(self):
        if getattr(self, "_selecting_enemy_cursor", False):
            return
        obj = self.enemy_at_cursor()
        if obj is None:
            return
        enemy_id = obj.properties.get("enemy_id")
        if enemy_id == self.selected_enemy_id or enemy_id not in self.get_enemy_definitions():
            return
        self._selecting_enemy_cursor = True
        try:
            if self.selected_enemy_id and not self.save_enemy_definition(refresh=False):
                return
            self.selected_enemy_id = enemy_id
        finally:
            self._selecting_enemy_cursor = False

    def refresh_enemy_instance_editor(self):
        if not hasattr(self, "enemy_instance_loot_selector"):
            return
        self._enemy_loot_choices()
        self.refresh_enemy_summary()
        obj = self.enemy_at_cursor()
        if obj is None:
            self.enemy_instance_label.config(text="Select a placed enemy with the map cursor.")
            self.enemy_instance_loot_var.set("")
            self.enemy_instance_loot_selector.config(state="disabled")
            return
        definition = self.enemy_definition_for_instance(obj) or {}
        global_loot = definition.get("loot_object", "")
        label = next((label for label, value in self._enemy_loot_labels.items() if value == global_loot), global_loot or "None")
        inherit_label = f"Use This Game ({label})"
        self._instance_loot_labels = {inherit_label: None, **self._enemy_loot_labels}
        override = obj.properties.get("loot_object_override")
        if override is not None and override not in self._instance_loot_labels.values():
            self._instance_loot_labels[f"Missing: {override}"] = override
        self.enemy_instance_label.config(text=f"{definition.get('name', obj.type)} at ({obj.x}, {obj.y}) — Loot object:")
        self.enemy_instance_loot_selector.config(values=tuple(self._instance_loot_labels), state="readonly")
        self.enemy_instance_loot_var.set(next(label for label, value in self._instance_loot_labels.items() if value == override))

    def save_enemy_instance_loot(self, event=None):
        obj = self.enemy_at_cursor()
        if obj is None:
            return
        label = self.enemy_instance_loot_var.get()
        if label not in self._instance_loot_labels:
            return
        override = self._instance_loot_labels[label]
        if override is None:
            obj.properties.pop("loot_object_override", None)
        else:
            obj.properties["loot_object_override"] = override
        self.refresh_enemy_instance_editor()

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
            "loot_object": "",
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
        if getattr(self, "enemy_loot_selector", None) is not None:
            self.enemy_loot_selector.configure(values=self._enemy_loot_choices())
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
            if hasattr(self, "enemy_loot_var"):
                self.enemy_loot_var.set("None")
        self.refresh_enemy_instance_editor()
        if hasattr(self, "tile_canvas"):
            self.update_tile_display()

    def _load_enemy_fields(self, definition):
        self._enemy_loaded_id = self.selected_enemy_id
        if not hasattr(self, "enemy_name_var"):
            return
        if hasattr(self, "enemy_loot_var"):
            loot = definition.get("loot_object", "")
            labels = self._enemy_loot_labels
            if loot and loot not in labels.values():
                labels[f"Missing: {loot}"] = loot
                self.enemy_loot_selector.configure(values=tuple(labels))
            self.enemy_loot_var.set(next(label for label, value in labels.items() if value == loot))
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
                    "enemy_ranged_attack_var", "enemy_behavior_var", "enemy_damage_var", "enemy_loot_var",
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
        self.refresh_enemy_instance_editor()

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

        loot = definition.get("loot_object", "")
        if hasattr(self, "enemy_loot_var"):
            loot = self._enemy_loot_labels.get(self.enemy_loot_var.get())
            if loot is None or (loot and loot not in self.tile_manager.get_object_names()):
                messagebox.showerror("Invalid Enemy", "Choose an available loot object or None.")
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
            "loot_object": loot,
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
                    "enemy_ranged_attack_var", "enemy_behavior_var", "enemy_damage_var", "enemy_loot_var",
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
                "enemy_instance_id": f"enemy_instance_{uuid4().hex}",
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
