import sys,json,importlib.util,tkinter as tk
from pathlib import Path
from collections import deque
from tempfile import TemporaryDirectory
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from runner_engine import RunnerEngine,DIRECTIONS
spec=importlib.util.spec_from_file_location('bell_runner',ROOT/'tinker-runner.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
root=tk.Tk();root.withdraw()
e=RunnerEngine('lantern_vale')
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
   raise AssertionError(('No route',source,start,(x,y)))
  e.move(route[0]);flush()
 raise AssertionError(('Walk timeout',source,x,y))

def equip(item):assert e.equip(e.inventory.index(item));flush()
def checkpoint(name):
 print(name,e.current_area_filename,(e.player_x,e.player_y),'health',e.health,'energy',e.energy,'inventory',[i for i in e.inventory if i],flush=True)
 flush()


walk(6,3);walk(3,5);equip('sword_object');walk(4,5);e.use_item(e.inventory.index('book_object'));flush()
walk(8,5);equip('torch_object');e.use_slot('light');flush()
# Drop a readable item, walk away, and recover it through generated triggers.
walk(7,6);assert e.drop_item(e.inventory.index('book_object'));flush()
walk(8,6);walk(7,6);assert 'book_object' in e.inventory
walk(6,10,'lv_vale.json');checkpoint('Dawnmere complete')
walk(13,8,'lv_briarford.json');walk(3,6);equip('helmet_object');walk(4,6);equip('shield_object')
walk(8,6);equip('magic_wand_object');walk(9,6);walk(9,3);walk(2,4)
assert e.stats['gold']==12
# Spend energy using the normal attack action, then test the two-charge shrine.
e.attack();flush();walk(10,4);assert e.energy==10
walk(10,5);e.attack();flush();walk(10,4);assert e.energy==10
walk(10,5);e.attack();flush();walk(10,4);assert e.energy==9
assert not any(t.name=='two_recharges' for t in e.current_area.triggers)
checkpoint('Two finite charges exhausted without becoming unlimited')
walk(6,10,'lv_vale.json');walk(5,2,'lv_grove.json')
walk(2,8);walk(9,8);before=e.health;walk(10,8);assert e.health==before-4
# Use restoration item to free a slot before the enemy reward.
e.use_item(e.inventory.index('blue_gem_object'));flush()
walk(6,4)
if 'green_gem_object' not in e.inventory:
 loot=next(o for o in e.current_area.objects if o.type=='green_gem_object');walk(loot.x,loot.y)
assert 'green_gem_object' in e.inventory
assert not any(e._enemy_definition(o) for o in e.current_area.objects)
checkpoint('Guardian defeated and seal loot collected')
walk(6,10,'lv_vale.json');walk(12,2,'lv_castle.json')
walk(5,11);walk(5,10);assert e.stats['gold']==7
walk(7,8);assert 'green_gem_object' not in e.inventory
walk(7,7);assert e.current_area.tiles[7][7].type=='gray_brick_open_door'
walk(3,6);walk(4,5);assert 'blue_gem_object' in e.inventory
with TemporaryDirectory() as directory:
 save=Path(directory)/'bell.save.json';e.save_to_file(save,'Belfry expedition')
 old=(e.health,e.energy,e.stats['gold'],dict(e.equipment),set(e.active_items))
 e=RunnerEngine.load_save(save,dialog_handler=r.show_dialog);r.engine=e
 assert old==(e.health,e.energy,e.stats['gold'],dict(e.equipment),set(e.active_items))
 assert not any(t.name=='two_recharges' for a in e.areas.values() for t in a.triggers)
 flush()
checkpoint('Castle unlocked and save restored')
walk(11,2,'lv_vault.json');walk(5,11)
# Restore spent energy before the boss battle.
e.use_item(e.inventory.index('blue_gem_object'));flush()
walk(5,4)
if 'red_gem_object' not in e.inventory:
 loot=next(o for o in e.current_area.objects if o.type=='red_gem_object');walk(loot.x,loot.y)
assert 'red_gem_object' in e.inventory
assert not any(e._enemy_definition(o) for o in e.current_area.objects)
checkpoint('The Hush defeated and heart loot collected')
walk(5,12,'lv_castle.json');walk(3,2)
assert e.ended and e.end_result=='win'
assert any(o.type=='fountain_object' and (o.x,o.y)==(3,3) for o in e.current_area.objects)
assert not any(o.type=='fountain_red_object' for o in e.current_area.objects)
checkpoint('The dawn bell rings')
report=ROOT/'adventures/lantern_vale'
(report/'playthrough.txt').write_text('\n'.join(log)+'\n')
(report/'playthrough_result.json').write_text(json.dumps({'result':e.end_result,'turns':e.turn_count,'health_remaining':e.health,'energy_remaining':e.energy,'funds':e.stats['gold'],'validation_issues':e.validation_issues,'diagnostics':e.diagnostics},indent=2)+'\n')
root.destroy()
