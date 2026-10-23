import importlib.util
import json
import os
import tempfile
import unittest
from unittest.mock import Mock, patch

from data_classes import Area, Game, Trigger
from dialog_tools import DialogTools
from editor_methods import EditorMethods
from file_manager import FileManager
import tile_manager
from tile_manager import TileManager

MAIN_MODULE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tinker-main.py")
MAIN_MODULE_SPEC = importlib.util.spec_from_file_location("tinker_main", MAIN_MODULE_PATH)
tinker_main = importlib.util.module_from_spec(MAIN_MODULE_SPEC)
MAIN_MODULE_SPEC.loader.exec_module(tinker_main)


class ResizeHarness(DialogTools):
    def __init__(self):
        self.current_area = Area()
        self.cursor_x = 0
        self.cursor_y = 0

    def draw_area(self):
        pass

    def update_properties_display(self):
        pass


class FileManagerHarness(FileManager):
    def __init__(self):
        self.current_game = Game()
        self.current_area = Area()
        self.current_area_file = None
        self.current_game_file = None


class ModeHarness(EditorMethods):
    def __init__(self, mode, assets):
        self.mode_var = Mock()
        self.mode_var.get.return_value = mode
        self.tile_manager = assets
        self.selected_tile = "previous-selection"

    def update_tile_display(self):
        pass


class AssetNames:
    def get_tile_names(self):
        return ["stone", "floor"]

    def get_object_names(self):
        return ["chest", "lever"]

    def get_npc_names(self):
        return ["guard", "wizard"]


class TriggerValidationHarness(EditorMethods):
    def __init__(self):
        self.current_game = Game(areas=["fountain_room.json"])
        self.current_area = Area(width=20, height=15)
        self.current_area_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..",
            "areas",
            "fountain_room.json",
        )


class AreaLoadingHarness(FileManagerHarness):
    def __init__(self):
        super().__init__()
        self.area_name_var = Mock()
        self.draw_area = Mock()
        self.update_properties_display = Mock()


class PropertiesDisplayHarness(EditorMethods):
    def __init__(self, triggers):
        self.current_area = Area(triggers=triggers)
        self.cursor_x = 0
        self.cursor_y = 0
        self.selected_trigger_index = 0
        self.tile_manager = Mock()
        self.tile_manager.get_tile_info.return_value = {"display_name": "Empty"}
        self.tile_manager.get_default_walkable.return_value = True
        self.properties_text = Mock()
        self.global_walkable_label = Mock()
        self.walkable_override_var = Mock()
        self.rendered_text = ""
        self.properties_text.insert.side_effect = self.capture_text

    def capture_text(self, _position, text):
        self.rendered_text = text


class ToolboxCanvas:
    def __init__(self):
        self.items = []

    def delete(self, _tag):
        self.items.clear()

    def create_text(self, *args, **kwargs):
        self.items.append((args, kwargs))

    def bbox(self, _tag):
        return (0, 0, 200, max(1, len(self.items) * 50))

    def configure(self, **_kwargs):
        pass

    def find_closest(self, *_args):
        return [1]

    def gettags(self, _item):
        return ("message_intro",)


class ToolboxDisplayHarness(EditorMethods):
    def __init__(self, mode):
        self.selected_mode = mode
        self.selected_tile = "stone"
        self.tile_canvas = ToolboxCanvas()
        self.selected_tile_label = Mock()


