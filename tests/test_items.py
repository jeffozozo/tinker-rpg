"""Active items, resource costs, equipment, and persistence integration tests."""

import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image

from data_classes import Area, Game, GameObject, Trigger
from dataclasses import asdict
from runner_engine import RunnerEngine, RunnerError


class ActiveItemTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        for category, names in {
            "games": [], "areas": [], "tiles": ["grass"],
            "npcs": ["fighter_npc", "black_blob_npc"],
            "objects": ["sword_object", "magic_wand_object", "helmet_object", "shield_object",
                        "torch_object", "book_object", "gem_object", "rock_object", "chest_object"],
        }.items():
            (self.root / category).mkdir()
            for name in names:
                Image.new("RGBA", (32, 32)).save(self.root / category / f"{name}.png")
        self.area = Area(width=7, height=5)
        for row in self.area.tiles:
            for tile in row:
                tile.type = "grass"
        self.game = Game(areas=["start.json"], properties={
            "start_area": "start.json", "start_x": 1, "start_y": 2,
            "player": {"sprite": "fighter_npc", "stats": {
                "starting_health": 12, "max_health": 20,
                "starting_energy": 5, "max_energy": 10,
            }, "starting_inventory": ["sword_object", "magic_wand_object", "helmet_object",
                                      "shield_object", "torch_object", "book_object", "gem_object", "rock_object"]},
        }, object_definitions={
            "gem_object": {"item_type": "consumable", "gettable": True,
                           "effects": {"health": 8, "energy": 3}},
            "magic_wand_object": {"energy_cost": 2, "attack_range": 5, "ranged": True},
        })

    def engine(self):
        (self.root / "areas/start.json").write_text(json.dumps(asdict(self.area)))
        (self.root / "games/test.json").write_text(json.dumps(asdict(self.game)))
        return RunnerEngine("test", project_root=self.root)

    def add_enemy(self, x=5, y=2, damage=3):
        self.game.properties["enemies"] = {"blob": {
            "name": "Black Blob", "sprite": "black_blob_npc", "health": 20,
            "movement_speed": 0, "behavior": "chase", "contact_damage": damage,
        }}
        self.area.objects.append(GameObject("black_blob_npc", x, y, {"enemy_id": "blob"}))

    def test_equipment_is_explicit_and_slot_compatibility_is_enforced(self):
        engine = self.engine()
        self.assertEqual(engine.attack_weapon(), (None, 0))
        self.assertFalse(engine.equip(0, "head"))
        for index, slot in ((0, "weapon"), (2, "head"), (3, "offhand"), (4, "light"), (6, "quick")):
            self.assertTrue(engine.equip(index, slot))
            self.assertEqual(engine.equipment[slot], index)
        self.assertEqual(engine.attack_weapon(), ("sword_object", 4))
        self.assertEqual(len([item for item in engine.inventory if item]), 8)
        engine.unequip("weapon")
        self.assertEqual(engine.attack_weapon(), (None, 0))
        self.assertEqual(engine.turn_count, 0)

    def test_head_and_shield_protection_only_applies_when_equipped(self):
        self.add_enemy(x=2, damage=5)
        engine = self.engine()
        engine.wait()
        self.assertEqual(engine.health, 7)
        engine.equip(2)
        engine.equip(3)
        self.assertEqual(engine.armor(), 4)
        engine.wait()
        self.assertEqual(engine.health, 6)
        engine.unequip("head")
        engine.wait()
        self.assertEqual(engine.health, 3)

    def test_consumable_restores_clamps_and_clears_quick_slot(self):
        engine = self.engine()
        engine.equip(6)
        engine.use_slot("quick")
        self.assertEqual((engine.health, engine.energy), (20, 8))
        self.assertEqual(engine.inventory[6], "")
        self.assertIsNone(engine.equipment["quick"])
        self.assertEqual(engine.turn_count, 1)

    def test_full_health_and_energy_does_not_waste_consumable(self):
        engine = self.engine()
        engine.health, engine.energy = 20, 10
        self.assertFalse(engine.use_item(6))
        self.assertEqual(engine.inventory[6], "gem_object")
        self.assertEqual(engine.turn_count, 0)

    def test_light_toggles_and_unequipping_turns_it_off(self):
        engine = self.engine()
        engine.equip(4)
        engine.use_slot("light")
        self.assertIn(4, engine.active_items)
        engine.use_slot("light")
        self.assertNotIn(4, engine.active_items)
        engine.use_slot("light")
        engine.unequip("light")
        self.assertEqual(engine.active_items, set())

    def test_reading_displays_text_without_consuming_or_taking_turn(self):
        engine = self.engine()
        engine.use_item(5)
        self.assertIn("The pages of this old book are blank.", engine.events)
        self.assertEqual(engine.inventory[5], "book_object")
        self.assertEqual(engine.turn_count, 0)

    def test_wand_hits_at_range_using_facing_and_energy(self):
        self.add_enemy()
        engine = self.engine()
        engine.equip(1)
        engine.facing = "right"
        engine.use_slot("weapon")
        self.assertEqual(engine.current_area.objects[0].properties["enemy_health"], 14)
        self.assertEqual(engine.energy, 3)
        self.assertEqual(engine.feedback[0]["from_x"], 1)

    def test_ranged_attack_stops_at_wall(self):
        self.add_enemy()
        self.area.tiles[2][3].walkable_override = False
        engine = self.engine()
        engine.equip(1)
        engine.attack("right")
        self.assertEqual(engine.feedback[0]["kind"], "miss")
        self.assertEqual(engine.current_area.objects[0].properties["enemy_health"], 20)
        self.assertEqual(engine.energy, 3)

    def test_ranged_attack_stops_at_blocking_object(self):
        self.add_enemy()
        self.area.objects.append(GameObject("chest_object", 3, 2, {"walkable": False}))
        engine = self.engine()
        engine.equip(1)
        engine.attack("right")
        self.assertEqual(engine.feedback[0]["kind"], "miss")
        self.assertEqual(engine.current_area.objects[0].properties["enemy_health"], 20)

    def test_ranged_attack_hits_first_enemy(self):
        self.add_enemy()
        self.add_enemy(x=3)
        engine = self.engine()
        engine.equip(1)
        engine.attack("right")
        self.assertEqual(engine.current_area.objects[0].properties["enemy_health"], 20)
        self.assertEqual(engine.current_area.objects[1].properties["enemy_health"], 14)

    def test_energy_and_ammunition_are_checked_before_spending(self):
        self.game.object_definitions["magic_wand_object"]["ammo_item"] = "rock_object"
        engine = self.engine()
        engine.equip(1)
        engine.energy = 1
        self.assertFalse(engine.attack("right"))
        self.assertIn("rock_object", engine.inventory)
        self.assertEqual(engine.energy, 1)
        self.assertEqual(engine.turn_count, 0)
        engine.energy = 5
        self.assertTrue(engine.attack("right"))  # A shot into empty space still costs resources.
        self.assertNotIn("rock_object", engine.inventory)
        self.assertEqual(engine.energy, 3)
        self.assertFalse(engine.attack("right"))
        self.assertEqual(engine.energy, 3)

    def test_inventory_trigger_clears_removed_equipment_even_when_replacing_same_slot(self):
        engine = self.engine()
        engine.equip(0)
        engine._apply_inventory_trigger({"remove": "sword_object", "add": "sword_object"})
        self.assertIsNone(engine.equipment["weapon"])

    def test_equipment_light_and_facing_survive_save_load(self):
        engine = self.engine()
        for index in (0, 2, 3, 4, 6):
            engine.equip(index)
        engine.use_slot("light")
        engine.facing = "left"
        save = self.root / "saved.json"
        engine.save_to_file(save, "Items")
        loaded = RunnerEngine.load_save(save, project_root=self.root)
        self.assertEqual(loaded.equipment, engine.equipment)
        self.assertEqual(loaded.active_items, {4})
        self.assertEqual(loaded.facing, "left")
        self.assertEqual(loaded.armor(), 4)

    def test_invalid_saved_equipment_is_rejected(self):
        engine = self.engine()
        save = self.root / "saved.json"
        engine.save_to_file(save, "Items")
        data = json.loads(save.read_text())
        data["player"]["equipment"] = {"head": 0}
        save.write_text(json.dumps(data))
        with self.assertRaisesRegex(RunnerError, "equipment slot"):
            RunnerEngine.load_save(save, project_root=self.root)

    def test_open_close_changes_collision_and_refuses_to_close_on_player(self):
        self.game.object_definitions["chest_object"] = {"item_type": "openable"}
        self.area.objects.append(GameObject("chest_object", 2, 2))
        engine = self.engine()
        self.assertFalse(engine.move("right"))
        self.assertTrue(engine.interact())
        self.assertTrue(engine.move("right"))
        self.assertFalse(engine.interact())
        self.assertTrue(engine.move("left"))
        self.assertTrue(engine.interact())
        self.assertFalse(engine.move("right"))

    def test_legacy_helmet_armor_effect_is_preserved(self):
        self.game.object_definitions["helmet_object"] = {
            "item_type": "object", "gettable": True, "effects": {"armor": 5},
        }
        engine = self.engine()
        self.assertTrue(engine.equip(2))
        self.assertEqual(engine.armor(), 5)

    def test_equipped_armor_is_inspected_without_unequipping(self):
        engine = self.engine()
        engine.equip(2)
        engine.use_slot("head")
        self.assertEqual(engine.equipment["head"], 2)
        self.assertIn("Helmet: +2 armor while equipped.", engine.events)
        self.assertEqual(engine.turn_count, 0)

    def test_ordinary_object_has_no_use_action(self):
        engine = self.engine()
        self.assertFalse(engine.use_item(7))
        self.assertFalse(engine.equip(7))
        self.assertEqual(engine.inventory[7], "rock_object")

    def pickup_pair(self):
        self.area.objects.append(GameObject("sword_object", 2, 2))
        self.area.triggers = [
            Trigger(2, 2, "inventory", "take_sword", {"add": "sword_object", "once": True}),
            Trigger(2, 2, "area_object", "hide_sword", {"action": "remove", "object": "sword_object", "once": True}),
        ]

    def test_paired_pickup_grants_one_item_and_removes_map_object_once(self):
        self.game.properties["player"]["starting_inventory"][0] = ""
        self.pickup_pair()
        engine = self.engine()
        engine.move("right")
        self.assertEqual(engine.inventory.count("sword_object"), 1)
        self.assertEqual(engine.current_area.objects, [])
        self.assertEqual(engine.current_area.triggers, [])
        engine.move("left")
        engine.move("right")
        self.assertEqual(engine.inventory.count("sword_object"), 1)
        path = self.root / "pickup.json"
        engine.save_to_file(path, "Picked up")
        loaded = RunnerEngine.load_save(path, project_root=self.root)
        loaded.move("left")
        loaded.move("right")
        self.assertEqual(loaded.inventory.count("sword_object"), 1)
        self.assertEqual(loaded.current_area.objects, [])

    def test_full_inventory_stops_map_removal_and_allows_pickup_retry(self):
        self.pickup_pair()
        engine = self.engine()
        engine.move("right")
        self.assertEqual(len(engine.current_area.objects), 1)
        self.assertEqual(len(engine.current_area.triggers), 2)
        self.assertIn("inventory is full", engine.events[-1])
        engine._remove_inventory_item(0)
        engine.move("left")
        engine.move("right")
        self.assertEqual(engine.inventory.count("sword_object"), 1)
        self.assertEqual(engine.current_area.objects, [])

    def test_reverse_pair_removes_equipped_item_and_adds_map_object(self):
        self.area.triggers = [
            Trigger(2, 2, "inventory", "give_sword", {"remove": "sword_object", "once": True}),
            Trigger(2, 2, "area_object", "show_sword", {"action": "add", "object": "sword_object", "once": True}),
        ]
        engine = self.engine()
        engine.equip(0)
        engine.move("right")
        self.assertNotIn("sword_object", engine.inventory)
        self.assertIsNone(engine.equipment["weapon"])
        self.assertEqual([(obj.type, obj.x, obj.y) for obj in engine.current_area.objects], [("sword_object", 2, 2)])
        self.assertEqual(engine.current_area.triggers, [])

    def test_missing_inventory_item_stops_following_map_addition(self):
        self.game.properties["player"]["starting_inventory"][0] = ""
        self.area.triggers = [
            Trigger(2, 2, "inventory", "give_sword", {"remove": "sword_object", "once": True}),
            Trigger(2, 2, "area_object", "show_sword", {"object": "sword_object", "once": True}),
        ]
        engine = self.engine()
        engine.move("right")
        self.assertEqual(engine.current_area.objects, [])
        self.assertEqual(len(engine.current_area.triggers), 2)

    def test_object_removal_only_affects_named_item_at_target_coordinates(self):
        self.area.objects = [GameObject("sword_object", 3, 2), GameObject("sword_object", 4, 2), GameObject("helmet_object", 3, 2)]
        self.area.triggers = [Trigger(2, 2, "area_object", "remove_target", {
            "action": "remove", "object": "sword_object", "x": 3, "y": 2,
        })]
        engine = self.engine()
        engine.move("right")
        self.assertEqual([(obj.type, obj.x) for obj in engine.current_area.objects], [("sword_object", 4), ("helmet_object", 3)])

    def test_repeating_inventory_trigger_remains_repeatable(self):
        self.game.properties["player"]["starting_inventory"] = []
        self.area.triggers = [Trigger(2, 2, "inventory", "grant", {"add": "sword_object"})]
        engine = self.engine()
        engine.move("right")
        engine.move("left")
        engine.move("right")
        self.assertEqual(engine.inventory.count("sword_object"), 2)
        self.assertEqual(len(engine.current_area.triggers), 1)

    def test_ended_game_blocks_item_actions(self):
        engine = self.engine()
        engine.ended = True
        self.assertFalse(engine.equip(0))
        self.assertFalse(engine.use_item(6))
        self.assertFalse(engine.unequip("weapon"))
        self.assertEqual(engine.inventory[6], "gem_object")


if __name__ == "__main__":
    unittest.main()
