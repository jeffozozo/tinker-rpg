"""Game loading and turn-based state for the Tinker runner."""

import json
import math
from collections import deque
import os
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

from PIL import Image

from data_classes import (
    MAX_AREA_DIMENSION,
    MAX_PLAYER_INVENTORY_SLOTS,
    PLAYER_STAT_CHANGES,
    Area,
    GameObject,
    Game,
    Tile,
    Trigger,
)
from project_paths import asset_root as get_asset_root
from project_paths import project_root as get_project_root
from item_rules import EQUIPMENT_SLOTS, compatible_slot, validate_item
from tile_manager import default_tile_walkable


TRIGGER_TYPES = {
    "teleport",
    "inventory",
    "player_stats",
    "tile_update",
    "area_object",
    "game_end",
    "show_message",
    "custom",
}
DIRECTIONS = {
    "up": (0, -1),
    "down": (0, 1),
    "left": (-1, 0),
    "right": (1, 0),
}


class RunnerError(ValueError):
    """Raised when a game cannot be loaded safely."""


def resolve_game_path(game_argument, cwd=None, project_root=None):
    cwd = Path(cwd or os.getcwd()).resolve()
    project_root = Path(project_root or get_project_root()).resolve()
    supplied = Path(game_argument).expanduser()

    def candidates_in(directory, name):
        candidate = directory / name
        candidates = [candidate]
        if candidate.suffix.lower() != ".json":
            candidates.append(Path(f"{candidate}.json"))
        return [path.resolve() for path in candidates if path.is_file()]

    is_path = supplied.is_absolute() or len(supplied.parts) > 1
    if is_path or supplied.exists():
        found = candidates_in(cwd, supplied) if not supplied.is_absolute() else (
            [supplied.resolve()] if supplied.is_file() else
            [Path(f"{supplied}.json").resolve()]
            if supplied.suffix.lower() != ".json"
            and Path(f"{supplied}.json").is_file() else []
        )
        if len(found) == 1:
            return found[0]
        if len(found) > 1:
            raise RunnerError(
                "Game path is ambiguous: " + ", ".join(str(path) for path in found)
            )
        attempts = [str(cwd / supplied)]
        if supplied.suffix.lower() != ".json":
            attempts.append(str(Path(f"{cwd / supplied}.json")))
        raise RunnerError(
            f"Game file not found: {game_argument}. Tried: " + ", ".join(attempts)
        )

    matches = []
    for directory in (cwd, project_root / "games"):
        matches.extend(candidates_in(directory, supplied.name))
    unique_matches = list(dict.fromkeys(matches))
    if len(unique_matches) == 1:
        return unique_matches[0]
    if len(unique_matches) > 1:
        raise RunnerError(
            "Game name is ambiguous; pass a path. Matches: "
            + ", ".join(str(path) for path in unique_matches)
        )
    tried = [
        str(cwd / supplied.name),
        str(cwd / f"{supplied.name}.json")
        if supplied.suffix.lower() != ".json"
        else str(cwd / supplied.name),
        str(project_root / "games" / supplied.name),
        str(project_root / "games" / f"{supplied.name}.json")
        if supplied.suffix.lower() != ".json"
        else str(project_root / "games" / supplied.name),
    ]
    raise RunnerError(
        f"Game not found: {game_argument}. Tried: " + ", ".join(tried)
    )


