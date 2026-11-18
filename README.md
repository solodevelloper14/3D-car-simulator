# 🚗 3D Car Simulator

A lightweight 3D car simulator built with Python and **Ursina Engine**.

The project includes a generated racing track, keyboard and gamepad support, basic vehicle dynamics, lap timing, and different grip behavior for asphalt and grass.

## ✨ Features

- 3D racing environment
- Keyboard and gamepad controls
- Asphalt and grass surface handling
- Steering, braking, rolling resistance, and aerodynamic drag
- Real-time speed and lateral acceleration display
- Lap counter and current/best lap time
- Procedurally loaded circuit from `track.json`
- Finish-line rendering
- Circuit validation with track visualization

## 🎮 Controls

| Action | Keyboard | Gamepad |
|---|---|---|
| Accelerate | `W` | Right trigger |
| Brake / reverse | `S` | Left trigger |
| Steer left | `A` | Left stick |
| Steer right | `D` | Left stick |
| Exit | Window controls | Window controls |

> Trigger, stick, and steering dead zones are applied to improve controller handling.

## 🛠️ Requirements

- Python 3.10 or newer
- `ursina`
- `svgpathtools`
- `matplotlib`

## 📦 Installation

Clone the repository:

```bash
git clone https://github.com/solodevelloper14/3D-car-simulator.git
cd 3D-car-simulator
```

Install the dependencies:

```bash
pip install ursina svgpathtools matplotlib
```

## ▶️ Running the Simulator

Start the game:

```bash
python "main(3d).py"
```

Make sure `track.json`, `ring.svg`, and the `textures` directory are available in the repository root.

## 🗺️ Generating the Track

The circuit is generated from `ring.svg` with `track_check.py`.

```bash
python track_check.py
```

This script:

1. Loads `ring.svg`.
2. Converts the SVG path into 750 points.
3. Applies a scale factor of `5`.
4. Saves the result as `track.json`.
5. Displays the generated circuit using Matplotlib.

## 📁 Project Structure

```text
.
├── main(3d).py       # Main Ursina simulator
├── track_check.py    # Converts ring.svg into track.json
├── track.json        # Racing track coordinates
├── ring.svg          # Source vector track
├── textures/
│   ├── asphalt.jpg   # Road texture
│   └── finish.png    # Finish-line texture
├── grass.jpg         # Terrain texture
└── README.md
```

## 🧠 Vehicle Physics

The simulator includes simplified vehicle and tire behavior:

- Speed-dependent steering angle
- Dry asphalt and grass grip levels
- Acceleration and aerodynamic drag
- Rolling resistance
- Front and rear tire slip angles
- Corner drag
- Speed-dependent lateral movement
- Grass off-track drag
- Traction and braking limits

## 🏁 Lap Tracking

Lap distance is calculated along the circuit points in `track.json`.

- A lap is counted after completing a full circuit.
- Leaving the road invalidates the current lap.
- Returning to the circuit resets lap validation.
- The interface shows the current lap time and the best valid lap.
