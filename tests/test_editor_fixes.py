import importlib.util
import json
import os
import tempfile
import unittest
from unittest.mock import Mock, patch

from data_classes import Area, Game, GameObject, Trigger
from dialog_tools import DialogTools
import editor_methods
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
        self.object_definition_frame = Mock()
        self.tile_walkable_frame = Mock()
        self.details_label = Mock()
        self.load_object_definition_editor = Mock()

    def update_tile_display(self):
        pass

    def update_properties_display(self):
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
    def __init__(self, triggers, selected_mode=None, selected_tile="teleport"):
        self.current_area = Area(triggers=triggers)
        self.current_game = Game()
        self.selected_mode = selected_mode
        self.selected_tile = selected_tile
        self.cursor_x = 0
        self.cursor_y = 0
        self.selected_trigger_index = 0
        self.tile_manager = Mock()
        self.tile_manager.get_tile_info.return_value = {"display_name": "Empty"}
        self.tile_manager.get_default_walkable.return_value = True
        self.tile_manager.get_npc_names.return_value = []
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

    @patch("editor_methods.ttk.Button")
    @patch("editor_methods.tk.Text")
    @patch("editor_methods.ttk.Frame")
    @patch("editor_methods.tk.Toplevel")
    def test_message_dialog_reserves_bottom_row_for_save_buttons(
        self, toplevel, frame_factory, text_factory, button_factory
    ):
        editor = object.__new__(EditorMethods)
        editor.root = Mock()
        editor.current_game = Game()
        dialog = Mock()
        button_frame = Mock()
        message_text = Mock()
        toplevel.return_value = dialog
        frame_factory.return_value = button_frame
        text_factory.return_value = message_text
        layout_order = []
        button_frame.pack.side_effect = lambda **_kwargs: layout_order.append("buttons")
        message_text.pack.side_effect = lambda **_kwargs: layout_order.append("text")

        editor.edit_game_message("intro")

        self.assertEqual(button_frame.pack.call_args.kwargs["side"], editor_methods.tk.BOTTOM)
        self.assertLess(layout_order.index("buttons"), layout_order.index("text"))
        self.assertEqual(button_factory.call_count, 2)

    def test_help_modes_block_map_clicks_and_keys(self):
        for mode in ("messages", "editor_help"):
            with self.subTest(mode=mode):
                editor = Mock()
                editor.selected_mode = mode
                editor._trigger_position_picker = None
                editor.root.focus_get.return_value = editor.canvas
                editor.on_canvas_click = EditorMethods.on_canvas_click.__get__(editor)
                editor.on_key_press = EditorMethods.on_key_press.__get__(editor)

                editor.on_canvas_click(Mock(x=20, y=20))
                result = editor.on_key_press(Mock(keysym="space"))

                editor.canvas.focus_set.assert_not_called()
                self.assertEqual(result, "break")

    def test_map_click_during_tile_update_edit_sets_target_without_moving_cursor(self):
        editor = Mock()
        editor._trigger_position_picker = None
        editor.selected_mode = "trigger"
        editor._trigger_editor_trigger = Trigger(x=1, y=2, trigger_type="tile_update")
        editor._trigger_editor_draft_type = "tile_update"
        editor._trigger_editor_vars = {"x": Mock(), "y": Mock()}
        editor.canvas.canvasx.return_value = 70
        editor.canvas.canvasy.return_value = 40
        editor.current_area = Area(width=6, height=4)
        editor.tile_size = 32
        editor.cursor_x = 0
        editor.cursor_y = 0
        editor.selected_trigger_index = 0
        editor.on_canvas_click = EditorMethods.on_canvas_click.__get__(editor)

        result = editor.on_canvas_click(Mock(x=70, y=40))

        editor.canvas.focus_set.assert_called_once_with()
        editor._trigger_editor_vars["x"].set.assert_called_once_with("2")
        editor._trigger_editor_vars["y"].set.assert_called_once_with("1")
        editor.save_selected_trigger.assert_not_called()
        editor.update_properties_display.assert_not_called()
        editor.refresh_trigger_editor.assert_not_called()
        self.assertEqual((editor.cursor_x, editor.cursor_y), (0, 0))
        self.assertEqual(result, "break")

    def test_map_click_outside_area_during_tile_update_edit_does_not_save(self):
        editor = Mock()
        editor._trigger_position_picker = None
        editor.selected_mode = "trigger"
        editor._trigger_editor_trigger = Trigger(x=1, y=2, trigger_type="tile_update")
        editor._trigger_editor_draft_type = "tile_update"
        editor._trigger_editor_vars = {"x": Mock(), "y": Mock()}
        editor.canvas.canvasx.return_value = 200
        editor.canvas.canvasy.return_value = 40
        editor.current_area = Area(width=6, height=4)
        editor.tile_size = 32
        editor.cursor_x = 0
        editor.cursor_y = 0
        editor.on_canvas_click = EditorMethods.on_canvas_click.__get__(editor)

        result = editor.on_canvas_click(Mock(x=200, y=40))

        editor._trigger_editor_vars["x"].set.assert_not_called()
        editor._trigger_editor_vars["y"].set.assert_not_called()
        editor.save_selected_trigger.assert_not_called()
        self.assertEqual((editor.cursor_x, editor.cursor_y), (0, 0))
        self.assertEqual(result, "break")

    def test_inline_coordinate_picker_sets_target_without_moving_trigger_cursor(self):
        editor = Mock()
        picker = {
            "x_var": Mock(),
            "y_var": Mock(),
        }
        editor._trigger_position_picker = picker
        editor.canvas.canvasx.return_value = 70
        editor.canvas.canvasy.return_value = 40
        editor.current_area = Area(width=6, height=4)
        editor.tile_size = 32
        editor.cursor_x = 1
        editor.cursor_y = 2
        editor.on_canvas_click = EditorMethods.on_canvas_click.__get__(editor)

        result = editor.on_canvas_click(Mock(x=70, y=40))

        picker["x_var"].set.assert_called_once_with("2")
        picker["y_var"].set.assert_called_once_with("1")
        self.assertIsNone(editor._trigger_position_picker)
        self.assertEqual((editor.cursor_x, editor.cursor_y), (1, 2))
        self.assertEqual(result, "break")

    def test_mouse_position_shows_0_based_map_coordinates(self):
        editor = Mock()
        editor.canvas.canvasx.return_value = 70
        editor.canvas.canvasy.return_value = 40
        editor.current_area = Area(width=6, height=4)
        editor.tile_size = 32
        editor.on_canvas_motion = EditorMethods.on_canvas_motion.__get__(editor)

        editor.on_canvas_motion(Mock(x=10, y=8))

        editor.mouse_position_label.config.assert_called_once_with(
            text="Mouse: (2, 1)"
        )

    def test_mouse_position_clears_outside_area_and_on_leave(self):
        editor = Mock()
        editor.canvas.canvasx.return_value = 200
        editor.canvas.canvasy.return_value = 40
        editor.current_area = Area(width=6, height=4)
        editor.tile_size = 32
        editor.on_canvas_motion = EditorMethods.on_canvas_motion.__get__(editor)
        editor.on_canvas_leave = EditorMethods.on_canvas_leave.__get__(editor)

        editor.on_canvas_motion(Mock(x=10, y=8))
        editor.mouse_position_label.config.assert_called_once_with(text="Mouse: --")

        editor.mouse_position_label.config.reset_mock()
        editor.on_canvas_leave()
        editor.mouse_position_label.config.assert_called_once_with(text="Mouse: --")

    def test_switching_trigger_selection_saves_current_form(self):
        editor = object.__new__(EditorMethods)
        editor.current_area = Area(
            width=3,
            height=3,
            triggers=[
                Trigger(x=0, y=0, trigger_type="show_message"),
                Trigger(x=0, y=0, trigger_type="show_message"),
            ],
        )
        editor.cursor_x = 0
        editor.cursor_y = 0
        editor.selected_mode = "trigger"
        editor.selected_trigger_index = 0
        editor.save_selected_trigger = Mock(return_value=True)
        editor.refresh_trigger_editor = Mock()
        editor.update_properties_display = Mock()
        editor.draw_area = Mock()

        self.assertTrue(editor.select_trigger_index(1))

        editor.save_selected_trigger.assert_called_once_with(
            show_error=True, refresh=False
        )
        self.assertEqual(editor.selected_trigger_index, 1)
        editor.refresh_trigger_editor.assert_called_once_with()
        editor.draw_area.assert_called_once_with()

    def test_saving_type_change_replaces_old_parameters(self):
        trigger = Trigger(
            x=0,
            y=0,
            trigger_type="teleport",
            parameters={"area": "old_area", "x": 5, "y": 6, "obsolete": True},
        )
        editor = object.__new__(EditorMethods)
        editor.selected_mode = "trigger"
        editor._trigger_editor_trigger = trigger
        editor._trigger_editor_type_labels = {"Show Message": "show_message"}
        editor._trigger_editor_vars = {
            "name": Mock(get=Mock(return_value="Updated")),
            "trigger_type": Mock(get=Mock(return_value="Show Message")),
            "message": Mock(get=Mock(return_value="Door opened")),
        }
        editor._trigger_coordinate_error = Mock(return_value=None)
        editor.refresh_trigger_editor = Mock()
        editor.update_properties_display = Mock()
        editor.draw_area = Mock()

        self.assertTrue(editor.save_selected_trigger())

        self.assertEqual(trigger.trigger_type, "show_message")
        self.assertEqual(trigger.name, "Updated")
        self.assertEqual(trigger.parameters, {"message": "Door opened"})

    def test_delete_removes_only_the_selected_trigger(self):
        first_trigger = Trigger(x=1, y=1, trigger_type="show_message")
        second_trigger = Trigger(x=1, y=1, trigger_type="show_message")
        other_location_trigger = Trigger(x=2, y=1, trigger_type="show_message")
        editor = object.__new__(EditorMethods)
        editor.current_area = Area(
            width=4,
            height=3,
            triggers=[first_trigger, second_trigger, other_location_trigger],
        )
        editor.cursor_x = 1
        editor.cursor_y = 1
        editor.selected_trigger_index = 1
        editor.refresh_trigger_editor = Mock()
        editor.update_properties_display = Mock()
        editor.draw_area = Mock()

        self.assertTrue(editor.delete_selected_trigger())

        self.assertEqual(
            editor.current_area.triggers, [first_trigger, other_location_trigger]
        )
        self.assertEqual(editor.selected_trigger_index, 0)

    def test_numbered_trigger_stack_uses_selected_trigger_color(self):
        editor = object.__new__(EditorMethods)
        editor.current_area = Area(
            width=1,
            height=1,
            triggers=[
                Trigger(x=0, y=0, trigger_type="teleport"),
                Trigger(x=0, y=0, trigger_type="tile_update"),
                Trigger(x=0, y=0, trigger_type="show_message"),
            ],
        )
        editor.cursor_x = 0
        editor.cursor_y = 0
        editor.selected_trigger_index = 1
        editor.tile_size = 32
        editor.tile_manager = Mock()
        editor.tile_manager.get_tile_info.return_value = {"image": "tile"}
        editor.trigger_colors = {
            "teleport": "#0066CC",
            "tile_update": "#FFCC00",
        }
        editor.canvas = Mock()
        editor.cursor_label = Mock()

        editor.draw_area()

        self.assertEqual(
            editor.canvas.create_polygon.call_args.kwargs["fill"], "#FFCC00"
        )
        self.assertEqual(editor.canvas.create_text.call_args.kwargs["text"], "2")
        self.assertEqual(editor.canvas.create_text.call_args.kwargs["fill"], "black")

    def test_placing_same_trigger_type_adds_another_trigger(self):
        existing_trigger = Trigger(
            x=1, y=1, trigger_type="tile_update", name="door_trigger"
        )
        other_trigger = Trigger(
            x=1, y=1, trigger_type="show_message", name="welcome_trigger"
        )
        editor = object.__new__(EditorMethods)
        editor.selected_mode = "trigger"
        editor.selected_tile = "tile_update"
        editor.current_area = Area(
            width=4, height=3, triggers=[existing_trigger, other_trigger]
        )
        editor.cursor_x = 1
        editor.cursor_y = 1
        editor.selected_trigger_index = 0
        editor.draw_area = Mock()
        editor.update_properties_display = Mock()
        editor.get_next_trigger_name = Mock(return_value="trigger_2")

        editor.place_tile()

        self.assertEqual(len(editor.current_area.triggers), 3)
        new_trigger = editor.current_area.triggers[-1]
        self.assertEqual(new_trigger.trigger_type, "tile_update")
        self.assertEqual(new_trigger.name, "trigger_2")
        self.assertEqual((new_trigger.x, new_trigger.y), (1, 1))
        self.assertEqual(editor.selected_trigger_index, 2)
        editor.draw_area.assert_called_once_with()
        editor.update_properties_display.assert_called_once_with()

    def test_tenth_trigger_is_allowed_but_eleventh_is_rejected(self):
        triggers = [
            Trigger(x=1, y=1, trigger_type="show_message", name=f"trigger_{index}")
            for index in range(1, 10)
        ]
        editor = object.__new__(EditorMethods)
        editor.selected_mode = "trigger"
        editor.selected_tile = "show_message"
        editor.current_area = Area(width=4, height=3, triggers=triggers)
        editor.cursor_x = 1
        editor.cursor_y = 1
        editor.selected_trigger_index = 0
        editor.draw_area = Mock()
        editor.update_properties_display = Mock()
        editor.get_next_trigger_name = Mock(return_value="trigger_10")
        editor.refresh_trigger_editor = Mock()
        editor.save_selected_trigger = Mock(return_value=True)

        editor.place_tile()
        self.assertEqual(len(editor.current_area.triggers), 10)

        with patch("editor_methods.messagebox.showwarning") as showwarning:
            editor.place_tile()

        self.assertEqual(len(editor.current_area.triggers), 10)
        showwarning.assert_called_once()

    def test_fill_empty_tiles_preserves_existing_tiles(self):
        editor = object.__new__(EditorMethods)
        editor.selected_mode = "tile"
        editor.selected_tile = "grass"
        editor.current_area = Area(width=3, height=2)
        editor.current_area.tiles[0][1].type = "forest"
        editor.current_area.tiles[1][2].type = "swamp"
        editor.draw_area = Mock()
        editor.update_properties_display = Mock()

        filled_count = editor.fill_empty_tiles()

        self.assertEqual(filled_count, 4)
        self.assertEqual(
            [[tile.type for tile in row] for row in editor.current_area.tiles],
            [["grass", "forest", "grass"], ["grass", "grass", "swamp"]],
        )
        editor.draw_area.assert_called_once_with()
        editor.update_properties_display.assert_called_once_with()

    @patch("editor_methods.messagebox.showwarning")
    def test_fill_empty_tiles_requires_tile_mode(self, showwarning):
        editor = object.__new__(EditorMethods)
        editor.selected_mode = "object"
        editor.current_area = Area(width=2, height=2)
        editor.draw_area = Mock()
        editor.update_properties_display = Mock()

        self.assertEqual(editor.fill_empty_tiles(), 0)

        self.assertTrue(all(tile.type == "empty" for row in editor.current_area.tiles for tile in row))
        showwarning.assert_called_once()
        editor.draw_area.assert_not_called()
        editor.update_properties_display.assert_not_called()

    def test_right_click_places_selected_tool_at_clicked_cell(self):
        editor = Mock()
        editor._trigger_position_picker = None
        editor.selected_mode = "tile"
        editor.canvas.canvasx.return_value = 70
        editor.canvas.canvasy.return_value = 40
        editor.current_area = Area(width=6, height=4)
        editor.tile_size = 32
        editor.on_canvas_right_click = EditorMethods.on_canvas_right_click.__get__(editor)

        result = editor.on_canvas_right_click(Mock(x=70, y=40))

        self.assertEqual((editor.cursor_x, editor.cursor_y), (2, 1))
        editor.canvas.focus_set.assert_called_once_with()
        editor.place_tile.assert_called_once_with()
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
        ask_save.return_value = "/tmp/My Game.json"
        manager._save_game_to_file = Mock(return_value=False)

        manager.save_game_as()
        self.assertIsNone(manager.current_game_file)
        self.assertEqual(
            manager._save_game_to_file.call_args.args[0], "/tmp/My_Game.json"
        )

        manager._save_game_to_file.return_value = True
        manager.save_game_as()
        self.assertEqual(manager.current_game_file, "/tmp/My_Game.json")

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
        ask_save.return_value = area_path.replace("unit_test_area", "unit test area")
        manager._save_area_to_file = Mock(return_value=False)

        manager.save_area_as()
        self.assertIsNone(manager.current_area_file)
        manager._save_area_to_file.assert_called_with(area_path)

        manager._save_area_to_file.return_value = True
        manager.save_area_as()
        self.assertEqual(manager.current_area_file, area_path)

    @patch("file_manager.messagebox.askyesno", return_value=False)
    @patch("file_manager.filedialog.asksaveasfilename")
    def test_save_area_as_confirms_overwriting_existing_area(
        self, ask_save, confirm_overwrite
    ):
        manager = FileManagerHarness()
        with tempfile.TemporaryDirectory() as directory:
            areas_dir = os.path.join(directory, "areas")
            os.makedirs(areas_dir)
            area_path = os.path.join(areas_dir, "main_map.json")
            with open(area_path, "w") as existing_area:
                existing_area.write("{}")
            manager._project_path = lambda *parts: os.path.join(directory, *parts)
            ask_save.return_value = area_path
            manager._save_area_to_file = Mock(return_value=True)

            manager.save_area_as()

        confirm_overwrite.assert_called_once_with(
            "Area Already Exists",
            "An area named 'main_map' already exists. Do you want to overwrite it?",
        )
        manager._save_area_to_file.assert_not_called()
        self.assertIsNone(manager.current_area_file)

    @patch("file_manager.messagebox.askyesno", return_value=True)
    @patch("file_manager.filedialog.asksaveasfilename")
    def test_save_area_as_overwrites_after_confirmation(
        self, ask_save, confirm_overwrite
    ):
        manager = FileManagerHarness()
        with tempfile.TemporaryDirectory() as directory:
            areas_dir = os.path.join(directory, "areas")
            os.makedirs(areas_dir)
            area_path = os.path.join(areas_dir, "main_map.json")
            with open(area_path, "w") as existing_area:
                existing_area.write("{}")
            manager._project_path = lambda *parts: os.path.join(directory, *parts)
            ask_save.return_value = area_path
            manager._save_area_to_file = Mock(return_value=True)

            manager.save_area_as()

        confirm_overwrite.assert_called_once()
        manager._save_area_to_file.assert_called_once_with(area_path)
        self.assertEqual(manager.current_area_file, area_path)

    def test_game_name_field_updates_current_game_name(self):
        editor = object.__new__(EditorMethods)
        editor.current_game = Game()
        editor.game_name_var = Mock()
        editor.game_name_var.get.return_value = "Castle Adventure"

        editor.on_game_name_change()

        self.assertEqual(editor.current_game.name, "Castle Adventure")

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

    @patch("file_manager.messagebox.showinfo")
    def test_area_references_use_filenames_as_ids(self, _showinfo):
        manager = FileManagerHarness()
        manager.current_area = Area(name="Great Hall")
        manager.game_areas_listbox = Mock()

        with tempfile.TemporaryDirectory() as directory:
            os.makedirs(os.path.join(directory, "areas"))
            first_path = os.path.join(directory, "areas", "great-hall.json")
            second_path = os.path.join(directory, "areas", "fountain-room.json")
            manager._project_path = lambda *parts: os.path.join(directory, *parts)

            self.assertTrue(manager._save_area_to_file(first_path))
            manager.current_area_file = first_path
            manager.add_area_to_game()
            self.assertEqual(manager.current_game.areas, ["great-hall.json"])
            manager.game_areas_listbox.delete.assert_called_once_with(0, "end")
            manager.game_areas_listbox.insert.assert_called_once_with("end", "great-hall")

    def test_game_area_list_shows_empty_game_state(self):
        manager = FileManagerHarness()
        manager.game_areas_listbox = Mock()

        manager.refresh_game_areas_list()

        manager.game_areas_listbox.delete.assert_called_once_with(0, "end")
        manager.game_areas_listbox.insert.assert_called_once_with(
            "end", "(No areas in this game)"
        )

    def test_selecting_game_area_loads_its_file(self):
        manager = FileManagerHarness()
        manager.current_game.areas = ["great-hall.json", "fountain-room.json"]
        manager.game_areas_listbox = Mock()
        manager.game_areas_listbox.curselection.return_value = (1,)
        manager._load_area_from_file = Mock()

        manager.load_selected_game_area()

        manager._load_area_from_file.assert_called_once_with(
            manager._project_path("areas", "fountain-room.json"),
            show_message=False,
        )

    def test_selecting_empty_game_area_placeholder_does_not_load(self):
        manager = FileManagerHarness()
        manager.current_game.areas = []
        manager.game_areas_listbox = Mock()
        manager.game_areas_listbox.curselection.return_value = (0,)
        manager._load_area_from_file = Mock()

        manager.load_selected_game_area()

        manager._load_area_from_file.assert_not_called()

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
                if mode == "object":
                    editor.object_definition_frame.pack.assert_called_once()
                    editor.tile_walkable_frame.pack_forget.assert_called_once()
                    editor.load_object_definition_editor.assert_called_once()
                elif mode == "trigger":
                    editor.object_definition_frame.pack_forget.assert_called_once()
                    editor.tile_walkable_frame.pack_forget.assert_called_once()
                    editor.tile_walkable_frame.pack.assert_not_called()
                    editor.load_object_definition_editor.assert_not_called()
                else:
                    editor.object_definition_frame.pack_forget.assert_called_once()
                    editor.tile_walkable_frame.pack.assert_called_once()
                    editor.load_object_definition_editor.assert_not_called()

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

    def test_outdoor_tile_walkability_defaults(self):
        manager = object.__new__(TileManager)

        for tile_name in ("grass", "forest", "swamp", "town", "castle"):
            with self.subTest(tile=tile_name):
                self.assertTrue(manager.get_default_walkable(tile_name))

        for tile_name in (
            "mountains",
            "lake_left",
            "lake_right",
            "lake_top",
            "lake_bottom",
            "lake_center",
        ):
            with self.subTest(tile=tile_name):
                self.assertFalse(manager.get_default_walkable(tile_name))

    def test_object_definition_defaults_and_partial_effects(self):
        game = Game(object_definitions={
            "sword_object": {
                "gettable": True,
                "effects": {"attack": 5},
            },
        })

        definition = game.get_object_definition("sword_object")

        self.assertTrue(definition["gettable"])
        self.assertTrue(definition["walkable"])
        self.assertEqual(definition["effect_mode"], "passive")
        self.assertEqual(
            definition["effects"],
            {"health": 0, "energy": 0, "armor": 0, "attack": 5},
        )
        self.assertEqual(game.object_definitions["sword_object"]["effects"], {"attack": 5})

    def test_object_definitions_round_trip_in_game_save_data(self):
        manager = FileManagerHarness()
        manager.current_game.object_definitions["bread_object"] = {
            "gettable": True,
            "walkable": True,
            "effect_mode": "consumable",
            "effects": {"health": 10, "energy": 0, "armor": 0, "attack": 0},
        }

        with tempfile.TemporaryDirectory() as directory:
            game_path = os.path.join(directory, "game.json")
            with patch("file_manager.messagebox.showinfo"):
                self.assertTrue(manager._save_game_to_file(game_path))
            with open(game_path, "r") as game_file:
                saved_game = Game(**json.load(game_file))

        self.assertEqual(saved_game.get_object_definition("bread_object")["effect_mode"], "consumable")
        self.assertEqual(saved_game.get_object_definition("bread_object")["effects"]["health"], 10)

    def test_object_walkability_comes_from_shared_definition_with_instance_override(self):
        editor = object.__new__(EditorMethods)
        editor.current_game = Game(object_definitions={
            "chest_object": {"walkable": False},
        })
        editor.current_area = Area(objects=[GameObject(type="chest_object", x=0, y=0)])
        editor.tile_manager = Mock()
        editor.tile_manager.get_npc_names.return_value = []
        editor.tile_manager.get_default_walkable.return_value = True

        self.assertTrue(editor.is_tile_blocked(0, 0))
        editor.current_area.objects[0].properties["walkable"] = True
        self.assertFalse(editor.is_tile_blocked(0, 0))

    def test_object_mode_details_show_definition_and_signed_effects(self):
        editor = PropertiesDisplayHarness([], selected_mode="object", selected_tile="sword_object")
        editor.current_game.object_definitions["sword_object"] = {
            "gettable": True,
            "walkable": True,
            "effect_mode": "passive",
            "effects": {"attack": 5},
        }

        editor.update_properties_display()

        self.assertIn("Gettable: True", editor.rendered_text)
        self.assertIn("Effect mode: passive", editor.rendered_text)
        self.assertIn("attack +5", editor.rendered_text)

    def test_right_panel_save_applies_object_definition_to_current_game(self):
        editor = object.__new__(EditorMethods)
        editor.selected_mode = "object"
        editor.selected_tile = "sword_object"
        editor.current_game = Game()
        editor.draw_area = Mock()
        editor.update_properties_display = Mock()
        editor.object_gettable_var = Mock(get=Mock(return_value=True))
        editor.object_walkable_var = Mock(get=Mock(return_value=False))
        editor.object_effect_mode_var = Mock(get=Mock(return_value="passive"))
        editor.object_effect_vars = {
            stat: Mock(get=Mock(return_value=str(value)))
            for stat, value in {"health": 0, "energy": -2, "armor": 1, "attack": 5}.items()
        }

        editor.save_object_definition_changes()

        self.assertEqual(editor.current_game.object_definitions["sword_object"], {
            "gettable": True,
            "walkable": False,
            "effect_mode": "passive",
            "effects": {"health": 0, "energy": -2, "armor": 1, "attack": 5},
        })
        editor.draw_area.assert_called_once()
        editor.update_properties_display.assert_called_once()

    def test_non_gettable_object_save_clears_inventory_effects(self):
        editor = object.__new__(EditorMethods)
        editor.selected_mode = "object"
        editor.selected_tile = "fountain_object"
        editor.current_game = Game()
        editor.draw_area = Mock()
        editor.update_properties_display = Mock()
        editor.object_gettable_var = Mock(get=Mock(return_value=False))
        editor.object_walkable_var = Mock(get=Mock(return_value=True))
        editor.object_effect_mode_var = Mock(get=Mock(return_value="consumable"))
        editor.object_effect_vars = {
            stat: Mock(get=Mock(return_value="25" if stat == "health" else "0"))
            for stat in ("health", "energy", "armor", "attack")
        }

        editor.save_object_definition_changes()

        self.assertEqual(editor.current_game.object_definitions["fountain_object"], {
            "gettable": False,
            "walkable": True,
            "effect_mode": "consumable",
            "effects": {
            "health": 0, "energy": 0, "armor": 0, "attack": 0,
            },
        })

    def test_gettable_toggle_shows_and_hides_inventory_effects(self):
        editor = object.__new__(EditorMethods)
        editor.object_gettable_var = Mock()
        editor.object_effects_frame = Mock()

        editor.object_gettable_var.get.return_value = True
        editor.on_object_gettable_change()
        editor.object_effects_frame.pack.assert_called_once()
        editor.object_effects_frame.pack_forget.assert_not_called()

        editor.object_gettable_var.get.return_value = False
        editor.on_object_gettable_change()
        editor.object_effects_frame.pack_forget.assert_called_once()

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

    def test_selected_toolbox_trigger_description_is_shown_above_details(self):
        editor = PropertiesDisplayHarness([], selected_mode="trigger", selected_tile="inventory")

        editor.update_properties_display()

        self.assertTrue(editor.rendered_text.startswith(
            "Trigger type: Adds or removes an item from the player's inventory."
        ))
        self.assertLess(
            editor.rendered_text.index("Trigger type:"),
            editor.rendered_text.index("Position:"),
        )

    def test_clicking_toolbox_trigger_refreshes_details(self):
        editor = Mock()
        editor.tile_canvas.find_closest.return_value = [1]
        editor.tile_canvas.gettags.return_value = ("trigger_show_message",)
        editor.on_tile_canvas_click = EditorMethods.on_tile_canvas_click.__get__(editor)

        editor.on_tile_canvas_click(Mock(x=10, y=10))

        self.assertEqual(editor.selected_tile, "show_message")
        editor.update_tile_display.assert_called_once()
        editor.update_properties_display.assert_called_once()

    def test_legacy_show_dialog_type_is_loaded_as_show_message(self):
        trigger = Trigger(trigger_type="show_dialog", parameters={"message": "Hello"})

        self.assertEqual(trigger.trigger_type, "show_message")
        self.assertIn("Hello", trigger.get_description())


if __name__ == "__main__":
    unittest.main()
