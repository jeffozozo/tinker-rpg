import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
import tkinter as tk
import importlib.util
from unittest.mock import patch
from data_classes import Area
from item_rules import item_defaults
from copy import deepcopy
spec=importlib.util.spec_from_file_location('adventure_editor',ROOT/'tinker-edit.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
root=tk.Tk();root.withdraw()
errors=[];infos=[]
patches=[patch.object(m.TinkerEditor,'show_startup_message'),patch('tkinter.messagebox.showinfo',side_effect=lambda *a,**k:infos.append(a)),patch('tkinter.messagebox.showerror',side_effect=lambda *a,**k:errors.append(a)),patch('tkinter.messagebox.askyesno',return_value=True)]
for p in patches:p.start()
e=m.TinkerEditor(root);e.new_game();e.game_name_var.set('Lantern Vale: The Bell of Dawn')
# Use the real editor's form save paths, with rendering batched during layout.
real_draw=e.draw_area;real_details=e.update_properties_display
real_refresh=e.refresh_trigger_editor
e.draw_area=lambda:None;e.update_properties_display=lambda:None

# The user requested replacing the original adventure; limit deletion to its files.
for p in [ROOT/'games/lantern_vale.json', *[ROOT/'areas'/name for name in ('lv_vale.json','lv_dawnmere.json','lv_briarford.json','lv_grove.json','lv_castle.json','lv_vault.json')]]:
 p.unlink(missing_ok=True)
report=ROOT/'adventures/lantern_vale'
report.mkdir(parents=True,exist_ok=True)
for name in ('map_overview.png','playthrough.txt','playthrough_result.json','verification.json'):
 (report/name).unlink(missing_ok=True)
areas=[('lv_vale.json','Lantern Vale',17,13),('lv_dawnmere.json','Dawnmere Village',13,11),('lv_briarford.json','Briarford Village',13,11),('lv_grove.json','The Listening Grove',13,11),('lv_castle.json','Dawnbell Castle',15,13),('lv_vault.json','The Silent Belfry',11,13)]
e.current_game.areas=[a[0] for a in areas]
for filename,name,w,h in areas:
 e.current_area=Area();e.cursor_x=e.cursor_y=0;e.selected_mode='tile'
 e.resize_canvas(w,h);e.area_name_var.set(name);e.selected_tile='grass';e.fill_empty_tiles()
 assert e._save_area_to_file(str(ROOT/'areas'/filename),show_message=False)
def item(name,kind,**values):
 e.selected_mode='object';e.selected_tile=name;e.load_object_definition_editor()
 e.object_item_type_var.set(kind);e.on_object_item_type_change()
 e.object_gettable_var.set(kind not in ('object','openable'))
 e.object_walkable_var.set(values.pop('walkable',True))
 e.object_weapon_damage_var.set(str(values.pop('weapon_damage',0)))
 effects=values.pop('effects',{})
 for key,var in e.object_effect_vars.items():var.set(str(effects.get(key,0)))
 for key,value in values.items():
  if key in e.item_detail_vars:e.item_detail_vars[key].set(('yes' if value else 'no') if key=='ranged' else str(value))
 assert e.save_object_definition_changes(),(name,errors)


item('sword_object','weapon',weapon_damage=4)
item('magic_wand_object','weapon',weapon_damage=5,ranged=True,attack_range=5,energy_cost=1)
item('helmet_object','armor',armor_bonus=1,equipment_slot='head')
item('shield_object','armor',armor_bonus=1,equipment_slot='offhand')
item('torch_object','toggle')
item('book_object','readable',read_text='KEEPER’S FIELD NOTES\nWalk onto people and objects to interact. Equip your sword, helmet and shield in inventory. F attacks in the last direction moved. The wand uses energy. A blue gem restores health and energy. Drop items on clear ground and walk away and back to recover them.\nThe grove guardian holds a green seal. The castle bell needs a crimson heart. Return to the throne after the belfry falls silent.')
item('blue_gem_object','consumable',effects={'health':10,'energy':6})
for name in ('green_gem_object','red_gem_object'):
 item(name,'object');e.current_game.object_definitions[name]['gettable']=True
for name in ('fountain_object','fountain_red_object','lever_object','throne_object','gargoyle_object','candles_object','gold_coins_object'):
 item(name,'object',walkable=False)
enemies={}
for key,name,sprite,health,speed,damage in [('blob','Road Slime','black_blob_npc',8,.5,2),('spider','Briar Spider','spider_npc',9,.5,3),('guardian','Moss Guardian','gargoyle_npc',15,.5,4),('sentry','Hollow Sentry','skeleton_npc',12,.5,4),('warden','The Hush','dragon_npc',24,.5,5)]:
 e.selected_enemy_id=None;e.add_enemy_definition();eid=e.selected_enemy_id
 e.enemy_name_var.set(name);e.enemy_sprite_var.set(sprite);e.enemy_health_var.set(str(health));e.enemy_speed_var.set(str(speed));e.enemy_behavior_var.set('chase');e.enemy_damage_var.set(str(damage))
 assert e.save_enemy_definition(),errors
 enemies[key]=eid
 e.selected_enemy_id=None
def begin(filename,name,w,h,base='grass',border='forest'):
 e.selected_mode='tile';e._trigger_editor_trigger=None;e._trigger_editor_vars={}
 e.current_area=Area();e.current_area_file=None;e.cursor_x=e.cursor_y=0
 e.resize_canvas(w,h);e.area_name_var.set(name)
 e.selected_tile=base;e.fill_empty_tiles()
 for x in range(w):paint(border,x,0);paint(border,x,h-1)
 for y in range(1,h-1):paint(border,0,y);paint(border,w-1,y)
 e.current_area_file=str(ROOT/'areas'/filename)

def paint(tile,x,y):
 if e.current_area.tiles[y][x].type==tile:return
 e.selected_mode='tile';e.selected_tile=tile;e.cursor_x=x;e.cursor_y=y;e.place_tile()
 if tile.endswith('_door'):
  e.walkable_override_var.set('walkable');e.on_walkable_change()

def rect(tile,x1,y1,x2,y2):
 for y in range(y1,y2+1):
  for x in range(x1,x2+1):paint(tile,x,y)

def obj(name,x,y,npc=False):
 e.selected_mode='npc' if npc else 'object';e.selected_tile=name;e.cursor_x=x;e.cursor_y=y;e.place_tile()

def enemy(key,x,y):
 e.selected_mode='enemy';e.selected_enemy_id=enemies[key];e.cursor_x=x;e.cursor_y=y;assert e.place_selected_enemy();e.selected_enemy_id=None
 from data_classes import ensure_enemy_instance_ids
 ensure_enemy_instance_ids(e.current_area)
 return e.current_area.objects[-1].properties['enemy_instance_id']

def trig(kind,name,tile_x,tile_y,attached='',**params):
 if attached:
  if kind=='inventory' and params.get('add'):
   obj=next(o for o in e.current_area.objects if o.properties.get('enemy_instance_id')==attached)
   obj.properties['loot_object_override']=params['add']
  return
 e.selected_mode='trigger';e.selected_tile=kind;e.cursor_x=tile_x;e.cursor_y=tile_y
 e._trigger_editor_trigger=None;e._trigger_editor_vars={}
 e.place_tile()
 t=e._trigger_editor_trigger
 assert t is not None
 e._trigger_editor_vars['name'].set(name)
 params['charges']=params.pop('charges',1)
 params.pop('once',None)
 for key,value in params.items():
  var=e._trigger_editor_vars[key]
  if isinstance(var,tk.Text):var.delete('1.0',tk.END);var.insert('1.0',str(value))
  else:var.set(value)
 assert e.save_selected_trigger(refresh=False),(name,errors)
 return t

def say(name,x,y,message,charges=1,attached=''):
 return trig('show_message',name,x,y,message=message,charges=charges,attached=attached)

def stats(name,x,y,stat,amount,charges=1):
 return trig('player_stats',name,x,y,stat=stat,amount=amount,charges=charges)

def pickup(itemname,x,y,label):
 obj(itemname,x,y)
 trig('inventory','take_'+label,x,y,add=itemname,once=True)
 trig('area_object','remove_'+label,x,y,action='remove',object=itemname,area='',x=x,y=y,once=True)

def portal(name,x,y,target,tx,ty):trig('teleport',name,x,y,area=Path(target).stem,x=tx,y=ty,charges=0)

def finish():
 e.selected_mode='tile';e._trigger_editor_trigger=None;e._trigger_editor_vars={}
 assert e._save_area_to_file(e.current_area_file,show_message=False),errors
 print(Path(e.current_area_file).name,len(e.current_area.objects),'objects',len(e.current_area.triggers),'triggers',flush=True)


begin('lv_dawnmere.json','Dawnmere Village',13,11)
rect('cobblestone_floor',6,2,6,9);rect('cobblestone_floor',2,5,10,5)
rect('brown_brick_wall',1,1,3,3);paint('gray_brick_door',2,3)
rect('brown_brick_wall',9,1,11,3);paint('gray_brick_door',10,3)
obj('oldwoman_npc',6,2,True)
say('mara_request',6,3,'Mara: The dawn bell has fallen silent. Visit Briarford for armor and a wand. Defeat the guardian in the northern grove for its green seal, then enter the castle. Bring the heart of the silence back to the throne. Take the supplies along this road.')
pickup('sword_object',3,5,'sword');pickup('book_object',4,5,'notes');pickup('torch_object',8,5,'torch')
obj('fountain_object',10,7);stats('village_spring',10,8,'health',40,charges=0)
say('spring_hint',9,8,'The clear spring restores health whenever you return.')
paint('town',6,10);portal('village_exit',6,10,'lv_vale.json',3,9)
finish()

begin('lv_vale.json','Lantern Vale',17,13,border='mountains')
rect('lake_center',7,7,8,10);rect('cobblestone_floor',2,8,14,8);rect('cobblestone_floor',5,2,5,8);rect('cobblestone_floor',12,2,12,8)
for x,y in [(2,2),(3,2),(3,3),(9,3),(10,3),(13,10),(14,10)]:paint('forest',x,y)
paint('town',3,8);portal('west_village',3,8,'lv_dawnmere.json',6,9)
paint('town',13,8);portal('east_village',13,8,'lv_briarford.json',6,9)
paint('down_stairs',5,2);portal('north_grove',5,2,'lv_grove.json',6,9)
paint('castle',12,2);portal('castle_road',12,2,'lv_castle.json',7,11)
say('crossroads',5,8,'THE OLD ROAD\nWest: Dawnmere. East: Briarford. Northwest: Listening Grove. Northeast: Dawnbell Castle.')
enemy('blob',5,10);enemy('spider',14,4)
finish()

begin('lv_briarford.json','Briarford Village',13,11)
rect('cobblestone_floor',6,2,6,9);rect('cobblestone_floor',2,6,10,6)
obj('wizard_npc',9,2,True)
say('fen_advice',9,3,'Fen: Ready the wand in your weapon slot and press F to fire along your facing. Armor protects only while equipped. The runic candles hold two recharges; save them for your return.')
pickup('helmet_object',3,6,'helmet');pickup('shield_object',4,6,'shield');pickup('magic_wand_object',8,6,'wand');pickup('blue_gem_object',9,6,'blue_gem')
obj('candles_object',10,3);stats('two_recharges',10,4,'energy',20,charges=2)
say('recharge_hint',10,5,'The runestone can restore energy twice. Save a charge for your return.')
obj('gold_coins_object',2,3)
trig('funds','travel_funds',2,4,action='add',amount=12)
trig('area_object','collect_purse',2,4,action='remove',object='gold_coins_object',area='',x=2,y=3)
say('purse_note',2,4,'A village purse: a gift for your journey.')
paint('town',6,10);portal('briarford_exit',6,10,'lv_vale.json',13,9)
finish()

begin('lv_grove.json','The Listening Grove',13,11,border='forest')
rect('cobblestone_floor',6,2,6,9)
for x,y in [(3,3),(4,3),(8,3),(9,3),(3,6),(9,6)]:paint('forest',x,y)
obj('gargoyle_object',2,7);stats('stone_blessing',2,8,'strength',1)
say('stone_words',2,8,'An old keeper’s courage warms your hands.')
obj('fountain_red_object',10,7)
say('red_warning',9,8,'The red spring is bitter. The pool beneath it will burn you.')
stats('red_pool',10,8,'health',-4,charges=0)
guardian=enemy('guardian',6,4)
say('guardian_warning',6,9,'Stone grinds ahead. The Moss Guardian carries the seal; it must be defeated.')
trig('inventory','guardian_seal',6,4,add='green_gem_object',attached=guardian)
say('guardian_reward',6,4,'The guardian crumbles. A green seal settles into your hand. The castle awaits.',attached=guardian)
paint('up_stairs',6,10);portal('grove_exit',6,10,'lv_vale.json',5,3)
finish()

begin('lv_castle.json','Dawnbell Castle',15,13,base='cobblestone_floor',border='gray_brick_wall')
rect('gray_brick_wall',1,7,13,7)
paint('gray_brick_open_door',5,10)
obj('guard_npc',4,10,True)
say('donation_sign',5,11,'Keeper: If you can spare $5, step onto the silver paving beside me to help restore the castle. This offering is optional. The green seal opens the inner gate.')
trig('funds','castle_donation',5,10,action='remove',amount=5)
say('donation_thanks',5,10,'The keeper bows. Your gift will help repair the bell tower.')
trig('inventory','seal_offering',7,8,remove='green_gem_object')
trig('tile_update','open_gate',7,8,x=7,y=7,tile='Gray Brick Open Door',walkable=True)
say('gate_response',7,8,'Green light runs through the stone. The inner gate opens. The throne stands in the northwest hall; the belfry stairs are northeast.')
obj('throne_object',3,1)
trig('inventory','heart_offering',3,2,remove='red_gem_object')
trig('area_object','restore_fountain',3,2,area='',action='remove',object='fountain_red_object',x=3,y=3)
trig('area_object','clear_fountain',3,2,area='',action='add',object='fountain_object',x=3,y=3)
trig('game_end','ring_dawn',3,2,win_lose='win',message='You set the crimson heart beneath the throne. The spring clears. Above the castle, the dawn bell rings for the first time in a hundred mornings. Both villages answer with lanterns.\n\nTHE END — The Bell of Dawn')
obj('fountain_red_object',3,3)
enemy('sentry',10,5)
obj('lever_object',3,5)
trig('area_object','supply_spawn',3,6,action='add',object='blue_gem_object',area='',x=4,y=5)
say('supply_hint',3,6,'A hidden drawer opens. A restoration gem rolls onto the paving.')
trig('inventory','supply_take',4,5,add='blue_gem_object')
trig('area_object','supply_remove',4,5,action='remove',object='blue_gem_object',area='',x=4,y=5)
paint('up_stairs',11,2);portal('belfry_stairs',11,2,'lv_vault.json',5,10)
paint('gray_brick_open_door',7,12);portal('castle_exit',7,12,'lv_vale.json',12,3)
finish()

begin('lv_vault.json','The Silent Belfry',11,13,base='gray_brick_wall',border='gray_brick_wall')
rect('cobblestone_floor',3,1,7,4);rect('cobblestone_floor',5,5,5,8);rect('cobblestone_floor',3,9,7,11)
obj('candles_object',3,2);obj('candles_object',7,2)
say('hush_warning',5,10,'The bell hangs soundless above you. The Hush waits in the passage. Defeat it to recover the crimson heart.')
warden=enemy('warden',5,5)
trig('inventory','hush_heart',5,5,add='red_gem_object',attached=warden)
say('hush_falls',5,5,'The Hush breaks apart like smoke. Its crimson heart remains. Bring it to the castle throne.',attached=warden)
paint('down_stairs',5,12);portal('belfry_exit',5,12,'lv_castle.json',11,3)
finish()

e.selected_mode='tile';e._trigger_editor_trigger=None;e._trigger_editor_vars={}
e._load_area_from_file(str(ROOT/'areas/lv_dawnmere.json'),show_message=False)
e.selected_mode='player';e.selected_tile='fighter_npc';assert e.set_player_start(6,7)
player=e.get_player_settings();player['starting_inventory']=['']*8
player['stats'].update(starting_health=32,max_health=32,starting_energy=10,max_energy=10,strength=2,intelligence=1,gold=0)
e.refresh_player_setup()
e.current_game.intro_message='LANTERN VALE: THE BELL OF DAWN\n\nNo bell has welcomed the sunrise in a hundred days. You arrive in Dawnmere with empty hands. Mara waits at the north end of the road; walk to her, gather supplies, and begin your journey.'
e.current_game.instructions_message='Arrows / WASD move. F attacks in the last direction moved. I opens inventory: equip gear, use items, or drop them on clear ground. Walk away and back to recover dropped items. Bottom slots (1–5) use equipped items. Period waits. Walk onto people, items and landmarks to activate their triggers. Blocked moves also take a turn. Save from the Game menu. If your health reaches zero, you can restart.'
e.current_game.game_end_message='The dawn returns to Lantern Vale.'
e.update_game_assets_silent();e.current_game_file=str(ROOT/'games/lantern_vale.json')
e.selected_mode='tile';e.selected_enemy_id=None;e.save_all()
assert not errors,errors
root.update_idletasks();root.destroy()
for p in reversed(patches):p.stop()
print('Fresh adventure authored through editor APIs.')
