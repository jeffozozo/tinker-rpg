LANTERN VALE: THE BELL OF DAWN
Built from scratch on November 13, 2026.

The previous Crimson Spring adventure has been replaced. This is a new game
with new maps, dialogue, enemy definitions, item configuration and trigger data.
Your other games and areas were left alone. Old saved runs contain snapshots
of the old adventure; start a NEW GAME to play this version.

PLAY
From the tinker-rpg directory:
    python3 tinker-runner.py lantern_vale
Or open games/lantern_vale.json in the editor and use its runner command.

Start with empty hands in Dawnmere. Walk north to speak with Mara and gather
supplies on the village road. The instructions and keeper's book explain the
controls. Walk onto trigger positions to interact; there is no Space command.

Six areas: Dawnmere, Lantern Vale, Briarford, Listening Grove, Dawnbell Castle,
and Silent Belfry. Two enemy-defeat rewards gate the main quest. Features used
include equipment, readable items, toggle lights, ranged weapons, consumables,
paired pickups, funds additions/removals, stat changes, finite and unlimited
charges, scenery changes, tile changes, travel, save/load, and a win ending.
The optional castle donation demonstrates removing funds without a shop.

TESTING
A scripted complete playthrough used the real native runner and engine actions,
rendering each action. It used ordinary movement, combat, inventory, and portals
without teleporting the player to skip the quest. It won in the turn count
recorded in playthrough_result.json. The log is in playthrough.txt (spoilers).
Separate targeted checks deliberately positioned fresh game snapshots to test
failure and recovery cases. These include full inventory, pending enemy rewards,
charge exhaustion, missing quest items, insufficient money, inventory keyboard
isolation, save/load, and both death-prompt choices. See verification.json.
The game validator reports no errors; all 233 automated tests passed.
This was automated native UI verification, not a manual keyboard playthrough.

REVIEW
ISSUES.txt contains four observations for discussion. No engine fixes were made
during this rebuild. The door problem has a per-tile adventure workaround.
WALKTHROUGH.txt and map_overview.png contain spoilers.

REPRODUCTION TOOLS
The tools/ directory retains the authoring, native playthrough, verification,
and overview-rendering scripts. Run them from this project's Python environment.
Authoring opens a hidden Tk editor and replaces only this adventure's game/area
files and generated verification outputs. It does not remove other games or saves.
