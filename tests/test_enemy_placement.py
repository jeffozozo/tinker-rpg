import json
from dataclasses import asdict
from pathlib import Path
import tempfile
import unittest
from PIL import Image
from data_classes import Area, Game, GameObject, Trigger
from runner_engine import RunnerEngine


class EnemyPlacementTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(); self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        for folder in ('games', 'areas', 'tiles', 'npcs', 'objects'):
            (self.root / folder).mkdir()
        for folder, names in [('tiles', ['grass']), ('npcs', ['fighter_npc', 'orc_npc', 'black_blob_npc']), ('objects', ['gem_object'])]:
            for name in names: Image.new('RGBA', (32, 32)).save(self.root / folder / (name + '.png'))
        self.areas = {}
        for name in ('first.json', 'second.json'):
            a = Area(name=name, width=7, height=5)
            for row in a.tiles:
                for tile in row: tile.type = 'grass'
            self.areas[name] = a
        self.enemies = {name: dict(id=name, name=name, sprite=sprite, health=7,
                                  movement_speed=0, behavior='stationary', contact_damage=2, loot_object='gem_object')
                        for name, sprite in [('orc', 'orc_npc'), ('blob', 'black_blob_npc')]}
        self.game = Game(areas=list(self.areas), object_definitions={'gem_object': {'gettable': True}}, properties={
            'start_area': 'first.json', 'start_x': 1, 'start_y': 2,
            'player': {'sprite': 'fighter_npc'}, 'enemies': self.enemies})

    def engine(self):
        for name, a in self.areas.items(): (self.root / 'areas' / name).write_text(json.dumps(asdict(a)))
        (self.root / 'games/test.json').write_text(json.dumps(asdict(self.game)))
        return RunnerEngine('test', project_root=self.root)

    def action(self, action='place', scope='position', **params):
        self.areas['first.json'].triggers = [Trigger(2, 2, 'enemy_placement', 'enemy_action', dict(
            action=action, scope=scope, enemy_id='orc', area='', x=4, y=2, charges=1, **params))]

    def enemy(self, area='first.json', kind='orc', x=4, y=2):
        self.areas[area].objects.append(GameObject(self.enemies[kind]['sprite'], x, y, {'enemy_id': kind}))

    def test_place_creates_real_enemy_with_fresh_identity_and_type_loot(self):
        self.action(); e = self.engine(); e.move('right')
        obj = e.current_area.objects[0]
        self.assertEqual((obj.x, obj.y), (4, 2))
        self.assertEqual(obj.properties['enemy_id'], 'orc')
        self.assertEqual(obj.properties['enemy_data']['loot_object'], 'gem_object')
        self.assertEqual(obj.properties['enemy_health'], 7)
        self.assertTrue(obj.properties['enemy_instance_id'])
        self.assertFalse(e.current_area.triggers)
        obj.properties['enemy_health'] = 0; e.wait()
        self.assertEqual([o.type for o in e.current_area.objects], ['gem_object'])

    def test_occupied_target_fails_without_charge_or_later_action(self):
        self.action(); self.enemy()
        self.areas['first.json'].triggers.append(Trigger(2, 2, 'funds', 'later', {'action': 'add', 'amount': 10}))
        e = self.engine(); e.move('right')
        self.assertEqual(len(e.current_area.objects), 1)
        self.assertEqual(e.stats['gold'], 0)
        self.assertEqual(e.current_area.triggers[0].parameters['charges'], 1)
        self.assertTrue(any('no room' in event for event in e.events))

    def test_place_rejects_blocked_tile_and_player_tile(self):
        for target in ('floor', 'player'):
            with self.subTest(target=target):
                self.action()
                if target == 'floor': self.areas['first.json'].tiles[2][4].walkable_override = False
                else:
                    self.areas['first.json'].tiles[2][4].walkable_override = None
                    self.areas['first.json'].triggers[0].parameters.update(x=2, y=2)
                e = self.engine(); e.move('right')
                self.assertFalse(e.current_area.objects)
                self.assertEqual(len(e.current_area.triggers), 1)

    def test_remove_at_position_only_matches_selected_type_and_produces_no_loot(self):
        self.action('remove'); self.enemy(); self.enemy(kind='blob', x=5)
        e = self.engine(); e.move('right')
        self.assertEqual([o.properties['enemy_id'] for o in e.current_area.objects], ['blob'])
        self.assertFalse(e.current_area.triggers)
        self.assertFalse(any(o.type == 'gem_object' for o in e.current_area.objects))

    def test_remove_all_in_area_preserves_other_area_and_other_type(self):
        self.action('remove', 'area'); self.enemy(); self.enemy(x=5); self.enemy(kind='blob', x=3)
        self.enemy('second.json')
        e = self.engine(); e.move('right')
        self.assertEqual([o.properties['enemy_id'] for o in e.current_area.objects], ['blob'])
        self.assertEqual(len(e.areas['second.json'].objects), 1)

    def test_remove_all_game_and_save_load(self):
        self.action('remove', 'game'); self.enemy(); self.enemy('second.json'); self.enemy('second.json', kind='blob', x=5)
        e = self.engine(); e.move('right')
        self.assertFalse(e.current_area.objects)
        self.assertEqual([o.properties['enemy_id'] for o in e.areas['second.json'].objects], ['blob'])
        save = self.root / 'removed.save.json'; e.save_to_file(save, 'Removed')
        loaded = RunnerEngine.load_save(save, project_root=self.root)
        self.assertFalse(any(o.properties.get('enemy_id') == 'orc' for a in loaded.areas.values() for o in a.objects))
        self.assertEqual(loaded.properties['enemies']['orc'], e.properties['enemies']['orc'])

    def test_named_trigger_can_spawn_in_another_area_and_persist(self):
        self.game.properties['trigger_definitions'] = {'summon': dict(name='summon_orc', trigger_type='enemy_placement', enabled=True,
            parameters=dict(action='place', scope='position', enemy_id='orc', area='second', x=4, y=2, charges=0))}
        self.areas['first.json'].triggers = [Trigger(2, 2, definition_id='summon')]
        e = self.engine(); e.move('right')
        obj = e.areas['second.json'].objects[0]; identity = obj.properties['enemy_instance_id']
        save = self.root / 'spawned.save.json'; e.save_to_file(save, 'Spawned')
        loaded = RunnerEngine.load_save(save, project_root=self.root)
        self.assertEqual(loaded.areas['second.json'].objects[0].properties['enemy_instance_id'], identity)

    def test_invalid_enemy_target_is_reported_and_repeated_remove_is_safe(self):
        self.action('remove', 'game'); e = self.engine(); e.move('right')
        self.assertFalse(e.current_area.triggers)
        self.action(); self.areas['first.json'].triggers[0].parameters['enemy_id'] = 'missing'
        e = self.engine()
        self.assertTrue(any('enemy type' in issue for issue in e.validation_issues))


if __name__ == '__main__': unittest.main()
