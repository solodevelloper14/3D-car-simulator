from ursina import *
from math import sqrt, radians, tan, degrees, atan, atan2
import json

app = Ursina(icon="icon.ico")
window.title = 'Car Simulator'
window.borderless = False
window.exit_button.visible = False
window.entity_counter.enabled = False
window.collider_counter.enabled = False
window.cog_button.enabled = False

dots=[tuple(p) for p in json.load(open("track.json"))]
road_width = 14
# Земля
Entity(model='plane', scale=4000, texture='grass',
       texture_scale=(4000,4000), color=rgb(0, 130, 0), y=-0.1)
asphalt_texture = load_texture('textures/asphalt.jpg', filtering='mipmap')
finish_texture=load_texture('textures/finish.png')
(fx, fz), (fx1, fz1) = dots[0], dots[1]
finish=Entity(model='quad',texture=finish_texture,position=(fx, 0.02, fz),rotation=(90, degrees(atan2(fx1 - fx, fz1 - fz)), 0),scale=(road_width, 4),)   #повернута вздовж дороги
# Машина
car = Entity()
# кузов
Entity(parent=car, model='cube', color=color.azure,
       scale=(1.8, 0.6, 4.5), y=0.45, collider='box')
# кабіна
Entity(parent=car, model='cube', color=color.light_gray,
       scale=(1.6, 0.5, 2.2), y=1.025, z=-0.2)
STEER_DEADZONE = 0.1
TRIGGER_DEADZONE = 0.02
def apply_deadzone(v, dz):
    if abs(v) <= dz:
        return 0
    sign = 1 if v > 0 else -1
    return sign * (abs(v) - dz) / (1 - dz)

def analyze_input():
    # клавіатура
    kb_steer = held_keys['d'] - held_keys['a']
    kb_throttle = held_keys['w']
    kb_brake = held_keys['s']

    #контроллер
    pad_steer = apply_deadzone(held_keys['gamepad left stick x'], STEER_DEADZONE)
    pad_steer = (1 if pad_steer > 0 else -1) * abs(pad_steer) ** 1.5
    pad_throttle = apply_deadzone(held_keys['gamepad right trigger'], TRIGGER_DEADZONE)
    pad_brake = apply_deadzone(held_keys['gamepad left trigger'], TRIGGER_DEADZONE)

    steer = kb_steer if abs(kb_steer) > abs(pad_steer) else pad_steer
    throttle = max(kb_throttle, pad_throttle)
    brake = max(kb_brake, pad_brake)
    return steer, throttle, brake
# траса
n=len(dots)
vert,uvs,triangles=[],[],[]
dist=0
title=5
start = n - 15 
(x0, z0), (x1, z1) = dots[start], dots[start + 1]
car.position = (x0, 0, z0)
car.rotation_y = degrees(atan2(x1 - x0, z1 - z0))
for i in range(n+1):
    x,z=dots[i%n]
    px,pz=dots[(i-1)%n]
    nx,nz=dots[(i+1)%n]
    dx, dz = nx - px, nz - pz
    l = sqrt(dx * dx + dz * dz)
    dx, dz = dx / l, dz / l
    ox,oz=dz*road_width/2, -dx*road_width/2
    vert.append((x+ox, 0, z+oz))
    vert.append((x-ox, 0, z-oz))
    uvs.append((0,dist/title))
    uvs.append((1,dist/title))
    dist += sqrt((nx - x) ** 2 + (nz - z) ** 2)
for i in range(n):
    a, b = 2 * i, 2 * i + 1
    c, d = 2 * i + 2, 2 * i + 3
    triangles.append((a, b, d))
    triangles.append((a, d, c))
