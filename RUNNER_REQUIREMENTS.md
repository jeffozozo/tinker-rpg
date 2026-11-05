# Tinker Runner Requirements

## 1. Purpose

`tinker-runner.py` runs a game created with Tinker Editor so the author can play
it, validate maps and triggers, and discover missing editor features. The first
release should be a small, reliable, turn-based RPG runtime rather than a
general-purpose scripting engine.

## 2. Scope and delivery phases

### Phase 1: First playable runner

- Load and validate a game and its areas.
- Show the intro message, then place the player at the configured start location.
- Render the current area, player, persistent status panel, and message/status log.
- Support walking, collision, area transitions, an eight-slot inventory, and
  the existing trigger types.
- Provide editor controls for the start area and position, player icon, starting
  stats, and starting inventory.
- Keep enemies stationary and blocking for now. Enemy turns and combat are out
  of scope until the editor can configure the required combat rules.

### Phase 2: RPG systems

- Add enemy movement and combat, weapons, ranged attacks/spells, treasure,
  equipment, and combat balancing.
- Add branching choices and conditional/action sequences for shops, doors,
  quests, and similar interactions.
- Add player progression and additional stats if a game needs them.

Keep the game data format backward-compatible: games without the new settings
should load in the editor, and the runner should explain which required settings
are missing.

## 3. Launching and loading

### Command line

```text
python tinker-runner.py <game_name_or_path>
python tinker-runner.py --check <game_name_or_path>
```

- Accept a path to a game JSON file, or a game name / filename stem.
- For a name, search the current working directory first, then the project's
  `games/` directory. Accept names with or without `.json`.
- If no match exists, report the attempted locations and exit with a nonzero
  status. If multiple matches make the name ambiguous, report the matches and
  ask the user to pass a path; do not silently choose one.
- `--check` loads and validates the game, areas, trigger references, and
  referenced images, reports all detected issues, and exits without opening a
  game window. Return a nonzero status if validation fails.
- Resolve each game area by its stored filename, relative to the project's
  `areas/` directory for project games. For an explicitly supplied game path
  outside the project, first look for an `areas/` directory beside that game,
  then use the project's `areas/` directory for compatibility with portable
  area files.
- Validate all referenced files and report missing or malformed game/area data
  before starting. Never replace a missing area with an empty map.

### Startup sequence

1. Load and validate game and area data.
2. Show `intro_message` if non-empty.
3. Show `instructions_message` on request (and optionally after the intro).
4. Place the player at the configured start area and coordinates.
5. Start accepting player input.
- Initially size the window so the configured start map is visible in full when
  it fits on the screen. If it does not fit, use the available screen space and
  keep the map scrollable.
- Center the rendered area within the map viewport when the area is smaller
  than the viewport, including after the window is resized.

If start settings are incomplete or the start location is blocked/out of bounds,
show an actionable error naming the setting to fix in the editor.

## 4. Editor data required

Store new game-level settings in the existing `Game.properties` dictionary (or
promote them to typed `Game` fields if the editor needs stronger validation).
Use filenames as area references, matching the current `Game.areas` format.

Suggested initial shape:

```json
{
  "properties": {
    "start_area": "great_hall.json",
    "start_x": 3,
    "start_y": 5,
    "player": {
      "sprite": "fighter_npc",
      "stats": {
        "max_health": 20,
        "starting_health": 20,
        "max_energy": 0,
        "starting_energy": 0,
        "strength": 1,
        "intelligence": 1,
        "gold": 0
      },
      "starting_inventory": ["key_object", "", "", "", "", "", "", ""]
    }
  }
}
```

Editor requirements:

- For teleport triggers, the coordinate picker displays the selected destination
  area while coordinates are chosen, then returns to the area being edited.
  Selecting the current area as the destination is valid.
- Add a **Player** mode to the left-side mode selector. In that mode, choose a
  player sprite and click the map to place the player marker and set the game's
  start X/Y. Clicking another location moves the single player marker.
- Treat the marker as game-level start-position data, not an area object or
  terrain tile. Display it over the existing map without changing the tile,
  objects, or triggers beneath it.
- Let the author choose a start area from the areas belonging to the game.
- Let the author also set start X/Y numerically. Validate bounds and walkability
  and visibly mark the start location in the editor.
- Let the author choose a player sprite from available 32x32 NPC art (or a
  dedicated player-art directory). Clearly distinguish the chosen player sprite
  from ordinary NPC/enemy instances.
- Let the author configure starting health and energy, their maximums, strength,
  intelligence, starting `$`, and starting inventory. Show eight item dropdowns
  in Player mode on the left side; each slot may be empty or contain one object
  marked Gettable in Objects mode. Allow duplicate item types in different
  slots. Save the selected object IDs in `player.starting_inventory`,
  preserving empty slots and slot order.
  Require positive max health and starting values within their maximums; make
  energy optional/zero by default. Keep the saved stat key as `gold` for
  compatibility.
- Save settings in the game JSON and preserve them when opening and saving older
  games. Sensible defaults should be visible in the editor.
