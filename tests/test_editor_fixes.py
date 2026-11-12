import importlib.util
import json
import os
import tempfile
import unittest
from unittest.mock import Mock, patch

from PIL import Image

from data_classes import Area, Game, GameObject, Trigger
from dialog_tools import DialogTools
import editor_methods
from editor_methods import EditorMethods
from enemy_editor import EnemyEditor
from file_manager import FileManager
import tile_manager
from tile_manager import TileManager

MAIN_MODULE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tinker-edit.py")
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


class GameLifecycleTests(unittest.TestCase):
    def manager(self):
        from dataclasses import asdict
        manager = FileManagerHarness()
        manager.root = Mock()
        manager._saved_game_state = asdict(manager.current_game)
        manager._saved_area_state = asdict(manager.current_area)
        return manager

    @patch("file_manager.messagebox.askyesnocancel")
    def test_close_clean_editor_does_not_prompt(self, prompt):
        manager = self.manager()
        manager.close_editor()
        prompt.assert_not_called()
        manager.root.destroy.assert_called_once()

    @patch("file_manager.messagebox.askyesnocancel", return_value=None)
    def test_close_cancel_keeps_dirty_editor_open(self, prompt):
        manager = self.manager()
        manager.current_area.tiles[0][0].type = "grass"
        manager.close_editor()
        prompt.assert_called_once()
        manager.root.destroy.assert_not_called()

    @patch("file_manager.messagebox.askyesnocancel", return_value=False)
    def test_close_discard_closes_without_saving(self, prompt):
        manager = self.manager()
        manager.current_game.name = "Changed"
        manager.save_all = Mock()
        manager.close_editor()
        manager.save_all.assert_not_called()
        manager.root.destroy.assert_called_once()

    @patch("file_manager.messagebox.askyesnocancel", return_value=True)
    def test_close_failed_or_cancelled_save_stays_open(self, prompt):
        manager = self.manager()
        manager.current_game.name = "Changed"
        manager.save_all = Mock()
        manager.close_editor()
        manager.save_all.assert_called_once()
        manager.root.destroy.assert_not_called()

    @patch("file_manager.messagebox.askyesnocancel", return_value=True)
    def test_close_successful_save_closes(self, prompt):
        from dataclasses import asdict
        manager = self.manager()
        manager.current_game.name = "Changed"
        manager.save_all = Mock(side_effect=lambda: setattr(
            manager, "_saved_game_state", asdict(manager.current_game)
        ))
        manager.close_editor()
        manager.root.destroy.assert_called_once()

    @patch("file_manager.messagebox.showerror")
    def test_open_game_loads_start_area_instead_of_first_area(self, showerror):
        manager = self.manager()
        manager.game_name_var = Mock()
        manager.area_name_var = Mock()
        manager.refresh_game_areas_list = Mock()
        manager.refresh_player_setup = Mock()
        manager.draw_area = Mock()
        manager.update_properties_display = Mock()
        manager.show_load_message = Mock()
        manager._remember_recent_game = Mock()
        manager._load_area_from_file = Mock()
        with tempfile.TemporaryDirectory() as directory:
            manager._project_path = lambda *parts: os.path.join(directory, *parts)
            os.mkdir(os.path.join(directory, "areas"))
            for name in ("first.json", "main.json"):
                with open(os.path.join(directory, "areas", name), "w") as handle:
                    handle.write("{}")
            game_path = os.path.join(directory, "game.json")
            with open(game_path, "w") as handle:
                json.dump({"areas": ["first.json", "main.json"],
                           "properties": {"start_area": "main.json"}}, handle)
            manager.open_game(game_path)
            manager._load_area_from_file.assert_called_once_with(
                os.path.join(directory, "areas", "main.json"), show_message=False
            )
        showerror.assert_not_called()


class EnemyEditorHarness(EnemyEditor):
    def __init__(self):
        self.current_game = Game()
        self.current_area = Area()
        self.tile_manager = Mock()
        self.tile_manager.get_npc_names.return_value = ["goblin", "wizard"]
        self.selected_enemy_id = None
        self.draw_area = Mock()
        self.update_properties_display = Mock()


