A CASTLE GAME — UPDATED NOVEMBER 15, 2026

Start a NEW run:
    python3 tinker-runner.py a_castle_game
Old saves contain snapshots of the previous version.

The five original maps and the old woman's scepter/gargoyle story remain.
Added Beneath the Castle and The Dragon's Vault to complete the quest.

FEATURES
- Explicit existing start at (3,3) in Castle Grounds; updated instructions.
- Sword, helmet, torch and readable journal beside the starting position.
- Equip weapons/armor through inventory; active light and quick-use slots.
- Moving, four-direction enemies with configured speed, health and damage.
- Reusable enemy-type loot: skeleton -> wand; orc -> shield; dragon -> red gem;
  spiders/blobs -> restorative blue gems; gargoyle type -> green gem.
  Every instance of the respective type shares its loot definition. Collect
  loot where the enemy actually dies. Full inventory leaves it on the map.
- A wand uses energy and attacks at range. Blue gems restore health and energy.
- Paired one-charge walk-on pickups, plus quest inventory removals/additions.
- Funds: road purse, optional castle donation, enemy-attached armory bounty.
- Two-charge energy runestone, unlimited health spring, swamp health damage.
- One-charge lever removes the red fountain and adds a clear healing spring.
- Green-token offering opens the gargoyle's doorway using Tile Update.
- Enemy-attached Funds/Message triggers on the armory orc supplement its type loot.
- Save/load, dropping/recovering items and death/restart use the current runner.
- Crown return gives an explicit win ending.

REPAIRS
The old fountain lever had an out-of-bounds target. The spring chamber and
castle hall lacked usable return routes. Doors now have explicit walkability.
All authored triggers use Charges: 0 unlimited, 1 one use, shrine 2 uses.
Embedded enemy definitions are synchronized with the game-wide definitions.

SPOILER ROUTE
Gather and equip supplies. Explore the grounds and defeat the skeleton for a
wand. Take it to the old woman in the southeast cave; receive a green token.
Inside the castle, the west candle offering is optional. The northeast room's
lever restores the spring; its western runestone recharges energy twice.
The southeast hall stairs lead to the armory dungeon: recover another wand
and a shield from enemies. The northwest room's gargoyle accepts the token;
its new doorway leads to the dragon. Collect the dragon's red gem and return
it to the throne in the great hall.

VERIFICATION
A scripted native runner playthrough completed the quest using normal travel,
movement/facing, combat, equipment and inventory. It also saved/reloaded midway.
See playthrough.txt and verification.json. All 238 automated tests pass, and
runner --check reports no errors. No other game's area references overlap the
updated original maps. Existing saves were not modified.

KNOWN RUNNER BEHAVIOR
Story dialogue can precede queued action reports. Approaching the empty throne
before obtaining the crown gives the generic missing-item message and records
that expected failed condition in Diagnostics. A finite energy shrine spends a
charge even when already full; save its two uses for when you need them.
These engine behaviors were not changed as part of updating this adventure.