- Add an **Enemies** mode with a reusable enemy-definition list on the left and
  selected-definition fields on the right. Each definition has a name, live
  sprite, health, movement speed in tiles per turn (including fractional values
  and zero), and a ranged-attack type (none, flame, lightning, or gun).
- Seed new games with starter definitions for Gargoyle, Orc, Dragon, Spider,
  Skeleton, and Black Blob so they appear immediately in the enemy palette. The
  editor must not overwrite an existing definition when adding missing examples
  to a game.
- Let the author place multiple instances of a selected enemy in an area.
  Store an enemy ID and a copy of its definition with each instance so area
  files remain portable; when a definition changes, synchronize linked
  instances across every saved game area and the currently open area.
- Keep enemy editor UI and definition logic in a dedicated module rather than
  adding enemy-specific fields and workflows to the main editor module.

## 5. Runtime display and controls

- Use the existing Tkinter/Pillow stack and the editor's 32x32 tile/art format.
- Provide a top-level **Game** menu with Save, Load, Restart, and Quit commands;
  a **Player** menu with Inventory; and a **Help** menu with Instructions.
- Restart reloads the authored game from its beginning, clears the current
  playthrough's save association, and confirms before discarding unsaved progress.
- Keep health, energy (if enabled), `$`, and current area visible at all times.
- Provide a message/status log for trigger text, combat results, item pickup,
  errors, instructions, and turn feedback. Display game messages and
  notifications in this log rather than opening message pop-up windows.
  Important messages must not disappear immediately.
- `W`, `A`, `S`, `D` and the arrow keys move one tile in the four cardinal
  directions. Ignore key case.
- `I` opens/closes inventory. Show all eight slots, including empty slots;
  repeated item IDs occupy separate slots.
- `Space` interacts with the current tile or nearby interactable. It should not
  have an undefined or generic action: allow pickup of gettable objects in the
  current or an adjacent tile, and give feedback when nothing can be interacted
  with or the inventory is full.
- `Q` requests quit. If a run has unsaved/persistent progress, confirm before
  discarding it.
- Provide **Save Game** and **Load Game** controls. Save files are separate from
  the authored game and area files, use a project `saves/` directory, and
  prompt for a file on every save and load. Save files have a user-chosen name
  and preserve the current player stats/position/inventory plus runtime changes
  to every loaded area. Loading restores that playthrough without replaying its
  start tile triggers.
- `?` or `H` opens the game's instructions.
- A valid movement or completed action consumes a turn; inventory viewing,
  invalid movement, and opening help do not.

## 6. Movement, map, and area transitions

- Draw tiles from their asset names and apply per-tile `walkable_override` before
  the tile manager's default walkability.
- Block movement beyond map bounds, into blocked tiles, and into blocking
  objects/enemies. Show a short reason when appropriate.
- Treat objects as walkable/blocking according to their game object definition
  and per-instance properties. Preserve editor-defined behavior.
