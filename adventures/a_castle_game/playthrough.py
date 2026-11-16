import sys,json,importlib.util,tkinter as tk
from pathlib import Path
from collections import deque
from tempfile import TemporaryDirectory
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from runner_engine import RunnerEngine,DIRECTIONS
spec=importlib.util.spec_from_file_location('bell_runner',ROOT/'tinker-runner.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
root=tk.Tk();root.withdraw()
e=RunnerEngine('a_castle_game')
r=m.TinkerRunner(root,e)
log=[]
original_log=r._append_log
r._append_log=lambda text:(log.append(text),original_log(text))
r.start_game()
def flush():
 r.engine=e
 r._after_action()
 root.update_idletasks()
 assert not e.ended or e.end_result=='win','Player died during walkthrough'
def fight():
 # The normal attack action targets a visible enemy in a cardinal line.
 for obj in list(e.current_area.objects):
  if e._enemy_definition(obj) is None:continue
  dx=obj.x-e.player_x;dy=obj.y-e.player_y
  if dx and dy:continue
  dist=abs(dx)+abs(dy)
  direction=next((name for name,(x,y) in DIRECTIONS.items() if (x==(1 if dx>0 else -1 if dx<0 else 0) and y==(1 if dy>0 else -1 if dy<0 else 0))),None)
  if not direction:continue
  weapon=e.attack_weapon()[0];limit=e._item_definition(weapon)['attack_range'] if weapon and e._item_definition(weapon)['ranged'] else 1
  if dist>limit:continue
  # Do not spend shots through walls or another object.
  vx,vy=DIRECTIONS[direction]
  if any(not e._position_is_open(e.current_area,e.player_x+vx*i,e.player_y+vy*i) for i in range(1,dist)):continue
  if weapon and e._item_definition(weapon)['ranged'] and e.energy<e._item_definition(weapon)['energy_cost']:
   e.equip(e.inventory.index('sword_object'))
  if e.facing!=direction:
   e.move(direction);flush();return True
  e.attack();flush();return True
 return False

def walk(x,y,expected=None,combat=True):
 source=e.current_area_filename
 for attempt in range(400):
  if e.ended:return
  if e.current_area_filename!=source:
   assert expected==e.current_area_filename,(source,expected,e.current_area_filename)
   flush();return
  if (e.player_x,e.player_y)==(x,y):flush();return
  if combat and fight():continue
  start=(e.player_x,e.player_y);q=deque([(start,[])]);visited={start};route=None
  portals={(t.x,t.y) for t in e.current_area.triggers if t.trigger_type=='teleport'}
  while q:
   point,path=q.popleft()
   if point==(x,y):route=path;break
   for direction,(dx,dy) in DIRECTIONS.items():
    nxt=(point[0]+dx,point[1]+dy)
    if nxt in visited or (nxt in portals and nxt!=(x,y)):continue
    if e._position_is_open(e.current_area,*nxt):
     visited.add(nxt);q.append((nxt,path+[direction]))
  if not route:
   if combat and fight():continue
   if any(e._enemy_definition(o) is not None and (o.x,o.y)==(x,y) for o in e.current_area.objects):
    e.wait();flush();continue
   raise AssertionError(('No route',source,start,(x,y)))
  e.move(route[0]);flush()
 raise AssertionError(('Walk timeout',source,x,y))

def equip(item):assert e.equip(e.inventory.index(item));flush()
def checkpoint(name):
 print(name,e.current_area_filename,(e.player_x,e.player_y),'health',e.health,'energy',e.energy,'inventory',[i for i in e.inventory if i],flush=True)
 flush()



def use_gems():
 for _ in range(8):
  if 'blue_gem_object' not in e.inventory:break
  if (e.health,e.energy)==(e.stats['max_health'],e.stats['max_energy']):break
  e.use_item(e.inventory.index('blue_gem_object'));flush()
def room(name):
 assert e.current_area_filename==name
walk(4,3);equip('sword_object');walk(5,3);equip('helmet_object')
walk(4,4);equip('torch_object');e.use_slot('light');flush()
walk(5,4);e.use_item(e.inventory.index('book_object'));flush()
walk(12,3);assert e.stats['gold']==15
walk(13,10);use_gems()
# Find and collect loot left by the moving exterior skeleton.
wand=next(o for o in e.current_area.objects if o.type=='magic_wand_object')
walk(wand.x,wand.y);assert 'magic_wand_object' in e.inventory
walk(9,8);checkpoint('Grounds explored, supplies and skeleton loot collected')
walk(19,14,'cave.json');walk(2,6);walk(3,6)
assert 'green_gem_object' in e.inventory and 'magic_wand_object' not in e.inventory
walk(0,0,'outside-map.json');walk(9,6,'great_hall.json');checkpoint('Old woman quest complete')
walk(2,10);walk(1,10);assert e.stats['gold']==10
walk(4,0,'fountain_room.json');walk(5,2);walk(4,1);use_gems();walk(1,1)
assert [(o.x,o.y) for o in e.current_area.objects if o.type=='fountain_object']==[(1,1)]
assert not any(o.type=='fountain_red_object' for o in e.current_area.objects)
walk(3,3,'great_hall.json');walk(5,12,'a_castle_dungeon.json')
# Fight and collect both type-level drops while retaining a free quest slot.
walk(6,4);use_gems()
for o in list(e.current_area.objects):
 if o.type in ('magic_wand_object','shield_object'):
  walk(o.x,o.y)
assert 'magic_wand_object' in e.inventory and 'shield_object' in e.inventory
assert e.stats['gold']==20
equip('shield_object');equip('magic_wand_object');checkpoint('Dungeon loot and attached bounty collected')
with TemporaryDirectory() as d:
 save=Path(d)/'castle.save.json';e.save_to_file(save,'Castle expedition')
 e=RunnerEngine.load_save(save,dialog_handler=r.show_dialog);r.engine=e;flush()
walk(3,9,'great_hall.json');walk(2,0,'gargoyle_room.json')
assert 'green_gem_object' not in e.inventory
assert e.current_area.tiles[0][2].type=='gray_brick_open_door'
walk(2,0,'a_castle_vault.json');walk(4,2);use_gems()
if 'red_gem_object' not in e.inventory:
 crown=next(o for o in e.current_area.objects if o.type=='red_gem_object')
 walk(crown.x,crown.y)
assert 'red_gem_object' in e.inventory
checkpoint('Dragon defeated; type-level crown loot collected')
walk(4,8,'gargoyle_room.json');walk(3,3,'great_hall.json');walk(3,2)
assert e.ended and e.end_result=='win'
checkpoint('Castle restored')
report=ROOT/'adventures/a_castle_game'
(report/'playthrough.txt').write_text('\n'.join(log)+'\n')
(report/'verification.json').write_text(json.dumps({'result':e.end_result,'turns':e.turn_count,'health':e.health,'funds':e.stats['gold'],'validation_issues':e.validation_issues,'diagnostics':e.diagnostics},indent=2)+'\n')
root.destroy()
