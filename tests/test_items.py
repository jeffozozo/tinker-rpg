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

    def loot_engine(self, loot="gem_object"):
        self.add_enemy(x=2, y=2, damage=0)
        self.game.properties["enemies"]["blob"].update(health=1, loot_object=loot)
        engine = self.engine()
        engine.equip(0)
        return engine

    def test_enemy_type_loot_drops_for_each_instance_at_death_position(self):
        engine = self.loot_engine()
        original = engine.current_area.objects[0]
        engine.current_area.objects.append(GameObject(original.type, 3, 2, dict(original.properties)))
        engine.attack("right")
        self.assertEqual(sum(o.type == "gem_object" for o in engine.current_area.objects), 1)
        self.assertEqual((next(o for o in engine.current_area.objects if o.type == "gem_object").x), 2)
        engine.inventory[6] = ""
        engine.move("right")
        self.assertEqual(engine.inventory[6], "gem_object")
        engine.attack("right")
        self.assertEqual([(o.x, o.y) for o in engine.current_area.objects if o.type == "gem_object"], [(3, 2)])
        engine.wait()
        self.assertEqual(sum(o.type == "gem_object" for o in engine.current_area.objects), 1)

    def test_enemy_loot_full_inventory_remains_and_survives_save_load(self):
        engine = self.loot_engine()
        engine.attack("right")
        engine.move("right")
        self.assertTrue(any(o.type == "gem_object" for o in engine.current_area.objects))
        path = self.root / "loot.save.json"
        engine.save_to_file(path, "Loot")
        engine = RunnerEngine.load_save(path, project_root=self.root)
        engine.inventory[6] = ""
        engine.move("left")
        engine.move("right")
        self.assertEqual(engine.inventory[6], "gem_object")
        self.assertFalse(any(o.type == "gem_object" for o in engine.current_area.objects))
        self.assertFalse(engine.current_area.triggers)

    def test_noncollectible_enemy_loot_uses_normal_object_behavior(self):
        engine = self.loot_engine("chest_object")
        engine.attack("right")
        loot = next(o for o in engine.current_area.objects if o.type == "chest_object")
        self.assertEqual((loot.x, loot.y), (2, 2))
        self.assertFalse(loot.properties.get("dropped_item", False))
        self.assertFalse(engine.current_area.triggers)

    def test_enemy_without_loot_preserves_old_behavior(self):
        engine = self.loot_engine("")
        engine.attack("right")
        self.assertFalse(engine.current_area.objects)
        self.assertFalse(engine.current_area.triggers)

    def test_ranged_kill_leaves_loot_at_moved_enemy_position(self):
        engine = self.loot_engine()
        enemy = engine.current_area.objects[0]
        enemy.x = 4
        engine.equip(1)
        engine.attack("right")
        self.assertEqual([(o.x, o.y) for o in engine.current_area.objects], [(4, 2)])
        self.assertEqual(engine.current_area.objects[0].type, "gem_object")

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

    def test_world_object_changes_require_walking_onto_a_trigger(self):
        self.game.object_definitions["chest_object"] = {"item_type": "openable"}
        self.area.objects.append(GameObject("chest_object", 2, 2))
        self.area.triggers = [Trigger(1, 1, "area_object", "remove_chest", {
            "action": "remove", "object": "chest_object", "x": 2, "y": 2, "once": True,
        })]
        engine = self.engine()
        self.assertFalse(engine.move("right"))
        self.assertTrue(engine.move("up"))
        self.assertEqual(engine.current_area.objects, [])
        self.assertTrue(engine.move("down"))
        self.assertTrue(engine.move("right"))

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
        self.assertIn("Helmet: protects against 2 damage while equipped.", engine.events)
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

    def test_stat_trigger_changes_health_once_on_entry(self):
        self.area.triggers = [Trigger(2, 2, "player_stats", "heal", {"stat": "health", "amount": 5, "once": True})]
        engine = self.engine()
        engine.move("right")
        self.assertEqual(engine.health, 17)
        engine.move("left")
        engine.move("right")
        self.assertEqual(engine.health, 17)
        self.assertEqual(engine.current_area.triggers, [])

    def test_stat_trigger_clamps_current_values_and_stat_minimums(self):
        engine = self.engine()
        engine._apply_stat_trigger({"stat": "health", "amount": 100})
        engine._apply_stat_trigger({"stat": "energy", "amount": 100})
        self.assertEqual((engine.health, engine.energy), (20, 10))
        with self.assertRaisesRegex(RunnerError, "Insufficient funds"):
            engine._apply_stat_trigger({"stat": "gold", "amount": -100})
        self.assertEqual(engine.stats["gold"], 0)
        engine._apply_stat_trigger({"stat": "max_health", "amount": -100})
        engine._apply_stat_trigger({"stat": "max_energy", "amount": -100})
        self.assertEqual((engine.stats["max_health"], engine.health), (1, 1))
        self.assertEqual((engine.stats["max_energy"], engine.energy), (0, 0))

    def test_stat_damage_can_end_game_and_stop_remaining_tile_triggers(self):
        self.area.triggers = [
            Trigger(2, 2, "player_stats", "damage", {"stat": "health", "amount": -100}),
            Trigger(2, 2, "player_stats", "reward", {"stat": "gold", "amount": 10}),
        ]
        engine = self.engine()
        engine.move("right")
        self.assertEqual(engine.health, 0)
        self.assertTrue(engine.ended)
        self.assertEqual(engine.end_result, "lose")
        self.assertEqual(engine.stats["gold"], 0)

    def test_stat_trigger_changes_combat_strength_and_persists_all_runtime_stats(self):
        engine = self.engine()
        for stat, amount in (("max_health", 10), ("max_energy", 5), ("strength", 4), ("intelligence", 3), ("gold", 10)):
            engine._apply_stat_trigger({"stat": stat, "amount": amount})
        engine._apply_stat_trigger({"stat": "health", "amount": 100})
        engine._apply_stat_trigger({"stat": "energy", "amount": 100})
        path = self.root / "stats.json"
        engine.save_to_file(path, "Stats changed")
        loaded = RunnerEngine.load_save(path, project_root=self.root)
        for stat in ("max_health", "max_energy", "strength", "intelligence", "gold"):
            self.assertEqual(loaded.stats[stat], engine.stats[stat])
        self.assertEqual((loaded.health, loaded.energy), (30, 15))

    def test_legacy_save_without_runtime_stats_still_loads(self):
        engine = self.engine()
        path = self.root / "legacy.json"
        engine.save_to_file(path, "Legacy")
        saved = json.loads(path.read_text())
        saved["player"].pop("stats")
        path.write_text(json.dumps(saved))
        loaded = RunnerEngine.load_save(path, project_root=self.root)
        self.assertEqual(loaded.health, 12)
        self.assertEqual(loaded.stats["max_health"], 20)

    def test_invalid_stat_changes_are_rejected_without_changing_state(self):
        engine = self.engine()
        for params in ({"stat": "health", "amount": 1.5}, {"stat": "unknown", "amount": 5}, {"stat": "health", "amount": True}):
            with self.subTest(params=params), self.assertRaises(RunnerError):
                engine._apply_stat_trigger(params)
        self.assertEqual(engine.health, 12)

    def test_drop_creates_trigger_pair_and_recovers_item_only_on_reentry(self):
        engine = self.engine()
        engine.equip(0)
        self.assertTrue(engine.drop_item(0))
        self.assertEqual(engine.inventory[0], "")
        self.assertIsNone(engine.equipment["weapon"])
        self.assertEqual(engine.turn_count, 1)
        self.assertEqual(len(engine.current_area.objects), 1)
        self.assertEqual([trigger.trigger_type for trigger in engine.current_area.triggers], ["inventory", "area_object"])
        self.assertTrue(all(trigger.parameters["charges"] == 1 for trigger in engine.current_area.triggers))
        engine.move("up")
        engine.move("down")
        self.assertEqual(engine.inventory.count("sword_object"), 1)
        self.assertEqual(engine.current_area.objects, [])
        self.assertEqual(engine.current_area.triggers, [])
        engine.move("up")
        engine.move("down")
        self.assertEqual(engine.inventory.count("sword_object"), 1)

    def test_dropping_active_light_turns_it_off(self):
        engine = self.engine()
        engine.use_item(4)
        self.assertIn(4, engine.active_items)
        engine.drop_item(4)
        self.assertEqual(engine.active_items, set())
        self.assertIsNone(engine.equipment["light"])
        self.assertEqual(engine.inventory[4], "")

    def test_drop_refuses_objects_triggers_and_blocked_floor_without_mutation(self):
        for obstacle in ("object", "trigger", "floor"):
            with self.subTest(obstacle=obstacle):
                engine = self.engine()
                engine.equip(0)
                if obstacle == "object":
                    engine.current_area.objects.append(GameObject("rock_object", 1, 2))
                elif obstacle == "trigger":
                    engine.current_area.triggers.append(Trigger(1, 2, "show_message", "sign", {"message": "Hello"}))
                else:
                    engine.current_area.tiles[2][1].walkable_override = False
                objects = list(engine.current_area.objects)
                triggers = list(engine.current_area.triggers)
                self.assertFalse(engine.drop_item(0))
                self.assertEqual(engine.inventory[0], "sword_object")
                self.assertEqual(engine.equipment["weapon"], 0)
                self.assertEqual(engine.turn_count, 0)
                self.assertEqual(engine.current_area.objects, objects)
                self.assertEqual(engine.current_area.triggers, triggers)
                self.assertIn("Move to open ground", engine.events[-1])

    def test_full_inventory_keeps_dropped_item_and_triggers_for_later(self):
        engine = self.engine()
        engine.drop_item(0)
        engine.inventory[0] = "rock_object"
        engine.move("up")
        engine.move("down")
        self.assertEqual(len(engine.current_area.objects), 1)
        self.assertEqual(len(engine.current_area.triggers), 2)
        self.assertNotIn("sword_object", engine.inventory)
        engine._remove_inventory_item(7)
        engine.move("up")
        engine.move("down")
        self.assertIn("sword_object", engine.inventory)
        self.assertEqual(engine.current_area.objects, [])

    def test_drop_state_survives_save_and_blocking_items_stay_recoverable(self):
        engine = self.engine()
        engine.inventory[0] = "chest_object"
        engine.object_definitions["chest_object"] = {"item_type": "openable", "walkable": False}
        engine.game["object_definitions"] = engine.object_definitions
        engine.drop_item(0)
        path = self.root / "drop.json"
        engine.save_to_file(path, "Dropped chest")
        loaded = RunnerEngine.load_save(path, project_root=self.root)
        self.assertEqual(loaded.inventory[0], "")
        self.assertEqual(len(loaded.current_area.triggers), 2)
        self.assertTrue(loaded.current_area.objects[0].properties["dropped_item"])
        loaded.move("up")
        self.assertTrue(loaded.move("down"))
        self.assertEqual(loaded.inventory[0], "chest_object")
        self.assertEqual(loaded.current_area.objects, [])

    def test_dropping_one_copy_does_not_unequip_another_copy(self):
        engine = self.engine()
        engine.inventory[7] = "sword_object"
        engine.equip(0)
        engine.drop_item(7)
        self.assertEqual(engine.inventory[0], "sword_object")
        self.assertEqual(engine.equipment["weapon"], 0)

    def test_drop_uses_turn_and_enemies_can_attack(self):
        self.add_enemy(x=2, y=2, damage=3)
        engine = self.engine()
        self.assertTrue(engine.drop_item(0))
        self.assertEqual(engine.health, 9)
        self.assertEqual(engine.turn_count, 1)

    def test_drop_rejects_invalid_slots_and_ended_games(self):
        engine = self.engine()
        for index in (-1, 8, True, None):
            self.assertFalse(engine.drop_item(index))
        engine.ended = True
        self.assertFalse(engine.drop_item(0))
        self.assertEqual(engine.inventory[0], "sword_object")
        self.assertEqual(engine.current_area.objects, [])

    def test_nine_charge_trigger_stays_exhausted_on_tenth_and_later_entries(self):
        self.area.triggers = [Trigger(2, 2, "player_stats", "nine_rewards", {"stat": "gold", "amount": 1, "charges": 9})]
        engine = self.engine()
        for entry in range(1, 13):
            engine.move("right")
            self.assertEqual(engine.stats["gold"], min(entry, 9))
            engine.move("left")
        self.assertEqual(engine.current_area.triggers, [])
        path = self.root / "exhausted.json"
        engine.save_to_file(path, "Exhausted")
        loaded = RunnerEngine.load_save(path, project_root=self.root)
        loaded.move("right")
        self.assertEqual(loaded.stats["gold"], 9)
        self.assertEqual(loaded.current_area.triggers, [])

    def test_zero_charge_setting_is_unlimited(self):
        self.area.triggers = [Trigger(2, 2, "player_stats", "unlimited", {"stat": "gold", "amount": 1, "charges": 0})]
        engine = self.engine()
        for _ in range(12):
            engine.move("right")
            engine.move("left")
        self.assertEqual(engine.stats["gold"], 12)
        self.assertEqual(engine.current_area.triggers[0].parameters["charges"], 0)

    def test_remaining_finite_charges_survive_save_load(self):
        self.area.triggers = [Trigger(2, 2, "player_stats", "three", {"stat": "gold", "amount": 1, "charges": 3})]
        engine = self.engine()
        engine.move("right")
        engine.move("left")
        self.assertEqual(engine.current_area.triggers[0].parameters["charges"], 2)
        path = self.root / "charges.json"
        engine.save_to_file(path, "Two left")
        loaded = RunnerEngine.load_save(path, project_root=self.root)
        for _ in range(3):
            loaded.move("right")
            loaded.move("left")
        self.assertEqual(loaded.stats["gold"], 3)
        self.assertEqual(loaded.current_area.triggers, [])

    def test_failed_inventory_trigger_does_not_consume_charge(self):
        self.area.triggers = [Trigger(2, 2, "inventory", "limited_pickup", {"add": "sword_object", "charges": 2})]
        engine = self.engine()
        engine.move("right")
        self.assertEqual(engine.current_area.triggers[0].parameters["charges"], 2)
        engine._remove_inventory_item(7)
        engine.move("left")
        engine.move("right")
        self.assertEqual(engine.current_area.triggers[0].parameters["charges"], 1)

    def test_one_charge_teleport_retires_in_its_source_area(self):
        self.game.areas.append("second.json")
        destination = Area(width=3, height=3)
        for row in destination.tiles:
            for tile in row:
                tile.type = "grass"
        (self.root / "areas/second.json").write_text(json.dumps(asdict(destination)))
        self.area.triggers = [Trigger(2, 2, "teleport", "one_trip", {"area": "second", "x": 1, "y": 1, "charges": 1})]
        engine = self.engine()
        engine.move("right")
        self.assertEqual(engine.current_area_filename, "second.json")
        self.assertEqual(engine.areas["start.json"].triggers, [])

    def test_explicit_unlimited_overrides_legacy_once(self):
        self.area.triggers = [Trigger(2, 2, "player_stats", "migrated", {"stat": "gold", "amount": 1, "once": True, "charges": 0})]
        engine = self.engine()
        for _ in range(2):
            engine.move("right")
            engine.move("left")
        self.assertEqual(engine.stats["gold"], 2)
        self.assertEqual(len(engine.current_area.triggers), 1)

    def test_invalid_charges_do_not_execute_trigger(self):
        for value in (-1, 1.5, True, "2", None):
            with self.subTest(charges=value):
                self.area.triggers = [Trigger(2, 2, "player_stats", "bad", {"stat": "gold", "amount": 10, "charges": value})]
                engine = self.engine()
                self.assertTrue(engine.validation_issues)
                engine.move("right")
                self.assertEqual(engine.stats["gold"], 0)
                self.assertEqual(len(engine.current_area.triggers), 1)

    def test_funds_trigger_adds_money_with_limited_charges(self):
        self.area.triggers = [Trigger(2, 2, "funds", "reward", {"action": "add", "amount": 5, "charges": 2})]
        engine = self.engine()
        for _ in range(3):
            engine.move("right")
            engine.move("left")
        self.assertEqual(engine.stats["gold"], 10)
        self.assertEqual(engine.current_area.triggers, [])

    def test_insufficient_funds_preserves_balance_charge_and_later_triggers(self):
        self.game.properties["player"]["stats"]["gold"] = 3
        self.area.triggers = [
            Trigger(2, 2, "funds", "pay", {"action": "remove", "amount": 10, "charges": 2}),
            Trigger(2, 2, "show_message", "reward", {"message": "Paid successfully", "charges": 1}),
        ]
        engine = self.engine()
        engine.move("right")
        self.assertEqual(engine.stats["gold"], 3)
        self.assertEqual(len(engine.current_area.triggers), 2)
        self.assertEqual(engine.current_area.triggers[0].parameters["charges"], 2)
        self.assertNotIn("Paid successfully", engine.events)
        engine._apply_funds_trigger({"action": "add", "amount": 7})
        engine.move("left")
        engine.move("right")
        self.assertEqual(engine.stats["gold"], 0)
        self.assertEqual(engine.current_area.triggers[0].parameters["charges"], 1)
        self.assertIn("Paid successfully", engine.events)

    def test_funds_and_remaining_charges_survive_save_load(self):
        self.area.triggers = [Trigger(2, 2, "funds", "reward", {"action": "add", "amount": 8, "charges": 2})]
        engine = self.engine()
        engine.move("right")
        engine.move("left")
        path = self.root / "funds.json"
        engine.save_to_file(path, "Funds")
        loaded = RunnerEngine.load_save(path, project_root=self.root)
        self.assertEqual(loaded.stats["gold"], 8)
        self.assertEqual(loaded.current_area.triggers[0].parameters["charges"], 1)
        loaded.move("right")
        self.assertEqual(loaded.stats["gold"], 16)
        self.assertEqual(loaded.current_area.triggers, [])

    def test_invalid_funds_amounts_and_actions_do_not_change_balance(self):
        engine = self.engine()
        engine.stats["gold"] = 10
        for params in ({"action": "remove", "amount": -5}, {"action": "add", "amount": 0},
                       {"action": "add", "amount": 1.5}, {"action": "add", "amount": True},
                       {"action": "unknown", "amount": 1}):
            with self.subTest(params=params), self.assertRaises(RunnerError):
                engine._apply_funds_trigger(params)
        self.assertEqual(engine.stats["gold"], 10)

    def test_legacy_gold_removal_uses_affordability_rules(self):
        self.game.properties["player"]["stats"]["gold"] = 3
        self.area.triggers = [Trigger(2, 2, "player_stats", "legacy_pay", {"stat": "gold", "amount": -10, "charges": 1})]
        engine = self.engine()
        engine.move("right")
        self.assertEqual(engine.stats["gold"], 3)
        self.assertEqual(len(engine.current_area.triggers), 1)
        self.assertTrue(any("You need $10, but have only $3." in event for event in engine.events))

    def attach_enemy(self, *triggers, identity="warden"):
        self.add_enemy(x=2, y=2, damage=0)
        self.game.properties["enemies"]["blob"]["health"] = 1
        self.area.objects[-1].properties["enemy_instance_id"] = identity
        for trigger in triggers:
            trigger.enemy_attached = identity
        self.area.triggers.extend(triggers)

    def test_enemy_death_fires_trigger_at_fixed_position_without_moving_player(self):
        self.attach_enemy(Trigger(5, 3, "area_object", "relic", {
            "object": "gem_object", "action": "add", "charges": 1,
        }))
        engine = self.engine()
        engine.attack("right")
        self.assertEqual((engine.player_x, engine.player_y), (1, 2))
        self.assertEqual([(obj.type, obj.x, obj.y) for obj in engine.current_area.objects], [("gem_object", 5, 3)])
        self.assertEqual(engine.current_area.triggers, [])

    def test_walking_on_attached_trigger_does_not_fire_while_enemy_lives(self):
        self.attach_enemy(Trigger(1, 1, "funds", "reward", {"action": "add", "amount": 5}))
        engine = self.engine()
        engine.move("up")
        self.assertEqual(engine.stats["gold"], 0)
        engine.move("down")
        engine.attack("right")
        self.assertEqual(engine.stats["gold"], 5)
        engine.move("up")
        self.assertEqual(engine.stats["gold"], 5)  # No repeat merely from walking after the event.

    def test_attachment_tracks_a_moving_enemy(self):
        self.attach_enemy(Trigger(6, 3, "funds", "reward", {"action": "add", "amount": 5, "charges": 1}))
        self.area.objects[-1].x, self.area.objects[-1].y = 4, 2
        self.game.properties["enemies"]["blob"]["movement_speed"] = 1
        engine = self.engine()
        engine.wait()
        engine.wait()
        self.assertEqual(engine.current_area.objects[0].x, 2)
        engine.attack("right")
        self.assertEqual(engine.stats["gold"], 5)

    def test_attachment_is_specific_to_one_instance_of_same_enemy_type(self):
        self.attach_enemy(Trigger(5, 3, "funds", "reward", {"action": "add", "amount": 5, "charges": 1}))
        self.area.objects[-1].x = 4
        self.area.objects.append(GameObject("black_blob_npc", 2, 2, {"enemy_id": "blob", "enemy_instance_id": "other"}))
        engine = self.engine()
        engine.attack("right")
        self.assertEqual(engine.stats["gold"], 0)
        engine.move("right")
        engine.move("right")
        engine.attack("right")
        self.assertEqual(engine.stats["gold"], 5)

    def test_attached_trigger_order_and_charges_are_preserved(self):
        self.attach_enemy(
            Trigger(5, 3, "funds", "grant", {"action": "add", "amount": 5, "charges": 2}),
            Trigger(5, 3, "funds", "take", {"action": "remove", "amount": 3, "charges": 1}),
        )
        engine = self.engine()
        engine.attack("right")
        self.assertEqual(engine.stats["gold"], 2)
        self.assertEqual(len(engine.current_area.triggers), 1)
        self.assertEqual(engine.current_area.triggers[0].parameters["charges"], 1)
        self.assertFalse(engine.current_area.triggers[0].enemy_pending)

    def test_full_inventory_keeps_defeat_action_pending_for_walk_retry(self):
        self.attach_enemy(
            Trigger(1, 1, "inventory", "reward", {"add": "sword_object", "charges": 1}),
            Trigger(1, 1, "area_object", "show_reward", {"object": "gem_object", "charges": 1}),
        )
        engine = self.engine()
        engine.attack("right")
        self.assertEqual(len(engine.current_area.triggers), 2)
        self.assertTrue(all(trigger.enemy_pending for trigger in engine.current_area.triggers))
        self.assertEqual(engine.current_area.objects, [])
        engine._remove_inventory_item(7)
        engine.move("up")
        self.assertEqual(engine.inventory[7], "sword_object")
        self.assertEqual(engine.current_area.triggers, [])
        self.assertEqual([(obj.x, obj.y) for obj in engine.current_area.objects], [(1, 1)])

    def test_attachment_and_pending_defeat_actions_survive_save_load(self):
        self.attach_enemy(Trigger(1, 1, "inventory", "reward", {"add": "sword_object", "charges": 1}))
        engine = self.engine()
        path = self.root / "attached.json"
        engine.save_to_file(path, "Before defeat")
        loaded = RunnerEngine.load_save(path, project_root=self.root)
        self.assertEqual(loaded.current_area.triggers[0].enemy_attached, "warden")
        loaded.attack("right")  # Full inventory; action remains pending.
        loaded.save_to_file(path, "After defeat")
        loaded = RunnerEngine.load_save(path, project_root=self.root)
        self.assertEqual(loaded.validation_issues, [])
        self.assertTrue(loaded.current_area.triggers[0].enemy_pending)
        loaded._remove_inventory_item(7)
        loaded.move("up")
        self.assertEqual(loaded.inventory[7], "sword_object")
        self.assertEqual(loaded.current_area.triggers, [])

    def test_enemy_death_can_end_game(self):
        self.attach_enemy(Trigger(5, 3, "game_end", "win", {"win_lose": "win", "charges": 1}))
        engine = self.engine()
        engine.attack("right")
        self.assertTrue(engine.ended)
        self.assertEqual(engine.end_result, "win")

    def test_missing_attached_enemy_is_reported_and_does_not_activate_on_walk(self):
        self.area.triggers = [Trigger(1, 1, "funds", "missing", {"action": "add", "amount": 5}, enemy_attached="absent")]
        engine = self.engine()
        self.assertTrue(any("attached enemy is missing" in issue for issue in engine.validation_issues))
        engine.move("up")
        self.assertEqual(engine.stats["gold"], 0)

    def test_successful_unlimited_attachment_does_not_fire_again_after_save_load(self):
        self.attach_enemy(Trigger(1, 1, "funds", "once_per_defeat", {"action": "add", "amount": 5, "charges": 0}))
        engine = self.engine()
        enemy = engine.current_area.objects[0]
        engine.attack("right")
        engine._activate_enemy_triggers(enemy)  # A duplicate notification must not repeat the reward.
        self.assertEqual(engine.stats["gold"], 5)
        path = self.root / "completed_enemy.json"
        engine.save_to_file(path, "Enemy gone")
        loaded = RunnerEngine.load_save(path, project_root=self.root)
        self.assertEqual(loaded.validation_issues, [])
        loaded.move("up")
        self.assertEqual(loaded.stats["gold"], 5)

    def test_attached_teleport_uses_player_position_and_consumes_source_charge(self):
        destination = Area(width=3, height=3)
        for row in destination.tiles:
            for tile in row:
                tile.type = "grass"
        destination.triggers = [Trigger(1, 1, "funds", "arrival", {"action": "add", "amount": 3})]
        self.game.areas.append("second.json")
        (self.root / "areas/second.json").write_text(json.dumps(asdict(destination)))
        self.attach_enemy(Trigger(5, 3, "teleport", "escape", {"area": "second", "x": 1, "y": 1, "charges": 1}))
        engine = self.engine()
        engine.attack("right")
        self.assertEqual(engine.current_area_filename, "second.json")
        self.assertEqual((engine.player_x, engine.player_y), (1, 1))
        self.assertEqual(engine.stats["gold"], 3)
        self.assertEqual(engine.areas["start.json"].triggers, [])

    def test_missing_quest_item_does_not_reveal_its_name_or_trigger(self):
        self.game.properties["player"]["starting_inventory"] = []
        self.area.triggers = [Trigger(2, 2, "inventory", "secret_key_to_vault", {"remove": "red_gem_object"})]
        engine = self.engine()
        engine.move("right")
        self.assertIn("You do not have what you need here.", engine.events)
        self.assertFalse(any("red gem" in event or "red_gem" in event or "secret_key" in event for event in engine.events))
        self.assertTrue(any("secret_key_to_vault" in detail for detail in engine.diagnostics))

    def test_ended_game_blocks_item_actions(self):
        engine = self.engine()
        engine.ended = True
        self.assertFalse(engine.equip(0))
        self.assertFalse(engine.use_item(6))
        self.assertFalse(engine.unequip("weapon"))
        self.assertEqual(engine.inventory[6], "gem_object")


if __name__ == "__main__":
    unittest.main()
