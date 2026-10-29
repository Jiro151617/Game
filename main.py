import pygame, random, sys, math, array, json, os, traceback
pygame.mixer.pre_init(16000, -16, 1, 512)
pygame.init()
pygame.display.set_caption("Star Hop Adventure")
try:
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
except pygame.error:
    screen = pygame.display.set_mode((960, 540))
SW, SH = screen.get_size()
clock = pygame.time.Clock()
W, H = 480, max(270, int(480 * SH / max(1, SW)))
canvas = pygame.Surface((W, H))
font = pygame.font.Font(None, 19)
small = pygame.font.Font(None, 14)
big = pygame.font.Font(None, 36)

def crash_handler(et,ev,tb):
    msg="".join(traceback.format_exception(et,ev,tb))
    try:
        with open("star_hop_error.txt","w") as f: f.write(msg)
    except Exception: pass
    try:
        print(msg)
        lines=[l[:100] for l in msg.strip().split("\n")][-14:]
        ef=pygame.font.Font(None,max(18,SH//28)); end=pygame.time.get_ticks()+60000
        while pygame.time.get_ticks()<end:
            for e in pygame.event.get():
                if e.type in (pygame.QUIT,pygame.KEYDOWN,pygame.MOUSEBUTTONDOWN,pygame.FINGERDOWN): end=0
            screen.fill((40,10,10))
            for i,l in enumerate(lines): screen.blit(ef.render(l,True,(255,230,230)),(10,10+i*ef.get_height()))
            pygame.display.flip(); clock.tick(10)
    except Exception: pass
    pygame.quit()
sys.excepthook=crash_handler

def clamp(v,a,b): return max(a,min(b,v))
def show_loading():
    canvas.fill((20,30,55)); im=font.render("LOADING...",True,(255,250,225))
    canvas.blit(im,im.get_rect(center=(W//2,H//2)))
    screen.blit(pygame.transform.scale(canvas,(SW,SH)),(0,0)); pygame.display.flip()
show_loading()

# ================================================================ AUDIO (synthesized)
AUDIO=False; RATE=16000; CH=1
try:
    if not pygame.mixer.get_init(): pygame.mixer.init(16000,-16,1,512)
    RATE,_f,CH=pygame.mixer.get_init(); AUDIO=True
except Exception:
    AUDIO=False
def to_sound(smp,vol=0.5):
    buf=array.array('h')
    for v in smp:
        s=int(clamp(v,-1,1)*32767*vol); buf.append(s)
        if CH==2: buf.append(s)
    return pygame.mixer.Sound(buffer=buf.tobytes())
def tone(f0,f1,dur,wave="sq"):
    n=int(RATE*dur); out=[]; ph=0.0
    for i in range(n):
        t=i/n; ph+=(f0+(f1-f0)*t)/RATE; x=ph%1.0
        v=random.uniform(-1,1) if wave=="noise" else (0.7 if x<.5 else -0.7)
        out.append(v*(1-t))
    return out
def mid(n): return 440.0*2**((n-69)/12)
def make_music():
    N=None
    mel=[72,76,79,76,72,76,79,76, 77,81,84,81,77,81,84,81, 79,83,86,83,79,83,86,83, 72,76,79,84,79,76,72,N,
         69,72,76,72,69,72,76,72, 65,69,72,69,65,69,72,69, 67,71,74,71,67,71,74,71, 72,76,79,76,72,N,N,N]
    roots=[60,65,67,60,57,65,67,60]; ne=int(RATE*0.2); out=[]
    for bar in range(8):
        seg=[0.0]*(ne*8)
        for k in range(8):
            n=mel[bar*8+k]
            if n is None: continue
            f=mid(n); base=k*ne
            for i in range(ne):
                x=(i*f/RATE)%1.0; env=1-0.6*i/ne
                if i>ne*.9: env*=(ne-i)/(ne*.1)
                seg[base+i]=(0.5 if x<.25 else -0.5)*env*0.55
        for k in range(4):
            f=mid(roots[bar] if k%2==0 else roots[bar]+7); base=k*2*ne
            for i in range(2*ne):
                x=(i*f/RATE)%1.0; env=1.0 if i<1.7*ne else (2*ne-i)/(0.3*ne)
                seg[base+i]+=(4*abs(x-0.5)-1)*env*0.45
        out+=seg
    return out
SFX={}; music_snd=None
if AUDIO:
    try:
        SFX["jump"]=to_sound(tone(280,640,.13),.35)
        SFX["coin"]=to_sound(tone(988,988,.05)+tone(1319,1319,.14),.3)
        SFX["hurt"]=to_sound(tone(330,70,.35),.45)
        SFX["stomp"]=to_sound(tone(200,60,.12)+tone(120,40,.1,"noise"),.45)
        SFX["power"]=to_sound(sum((tone(f,f,.07) for f in (523,659,784,1046,1318)),[]),.35)
        SFX["boss"]=to_sound(tone(400,100,.18,"noise")+tone(150,60,.15),.5)
        SFX["shoot"]=to_sound(tone(500,150,.12,"noise"),.3)
        SFX["win"]=to_sound(sum((tone(f,f,.12) for f in (523,659,784,1046,784,1046,1318)),[]),.4)
        SFX["over"]=to_sound(tone(392,392,.15)+tone(330,330,.15)+tone(262,130,.5),.4)
        music_snd=to_sound(make_music(),.35)
    except Exception:
        AUDIO=False; music_snd=None
def sfx(n):
    s=SFX.get(n)
    if s:
        try: s.play()
        except Exception: pass

# ================================================================ game data
SKY=(105,185,235); GREEN=(64,175,70); DGREEN=(35,125,55)
DIRT=(150,91,53); BROWN=(99,56,40); GOLD=(255,207,52)
RED=(230,60,70); BLUE=(48,104,226); BLACK=(34,39,53); WHITE=(255,250,225)
TILE=24; GROUND=H-55
GRAVITY=900; SPEED=205; JUMP=390; JUMP_FULL=430; JUMP_MIN=300
STAR_TIME=4.11; NAME_MAX=10

DIFFS=[{"name":"EASY","lives":5,"es":0.8,"bhp":0.7,"mult":0.75,"ps":0.85,"dens":0.75,"col":(60,150,80)},
       {"name":"NORMAL","lives":3,"es":1.0,"bhp":1.0,"mult":1.0,"ps":1.0,"dens":1.0,"col":(60,110,200)},
       {"name":"HARD","lives":2,"es":1.25,"bhp":1.4,"mult":1.5,"ps":1.2,"dens":1.3,"col":(210,130,40)},
       {"name":"INSANE","lives":1,"es":1.4,"bhp":1.8,"mult":2.5,"ps":1.35,"dens":1.6,"col":(200,50,60)}]
LEVELS=[
 {"name":"GREEN VALLEY","theme":0,"secs":[3],"bosses":["golem"],"enemies":{"slime":5,"spike":2,"bat":2},"dens":1.0,"gap":(80,115),"par":140},
 {"name":"SANDY RUINS","theme":1,"secs":[4],"bosses":["king"],"enemies":{"slime":2,"spike":3,"bat":2,"frog":4,"charger":2},"dens":1.1,"gap":(85,120),"par":180},
 {"name":"FROST PEAKS","theme":2,"secs":[3,3],"bosses":["golem","king"],"enemies":{"spike":2,"bat":3,"frog":3,"ghost":3,"turret":2,"charger":2},"dens":1.2,"gap":(90,125),"par":260},
 {"name":"LAVA CASTLE","theme":3,"secs":[3,3,3],"bosses":["golem","king","king"],"enemies":{"slime":1,"spike":3,"bat":3,"frog":2,"ghost":3,"turret":3,"charger":3},"dens":1.35,"gap":(95,125),"par":380},
]
EPTS={"slime":50,"spike":40,"bat":75,"frog":60,"ghost":100,"turret":100,"charger":90}
THEMES=[
 dict(sky=((95,160,235),(190,230,250)),mtn=(150,168,214),snow=True,hill=(112,188,140),spA=(46,140,80),spB=(64,164,96),cloud=(255,250,225),
      orb=((255,240,170),(255,222,100)),top=(64,175,70),dtop=(35,125,55),hl=(105,210,95),dirt=(150,91,53),peb=((120,70,42),(172,110,66),(95,55,38)),
      stone=((84,88,104),(104,110,126),(52,56,70)),brick=((150,142,150),(190,184,190),(98,92,104)),plank=((180,105,57),(255,196,88),(130,72,40)),
      liq=((40,110,200),(30,85,170),(150,215,255)),decor=("tree","tree","bush","flower","flower","rock","fence"),house=((225,205,170),(190,60,60)),
      lava=False,rays=True,birds=True,embers=False,snowfall=False,castle=(124,130,150),crys=(150,220,255)),
 dict(sky=((235,160,100),(255,232,180)),mtn=(205,150,115),snow=False,hill=(232,190,120),spA=(205,165,100),spB=(228,194,128),cloud=(255,238,205),
      orb=((255,200,120),(255,150,60)),top=(232,204,120),dtop=(200,165,90),hl=(250,228,150),dirt=(196,150,86),peb=((170,125,70),(215,175,105),(150,105,60)),
      stone=((150,115,80),(175,140,100),(110,80,55)),brick=((205,170,115),(230,200,145),(150,115,75)),plank=((160,110,60),(225,175,95),(115,75,40)),
      liq=((200,160,85),(165,125,60),(235,205,130)),decor=("cactus","cactus","dry","rock","pillar"),house=((232,205,150),(175,95,55)),
      lava=False,rays=False,birds=False,embers=False,snowfall=False,castle=(214,180,125),crys=(255,200,90)),
 dict(sky=((120,150,205),(215,235,250)),mtn=(170,190,225),snow=True,hill=(205,225,240),spA=(60,110,110),spB=(90,140,140),cloud=(240,245,255),
      orb=((235,240,255),(255,255,255)),top=(238,246,255),dtop=(170,200,230),hl=(255,255,255),dirt=(105,115,150),peb=((80,90,125),(135,145,180),(65,72,105)),
      stone=((90,100,130),(120,130,160),(60,66,92)),brick=((170,185,210),(215,225,240),(110,125,155)),plank=((140,150,175),(215,230,250),(95,105,135)),
      liq=((30,80,150),(20,55,115),(150,200,250)),decor=("pine","pine","snowman","crystal","rock","fence"),house=((235,238,248),(70,95,150)),
      lava=False,rays=False,birds=False,embers=False,snowfall=True,castle=(170,185,210),crys=(150,220,255)),
 dict(sky=((35,18,48),(160,60,50)),mtn=(75,40,70),snow=False,hill=(95,45,60),spA=(60,30,50),spB=(84,42,62),cloud=(80,55,75),
      orb=((200,70,60),(240,110,70)),top=(96,62,70),dtop=(66,40,52),hl=(150,100,90),dirt=(70,45,55),peb=((50,30,42),(100,65,70),(40,24,34)),
      stone=((54,42,62),(76,62,86),(34,26,42)),brick=((96,80,110),(130,115,145),(60,48,72)),plank=((90,60,60),(150,100,90),(55,35,40)),
      liq=((230,90,30),(190,50,20),(255,210,90)),decor=("torch","torch","crystal","rock","pillar"),house=None,
      lava=True,rays=False,birds=False,embers=True,snowfall=False,castle=(90,70,105),crys=(255,120,60)),
]
OUTFITS=[
 {"id":"classic","name":"CLASSIC","top":(133,86,50),"topd":(98,62,36),"trim":(165,115,75),"btn":(80,50,30),"pant":(74,80,100),"shoe":(58,38,30),"hand":(240,200,160)},
 {"id":"ninja","name":"NINJA","top":(42,44,60),"topd":(26,28,40),"trim":(200,50,60),"btn":(90,90,110),"pant":(32,34,46),"shoe":(20,20,26),"hand":(30,32,44)},
 {"id":"forest","name":"FOREST","top":(62,140,72),"topd":(40,100,52),"trim":(210,190,110),"btn":(230,210,120),"pant":(110,78,48),"shoe":(80,54,34),"hand":(240,200,160)},
 {"id":"royal","name":"ROYAL","top":(112,52,160),"topd":(80,34,120),"trim":(245,245,250),"btn":(255,207,52),"pant":(60,30,90),"shoe":(230,190,60),"hand":(240,200,160)},
 {"id":"wizard","name":"WIZARD","top":(60,70,170),"topd":(40,48,130),"trim":(255,220,80),"btn":(255,220,80),"pant":(40,48,110),"shoe":(90,60,40),"hand":(240,200,160)},
 {"id":"pirate","name":"PIRATE","top":(190,50,55),"topd":(130,32,38),"trim":(240,235,220),"btn":(240,200,60),"pant":(50,50,70),"shoe":(30,30,36),"hand":(240,200,160)},
 {"id":"chef","name":"CHEF","top":(245,245,250),"topd":(205,205,218),"trim":(220,60,60),"btn":(150,150,165),"pant":(90,95,110),"shoe":(40,40,46),"hand":(240,200,160)},
 {"id":"cowboy","name":"COWBOY","top":(210,175,125),"topd":(160,125,80),"trim":(210,60,55),"btn":(110,70,40),"pant":(60,90,150),"shoe":(90,55,30),"hand":(240,200,160)},
 {"id":"astronaut","name":"ASTRONAUT","top":(235,238,245),"topd":(170,175,190),"trim":(240,140,40),"btn":(90,200,255),"pant":(225,228,238),"shoe":(130,135,150),"hand":(200,205,220)},
]

# ================================================================ settings / save
player_name="Grandpa"; outfit=0; music_on=True; diff=1; unlocked=1; best={}
try: SAVE=os.path.join(os.path.dirname(os.path.abspath(__file__)),"star_hop_save.json")
except Exception: SAVE="star_hop_save.json"
def save_settings():
    try:
        with open(SAVE,"w") as f: json.dump({"name":player_name,"outfit":outfit,"music":music_on,"diff":diff,"unlocked":unlocked,"best":best},f)
    except Exception: pass
try:
    with open(SAVE) as f: d=json.load(f)
    player_name=str(d.get("name",player_name))[:NAME_MAX]; outfit=int(d.get("outfit",0))%len(OUTFITS); music_on=bool(d.get("music",True))
    diff=int(d.get("diff",1))%len(DIFFS); unlocked=clamp(int(d.get("unlocked",1)),1,len(LEVELS)); best=dict(d.get("best",{}))
except Exception: pass
def apply_music():
    if not AUDIO or music_snd is None: return
    try:
        if music_on: music_snd.play(-1)
        else: music_snd.stop()
    except Exception: pass
def toggle_music():
    global music_on
    music_on=not music_on; apply_music(); save_settings()

# ================================================================ themed tiles
TH=THEMES[0]; grass_t=dirt_t=stone_t=brick_t=plank_t=sky=None
def mk_dirt(seed):
    r=random.Random(seed); t=pygame.Surface((TILE,TILE)); t.fill(TH["dirt"])
    for _ in range(9): pygame.draw.rect(t,r.choice(TH["peb"]),(r.randrange(1,20),r.randrange(1,20),r.choice((2,3,4)),2))
    return t
def mk_grass(seed):
    t=mk_dirt(seed); r=random.Random(seed+9)
    pygame.draw.rect(t,TH["top"],(0,0,TILE,7)); pygame.draw.rect(t,TH["dtop"],(0,7,TILE,2)); pygame.draw.rect(t,TH["hl"],(0,0,TILE,2))
    for xx in range(0,TILE,4): pygame.draw.rect(t,TH["dtop"],(xx,9,2,r.choice((2,3,4))))
    for _ in range(3): pygame.draw.rect(t,TH["hl"],(r.randrange(0,TILE-2),r.randrange(2,6),2,1))
    return t
def mk_stone(base,hi,mortar):
    t=pygame.Surface((TILE,TILE)); t.fill(base)
    pygame.draw.rect(t,mortar,(0,0,TILE,1)); pygame.draw.rect(t,mortar,(0,12,TILE,1))
    pygame.draw.rect(t,mortar,(11,0,1,12)); pygame.draw.rect(t,mortar,(0,12,1,12))
    pygame.draw.rect(t,hi,(1,1,10,2)); pygame.draw.rect(t,hi,(12,1,11,2)); pygame.draw.rect(t,hi,(2,13,21,2))
    return t
def apply_theme(i):
    global TH,grass_t,dirt_t,stone_t,brick_t,plank_t,sky
    TH=THEMES[i]
    grass_t=[mk_grass(k) for k in range(3)]; dirt_t=[mk_dirt(k+20) for k in range(3)]
    stone_t=mk_stone(*TH["stone"]); brick_t=mk_stone(*TH["brick"])
    base,topc,dark=TH["plank"]
    plank_t=pygame.Surface((TILE,14)); plank_t.fill(base)
    pygame.draw.rect(plank_t,topc,(0,0,TILE,4)); pygame.draw.rect(plank_t,dark,(0,12,TILE,2))
    pygame.draw.rect(plank_t,dark,(3,7,10,1)); pygame.draw.rect(plank_t,dark,(14,9,8,1)); pygame.draw.rect(plank_t,dark,(0,0,1,14))
    sky=pygame.Surface((W,H)); a,b=TH["sky"]
    for yy in range(H):
        t=yy/H; pygame.draw.line(sky,tuple(int(a[k]+(b[k]-a[k])*t) for k in range(3)),(0,yy),(W,yy))
apply_theme(0)
def pix(rows,col,scale=2):
    s=pygame.Surface((len(rows[0])*scale,len(rows)*scale),pygame.SRCALPHA)
    for y,row in enumerate(rows):
        for x,ch in enumerate(row):
            if ch=="X": pygame.draw.rect(s,col,(x*scale,y*scale,scale,scale))
    return s
HEART=pix([".XX.XX.","XXXXXXX","XXXXXXX",".XXXXX.","..XXX..","...X..."],(235,60,80))
STARI=pix(["...X...","..XXX..","XXXXXXX",".XXXXX.",".XX.XX.","X.....X"],GOLD)
SHADOW=pygame.Surface((22,6),pygame.SRCALPHA); pygame.draw.ellipse(SHADOW,(0,0,0,80),(0,0,22,6))
def mk_coin():
    c=pygame.Surface((16,16),pygame.SRCALPHA)
    pygame.draw.circle(c,(185,125,28),(8,8),8); pygame.draw.circle(c,(255,205,50),(8,8),7); pygame.draw.circle(c,(255,232,120),(8,8),5)
    pts=[(8+math.cos(-math.pi/2+i*math.pi/5)*(4.6 if i%2==0 else 2.0),8.4+math.sin(-math.pi/2+i*math.pi/5)*(4.6 if i%2==0 else 2.0)) for i in range(10)]
    pygame.draw.polygon(c,(214,138,18),pts); pygame.draw.rect(c,(255,250,200),(3,3,2,1))
    return c
COIN=mk_coin(); COIN_FR=[pygame.transform.scale(COIN,(w,16)) for w in (16,13,9,4,9,13)]
def mk_sandwich():
    s=pygame.Surface((32,26),pygame.SRCALPHA)
    def R(c,x,y,w,h): pygame.draw.rect(s,c,(x,y,w,h))
    O=(90,55,30); CR=(196,128,60); BR=(240,196,120)
    R(O,1,19,30,7); R(CR,2,20,28,5); R(BR,3,20,26,2)
    R((240,140,150),0,16,32,4); R((255,180,185),2,16,28,1)
    R((255,214,60),1,13,28,3); R((255,214,60),21,16,6,3)
    R((226,60,55),2,10,26,3); R((255,205,195),7,11,1,1); R((255,205,195),15,11,1,1); R((255,205,195),22,11,1,1)
    for i in range(0,32,4): R((110,200,80),i,8+(i//4)%2,5,3); R((70,150,60),i,10+(i//4)%2,5,1)
    R(O,4,0,24,1); R(O,2,1,28,1); R(O,1,2,30,6); R(CR,5,1,22,1); R(CR,3,2,26,5); R(BR,5,2,22,3)
    for sx,sy in ((8,3),(15,2),(21,4),(12,5),(25,3)): R((255,250,225),sx,sy,2,1)
    return s
SAND=mk_sandwich(); SAND2=pygame.transform.scale(SAND,(64,52))

# ================================================================ level building
platforms=[]; blocks=[]; coins=[]; enemies=[]; checkpoints=[]; powerups=[]; bosses=[]; projectiles=[]; parts=[]; decor=[]; houses=[]
cp_on=[]; WORLD=5200; goal=5050; gen_x=0; gen_i=0; erng=random.Random()
def ground(a,b): return pygame.Rect(a,GROUND,b-a,H-GROUND+80)
def stairs(x,n,d):
    for i in range(n):
        h=TILE*(i+1) if d>0 else TILE*(n-i)
        blocks.append(pygame.Rect(x+i*TILE,GROUND-h,TILE,h))
def add_coin(x,y): coins.append({"r":pygame.Rect(x,y,12,14),"got":False})
def pick(rnd,weights):
    items=list(weights.items()); tot=sum(w for _,w in items); r=rnd.random()*tot
    for k,w in items:
        r-=w
        if r<=0: return k
    return items[-1][0]
def add_plank(x,h,w,rnd,prob,kind=None):
    platforms.append(pygame.Rect(x,GROUND-h,w,14))
    for cx in range(x+12,x+w-12,24): add_coin(cx,GROUND-h-20)
    if kind or rnd.random()<prob:
        powerups.append({"k":kind or pick(rnd,{"speed":3,"jump":3,"star":2}),"x":x+w//2-8,"y":GROUND-h-18,"got":False})
def mk_enemy(t,x):
    es=DIFFS[diff]["es"]
    e={"t":t,"x":float(x),"d":random.choice([-1,1]),"alive":True,"cd":random.uniform(.3,1.5),"air":False,"vy":0.0,"st":"walk","tm":0.0,"flash":0.0,"watched":False}
    if t=="slime": e.update(y=GROUND-21,w=25,h=21,sp=45,speed=random.randint(35,55)*es)
    elif t=="spike": e.update(y=GROUND-19,w=22,h=19,sp=55,speed=random.randint(55,75)*es)
    elif t=="bat": e.update(y=GROUND-62,by=GROUND-62,w=22,h=14,sp=60,speed=random.randint(50,70)*es)
    elif t=="frog": e.update(y=GROUND-16,w=20,h=16,sp=40,speed=85*es)
    elif t=="ghost": e.update(y=GROUND-80,by=GROUND-80,w=20,h=22,sp=0,speed=40*es)
    elif t=="turret": e.update(y=GROUND-22,w=24,h=22,sp=0,speed=0)
    else: e.update(y=GROUND-18,w=28,h=18,sp=70,speed=random.randint(30,40)*es)
    e["lo"]=x-e["sp"]; e["hi"]=x+e["sp"]
    return e
def fill_segment(a,b,rnd,weights,dens,first=False):
    L=b-a; n0=len(coins); res=[]
    if L>420 and not first and rnd.random()<0.55:
        sx=rnd.randrange(a+140,b-220)//24*24
        if rnd.random()<0.5: stairs(sx,3,rnd.choice((1,-1))); res.append((sx-30,sx+3*TILE+30))
        else: blocks.append(pygame.Rect(sx,GROUND-rnd.choice((48,72)),48,0)); blocks[-1].height=GROUND-blocks[-1].y; res.append((sx-40,sx+90))
    taken=list(res)
    for _ in range(rnd.randint(1,3) if L>400 else 1):
        for tries in range(6):
            w=rnd.choice((96,120)); x=rnd.randrange(a+50,b-160)//24*24
            if all(x+w+40<t0 or x-40>t1 for t0,t1 in taken):
                taken.append((x,x+w)); h=rnd.choice((75,85,95)); add_plank(x,h,w,rnd,0.3)
                if rnd.random()<0.5 and x+w-48+96<b-30:
                    hx=x+w-48; taken.append((hx,hx+96)); add_plank(hx,h+60,96,rnd,0.25)
                break
    for x in range(a+70,b-25,76): add_coin(x,GROUND-42)
    for c in coins[n0:]:
        for bl in blocks:
            if c["r"].colliderect(bl): c["r"].bottom=bl.top-4
    for _ in range(int(L/230*dens+rnd.random())):
        t=pick(rnd,weights)
        for tries in range(5):
            x=rnd.randrange(a+350 if first else a+90,b-90)
            if all(x+80<t0 or x-80>t1 for t0,t1 in res) and all(abs(x-c)>90 for c in checkpoints):
                enemies.append(mk_enemy(t,x)); break
    x=a+25
    while x<b-45:
        decor.append((rnd.choice(TH["decor"]),x,rnd.randrange(3))); x+=rnd.randrange(38,95)
    if TH["house"] and not first and L>420 and rnd.random()<0.35: houses.append(rnd.randrange(a+40,b-100))
def fill_arena(lo,hi,kind,n,rnd):
    D=DIFFS[diff]
    add_plank(lo+144,85,120,rnd,0,"star"); add_plank((hi-300)//24*24,85,120,rnd,0,"jump")
    for x in range(lo+70,hi-60,76): add_coin(x,GROUND-42)
    x=lo+60
    while x<hi-60:
        decor.append((rnd.choice(TH["decor"]),x,rnd.randrange(3))); x+=rnd.randrange(90,160)
    base={"golem":5,"king":7}[kind]+n
    hp=max(2,int(round(base*D["bhp"])))
    bosses.append(mk_boss(kind,lo,hi,lo+90,hp,46 if kind=="golem" else 48,46 if kind=="golem" else 40))
def mk_boss(k,lo,hi,trig,hp,w,h):
    return {"k":k,"lo":lo,"hi":hi,"trig":trig,"hp":hp,"max":hp,"w":w,"h":h,"active":False,"dead":False,
            "x":0.0,"y":0.0,"vx":0.0,"vy":0.0,"t":0.0,"hit":0.0,"air":False,"d":-1,"fire":1.5,"dive":0.0,"rt":0.0,"tx":0.0,"st":"hover"}
def clear_world():
    for l in (platforms,blocks,coins,enemies,checkpoints,powerups,bosses,projectiles,parts,decor,houses): l.clear()
def build_level(n):
    global WORLD,goal,cp_on
    cfg=LEVELS[n]; apply_theme(cfg["theme"]); clear_world(); rnd=random.Random(1000+n)
    dens=cfg["dens"]*DIFFS[diff]["dens"]
    platforms.append(ground(0,700)); fill_segment(0,700,rnd,cfg["enemies"],dens,True); cursor=700; sidx=0
    for gi,kind in enumerate(cfg["bosses"]):
        for s in range(cfg["secs"][gi]):
            a=cursor+rnd.randrange(*cfg["gap"]); b=a+rnd.randrange(450,700)
            platforms.append(ground(a,b))
            if sidx%2==0: checkpoints.append(a+50)
            fill_segment(a,b,rnd,cfg["enemies"],dens); cursor=b; sidx+=1
        lo=cursor+rnd.randrange(90,115); hi=lo+(800 if gi<len(cfg["bosses"])-1 else 900)
        platforms.append(ground(lo,hi)); checkpoints.append(lo+30); fill_arena(lo,hi,kind,n,rnd); cursor=hi
    WORLD=cursor; goal=cursor-300; cp_on=[False]*len(checkpoints)
def build_endless():
    global WORLD,goal,cp_on,gen_x,gen_i
    apply_theme(erng.randrange(len(THEMES))); clear_world(); WORLD=10**9; goal=10**9; cp_on=[]
    platforms.append(ground(0,700)); fill_segment(0,700,erng,{"slime":1},0.5,True); gen_x=700; gen_i=0
    while gen_x<W+900: gen_chunk()
def gen_chunk():
    global gen_x,gen_i
    i=gen_i; a=gen_x+erng.randrange(80,100+min(35,i*2)); b=a+erng.randrange(420,680)
    w={"slime":4}
    for need,k,v in ((1,"bat",2),(2,"frog",3),(3,"spike",2),(5,"charger",2),(7,"turret",2),(9,"ghost",2)):
        if i>=need: w[k]=v
    platforms.append(ground(a,b)); fill_segment(a,b,erng,w,min(2.4,0.6+0.1*i)*DIFFS[diff]["dens"])
    gen_x=b; gen_i+=1
def cull(cx):
    platforms[:]=[r for r in platforms if r.right>cx]; blocks[:]=[r for r in blocks if r.right>cx]
    coins[:]=[c for c in coins if c["r"].right>cx]; powerups[:]=[u for u in powerups if u["x"]>cx]
    enemies[:]=[e for e in enemies if e["alive"] and e["x"]>cx]; decor[:]=[d for d in decor if d[1]>cx]; houses[:]=[h for h in houses if h>cx]

# ================================================================ UI layout
MY=(H-270)//2
M={"left":pygame.Rect(22,104+MY,38,38),"right":pygame.Rect(170,104+MY,38,38),"name":pygame.Rect(30,194+MY,170,26),
   "story":pygame.Rect(250,58+MY,210,30),"endless":pygame.Rect(250,94+MY,210,30),"diff":pygame.Rect(250,130+MY,210,30),
   "scores":pygame.Rect(250,166+MY,210,30),"music":pygame.Rect(250,202+MY,210,30)}
BACK=pygame.Rect(W//2-60,H-44,120,28)
CARDS=[pygame.Rect(W//2-215+(i%2)*220,54+MY+(i//2)*80,210,70) for i in range(4)]
UI={"menu":pygame.Rect(W-64,5,58,22),"music":pygame.Rect(W-128,5,58,22)}
RB={"retry":pygame.Rect(W//2-190,H-44,120,30),"menu":pygame.Rect(W//2-60,H-44,120,30),"next":pygame.Rect(W//2+70,H-44,120,30)}
BUT={"left":pygame.Rect(12,H-80,66,64),"right":pygame.Rect(86,H-80,66,64),"jump":pygame.Rect(W-100,H-92,86,76)}
def build_keys():
    keys=[]; kw=42; gap=3; y=64+MY
    for row in ["1234567890","QWERTYUIOP","ASDFGHJKL","ZXCVBNM"]:
        x0=(W-(len(row)*(kw+gap)-gap))//2
        for i,ch in enumerate(row): keys.append((ch,pygame.Rect(x0+i*(kw+gap),y,kw,30)))
        y+=33
    keys.append(("DEL",pygame.Rect(W//2-175,y,80,30))); keys.append(("SPACE",pygame.Rect(W//2-91,y,120,30))); keys.append(("OK",pygame.Rect(W//2+35,y,140,30)))
    return keys
KEYS=build_keys()
def make_btn(n,pressed):
    r=BUT[n]; a=pygame.Surface(r.size,pygame.SRCALPHA)
    a.fill((255,255,255,150) if pressed else (255,255,255,80))
    pygame.draw.rect(a,(20,30,50,190),(0,0,r.w,r.h),3)
    w,h=r.w,r.h; c=(30,40,70,235)
    if n=="left": pygame.draw.polygon(a,c,[(w*.66,h*.2),(w*.32,h*.5),(w*.66,h*.8)])
    elif n=="right": pygame.draw.polygon(a,c,[(w*.34,h*.2),(w*.68,h*.5),(w*.34,h*.8)])
    else:
        pygame.draw.polygon(a,c,[(w*.5,h*.12),(w*.22,h*.45),(w*.4,h*.45),(w*.4,h*.62),(w*.6,h*.62),(w*.6,h*.45),(w*.78,h*.45)])
        im=small.render("JUMP",True,(30,40,70)); a.blit(im,im.get_rect(center=(w//2,int(h*.82))))
    return a
BTNS={(n,s):make_btn(n,s) for n in BUT for s in (False,True)}

# ================================================================ state
p=pygame.Rect(70,GROUND-28,19,28); px=float(p.x); py=float(p.y); vx=vy=0
lives=3; spawn=70.0; invuln=0; cam=0.0; cam_floor=0.0; grounded=False; face=1; state="menu"; frame=0
mode="story"; level=0; stats={}; level_time=0.0; maxx=0.0; result={}
held=set(); fingers={}; mouseheld=set(); jump_prev=False; jumping=False; jump_event=False
jump_buffer=0.0; coyote_time=0.0; anim_time=0.0; land_squash=0.0
speed_t=jump_t=star_t=0.0; shake=0.0; banner=""; banner_t=0.0; cam_smooth=0.0
finger_seen=False; last_tap=(-1000,(0,0)); prev_state="menu"
dtime=0.0; splashed=False; sand_got=False; win_timer=0.0

def txt(s,t,x,y,f=font,c=WHITE):
    s.blit(f.render(t,True,BLACK),(x+1,y+1)); s.blit(f.render(t,True,c),(x,y))
def label(s,t,cx,y,f=small,c=WHITE):
    im=f.render(t,True,c); sh=f.render(t,True,BLACK); x=cx-im.get_width()//2
    for dx,dy in ((-1,0),(1,0),(0,-1),(0,1)): s.blit(sh,(x+dx,y+dy))
    s.blit(im,(x,y))
def to_logical(pos): return int(pos[0]*W/SW),int(pos[1]*H/SH)
def hit_control(pos):
    for n,r in BUT.items():
        if r.inflate(8,24).collidepoint(pos): return n
def burst(x,y,col,n=8,size=2,spread=70,up=110,grav=400,life=0.5):
    for _ in range(n): parts.append([x,y,random.uniform(-spread,spread),random.uniform(-up,-up*.1),life+random.random()*0.3,col,size,grav])
def say(t,sec=2.2):
    global banner,banner_t
    banner=t; banner_t=sec
def boss_walls(b): return [pygame.Rect(b["lo"],-120,20,H+400),pygame.Rect(b["hi"]-20,-120,20,H+400)]
def reset_boss(b):
    if b["dead"]: return
    b["active"]=False; b["hp"]=b["max"]; b["hit"]=0; b["t"]=0; b["vx"]=b["vy"]=0; b["air"]=False; b["rt"]=0
    if b["k"]=="golem": b["x"]=float(b["hi"]-110); b["y"]=float(GROUND-b["h"])
    else: b["x"]=float(b["hi"]-150); b["y"]=float(GROUND-120); b["st"]="hover"; b["fire"]=1.5; b["dive"]=0; b["d"]=-1
    projectiles.clear()
def reset_player():
    global px,py,vx,vy,invuln,grounded,jumping,splashed
    px=float(spawn); py=float(GROUND-p.height); vx=vy=0; invuln=1.4; grounded=False; jumping=False; splashed=False
def raw_now():
    s=stats; r=s["coins"]*10+s["kill_pts"]+s["bosses"]*500+s["power"]*25+s["cps"]*100
    if mode=="endless": r+=int(maxx)//10
    return r
def restart():
    global lives,spawn,state,cam,cam_floor,cp_on,speed_t,jump_t,star_t,stats,level_time,maxx,cam_smooth,banner_t,sand_got,win_timer
    if mode=="endless": build_endless()
    else: build_level(level)
    stats={"coins":0,"kills":0,"kill_pts":0,"bosses":0,"power":0,"cps":0}
    lives=DIFFS[diff]["lives"]; spawn=70.0; state="play"; cam=0.0; cam_floor=0.0; cam_smooth=0.0; banner_t=0.0
    speed_t=jump_t=star_t=0.0; level_time=0.0; maxx=0.0; sand_got=False; win_timer=0.0
    for b in bosses: reset_boss(b)
    reset_player()
    say("ENDLESS MODE" if mode=="endless" else "LEVEL %d: %s"%(level+1,LEVELS[level]["name"]),2.5)
def start_run(m,l):
    global mode,level
    mode=m; level=l; held.clear(); fingers.clear(); mouseheld.clear(); restart()
def go_menu():
    global state
    state="menu"; held.clear(); fingers.clear(); mouseheld.clear()
def start_dying():
    global state,dtime,vx,vy
    state="dying"; dtime=0.0; vx=0; vy=0
    burst(p.centerx,p.centery,(255,230,110),14,3,110,120)
def hurt():
    global lives,invuln,vx,vy
    if sand_got: return
    lives-=1; sfx("hurt")
    if lives<=0: start_dying()
    else:
        invuln=1.25; vx=-face*120; vy=-210; burst(p.centerx,p.centery,(255,110,110),8,3,90,90)
def fall_death():
    global lives,state
    lives-=1; sfx("hurt")
    for b in bosses: reset_boss(b)
    if lives<=0: state="over"
    else: reset_player()
def kill_enemy(e):
    e["alive"]=False; stats["kills"]+=1; stats["kill_pts"]+=EPTS[e["t"]]
def calc_result(won):
    global result,unlocked
    D=DIFFS[diff]; s=stats; rows=[("Coins x%d"%s["coins"],s["coins"]*10),("Enemies x%d"%s["kills"],s["kill_pts"])]
    if mode=="story": rows.append(("Bosses x%d"%s["bosses"],s["bosses"]*500))
    rows+=[("Power-ups x%d"%s["power"],s["power"]*25),("Checkpoints x%d"%s["cps"],s["cps"]*100)]
    if mode=="endless": rows.append(("Distance %dm"%(maxx//24),int(maxx)//10))
    if won: rows+=[("Sandwich reward",500),("Time %ds"%level_time,max(0,int((LEVELS[level]["par"]-level_time)*10))),("Lives left x%d"%lives,lives*250)]
    total=int(sum(v for _,v in rows)*D["mult"])
    key=("E" if mode=="endless" else "L%d"%level)+"_%d"%diff; new=total>best.get(key,0)
    if new: best[key]=total
    if won and mode=="story": unlocked=max(unlocked,min(len(LEVELS),level+2))
    save_settings()
    title=("YOU WIN!" if level==len(LEVELS)-1 else "LEVEL CLEAR!") if won else "GAME OVER"
    result={"rows":rows,"total":total,"new":new,"won":won,"best":best.get(key,0),"mult":D["mult"],"dname":D["name"],"title":title}
def finish_name():
    global player_name,state
    player_name=player_name.strip() or "Grandpa"; state="menu"; save_settings()
def key_press(lab):
    global player_name
    if lab=="DEL": player_name=player_name[:-1]
    elif lab=="OK": finish_name()
    elif lab=="SPACE":
        if player_name and len(player_name)<NAME_MAX and not player_name.endswith(" "): player_name+=" "
    elif len(player_name)<NAME_MAX:
        player_name+=lab.upper() if (not player_name or player_name.endswith(" ")) else lab.lower()
def release(n):
    if n and n not in fingers.values() and n not in mouseheld: held.discard(n)
def press(pos,fid=None):
    global state,jump_event,last_tap,outfit,diff
    now=pygame.time.get_ticks()
    if now-last_tap[0]<200 and abs(pos[0]-last_tap[1][0])+abs(pos[1]-last_tap[1][1])<24: return
    last_tap=(now,pos)
    if state=="menu":
        if M["story"].collidepoint(pos): state="levels"
        elif M["endless"].collidepoint(pos): start_run("endless",0)
        elif M["left"].collidepoint(pos): outfit=(outfit-1)%len(OUTFITS); save_settings()
        elif M["right"].collidepoint(pos): outfit=(outfit+1)%len(OUTFITS); save_settings()
        elif M["name"].collidepoint(pos): state="name"
        elif M["diff"].collidepoint(pos): diff=(diff+1)%len(DIFFS); save_settings()
        elif M["scores"].collidepoint(pos): state="scores"
        elif M["music"].collidepoint(pos): toggle_music()
    elif state=="name":
        for lab,r in KEYS:
            if r.collidepoint(pos): key_press(lab); break
    elif state=="levels":
        if BACK.collidepoint(pos): state="menu"
        for i,r in enumerate(CARDS):
            if r.collidepoint(pos) and i<unlocked: start_run("story",i)
    elif state=="scores":
        if BACK.collidepoint(pos): state="menu"
    elif state=="play":
        if UI["menu"].collidepoint(pos): go_menu()
        elif UI["music"].collidepoint(pos): toggle_music()
        else:
            n=hit_control(pos)
            if n:
                held.add(n)
                if fid is None: mouseheld.add(n)
                else: fingers[fid]=n
                if n=="jump": jump_event=True
    elif state in ("over","win"):
        if RB["menu"].collidepoint(pos): go_menu()
        elif RB["retry"].collidepoint(pos): restart()
        elif RB["next"].collidepoint(pos) and result.get("won") and mode=="story" and level<len(LEVELS)-1: start_run("story",level+1)

# ================================================================ drawing: player sprite
def build_sprite(o,moving,ph,air):
    spr=pygame.Surface((23,34),pygame.SRCALPHA)
    def R(c,x,y,w,h): pygame.draw.rect(spr,c,(x+2,y+6,w,h))
    SKIN=(240,200,160); SKS=(214,160,120); HAIR=(200,200,210); HI=(238,238,246); oid=o["id"]
    l1=l2=0
    if moving: l1,l2=(0,2) if ph==0 else (2,0)
    if air: l1=l2=1
    R(o["pant"],4,23,5,3-l1); R(o["shoe"],3,26-l1,7,2); R(o["pant"],10,23,5,3-l2); R(o["shoe"],10,26-l2,7,2)
    R(o["top"],3,14,13,10); R(o["topd"],3,21,13,2)
    if oid=="ninja": R(o["trim"],3,19,13,2)
    elif oid=="royal": R(GOLD,3,22,13,1); R(o["trim"],6,14,7,3)
    elif oid=="forest": R(o["trim"],7,14,5,2); R(o["topd"],3,19,13,1)
    else: R(o["trim"],7,14,5,2)
    R(o["btn"],9,17,1,1); R(o["btn"],9,20,1,1)
    if moving: a1,a2=(1,-1) if ph==0 else (-1,1)
    elif air: a1=a2=-2
    else: a1=a2=0
    for ax,ay in ((0,a1),(15,a2)):
        R(o["top"],ax,15+ay,4,7); R(o["topd"],ax,21+ay,4,2); R(o["hand"],ax,23+ay,4,2)
    R(HAIR,2,3,4,9); R(HAIR,4,1,10,3); R(HI,5,1,5,1)
    R(SKIN,5,4,11,9); R(SKIN,16,8,2,3); R(SKS,5,7,2,3)
    R(HAIR,11,6,4,1); R(BLACK,12,7,2,2); R(WHITE,12,7,1,1)
    R(HI,11,11,6,2); R(HAIR,6,12,10,3); R(HI,8,13,5,1)
    if oid=="ninja":
        R(o["topd"],2,3,4,9); R(o["topd"],4,1,11,4); R(o["topd"],6,10,10,5)
        R((200,50,60),3,5,14,2); sw=1 if ph==0 else 0
        R((200,50,60),0,6+sw,3,2); R((200,50,60),-1,8+sw,2,2); R(BLACK,12,7,2,2); R(WHITE,12,7,1,1)
    elif oid=="forest":
        R((40,100,52),0,1,19,2); R((62,140,72),4,-3,10,4); R((62,140,72),7,-6,6,3)
        R((230,60,70),13,-6,2,6); R((255,150,150),13,-6,2,2)
    elif oid=="royal":
        R(GOLD,4,-3,11,4); R(GOLD,4,-5,2,2); R(GOLD,8,-6,3,3); R(GOLD,13,-5,2,2); R((230,50,70),9,-2,1,1)
    elif oid=="wizard":
        HT=(60,70,170); R(HI,6,14,10,5); R(HAIR,8,19,6,1)
        R(HT,1,1,19,2); R(HT,4,-2,12,3); R(HT,6,-4,8,2); R(HT,8,-6,4,2); R(GOLD,9,-1,2,2); R(GOLD,12,-3,1,1)
        R(GOLD,5,19,1,1); R(GOLD,12,21,1,1); R(GOLD,8,23,1,1)
    elif oid=="pirate":
        for yy in (16,19,22): R(WHITE,3,yy,13,1)
        R(BLACK,1,0,19,3); R(BLACK,4,-3,12,4); R(WHITE,9,-2,3,2); R(BLACK,5,5,11,1); R(BLACK,11,6,5,4)
    elif oid=="chef":
        R(WHITE,3,0,13,3); R(WHITE,2,-4,15,5); R(WHITE,4,-6,11,3); R((215,215,228),3,2,13,1)
    elif oid=="cowboy":
        V=(110,70,40); R(V,4,15,3,9); R(V,12,15,3,9); R((90,55,30),1,1,19,2); R((140,95,55),4,-3,11,4); R(V,4,0,11,1)
    elif oid=="astronaut":
        R((150,155,170),-1,15,3,9); R(o["trim"],5,17,4,3); R((90,200,255),11,17,3,2)
        pygame.draw.ellipse(spr,(200,230,255,150),(3,3,19,19),2)
        pygame.draw.rect(spr,(255,255,255,210),(7,6,4,1)); pygame.draw.rect(spr,(255,255,255,210),(6,8,1,3))
    return spr
def draw_dying(s):
    spr=build_sprite(OUTFITS[outfit],False,0,True); t=dtime
    spr.fill((120,30,30) if (t<0.4 and int(t*20)%2) else (70,10,10),special_flags=pygame.BLEND_RGB_ADD)
    if face<0: spr=pygame.transform.flip(spr,True,False)
    if t>=0.4: spr=pygame.transform.rotate(spr,(t-0.4)*640*(-face))
    cx=int(p.centerx-cam); s.blit(spr,spr.get_rect(center=(cx,p.bottom-17)))
    if t<0.4:
        for k in range(3):
            a=anim_time*12+k*2.09; sx=cx+int(math.cos(a)*10); sy=p.y-6+int(math.sin(a)*3)
            pygame.draw.rect(s,GOLD,(sx-1,sy-1,3,3)); pygame.draw.rect(s,WHITE,(sx,sy,1,1))
def draw_player(s):
    moving=abs(vx)>25 and grounded
    ph=int(anim_time*12)%2 if moving else 0
    spr=build_sprite(OUTFITS[outfit],moving,ph,not grounded)
    if star_t>0: spr.fill([(110,0,0),(110,90,0),(0,110,0),(0,100,110),(60,0,110)][int(anim_time*20)%5],special_flags=pygame.BLEND_RGB_ADD)
    size=(23,34)
    if land_squash>0: size=(27,30)
    elif not grounded and vy<-150: size=(21,36)
    if size!=(23,34): spr=pygame.transform.scale(spr,size)
    if face<0: spr=pygame.transform.flip(spr,True,False)
    bob=int(math.sin(anim_time*16)*2) if moving else (int(math.sin(anim_time*4)) if grounded else 0)
    s.blit(spr,(int(p.centerx-cam-size[0]/2),p.bottom-size[1]+bob))
    label(s,player_name,int(p.centerx-cam),p.y+bob-22)

# ================================================================ drawing: world
def mountains(s,par,base,hgt,col,snow):
    off=int(cam*par); step=60; k0=off//step; pts=[(0,H)]; peaks=[]
    for j in range(-1,W//step+3):
        i=k0+j; x=j*step-(off%step); y=int(base-hgt*(0.55+0.45*math.sin(i*2.1)*math.cos(i*0.7)))
        pts.append((x,y)); peaks.append((x,y))
    pts.append((W+step,H)); pygame.draw.polygon(s,col,pts)
    if snow:
        for x,y in peaks:
            if y<base-hgt*0.8: pygame.draw.polygon(s,(240,246,255),[(x-9,y+11),(x,y),(x+9,y+11)])
def background(s):
    s.blit(sky,(0,0))
    og,oc=TH["orb"]; pygame.draw.circle(s,og,(W-42,34),22); pygame.draw.circle(s,oc,(W-42,34),15)
    if TH["rays"]:
        for k in range(8):
            a=anim_time*.3+k*math.pi/4; pygame.draw.line(s,(255,235,150),(W-42+int(math.cos(a)*24),34+int(math.sin(a)*24)),(W-42+int(math.cos(a)*30),34+int(math.sin(a)*30)),2)
    mountains(s,.06,GROUND-25,120,TH["mtn"],TH["snow"])
    if TH["birds"]:
        for i in range(3):
            bx=int((i*190+anim_time*18-cam*.08)%(W+80))-40; by=36+i*16+int(math.sin(anim_time*2+i)*4); w=int(math.sin(anim_time*10+i)*3)
            pygame.draw.lines(s,(60,70,90),False,[(bx-5,by-w),(bx,by+2),(bx+5,by-w)],1)
    cc=TH["cloud"]
    for i in range(6):
        x=int((i*105-cam*.15+anim_time*4)%(W+90))-45; y=30+(i%3)*19
        pygame.draw.rect(s,cc,(x+8,y+4,36,12)); pygame.draw.rect(s,cc,(x+16,y,20,20))
    mountains(s,.15,GROUND,70,TH["hill"],False)
    off=int(cam*.4)
    for j in range(-1,W//64+2):
        i=off//64+j; x=j*64-(off%64)
        if i%3==0: continue
        h=22+(i*37%5)*5
        pygame.draw.polygon(s,TH["spA"],[(x,GROUND-5),(x+10,GROUND-h),(x+21,GROUND-5)])
        pygame.draw.polygon(s,TH["spB"],[(x+3,GROUND-h//2),(x+10,GROUND-h-8),(x+18,GROUND-h//2)])
    if TH["embers"]:
        for i in range(14): pygame.draw.rect(s,(255,170,60),((i*47+int(anim_time*14*(1+i%3)))%W,int(H-(anim_time*30+i*31)%H),2,2))
    if TH["snowfall"]:
        for i in range(26): pygame.draw.rect(s,(255,255,255),(int(i*53+math.sin(anim_time+i)*8)%W,int(anim_time*28+i*37)%H,2,2))
def d_tree(s,x,v,sw):
    h=26+v*8
    pygame.draw.rect(s,(98,60,38),(x+9,GROUND-h,6,h)); pygame.draw.rect(s,(70,42,28),(x+13,GROUND-h,2,h))
    for i,(w,c) in enumerate(((28,(38,132,62)),(22,(52,158,76)),(14,(88,190,98)))):
        pygame.draw.rect(s,c,(x+12-w//2+sw*(i+1)//2,GROUND-h-8-i*7,w,12))
def d_house(s,x):
    wall,roof=TH["house"]; rd_=tuple(int(c*.8) for c in roof); sh=tuple(int(c*.85) for c in wall)
    pygame.draw.rect(s,wall,(x,GROUND-34,56,34)); pygame.draw.rect(s,sh,(x,GROUND-6,56,6))
    pygame.draw.rect(s,(130,80,60),(x+40,GROUND-62,8,16))
    pygame.draw.polygon(s,roof,[(x-5,GROUND-33),(x+28,GROUND-58),(x+61,GROUND-33)]); pygame.draw.rect(s,rd_,(x-5,GROUND-37,66,4))
    pygame.draw.rect(s,(110,70,45),(x+8,GROUND-22,14,22)); pygame.draw.rect(s,GOLD,(x+19,GROUND-11,2,2))
    pygame.draw.rect(s,(120,70,45),(x+32,GROUND-26,16,14)); pygame.draw.rect(s,(150,210,240),(x+34,GROUND-24,12,10)); pygame.draw.rect(s,(120,70,45),(x+39,GROUND-24,2,10))
    sm=int(anim_time*10)%12; pygame.draw.rect(s,(230,230,235),(x+42+sm//4,GROUND-66-sm,4,4))
def draw_decor(s):
    for x in houses:
        if -80<x-cam<W+80: d_house(s,int(x-cam))
    for k,wx,v in decor:
        x=int(wx-cam)
        if x<-40 or x>W+40: continue
        sw=int(round(math.sin(anim_time*1.5+wx*.07)*1.2))
        if k=="tree": d_tree(s,x,v,sw)
        elif k=="bush":
            pygame.draw.rect(s,(46,140,62),(x,GROUND-10,22,10)); pygame.draw.rect(s,(70,170,80),(x+4+sw,GROUND-14,14,8)); pygame.draw.rect(s,(255,120,140),(x+6,GROUND-9,2,2))
        elif k=="flower":
            col=((255,90,120),(255,230,80),(190,120,255))[v]
            pygame.draw.rect(s,DGREEN,(x+3,GROUND-8,1,8)); pygame.draw.rect(s,col,(x+1+sw,GROUND-11,5,4)); pygame.draw.rect(s,WHITE,(x+3+sw,GROUND-10,1,2))
        elif k=="rock":
            pygame.draw.rect(s,(120,124,138),(x,GROUND-8,16,8)); pygame.draw.rect(s,(150,154,168),(x+2,GROUND-10,10,4))
        elif k=="fence":
            for dx in (0,12,24): pygame.draw.rect(s,(170,120,75),(x+dx,GROUND-14,4,14))
            pygame.draw.rect(s,(190,140,90),(x,GROUND-11,28,3))
        elif k=="cactus":
            h=22+v*5; c=(56,140,76)
            pygame.draw.rect(s,c,(x+6,GROUND-h,6,h)); pygame.draw.rect(s,c,(x,GROUND-h//2-6,3,10)); pygame.draw.rect(s,c,(x,GROUND-h//2+2,8,3))
            pygame.draw.rect(s,c,(x+15,GROUND-h//2-10,3,12)); pygame.draw.rect(s,c,(x+10,GROUND-h//2,8,3)); pygame.draw.rect(s,(90,175,100),(x+7,GROUND-h,1,h))
        elif k=="dry":
            pygame.draw.rect(s,(150,110,60),(x,GROUND-8,3,8)); pygame.draw.rect(s,(150,110,60),(x+4,GROUND-12,2,12)); pygame.draw.rect(s,(170,130,70),(x+8,GROUND-7,3,7))
        elif k=="pillar":
            h=30+v*8; pygame.draw.rect(s,(215,190,140),(x+2,GROUND-h,12,h)); pygame.draw.rect(s,(190,165,115),(x+10,GROUND-h,4,h)); pygame.draw.rect(s,(235,215,165),(x,GROUND-h-3,16,4))
        elif k=="pine":
            h=30+v*8; pygame.draw.rect(s,(80,55,40),(x+10,GROUND-8,4,8))
            pygame.draw.polygon(s,TH["spA"],[(x,GROUND-8),(x+12,GROUND-h),(x+24,GROUND-8)]); pygame.draw.polygon(s,(245,250,255),[(x+6,GROUND-h+12),(x+12,GROUND-h),(x+18,GROUND-h+12)])
        elif k=="snowman":
            pygame.draw.circle(s,(245,248,255),(x+8,GROUND-6),6); pygame.draw.circle(s,(245,248,255),(x+8,GROUND-15),4)
            pygame.draw.rect(s,BLACK,(x+6,GROUND-17,1,1)); pygame.draw.rect(s,BLACK,(x+9,GROUND-17,1,1)); pygame.draw.rect(s,(255,140,40),(x+8,GROUND-15,4,1)); pygame.draw.rect(s,BLACK,(x+5,GROUND-22,6,3))
        elif k=="crystal":
            c=TH["crys"]; pygame.draw.polygon(s,c,[(x+4,GROUND),(x,GROUND-10-v*3),(x+4,GROUND-18-v*4),(x+8,GROUND-10-v*3),(x+8,GROUND)])
            pygame.draw.rect(s,WHITE,(x+3,GROUND-14-v*3,1,6))
        elif k=="torch":
            pygame.draw.rect(s,(90,60,40),(x+3,GROUND-22,3,22)); ht=4+int(abs(math.sin(anim_time*10+wx))*3)
            pygame.draw.rect(s,(255,150,40),(x+1,GROUND-28-ht,7,ht+6)); pygame.draw.rect(s,(255,230,100),(x+3,GROUND-26-ht//2,3,ht))
    cx=int(goal+95-cam)
    if -100<cx<W+20:
        cs=TH["castle"]; cl=tuple(min(255,c+25) for c in cs)
        pygame.draw.rect(s,cs,(cx,GROUND-80,70,80)); pygame.draw.rect(s,cl,(cx,GROUND-80,70,4))
        for dx in range(0,70,20): pygame.draw.rect(s,cs,(cx+dx,GROUND-90,12,10))
        pygame.draw.rect(s,(60,40,50),(cx+26,GROUND-32,18,32)); pygame.draw.rect(s,(60,40,50),(cx+26,GROUND-38,18,8))
        lit=(255,220,100) if int(anim_time*6)%2 else (255,180,70)
        pygame.draw.rect(s,lit,(cx+10,GROUND-60,8,10)); pygame.draw.rect(s,lit,(cx+52,GROUND-60,8,10))
def draw_water(s):
    a,b,hi=TH["liq"]; top=GROUND+14
    pygame.draw.rect(s,a,(0,top,W,H-top)); pygame.draw.rect(s,b,(0,top+14,W,H))
    for xx in range(-12,W,12):
        yy=top+int(math.sin(anim_time*3+(xx+cam)*.09)*2); pygame.draw.rect(s,hi,(xx,yy,8,2))
    if TH["lava"]:
        for i in range(5):
            bx=(i*110+int(anim_time*20*(i+1)))%W; pygame.draw.circle(s,hi,(bx,top+6+int(math.sin(anim_time*3+i)*3)),2)
def draw_platform(s,r):
    sx=int(r.x-cam)
    if sx+r.width<0 or sx>W: return
    if r.y>=GROUND:
        s.set_clip(pygame.Rect(sx,r.y,r.width,r.height)); base=r.x//TILE
        for c in range(max(0,(-sx)//TILE),min((r.width+TILE-1)//TILE,(W-sx)//TILE+1)):
            x=sx+c*TILE
            for row in range(min((r.height+TILE-1)//TILE,(H-r.y)//TILE+1)):
                t=grass_t[(base+c)%3] if row==0 else (dirt_t[(base+c+row)%3] if row<3 else stone_t)
                s.blit(t,(x,r.y+row*TILE))
        s.set_clip(None)
    else:
        for c in range(r.width//TILE): s.blit(plank_t,(sx+c*TILE,r.y))
def draw_block(s,r):
    sx=int(r.x-cam)
    if sx+r.width<0 or sx>W: return
    for c in range(r.width//TILE):
        for row in range(r.height//TILE): s.blit(brick_t,(sx+c*TILE,r.y+row*TILE))
    pygame.draw.rect(s,tuple(min(255,c+40) for c in TH["brick"][1]),(sx,r.y,r.width,2))
    if r.width>=48:
        for c in range(0,r.width,TILE): pygame.draw.rect(s,TH["brick"][0],(sx+c+3,r.y-5,8,5))
def draw_wall(s,r):
    x=int(r.x-cam)
    if x<-30 or x>W: return
    pygame.draw.rect(s,(70,40,110),(x,0,20,H))
    for yy in range(0,H+12,12): pygame.draw.rect(s,(150,90,220),(x+3,(yy+int(anim_time*30))%H,4,8))
    pygame.draw.rect(s,(200,150,255),(x+9,0,2,H))
def draw_scene():
    background(canvas); draw_decor(canvas); draw_water(canvas)
    for r in platforms: draw_platform(canvas,r)
    for r in blocks: draw_block(canvas,r)
def draw_flag(x,active):
    sx=int(x-cam); color=GOLD if active else (215,225,235); wv=int(math.sin(anim_time*5)*2)
    pygame.draw.rect(canvas,(100,72,52),(sx,GROUND-56,4,56)); pygame.draw.rect(canvas,color,(sx+4,GROUND-54,20+wv,13))
def draw_goal():
    if sand_got: return
    x=int(goal-cam)
    if x<-100 or x>W+40: return
    bob=int(math.sin(anim_time*3)*3)
    pygame.draw.rect(canvas,(96,100,120),(x,GROUND-10,64,10)); pygame.draw.rect(canvas,(120,126,146),(x+14,GROUND-24,36,14))
    pygame.draw.rect(canvas,(235,235,245),(x+6,GROUND-29,52,6)); pygame.draw.rect(canvas,(190,190,205),(x+6,GROUND-24,52,1))
    g=pygame.Surface((100,100),pygame.SRCALPHA); pygame.draw.circle(g,(255,230,120,int(55+25*math.sin(anim_time*4))),(50,50),48)
    canvas.blit(g,(x+32-50,GROUND-55-50+bob)); canvas.blit(SAND2,(x,GROUND-29-52+bob))
    for k in range(4):
        a=anim_time*2+k*1.57; sx=x+32+int(math.cos(a)*42); sy=GROUND-55+int(math.sin(a)*28)+bob
        pygame.draw.rect(canvas,WHITE,(sx-2,sy,5,1)); pygame.draw.rect(canvas,WHITE,(sx,sy-2,1,5))

# ================================================================ drawing: things
def draw_enemy(e):
    x,y=int(e["x"]-cam),int(e["y"]); t=e["t"]; d=e["d"]
    if t=="slime":
        y-=int(abs(math.sin(anim_time*7+e["x"]*.04))*2)
        pygame.draw.rect(canvas,(69,42,108),(x+3,y+5,19,14)); pygame.draw.rect(canvas,(145,86,207),(x+1,y+6,23,12)); pygame.draw.rect(canvas,(177,120,232),(x+4,y+6,16,3))
        pygame.draw.rect(canvas,WHITE,(x+5,y+8,5,5)); pygame.draw.rect(canvas,WHITE,(x+15,y+8,5,5))
        pygame.draw.rect(canvas,BLACK,(x+7,y+10,2,3)); pygame.draw.rect(canvas,BLACK,(x+17,y+10,2,3))
        pygame.draw.rect(canvas,BLACK,(x+5,y+19,6,3)); pygame.draw.rect(canvas,BLACK,(x+15,y+19,6,3)); pygame.draw.rect(canvas,(255,150,220),(x+10,y+15,5,2))
    elif t=="bat":
        up=math.sin(anim_time*14+e["x"])>0; wy=y-3 if up else y+4
        pygame.draw.rect(canvas,(60,30,90),(x,wy,8,5)); pygame.draw.rect(canvas,(60,30,90),(x+14,wy,8,5))
        pygame.draw.rect(canvas,(90,50,130),(x+2,wy+1,5,3)); pygame.draw.rect(canvas,(90,50,130),(x+15,wy+1,5,3))
        pygame.draw.rect(canvas,(45,25,70),(x+6,y+2,10,10)); pygame.draw.rect(canvas,(45,25,70),(x+6,y-1,3,4)); pygame.draw.rect(canvas,(45,25,70),(x+13,y-1,3,4))
        pygame.draw.rect(canvas,(255,70,70),(x+8,y+5,2,2)); pygame.draw.rect(canvas,(255,70,70),(x+12,y+5,2,2))
        pygame.draw.rect(canvas,WHITE,(x+9,y+9,1,2)); pygame.draw.rect(canvas,WHITE,(x+12,y+9,1,2))
    elif t=="spike":
        cx,cy=x+11,y+10; ang=e["x"]*0.12
        for k in range(8):
            a=ang+k*math.pi/4; ex=cx+int(math.cos(a)*11); ey=cy+int(math.sin(a)*11)
            pygame.draw.line(canvas,(200,200,215),(cx,cy),(ex,ey),2); pygame.draw.rect(canvas,RED,(ex-1,ey-1,3,3))
        pygame.draw.circle(canvas,(70,74,92),(cx,cy),7); pygame.draw.circle(canvas,(110,115,135),(cx-2,cy-2),3)
        pygame.draw.rect(canvas,(255,80,80),(cx-3,cy-1,2,2)); pygame.draw.rect(canvas,(255,80,80),(cx+1,cy-1,2,2))
    elif t=="frog":
        c=(60,170,70); cd=(40,120,50)
        pygame.draw.rect(canvas,cd,(x+1,y+5,18,9)); pygame.draw.rect(canvas,c,(x+2,y+5,16,8)); pygame.draw.rect(canvas,(200,240,160),(x+5,y+9,10,5))
        for ex in (x+2,x+13):
            pygame.draw.rect(canvas,c,(ex,y+2,5,5)); pygame.draw.rect(canvas,WHITE,(ex+1,y+3,3,3)); pygame.draw.rect(canvas,BLACK,(ex+2,y+4,1,2))
        pygame.draw.rect(canvas,cd,(x+6,y+8,8,1))
        if e["air"]: pygame.draw.rect(canvas,cd,(x-2,y+12,4,3)); pygame.draw.rect(canvas,cd,(x+18,y+12,4,3))
        else: pygame.draw.rect(canvas,cd,(x,y+13,5,3)); pygame.draw.rect(canvas,cd,(x+15,y+13,5,3))
    elif t=="ghost":
        a=90 if e["watched"] else 210; col=(235,240,255,a); g=pygame.Surface((20,24),pygame.SRCALPHA)
        pygame.draw.ellipse(g,col,(0,0,20,16)); pygame.draw.rect(g,col,(0,8,20,13))
        for k in range(4): pygame.draw.polygon(g,col,[(k*5,20),(k*5+5,20),(k*5+2,24)])
        ec=(30,30,60,min(255,a+40)); pygame.draw.rect(g,ec,(4,7,3,4)); pygame.draw.rect(g,ec,(13,7,3,4))
        if e["watched"]: pygame.draw.rect(g,ec,(8,15,4,1))
        else: pygame.draw.rect(g,ec,(7,14,6,4))
        canvas.blit(g,(x,y+int(math.sin(anim_time*4)*2)))
    elif t=="turret":
        pygame.draw.rect(canvas,(60,64,80),(x+2,y+14,20,8)); pygame.draw.rect(canvas,(96,100,120),(x+1,y+6,22,10)); pygame.draw.rect(canvas,(130,134,154),(x+1,y+6,22,2))
        bx=x+(16 if d>0 else -4); pygame.draw.rect(canvas,(40,42,56),(bx,y+8,12,6))
        pygame.draw.circle(canvas,(60,64,80),(x+12,y+8),6); pygame.draw.circle(canvas,(100,104,126),(x+10,y+6),2)
        if e["flash"]>0: pygame.draw.circle(canvas,(255,200,80),(bx+(13 if d>0 else -1),y+11),4)
    else:
        ch=e["st"]=="charge"; body=(150,100,70); dark=(105,68,48)
        pygame.draw.rect(canvas,dark,(x+2,y+3,24,12)); pygame.draw.rect(canvas,body,(x+3,y+2,22,11)); pygame.draw.rect(canvas,(90,56,40),(x+4,y,16,3))
        hx=x+(20 if d>0 else 0); pygame.draw.rect(canvas,dark,(hx,y+4,8,10))
        pygame.draw.rect(canvas,(255,60,60) if e["st"] in ("charge","windup") else BLACK,(hx+(4 if d>0 else 2),y+6,2,2))
        pygame.draw.rect(canvas,WHITE,(hx+(7 if d>0 else -1),y+10,2,4))
        lg=int(anim_time*(24 if ch else 10))%2
        pygame.draw.rect(canvas,dark,(x+4,y+13+lg,4,5-lg)); pygame.draw.rect(canvas,dark,(x+19,y+14-lg,4,4+lg))
def draw_powerup(pu):
    x=int(pu["x"]-cam)+8; y=int(pu["y"]+8+math.sin(anim_time*4+pu["x"])*3)
    if x<-20 or x>W+20: return
    if pu["k"]=="speed":
        pygame.draw.circle(canvas,(50,120,240),(x,y),9); pygame.draw.circle(canvas,WHITE,(x,y),9,1)
        pygame.draw.polygon(canvas,GOLD,[(x+1,y-7),(x-4,y+1),(x,y+1),(x-1,y+7),(x+4,y-2),(x,y-2)])
    elif pu["k"]=="jump":
        pygame.draw.circle(canvas,(60,190,90),(x,y),9); pygame.draw.circle(canvas,WHITE,(x,y),9,1)
        pygame.draw.polygon(canvas,WHITE,[(x,y-6),(x-5,y),(x-2,y),(x-2,y+5),(x+2,y+5),(x+2,y),(x+5,y)])
    else:
        pygame.draw.circle(canvas,GOLD,(x,y),11+int(anim_time*8)%2,1)
        pygame.draw.rect(canvas,(250,235,200),(x-3,y+1,6,7)); pygame.draw.rect(canvas,(230,50,60),(x-8,y-6,16,8))
        pygame.draw.rect(canvas,(230,50,60),(x-6,y-9,12,3)); pygame.draw.rect(canvas,WHITE,(x-5,y-5,3,3)); pygame.draw.rect(canvas,WHITE,(x+2,y-7,3,3))
def draw_boss(b):
    if b["dead"] or not b["active"]: return
    if b["hit"]>0 and frame%6<3: return
    x,y=int(b["x"]-cam),int(b["y"])
    if b["k"]=="golem":
        pygame.draw.rect(canvas,(90,95,110),(x+4,y+8,38,34)); pygame.draw.rect(canvas,(120,125,140),(x+6,y+10,34,6))
        pygame.draw.rect(canvas,(110,115,130),(x+12,y,22,16)); pygame.draw.rect(canvas,(90,95,110),(x,y+14,8,24)); pygame.draw.rect(canvas,(90,95,110),(x+38,y+14,8,24))
        pygame.draw.rect(canvas,(70,74,88),(x+6,y+42,14,4)); pygame.draw.rect(canvas,(70,74,88),(x+26,y+42,14,4))
        eye=(255,60,60) if int(anim_time*6)%2 else (255,150,80)
        pygame.draw.rect(canvas,eye,(x+16,y+6,5,4)); pygame.draw.rect(canvas,eye,(x+27,y+6,5,4))
        pygame.draw.rect(canvas,BLACK,(x+18,y+12,10,2)); pygame.draw.rect(canvas,(70,150,80),(x+8,y+20,8,4)); pygame.draw.rect(canvas,(70,150,80),(x+28,y+30,9,4))
        pygame.draw.rect(canvas,(60,64,78),(x+22,y+22,2,10))
    else:
        fl=int(math.sin(anim_time*10)*4)
        pygame.draw.polygon(canvas,(50,22,86),[(x+6,y+10),(x-12,y+4+fl),(x+4,y+24)]); pygame.draw.polygon(canvas,(50,22,86),[(x+42,y+10),(x+60,y+4+fl),(x+44,y+24)])
        pygame.draw.rect(canvas,(70,30,110),(x+6,y+10,36,30)); pygame.draw.rect(canvas,(70,30,110),(x+10,y+36,28,4))
        pygame.draw.rect(canvas,(35,20,60),(x+14,y+2,20,14)); pygame.draw.rect(canvas,(255,220,60),(x+18,y+8,4,3)); pygame.draw.rect(canvas,(255,220,60),(x+27,y+8,4,3))
        pygame.draw.rect(canvas,GOLD,(x+14,y-1,20,4))
        for dx in (14,22,30): pygame.draw.rect(canvas,GOLD,(x+dx,y-5,4,4))
        pygame.draw.rect(canvas,(120,60,180),(x+12,y+20,24,3))
def draw_button(r,text,col=(72,91,120),f=font):
    pygame.draw.rect(canvas,WHITE,r.inflate(4,4)); pygame.draw.rect(canvas,col,r)
    pygame.draw.rect(canvas,tuple(min(255,c+45) for c in col),(r.x,r.y,r.w,3)); pygame.draw.rect(canvas,(35,48,73),r,2)
    im=f.render(text,True,WHITE); canvas.blit(im,im.get_rect(center=r.center))
def draw_hud():
    pygame.draw.rect(canvas,(31,49,77),(7,7,120,34)); pygame.draw.rect(canvas,(90,120,170),(7,7,120,34),1)
    canvas.blit(STARI,(12,10)); txt(canvas,str(int(raw_now()*DIFFS[diff]["mult"])),30,12,small,GOLD)
    for i in range(lives): canvas.blit(HEART,(12+i*17,25))
    y0=46
    for lab,t,mx,col in (("SPEED",speed_t,6,(80,150,255)),("JUMP",jump_t,8,(90,220,110)),("IMMORTAL",star_t,STAR_TIME,GOLD)):
        if t>0:
            pygame.draw.rect(canvas,(31,49,77),(7,y0,100,14)); pygame.draw.rect(canvas,col,(9,y0+10,int(96*t/mx),3))
            txt(canvas,lab+" %.1f"%t,12,y0,small,WHITE); y0+=16
    head="ENDLESS  %dm"%(maxx//24) if mode=="endless" else "LEVEL %d: %s"%(level+1,LEVELS[level]["name"])
    label(canvas,head,W//2,8)
    for b in bosses:
        if b["active"] and not b["dead"]:
            bx=W//2-70
            pygame.draw.rect(canvas,(31,49,77),(bx-2,22,144,12)); pygame.draw.rect(canvas,(120,30,40),(bx,24,140,8))
            pygame.draw.rect(canvas,(240,70,80),(bx,24,int(140*b["hp"]/b["max"]),8))
            label(canvas,"ROCK GOLEM" if b["k"]=="golem" else "SHADOW KING",W//2,36)
    if banner_t>0:
        im=big.render(banner,True,GOLD); canvas.blit(big.render(banner,True,BLACK),im.get_rect(center=(W//2+1,71))); canvas.blit(im,im.get_rect(center=(W//2,70)))
    draw_button(UI["music"],"MUSIC "+("ON" if music_on else "OFF"),(60,140,80) if music_on else (140,60,60),small)
    draw_button(UI["menu"],"MENU",(72,91,120),small)
def draw_controls():
    for n,r in BUT.items(): canvas.blit(BTNS[(n,n in held)],r)
def shade_screen(a):
    sh=pygame.Surface((W,H),pygame.SRCALPHA); sh.fill((15,25,50,a)); canvas.blit(sh,(0,0))
def draw_results():
    shade_screen(200); r=result
    label(canvas,r["title"],W//2,8+MY,big,GOLD if r["won"] else (255,120,120))
    if r["won"] and mode=="story": canvas.blit(SAND,(W//2-158,6+MY)); canvas.blit(SAND,(W//2+126,6+MY))
    y=48+MY
    for lab,v in r["rows"]:
        txt(canvas,lab,W//2-120,y); im=font.render("+%d"%v,True,WHITE); canvas.blit(im,(W//2+120-im.get_width(),y)); y+=15
    txt(canvas,"Difficulty "+r["dname"],W//2-120,y,font,DIFFS[diff]["col"]); im=font.render("x%.2f"%r["mult"],True,WHITE); canvas.blit(im,(W//2+120-im.get_width(),y)); y+=17
    txt(canvas,"TOTAL",W//2-120,y,font,GOLD); im=font.render(str(r["total"]),True,GOLD); canvas.blit(im,(W//2+120-im.get_width(),y)); y+=15
    txt(canvas,"BEST  "+str(r["best"])+("   NEW BEST!" if r["new"] else ""),W//2-120,y,small,(160,255,160) if r["new"] else WHITE)
    draw_button(RB["retry"],"RETRY",(60,140,80)); draw_button(RB["menu"],"MENU")
    if r["won"] and mode=="story" and level<len(LEVELS)-1: draw_button(RB["next"],"NEXT LEVEL",(50,120,200))
def draw_menu():
    global cam
    cam=(anim_time*35)%700; draw_scene(); shade_screen(110)
    ty=12+MY+int(math.sin(anim_time*2)*2)
    for dx,dy in ((2,2),(-1,0),(1,0),(0,-1)):
        im=big.render("STAR HOP ADVENTURE",True,BLACK); canvas.blit(im,im.get_rect(center=(W//2+dx,ty+14+dy)))
    im=big.render("STAR HOP ADVENTURE",True,GOLD); canvas.blit(im,im.get_rect(center=(W//2,ty+14)))
    label(canvas,"Tap = hop    Hold = high jump",W//2,40+MY)
    o=OUTFITS[outfit]; bob=int(math.sin(anim_time*8)*2)
    spr=pygame.transform.scale(build_sprite(o,True,int(anim_time*8)%2,False),(69,102))
    canvas.blit(pygame.transform.scale(SHADOW,(60,14)),(85,160+MY)); canvas.blit(spr,(81,60+MY+bob))
    label(canvas,player_name,115,50+MY+bob,font); label(canvas,o["name"]+" ("+str(outfit+1)+"/"+str(len(OUTFITS))+")",115,172+MY,font,GOLD)
    draw_button(M["left"],"<",(72,91,120),big); draw_button(M["right"],">",(72,91,120),big)
    draw_button(M["name"],"NAME: "+player_name,(110,80,150))
    draw_button(M["story"],"STORY MODE",(50,160,80)); draw_button(M["endless"],"ENDLESS MODE",(60,110,200))
    D=DIFFS[diff]; draw_button(M["diff"],"DIFFICULTY: "+D["name"],D["col"])
    draw_button(M["scores"],"HIGH SCORES",(110,80,150))
    draw_button(M["music"],"MUSIC: "+("ON" if music_on else "OFF"),(60,140,80) if music_on else (140,60,60))
    label(canvas,"Lives: %d   Score x%.2f"%(D["lives"],D["mult"]),355,244+MY)
def draw_levels():
    global cam
    cam=(anim_time*25)%600; draw_scene(); shade_screen(150)
    label(canvas,"SELECT LEVEL",W//2,10+MY,big,GOLD); D=DIFFS[diff]
    label(canvas,"Difficulty: "+D["name"]+"  ("+str(D["lives"])+(" life)" if D["lives"]==1 else " lives)"),W//2,40+MY,font,D["col"])
    for i,r in enumerate(CARDS):
        lock=i>=unlocked; cfg=LEVELS[i]; col=THEMES[cfg["theme"]]["top"]
        pygame.draw.rect(canvas,WHITE,r.inflate(4,4)); pygame.draw.rect(canvas,(70,70,80) if lock else tuple(int(c*.7) for c in col),r)
        pygame.draw.rect(canvas,(35,48,73),r,2)
        label(canvas,"LEVEL %d"%(i+1),r.centerx,r.y+8,font,GOLD if not lock else (150,150,150))
        label(canvas,cfg["name"] if not lock else "LOCKED",r.centerx,r.y+28,font)
        if not lock: label(canvas,"BEST: %d"%best.get("L%d_%d"%(i,diff),0),r.centerx,r.y+49)
    draw_button(BACK,"BACK")
def draw_scores():
    global cam
    cam=(anim_time*25)%600; draw_scene(); shade_screen(170)
    label(canvas,"HIGH SCORES",W//2,8+MY,big,GOLD)
    for j,D in enumerate(DIFFS): label(canvas,D["name"],200+j*72,46+MY,font,D["col"])
    for i in range(len(LEVELS)+1):
        y=66+MY+i*26; name="LEVEL %d"%(i+1) if i<len(LEVELS) else "ENDLESS"
        txt(canvas,name,22,y,font,WHITE if i<unlocked or i==len(LEVELS) else (120,120,120))
        for j in range(len(DIFFS)):
            v=best.get(("L%d_%d"%(i,j)) if i<len(LEVELS) else ("E_%d"%j),0)
            label(canvas,str(v) if v else "-",200+j*72,y+2,font)
    draw_button(BACK,"BACK")
def draw_name():
    global cam
    cam=(anim_time*20)%500; draw_scene(); shade_screen(170)
    label(canvas,"ENTER YOUR NAME",W//2,6+MY,font,GOLD)
    fr=pygame.Rect(W//2-120,26+MY,240,30)
    pygame.draw.rect(canvas,WHITE,fr.inflate(4,4)); pygame.draw.rect(canvas,(20,30,55),fr)
    cur="_" if int(anim_time*2)%2 else " "
    im=big.render(player_name+cur,True,WHITE); canvas.blit(im,im.get_rect(center=fr.center))
    for lab,r in KEYS: draw_button(r,lab,(60,140,80) if lab=="OK" else ((150,70,70) if lab=="DEL" else (72,91,120)))

# ================================================================ enemy + boss logic
def update_enemy(e,dt):
    t=e["t"]; pcx=p.centerx; D=DIFFS[diff]
    if t in ("slime","spike","bat"):
        e["x"]+=e["d"]*e["speed"]*dt
        if e["x"]<e["lo"]: e["x"]=e["lo"]; e["d"]=1
        elif e["x"]>e["hi"]: e["x"]=e["hi"]; e["d"]=-1
        if t=="bat": e["y"]=e["by"]+math.sin(anim_time*3+e["lo"]*.1)*18
    elif t=="frog":
        e["cd"]-=dt
        if e["air"]:
            e["vy"]+=GRAVITY*dt; e["y"]+=e["vy"]*dt; e["x"]+=e["d"]*e["speed"]*dt
            if e["y"]>=GROUND-e["h"]: e["y"]=float(GROUND-e["h"]); e["air"]=False; e["cd"]=random.uniform(.6,1.4)
        elif e["cd"]<=0:
            if abs(pcx-e["x"])<240: e["d"]=1 if pcx>e["x"] else -1
            elif e["x"]<e["lo"]: e["d"]=1
            elif e["x"]>e["hi"]: e["d"]=-1
            e["air"]=True; e["vy"]=-300
    elif t=="ghost":
        dx=pcx-(e["x"]+e["w"]/2); dy=p.centery-(e["y"]+e["h"]/2); dist=max(1,math.hypot(dx,dy))
        e["watched"]=(face>0 and dx>0) or (face<0 and dx<0)
        if dist<280 and not e["watched"]:
            e["x"]+=dx/dist*e["speed"]*dt*1.6; e["y"]+=dy/dist*e["speed"]*dt*1.6
            e["y"]=clamp(e["y"],GROUND-140,GROUND-e["h"])
    elif t=="turret":
        e["flash"]=max(0,e["flash"]-dt)
        if abs(pcx-e["x"])<290:
            e["d"]=1 if pcx>e["x"] else -1; e["cd"]-=dt
            if e["cd"]<=0:
                e["cd"]=2.4/D["ps"]; e["flash"]=.15; sfx("shoot")
                projectiles.append({"k":"ball","x":e["x"]+12+e["d"]*16,"y":e["y"]+11,"vx":e["d"]*125*D["ps"],"vy":0,"w":9,"h":9})
    else:
        e["tm"]+=dt; dx=pcx-e["x"]
        if e["st"]=="walk":
            e["x"]+=e["d"]*e["speed"]*dt
            if e["x"]<e["lo"]: e["d"]=1
            elif e["x"]>e["hi"]: e["d"]=-1
            if abs(dx)<160 and abs(p.bottom-(e["y"]+e["h"]))<40: e["st"]="windup"; e["tm"]=0; e["d"]=1 if dx>0 else -1
        elif e["st"]=="windup":
            if e["tm"]>.45: e["st"]="charge"; e["tm"]=0
        elif e["st"]=="charge":
            e["x"]=clamp(e["x"]+e["d"]*190*D["es"]*dt,e["lo"]-90,e["hi"]+90)
            if e["tm"]>1.0: e["st"]="rest"; e["tm"]=0
        elif e["tm"]>.8: e["st"]="walk"; e["tm"]=0
def waves(b):
    cx=b["x"]+b["w"]/2
    for d in (-1,1): projectiles.append({"k":"wave","x":cx,"y":GROUND-8,"vx":d*140*DIFFS[diff]["ps"],"vy":0,"w":14,"h":8})
def update_boss(b,dt):
    global vy,grounded,py,shake,jumping
    if b["dead"] or not b["active"]: return
    f=1+(b["max"]-b["hp"])*0.12; ps=DIFFS[diff]["ps"]
    b["hit"]=max(0,b["hit"]-dt); b["t"]+=dt; pcx=p.centerx
    if b["k"]=="golem":
        gy=GROUND-b["h"]; b["vy"]+=GRAVITY*dt; b["y"]+=b["vy"]*dt
        if b["y"]>=gy:
            b["y"]=float(gy); b["vy"]=0
            if b["air"]: b["air"]=False; shake=.35; waves(b); burst(b["x"]+b["w"]/2,GROUND,(200,190,170),10,3,90,60)
            d=1 if pcx>b["x"]+b["w"]/2 else -1
            b["x"]+=d*55*f*ps*dt
            if b["t"]>2.2/(f*ps): b["vy"]=-440; b["vx"]=d*150*f; b["air"]=True; b["t"]=0
        else: b["x"]+=b["vx"]*dt
    else:
        if b["st"]=="hover":
            b["x"]+=b["d"]*85*f*ps*dt
            if b["x"]<b["lo"]+30: b["d"]=1
            elif b["x"]>b["hi"]-30-b["w"]: b["d"]=-1
            b["y"]=GROUND-120+math.sin(anim_time*3)*8; b["fire"]-=dt
            if b["fire"]<=0:
                b["fire"]=1.5/(f*ps); sx=b["x"]+b["w"]/2; sy=b["y"]+b["h"]/2
                dx=pcx-sx; dy=p.centery-sy; dist=max(1,math.hypot(dx,dy)); sp=(140+(f-1)*60)*ps
                projectiles.append({"k":"fire","x":sx,"y":sy,"vx":dx/dist*sp,"vy":dy/dist*sp,"w":8,"h":8})
            b["dive"]+=dt
            if b["dive"]>5/ps: b["st"]="dive"; b["tx"]=pcx-b["w"]/2; b["dive"]=0
        elif b["st"]=="dive":
            b["x"]+=clamp(b["tx"]-b["x"],-180*dt,180*dt); b["y"]+=260*dt
            if b["y"]>=GROUND-b["h"]: b["y"]=float(GROUND-b["h"]); b["st"]="rest"; b["rt"]=0; shake=.35; waves(b)
        elif b["st"]=="rest":
            b["rt"]+=dt
            if b["rt"]>1.6: b["st"]="rise"
        else:
            b["y"]-=140*dt
            if b["y"]<=GROUND-120: b["st"]="hover"
    b["x"]=clamp(b["x"],b["lo"]+20,b["hi"]-20-b["w"])
    br=pygame.Rect(int(b["x"]),int(b["y"]),b["w"],b["h"])
    if p.colliderect(br) and b["hit"]<=0:
        stomp=vy>0 and p.bottom-br.top<18
        if stomp or star_t>0:
            b["hp"]-=1; b["hit"]=1.0; stats["kill_pts"]+=25; sfx("boss"); burst(br.centerx,br.centery,(255,230,120),14,3)
            if stomp: vy=-JUMP*.85; grounded=False; p.bottom=br.top; py=float(p.y); jumping=False
            else: b["x"]+=12 if br.centerx>pcx else -12
            if b["hp"]<=0:
                b["dead"]=True; stats["bosses"]+=1; projectiles.clear(); burst(br.centerx,br.centery,(255,200,80),30,3,120,140)
                say("BOSS DEFEATED!" if b["k"]=="golem" else "THE KING FALLS!")
        elif invuln<=0 and star_t<=0: hurt()

# ================================================================ main loop
apply_music()
running=True
while running:
    dt=min(clock.tick(60)/1000,0.033); frame+=1; jump_event=False
    anim_time+=dt
    land_squash=max(0.0,land_squash-dt); jump_buffer=max(0.0,jump_buffer-dt); coyote_time=max(0.0,coyote_time-dt)
    shake=max(0.0,shake-dt); banner_t=max(0.0,banner_t-dt); cam_smooth=max(0.0,cam_smooth-dt)
    for ev in pygame.event.get():
        if ev.type==pygame.QUIT: running=False
        elif ev.type==pygame.KEYDOWN:
            if state=="name":
                if ev.key==pygame.K_BACKSPACE: player_name=player_name[:-1]
                elif ev.key in (pygame.K_RETURN,pygame.K_ESCAPE): finish_name()
            elif ev.key==pygame.K_ESCAPE:
                if state=="menu": running=False
                else: go_menu()
            elif state=="menu" and ev.key==pygame.K_RETURN: state="levels"
            elif state=="play" and ev.key in (pygame.K_SPACE,pygame.K_UP,pygame.K_w): jump_event=True
            elif state in ("over","win") and ev.key==pygame.K_r: restart()
        elif ev.type==pygame.TEXTINPUT and state=="name":
            for ch in ev.text:
                if ch.isprintable() and len(player_name)<NAME_MAX: player_name+=ch
        elif ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1:
            if getattr(ev,"touch",False) and finger_seen: continue
            press(to_logical(ev.pos),None)
        elif ev.type==pygame.MOUSEBUTTONUP and ev.button==1:
            ns=list(mouseheld); mouseheld.clear()
            for n in ns: release(n)
        elif ev.type==pygame.FINGERDOWN:
            finger_seen=True; press((int(ev.x*W),int(ev.y*H)),ev.finger_id)
        elif ev.type==pygame.FINGERMOTION and state=="play" and ev.finger_id in fingers:
            n=hit_control((int(ev.x*W),int(ev.y*H))); old=fingers[ev.finger_id]
            if n!=old and n in ("left","right") and old in ("left","right"):
                fingers[ev.finger_id]=n; held.add(n); release(old)
        elif ev.type==pygame.FINGERUP:
            n=fingers.pop(ev.finger_id,None); release(n)
    jump_pressed=jump_event
    keys=pygame.key.get_pressed()
    left="left" in held or keys[pygame.K_LEFT] or keys[pygame.K_a]
    right="right" in held or keys[pygame.K_RIGHT] or keys[pygame.K_d]
    jdown="jump" in held or keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]
    if state!="play": left=right=jdown=False
    if jdown and not jump_prev: jump_pressed=True
    if jump_pressed: jump_buffer=0.16
    jump_prev=jdown

    walls_now=[w for b in bosses if b["active"] and not b["dead"] for w in boss_walls(b)]
    solid_now=platforms+blocks+walls_now
    if state=="play":
        level_time+=dt
        speed_t=max(0,speed_t-dt); jump_t=max(0,jump_t-dt); star_t=max(0,star_t-dt)
        spd=SPEED*(1.5 if speed_t>0 else 1); jb=1.28 if jump_t>0 else 1
        if left and not right: vx=-spd; face=-1
        elif right and not left: vx=spd; face=1
        else: vx*=.72; vx=0 if abs(vx)<5 else vx
        if grounded: coyote_time=0.10
        if jump_buffer>0 and (grounded or coyote_time>0):
            vy=-JUMP_FULL*jb; grounded=False; coyote_time=0.0; jump_buffer=0.0; jumping=True; sfx("jump")
            burst(p.centerx,p.bottom,(225,215,190),4,2,40,30)
            if jump_t>0: burst(p.centerx,p.bottom,(110,240,130),8)
        if jumping and not jdown and vy<-JUMP_MIN*jb: vy=-JUMP_MIN*jb
        px+=vx*dt; p.x=int(px)
        for r in solid_now:
            if p.colliderect(r):
                if grounded and vx!=0 and r in blocks and 0<p.bottom-r.top<=26:
                    p.bottom=r.top; py=float(p.y); continue
                if vx>0: p.right=r.left
                elif vx<0: p.left=r.right
                px=float(p.x)
        old_bottom=p.bottom; vy+=GRAVITY*dt; py+=vy*dt; p.y=int(py); grounded=False
        for r in solid_now:
            if p.colliderect(r):
                if vy>0 and old_bottom<=r.top+8:
                    if vy>250: burst(p.centerx,r.top,(225,215,190),6,2,60,40)
                    p.bottom=r.top; py=float(p.y); vy=0; grounded=True; land_squash=0.10; jumping=False
                    if mode=="endless" and r.y>=GROUND and r.bottom>GROUND+40: spawn=float(clamp(p.x-10,r.left+5,r.right-30))
                elif vy<0:
                    p.top=r.bottom; py=float(p.y); vy=0
        lb=cam_floor if mode=="endless" else 0
        if p.left<lb: p.left=int(lb); px=float(p.x)
        if not splashed and p.centery>GROUND+16 and vy>0:
            splashed=True; sfx("stomp"); burst(p.centerx,GROUND+14,TH["liq"][2],16,3,90,170)
        if p.top>H+90: fall_death()
        invuln=max(0,invuln-dt)
        if mode=="endless": maxx=max(maxx,p.centerx)
        if grounded and abs(vx)>25 and frame%6==0: burst(p.centerx-face*6,p.bottom-1,(225,215,190),1,2,15,25,200,.3)
        if speed_t>0 and abs(vx)>25 and frame%3==0: burst(p.centerx-face*8,p.centery,(110,170,255),1,3,10,10,0,.3)
        if star_t>0 and frame%2==0: burst(p.centerx,p.centery,(255,230,110),1,2,40,40)
        for c in coins:
            if not c["got"] and p.colliderect(c["r"]):
                c["got"]=True; stats["coins"]+=1; sfx("coin"); burst(c["r"].centerx,c["r"].centery,GOLD,5,2,40,60)
        for pu in powerups:
            if not pu["got"] and p.colliderect(pygame.Rect(pu["x"],pu["y"],16,16)):
                pu["got"]=True; stats["power"]+=1; burst(pu["x"]+8,pu["y"]+8,GOLD,14,3); sfx("power")
                if pu["k"]=="speed": speed_t=6.0; say("SPEED BOOST!",1.4)
                elif pu["k"]=="jump": jump_t=8.0; say("JUMP BOOST!",1.4)
                else: star_t=STAR_TIME; say("IMMORTAL!",1.4)
        for i,x in enumerate(checkpoints):
            if p.colliderect(pygame.Rect(x,GROUND-60,28,60)) and not cp_on[i]:
                cp_on[i]=True; spawn=float(x+18); stats["cps"]+=1
        for b in bosses:
            if not b["dead"] and not b["active"] and p.centerx>=b["trig"]:
                b["active"]=True; cam_smooth=1.0; say("ROCK GOLEM!" if b["k"]=="golem" else "SHADOW KING!")
            update_boss(b,dt)
        lo_c,hi_c=(cam_floor,10**9) if mode=="endless" else (0,WORLD-W)
        for b in bosses:
            if b["active"] and not b["dead"]: lo_c,hi_c=b["lo"],b["hi"]-W
        target=clamp(p.centerx-W*.38,lo_c,hi_c)
        cam=target if cam_smooth<=0 else cam+(target-cam)*min(1,dt*6)
        if mode=="endless":
            cam_floor=max(cam_floor,cam)
            while gen_x<cam+W+700: gen_chunk()
            if frame%60==0: cull(cam-500)
        for e in enemies:
            if not e["alive"] or abs(e["x"]-p.centerx)>W+100: continue
            update_enemy(e,dt)
            er=pygame.Rect(int(e["x"]),int(e["y"]),e["w"],e["h"])
            if p.colliderect(er):
                if star_t>0:
                    kill_enemy(e); sfx("stomp"); burst(er.centerx,er.centery,(255,230,110),10,3)
                elif e["t"]!="spike" and vy>0 and p.bottom-er.top<15:
                    kill_enemy(e); vy=-JUMP*.62; grounded=False; jumping=False; p.bottom=er.top; py=float(p.y)
                    sfx("stomp"); burst(er.centerx,er.centery,(200,160,255),10,3)
                elif invuln<=0: hurt()
        for pr in projectiles[:]:
            pr["x"]+=pr["vx"]*dt; pr["y"]+=pr["vy"]*dt
            rr=pygame.Rect(int(pr["x"]-pr["w"]/2),int(pr["y"]-pr["h"]/2),pr["w"],pr["h"])
            gone=pr["x"]<cam-50 or pr["x"]>cam+W+50 or (pr["k"]=="fire" and pr["y"]>GROUND-2)
            if p.colliderect(rr):
                gone=True
                if invuln<=0 and star_t<=0: hurt()
            if gone: projectiles.remove(pr)
        if mode=="story" and bosses and bosses[-1]["dead"] and not sand_got and state=="play" and p.colliderect(pygame.Rect(goal-8,GROUND-90,80,90)):
            sand_got=True; win_timer=1.3; sfx("win"); say("YUMMY SANDWICH!",1.6)
            for _ in range(4): burst(goal+32,GROUND-50,(255,220,100),10,3,130,170)
        if sand_got and state=="play":
            win_timer-=dt
            if frame%3==0: burst(p.centerx,p.top,(255,230,120),2,3,80,80)
            if win_timer<=0: state="win"
    if state=="dying":
        dtime+=dt
        if dtime>=0.4:
            if dtime-dt<0.4: vy=-330.0
            vy+=GRAVITY*dt; py+=vy*dt; p.y=int(py)
        if dtime>1.8: state="over"
    for q in parts[:]:
        q[0]+=q[2]*dt; q[1]+=q[3]*dt; q[3]+=q[7]*dt; q[4]-=dt
        if q[4]<=0: parts.remove(q)
    if state!=prev_state:
        if state in ("win","over") and prev_state in ("play","dying"):
            calc_result(state=="win"); sfx("win" if state=="win" else "over")
        prev_state=state

    if state=="menu": draw_menu()
    elif state=="name": draw_name()
    elif state=="levels": draw_levels()
    elif state=="scores": draw_scores()
    else:
        draw_scene()
        for r in walls_now: draw_wall(canvas,r)
        for i,x in enumerate(checkpoints): draw_flag(x,cp_on[i])
        if mode=="story": draw_goal()
        for c in coins:
            if not c["got"] and -20<c["r"].x-cam<W+20:
                x=int(c["r"].centerx-cam); y=c["r"].centery+int(math.sin(anim_time*5+x*.08)*2)
                im=COIN_FR[int(anim_time*8+c["r"].x*.05)%len(COIN_FR)]
                canvas.blit(im,(x-im.get_width()//2,y-8))
                if frame%24<4: pygame.draw.rect(canvas,WHITE,(x+6,y-8,2,2))
        for pu in powerups:
            if not pu["got"]: draw_powerup(pu)
        for e in enemies:
            if e["alive"] and -40<e["x"]-cam<W+40: draw_enemy(e)
        for b in bosses: draw_boss(b)
        for pr in projectiles:
            x,y=int(pr["x"]-cam),int(pr["y"])
            if pr["k"]=="fire":
                pygame.draw.circle(canvas,(255,120,30),(x,y),5); pygame.draw.circle(canvas,(255,230,100),(x,y),2)
            elif pr["k"]=="ball":
                pygame.draw.circle(canvas,(30,32,44),(x,y),5); pygame.draw.circle(canvas,(90,94,116),(x-1,y-1),2)
            else:
                pygame.draw.rect(canvas,(255,140,40),(x-7,y-4,14,8)); pygame.draw.rect(canvas,(255,230,100),(x-4,y-2,8,3))
        gy=None
        for r in solid_now:
            if r.left<p.right and r.right>p.left and r.top>=p.bottom-2 and (gy is None or r.top<gy): gy=r.top
        if gy is not None and gy-p.bottom<120 and state!="dying":
            sw=max(8,22-(gy-p.bottom)//6); canvas.blit(pygame.transform.scale(SHADOW,(sw,5)),(int(p.centerx-cam-sw/2),gy-2))
        if state=="dying": draw_dying(canvas)
        elif invuln<=0 or frame%8<4: draw_player(canvas)
        for q in parts:
            sz=q[6]; pygame.draw.rect(canvas,q[5],(int(q[0]-cam),int(q[1]),sz,sz))
        draw_hud()
        if state=="play": draw_controls()
        elif state in ("over","win"): draw_results()
    ox=oy=0
    if shake>0: ox=random.randint(-4,4); oy=random.randint(-3,3); screen.fill((0,0,0))
    screen.blit(pygame.transform.scale(canvas,(SW,SH)),(ox,oy)); pygame.display.flip()
pygame.quit()
sys.exit()
