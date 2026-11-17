"""Enemy definition drafts remain separate from map placement/instance settings."""
from copy import deepcopy
import unittest
from unittest.mock import Mock, patch
from data_classes import Area, Game, GameObject
from enemy_editor import EnemyEditor
from enemy_manager import EnemyDefinitionForm, EnemyManager


class EnemyManagerTests(unittest.TestCase):
    def manager(self, health='22'):
        owner = object.__new__(EnemyEditor)
        definition = dict(id='orc', name='Orc', sprite='orc_npc', health=10,
                          movement_speed=1.0, behavior='chase', contact_damage=2,
                          ranged_attack='none', loot_object='helmet_object')
        owner.current_game = Game(properties={'enemies': {'orc': definition}})
        owner.current_area = Area()
        owner.current_area_file = None
        owner.selected_enemy_id = 'orc'
        owner.current_area.objects = [GameObject('orc_npc', 1, 1, {'enemy_id': 'orc', 'loot_object_override': 'shield_object'})]
        owner.tile_manager = Mock()
        owner.tile_manager.get_npc_names.return_value = ['orc_npc']
        owner.tile_manager.get_object_names.return_value = ['helmet_object', 'shield_object']
        owner.draw_area = Mock()
        owner.update_properties_display = Mock()
        form = object.__new__(EnemyDefinitionForm)
        form.owner = owner
        form.selected_enemy_id = 'orc'
        form.draft = deepcopy(definition)
        for name, value in dict(name='Stronger Orc', sprite='orc_npc', health=health,
                                speed='0.5', ranged_attack='none', behavior='chase',
                                damage='4', loot='Helmet').items():
            setattr(form, 'enemy_' + name + '_var', Mock(get=Mock(return_value=value)))
        form._enemy_loot_labels = {'Helmet': 'helmet_object'}
        manager = object.__new__(EnemyManager)
        manager.owner = owner
        manager.form = form
        manager.refresh_list = Mock()
        return manager

    def test_draft_is_isolated_until_save_then_syncs_without_overwriting_override(self):
        manager = self.manager()
        self.assertEqual(manager.owner.get_enemy_definitions()['orc']['health'], 10)
        manager.form.draft['health'] = 12
        self.assertEqual(manager.owner.get_enemy_definitions()['orc']['health'], 10)
        self.assertTrue(manager.save())
        self.assertEqual(manager.owner.get_enemy_definitions()['orc']['health'], 22)
        obj = manager.owner.current_area.objects[0]
        self.assertEqual(obj.properties['enemy_data']['health'], 22)
        self.assertEqual(obj.properties['loot_object_override'], 'shield_object')
        self.assertFalse(hasattr(manager.owner, 'enemy_name_var'))

    @patch('enemy_editor.messagebox.showerror')
    def test_invalid_draft_does_not_change_type_or_instances(self, error):
        manager = self.manager(health='invalid')
        before = deepcopy(manager.owner.current_area.objects)
        self.assertFalse(manager.save())
        self.assertEqual(manager.owner.get_enemy_definitions()['orc']['health'], 10)
        self.assertEqual(manager.owner.current_area.objects, before)
        error.assert_called_once()

    def test_draft_guard_supports_save_discard_and_cancel(self):
        manager = self.manager()
        manager.window = Mock()
        manager.baseline = ('before',)
        manager.values = Mock(return_value=('after',))
        manager.save = Mock(return_value=True)
        for answer, expected in ((None, False), (False, True), (True, True)):
            with patch('enemy_manager.messagebox.askyesnocancel', return_value=answer):
                self.assertEqual(manager.confirm_draft(), expected)
        manager.save.assert_called_once()

    @patch('enemy_manager.messagebox.showwarning')
    @patch('enemy_manager.messagebox.askyesno')
    def test_in_use_definition_cannot_be_deleted(self, confirm, warning):
        manager = self.manager()
        manager.window = Mock()
        manager.owner.enemy_definition_usage = Mock(return_value=['another_area.json (3, 4)'])
        manager.delete()
        self.assertIn('orc', manager.owner.get_enemy_definitions())
        warning.assert_called_once()
        confirm.assert_not_called()

    def test_finish_edit_propagates_cancel(self):
        owner = self.manager().owner
        manager = Mock()
        manager.close.return_value = False
        owner._enemy_manager = manager
        self.assertFalse(owner.finish_enemy_edit())
        manager.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
