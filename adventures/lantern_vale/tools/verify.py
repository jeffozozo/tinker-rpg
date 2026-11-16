import sys,json,importlib.util,tkinter as tk
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from runner_engine import RunnerEngine
from data_classes import trigger_charges
spec=importlib.util.spec_from_file_location('verify_runner',ROOT/'tinker-runner.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
checks={};findings={}
def fresh(area,x,y):
 e=RunnerEngine('lantern_vale');e._teleport({'area':area,'x':x,'y':y});e.events.clear();return e
# Isolated checks deliberately position fresh snapshots. The main walkthrough uses normal travel.
e=fresh('lv_castle',5,11);e.move('up')
checks['insufficient_funds_preserves_charge_and_money']=e.stats['gold']==0 and any(t.name=='castle_donation' and trigger_charges(t.parameters)==1 for t in e.current_area.triggers) and any('only $0' in v for v in e.events)
e=fresh('lv_castle',7,8);e.process_entry_triggers()
checks['missing_seal_keeps_gate_closed']=e.current_area.tiles[7][7].type=='gray_brick_wall'
e=fresh('lv_briarford',10,5);e.move('up')
t=next(t for t in e.current_area.triggers if t.name=='two_recharges')
findings['full_energy_spends_finite_charge']={'energy':e.energy,'remaining_charges':trigger_charges(t.parameters),'energy_restored':any('regain' in s for s in e.events)}
assert trigger_charges(t.parameters)==1 and e.energy==10
# Full inventory while defeating an enemy: reward persists through save, then retry.
e=fresh('lv_grove',6,8);e.inventory=['sword_object']+['rock_object']*7;e.equip(0)
for _ in range(6):e.wait()
corpse=next((o.x,o.y) for o in e.current_area.objects if e._enemy_definition(o))
findings['moved_enemy_reward']={'defeated_at':corpse,'retry_at':[6,4]}
for i in range(10):
 if not any(e._enemy_definition(o) for o in e.current_area.objects):break
 e.attack('up')
assert not any(e._enemy_definition(o) for o in e.current_area.objects)
pending=[t for t in e.current_area.triggers if t.enemy_pending]
checks['full_inventory_enemy_reward_is_pending']=len(pending)==2 and 'green_gem_object' not in e.inventory
findings['reward_retry_message']=' | '.join(e.events[-3:])
with TemporaryDirectory() as d:
 p=Path(d)/'pending.save.json';e.save_to_file(p,'Pending reward');e=RunnerEngine.load_save(p)
 assert len([t for t in e.current_area.triggers if t.enemy_pending])==2
 # Drop on a clear tile; the reward remains at its original authored position.
 e.move('left');assert e.drop_item(1)
 e.move('right')
 while e.player_y>4:e.move('up')
 assert 'green_gem_object' in e.inventory
checks['pending_reward_survives_save_and_can_be_recovered']=True
# Native runner keyboard, modal inventory, death prompt and fresh restart.
root=tk.Tk();root.withdraw()
try:
 e=RunnerEngine('lantern_vale');r=m.TinkerRunner(root,e);r.start_game()
 r.toggle_inventory();turn=e.turn_count;xy=(e.player_x,e.player_y)
 r.on_key_press(SimpleNamespace(keysym='Right',widget=r.canvas))
 checks['inventory_blocks_background_movement']=e.turn_count==turn and xy==(e.player_x,e.player_y) and r.inventory_window.grab_current() is r.inventory_window
 r.close_inventory();r.on_key_press(SimpleNamespace(keysym='space',widget=r.canvas))
 checks['space_does_not_advance_turn']=e.turn_count==turn
 e._teleport({'area':'lv_grove','x':6,'y':5});e.health=1
 with patch.object(m.messagebox,'askyesno',return_value=False) as prompt:
  r.on_key_press(SimpleNamespace(keysym='period',widget=r.canvas))
  assert e.ended and e.health==0
  r._after_action();checks['death_decline_prompts_once_and_blocks_play']=prompt.call_count==1
  n=e.turn_count;r.on_key_press(SimpleNamespace(keysym='Right',widget=r.canvas));assert e.turn_count==n
 # A separate dying run verifies Yes invokes a fresh engine, not a saved snapshot.
 e=fresh('lv_grove',6,5);e.health=1;r.engine=e;r.dirty=True
 with patch.object(m.messagebox,'askyesno',return_value=True) as prompt:
  r.on_key_press(SimpleNamespace(keysym='period',widget=r.canvas))
  checks['death_restart_starts_fresh_without_second_prompt']=prompt.call_count==1 and r.engine is not e and r.engine.health==32 and r.engine.current_area_filename=='lv_dawnmere.json' and r.save_path is None
 root.update_idletasks()
finally:root.destroy()
assert all(checks.values()),checks
(ROOT/'adventures/lantern_vale/verification.json').write_text(json.dumps({'checks':checks,'observations':findings},indent=2)+'\n')
print(json.dumps(checks,indent=2))
print(json.dumps(findings,indent=2))
