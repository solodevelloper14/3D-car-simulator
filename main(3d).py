from ursina import *
from ursina.shaders import basic_lighting_shader
from math import sqrt, radians, degrees, atan, atan2,sin,cos,pi
import json
from panda3d.core import MaterialAttrib, TransparencyAttrib

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
car.collider = BoxCollider(car, center=(0, 0.5, 0), size=(1.9, 1, 4.6))
body = Entity(parent=car, model='models/porsche_911_gt3/scene.gltf', rotation_y=180)
body.shader=basic_lighting_shader
#Освітлення
sun = DirectionalLight()
sun.look_at(Vec3(1, -1, -1))
AmbientLight(color=color.rgba(120, 120, 120, 0.5))
KEEP = {'INT_Metal_Rollbar.001'}
interior = []
for gnp in body.model.find_all_matches('**/+GeomNode'):
    gn = gnp.node()
    if gn.get_num_geoms() == 0:
        continue
    attrib = gn.get_geom_state(0).get_attrib(MaterialAttrib)
    if attrib is None or attrib.get_material() is None:
        continue
    m = attrib.get_material()
    name = m.get_name()
    if name.startswith('INT_') and name not in KEEP:
        interior.append(gnp)
    col = m.get_base_color()
    gamma = 1 / 2.2
    gnp.set_color_scale(col[0]**gamma, col[1]**gamma, col[2]**gamma, col[3])
    if col[3] < 1:
        gnp.set_transparency(TransparencyAttrib.M_alpha)
#Колеса
corners = {}
for p in body.model.find_all_matches('**'):
    if not any(k in p.name for k in ('Tyre', 'rim', 'Hub', 'DISC', 'Caliper')):
        continue
    b = p.get_tight_bounds(car)
    if b is None:
        continue
    c = (b[0] + b[1]) / 2
    key = (1 if c.x > 0 else -1, 1 if c.z > 0 else -1)
    d = corners.setdefault(key, {'centers': [], 'spin': [], 'caliper': []})
    if 'Caliper' in p.name:
        d['caliper'].append(p)
    else:
        d['spin'].append(p)
        if 'Tyre' in p.name:
            d['centers'].append(c)
wheels = {}
for key, d in corners.items():
    if not d['centers']:
        continue
    center = Vec3(0, 0, 0)
    for c in d['centers']:
        center += c
    center = center / len(d['centers'])
    steer_pivot = Entity(parent=car, position=center, shader=basic_lighting_shader)
    spin = Entity(parent=steer_pivot, shader=basic_lighting_shader)
    for p in d['spin']:
        p.wrt_reparent_to(spin)
    for p in d['caliper']:
        p.wrt_reparent_to(steer_pivot)
    wheels[key] = (steer_pivot, spin)
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
#Відбійники вздовж країв траси
BARRIER_SPC = 4
BARRIER_OFFSET = road_width/2+10
BARRIER_NATIVE_LENGTH = 1.4396947622299194 * 2
BARRIER_STRAIGHT_ANGLE = 2
BARRIER_TOTAL_ANGLE = 5
BARRIER_STRAIGHT_DEVIATION = 1.0
BARRIER_STRAIGHT_MIN_SEGMENTS = 15
barriers = []
def add_stretched_barriers(ax, az, bx, bz):
    dx, dz = bx - ax, bz - az
    segment_length = sqrt(dx * dx + dz * dz)
    if segment_length == 0:
        return
    dx/=segment_length
    dz/=segment_length
    n_x,n_z = dz, -dx
    yaw=degrees(atan2(dx, dz)) + 90
    cx=(ax+bx)/2
    cz=(az+bz)/2
    scale_x = segment_length / BARRIER_NATIVE_LENGTH
    for side in (-1, 1):
        b = Entity(model='models/barrier/scene.gltf',position=(cx+n_x*BARRIER_OFFSET*side,0,cz+n_z*BARRIER_OFFSET*side),rotation_y=yaw,scale=(scale_x, 1.5, 1.5), collider='box', shader=basic_lighting_shader)
        b.wall_n = (-n_x * side, -n_z * side)
        barriers.append(b)
