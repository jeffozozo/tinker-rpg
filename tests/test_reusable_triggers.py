"""Reusable definitions, per-location charges, and game-wide control integration."""
import json
from dataclasses import asdict
from pathlib import Path
import tempfile
import unittest
from PIL import Image
from data_classes import Area, Game, Trigger
from runner_engine import RunnerEngine, RunnerError


class ReusableTriggerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        for folder in ('games', 'areas', 'tiles', 'npcs', 'objects'):
            (self.root / folder).mkdir()
        Image.new('RGBA', (32, 32)).save(self.root / 'tiles/grass.png')
        Image.new('RGBA', (32, 32)).save(self.root / 'npcs/fighter_npc.png')
        self.areas = {}
        for name in ('first.json', 'second.json'):
            area = Area(name=name, width=6, height=5)
            for row in area.tiles:
                for tile in row:
                    tile.type = 'grass'
            self.areas[name] = area
        self.definitions = {
            'poison': dict(name='fountain_poison', trigger_type='player_stats', parameters=dict(stat='health', amount=-5, charges=0), enabled=True),
            'heal': dict(name='fountain_healing', trigger_type='player_stats', parameters=dict(stat='health', amount=5, charges=0), enabled=False),
        }
        self.game = Game(areas=list(self.areas), properties={
            'start_area': 'first.json', 'start_x': 1, 'start_y': 2,
            'player': {'sprite': 'fighter_npc', 'starting_inventory': [],
                       'stats': {'starting_health': 15, 'max_health': 30}},
            'trigger_definitions': self.definitions,
        })
        for area in self.areas.values():
            area.triggers = [Trigger(2, 2, definition_id='poison'), Trigger(2, 2, definition_id='heal')]

    def engine(self):
        for name, area in self.areas.items():
            (self.root / 'areas' / name).write_text(json.dumps(asdict(area)))
        (self.root / 'games/test.json').write_text(json.dumps(asdict(self.game)))
        return RunnerEngine('test', project_root=self.root)

    def control(self, area, target, action, x=3, y=2):
        self.areas[area].triggers.append(Trigger(x, y, 'trigger_control', 'control', dict(target=target, action=action, charges=1)))

    def test_control_changes_every_area_and_survives_save_load(self):
        self.control('first.json', 'poison', 'disable')
        self.control('first.json', 'heal', 'enable')
        engine = self.engine()
        engine.move('right')
        self.assertEqual(engine.health, 10)
        engine.move('right')
        engine.move('left')
        self.assertEqual(engine.health, 15)
        engine._teleport(dict(area='second', x=1, y=2))
        engine.move('right')
        self.assertEqual(engine.health, 20)
        path = self.root / 'world.save.json'
        engine.save_to_file(path, 'Restored fountains')
        engine = RunnerEngine.load_save(path, project_root=self.root)
        engine.move('left'); engine.move('right')
        self.assertEqual(engine.health, 25)
        self.assertFalse(engine.trigger_definitions['poison']['enabled'])

    def test_charges_are_per_placement_and_remain_finite_after_reload(self):
        self.definitions['poison']['parameters']['charges'] = 2
        engine = self.engine()
        engine.move('right')
        self.assertEqual(engine.current_area.triggers[0].remaining_charges, 1)
        self.assertIsNone(engine.areas['second.json'].triggers[0].remaining_charges)
        path = self.root / 'charges.save.json'; engine.save_to_file(path, 'Charges')
        engine = RunnerEngine.load_save(path, project_root=self.root)
        engine.move('left'); engine.move('right')
        self.assertFalse(any(t.definition_id == 'poison' for t in engine.current_area.triggers))
        engine.move('left'); engine.move('right')
        self.assertEqual(engine.health, 5)
        self.assertEqual(engine.trigger_definitions['poison']['parameters']['charges'], 2)

    def test_disabling_does_not_spend_charges_and_enabling_does_not_reset(self):
        self.definitions['poison']['parameters']['charges'] = 2
        self.control('first.json', 'poison', 'disable', 3, 2)
        self.control('first.json', 'poison', 'enable', 4, 2)
        engine = self.engine()
        engine.move('right'); engine.move('right'); engine.move('left')
        self.assertEqual(engine.health, 10)
        self.assertEqual(engine.current_area.triggers[0].remaining_charges, 1)
        engine.move('right'); engine.move('right'); engine.move('left'); engine.move('left')
        self.assertEqual(engine.health, 5)
        self.assertFalse(any(t.definition_id == 'poison' for t in engine.current_area.triggers))

    def test_inventory_gate_prevents_control_when_item_is_missing(self):
        self.areas['first.json'].triggers.insert(0, Trigger(3, 2, 'inventory', 'offering', dict(remove='green_gem_object', charges=1)))
        self.control('first.json', 'poison', 'disable')
        engine = self.engine()
        engine.move('right'); engine.move('right')
        self.assertTrue(engine.trigger_definitions['poison']['enabled'])
        engine.inventory[0] = 'green_gem_object'
        engine.move('left'); engine.move('right')
        self.assertFalse(engine.trigger_definitions['poison']['enabled'])
        self.assertNotIn('green_gem_object', engine.inventory)

    def test_control_can_be_reused_and_disables_later_trigger_in_same_stack(self):
        self.definitions['off'] = dict(name='switch_off', trigger_type='trigger_control', parameters=dict(target='poison', action='disable', charges=0))
        self.areas['first.json'].triggers.insert(0, Trigger(2, 2, definition_id='off'))
        engine = self.engine(); engine.move('right')
        self.assertEqual(engine.health, 15)

    def test_renaming_definition_preserves_control_references(self):
        self.control('first.json', 'poison', 'disable')
        self.definitions['poison']['name'] = 'renamed_poison'
        engine = self.engine(); engine.move('right'); engine.move('right')
        self.assertFalse(engine.trigger_definitions['poison']['enabled'])
        self.assertEqual(engine.areas['second.json'].triggers[0].name, 'renamed_poison')

    def test_duplicate_names_and_missing_definitions_are_rejected(self):
        self.definitions['heal']['name'] = 'FOUNTAIN_POISON'
        with self.assertRaisesRegex(RunnerError, 'unique'):
            self.engine()
        self.definitions['heal']['name'] = 'healing'
        self.areas['first.json'].triggers.append(Trigger(3, 2, definition_id='absent'))
        with self.assertRaisesRegex(RunnerError, 'missing'):
            self.engine()

    def test_missing_control_target_is_reported(self):
        self.control('first.json', 'missing', 'enable')
        engine = self.engine()
        self.assertTrue(any('existing named trigger' in issue for issue in engine.validation_issues))