class RunnerEngine:
    """Validated game data plus the mutable state for one play session."""

    def __init__(self, game_argument, project_root=None, dialog_handler=None):
        self.project_root = Path(project_root or get_project_root()).resolve()
        self.asset_root = (
            Path(project_root).resolve()
            if project_root is not None and not getattr(sys, "frozen", False)
            else get_asset_root()
        )
        self.game_path = resolve_game_path(
            game_argument, project_root=self.project_root
        )
        self._initialize_runtime(dialog_handler)
        self.game = self._read_json(self.game_path, "game")
        self._configure_game()
        self.area_paths = self._resolve_area_paths()
        self.areas = {
            filename: self._load_area(path)
            for filename, path in self.area_paths.items()
        }
        self._finish_game_load()

    def _initialize_runtime(self, dialog_handler=None):
        self.dialog_handler = dialog_handler
        self.events = []
        self.feedback = []
        self.validation_issues = []
        self.facing = "down"
        self.turn_count = 0
        self.ended = False
        self.end_result = None
        self.tile_names = self._asset_names("tiles")
        self.object_names = self._asset_names("objects")
        self.npc_names = self._asset_names("npcs")

    def _configure_game(self):
        if not isinstance(self.game, dict):
            raise RunnerError(f"{self.game_path}: game data must be an object.")
        if not isinstance(self.game.get("name", "Untitled Game"), str):
            raise RunnerError(f"{self.game_path}: game name must be text.")
        for field in ("intro_message", "instructions_message", "game_end_message"):
            if not isinstance(self.game.get(field, ""), str):
                raise RunnerError(f"{self.game_path}: {field} must be text.")
        if not isinstance(self.game.get("areas", []), list):
            raise RunnerError(f"{self.game_path}: areas must be a list.")
        used_objects = self.game.get("used_objects", [])
        if not isinstance(used_objects, list) or any(
            not isinstance(item, str) for item in used_objects
        ):
            raise RunnerError(f"{self.game_path}: used_objects must be a list of IDs.")
        self.used_objects = set(used_objects)
        self.properties = self.game.setdefault("properties", {})
        if not isinstance(self.properties, dict):
            raise RunnerError(f"{self.game_path}: properties must be an object.")
        self.object_definitions = self.game.get("object_definitions", {})
        if not isinstance(self.object_definitions, dict):
            raise RunnerError(
                f"{self.game_path}: object_definitions must be an object."
            )
        for object_type, definition in self.object_definitions.items():
            if not isinstance(object_type, str) or not isinstance(definition, dict):
                raise RunnerError(
                    f"{self.game_path}: each object definition must be an object "
                    "keyed by its object ID."
                )
            try:
                validate_item(self._item_definition(object_type))
                if definition.get("ammo_item") == object_type:
                    raise ValueError("A weapon cannot use itself as ammunition.")
            except ValueError as error:
                raise RunnerError(f"{self.game_path}: {object_type}: {error}") from error
            if "walkable" in definition and type(definition["walkable"]) is not bool:
                raise RunnerError(
                    f"{self.game_path}: {object_type}.walkable must be true or false."
                )

    def _finish_game_load(self, set_start=True):
        self.area_names = self._index_area_names()
        self._load_player()
        if set_start:
            self._set_start_position()
        for area in self.areas.values():
            for obj in area.objects:
                definition = self._enemy_definition(obj)
                if definition is None:
                    continue
                speed = definition.get("movement_speed", 1.0)
                damage = definition.get("contact_damage", 1)
                health = definition.get("health", 10)
                if (type(speed) not in (int, float) or not math.isfinite(speed) or speed < 0
                        or type(damage) is not int or damage < 0
                        or type(health) is not int or health < 1
                        or definition.get("behavior", "stationary") not in ("stationary", "chase")):
                    raise RunnerError(f"Invalid movement or combat settings for enemy {obj.type!r}.")
                remaining = obj.properties.get("enemy_health", health)
                credit = obj.properties.get("movement_credit", 0.0)
                if (type(remaining) is not int or not 0 <= remaining <= health
                        or type(credit) not in (int, float) or not math.isfinite(credit)
                        or not 0 <= credit < 1):
                    raise RunnerError(f"Invalid saved combat state for enemy {obj.type!r}.")
        self._validate_trigger_references()
        self._validate_asset_references()

    def save_to_file(self, filename, save_name):
        filename = Path(filename).expanduser().resolve()
        if not isinstance(save_name, str) or not save_name.strip():
            raise RunnerError("Save name cannot be empty.")
        data = {
            "format_version": 1,
            "save_name": save_name.strip(),
            "source_game_path": str(self.game_path),
            "game": self.game,
            "areas": {
                name: asdict(area) for name, area in self.areas.items()
            },
            "current_area": self.current_area_filename,
            "player": {
                "x": self.player_x,
                "y": self.player_y,
                "health": self.health,
                "energy": self.energy,
                "gold": self.stats["gold"],
                "stats": {key: self.stats[key] for key in ("max_health", "max_energy", "strength", "intelligence")},
                "inventory": self.inventory,
                "equipment": self.equipment,
                "active_items": sorted(self.active_items),
                "facing": self.facing,
            },
            "turn_count": self.turn_count,
            "ended": self.ended,
            "end_result": self.end_result,
        }
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=filename.parent,
                prefix=f".{filename.name}.",
                suffix=".tmp",
                delete=False,
            ) as save_file:
                temporary_path = Path(save_file.name)
                json.dump(data, save_file, indent=2)
            os.replace(temporary_path, filename)
        except (OSError, TypeError, ValueError) as error:
            if temporary_path is not None:
                try:
                    temporary_path.unlink()
                except FileNotFoundError:
                    pass
            raise RunnerError(f"Could not save game to {filename}: {error}") from error
        return filename

    @classmethod
    def load_save(cls, filename, project_root=None, dialog_handler=None):
        save_path = Path(filename).expanduser().resolve()
        data = cls._read_json(save_path, "saved game")
        if not isinstance(data, dict) or data.get("format_version") != 1:
            raise RunnerError(
                f"{save_path}: unsupported or invalid saved-game format."
            )
        save_name = data.get("save_name")
        game = data.get("game")
        areas_data = data.get("areas")
        if not isinstance(save_name, str) or not save_name.strip():
            raise RunnerError(f"{save_path}: save_name must be non-empty text.")
        if not isinstance(game, dict):
            raise RunnerError(f"{save_path}: game snapshot must be an object.")
        if not isinstance(areas_data, dict):
            raise RunnerError(f"{save_path}: area snapshots must be an object.")

        engine = cls.__new__(cls)
        engine.project_root = Path(project_root or get_project_root()).resolve()
        engine.asset_root = (
            Path(project_root).resolve()
            if project_root is not None and not getattr(sys, "frozen", False)
            else get_asset_root()
        )
        source_game_path = data.get("source_game_path", "")
        engine.game_path = (
            Path(source_game_path)
            if isinstance(source_game_path, str) and source_game_path
            else save_path
        )
        engine._initialize_runtime(dialog_handler)
        engine.game = game
        engine._configure_game()
        area_references = engine.game.get("areas", [])
        if (
            any(not isinstance(reference, str) for reference in area_references)
            or len(set(area_references)) != len(area_references)
        ):
            raise RunnerError(f"{save_path}: game area references are invalid.")
        if set(areas_data) != set(area_references):
            raise RunnerError(
                f"{save_path}: saved area snapshots do not match game area references."
            )
        engine.area_paths = {
            filename: engine.project_root / "areas" / filename
            for filename in area_references
        }
        engine.areas = {}
        for filename in area_references:
            area_data = areas_data[filename]
            if not isinstance(area_data, dict):
                raise RunnerError(
                    f"{save_path}: snapshot for area {filename!r} must be an object."
                )
            engine.areas[filename] = engine._parse_area_data(
                area_data, engine.area_paths[filename]
            )
        engine._finish_game_load(set_start=False)

        current_area = data.get("current_area")
        if not isinstance(current_area, str) or current_area not in engine.areas:
            raise RunnerError(f"{save_path}: current_area is not in this game.")
        player_state = data.get("player")
        if not isinstance(player_state, dict):
            raise RunnerError(f"{save_path}: player state must be an object.")
        engine.current_area_filename = current_area
        engine.current_area = engine.areas[current_area]
        engine.player_x = player_state.get("x")
        engine.player_y = player_state.get("y")
        if (
            type(engine.player_x) is not int
            or type(engine.player_y) is not int
            or not (0 <= engine.player_x < engine.current_area.width
                    and 0 <= engine.player_y < engine.current_area.height)
        ):
            raise RunnerError(
                f"{save_path}: saved player position is out of bounds."
            )

        runtime_stats = player_state.get("stats", {})
        allowed = {"max_health", "max_energy", "strength", "intelligence"}
        if not isinstance(runtime_stats, dict) or set(runtime_stats) - allowed:
            raise RunnerError(f"{save_path}: invalid saved player stats.")
        for key, value in runtime_stats.items():
            if type(value) is not int or value < (1 if key == "max_health" else 0):
                raise RunnerError(f"{save_path}: invalid saved player stat {key}.")
        engine.stats.update(runtime_stats)

        for field, minimum, maximum in (
            ("health", 0, engine.stats["max_health"]),
            ("energy", 0, engine.stats["max_energy"]),
        ):
            value = player_state.get(field)
            if type(value) is not int or not minimum <= value <= maximum:
                raise RunnerError(
                    f"{save_path}: saved player {field} is outside its valid range."
                )
            setattr(engine, field, value)
        gold = player_state.get("gold")
        if type(gold) is not int or gold < 0:
            raise RunnerError(f"{save_path}: saved player gold must be non-negative.")
        engine.stats["gold"] = gold

        inventory = player_state.get("inventory")
        if (
            not isinstance(inventory, list)
            or len(inventory) != MAX_PLAYER_INVENTORY_SLOTS
            or any(not isinstance(item, str) for item in inventory)
        ):
            raise RunnerError(
                f"{save_path}: saved inventory must contain exactly "
                f"{MAX_PLAYER_INVENTORY_SLOTS} text slots."
            )
        engine.inventory = inventory
        engine._load_equipment(player_state.get("equipment", {}))
        active = player_state.get("active_items", [])
        if (not isinstance(active, list) or any(type(index) is not int
                or index not in engine.equipment.values()
                or engine._item_definition(engine.inventory[index])["item_type"] != "toggle"
                for index in active)):
            raise RunnerError("Invalid saved active items.")
        engine.active_items = set(active)
        engine.facing = player_state.get("facing", "down")
        if engine.facing not in DIRECTIONS:
            raise RunnerError("Invalid saved facing direction.")
        turn_count = data.get("turn_count")
        if type(turn_count) is not int or turn_count < 0:
            raise RunnerError(f"{save_path}: turn_count must be a non-negative integer.")
        engine.turn_count = turn_count
        ended = data.get("ended", False)
        end_result = data.get("end_result")
        if type(ended) is not bool or end_result not in (None, "win", "lose"):
            raise RunnerError(f"{save_path}: invalid end-of-game state.")
        if ended != (end_result is not None):
            raise RunnerError(f"{save_path}: ended and end_result do not agree.")
        engine.ended = ended
        engine.end_result = end_result
        engine.save_name = save_name.strip()
        return engine

    def _asset_names(self, category):
        directory = self.asset_root / category
        return {
            path.stem for path in directory.glob("*.png")
        } if directory.is_dir() else set()

    @staticmethod
    def _read_json(path, description):
        try:
            with open(path, "r", encoding="utf-8") as file:
                return json.load(file)
        except (OSError, json.JSONDecodeError) as error:
            raise RunnerError(f"Could not load {description} {path}: {error}") from error

    def _resolve_area_paths(self):
        stored_areas = self.game.get("areas", [])
        if not stored_areas:
            raise RunnerError(f"{self.game_path}: game has no areas.")

        try:
            self.game_path.relative_to(self.project_root)
            is_project_game = True
        except ValueError:
            is_project_game = False
        area_directories = (
            [self.project_root / "areas"]
            if is_project_game
            else [self.game_path.parent / "areas", self.project_root / "areas"]
        )

        paths = {}
        for area_reference in stored_areas:
            if not isinstance(area_reference, str) or not area_reference:
                raise RunnerError(
                    f"{self.game_path}: every area reference must be a filename."
                )
            filename = Path(area_reference).name
            if filename != area_reference or filename in {".", ".."}:
                raise RunnerError(
                    f"{self.game_path}: area reference must be a filename, "
                    f"not a path: {area_reference!r}."
                )
            area_path = next(
                (
                    directory / filename
                    for directory in area_directories
                    if (directory / filename).is_file()
                ),
                None,
            )
            if area_path is None:
                tried = ", ".join(str(directory / filename) for directory in area_directories)
                raise RunnerError(
                    f"{self.game_path}: area {filename!r} was not found. Tried: {tried}"
                )
            if filename in paths:
                raise RunnerError(
                    f"{self.game_path}: duplicate area reference {filename!r}."
                )
            paths[filename] = area_path.resolve()
        return paths

    def _load_area(self, path):
        data = self._read_json(path, "area")
        return self._parse_area_data(data, path)

    def _parse_area_data(self, data, path):
        if not isinstance(data, dict):
            raise RunnerError(f"{path}: area data must be an object.")
        if not isinstance(data.get("name", path.stem), str):
            raise RunnerError(f"{path}: area name must be text.")
        width, height = data.get("width"), data.get("height")
        if (
            type(width) is not int
            or type(height) is not int
            or not (1 <= width <= MAX_AREA_DIMENSION)
            or not (1 <= height <= MAX_AREA_DIMENSION)
        ):
            raise RunnerError(
                f"{path}: width and height must be integers between 1 and "
                f"{MAX_AREA_DIMENSION}."
            )
        raw_tiles = data.get("tiles")
        if not isinstance(raw_tiles, list) or len(raw_tiles) != height:
            raise RunnerError(f"{path}: tiles must contain exactly {height} rows.")
        tiles = []
        for y, row in enumerate(raw_tiles):
            if not isinstance(row, list) or len(row) != width:
                raise RunnerError(
                    f"{path}: tile row {y} must contain exactly {width} tiles."
                )
            parsed_row = []
            for x, tile_data in enumerate(row):
                if isinstance(tile_data, str):
                    tile_data = {"type": tile_data}
                if not isinstance(tile_data, dict):
                    raise RunnerError(f"{path}: tile ({x},{y}) must be an object.")
                tile_type = tile_data.get("type", "empty")
                override = tile_data.get("walkable_override")
                if not isinstance(tile_type, str) or (
                    override is not None and type(override) is not bool
                ):
                    raise RunnerError(f"{path}: invalid tile data at ({x},{y}).")
                tile_properties = tile_data.get("properties", {})
                if tile_properties is None:
                    tile_properties = {}
                if not isinstance(tile_properties, dict):
                    raise RunnerError(
                        f"{path}: tile ({x},{y}) properties must be an object."
                    )
                parsed_row.append(Tile(
                    type=tile_type,
                    walkable_override=override,
                    properties=tile_properties,
                ))
            tiles.append(parsed_row)

        raw_objects = data.get("objects", [])
        if not isinstance(raw_objects, list):
            raise RunnerError(f"{path}: objects must be a list.")
        objects = []
        for index, object_data in enumerate(raw_objects):
            if not isinstance(object_data, dict):
                raise RunnerError(f"{path}: object {index + 1} must be an object.")
            x, y = object_data.get("x"), object_data.get("y")
            object_type = object_data.get("type")
            if (
                type(x) is not int
                or type(y) is not int
                or not (0 <= x < width and 0 <= y < height)
                or not isinstance(object_type, str)
                or not object_type
            ):
                raise RunnerError(f"{path}: object {index + 1} has invalid type or coordinates.")
            properties = object_data.get("properties", {})
            if properties is None:
                properties = {}
            if not isinstance(properties, dict):
                raise RunnerError(f"{path}: object {index + 1} properties must be an object.")
            if (
                "walkable" in properties
                and type(properties["walkable"]) is not bool
            ):
                raise RunnerError(
                    f"{path}: object {index + 1} walkable must be true or false."
                )
            objects.append(GameObject(object_type, x, y, properties))

        raw_triggers = data.get("triggers", [])
        if not isinstance(raw_triggers, list):
            raise RunnerError(f"{path}: triggers must be a list.")
        triggers = []
        for index, trigger_data in enumerate(raw_triggers):
            if not isinstance(trigger_data, dict):
                raise RunnerError(f"{path}: trigger {index + 1} must be an object.")
            try:
                trigger = Trigger(**trigger_data)
            except (TypeError, ValueError) as error:
                raise RunnerError(f"{path}: invalid trigger {index + 1}: {error}") from error
            if (
                type(trigger.x) is not int
                or type(trigger.y) is not int
                or not (0 <= trigger.x < width and 0 <= trigger.y < height)
            ):
                raise RunnerError(
                    f"{path}: trigger {trigger.name!r} has out-of-bounds coordinates."
                )
            if not isinstance(trigger.trigger_type, str) or (
                trigger.trigger_type not in TRIGGER_TYPES
            ):
                raise RunnerError(
                    f"{path}: trigger {trigger.name!r} has unsupported type "
                    f"{trigger.trigger_type!r}."
                )
            if not isinstance(trigger.name, str):
                raise RunnerError(f"{path}: trigger {index + 1} name must be text.")
            if not isinstance(trigger.parameters, dict):
                raise RunnerError(
                    f"{path}: trigger {trigger.name!r} parameters must be an object."
                )
            triggers.append(trigger)
        return Area(
            name=data.get("name", path.stem),
            width=width,
            height=height,
            tiles=tiles,
            objects=objects,
            triggers=triggers,
        )

    def _index_area_names(self):
        indexed = {}
        for filename in self.areas:
            stem = Path(filename).stem
            indexed.setdefault(stem, []).append(filename)
            indexed[filename] = [filename]
        return indexed

    def area_filename(self, reference):
        if not isinstance(reference, str) or not reference:
            raise RunnerError("Area name is missing.")
        if reference in self.areas:
            return reference
        stem = Path(reference).stem
        matches = self.area_names.get(stem, [])
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise RunnerError(f"Area name {reference!r} is ambiguous.")
        raise RunnerError(f"Area {reference!r} is not included in this game.")

    def _load_player(self):
        player = self.properties.get("player", {})
        if not isinstance(player, dict):
            raise RunnerError(f"{self.game_path}: properties.player must be an object.")
        self.player_settings = player
        if not isinstance(player.get("sprite", "fighter_npc"), str):
            raise RunnerError(f"{self.game_path}: player.sprite must be text.")
        raw_stats = player.get("stats", {})
        if not isinstance(raw_stats, dict):
            raise RunnerError(f"{self.game_path}: player.stats must be an object.")
        self.stats = {
            "max_health": raw_stats.get("max_health", 20),
            "starting_health": raw_stats.get("starting_health", 20),
            "max_energy": raw_stats.get("max_energy", 0),
            "starting_energy": raw_stats.get("starting_energy", 0),
            "strength": raw_stats.get("strength", 1),
            "intelligence": raw_stats.get("intelligence", 1),
            "gold": raw_stats.get("gold", 0),
        }
        for key, value in self.stats.items():
            if type(value) is not int or value < 0:
                raise RunnerError(
                    f"{self.game_path}: player stat {key} must be a non-negative integer."
                )
        if self.stats["max_health"] < 1:
            raise RunnerError(f"{self.game_path}: player max_health must be positive.")
        if self.stats["starting_health"] < 1:
            raise RunnerError(f"{self.game_path}: player starting_health must be positive.")
        if self.stats["starting_health"] > self.stats["max_health"]:
            raise RunnerError(
                f"{self.game_path}: starting_health cannot exceed max_health."
            )
        if self.stats["starting_energy"] > self.stats["max_energy"]:
            raise RunnerError(
                f"{self.game_path}: starting_energy cannot exceed max_energy."
            )
        self.health = self.stats["starting_health"]
        self.energy = self.stats["starting_energy"]

        inventory = player.get("starting_inventory", [])
        if not isinstance(inventory, list):
            raise RunnerError(
                f"{self.game_path}: player.starting_inventory must be a list."
            )
        if len(inventory) > MAX_PLAYER_INVENTORY_SLOTS:
            raise RunnerError(
                f"{self.game_path}: starting_inventory exceeds the "
                f"{MAX_PLAYER_INVENTORY_SLOTS}-slot limit."
            )
        if any(item is not None and not isinstance(item, str) for item in inventory):
            raise RunnerError(
                f"{self.game_path}: inventory slots must contain item names or be empty."
            )
        self.inventory = [
            item or "" for item in inventory
        ] + [""] * (MAX_PLAYER_INVENTORY_SLOTS - len(inventory))
        known_items = (
            self.object_names
            | self.used_objects
            | set(self.object_definitions)
        )
        for item in self.inventory:
            if item and item not in known_items:
                self._validation_issue(
                    f"Starting inventory item {item!r} has no matching object "
                    "definition or project asset."
                )

        self._load_equipment(player.get("starting_equipment", {}))
        self.active_items = set()

    def _load_equipment(self, equipment):
        if not isinstance(equipment, dict) or set(equipment) - set(EQUIPMENT_SLOTS):
            raise RunnerError("Equipment must contain valid active slots.")
        self.equipment = dict.fromkeys(EQUIPMENT_SLOTS)
        for slot, index in equipment.items():
            if index is None:
                continue
            if (type(index) is not int or not 0 <= index < len(self.inventory)
                    or not self.inventory[index]
                    or compatible_slot(self._item_definition(self.inventory[index])) != slot):
                raise RunnerError(f"Invalid inventory item for equipment slot {slot}.")
            self.equipment[slot] = index

    def _set_start_position(self):
        start_area = self.properties.get("start_area")
        if not start_area:
            raise RunnerError(
                f"{self.game_path}: set properties.start_area in Player mode."
            )
        self.current_area_filename = self.area_filename(start_area)
        self.current_area = self.areas[self.current_area_filename]
        self.player_x = self.properties.get("start_x")
        self.player_y = self.properties.get("start_y")
        if type(self.player_x) is not int or type(self.player_y) is not int:
            raise RunnerError(
                f"{self.game_path}: properties.start_x and start_y must be integers."
            )
        if not (0 <= self.player_x < self.current_area.width
                and 0 <= self.player_y < self.current_area.height):
            raise RunnerError(
                f"{self.game_path}: player start ({self.player_x},{self.player_y}) "
                f"in {self.current_area_filename} is out of bounds."
            )

    @property
    def area_name(self):
        return self.current_area.name

    def _position_is_open(self, area, x, y):
        if not (0 <= x < area.width and 0 <= y < area.height):
            return False
        tile = area.tiles[y][x]
        walkable = (
            tile.walkable_override
            if tile.walkable_override is not None
            else default_tile_walkable(tile.type)
        )
        if not walkable:
            return False
        for obj in area.objects:
            if obj.x != x or obj.y != y:
                continue
            if "enemy_id" in obj.properties or "enemy_data" in obj.properties:
                return False
            if obj.type in self.npc_names:
                if obj.properties.get("walkable", False) is False:
                    return False
                continue
            definition = self._item_definition(obj.type)
            if definition["item_type"] == "openable":
                if not obj.properties.get("open", False):
                    return False
                continue
            default_walkable = (
                definition.get("walkable", True)
                if isinstance(definition, dict)
                else True
            )
            if obj.properties.get("walkable", default_walkable) is False:
                return False
        return True

    def _feedback(self, kind, x, y, damage=0):
        self.feedback.append({
            "kind": kind, "area": self.current_area_filename,
            "x": x, "y": y, "damage": damage,
        })

    def _report(self, message):
        self.events.append(message)

    def _validation_issue(self, message):
        if message not in self.validation_issues:
            self.validation_issues.append(message)
        self._report(message)

    def _dialog(self, message):
        self._report(message)
        if self.dialog_handler is not None:
            self.dialog_handler(message)

    def move(self, direction):
        if self.ended:
            return False
        if direction not in DIRECTIONS:
            self._report(f"Unknown direction: {direction}.")
            return False
        self.facing = direction
        dx, dy = DIRECTIONS[direction]
        target_x, target_y = self.player_x + dx, self.player_y + dy
        if not (0 <= target_x < self.current_area.width and
                0 <= target_y < self.current_area.height):
            self._report("You cannot move beyond the edge of the area.")
            self.wait()
            return False
        if not self._position_is_open(self.current_area, target_x, target_y):
            self._report("That way is blocked.")
            self.wait()
            return False
        self.player_x, self.player_y = target_x, target_y
        self._feedback("step", target_x, target_y)
        self.turn_count += 1
        self.process_entry_triggers()
        self._enemy_turn()
        return True

    def _enemy_definition(self, obj):
        if "enemy_id" not in obj.properties and "enemy_data" not in obj.properties:
            return None
        definitions = self.properties.get("enemies", {})
        if not isinstance(definitions, dict):
            raise RunnerError("Game enemy definitions must be an object.")
        definition = definitions.get(
            obj.properties.get("enemy_id"), obj.properties.get("enemy_data", {})
        )
        if not isinstance(definition, dict):
            raise RunnerError(f"Enemy {obj.type!r} must have an object definition.")
        return definition

    def _chase_step(self, enemy):
        # Breadth-first search keeps routes shortest. Prefer closing the larger
        # axis gap when routes tie, instead of always copying vertical movement.
        start = (enemy.x, enemy.y)
        target = (self.player_x, self.player_y)
        queue = deque([(start, None)])
        visited = {start}
        while queue:
            (x, y), first_step = queue.popleft()
            directions = sorted(
                DIRECTIONS.values(),
                key=lambda delta: (target[0] - x - delta[0]) ** 2
                                  + (target[1] - y - delta[1]) ** 2,
            )
            for dx, dy in directions:
                point = (x + dx, y + dy)
                if point in visited:
                    continue
                step = first_step or point
                if point == target:
                    return step
                if self._position_is_open(self.current_area, *point):
                    visited.add(point)
                    queue.append((point, step))
        return None

    def _enemy_turn(self):
        if self.ended:
            return
        for enemy in list(self.current_area.objects):
            definition = self._enemy_definition(enemy)
            if definition is None:
                continue
            health = enemy.properties.setdefault("enemy_health", definition.get("health", 10))
            if health <= 0:
                self.current_area.objects.remove(enemy)
                continue
            if definition.get("behavior", "stationary") != "chase":
                continue
            speed = definition.get("movement_speed", 1.0)
            credit = enemy.properties.get("movement_credit", 0.0) + speed
            steps = int(credit)
            enemy.properties["movement_credit"] = credit - steps
            # More than the map size cannot improve a shortest chase this turn.
            for _ in range(min(steps, self.current_area.width * self.current_area.height)):
                if (enemy.x, enemy.y) == (self.player_x, self.player_y):
                    break
                step = self._chase_step(enemy)
                if step is None:
                    break
                if step == (self.player_x, self.player_y):
                    break
                enemy.x, enemy.y = step
            if abs(enemy.x - self.player_x) + abs(enemy.y - self.player_y) <= 1:
                damage = max(0, definition.get("contact_damage", 1) - self.armor())
                self.health = max(0, self.health - damage)
                self._feedback("hurt", self.player_x, self.player_y, damage)
                self._report(f"{definition.get('name', enemy.type)} hits you for {damage} damage.")
                if self.health == 0:
                    self.ended = True
                    self.end_result = "lose"
                    self._dialog("Game over. You have died.")
                    return

    def wait(self):
        if self.ended:
            return False
        self.turn_count += 1
        self._enemy_turn()
        return True

    def _item_definition(self, item):
        return Game(object_definitions=self.object_definitions).get_object_definition(item)

    def equip(self, index, slot=None):
        if self.ended or type(index) is not int or not 0 <= index < len(self.inventory) or not self.inventory[index]:
            return False
        item = self.inventory[index]
        expected = compatible_slot(self._item_definition(item))
        slot = slot or expected
        if expected is None or slot != expected:
            self._report("That item does not fit this active slot.")
            return False
        old = self.equipment[slot]
        if old is not None:
            self.active_items.discard(old)
        self.equipment[slot] = index
        self._report(f"Equipped {self.item_name(item)} in {slot}.")
        return True

    def unequip(self, slot):
        if self.ended or slot not in self.equipment or self.equipment[slot] is None:
            return False
        self.active_items.discard(self.equipment[slot])
        self.equipment[slot] = None
        self._report(f"Unequipped {slot}.")
        return True

    @staticmethod
    def item_name(item):
        return item.removesuffix("_object").replace("_", " ")

    def _remove_inventory_item(self, index):
        self.inventory[index] = ""
        for slot, equipped in self.equipment.items():
            if equipped == index:
                self.equipment[slot] = None
        self.active_items.discard(index)

    def armor(self):
        return sum(self._item_definition(self.inventory[index])["armor_bonus"]
                   for slot in ("head", "offhand")
                   if (index := self.equipment[slot]) is not None)

    def use_item(self, index):
        if self.ended or type(index) is not int or not 0 <= index < len(self.inventory) or not self.inventory[index]:
            return False
        item = self.inventory[index]
        definition = self._item_definition(item)
        kind = definition["item_type"]
        if kind == "weapon":
            if self.equipment["weapon"] != index:
                self.equip(index)
            return self.attack()
        if kind == "armor":
            if self.equipment[compatible_slot(definition)] != index:
                return self.equip(index)
            self._report(f"{self.item_name(item).title()}: +{definition['armor_bonus']} armor while equipped.")
            return False
        if kind == "readable":
            self._dialog(definition["read_text"] or "There is nothing written here.")
            return False
        if kind == "toggle":
            if self.equipment["light"] != index:
                self.equip(index)
            if index in self.active_items:
                self.active_items.remove(index)
            else:
                self.active_items.add(index)
            state = "on" if index in self.active_items else "off"
            self._report(f"{self.item_name(item).title()} is {state}.")
        elif kind == "consumable":
            effects = definition["effects"]
            health = min(self.stats["max_health"], max(0, self.health + effects.get("health", 0)))
            energy = min(self.stats["max_energy"], max(0, self.energy + effects.get("energy", 0)))
            if (health, energy) == (self.health, self.energy):
                self._report("That item has no effect right now.")
                return False
            self.health, self.energy = health, energy
            self._remove_inventory_item(index)
            self._report(f"Used {self.item_name(item)}.")
            if not self.health:
                self.ended, self.end_result = True, "lose"
                self._dialog("Game over. You have died.")
        else:
            self._report("That item has no use action.")
            return False
        self.turn_count += 1
        self._enemy_turn()
        return True

    def use_slot(self, slot):
        index = self.equipment.get(slot)
        return self.use_item(index) if index is not None else False

    def attack_weapon(self):
        index = self.equipment["weapon"]
        item = self.inventory[index] if index is not None else None
        return (item, self._item_definition(item)["weapon_damage"]) if item else (None, 0)

    def attack(self, direction=None):
        if self.ended:
            return False
        direction = direction or self.facing
        if direction not in DIRECTIONS:
            return False
        self.facing = direction
        weapon, bonus = self.attack_weapon()
        settings = self._item_definition(weapon) if weapon else {}
        ranged = settings.get("ranged", False)
        cost = settings.get("energy_cost", 0) if ranged else 0
        ammo = settings.get("ammo_item", "") if ranged else ""
        if self.energy < cost or (ammo and ammo not in self.inventory):
            self._report("Not enough energy or ammunition to fire.")
            return False
        if ranged:
            self.energy -= cost
            if ammo:
                self._remove_inventory_item(self.inventory.index(ammo))
        dx, dy = DIRECTIONS[direction]
        target = (self.player_x, self.player_y)
        enemy = None
        for distance in range(1, (settings.get("attack_range", 6) if ranged else 1) + 1):
            target = (self.player_x + dx * distance, self.player_y + dy * distance)
            if not (0 <= target[0] < self.current_area.width and 0 <= target[1] < self.current_area.height):
                break
            if ranged:
                tile = self.current_area.tiles[target[1]][target[0]]
                walkable = tile.walkable_override if tile.walkable_override is not None else default_tile_walkable(tile.type)
                if not walkable:
                    break
            enemy = next((obj for obj in self.current_area.objects
                          if (obj.x, obj.y) == target and self._enemy_definition(obj) is not None), None)
            if enemy is not None or not self._position_is_open(self.current_area, *target):
                break
        if enemy is not None:
            definition = self._enemy_definition(enemy)
            damage = max(1, self.stats["strength"]) + bonus
            method = f"with a {self.item_name(weapon)}" if weapon else "unarmed"
            self._report(f"You attack {definition.get('name', enemy.type)} {method}.")
            remaining = max(0, enemy.properties.get("enemy_health", definition.get("health", 10)) - damage)
            enemy.properties["enemy_health"] = remaining
            self._feedback("hit", *target, damage)
            self._report(f"You hit {definition.get('name', enemy.type)} for {damage} damage ({remaining} health left).")
            if remaining == 0:
                self.current_area.objects.remove(enemy)
                self._report(f"{definition.get('name', enemy.type)} defeated.")
        else:
            self._feedback("miss", *target)
            self._report("Miss! No enemy within reach in that direction.")
        if ranged:
            self.feedback[-1].update(from_x=self.player_x, from_y=self.player_y)
        if enemy is not None or ranged:
            self.turn_count += 1
            self._enemy_turn()
            return True
        return False

    def process_entry_triggers(self, visited=None):
        if self.ended:
            return
        visited = set() if visited is None else visited
        for _ in range(64):
            location = (
                self.current_area_filename, self.player_x, self.player_y
            )
            if location in visited:
                self._report("Stopped a repeating teleport-trigger loop.")
                return
            visited.add(location)
            relocated = False
            for trigger in list(self.current_area.triggers):
                if (trigger.x, trigger.y) != (self.player_x, self.player_y):
                    continue
                old_location = (
                    self.current_area_filename, self.player_x, self.player_y
                )
                owner = self.current_area
                try:
                    self._execute_trigger(trigger)
                except RunnerError as error:
                    self._report(f"Trigger {trigger.name!r}: {error}")
                    return
                if trigger.parameters.get("once", False):
                    owner.triggers.remove(trigger)
                if self.ended:
                    return
                new_location = (
                    self.current_area_filename, self.player_x, self.player_y
                )
                if new_location != old_location:
                    relocated = True
                    break
            if not relocated:
                return
        self._report("Stopped a teleport-trigger chain after 64 relocations.")

    def _validate_trigger_references(self):
        for filename, area in self.areas.items():
            for trigger in area.triggers:
                params = trigger.parameters
                try:
                    if type(params.get("once", False)) is not bool:
                        raise RunnerError("once must be true or false.")
                    if trigger.trigger_type == "teleport":
                        destination = self.area_filename(params.get("area", ""))
                        x, y = params.get("x"), params.get("y")
                        if type(x) is not int or type(y) is not int:
                            raise RunnerError("target coordinates must be integers.")
                        if not self._position_is_open(self.areas[destination], x, y):
                            raise RunnerError(
                                f"target {destination} ({x},{y}) is blocked or out of bounds."
                            )
                    elif trigger.trigger_type == "area_object":
                        destination = self.area_filename(params.get("area") or filename)
                        if params.get("action", "add") not in ("add", "remove"):
                            raise RunnerError("area object action must be add or remove.")
                        object_type = params.get("object")
                        if not isinstance(object_type, str) or not object_type:
                            raise RunnerError("object name is missing.")
                        target = self.areas[destination]
                        x, y = params.get("x", trigger.x), params.get("y", trigger.y)
                        if type(x) is not int or type(y) is not int:
                            raise RunnerError("object coordinates must be integers.")
                        if not (0 <= x < target.width and 0 <= y < target.height):
                            raise RunnerError(
                                f"object position ({x},{y}) is outside "
                                f"{destination}."
                            )
                    elif trigger.trigger_type == "tile_update":
                        x, y = params.get("x"), params.get("y")
                        if type(x) is not int or type(y) is not int:
                            raise RunnerError("tile update coordinates must be integers.")
                        if not (0 <= x < area.width and 0 <= y < area.height):
                            raise RunnerError(
                                f"tile update target ({x},{y}) is outside {filename}."
                            )
                        if not isinstance(params.get("tile"), str) or not params["tile"]:
                            raise RunnerError("tile update name is missing.")
                        if (
                            "walkable" in params
                            and type(params["walkable"]) is not bool
                        ):
                            raise RunnerError("walkable must be true or false.")
                        if params["tile"] != "empty" and params["tile"] not in self.tile_names:
                            self._validation_issue(
                                f"Trigger {trigger.name!r} in {filename}: tile "
                                f"image {params['tile']!r} is missing."
                            )
                    elif trigger.trigger_type == "player_stats":
                        if params.get("stat", "health") not in PLAYER_STAT_CHANGES:
                            raise RunnerError("choose a valid player stat.")
                        if type(params.get("amount", 0)) is not int:
                            raise RunnerError("stat change must be a whole number.")
                    elif trigger.trigger_type == "inventory":
                        if any(
                            not isinstance(params.get(key, ""), str)
                            for key in ("add", "remove")
                        ):
                            raise RunnerError("inventory item names must be text.")
                    elif trigger.trigger_type == "show_message":
                        if not isinstance(params.get("message", ""), str):
                            raise RunnerError("message must be text.")
                    elif trigger.trigger_type == "game_end":
                        if params.get("win_lose", "win") not in ("win", "lose"):
                            raise RunnerError("result must be win or lose.")
                        if not isinstance(params.get("message", ""), str):
                            raise RunnerError("game-end message must be text.")
                except RunnerError as error:
                    self._validation_issue(
                        f"Trigger {trigger.name!r} in {filename}: {error}"
                    )

    def _validate_asset_references(self):
        checked = set()

        def check(category, name, context):
            if not isinstance(name, str) or not name:
                self._validation_issue(f"{context}: asset name is missing.")
                return
            key = (category, name)
            if key in checked:
                return
            checked.add(key)
            path = self.asset_root / category / f"{name}.png"
            try:
                with Image.open(path) as image:
                    image.verify()
            except (OSError, ValueError):
                self._validation_issue(f"{context}: missing or invalid image {path}.")

        player_sprite = self.player_settings.get("sprite", "fighter_npc")
        check("npcs", player_sprite, "Player sprite")

        for object_type in self.object_definitions:
            category = "npcs" if object_type in self.npc_names else "objects"
            check(category, object_type, f"Object definition {object_type!r}")

        enemy_definitions = self.properties.get("enemies", {})
        if not isinstance(enemy_definitions, dict):
            self._validation_issue(
                f"{self.game_path}: properties.enemies must be an object."
            )
        else:
            for enemy_id, definition in enemy_definitions.items():
                if not isinstance(definition, dict):
                    self._validation_issue(
                        f"{self.game_path}: enemy {enemy_id!r} must be an object."
                    )
                    continue
                check(
                    "npcs",
                    definition.get("sprite"),
                    f"Enemy {definition.get('name', enemy_id)!r} sprite",
                )

        for filename, area in self.areas.items():
            for row in area.tiles:
                for tile in row:
                    if tile.type != "empty":
                        check("tiles", tile.type, f"Area {filename!r} tile")
            for obj in area.objects:
                is_enemy = (
                    "enemy_id" in obj.properties
                    or "enemy_data" in obj.properties
                )
                enemy_data = obj.properties.get("enemy_data", {})
                sprite = (
                    enemy_data.get("sprite", obj.type)
                    if is_enemy and isinstance(enemy_data, dict)
                    else obj.type
                )
                category = "npcs" if is_enemy or sprite in self.npc_names else "objects"
                check(category, sprite, f"Area {filename!r} object {obj.type!r}")

    def _execute_trigger(self, trigger):
        params = trigger.parameters
        trigger_type = trigger.trigger_type
        if type(params.get("once", False)) is not bool:
            raise RunnerError("once must be true or false.")
        if trigger_type == "show_message":
            message = params.get("message", "")
            if not isinstance(message, str):
                raise RunnerError("message must be text.")
            if message:
                self._dialog(message)
        elif trigger_type == "player_stats":
            self._apply_stat_trigger(params)
        elif trigger_type == "inventory":
            self._apply_inventory_trigger(params)
        elif trigger_type == "tile_update":
            x, y = params.get("x"), params.get("y")
            if type(x) is not int or type(y) is not int:
                raise RunnerError("tile update coordinates must be integers.")
            if not (0 <= x < self.current_area.width and
                    0 <= y < self.current_area.height):
                raise RunnerError(f"tile update target ({x},{y}) is outside the area.")
            tile_type = params.get("tile")
            if not isinstance(tile_type, str) or not tile_type:
                raise RunnerError("tile update is missing a tile name.")
            walkable = params.get("walkable")
            if walkable is not None and type(walkable) is not bool:
                raise RunnerError("tile update walkable must be true or false.")
            self.current_area.tiles[y][x] = Tile(
                type=tile_type, walkable_override=walkable
            )
            self._report(f"Changed tile ({x},{y}) to {tile_type}.")
        elif trigger_type == "area_object":
            self._add_area_object(trigger, params)
        elif trigger_type == "teleport":
            self._teleport(params)
        elif trigger_type == "game_end":
            result = params.get("win_lose", "win")
            if result not in ("win", "lose"):
                raise RunnerError("result must be win or lose.")
            message = params.get("message") or self.game.get("game_end_message", "")
            if not isinstance(message, str):
                raise RunnerError("game-end message must be text.")
            self.ended = True
            self.end_result = result
            self._dialog(message or ("You win!" if result == "win" else "You lose."))
            self._report(f"Game ended: {result}.")
        elif trigger_type == "custom":
            self._report(
                f"Trigger {trigger.name!r} uses a custom script, which the runner "
                "does not execute."
            )

    def _apply_stat_trigger(self, params):
        stat, amount = params.get("stat", "health"), params.get("amount", 0)
        if stat not in PLAYER_STAT_CHANGES or type(amount) is not int:
            raise RunnerError("Choose a valid player stat and a whole-number change.")
        old = getattr(self, stat) if stat in ("health", "energy") else self.stats[stat]
        if stat in ("health", "energy"):
            value = min(self.stats[f"max_{stat}"], max(0, old + amount))
            setattr(self, stat, value)
        else:
            value = max(1 if stat == "max_health" else 0, old + amount)
            self.stats[stat] = value
            self.health = min(self.health, self.stats["max_health"])
            self.energy = min(self.energy, self.stats["max_energy"])
        self._report(f"{stat.replace('_', ' ').title()}: {old} → {value} ({value-old:+d}).")
        if self.health == 0:
            self.ended, self.end_result = True, "lose"
            self._dialog("Game over. You have died.")

    def _apply_inventory_trigger(self, params):
        add_item = params.get("add", "")
        remove_item = params.get("remove", "")
        if not isinstance(add_item, str) or not isinstance(remove_item, str):
            raise RunnerError("inventory add/remove values must be item names.")
        slots = self.inventory[:]
        if remove_item:
            try:
                slots[slots.index(remove_item)] = ""
            except ValueError as error:
                raise RunnerError(
                    f"cannot remove {remove_item!r}; it is not in the inventory."
                ) from error
        if add_item:
            try:
                empty_slot = slots.index("")
            except ValueError as error:
                raise RunnerError("inventory is full; no item was added.") from error
            slots[empty_slot] = add_item
        if remove_item:
            self._remove_inventory_item(self.inventory.index(remove_item))
        self.inventory = slots
        if remove_item:
            self._report(f"Removed {self.item_name(remove_item)} from inventory.")
        if add_item:
            self._report(f"Added {self.item_name(add_item)} to inventory.")

    def _add_area_object(self, trigger, params):
        # The legacy method name is retained for existing callers.
        try:
            filename = self.area_filename(params.get("area") or self.current_area_filename)
        except RunnerError as error:
            raise RunnerError(f"invalid destination area: {error}") from error
        object_type = params.get("object")
        if not isinstance(object_type, str) or not object_type:
            raise RunnerError("area object trigger is missing an object name.")
        action = params.get("action", "add")
        if action not in ("add", "remove"):
            raise RunnerError("area object action must be add or remove.")
        area = self.areas[filename]
        x, y = params.get("x", trigger.x), params.get("y", trigger.y)
        if (type(x) is not int or type(y) is not int
                or not (0 <= x < area.width and 0 <= y < area.height)):
            raise RunnerError(f"object position ({x},{y}) is outside {filename}.")
        existing = next((obj for obj in area.objects
                         if obj.type == object_type and obj.x == x and obj.y == y), None)
        if action == "remove":
            if existing is None:
                raise RunnerError(f"no {object_type} at ({x},{y}) in {filename}.")
            area.objects.remove(existing)
            self._report(f"Removed {self.item_name(object_type)} from {filename}.")
        elif existing is not None:
            self._report(f"{object_type} is already present in {filename}.")
        else:
            area.objects.append(GameObject(type=object_type, x=x, y=y))
            self._report(f"Added {self.item_name(object_type)} to {filename}.")

    def _teleport(self, params):
        try:
            filename = self.area_filename(params.get("area", ""))
        except RunnerError as error:
            raise RunnerError(f"invalid destination area: {error}") from error
        x, y = params.get("x"), params.get("y")
        if type(x) is not int or type(y) is not int:
            raise RunnerError("teleport coordinates must be integers.")
        area = self.areas[filename]
        if not self._position_is_open(area, x, y):
            raise RunnerError(
                f"destination {filename} ({x},{y}) is blocked or out of bounds."
            )
        self.current_area_filename = filename
        self.current_area = area
        self.player_x, self.player_y = x, y
        self._report(f"Entered {area.name}.")

    def interact(self):
        if self.ended:
            return False
        candidates = [(self.player_x, self.player_y)]
        candidates.extend(
            (self.player_x + dx, self.player_y + dy)
            for dx, dy in (DIRECTIONS[key] for key in ("up", "left", "down", "right"))
        )
        for x, y in candidates:
            for obj in list(self.current_area.objects):
                if (obj.x, obj.y) != (x, y):
                    continue
                definition = self._item_definition(obj.type)
                if definition["item_type"] == "openable":
                    opened = not obj.properties.get("open", False)
                    if not opened and (obj.x, obj.y) == (self.player_x, self.player_y):
                        self._report("Step away before closing it.")
                        return False
                    obj.properties["open"] = opened
                    self._report(f"{self.item_name(obj.type).title()} is {'open' if opened else 'closed'}.")
                    self.turn_count += 1
                    self._enemy_turn()
                    return True
                if not definition.get("gettable"):
                    continue
                try:
                    empty_slot = self.inventory.index("")
                except ValueError:
                    self._report("Inventory is full.")
                    return False
                self.inventory[empty_slot] = obj.type
                self.current_area.objects.remove(obj)
                self.turn_count += 1
                self._report(f"Picked up {obj.type}.")
                self._enemy_turn()
                return True
        self._report("There is nothing to interact with nearby.")
        return False
