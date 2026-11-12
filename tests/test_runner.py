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

    def test_missing_start_settings_are_actionable(self):
        self.game["properties"].pop("start_area")
        self._write_json(self.game_path, self.game)
        with self.assertRaisesRegex(RunnerError, "properties.start_area"):
            self.engine()

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