class ReusableTriggerEditorTests(unittest.TestCase):
    def editor(self):
        from unittest.mock import Mock
        from editor_methods import EditorMethods
        from reusable_trigger_editor import ReusableTriggerEditor
        class Editor(ReusableTriggerEditor, EditorMethods):
            pass
        class Value:
            def __init__(self, value=''): self.value = value
            def get(self): return self.value
            def set(self, value): self.value = value
        e = object.__new__(Editor)
        e.current_game = Game()
        e.current_area = Area(width=5, height=5)
        e.current_area_file = '/areas/first.json'
        e.cursor_x = e.cursor_y = 1
        e.selected_mode = 'trigger'
        e.selected_trigger_index = 0
        e.reusable_trigger_var = Value()
        e.current_area.triggers = [Trigger(1, 1, 'player_stats', 'fountain_poison', dict(stat='health', amount=-5, charges=2))]
        e.save_selected_trigger = Mock(return_value=True)
        e.refresh_trigger_editor = Mock()
        e.draw_area = Mock()
        e.update_properties_display = Mock()
        return e

    def test_named_palette_places_definition_instead_of_local_sentinel(self):
        e = self.editor(); e.make_trigger_reusable()
        identity = e.current_area.triggers[0].definition_id
        e.cursor_x = 2; e.selected_tile = 'named_trigger'
        e.place_tile()
        self.assertEqual(len(e.current_area.triggers), 2)
        self.assertEqual(e.current_area.triggers[-1].definition_id, identity)
        self.assertEqual(e.current_area.triggers[-1].trigger_type, 'player_stats')

    def test_named_placement_uses_summary_instead_of_definition_fields(self):
        from unittest.mock import Mock
        from editor_methods import EditorMethods
        e = self.editor(); e.make_trigger_reusable()
        e.trigger_listbox = Mock()
        e.trigger_form_frame = Mock()
        e.trigger_form_frame.winfo_children.return_value = []
        e.trigger_colors = {}
        e.show_named_trigger_summary = Mock()
        e._build_trigger_editor = Mock()
        EditorMethods.refresh_trigger_editor(e)
        e.show_named_trigger_summary.assert_called_once_with(e.current_area.triggers[0])
        e._build_trigger_editor.assert_not_called()
        self.assertEqual(e._trigger_editor_vars, {})

    def test_named_manager_draft_guard_handles_save_discard_and_cancel(self):
        from unittest.mock import Mock, patch
        from named_trigger_manager import NamedTriggerManager
        manager = object.__new__(NamedTriggerManager)
        manager.trigger = Trigger(name='draft')
        manager.window = Mock()
        manager.baseline = ('old',)
        manager.values = Mock(return_value=('changed',))
        manager.save = Mock(return_value=True)
        with patch('named_trigger_manager.messagebox.askyesnocancel', return_value=None):
            self.assertFalse(manager.confirm_draft())
        with patch('named_trigger_manager.messagebox.askyesnocancel', return_value=False):
            self.assertTrue(manager.confirm_draft())
        manager.save.assert_not_called()
        with patch('named_trigger_manager.messagebox.askyesnocancel', return_value=True):
            self.assertTrue(manager.confirm_draft())
        manager.save.assert_called_once()

    def test_control_save_resolves_selected_name_and_saved_id_without_cached_labels(self):
        from unittest.mock import Mock, patch
        from editor_methods import EditorMethods
        for selected in ('fountain_healing', 'healing_id'):
            with self.subTest(selected=selected):
                e = self.editor()
                e.current_game.properties['trigger_definitions'] = {
                    'healing_id': dict(name='fountain_healing', trigger_type='player_stats',
                                       parameters=dict(stat='health', amount=5, charges=0))}
                trigger = Trigger(1, 1, 'trigger_control', 'restore_fountain')
                e._trigger_editor_trigger = trigger
                e._trigger_editor_type_labels = {'Trigger Control': 'trigger_control'}
                e._trigger_control_labels = {}
                e._trigger_editor_vars = {key: Mock(get=Mock(return_value=value)) for key, value in
                    dict(name='restore_fountain', trigger_type='Trigger Control', target=selected, action='enable', charges='0').items()}
                e._trigger_coordinate_error = Mock(return_value=None)
                with patch('editor_methods.messagebox.showerror') as error:
                    self.assertTrue(EditorMethods.save_selected_trigger(e, refresh=False))
                    error.assert_not_called()
                self.assertEqual(trigger.parameters['target'], 'healing_id')

    def test_named_trigger_placement_allows_more_than_ten_per_location(self):
        e = self.editor()
        self.assertTrue(e.make_trigger_reusable())
        identity = e.current_area.triggers[0].definition_id
        for _ in range(29):
            self.assertTrue(e.place_reusable_trigger())
        self.assertEqual(len(e._triggers_at_cursor()), 30)
        self.assertEqual(e.selected_trigger_index, 29)
        self.assertTrue(all(trigger.definition_id == identity
                            for trigger in e.current_area.triggers))

    def test_make_reusable_and_place_share_one_definition(self):
        e = self.editor()
        self.assertTrue(e.make_trigger_reusable())
        first = e.current_area.triggers[0]
        e.cursor_x = 2
        self.assertTrue(e.place_reusable_trigger())
        self.assertEqual(first.definition_id, e.current_area.triggers[1].definition_id)
        first.parameters['amount'] = -7
        e.save_reusable_trigger(first)
        self.assertEqual(e.current_area.triggers[1].parameters['amount'], -7)
        self.assertEqual(len(e.current_game.properties['trigger_definitions']), 1)

    def test_copy_paste_keeps_definition_link_and_cross_game_copies_library(self):
        e = self.editor(); e.make_trigger_reusable(); e.copy_location()
        identity = e.current_area.triggers[0].definition_id
        e.cursor_x = 2; e.paste_location()
        self.assertEqual(e.current_area.triggers[1].definition_id, identity)
        e.current_game = Game()
        e.current_area = Area(width=5, height=5)
        e.cursor_x = e.cursor_y = 3
        e.paste_location()
        self.assertIn(identity, e.current_game.properties['trigger_definitions'])
        self.assertEqual(e.current_area.triggers[0].name, 'fountain_poison')

    def test_cross_game_control_copy_includes_its_target_definition(self):
        e = self.editor(); e.make_trigger_reusable()
        target = e.current_area.triggers[0].definition_id
        e.current_area.triggers = [Trigger(1, 1, 'trigger_control', 'lever', dict(target=target, action='disable', charges=1))]
        e.make_trigger_reusable(); control = e.current_area.triggers[0].definition_id
        e.copy_location(); e.current_game = Game(); e.current_area = Area(width=5, height=5)
        e.paste_location()
        definitions = e.current_game.properties['trigger_definitions']
        self.assertIn(control, definitions)
        self.assertIn(target, definitions)
        self.assertEqual(definitions[control]['parameters']['target'], target)

    def test_reusable_names_are_unique_and_delete_only_removes_placement(self):
        from unittest.mock import patch
        e = self.editor(); e.make_trigger_reusable()
        identity = e.current_area.triggers[0].definition_id
        e.current_area.triggers.append(Trigger(1, 1, 'player_stats', 'FOUNTAIN_POISON', dict(stat='health', amount=5)))
        e.selected_trigger_index = 1
        with patch('reusable_trigger_editor.messagebox.showerror') as error:
            self.assertFalse(e.make_trigger_reusable())
            error.assert_called_once()
        e.delete_location()
        self.assertEqual(e.current_area.triggers, [])
        self.assertIn(identity, e.current_game.properties['trigger_definitions'])


if __name__ == '__main__':
    unittest.main()