- Run a tile-entry trigger after a successful move. Resolve trigger ordering
  deterministically (the editor's saved order) and stop processing if an action
  ends the game or relocates the player.
- Teleport triggers move to a game area and coordinate only if the destination
  exists and is valid. Prevent repeated immediate re-entry loops; report invalid
  destinations rather than crashing.
- The initial runner should load the area's saved tile/object/trigger state.
  Whether tile updates and spawned objects persist after leaving and returning
  must be deterministic for a run; recommended default is to keep runtime
  changes in memory for the duration of that run.
- A new game begins with triggers on the start tile. Entering a tile runs its
  triggers in saved order. If a trigger teleports the player, stop processing
  triggers at the old location, then process the arrival tile. Stop and report
  if teleport triggers cycle repeatedly.

## 7. Triggers and interaction model

The editor currently has `teleport`, `inventory`, `tile_update`, `area_object`,
`game_end`, `show_message`, and `custom` trigger types. The runner must define
their runtime behavior, validate parameters, and give readable feedback for
invalid actions. The `show_dialog` legacy alias should behave as `show_message`.

- `show_message`: display the configured message and wait for acknowledgement.
- `inventory`: remove the first matching item and add to the first empty slot.
  If removal fails or the inventory is full, report it and apply neither change.
- `tile_update`: change a valid tile in the current area; preserve the configured
  walkability setting.
- `area_object`: add a valid object to a valid area without creating duplicates
  unless explicitly allowed. The current trigger coordinates are the spawn
  coordinates because the existing editor does not store separate spawn
  coordinates.
- `teleport`: change area and position as described above.
- `game_end`: display the result/message, show a clear win/loss status, and stop
  accepting gameplay input.
- `custom`: do not execute arbitrary Python in the first runner release. Mark it
  unsupported with a clear runtime message until a deliberately constrained and
  safe scripting model is designed.

### Choice, conditions, and action sequences

Current triggers do not provide yes/no choices, conditional branches, or an
ordered transaction. Add a structured interaction/action model rather than
trying to build a shop from separate overlapping triggers. It should support:

- A player-facing prompt with labeled choices, such as **Buy for $10?**
- Conditions such as `gold >= 10` and `inventory does not contain item`.
- Ordered actions such as subtract gold, add item, update a tile, or show a
  message.
- A decline branch with its own actions, such as moving the player back to the
  tile they came from.
- Atomic execution: validate every condition/action first; apply all actions or
  none. Never charge the player if granting the item fails.
- A deterministic once/repeat policy so a player cannot accidentally buy the
  same one-time treasure repeatedly.

Recommended editor concept: an interactable (merchant, chest, sign, door) with
one or more **interactions**, each containing a prompt/condition and explicit
success and decline action lists. Store this as structured JSON, not executable
code. Trigger-on-enter can remain for automatic events; `Space` handles explicit
interactions.

### Merchant example

The desired merchant flow should be represented as one interaction:

1. Player presses `Space` while adjacent to/in front of the merchant.
2. Runner displays `Buy <item> for $10?` with Yes/No choices.
3. Yes checks that the player has at least $10 and can receive the item.
4. If checks pass, subtract $10 and add the item as one atomic result.
5. If checks fail, make no changes and report insufficient funds or inventory
   capacity.
6. No leaves inventory/`$` unchanged and moves the player back only if the
   interaction explicitly requests it and the destination is legal. Prefer
   leaving the player in place by default; forced movement on declining should
   be an explicit editor-authored action.

This avoids relying on the player to step onto a sequence of trigger tiles and
avoids a race where one trigger charges but another fails to grant the item.

## 8. Inventory, items, and player stats

- Inventory is game state, not just a list of decorative objects. In the first
  runner, each of the eight slots holds one object ID or is empty; duplicate IDs
  occupy separate slots. An inventory trigger removes the first matching item
  and adds an item to the first empty slot. Validate both changes before
  applying either so a failed trigger has no partial effect.
- Currency is displayed with a `$` prefix in player-facing UI and messages. Keep
  the numeric `gold` stat in game data; it may be implemented as a dedicated
  stat rather than a normal inventory item. Do not allow it to go negative.
- Define item types before adding editor controls: at minimum, key/quest item,
  consumable, equipment, and treasure/currency. Items need display name,
  description, stackability, and optional use/equipment effects.
- Enforce health in `0..max_health`; reaching zero ends the run as a loss.
- Energy in `0..max_energy` is optional and used by spells/ranged attacks. Games
  with no energy should not display a confusing empty meter.
- Strength and intelligence should not affect outcomes until their combat/spell
  formulas are documented and testable. Keep them as displayed data in the
  initial runner if no mechanics are ready.
- Starting inventory entries and runtime inventory triggers use the same object
  IDs. Stacking, item categories, and equipment remain future work.

## 9. Enemies and combat

The editor's initial enemy definitions/instances provide a display name, live
sprite, health, movement speed, and ranged-attack type. Defeated enemies
disappear. The first runner displays enemies as stationary blocking objects and
does not attack or move them. Before combat behavior ships, define attack
damage, defense/armor, aggro/attack range, movement behavior, and optional
drops/experience. Keep enemy instances separate from ordinary decorative NPCs.

Recommended first combat rules:

- A melee weapon attacks an adjacent enemy in the chosen cardinal direction;
  never attack merely because any weapon is somewhere in inventory.
- Provide an explicit equipped weapon slot, with a default unarmed attack if
  desired. The editor/runtime must make the chosen weapon visible.
- A ranged weapon or spell enters targeting mode. The player chooses a cardinal
  direction with arrow keys/WASD; show the target/line before confirming.
- Define line-of-sight, range, energy/ammo cost, damage, armor reduction, and
  valid targets. Invalid/cancelled targeting does not consume a turn or resource.
- Damage and healing are bounded; defeated enemies disappear and stop blocking
  movement. Loot and other death effects can be added in a later phase.
- After each successful player turn, living hostile enemies act in a stable,
  documented order. They may move toward the player within their configured
  behavior or attack when in range. Invalid/blocked enemy movement does nothing.
- Player death immediately ends the game with the configured loss message.
- Avoid random outcomes in the first combat tests; inject/seed randomness so
  scenarios are reproducible.

## 10. Validation, errors, and testing

- Validate JSON shape, area dimensions, tile matrix dimensions, object/trigger
  coordinates, start location, references, and action parameters.
- Report file path and field/area/trigger name for load or validation errors.
- Never silently skip a broken trigger, missing image, or missing area. Continue
  only when safe, with a visible warning identifying what was skipped.
- Unit tests should cover game/path resolution, legacy game loading, start
  validation, collision, all trigger types, turn consumption, inventory
  transactions, area transitions, and win/loss.
- Integration tests should launch a sample game and exercise movement, an area
  transition, and trigger-driven messages and state changes.
- Add a small sample game configured for the runner so new runtime/editor work
  can be checked manually.

## 11. Deferred decisions

- Shop decline behavior and structured purchase interactions are deferred with
  shops.
- Enemy movement and combat are deferred. Until then, enemies remain stationary
  and block movement.
- Item categories, stacking, equipment, and use effects are deferred. The first
  runner uses one object ID per inventory slot.
