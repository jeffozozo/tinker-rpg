"""Shared item defaults, equipment compatibility, and editor/runtime validation."""

ITEM_TYPES = ("object", "weapon", "armor", "consumable", "toggle", "readable", "openable")
EQUIPMENT_SLOTS = ("weapon", "head", "offhand", "light", "quick")
SLOT_LABELS = ("Weapon", "Head", "Off hand", "Light", "Quick item")


def item_defaults(name):
    defaults = dict(
        item_type="object", weapon_damage=0, equipment_slot="quick",
        armor_bonus=0, ranged=False, attack_range=6, energy_cost=0,
        ammo_item="", read_text="", gettable=False,
    )
    examples = {
        "sword_object": dict(item_type="weapon", weapon_damage=4, equipment_slot="weapon"),
        "magic_wand_object": dict(item_type="weapon", weapon_damage=5, equipment_slot="weapon", ranged=True),
        "helmet_object": dict(item_type="armor", armor_bonus=2, equipment_slot="head"),
        "shield_object": dict(item_type="armor", armor_bonus=2, equipment_slot="offhand"),
        "torch_object": dict(item_type="toggle", equipment_slot="light"),
        "book_object": dict(item_type="readable", read_text="The pages of this old book are blank."),
    }
    if name in examples:
        defaults.update(examples[name], gettable=True)
    return defaults


def compatible_slot(definition):
    kind = definition["item_type"]
    if kind == "weapon":
        return "weapon"
    if kind == "armor":
        return definition.get("equipment_slot", "head")
    if kind == "toggle":
        return "light"
    if kind in ("consumable", "readable"):
        return "quick"
    return None


def validate_item(definition):
    if definition.get("item_type", "object") not in ITEM_TYPES:
        raise ValueError("Choose a valid item type.")
    for key in ("weapon_damage", "armor_bonus", "energy_cost"):
        value = definition.get(key, 0)
        if type(value) is not int or value < 0:
            raise ValueError(f"{key} must be a non-negative whole number.")
    if type(definition.get("attack_range", 6)) is not int or definition.get("attack_range", 6) < 1:
        raise ValueError("Attack range must be a positive whole number.")
    if type(definition.get("ranged", False)) is not bool:
        raise ValueError("Ranged must be true or false.")
    if definition.get("item_type") == "armor" and definition.get("equipment_slot", "head") not in ("head", "offhand"):
        raise ValueError("Armor belongs in the head or offhand slot.")
    for key in ("ammo_item", "read_text"):
        if not isinstance(definition.get(key, ""), str):
            raise ValueError(f"{key} must be text.")
    effects = definition.get("effects", {})
    if not isinstance(effects, dict) or any(type(value) is not int for value in effects.values()):
        raise ValueError("Item effects must be whole numbers.")
