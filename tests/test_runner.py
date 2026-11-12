import contextlib
import importlib.util
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from PIL import Image
from data_classes import GameObject, Tile
from runner_engine import RunnerEngine, RunnerError, resolve_game_path
import project_paths

RUNNER_PATH = Path(__file__).resolve().parents[1] / "tinker-runner.py"
RUNNER_SPEC = importlib.util.spec_from_file_location("tinker_runner", RUNNER_PATH)
tinker_runner = importlib.util.module_from_spec(RUNNER_SPEC)
RUNNER_SPEC.loader.exec_module(tinker_runner)


class RunnerEngineTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "games").mkdir()
        (self.root / "areas").mkdir()
        (self.root / "npcs").mkdir()
        (self.root / "objects").mkdir()
        (self.root / "tiles").mkdir()
        Image.new("RGBA", (32, 32)).save(self.root / "npcs" / "hero.png")
        Image.new("RGBA", (32, 32)).save(self.root / "objects" / "chest_object.png")
        Image.new("RGBA", (32, 32)).save(self.root / "tiles" / "grass.png")
        Image.new("RGBA", (32, 32)).save(self.root / "tiles" / "lake_center.png")
        self.area = self._area()
        self.area_path = self.root / "areas" / "start.json"
        self._write_json(self.area_path, self.area)
        self.game_path = self.root / "games" / "demo.json"
        self.game = self._game()
        self._write_json(self.game_path, self.game)

    def tearDown(self):
        self.temp_dir.cleanup()

    @staticmethod
    def _write_json(path, value):
        path.write_text(json.dumps(value), encoding="utf-8")

    @staticmethod
    def _area(width=3, height=3, triggers=None):
        return {
            "name": "Start",
            "width": width,
            "height": height,
            "tiles": [
                [{"type": "grass", "walkable_override": None} for _ in range(width)]
                for _ in range(height)
            ],
            "objects": [],
            "triggers": triggers or [],
        }

    @staticmethod
    def _game(areas=None, player_start=(1, 1)):
        return {
            "name": "Demo",
            "areas": areas or ["start.json"],
            "properties": {
                "start_area": (areas or ["start.json"])[0],
                "start_x": player_start[0],
                "start_y": player_start[1],
                "player": {
                    "sprite": "hero",
                    "stats": {
                        "starting_health": 12,
                        "max_health": 20,
                        "starting_energy": 0,
                        "max_energy": 0,
                        "strength": 1,
                        "intelligence": 1,
                        "gold": 3,
                    },
                    "starting_inventory": ["key_object", ""],
                },
            },
            "object_definitions": {},
        }

    def engine(self):
        return RunnerEngine(self.game_path, project_root=self.root)

    def test_project_root_resolves_frozen_package_data_directory(self):
        executable = self.root / "Tinker Editor" / "Tinker Editor.exe"
        with (
            patch.object(project_paths.sys, "frozen", True, create=True),
            patch.object(project_paths.sys, "executable", str(executable)),
        ):
            for directory in ("tiles", "npcs", "objects"):
                (self.root / directory).mkdir(exist_ok=True)
            self.assertEqual(project_paths.project_root(), self.root.resolve())

    def test_frozen_macos_app_uses_bundled_assets_and_documents_for_data(self):
        app_bundle = self.root / "Install" / "Tinker Editor.app"
        executable = app_bundle / "Contents" / "MacOS" / "Tinker Editor"
        bundled_assets = app_bundle / "Contents" / "Resources" / "TinkerData"
        for directory in ("tiles", "npcs", "objects"):
            (bundled_assets / directory).mkdir(parents=True, exist_ok=True)
            shutil.rmtree(self.root / directory)
        with (
            patch.object(project_paths.sys, "frozen", True, create=True),
            patch.object(project_paths.sys, "executable", str(executable)),
            patch.object(project_paths.Path, "home", return_value=self.root.resolve()),
        ):
            self.assertEqual(
                project_paths.project_root(),
                self.root.resolve() / "Documents" / "Tinker RPG",
            )
            self.assertEqual(project_paths.asset_root(), bundled_assets.resolve())

    def test_frozen_windows_installer_uses_external_assets_and_user_data(self):
        executable = self.root / "Install" / "Tinker Editor" / "Tinker Editor.exe"
        bundled_assets = self.root / "Install" / "assets"
        for directory in ("tiles", "npcs", "objects"):
            (bundled_assets / directory).mkdir(parents=True, exist_ok=True)
            shutil.rmtree(self.root / directory)
        with (
            patch.object(project_paths.sys, "frozen", True, create=True),
            patch.object(project_paths.sys, "executable", str(executable)),
            patch.object(project_paths.Path, "home", return_value=self.root.resolve()),
        ):
            self.assertEqual(
                project_paths.project_root(),
                self.root.resolve() / "Documents" / "Tinker RPG",
            )
            self.assertEqual(project_paths.asset_root(), bundled_assets.resolve())

    def test_runner_window_sizes_to_start_area_with_screen_limit(self):
        root = Mock()
        root.winfo_reqwidth.return_value = 400
        root.winfo_reqheight.return_value = 300
        root.winfo_screenwidth.return_value = 1920
        root.winfo_screenheight.return_value = 1080
        canvas = Mock()
        canvas.winfo_reqwidth.return_value = 100
        canvas.winfo_reqheight.return_value = 100
        runner = SimpleNamespace(
            root=root,
            canvas=canvas,
            engine=SimpleNamespace(
                current_area=SimpleNamespace(width=20, height=10)
            ),
        )

        tinker_runner.TinkerRunner._size_window_to_start_area(runner)

        root.geometry.assert_called_once_with("940x520")

        runner.engine.current_area = SimpleNamespace(width=100, height=100)
        root.geometry.reset_mock()
        tinker_runner.TinkerRunner._size_window_to_start_area(runner)

        root.geometry.assert_called_once_with("1840x960")

    def test_map_origin_centers_maps_that_fit_the_canvas(self):
        canvas = Mock()
        canvas.winfo_width.return_value = 800
        canvas.winfo_height.return_value = 600
        runner = SimpleNamespace(
            canvas=canvas,
            engine=SimpleNamespace(
                current_area=SimpleNamespace(width=10, height=5)
            ),
        )

        self.assertEqual(
            tinker_runner.TinkerRunner._map_origin(runner), (240, 220)
        )

        runner.engine.current_area = SimpleNamespace(width=40, height=30)
        self.assertEqual(
            tinker_runner.TinkerRunner._map_origin(runner), (0, 0)
        )

    def test_game_messages_are_written_to_the_message_log(self):
        runner = tinker_runner.TinkerRunner.__new__(
            tinker_runner.TinkerRunner
        )
        runner.engine = SimpleNamespace(events=["Welcome."])
        runner._append_log = Mock()

        with patch.object(tinker_runner.tk, "Toplevel") as toplevel:
            runner.show_dialog("Welcome.")
            runner._show_dialog("Could not save.", "Save Failed")

        self.assertEqual(runner.engine.events, [])
        runner._append_log.assert_has_calls([
            unittest.mock.call("Welcome."),
            unittest.mock.call("Save Failed: Could not save."),
        ])
        toplevel.assert_not_called()

    def test_restart_reloads_authored_game_and_clears_save_association(self):
        runner = tinker_runner.TinkerRunner.__new__(
            tinker_runner.TinkerRunner
        )
        runner.root = Mock()
        runner.engine = SimpleNamespace(game_path=self.game_path)
        runner.project_root = self.root
        runner.dirty = True
        runner.inventory_window = None
        runner.save_path = self.root / "old.save.json"
        runner.save_name = "Old Save"
        runner.message_log = Mock()
        runner.start_game = Mock()
        restarted_engine = SimpleNamespace(
            game={"name": "Demo"},
            save_name=None,
        )

        with (
            patch.object(tinker_runner.messagebox, "askyesno", return_value=True),
            patch.object(
                tinker_runner, "RunnerEngine", return_value=restarted_engine
            ) as engine_factory,
        ):
            runner.restart_game()

        engine_factory.assert_called_once_with(
            self.game_path,
            project_root=self.root,
            dialog_handler=runner.show_dialog,
        )
        self.assertIs(runner.engine, restarted_engine)
        self.assertIsNone(runner.save_path)
        self.assertEqual(runner.save_name, "Demo")
        self.assertFalse(runner.dirty)
        runner.root.title.assert_called_once_with("Demo")
        runner.start_game.assert_called_once_with()
        runner.message_log.delete.assert_called_once_with("1.0", "end")

    def test_save_always_prompts_in_saves_directory(self):
        save_path = self.root / "saves" / "new_slot.json"
        runner = tinker_runner.TinkerRunner.__new__(
            tinker_runner.TinkerRunner
        )
        runner.project_root = self.root
        runner.engine = SimpleNamespace(
            game={"name": "Demo"},
            game_path=self.game_path,
            save_to_file=Mock(return_value=save_path),
        )
        runner.root = Mock()
        runner.save_path = self.root / "saves" / "existing.json"
        runner.save_name = "Existing"
        runner.dirty = True
        runner._append_log = Mock()
        runner._show_dialog = Mock()

        with patch.object(
            tinker_runner.filedialog,
            "asksaveasfilename",
            return_value=str(save_path),
        ) as choose_path:
            runner.save_game()

        choose_path.assert_called_once()
        self.assertEqual(
            choose_path.call_args.kwargs["initialdir"], self.root / "saves"
        )
        self.assertEqual(choose_path.call_args.kwargs["defaultextension"], ".json")
        runner.engine.save_to_file.assert_called_once_with(
            str(save_path), "new_slot"
        )
        self.assertEqual(runner.save_path, save_path)
        self.assertFalse(runner.dirty)

    def test_load_prompts_in_saves_directory(self):
        save_path = self.root / "saves" / "slot.json"
        loaded_engine = SimpleNamespace(
            save_name="slot",
            game={"name": "Demo"},
            validation_issues=[],
        )
        runner = tinker_runner.TinkerRunner.__new__(
            tinker_runner.TinkerRunner
        )
        runner.project_root = self.root
        runner.engine = SimpleNamespace(game={"name": "Old"})
        runner.root = Mock()
        runner.save_path = self.root / "elsewhere" / "old.json"
        runner.save_name = "Old"
        runner.dirty = False
        runner._append_log = Mock()
        runner._after_action = Mock()
        runner.show_dialog = Mock()
        runner._show_dialog = Mock()

        with (
            patch.object(
                tinker_runner.filedialog,
                "askopenfilename",
                return_value=str(save_path),
            ) as choose_path,
            patch.object(
                tinker_runner, "RunnerEngine", autospec=True
            ) as engine_factory,
        ):
            engine_factory.load_save.return_value = loaded_engine
            runner.load_game()

        choose_path.assert_called_once()
        self.assertEqual(
            choose_path.call_args.kwargs["initialdir"], self.root / "saves"
        )
        engine_factory.load_save.assert_called_once_with(
            str(save_path),
            project_root=self.root,
            dialog_handler=runner.show_dialog,
        )
        self.assertIs(runner.engine, loaded_engine)
        self.assertEqual(runner.save_path, save_path.resolve())
        runner._after_action.assert_called_once_with()

    def _replace_triggers(self, triggers):
        self.area["triggers"] = triggers
        self._write_json(self.area_path, self.area)

    def test_resolves_game_stem_from_project_games_directory(self):
        self.assertEqual(
            resolve_game_path("demo", cwd=self.root, project_root=self.root),
            self.game_path.resolve(),
        )

    def test_ambiguous_game_stem_requires_path(self):
        local_game = self.root / "demo.json"
        self._write_json(local_game, self.game)
        with self.assertRaisesRegex(RunnerError, "ambiguous"):
            resolve_game_path("demo", cwd=self.root, project_root=self.root)

    def test_loads_start_settings_and_pads_inventory_slots(self):
        engine = self.engine()
        self.assertEqual((engine.player_x, engine.player_y), (1, 1))
        self.assertEqual(engine.health, 12)
        self.assertEqual(engine.inventory[:2], ["key_object", ""])
        self.assertEqual(len(engine.inventory), 8)

    def combat_engine(self, speed=1.0, damage=3, health=4, position=(4, 1), behavior="chase"):
        self.area = self._area(width=6, height=4)
        self.area["objects"] = [{
            "type": "hero", "x": position[0], "y": position[1],
            "properties": {"enemy_id": "blob", "enemy_data": {"health": 999}},
        }]
        self.game["properties"]["enemies"] = {"blob": {
            "name": "Blob", "sprite": "hero", "health": health,
            "behavior": behavior, "movement_speed": speed, "contact_damage": damage,
        }}
        self._write_json(self.area_path, self.area)
        self._write_json(self.game_path, self.game)
        return self.engine()

    def test_chase_fractional_speed_accumulates_and_contact_damages(self):
        engine = self.combat_engine(speed=0.5)
        enemy = engine.current_area.objects[0]
        engine.wait()
        self.assertEqual((enemy.x, enemy.y), (4, 1))
        engine.wait()
        self.assertEqual((enemy.x, enemy.y), (3, 1))
        engine.wait()
        engine.wait()
        self.assertEqual((enemy.x, enemy.y), (2, 1))
        self.assertEqual(engine.health, 9)
        engine.wait()
        self.assertEqual(engine.health, 6)
        self.assertNotEqual((enemy.x, enemy.y), (engine.player_x, engine.player_y))

    def test_chase_routes_around_walls_and_other_objects(self):
        engine = self.combat_engine()
        engine.current_area.tiles[1][3].walkable_override = False
        engine.current_area.objects.append(GameObject("chest_object", 3, 0, {"walkable": False}))
        enemy = engine.current_area.objects[0]
        for _ in range(8):
            engine.wait()
            self.assertNotEqual((enemy.x, enemy.y), (3, 1))
            self.assertNotEqual((enemy.x, enemy.y), (3, 0))
        self.assertLessEqual(abs(enemy.x-engine.player_x)+abs(enemy.y-engine.player_y), 1)

    def test_fast_enemy_hits_at_most_once_per_turn(self):
        engine = self.combat_engine(speed=4)
        engine.wait()
        self.assertEqual(engine.health, 9)
        self.assertEqual((engine.current_area.objects[0].x, engine.current_area.objects[0].y), (2, 1))

    def test_stationary_enemy_keeps_legacy_behavior(self):
        engine = self.combat_engine(position=(2, 1), behavior="stationary")
        engine.wait()
        self.assertEqual(engine.health, 12)
        self.assertEqual(engine.current_area.objects[0].x, 2)

    def test_player_attack_kills_and_removes_enemy_without_retaliation(self):
        engine = self.combat_engine(position=(2, 1), health=1)
        self.assertTrue(engine.attack("right"))
        self.assertEqual(engine.current_area.objects, [])
        self.assertEqual(engine.health, 12)
        self.assertTrue(engine.move("right"))

    def test_player_death_ends_game_and_blocks_actions(self):
        engine = self.combat_engine(position=(2, 1), damage=50)
        engine.wait()
        self.assertEqual(engine.health, 0)
        self.assertTrue(engine.ended)
        self.assertEqual(engine.end_result, "lose")
        turn = engine.turn_count
        self.assertFalse(engine.move("up"))
        self.assertFalse(engine.attack("right"))
        self.assertFalse(engine.wait())
        self.assertEqual(engine.turn_count, turn)

    def test_combat_health_and_movement_credit_survive_save(self):
        engine = self.combat_engine(speed=0.5, position=(2, 1))
        engine.attack("right")
        path = self.root / "combat.save.json"
        engine.save_to_file(path, "Combat")
        loaded = RunnerEngine.load_save(path, project_root=self.root)
        self.assertEqual(loaded.health, engine.health)
        self.assertEqual(loaded.current_area.objects[0].properties["enemy_health"], 3)
        self.assertEqual(loaded.current_area.objects[0].properties["movement_credit"], 0.5)

    def test_equipped_sword_adds_damage_and_names_weapon(self):
        engine = self.combat_engine(position=(2, 1), health=20)
        engine.inventory[0] = "sword_object"
        engine.equip(0)
        engine.attack("right")
        self.assertEqual(engine.current_area.objects[0].properties["enemy_health"], 15)
        self.assertIn("You attack Blob with a sword.", engine.events)
        self.assertEqual(engine.feedback[0]["damage"], 5)

    def test_only_selected_weapon_is_used_and_bonuses_do_not_stack(self):
        engine = self.combat_engine(position=(2, 1), health=20)
        engine.inventory[:4] = ["sword_object", "sword_object", "club_object", "book_object"]
        engine.object_definitions.update({
            "club_object": {"item_type": "weapon", "weapon_damage": 7},
            "book_object": {"item_type": "object", "weapon_damage": 99},
        })
        engine.equip(2)
        engine.attack("right")
        self.assertEqual(engine.feedback[0]["damage"], 8)
        self.assertIn("You attack Blob with a club.", engine.events)

    def test_removing_sword_returns_to_unarmed_damage(self):
        engine = self.combat_engine(position=(2, 1), health=20)
        engine.inventory[0] = "sword_object"
        engine.equip(0)
        engine.attack("right")
        engine._remove_inventory_item(0)
        engine.feedback.clear()
        engine.attack("right")
        self.assertEqual(engine.feedback[0]["damage"], 1)
        self.assertIn("You attack Blob unarmed.", engine.events)

    def test_sword_pickup_and_saved_weapon_settings_affect_attacks(self):
        engine = self.combat_engine(position=(2, 1), health=20)
        engine.current_area.objects.append(GameObject("sword_object", 1, 1))
        self.assertTrue(engine.interact())
        self.assertIn("sword_object", engine.inventory)
        engine.equip(engine.inventory.index("sword_object"))
        # Game-authored weapon values override the built-in sword default.
        engine.object_definitions["sword_object"] = {"item_type": "weapon", "weapon_damage": 9}
        engine.game["object_definitions"] = engine.object_definitions
        Image.new("RGBA", (32, 32)).save(self.root / "objects" / "sword_object.png")
        save_path = self.root / "weapon.save.json"
        engine.save_to_file(save_path, "Weapon")
        loaded = RunnerEngine.load_save(save_path, project_root=self.root)
        loaded.attack("right")
        self.assertEqual(loaded.feedback[0]["damage"], 10)

    def test_negative_weapon_damage_is_rejected(self):
        self.game["object_definitions"] = {"chest_object": {
            "item_type": "weapon", "weapon_damage": -2,
        }}
        self._write_json(self.game_path, self.game)
        with self.assertRaisesRegex(RunnerError, "weapon_damage"):
            self.engine()

    def test_attack_feedback_distinguishes_hit_miss_and_enemy_damage(self):
        engine = self.combat_engine(position=(2, 1))
        engine.attack("up")
        self.assertEqual([item["kind"] for item in engine.feedback], ["miss"])
        self.assertEqual((engine.feedback[0]["x"], engine.feedback[0]["y"]), (1, 0))
        engine.feedback.clear()
        engine.attack("right")
        self.assertEqual([item["kind"] for item in engine.feedback], ["hit", "hurt"])
        self.assertEqual(engine.feedback[0]["damage"], 1)
        self.assertEqual(engine.feedback[1]["damage"], 3)

    def test_step_feedback_only_occurs_after_successful_movement(self):
        engine = self.engine()
        engine.current_area.tiles[1][2].walkable_override = False
        engine.move("right")
        self.assertEqual(engine.feedback, [])
        engine.move("up")
        self.assertEqual([item["kind"] for item in engine.feedback], ["step"])

    def test_feedback_is_consumed_and_markers_clear_after_delay(self):
        runner = tinker_runner.TinkerRunner.__new__(tinker_runner.TinkerRunner)
        runner.engine = self.combat_engine(position=(2, 1))
        runner.engine.attack("right")
        runner.sounds = Mock()
        runner.canvas = Mock()
        runner.root = Mock()
        runner.marker_generation = 0
        runner._draw_attack_markers = Mock()
        runner._present_feedback()
        self.assertEqual(runner.engine.feedback, [])
        self.assertEqual(len(runner.attack_markers), 2)
        runner.sounds.play.assert_called_once_with("hit")
        self.assertEqual(runner.root.after.call_args.args[0], 300)
        runner.root.after.call_args.args[1]()
        self.assertEqual(runner.attack_markers, [])
        runner.sounds.play.reset_mock()
        runner._present_feedback()
        runner.sounds.play.assert_not_called()

    def test_action_dispatches_audio_before_map_redraw(self):
        runner = tinker_runner.TinkerRunner.__new__(tinker_runner.TinkerRunner)
        sequence = Mock()
        runner._present_feedback = sequence.feedback
        runner.redraw = sequence.redraw
        runner._flush_events = sequence.log
        runner.refresh_inventory = sequence.inventory
        runner.refresh_active_bar = sequence.bar
        runner._after_action()
        self.assertEqual(sequence.mock_calls[:2], [unittest.mock.call.feedback(), unittest.mock.call.redraw()])

    def test_player_damage_preserves_footstep_in_one_immediate_cue(self):
        runner = tinker_runner.TinkerRunner.__new__(tinker_runner.TinkerRunner)
        runner.engine = self.combat_engine(speed=0, position=(2, 1))
        runner.engine.feedback = [
            {"kind": "step", "area": "start.json", "x": 1, "y": 1, "damage": 0},
            {"kind": "hurt", "area": "start.json", "x": 1, "y": 1, "damage": 3},
        ]
        runner.sounds = Mock()
        runner.canvas = Mock()
        runner.root = Mock()
        runner.marker_generation = 0
        runner._draw_attack_markers = Mock()
        runner._present_feedback()
        runner.sounds.play.assert_called_once_with("step_hurt")

    def test_stale_marker_timer_does_not_clear_newer_attack(self):
        runner = tinker_runner.TinkerRunner.__new__(tinker_runner.TinkerRunner)
        runner.marker_generation = 2
        runner.attack_markers = [{"kind": "hit"}]
        runner.canvas = Mock()
        runner._clear_attack_markers(1)
        self.assertEqual(len(runner.attack_markers), 1)
        runner.canvas.delete.assert_not_called()

    def test_bundled_sounds_are_short_valid_distinct_wavs(self):
        import wave
        sounds = Path(__file__).resolve().parents[1] / "sounds"
        data = set()
        for name in ("step", "hit", "miss", "hurt"):
            with wave.open(str(sounds / f"{name}.wav")) as sound:
                self.assertEqual(sound.getnchannels(), 1)
                self.assertEqual(sound.getsampwidth(), 2)
                self.assertLess(sound.getnframes() / sound.getframerate(), 0.2)
                data.add(sound.readframes(sound.getnframes()))
        self.assertEqual(len(data), 4)

    def test_invalid_enemy_combat_values_are_rejected(self):
        for setting in ({"speed": float("nan")}, {"damage": -1}, {"health": 0}):
            with self.subTest(setting=setting), self.assertRaises(RunnerError):
                self.combat_engine(**setting)

    def test_missing_start_settings_are_actionable(self):
        self.game["properties"].pop("start_area")
        self._write_json(self.game_path, self.game)
        with self.assertRaisesRegex(RunnerError, "properties.start_area"):
            self.engine()

    def test_blocked_start_allows_leaving_but_not_returning(self):
        self.area["tiles"][1][1]["walkable_override"] = False
        self._write_json(self.area_path, self.area)
        engine = self.engine()
        self.assertTrue(engine.move("right"))
        self.assertFalse(engine.move("left"))
        self.assertIs(engine.current_area.tiles[1][1].walkable_override, False)

    def test_save_can_resume_on_blocked_start(self):
        self.area["tiles"][1][1]["walkable_override"] = False
        self._write_json(self.area_path, self.area)
        engine = self.engine()
        save_path = self.root / "blocked-start.save.json"
        engine.save_to_file(save_path, "Blocked start")
        loaded = RunnerEngine.load_save(save_path, project_root=self.root)
        self.assertEqual((loaded.player_x, loaded.player_y), (1, 1))
        self.assertTrue(loaded.move("right"))
        self.assertFalse(loaded.move("left"))

    def test_movement_blocks_edges_and_non_walkable_override(self):
        self.area["tiles"][1][2]["walkable_override"] = False
        self._write_json(self.area_path, self.area)
        engine = self.engine()
        self.assertFalse(engine.move("right"))
        self.assertTrue(engine.move("up"))
        self.assertEqual(engine.turn_count, 1)
        self.assertFalse(engine.move("up"))
        self.assertEqual(engine.turn_count, 1)

    def test_objects_and_enemies_block_movement(self):
        self.area["objects"] = [
            {"type": "chest_object", "x": 2, "y": 1, "properties": {}}
        ]
        self.game["object_definitions"] = {
            "chest_object": {"walkable": False}
        }
        self._write_json(self.area_path, self.area)
        self._write_json(self.game_path, self.game)
        engine = self.engine()
        self.assertFalse(engine.move("right"))

        self.area["objects"][0]["properties"] = {"enemy_id": "enemy_1"}
        self._write_json(self.area_path, self.area)
        engine = self.engine()
        self.assertFalse(engine.move("right"))

    def test_show_message_trigger_runs_on_tile_entry(self):
        self._replace_triggers([{
            "x": 2, "y": 1, "name": "sign", "trigger_type": "show_message",
            "parameters": {"message": "Welcome."},
        }])
        messages = []
        engine = self.engine()
        engine.dialog_handler = messages.append
        self.assertTrue(engine.move("right"))
        self.assertEqual(messages, ["Welcome."])
        self.assertEqual(engine.turn_count, 1)

    def test_inventory_trigger_adds_and_removes_slots_atomically(self):
        self._replace_triggers([{
            "x": 2, "y": 1, "name": "reward", "trigger_type": "inventory",
            "parameters": {"add": "chest_object", "remove": "key_object"},
        }])
        engine = self.engine()
        self.assertTrue(engine.move("right"))
        self.assertEqual(engine.inventory[:2], ["chest_object", ""])

        full_inventory = ["item"] * 8
        engine.inventory = full_inventory[:]
        with self.assertRaisesRegex(RunnerError, "not in the inventory"):
            engine._apply_inventory_trigger({"add": "reward", "remove": "missing"})
        self.assertEqual(engine.inventory, full_inventory)

    def test_tile_update_trigger_preserves_walkability_override(self):
        self._replace_triggers([{
            "x": 2, "y": 1, "name": "bridge", "trigger_type": "tile_update",
            "parameters": {
                "x": 0, "y": 0, "tile": "lake_center", "walkable": True,
            },
        }])
        engine = self.engine()
        engine.move("right")
        tile = engine.current_area.tiles[0][0]
        self.assertEqual(tile.type, "lake_center")
        self.assertIs(tile.walkable_override, True)

    def test_area_object_trigger_adds_once_at_trigger_position(self):
        self._replace_triggers([{
            "x": 2, "y": 1, "name": "spawn", "trigger_type": "area_object",
            "parameters": {"area": "start", "object": "chest_object"},
        }])
        engine = self.engine()
        engine.move("right")
        self.assertEqual(
            [(obj.type, obj.x, obj.y) for obj in engine.current_area.objects],
            [("chest_object", 2, 1)],
        )
        engine._add_area_object(engine.current_area.triggers[0],
                                engine.current_area.triggers[0].parameters)
        self.assertEqual(len(engine.current_area.objects), 1)

    def test_teleport_trigger_changes_area_and_runs_destination_triggers(self):
        second_area = self._area(triggers=[{
            "x": 1, "y": 1, "name": "arrival", "trigger_type": "show_message",
            "parameters": {"message": "Arrived."},
        }])
        self._write_json(self.root / "areas" / "second.json", second_area)
        self.game["areas"] = ["start.json", "second.json"]
        self.game["properties"]["start_area"] = "start.json"
        self._write_json(self.game_path, self.game)
        self._replace_triggers([{
            "x": 2, "y": 1, "name": "door", "trigger_type": "teleport",
            "parameters": {"area": "second", "x": 1, "y": 1},
        }])
        messages = []
        engine = self.engine()
        engine.dialog_handler = messages.append
        engine.move("right")
        self.assertEqual(engine.current_area_filename, "second.json")
        self.assertEqual((engine.player_x, engine.player_y), (1, 1))
        self.assertEqual(messages, ["Arrived."])

    def test_teleport_trigger_cycle_is_stopped_and_reported(self):
        second_area = self._area(triggers=[{
            "x": 1, "y": 1, "name": "back", "trigger_type": "teleport",
            "parameters": {"area": "start", "x": 1, "y": 1},
        }])
        self._write_json(self.root / "areas" / "second.json", second_area)
        self.game["areas"] = ["start.json", "second.json"]
        self.game["properties"]["start_area"] = "start.json"
        self._write_json(self.game_path, self.game)
        self._replace_triggers([{
            "x": 1, "y": 1, "name": "forward", "trigger_type": "teleport",
            "parameters": {"area": "second", "x": 1, "y": 1},
        }])

        engine = self.engine()
        engine.process_entry_triggers()

        self.assertTrue(any("repeating teleport-trigger loop" in event for event in engine.events))

    def test_game_end_and_custom_triggers_have_clear_runtime_behavior(self):
        self._replace_triggers([{
            "x": 2, "y": 1, "name": "finish", "trigger_type": "game_end",
            "parameters": {"win_lose": "win", "message": "Victory!"},
        }])
        messages = []
        engine = self.engine()
        engine.dialog_handler = messages.append
        engine.move("right")
        self.assertTrue(engine.ended)
        self.assertEqual(engine.end_result, "win")
        self.assertEqual(messages, ["Victory!"])

        self._replace_triggers([{
            "x": 2, "y": 1, "name": "legacy", "trigger_type": "custom",
            "parameters": {"code": "raise Exception()"},
        }])
        engine = self.engine()
        engine.move("right")
        self.assertFalse(engine.ended)
        self.assertTrue(any("does not execute" in event for event in engine.events))

    def test_legacy_show_dialog_alias_is_supported(self):
        self._replace_triggers([{
            "x": 2, "y": 1, "name": "legacy", "trigger_type": "show_dialog",
            "parameters": {"message": "Old save."},
        }])
        messages = []
        engine = self.engine()
        engine.dialog_handler = messages.append
        engine.move("right")
        self.assertEqual(messages, ["Old save."])

    def test_invalid_area_file_fails_before_runner_startup(self):
        self._write_json(self.area_path, {"width": 2, "height": 2, "tiles": []})
        with self.assertRaisesRegex(RunnerError, "exactly 2 rows"):
            self.engine()

    def test_check_reports_success_without_creating_a_tk_window(self):
        engine = Mock(
            game_path=self.game_path,
            validation_issues=[],
        )
        output = io.StringIO()
        with (
            patch.object(tinker_runner, "RunnerEngine", return_value=engine),
            patch.object(tinker_runner.tk, "Tk") as tk_root,
            contextlib.redirect_stdout(output),
        ):
            result = tinker_runner.main(["--check", str(self.game_path)])

        self.assertEqual(result, 0)
        self.assertIn("No errors found.", output.getvalue())
        tk_root.assert_not_called()

    def test_runner_without_game_prompts_for_file_and_allows_cancel(self):
        root = Mock()
        with (
            patch.object(tinker_runner.tk, "Tk", return_value=root),
            patch.object(
                tinker_runner.filedialog, "askopenfilename", return_value=""
            ) as choose_game,
            patch.object(tinker_runner, "RunnerEngine") as engine_factory,
        ):
            result = tinker_runner.main([])

        self.assertEqual(result, 0)
        choose_game.assert_called_once()
        self.assertEqual(
            choose_game.call_args.kwargs["initialdir"], project_paths.project_root() / "games"
        )
        root.destroy.assert_called_once_with()
        engine_factory.assert_not_called()

    def test_check_reports_validation_issues_with_failure_status(self):
        engine = Mock(
            game_path=self.game_path,
            validation_issues=["Trigger 'door': missing destination area."],
        )
        output = io.StringIO()
        with (
            patch.object(tinker_runner, "RunnerEngine", return_value=engine),
            patch.object(tinker_runner.tk, "Tk") as tk_root,
            contextlib.redirect_stdout(output),
        ):
            result = tinker_runner.main(["--check", str(self.game_path)])

        self.assertEqual(result, 1)
        self.assertIn("ERROR: Trigger 'door'", output.getvalue())
        tk_root.assert_not_called()

    def test_check_detects_missing_referenced_images(self):
        (self.root / "tiles" / "grass.png").unlink()
        engine = self.engine()
        self.assertTrue(any("tiles/grass.png" in issue for issue in engine.validation_issues))

    def test_save_and_load_restores_full_playthrough_state(self):
        engine = self.engine()
        engine.move("right")
        engine.health = 7
        engine.energy = 0
        engine.stats["gold"] = 11
        engine.inventory = ["key_object", "chest_object"] + [""] * 6
        engine.current_area.tiles[2][2] = Tile(
            type="lake_center", walkable_override=True
        )
        engine.current_area.objects.append(
            GameObject("chest_object", 0, 0, {"walkable": True})
        )
        save_path = self.root / "saves" / "My Adventure.save.json"
        save_path.parent.mkdir()
        original_game = self.game_path.read_bytes()
        engine.save_to_file(save_path, "My Adventure")

        self.assertEqual(self.game_path.read_bytes(), original_game)
        self.game_path.unlink()
        self.area_path.unlink()

        loaded = RunnerEngine.load_save(save_path, project_root=self.root)
        self.assertEqual(loaded.save_name, "My Adventure")
        self.assertEqual((loaded.player_x, loaded.player_y), (2, 1))
        self.assertEqual(loaded.health, 7)
        self.assertEqual(loaded.stats["gold"], 11)
        self.assertEqual(
            loaded.inventory, ["key_object", "chest_object"] + [""] * 6
        )
        self.assertEqual(
            loaded.current_area.tiles[2][2],
            Tile(type="lake_center", walkable_override=True),
        )
        self.assertEqual(
            [(obj.type, obj.x, obj.y) for obj in loaded.current_area.objects],
            [("chest_object", 0, 0)],
        )
        self.assertEqual(loaded.turn_count, 1)

    def test_load_save_rejects_invalid_player_state(self):
        engine = self.engine()
        save_path = self.root / "bad.save.json"
        engine.save_to_file(save_path, "Bad Save")
        data = json.loads(save_path.read_text(encoding="utf-8"))
        data["player"]["health"] = 999
        self._write_json(save_path, data)

        with self.assertRaisesRegex(RunnerError, "health"):
            RunnerEngine.load_save(save_path, project_root=self.root)

    def test_save_name_comes_from_the_selected_save_filename(self):
        self.assertEqual(
            tinker_runner.TinkerRunner._save_name_from_path(
                "/tmp/My Adventure.save.json"
            ),
            "My Adventure",
        )
        self.assertEqual(
            tinker_runner.TinkerRunner._save_name_from_path("/tmp/Adventure.json"),
            "Adventure",
        )


if __name__ == "__main__":
    unittest.main()
