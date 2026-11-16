import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[3]
game=json.loads((ROOT/'games/lantern_vale.json').read_text())
size=24;panelw=440;panelh=400
out=Image.new('RGB',(panelw*3,panelh*2),(20,24,31));draw=ImageDraw.Draw(out)
for i,filename in enumerate(game['areas']):
 a=json.loads((ROOT/'areas'/filename).read_text());x0=(i%3)*panelw+16;y0=(i//3)*panelh+44
 draw.text((x0,y0-28),a['name'],fill='white')
 for y,row in enumerate(a['tiles']):
  for x,t in enumerate(row):
   p=ROOT/'tiles'/(t['type']+'.png')
   if p.exists():
    im=Image.open(p).convert('RGBA').resize((size,size),Image.Resampling.NEAREST);out.paste(im,(x0+x*size,y0+y*size),im)
 for o in a['objects']:
  enemy=game['properties']['enemies'].get(o['properties'].get('enemy_id'),{})
  name=enemy.get('sprite',o['type']);folder='npcs' if name.endswith('_npc') else 'objects'
  p=ROOT/folder/(name+'.png')
  if p.exists():
   im=Image.open(p).convert('RGBA').resize((size,size),Image.Resampling.NEAREST);out.paste(im,(x0+o['x']*size,y0+o['y']*size),im)
 if filename==game['properties']['start_area']:
  im=Image.open(ROOT/'npcs/fighter_npc.png').convert('RGBA').resize((size,size),Image.Resampling.NEAREST)
  out.paste(im,(x0+game['properties']['start_x']*size,y0+game['properties']['start_y']*size),im)
out.save(ROOT/'adventures/lantern_vale/map_overview.png')