road = Entity(model=Mesh(vertices=vert, triangles=triangles, uvs=uvs, mode='triangle'), texture=asphalt_texture, double_sided=True)
# Камера
camera.parent = car
camera.position = (0, 2.7, -7.5)
camera.rotation = (14, 0, 0)
camera.fov=70
#editor_camera = EditorCamera()
#camera.parent = None
#camera.position = (0, 350, 0)
#camera.rotation = (90, 0, 0)
speed = 0
MAX_STEER = 30
GRIP_DRY_TARMAC=1
GRIP_DRY_GRASS=0.4
ROLL_TARMAC=0.5
ROLL_GRASS = 1.5
GRASS_DRAG = 0.13
MAX_FACTOR=1.1
VMAX = 70
DOWNFORCE=0.0003
DRAG =0.001
CORNER_DRAG=0.07
TC_LIMIT  = 0.85
ABS_LIMIT = 0.90
def locate(x, z, c=None):
    min_dist=1e9
    best_i=0
    best_t=0
    if c is None:
        partsnow = range(n)
    else:
        count = min(n, 30)
        first_offset = -(count // 2)
        partsnow = (
            (c + offset) % n
            for offset in range(first_offset, first_offset + count)
        )
    for i in partsnow:
        ax,az=dots[i]
        bx,bz=dots[(i+1)%n]
        abx,abz=bx-ax,bz-az
        apx,apz=x-ax,z-az
        t=(apx*abx+apz*abz)/(abx**2+abz**2)
        t=clamp(t,0,1)
        cx,cz=ax+t*abx,az+t*abz
        d=sqrt((x-cx)**2+(z-cz)**2)
        if d<min_dist:
            min_dist=d
            best_i=i
            best_t=t
    return min_dist, best_i, best_t
def surface(road_dist):
    if road_dist < road_width / 2:
        return GRIP_DRY_TARMAC, ROLL_TARMAC
    return GRIP_DRY_GRASS, ROLL_GRASS
speedometer = Text(text="0 km/h", position=window.bottom_right + Vec2(-1.25, 0.08),scale=2, color=color.white)
progress_t=Text(text="0", position=window.bottom_left+ Vec2(0.03,0.08), scale=2, color=color.white)
_, seg0, t0 = locate(car.x, car.z)
last_segment = seg0
last_progress = seg0 + t0
total = last_progress
laps = 0
max_index = 0
race_time = 0
lap_start = 0
best_time = None
lap_text = Text(text="", position=window.top_left + Vec2(0.02, -0.02), scale=2)
lap_valid=True
v_side=0
def fmt(sec):
    m, s = divmod(sec, 60)
    return f"{int(m)}:{s:06.3f}"
def calculate_omega(speed, steer,surface_grip):
    speedv=max(abs(speed), 0.1)
    
    limit_angle=MAX_FACTOR*atan(surface_grip*9.81*2.7/speedv**2)
    max_angle = min(radians(MAX_STEER), limit_angle)
    omega_steer=speed*tan(steer*max_angle)/2.7
    return omega_steer
def update():
    global speed, last_progress, total, laps, lap_start, race_time, max_index,best_time, last_segment, lap_valid,v_side
    steer, throttle, brake = analyze_input()
    road_dist, seg, t = locate(car.x, car.z, last_segment)
    last_segment = seg
    surface_grip, rolling = surface(road_dist)
    if road_dist > road_width / 2:
        rolling += GRASS_DRAG * abs(speed)
    surface_grip*=1+DOWNFORCE*speed**2
    a_long=0
    if throttle > 0:
        a_long=min(12 * (1 - speed/VMAX) * throttle,surface_grip * 9.81*TC_LIMIT)
        acceleration=a_long-rolling
        if speed <= 0:
            acceleration = max(0, acceleration)        
        speed+=acceleration*time.dt
    elif brake > 0:
        a_long=surface_grip*9.81 * brake*ABS_LIMIT
        speed -=a_long* time.dt
    else:
        k = rolling + speed**2 * DRAG
        if abs(speed) < k * time.dt:
            speed = 0
        else:
            speed -= k * time.dt * (1 if speed > 0 else -1)
    speed = clamp(speed, -8, VMAX)
    lat_grip = sqrt(max((surface_grip * 9.81)**2 - a_long**2, 0))
    omega = calculate_omega(speed, steer,lat_grip/9.81)
    speed-=CORNER_DRAG*abs(speed*omega)*time.dt*(1 if speed>0 else -1)
    car.rotation_y += degrees(omega) * time.dt
    dangle=omega*time.dt
    max_ad = lat_grip * time.dt
    if road_dist > road_width / 2:
        max_ad += (ROLL_GRASS + GRASS_DRAG * abs(v_side)) * time.dt
    v_side-=speed*dangle
    speed+=v_side*dangle
    if abs(v_side)<=max_ad:
        v_side=0
    else: v_side-=max_ad*(1 if v_side > 0 else -1)
    car.position += car.forward*speed * time.dt + car.right*v_side*time.dt
    speedometer.text = f'{abs(speed) * 3.6:.0f} km/h   lat {lat_grip / (surface_grip * 9.81) * 100:.0f}%'
    progress=t+seg
    progress_t.text=f"{progress:.1f}"
    delta=progress-last_progress
    if delta > n * 0.75:
        delta -= n
    elif delta < -n * 0.75:
        delta += n
    elif abs(delta) > n * 0.25:#блокування перескоку
        delta = 0
    total += delta
    last_progress = progress
    race_time+=time.dt
    index=int(total//n)
    if road_dist>road_width/2+0.9:
        lap_valid=False
    if index > max_index:
        max_index = index
        if max_index >= 2:
            lap_time = race_time - lap_start
            if lap_valid and (best_time is None or lap_time < best_time):
                best_time = lap_time
        lap_start = race_time
        lap_valid=True
    cur = race_time - lap_start if max_index >= 1 else 0
    lap_text.text = f"Коло {max(max_index, 1)}   {fmt(cur)}"
    lap_text.color = color.red if not lap_valid else color.white
    if best_time is not None:
        lap_text.text += f"\nКраще {fmt(best_time)}"
app.run()