class EditorFixTests(unittest.TestCase):
    @patch("PIL.ImageTk.PhotoImage")
    def test_app_icon_uses_gargoyle_art(self, photo_image):
        editor = object.__new__(tinker_main.TinkerEditor)
        editor.root = Mock()

        editor.set_app_icon()

        icon_image = photo_image.call_args.args[0]
        self.assertEqual(icon_image.size, (128, 128))
        self.assertEqual(editor.app_icon, photo_image.return_value)
        editor.root.iconphoto.assert_called_once_with(True, photo_image.return_value)

    def test_game_messages_are_saved_with_game_data(self):
        manager = FileManagerHarness()
        manager.current_game.intro_message = "Welcome"
        manager.current_game.instructions_message = "Find the key"
        manager.current_game.game_end_message = "You win!"

        with tempfile.TemporaryDirectory() as directory:
            game_path = os.path.join(directory, "game.json")
            with patch("file_manager.messagebox.showinfo"):
                self.assertTrue(manager._save_game_to_file(game_path))
            with open(game_path, "r") as game_file:
                saved_game = json.load(game_file)

        self.assertEqual(saved_game["intro_message"], "Welcome")
        self.assertEqual(saved_game["instructions_message"], "Find the key")
        self.assertEqual(saved_game["game_end_message"], "You win!")

    def test_messages_toolbox_lists_the_three_game_messages(self):
        editor = ToolboxDisplayHarness("messages")

        editor.update_tile_display()

        displayed_text = [item[1]["text"] for item in editor.tile_canvas.items]
        self.assertIn("Intro Message", displayed_text)
        self.assertIn("Help / Instructions Message", displayed_text)
        self.assertIn("Game End Message", displayed_text)

    def test_editor_help_mode_displays_instructions(self):
        editor = ToolboxDisplayHarness("editor_help")

        editor.update_tile_display()

        displayed_text = editor.tile_canvas.items[0][1]["text"]
        self.assertIn("EDITOR HELP", displayed_text)
        self.assertIn("Map navigation", displayed_text)

    def test_messages_mode_routes_toolbox_click_to_message_editor(self):
        editor = ToolboxDisplayHarness("messages")
        editor.edit_game_message = Mock()

        editor.on_tile_canvas_click(Mock(x=10, y=10))

        editor.edit_game_message.assert_called_once_with("intro")

    def test_help_modes_block_map_clicks_and_keys(self):
        for mode in ("messages", "editor_help"):
            with self.subTest(mode=mode):
                editor = Mock()
                editor.selected_mode = mode
                editor.root.focus_get.return_value = editor.canvas
                editor.on_canvas_click = EditorMethods.on_canvas_click.__get__(editor)
                editor.on_key_press = EditorMethods.on_key_press.__get__(editor)

                editor.on_canvas_click(Mock(x=20, y=20))
                result = editor.on_key_press(Mock(keysym="space"))

                editor.canvas.focus_set.assert_not_called()
                self.assertEqual(result, "break")

    @patch("dialog_tools.messagebox.showerror")
    @patch("dialog_tools.messagebox.showinfo")
    def test_resize_accepts_limit_and_rejects_larger_areas(self, _showinfo, _showerror):
        editor = ResizeHarness()

        self.assertFalse(editor.resize_canvas(101, 100))
        self.assertEqual((editor.current_area.width, editor.current_area.height), (20, 15))

        self.assertTrue(editor.resize_canvas(100, 100))
        self.assertEqual((editor.current_area.width, editor.current_area.height), (100, 100))
        self.assertEqual(len(editor.current_area.tiles), 100)
        self.assertEqual(len(editor.current_area.tiles[0]), 100)

    @patch("file_manager.messagebox.showerror")
    @patch("file_manager.messagebox.showinfo")
    def test_save_game_reports_success_or_failure(self, _showinfo, _showerror):
        manager = FileManagerHarness()

        with tempfile.TemporaryDirectory() as directory:
            game_path = os.path.join(directory, "game.json")
            self.assertTrue(manager._save_game_to_file(game_path))
            with open(game_path, "r") as saved_file:
                self.assertEqual(json.load(saved_file)["name"], manager.current_game.name)

            invalid_path = os.path.join(directory, "missing", "game.json")
            self.assertFalse(manager._save_game_to_file(invalid_path))

    @patch("file_manager.filedialog.asksaveasfilename")
    def test_save_game_as_updates_current_path_only_after_success(self, ask_save):
        manager = FileManagerHarness()
        ask_save.return_value = "/tmp/game.json"
        manager._save_game_to_file = Mock(return_value=False)

        manager.save_game_as()
        self.assertIsNone(manager.current_game_file)

        manager._save_game_to_file.return_value = True
        manager.save_game_as()
        self.assertEqual(manager.current_game_file, "/tmp/game.json")

    @patch("file_manager.messagebox.showerror")
    @patch("file_manager.messagebox.showinfo")
    @patch("file_manager.messagebox.showwarning")
    def test_save_all_reports_failed_writes_as_errors(self, showwarning, _showinfo, _showerror):
        manager = FileManagerHarness()
        manager.current_area_file = "/tmp/area.json"
        manager.current_game_file = "/tmp/game.json"
        manager._save_area_to_file = Mock(return_value=False)
        manager._save_game_to_file = Mock(return_value=False)
        manager.update_game_assets_silent = Mock()

        manager.save_all()

        showwarning.assert_called_once()
        report = showwarning.call_args.args[1]
        self.assertIn("Partially successful", report)
        self.assertIn("Failed to save area", report)
        self.assertIn("Failed to save game", report)

    @patch("file_manager.messagebox.showerror")
    @patch("file_manager.filedialog.asksaveasfilename")
    def test_save_area_as_rejects_outside_project_areas(self, ask_save, showerror):
        manager = FileManagerHarness()
        manager._save_area_to_file = Mock(return_value=True)
        with tempfile.TemporaryDirectory() as directory:
            ask_save.return_value = os.path.join(directory, "area.json")
            manager.save_area_as()

        manager._save_area_to_file.assert_not_called()
        self.assertIsNone(manager.current_area_file)
        showerror.assert_called_once()

    @patch("file_manager.filedialog.asksaveasfilename")
    def test_save_area_as_accepts_project_area_only_after_success(self, ask_save):
        manager = FileManagerHarness()
        area_path = manager._project_path("areas", "unit_test_area.json")
        ask_save.return_value = area_path
        manager._save_area_to_file = Mock(return_value=False)

        manager.save_area_as()
        self.assertIsNone(manager.current_area_file)

        manager._save_area_to_file.return_value = True
        manager.save_area_as()
        self.assertEqual(manager.current_area_file, area_path)

    @patch("file_manager.messagebox.showerror")
    def test_area_loader_rejects_dimensions_over_the_limit(self, showerror):
        manager = AreaLoadingHarness()
        original_area = manager.current_area

        with tempfile.TemporaryDirectory() as directory:
            area_path = os.path.join(directory, "too_large.json")
            with open(area_path, "w") as area_file:
                json.dump({"name": "Too Large", "width": 101, "height": 1}, area_file)
            manager._load_area_from_file(area_path, show_message=False)

        self.assertIs(manager.current_area, original_area)
        showerror.assert_called_once()

    def test_mode_change_selects_first_asset_for_each_mode(self):
        assets = AssetNames()
        for mode, selected in (
            ("tile", "stone"),
            ("object", "chest"),
            ("npc", "guard"),
            ("trigger", "teleport"),
            ("messages", "previous-selection"),
            ("editor_help", "previous-selection"),
        ):
            with self.subTest(mode=mode):
                editor = ModeHarness(mode, assets)
                editor.on_mode_change()
                self.assertEqual(editor.selected_tile, selected)

    def test_tile_assets_are_resolved_from_project_not_working_directory(self):
        manager = object.__new__(TileManager)
        manager.tiles = {}
        project_tiles = os.path.join(os.path.dirname(os.path.abspath(tile_manager.__file__)), "tiles")

        with tempfile.TemporaryDirectory() as directory:
            original_cwd = os.getcwd()
            try:
                os.chdir(directory)
                with patch("tile_manager.os.path.exists", return_value=True), \
                        patch("tile_manager.glob.glob", return_value=[]) as glob_files, \
                        patch.object(TileManager, "_create_default_tile"):
                    self.assertFalse(manager.load_tiles())
            finally:
                os.chdir(original_cwd)

        self.assertEqual(glob_files.call_args.args[0], os.path.join(project_tiles, "*.png"))

    def test_trigger_coordinates_are_checked_against_area_dimensions(self):
        editor = TriggerValidationHarness()

        self.assertIsNone(editor._trigger_coordinate_error(
            "tile_update", {"x": 19, "y": 14}
        ))
        self.assertIn("Coordinates", editor._trigger_coordinate_error(
            "tile_update", {"x": 20, "y": 14}
        ))
        self.assertIsNone(editor._trigger_coordinate_error(
            "teleport", {"area": "fountain_room", "x": 19, "y": 14}
        ))
        self.assertIn("Coordinates", editor._trigger_coordinate_error(
            "teleport", {"area": "fountain_room", "x": 20, "y": 14}
        ))
        self.assertIn("belongs to this game", editor._trigger_coordinate_error(
            "teleport", {"area": "unknown_area", "x": 0, "y": 0}
        ))

    def test_selected_trigger_description_is_shown_above_details(self):
        trigger = Trigger(
            x=0,
            y=0,
            trigger_type="show_message",
            parameters={"message": "Welcome"},
        )
        editor = PropertiesDisplayHarness([trigger])

        editor.update_properties_display()

        self.assertTrue(editor.rendered_text.startswith("Selected trigger: Message:"))
        self.assertLess(
            editor.rendered_text.index("Selected trigger:"),
            editor.rendered_text.index("Position:"),
        )
        self.assertIn("Welcome", editor.rendered_text)

    def test_legacy_show_dialog_type_is_loaded_as_show_message(self):
        trigger = Trigger(trigger_type="show_dialog", parameters={"message": "Hello"})

        self.assertEqual(trigger.trigger_type, "show_message")
        self.assertIn("Hello", trigger.get_description())


if __name__ == "__main__":
    unittest.main()
