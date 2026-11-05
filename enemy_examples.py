"""Reusable starter enemy definitions for new game projects."""


def example_enemy_definitions():
    return {
        "example:gargoyle": {
            "id": "example:gargoyle",
            "name": "Gargoyle",
            "sprite": "gargoyle_npc",
            "health": 24,
            "movement_speed": 0.5,
            "ranged_attack": "none",
        },
        "example:orc": {
            "id": "example:orc",
            "name": "Orc",
            "sprite": "orc_npc",
            "health": 16,
            "movement_speed": 1.0,
            "ranged_attack": "none",
        },
        "example:dragon": {
            "id": "example:dragon",
            "name": "Dragon",
            "sprite": "dragon_npc",
            "health": 50,
            "movement_speed": 0.5,
            "ranged_attack": "flame",
        },
        "example:spider": {
            "id": "example:spider",
            "name": "Spider",
            "sprite": "spider_npc",
            "health": 8,
            "movement_speed": 1.5,
            "ranged_attack": "none",
        },
        "example:skeleton": {
            "id": "example:skeleton",
            "name": "Skeleton",
            "sprite": "skeleton_npc",
            "health": 12,
            "movement_speed": 1.0,
            "ranged_attack": "none",
        },
        "example:black_blob": {
            "id": "example:black_blob",
            "name": "Black Blob",
            "sprite": "black_blob_npc",
            "health": 10,
            "movement_speed": 0.75,
            "ranged_attack": "none",
        },
    }