class EnemyFileManagerHarness(EnemyEditor, FileManager):
    def __init__(self):
        self.current_game = Game()
        self.current_area = Area()
        self.current_area_file = None
        self.current_game_file = None
        self.area_name_var = Mock()
        self.tile_manager = Mock()
        self.tile_manager.get_npc_names.return_value = ["goblin", "wizard"]
        self.draw_area = Mock()
        self.update_properties_display = Mock()
        self.selected_enemy_id = None


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

    def test_teleport_coordinate_picker_previews_destination_area_then_restores(self):
        source_area = Area(width=6, height=4, name="Source")
        destination_area = Area(width=3, height=2, name="Destination")
        editor = object.__new__(EditorMethods)
        editor.current_area = source_area
        editor.current_area_file = "/project/areas/source.json"
        editor.current_game = Game(areas=["source.json", "destination.json"])
        editor.cursor_x = 4
        editor.cursor_y = 2
        editor.selected_trigger_index = 1
        editor._project_path = lambda *parts: os.path.join("/project", *parts)
        editor._read_area_file = Mock(return_value=destination_area)
        editor.draw_area = Mock()
        editor.cursor_label = Mock()
        editor.canvas = Mock()
        x_var, y_var = Mock(), Mock()
        x_var.get.return_value = "1"
        y_var.get.return_value = "1"

        self.assertTrue(editor._begin_trigger_position_pick(
            x_var, y_var, "destination"
        ))

        self.assertIs(editor.current_area, destination_area)
        self.assertEqual(editor.current_area_file, "/project/areas/destination.json")
        self.assertEqual((editor.cursor_x, editor.cursor_y), (1, 1))
        editor._read_area_file.assert_called_once_with(
            "/project/areas/destination.json"
        )
        editor.draw_area.assert_called_once_with()
        editor.cursor_label.config.assert_called_once_with(
            text="Click target cell in Destination (Esc to cancel)"
        )

        editor.canvas.canvasx.return_value = 64
        editor.canvas.canvasy.return_value = 32
        editor.tile_size = 32
        result = editor.on_canvas_click(Mock(x=64, y=32))

        x_var.set.assert_called_once_with("2")
        y_var.set.assert_called_once_with("1")
        self.assertIs(editor.current_area, source_area)
        self.assertEqual(editor.current_area_file, "/project/areas/source.json")
        self.assertEqual((editor.cursor_x, editor.cursor_y), (4, 2))
        self.assertEqual(editor.selected_trigger_index, 1)
        self.assertIsNone(editor._coordinate_picker_source)
        self.assertEqual(result, "break")

    def test_teleport_coordinate_picker_allows_current_area_as_destination(self):
        editor = object.__new__(EditorMethods)
        current_area = Area(width=6, height=4, name="Current")
        editor.current_area = current_area
        editor.current_area_file = "/project/areas/current.json"
        editor.current_game = Game(areas=["current.json"])
        editor.cursor_x = 1
        editor.cursor_y = 2
        editor.selected_trigger_index = 0
        editor._project_path = lambda *parts: os.path.join("/project", *parts)
        editor._read_area_file = Mock()
        editor.draw_area = Mock()
        editor.cursor_label = Mock()
        editor.canvas = Mock()
        x_var, y_var = Mock(), Mock()
        x_var.get.return_value = "2"
        y_var.get.return_value = "1"

        self.assertTrue(editor._begin_trigger_position_pick(
            x_var, y_var, "current"
        ))

        self.assertIs(editor.current_area, current_area)
        editor._read_area_file.assert_not_called()

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
        self.assertEqual(ask_save.call_args.kwargs["initialdir"], manager._project_path("games"))
        self.assertIsNone(manager.current_game_file)
        self.assertEqual(
            manager._save_game_to_file.call_args.args[0], "/tmp/My_Game.json"
        )

        manager._save_game_to_file.return_value = True
        manager.save_game_as()
        self.assertEqual(manager.current_game_file, "/tmp/My_Game.json")

    def test_recent_games_are_persisted_and_most_recent_is_first(self):
        manager = FileManagerHarness()
        with tempfile.TemporaryDirectory() as directory:
            recent_file = os.path.join(directory, "config", "recent_games.json")
            game_paths = []
            for index in range(3):
                path = os.path.join(directory, f"game_{index}.json")
                with open(path, "w", encoding="utf-8") as game_file:
                    game_file.write("{}")
                game_paths.append(path)
            manager._recent_games_path = lambda: recent_file
            manager.recent_games = []

            manager._remember_recent_game(game_paths[0])
            manager._remember_recent_game(game_paths[1])
            manager._remember_recent_game(game_paths[0])

            with open(recent_file, "r", encoding="utf-8") as recent_list:
                self.assertEqual(
                    json.load(recent_list),
                    [game_paths[0], game_paths[1]],
                )
            self.assertEqual(
                manager._read_recent_games(),
                [game_paths[0], game_paths[1]],
            )

    def test_open_recent_menu_lists_games_and_can_be_cleared(self):
        manager = FileManagerHarness()
        menu = Mock()
        manager.recent_games_menu = menu
        manager.open_game = Mock()
        manager.clear_recent_games = Mock()

        with tempfile.TemporaryDirectory() as directory:
            games_directory = os.path.join(directory, "games")
            os.makedirs(games_directory)
            game_paths = [
                os.path.join(games_directory, "first.json"),
                os.path.join(games_directory, "second.json"),
            ]
            for path in game_paths:
                with open(path, "w", encoding="utf-8") as game_file:
                    game_file.write("{}")
            manager.recent_games = game_paths

            manager.refresh_open_recent_menu()

            self.assertEqual(menu.add_command.call_count, 3)
            self.assertEqual(
                menu.add_command.call_args_list[0].kwargs["label"],
                "first.json (games)",
            )
            self.assertEqual(
                menu.add_command.call_args_list[1].kwargs["label"],
                "second.json (games)",
            )
            self.assertEqual(
                menu.add_command.call_args_list[2].kwargs["label"],
                "Clear Recent",
            )
            menu.add_command.call_args_list[0].kwargs["command"]()
            manager.open_game.assert_called_once_with(game_paths[0])

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

    def test_save_trigger_and_area_saves_area_after_trigger_validation(self):
        manager = FileManagerHarness()
        manager.current_area_file = "/tmp/area.json"
        manager.save_selected_trigger = Mock(return_value=True)
        manager._save_area_to_file = Mock(return_value=True)

        self.assertTrue(manager.save_trigger_and_area())

        manager.save_selected_trigger.assert_called_once_with()
        manager._save_area_to_file.assert_called_once_with(
            "/tmp/area.json", save_trigger=False
        )

    def test_save_trigger_and_area_does_not_save_invalid_trigger(self):
        manager = FileManagerHarness()
        manager.current_area_file = "/tmp/area.json"
        manager.save_selected_trigger = Mock(return_value=False)
        manager._save_area_to_file = Mock()

        self.assertFalse(manager.save_trigger_and_area())

        manager._save_area_to_file.assert_not_called()

    def test_game_name_field_updates_current_game_name(self):
        editor = object.__new__(EditorMethods)
        editor.current_game = Game()
        editor.game_name_var = Mock()
        editor.game_name_var.get.return_value = "Castle Adventure"

        editor.on_game_name_change()

        self.assertEqual(editor.current_game.name, "Castle Adventure")

    def test_enemy_definitions_have_defaults_and_can_place_multiple_instances(self):
        editor = EnemyEditorHarness()
        editor.add_enemy_definition()

        enemy_id = editor.selected_enemy_id
        definition = editor.get_enemy_definitions()[enemy_id]
        self.assertEqual(definition["sprite"], "goblin")
        self.assertEqual(definition["health"], 10)
        self.assertEqual(definition["movement_speed"], 1.0)
        self.assertEqual(definition["ranged_attack"], "none")
        self.assertNotIn("dead_sprite", definition)

        editor.cursor_x, editor.cursor_y = 2, 3
        self.assertTrue(editor.place_selected_enemy())
        editor.cursor_x, editor.cursor_y = 5, 6
        self.assertTrue(editor.place_selected_enemy())

        self.assertEqual(len(editor.current_area.objects), 2)
        self.assertEqual(
            [(obj.x, obj.y) for obj in editor.current_area.objects],
            [(2, 3), (5, 6)],
        )
        self.assertTrue(all(obj.properties["enemy_id"] == enemy_id
                            for obj in editor.current_area.objects))

    def test_example_enemies_are_added_once_with_expected_defaults(self):
        editor = EnemyEditorHarness()
        editor.tile_manager.get_npc_names.return_value = [
            "gargoyle_npc",
            "orc_npc",
            "dragon_npc",
            "spider_npc",
            "skeleton_npc",
            "black_blob_npc",
        ]

        editor.add_example_enemy_definitions()

        definitions = editor.get_enemy_definitions()
        self.assertEqual(
            {definition["name"] for definition in definitions.values()},
            {"Gargoyle", "Orc", "Dragon", "Spider", "Skeleton", "Black Blob"},
        )
        by_name = {definition["name"]: definition for definition in definitions.values()}
        self.assertEqual(by_name["Dragon"]["ranged_attack"], "flame")
        self.assertEqual(by_name["Spider"]["movement_speed"], 1.5)
        by_name["Orc"]["health"] = 22

        editor.add_example_enemy_definitions()

        self.assertEqual(len(definitions), 6)
        self.assertEqual(
            {definition["name"]: definition for definition in definitions.values()}[
                "Orc"
            ]["health"],
            22,
        )

    def test_example_enemies_are_seeded_without_overwriting_custom_definitions(self):
        editor = EnemyEditorHarness()
        editor.tile_manager.get_npc_names.return_value = [
            "gargoyle_npc",
            "orc_npc",
            "dragon_npc",
            "spider_npc",
            "skeleton_npc",
            "black_blob_npc",
        ]
        editor.current_game.properties["enemies"] = {
            "example:orc": {"id": "example:orc", "name": "Custom Orc"}
        }

        editor.ensure_example_enemy_definitions()

        definitions = editor.get_enemy_definitions()
        self.assertEqual(len(definitions), 6)
        self.assertEqual(definitions["example:orc"]["name"], "Custom Orc")
        self.assertEqual(
            next(definition["name"] for definition in definitions.values()
                 if definition.get("starter_key") == "example:dragon"),
            "Dragon",
        )
        for enemy_id, definition in definitions.items():
            if definition.get("starter_key"):
                self.assertEqual(enemy_id, definition["id"])
                self.assertNotEqual(enemy_id, definition["starter_key"])

    def test_example_enemy_icons_are_32_by_32_pngs(self):
        npc_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "npcs")
        object_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "objects"
        )
        for sprite_name in (
            "gargoyle_npc",
            "orc_npc",
            "dragon_npc",
            "spider_npc",
            "skeleton_npc",
            "black_blob_npc",
        ):
            with self.subTest(sprite=sprite_name):
                image_path = os.path.join(npc_dir, f"{sprite_name}.png")
                with Image.open(image_path) as image:
                    self.assertEqual(image.size, (32, 32))
                    if sprite_name == "gargoyle_npc":
                        with Image.open(
                            os.path.join(object_dir, "gargoyle_object.png")
                        ) as original:
                            self.assertEqual(
                                image.convert("RGBA").tobytes(),
                                original.convert("RGBA").tobytes(),
                            )

    @patch("enemy_editor.messagebox.showerror")
    def test_enemy_definition_edits_sync_linked_instances(self, showerror):
        editor = EnemyEditorHarness()
        editor.add_enemy_definition()
        enemy_id = editor.selected_enemy_id
        definition = editor.get_enemy_definitions()[enemy_id]
        editor.current_area.objects = [
            GameObject(type="goblin", x=x, y=1, properties={
                "enemy_id": enemy_id,
                "enemy_data": dict(definition),
                "walkable": False,
            })
            for x in (2, 4)
        ]
        editor.enemy_name_var = Mock(get=Mock(return_value="Storm Caster"))
        editor.enemy_sprite_var = Mock(get=Mock(return_value="wizard"))
        editor.enemy_health_var = Mock(get=Mock(return_value="18"))
        editor.enemy_speed_var = Mock(get=Mock(return_value="0.25"))
        editor.enemy_ranged_attack_var = Mock(get=Mock(return_value="lightning"))
        editor.enemy_behavior_var = Mock(get=Mock(return_value="chase"))
        editor.enemy_damage_var = Mock(get=Mock(return_value="4"))

        self.assertTrue(editor.save_enemy_definition())
        self.assertEqual(definition["behavior"], "chase")
        self.assertEqual(definition["contact_damage"], 4)

        self.assertEqual(definition["name"], "Storm Caster")
        self.assertEqual(definition["sprite"], "wizard")
        self.assertEqual(definition["health"], 18)
        self.assertEqual(definition["movement_speed"], 0.25)
        self.assertEqual(definition["ranged_attack"], "lightning")
        self.assertNotIn("dead_sprite", definition)
        for instance in editor.current_area.objects:
            self.assertEqual(instance.type, "wizard")
            self.assertEqual(instance.properties["enemy_data"], definition)
        showerror.assert_not_called()

    def test_selecting_enemy_definition_loads_its_properties(self):
        editor = EnemyEditorHarness()
        editor.current_game.properties["enemies"] = {
            "enemy_a": {
                "id": "enemy_a",
                "name": "First",
                "sprite": "goblin",
                "health": 10,
                "movement_speed": 1.0,
                "ranged_attack": "none",
            },
            "enemy_b": {
                "id": "enemy_b",
                "name": "Second",
                "sprite": "wizard",
                "health": 20,
                "movement_speed": 0.25,
                "ranged_attack": "flame",
            },
        }
        editor.selected_enemy_id = "enemy_a"
        editor.tile_canvas = Mock()
        editor.update_tile_display = Mock()
        editor.enemy_name_var = Mock(get=Mock(return_value="First"), set=Mock())
        editor.enemy_sprite_var = Mock(get=Mock(return_value="goblin"), set=Mock())
        editor.enemy_health_var = Mock(get=Mock(return_value="10"), set=Mock())
        editor.enemy_speed_var = Mock(get=Mock(return_value="1"), set=Mock())
        editor.enemy_ranged_attack_var = Mock(get=Mock(return_value="none"), set=Mock())

        editor.select_enemy_definition(1)

        self.assertEqual(editor.selected_enemy_id, "enemy_b")
        self.assertNotIn("dead_sprite", editor.current_game.properties["enemies"]["enemy_b"])
        editor.enemy_name_var.set.assert_called_with("Second")
        editor.enemy_sprite_var.set.assert_called_with("wizard")
        editor.enemy_health_var.set.assert_called_with("20")
        editor.enemy_speed_var.set.assert_called_with("0.25")
        editor.enemy_ranged_attack_var.set.assert_called_with("flame")
        editor.update_tile_display.assert_called_once_with()

    def test_enemy_palette_draws_icons_and_names_with_selected_marker(self):
        editor = ToolboxDisplayHarness("enemy")
        editor.tile_canvas = Mock()
        editor.tile_canvas.bbox.return_value = (0, 0, 200, 80)
        editor.get_enemy_definitions = EnemyEditor.get_enemy_definitions.__get__(
            editor
        )
        editor.current_game = Game(properties={
            "enemies": {
                "enemy_a": {"name": "Orc", "sprite": "orc_npc"},
                "enemy_b": {"name": "Dragon", "sprite": "dragon_npc"},
            },
        })
        editor.selected_enemy_id = "enemy_b"
        editor.tile_manager = Mock()
        editor.tile_manager.get_npc_info.side_effect = lambda name: {
            "image": f"image:{name}"
        }

        editor.update_tile_display()

        create_image = editor.tile_canvas.create_image
        self.assertEqual(create_image.call_count, 2)
        self.assertEqual(create_image.call_args_list[0].kwargs["image"], "image:orc_npc")
        self.assertEqual(create_image.call_args_list[1].kwargs["image"], "image:dragon_npc")
        labels = [
            call.kwargs.get("text")
            for call in editor.tile_canvas.create_text.call_args_list
        ]
        self.assertEqual(labels, ["Orc", "Dragon"])
        editor.tile_canvas.create_rectangle.assert_called_once()

    def test_enemy_palette_click_selects_the_visible_scrolled_row(self):
        editor = object.__new__(EditorMethods)
        editor.selected_mode = "enemy"
        editor.tile_canvas = Mock()
        editor.tile_canvas.canvasy.return_value = 55
        editor.get_enemy_definitions = Mock(return_value={
            "enemy_a": {},
            "enemy_b": {},
        })
        editor.select_enemy_definition = Mock()

        editor.on_tile_canvas_click(Mock(x=60, y=15))

        editor.select_enemy_definition.assert_called_once_with(1)
        editor.tile_canvas.find_closest.assert_not_called()

    def test_enemy_placement_uses_the_map_spacebar_action(self):
        editor = object.__new__(EditorMethods)
        editor.root = Mock()
        editor.canvas = Mock()
        editor.root.focus_get.return_value = editor.canvas
        editor.selected_mode = "enemy"
        editor.place_tile = Mock()

        result = editor.on_key_press(Mock(keysym="space"))

        self.assertEqual(result, "break")
        editor.place_tile.assert_called_once_with()

    @patch("enemy_editor.messagebox.showerror")
    def test_enemy_definition_edit_updates_instances_in_every_saved_game_area(
        self, showerror
    ):
        editor = EnemyEditorHarness()
        editor.current_game.areas = ["first.json", "second.json"]
        editor.current_game.properties["enemies"] = {
            "enemy_shared": {
                "id": "enemy_shared",
                "name": "Orc",
                "sprite": "goblin",
                "health": 10,
                "movement_speed": 1.0,
                "ranged_attack": "none",
            },
        }
        editor.selected_enemy_id = "enemy_shared"
        editor.current_area_file = None
        editor.enemy_name_var = Mock(get=Mock(return_value="Armored Orc"))
        editor.enemy_sprite_var = Mock(get=Mock(return_value="wizard"))
        editor.enemy_health_var = Mock(get=Mock(return_value="30"))
        editor.enemy_speed_var = Mock(get=Mock(return_value="0"))
        editor.enemy_ranged_attack_var = Mock(get=Mock(return_value="gun"))

        with tempfile.TemporaryDirectory() as directory:
            editor._project_path = lambda *parts: os.path.join(directory, *parts)
            areas_directory = os.path.join(directory, "areas")
            os.makedirs(areas_directory)
            for area_name, x_positions in (
                ("first.json", (1, 2)), ("second.json", (4,))
            ):
                area_path = os.path.join(areas_directory, area_name)
                with open(area_path, "w") as area_file:
                    json.dump({
                        "objects": [
                            {
                                "type": "goblin",
                                "x": x,
                                "y": 2,
                                "properties": {
                                    "enemy_id": "enemy_shared",
                                    "enemy_data": {"health": 10},
                                    "walkable": False,
                                },
                            }
                            for x in x_positions
                        ],
                    }, area_file)

            self.assertTrue(editor.save_enemy_definition())

            for area_name in ("first.json", "second.json"):
                with open(os.path.join(areas_directory, area_name), "r") as area_file:
                    objects = json.load(area_file)["objects"]
                for obj in objects:
                    self.assertEqual(obj["type"], "wizard")
                    self.assertEqual(obj["properties"]["enemy_data"]["health"], 30)
                    self.assertEqual(
                        obj["properties"]["enemy_data"]["movement_speed"], 0.0
                    )
                    self.assertEqual(
                        obj["properties"]["enemy_data"]["ranged_attack"], "gun"
                    )
        showerror.assert_not_called()

    @patch("enemy_editor.messagebox.showwarning")
    def test_enemy_speed_zero_is_valid_and_duplicate_tile_placement_is_blocked(
        self, showwarning
    ):
        editor = EnemyEditorHarness()
        editor.add_enemy_definition()
        editor.enemy_name_var = Mock(get=Mock(return_value="Stationary Guard"))
        editor.enemy_sprite_var = Mock(get=Mock(return_value="goblin"))
        editor.enemy_health_var = Mock(get=Mock(return_value="5"))
        editor.enemy_speed_var = Mock(get=Mock(return_value="0"))
        editor.enemy_ranged_attack_var = Mock(get=Mock(return_value="none"))

        self.assertTrue(editor.save_enemy_definition())
        self.assertEqual(
            editor.get_enemy_definitions()[editor.selected_enemy_id][
                "movement_speed"
            ],
            0.0,
        )
        editor.cursor_x = editor.cursor_y = 1
        self.assertTrue(editor.place_selected_enemy())
        self.assertFalse(editor.place_selected_enemy())
        self.assertEqual(len(editor.current_area.objects), 1)
        showwarning.assert_called_once()

    def test_enemy_definitions_and_portable_instances_round_trip(self):
        manager = EnemyFileManagerHarness()
        manager.current_game.properties["enemies"] = {
            "enemy_1": {
                "id": "enemy_1",
                "name": "Stone Guard",
                "sprite": "goblin",
                "health": 14,
                "movement_speed": 0.5,
                "ranged_attack": "flame",
            },
        }
        manager.current_area.objects = [
            GameObject(type="goblin", x=3, y=4, properties={
                "enemy_id": "enemy_1",
                "enemy_data": {"health": 1},
                "walkable": False,
            })
        ]

        with tempfile.TemporaryDirectory() as directory:
            game_path = os.path.join(directory, "game.json")
            area_path = os.path.join(directory, "area.json")
            with patch("file_manager.messagebox.showinfo"):
                self.assertTrue(manager._save_game_to_file(game_path))
                self.assertTrue(manager._save_area_to_file(area_path))
            with open(game_path, "r") as saved_game:
                game_data = json.load(saved_game)
            with open(area_path, "r") as saved_area:
                area_data = json.load(saved_area)

            manager.current_game = Game(**game_data)
            manager._load_area_from_file(area_path, show_message=False)

        definition = manager.get_enemy_definitions()["enemy_1"]
        instance = manager.current_area.objects[0]
        self.assertEqual(definition["movement_speed"], 0.5)
        self.assertNotIn("dead_sprite", definition)
        self.assertEqual(area_data["objects"][0]["properties"]["enemy_data"], definition)
        self.assertEqual(instance.properties["enemy_data"], definition)
        self.assertEqual(instance.type, "goblin")

    def test_npc_palette_click_selects_the_sprite_in_the_clicked_scrolled_row(self):
        for mode in ("npc", "player"):
            with self.subTest(mode=mode):
                editor = object.__new__(EditorMethods)
                editor.selected_mode = mode
                editor.selected_tile = "previous-selection"
                editor.tile_manager = AssetNames()
                editor.tile_canvas = Mock()
                editor.tile_canvas.canvasy.side_effect = lambda y: y + 40
                editor.update_tile_display = Mock()
                editor.draw_area = Mock()
                player_settings = {"sprite": "previous-selection"}
                editor.get_player_settings = Mock(return_value=player_settings)

                editor.on_tile_canvas_click(Mock(x=55, y=15))

                self.assertEqual(editor.selected_tile, "wizard")
                editor.update_tile_display.assert_called_once_with()
                if mode == "player":
                    self.assertEqual(player_settings["sprite"], "wizard")
                    editor.draw_area.assert_called_once_with()
                else:
                    editor.get_player_settings.assert_not_called()
                    editor.draw_area.assert_not_called()

                editor.on_tile_canvas_click(Mock(x=55, y=47))

                self.assertEqual(editor.selected_tile, "wizard")
                editor.update_tile_display.assert_called_once_with()
                editor.tile_canvas.find_closest.assert_not_called()

    def test_player_start_selection_saves_area_position_and_sprite(self):
        editor = object.__new__(EditorMethods)
        editor.current_game = Game()
        editor.current_area_file = "/project/areas/main_map.json"
        editor.current_area = Area()
        editor.selected_tile = "wizard_npc"
        editor._is_project_area = Mock(return_value=True)
        editor.is_tile_blocked = Mock(return_value=False)
        editor.refresh_game_areas_list = Mock()
        editor.refresh_player_setup = Mock()
        editor.draw_area = Mock()
        editor.update_properties_display = Mock()

        self.assertTrue(editor.set_player_start(4, 6))

        self.assertEqual(editor.current_game.areas, ["main_map.json"])
        self.assertEqual(editor.current_game.properties["start_area"], "main_map.json")
        self.assertEqual(editor.current_game.properties["start_x"], 4)
        self.assertEqual(editor.current_game.properties["start_y"], 6)
        self.assertEqual(
            editor.current_game.properties["player"]["sprite"], "wizard_npc"
        )
        editor.refresh_game_areas_list.assert_called_once_with()
        editor.draw_area.assert_called_once_with()

    def test_player_start_allows_blocked_tiles_without_changing_them(self):
        editor = object.__new__(EditorMethods)
        editor.current_game = Game()
        editor.current_area = Area()
        editor.current_area.tiles[6][4].walkable_override = False
        editor.current_area_file = "/project/areas/main_map.json"
        editor.selected_tile = "wizard_npc"
        editor._is_project_area = Mock(return_value=True)
        editor.is_tile_blocked = Mock(return_value=True)
        editor.refresh_game_areas_list = Mock()
        editor.refresh_player_setup = Mock()
        editor.draw_area = Mock()
        editor.update_properties_display = Mock()
        self.assertTrue(editor.set_player_start(4, 6))
        self.assertIs(editor.current_area.tiles[6][4].walkable_override, False)
        editor.is_tile_blocked.assert_not_called()

    @patch("editor_methods.messagebox.showwarning")
    def test_player_start_rejects_out_of_bounds_tile(self, showwarning):
        editor = object.__new__(EditorMethods)
        editor.current_game = Game()
        editor.current_area_file = "/project/areas/main_map.json"
        editor.current_area = Area()
        editor.selected_tile = "wizard_npc"
        editor._is_project_area = Mock(return_value=True)
        editor.is_tile_blocked = Mock(return_value=True)
        editor.draw_area = Mock()

        self.assertFalse(editor.set_player_start(40, 60))

        self.assertEqual(editor.current_game.properties, {})
        showwarning.assert_called_once()
        editor.draw_area.assert_not_called()

    @patch("editor_methods.messagebox.showerror")
    def test_player_starting_stats_are_validated(self, showerror):
        editor = object.__new__(EditorMethods)
        editor.current_game = Game()
        editor.player_stat_vars = {
            "starting_health": Mock(get=Mock(return_value="21")),
            "max_health": Mock(get=Mock(return_value="20")),
            "starting_energy": Mock(get=Mock(return_value="0")),
            "max_energy": Mock(get=Mock(return_value="0")),
            "strength": Mock(get=Mock(return_value="1")),
            "intelligence": Mock(get=Mock(return_value="1")),
            "gold": Mock(get=Mock(return_value="0")),
        }

        self.assertFalse(editor.save_player_setup())

        showerror.assert_called_once()
        self.assertEqual(
            editor.current_game.properties["player"]["stats"]["starting_health"], 20
        )

    def test_player_settings_round_trip_in_game_save(self):
        manager = FileManagerHarness()
        manager.current_game.properties = {
            "start_area": "main_map.json",
            "start_x": 2,
            "start_y": 3,
            "player": {
                "sprite": "wizard_npc",
                "stats": {
                    "starting_health": 12,
                    "max_health": 20,
                    "starting_energy": 4,
                    "max_energy": 8,
                    "strength": 2,
                    "intelligence": 3,
                    "gold": 10,
                },
                "starting_inventory": [],
            },
        }

        with tempfile.TemporaryDirectory() as directory:
            game_path = os.path.join(directory, "game.json")
            with patch("file_manager.messagebox.showinfo"):
                self.assertTrue(manager._save_game_to_file(game_path))
            with open(game_path, "r") as saved_game:
                properties = json.load(saved_game)["properties"]

        self.assertEqual(properties["start_area"], "main_map.json")
        self.assertEqual((properties["start_x"], properties["start_y"]), (2, 3))
        self.assertEqual(properties["player"]["sprite"], "wizard_npc")
        self.assertEqual(properties["player"]["stats"]["gold"], 10)

    def test_player_inventory_editor_saves_eight_ordered_slots(self):
        editor = object.__new__(EditorMethods)
        editor.current_game = Game(object_definitions={
            "key_object": {"gettable": True},
            "chest_object": {"gettable": True},
        })
        editor.tile_manager = Mock()
        editor.tile_manager.get_object_names.return_value = [
            "key_object", "chest_object",
        ]
        editor.player_stat_vars = {
            "starting_health": Mock(get=Mock(return_value="20")),
            "max_health": Mock(get=Mock(return_value="20")),
            "starting_energy": Mock(get=Mock(return_value="0")),
            "max_energy": Mock(get=Mock(return_value="0")),
            "strength": Mock(get=Mock(return_value="1")),
            "intelligence": Mock(get=Mock(return_value="1")),
            "gold": Mock(get=Mock(return_value="0")),
        }
        selected_items = [
            "key_object", "", "chest_object", "key_object", "", "", "", "",
        ]
        editor.player_inventory_vars = [
            Mock(get=Mock(return_value=item)) for item in selected_items
        ]

        self.assertTrue(editor.save_player_setup())

        self.assertEqual(
            editor.current_game.properties["player"]["starting_inventory"],
            selected_items,
        )

    def test_player_inventory_choices_only_include_gettable_objects(self):
        editor = object.__new__(EditorMethods)
        editor.current_game = Game(object_definitions={
            "key_object": {"gettable": True},
            "table_object": {"gettable": False},
        })
        editor.tile_manager = Mock()
        editor.tile_manager.get_object_names.return_value = [
            "key_object", "table_object",
        ]

        self.assertEqual(editor._available_inventory_items(), ["key_object"])

    @patch("editor_methods.messagebox.showerror")
    def test_player_inventory_editor_rejects_more_than_eight_slots(self, showerror):
        editor = object.__new__(EditorMethods)
        editor.current_game = Game()
        editor.player_stat_vars = {
            "starting_health": Mock(get=Mock(return_value="20")),
            "max_health": Mock(get=Mock(return_value="20")),
            "starting_energy": Mock(get=Mock(return_value="0")),
            "max_energy": Mock(get=Mock(return_value="0")),
            "strength": Mock(get=Mock(return_value="1")),
            "intelligence": Mock(get=Mock(return_value="1")),
            "gold": Mock(get=Mock(return_value="0")),
        }
        editor.player_inventory_vars = [
            Mock(get=Mock(return_value="")) for _ in range(9)
        ]

        self.assertFalse(editor.save_player_setup())
        showerror.assert_called_once()

    def test_area_loader_populates_name_from_filename_for_unnamed_areas(self):
        from dataclasses import asdict
        for stored_name in (None, "", "  ", "Untitled Area", "Blob Arena"):
            with self.subTest(name=stored_name), tempfile.TemporaryDirectory() as directory:
                area_path = os.path.join(directory, "blob_battle.json")
                data = asdict(Area(width=2, height=2))
                if stored_name is None:
                    data.pop("name")
                else:
                    data["name"] = stored_name
                with open(area_path, "w") as area_file:
                    json.dump(data, area_file)
                manager = AreaLoadingHarness()
                manager._load_area_from_file(area_path, show_message=False)
                expected = "Blob Arena" if stored_name == "Blob Arena" else "blob_battle"
                self.assertEqual(manager.current_area.name, expected)
                manager.area_name_var.set.assert_called_with(expected)

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

    @patch("editor_methods.messagebox.showerror")
    def test_weapon_settings_save_reload_and_reject_invalid_damage(self, showerror):
        editor = object.__new__(EditorMethods)
        editor.selected_mode = "object"
        editor.selected_tile = "club_object"
        editor.current_game = Game()
        editor.draw_area = Mock()
        editor.update_properties_display = Mock()
        editor.object_gettable_var = Mock(get=Mock(return_value=True))
        editor.object_walkable_var = Mock(get=Mock(return_value=True))
        editor.object_effect_mode_var = Mock(get=Mock(return_value="passive"))
        editor.object_effect_vars = {}
        editor.object_item_type_var = Mock(get=Mock(return_value="weapon"))
        editor.object_weapon_damage_var = Mock(get=Mock(return_value="7"))
        editor.save_object_definition_changes()
        definition = editor.current_game.get_object_definition("club_object")
        self.assertEqual(definition["item_type"], "weapon")
        self.assertEqual(definition["weapon_damage"], 7)
        self.assertTrue(definition["gettable"])
        editor.on_object_item_type_change = Mock()
        editor.on_object_gettable_change = Mock()
        editor.load_object_definition_editor()
        editor.object_weapon_damage_var.set.assert_called_with("7")
        editor.object_item_type_var.set.assert_called_with("weapon")
        editor.object_weapon_damage_var.get.return_value = "-1"
        editor.save_object_definition_changes()
        showerror.assert_called_once()
        self.assertEqual(editor.current_game.get_object_definition("club_object")["weapon_damage"], 7)

    @patch("editor_methods.messagebox.showerror")
    def test_right_panel_saves_armor_and_ranged_item_settings(self, showerror):
        editor = object.__new__(EditorMethods)
        editor.selected_mode = "object"
        editor.selected_tile = "helmet_object"
        editor.current_game = Game()
        editor.draw_area = Mock()
        editor.update_properties_display = Mock()
        editor.object_gettable_var = Mock(get=Mock(return_value=True))
        editor.object_walkable_var = Mock(get=Mock(return_value=True))
        editor.object_effect_mode_var = Mock(get=Mock(return_value="passive"))
        editor.object_effect_vars = {}
        editor.object_item_type_var = Mock(get=Mock(return_value="armor"))
        editor.object_weapon_damage_var = Mock(get=Mock(return_value="6"))
        editor.item_detail_vars = {
            key: Mock(get=Mock(return_value=value)) for key, value in {
                "armor_bonus": "5", "equipment_slot": "head", "ranged": "no",
                "attack_range": "6", "energy_cost": "2", "ammo_item": "", "read_text": "A book",
            }.items()
        }
        editor.save_object_definition_changes()
        definition = editor.current_game.get_object_definition("helmet_object")
        self.assertEqual(definition["armor_bonus"], 5)
        self.assertEqual(definition["equipment_slot"], "head")
        editor.selected_tile = "magic_wand_object"
        editor.object_item_type_var.get.return_value = "weapon"
        editor.item_detail_vars["ranged"].get.return_value = "yes"
        editor.save_object_definition_changes()
        definition = editor.current_game.get_object_definition("magic_wand_object")
        self.assertTrue(definition["ranged"])
        self.assertEqual(definition["weapon_damage"], 6)
        self.assertEqual(definition["energy_cost"], 2)
        editor.item_detail_vars["energy_cost"].get.return_value = "-2"
        editor.save_object_definition_changes()
        showerror.assert_called_once()
        self.assertEqual(editor.current_game.get_object_definition("magic_wand_object")["energy_cost"], 2)

    def test_trigger_reordering_changes_only_triggers_at_selected_tile(self):
        editor = object.__new__(EditorMethods)
        first = Trigger(1, 1, "area_object", "hide")
        elsewhere = Trigger(4, 4, "show_message", "elsewhere")
        second = Trigger(1, 1, "inventory", "pickup")
        editor.current_area = Area(triggers=[first, elsewhere, second])
        editor.cursor_x = editor.cursor_y = 1
        editor.selected_trigger_index = 1
        editor.save_selected_trigger = Mock(return_value=True)
        editor.refresh_trigger_editor = Mock()
        editor.draw_area = Mock()
        editor.update_properties_display = Mock()
        self.assertTrue(editor.move_selected_trigger(-1))
        self.assertEqual([trigger.name for trigger in editor.current_area.triggers], ["pickup", "elsewhere", "hide"])
        self.assertEqual(editor.selected_trigger_index, 0)
        self.assertFalse(editor.move_selected_trigger(-1))

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