def add_segment_barriers(ax, az, bx, bz):
    dx, dz = bx - ax, bz - az
    segment_length = sqrt(dx * dx + dz * dz)
    if segment_length == 0:
        return
    dx /= segment_length
    dz /= segment_length
    n_x, n_z = dz, -dx
    yaw = degrees(atan2(dx, dz)) + 90
    count = int(segment_length // BARRIER_SPC)
    for j in range(count + 1):
        distance = j * BARRIER_SPC
        if distance > segment_length:
            break
        x = ax + dx * distance
        z = az + dz * distance
        for side in (-1, 1):
            b = Entity(model='models/barrier/scene.gltf',position=(x+n_x*BARRIER_OFFSET*side,0,z+n_z*BARRIER_OFFSET*side), rotation_y=yaw,scale=1.5, collider='box', shader=basic_lighting_shader)
            b.wall_n = (-n_x * side, -n_z * side)
            barriers.append(b)
def segment_heading(i):
    i %= n
    ax,az=dots[i]
    bx,bz=dots[(i+1)%n]
    dx,dz=bx-ax, bz - az
    length=sqrt(dx*dx+dz*dz)
    if length == 0:
        return None
    return dx / length, dz / length
def heading_diff(a,b):
    dot = clamp(a[0]*b[0]+a[1]*b[1],-1,1)
    return abs(degrees(atan2(a[0]*b[1]-a[1]*b[0], dot)))
straight_runs = []
covered_segments = set()
def straight_deviation(start, end):
    ax, az = dots[start]
    bx, bz = dots[end]
    dx, dz = bx - ax, bz - az
    length = sqrt(dx * dx + dz * dz)
    if length == 0:
        return 0
    max_deviation = 0
    for k in range(start, end + 1):
        px, pz = dots[k]
        rx, rz = px - ax, pz - az
        deviation = abs(dx * rz - dz * rx) / length
        max_deviation = max(max_deviation, deviation)
    return max_deviation
i = 0
while i < n - 1:
    initial_heading = segment_heading(i)
    if initial_heading is None:
        i += 1
        continue
    end = i
    while end + 1 < n:
        next_heading = segment_heading(end + 1)
        if next_heading is None:
            break
        if heading_diff(initial_heading, next_heading) > BARRIER_TOTAL_ANGLE:
            break
        if heading_diff(segment_heading(end), next_heading) > BARRIER_STRAIGHT_ANGLE:
            break
        end_point = end + 2 if end + 2 < n else end + 1
        if straight_deviation(i, end_point) > BARRIER_STRAIGHT_DEVIATION:
            break
        end += 1
    segment_count = end - i + 1
    if segment_count >= BARRIER_STRAIGHT_MIN_SEGMENTS:
        straight_runs.append((i, end))
        for segment_index in range(i, end + 1):
            covered_segments.add(segment_index)
        i = end + 1
    else:
        i += 1
for i in range(n):
    if i not in covered_segments:
        ax, az = dots[i]
        bx, bz = dots[(i + 1) % n]
        add_segment_barriers(ax, az, bx, bz)
for start, end in straight_runs:
    ax, az = dots[start]
    bx, bz = dots[end + 1]
    add_stretched_barriers(ax, az, bx, bz)
# Камера
camera.parent = car
camera.position = (0, 2.7, -7.5)
camera.rotation = (14, 0, 0)
#camera.position = (7, 1.5, 0)
#camera.rotation = (0, -90, 0)
#camera.fov=70
#editor_camera = EditorCamera()
#camera.parent = None
#camera.position = (0, 350, 0)
#camera.rotation = (90, 0, 0)
speed = 0
MAX_STEER = 30
GRIP_DRY_TARMAC=1.3
GRIP_DRY_GRASS=0.4
ROLL_TARMAC=0.5
ROLL_GRASS = 1.5
GRASS_DRAG = 0.13
VMAX = 70
DOWNFORCE=0.0003
DRAG =0.0004
TC_LIMIT= 0.85
ABS_LIMIT = 0.90
MASS=1250
IN_MOMENT=2000
A,B=1.4,1.3
L=A+B
ALPHA0=0.08
REAR_GRIP=1.35
V_FADE=3
LSF=6
DRIVE_REAR =1
H = 0.5 #висота центру мас
AERO_FRONT = 0.4
BRAKE_FRONT = 0.78
TAU = 0.15#інерція підвіски(с)
C=1.4
R_WHEEL=0.32
F_DRIVE = 3.7
GEARS=[3.6, 2.2, 1.5, 1.1, 0.9, 0.75]
REVERSE=3.2#передавальне число задньої
IDLE = 900
REDLINE=7000
TORQUE =[(900, 250),(2500, 340), (4500, 400), (6000, 390), (7000, 330)]
EFF = 0.9 #ККД трансмісії
ENG_BRAKE=90
OVERREV_K=20
REST = 0.2#скільки швидкості відбивається від стіни
WALL_F = 0.3#скільки швидкості стіна гасить тертям
PUSH = 0.15
gear = 0
ax_f = 0
r=0
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
def input(key):
    global gear
    if key in ("e", "gamepad a"):
        delta = 1
    elif key in ("q", "gamepad b"):
        delta = -1
    else:
        return
    new = clamp(gear + delta, -1, len(GEARS) - 1)
    if new == gear:
        return
    if -1 in (gear, new) and abs(speed) >= 5:
        return
    gear = new
def engine_torque(rpm):
    if rpm >= REDLINE:
        return 0
    for i in range(len(TORQUE) - 1):
        x0, y0 = TORQUE[i]
        x1, y1 = TORQUE[i + 1]
        if x0 <= rpm <= x1:
            t = (rpm - x0) / (x1 - x0)
            return lerp(y0, y1,t)
    return TORQUE[0][1]
def gear_ratio(g):
    return REVERSE if g == -1 else GEARS[g]
def wheel_rpm(spd, g):
    return abs(spd) / R_WHEEL * gear_ratio(g) * F_DRIVE * 60 / (2*pi)
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
SDK_LIFETIME = 20
SDK_INTERVAL = 0.0025
skidmark_timer = 0
skidmarks = []
CORNERS = [(-0.95, -2.3), (0.95, -2.3), (-0.95, 2.3), (0.95, 2.3)]
def fmt(sec):
    m, s = divmod(sec, 60)
    return f"{int(m)}:{s:06.3f}"
def update():
    global speed, last_progress, total, laps, lap_start, race_time, max_index, best_time,last_segment,lap_valid,v_side,r,ax_f,skidmark_timer
    steer, throttle, brake = analyze_input()
    road_dist, seg, t = locate(car.x, car.z, last_segment)
    last_segment = seg
    surface_grip, rolling = surface(road_dist)
    if road_dist > road_width / 2:
        rolling += GRASS_DRAG * abs(speed)
    down = DOWNFORCE * speed**2
    N_f=MASS*9.81*(B/L + AERO_FRONT*down) - MASS*ax_f*H/L
    N_r=MASS*9.81*(A/L + (1 - AERO_FRONT)*down) + MASS*ax_f*H/L
    N_f = max(N_f, 0.05*MASS*9.81)
    N_r = max(N_r, 0.05*MASS*9.81)
    F_max_f = surface_grip * N_f
    F_max_r = surface_grip * N_r * REAR_GRIP
    speed_start = speed
    a_long = 0
    F_x_f = F_x_r = 0
    ratio =gear_ratio(gear)
    direction=-1 if gear == -1 else 1
    rpm = max(wheel_rpm(speed, gear), IDLE)
    if throttle > 0:
        a_engine=throttle*engine_torque(rpm)*ratio*F_DRIVE*EFF/R_WHEEL/MASS
        traction_limits = [a_engine]
        if DRIVE_REAR > 0:
            traction_limits.append(TC_LIMIT * F_max_r / (MASS * DRIVE_REAR))
        if 1 - DRIVE_REAR > 0:
            traction_limits.append(TC_LIMIT * F_max_f / (MASS * (1 - DRIVE_REAR)))
        a_long = min(traction_limits)
        F_x_r = MASS * a_long * DRIVE_REAR
        F_x_f = MASS * a_long * (1 - DRIVE_REAR)
        acceleration=a_long-rolling-DRAG*speed**2
        rd= speed * direction
        if rd <= 0:
            acceleration = max(0, acceleration)
        speed += direction * acceleration * time.dt        
    elif brake > 0:
        a_long=brake * min(ABS_LIMIT * F_max_f / (BRAKE_FRONT * MASS),ABS_LIMIT * F_max_r / ((1 - BRAKE_FRONT) * MASS))
        F_x_f=BRAKE_FRONT*MASS*a_long
        F_x_r=(1-BRAKE_FRONT)*MASS*a_long
        sgn= 1 if speed > 0 else -1
        nspeed = speed - sgn* a_long * time.dt
        if nspeed * speed < 0:
            nspeed = 0
        speed=nspeed
    else:
        x = rpm / REDLINE
        factor = x + OVERREV_K * max(0, x - 1)**2
        a_eb = ENG_BRAKE*factor*ratio*F_DRIVE*EFF/R_WHEEL/MASS
        if DRIVE_REAR > 0:
            a_eb = min(a_eb, 0.95 * F_max_r / (MASS * DRIVE_REAR))
        k = rolling + speed**2 * DRAG + a_eb
        F_x_r = MASS * a_eb * DRIVE_REAR
        F_x_f = MASS * a_eb * (1 - DRIVE_REAR)
        if abs(speed) < k * time.dt:
            speed = 0
        else:
            speed -= k * time.dt * (1 if speed > 0 else -1)
    speed = clamp(speed, -8, VMAX)
    steer_angle = steer * radians(MAX_STEER) / (1 + (speed / 15) ** 2)
    nz=max(abs(speed),1)
    s=1 if speed>=0 else -1
    alpha_f = atan2(v_side + A*r, nz) - s * steer_angle
    alpha_r = atan2(v_side - B*r, nz)
    cap_f=sqrt(max(F_max_f**2 - F_x_f**2, 0))
    cap_r=sqrt(max(F_max_r**2 - F_x_r**2, 0))
    F_yf=-cap_f * sin(C * atan(alpha_f / (C * ALPHA0)))
    F_yr=-cap_r * sin(C * atan(alpha_r / (C * ALPHA0)))
    fade = min(1, abs(speed) / V_FADE)
    F_yf *= fade
    F_yr *= fade
    r+=(A*F_yf* cos(steer_angle) -B*F_yr)/IN_MOMENT*time.dt
    v_side+=((F_yf * cos(steer_angle) + F_yr) / MASS - speed * r) * time.dt
    speed+=(-F_yf * sin(steer_angle) / MASS + v_side * r) * time.dt
    ax=(speed - speed_start) / time.dt
    ax_f+=(ax - ax_f) * min(1, time.dt / TAU)
    damp=min(1, (1 - fade) * LSF * time.dt)
    r-=r*damp
    v_side-=v_side * damp
    if road_dist > road_width / 2:
        drag_side = (ROLL_GRASS + GRASS_DRAG * abs(v_side)) * time.dt
        v_side -= min(abs(v_side), drag_side) * (1 if v_side > 0 else -1)
    car.rotation_y += degrees(r) * time.dt
    car.position += car.forward * speed * time.dt + car.right * v_side * time.dt
    for barrier in barriers:
        dx = car.x - barrier.x
        dz = car.z - barrier.z
        if dx * dx + dz * dz > 36:
            continue
        if car.intersects(barrier).hit:
            nx,nz = barrier.wall_n
            vx=car.forward.x*speed + car.right.x * v_side
            vz=car.forward.z*speed + car.right.z * v_side
            vn = vx * nx + vz * nz#складова вздовж нормалі
            best_depth = 1e9
            for lx, lz in CORNERS:
                rx = car.right.x*lx + car.forward.x * lz
                rz = car.right.z*lx + car.forward.z * lz
                depth=rx*nx + rz*nz
                if depth < best_depth:
                    best_depth = depth
                    best_rx, best_rz = rx, rz
            k = nx * best_rz - nz * best_rx
            vc=vn+r*k
            if vc<0:
                J=-(1+REST)*vc/(1/MASS+k**2/IN_MOMENT)
                vx += J / MASS * nx
                vz += J / MASS * nz
                r+=J*k/IN_MOMENT
                vn2 = vx * nx + vz * nz#тертя об стіну
                vt_x = vx - vn2 * nx
                vt_z = vz - vn2 * nz
                vx = vn2 * nx + vt_x * (1 - WALL_F)
                vz = vn2 * nz + vt_z * (1 - WALL_F)
                speed  = vx * car.forward.x + vz * car.forward.z
                v_side = vx * car.right.x   + vz * car.right.z
            car.position += Vec3(nx, 0, nz)*PUSH
            break
    for (_, axle), (steer_pivot, spin) in wheels.items():
        if axle > 0:
            steer_pivot.rotation_y = degrees(steer_angle)
        else:
            steer_pivot.rotation_y = 0
        spin.rotation_x += degrees(speed * time.dt / R_WHEEL)

    skidmark_timer -= time.dt
    drift=road_dist < road_width / 2 and abs(speed) > 8 and abs(alpha_r) > radians(8)
    if drift and skidmark_timer <= 0:
        skidmark_timer = SDK_INTERVAL
        for (_, axle), (steer_pivot, spin) in wheels.items():
            if axle >= 0:
                continue
            world_pos = steer_pivot.world_position
            mark = Entity(model='quad',position=(world_pos.x, 0.025, world_pos.z),rotation=(90, car.rotation_y, 0),scale=(0.12, 0.45),color=color.rgba(0,0,0, 180),double_sided=True)
            mark.set_transparency(TransparencyAttrib.M_alpha)
            mark.lifetime = SDK_LIFETIME
            skidmarks.append(mark)
            if len(skidmarks) > 400:
                old_mark = skidmarks.pop(0)
                destroy(old_mark)
    for mark in skidmarks[:]:
        mark.lifetime -= time.dt
        if mark.lifetime <= 0:
            destroy(mark)
            skidmarks.remove(mark)
        else:
            alpha = int(180 * mark.lifetime / SDK_LIFETIME)
            mark.color = color.rgba(0, 0, 0, alpha)

    g = 'R' if gear == -1 else gear + 1
    camera.fov = 70 + abs(speed) * 0.25
    speedometer.text = f'{abs(speed)*3.6:.0f} km/h rpm {rpm:.0f} gear {g}'
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
