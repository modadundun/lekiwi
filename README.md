# LeKiWi: Low-Cost Dual-Arm Mobile Robot with Dexterous Hand Teleoperation

<div align="center">

[![License](https://img.shields.io/badge/license-Apache%202.0-green)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9+-blue)](https://www.python.org)
[![LeRobot](https://img.shields.io/badge/LeRobot-Compatible-orange)](https://github.com/huggingface/lerobot)

**A low-cost, open-source dual-arm mobile manipulation platform based on the LeRobot framework.**

[Hardware](#hardware) • [Features](#features) • [Installation](#installation) • [Usage](#usage) • [Documentation](#documentation)

</div>

---

## 🤖 Overview

LeKiWi (LeRobot + KiWi) is an affordable dual-arm mobile robot system built on top of the [HuggingFace LeRobot](https://github.com/huggingface/lerobot) framework. It integrates:

- **Dual 5-DOF arms** with position-controlled servos
- **8-DOF dexterous hand** for grasping and gesture expression
- **3-wheel omnidirectional base** for holonomic movement
- **Real-time keyboard teleoperation** with velocity limiting for smooth motion

The system is designed for **imitation learning data collection**, **teleoperation research**, and **low-cost mobile manipulation** applications.


---

## ✨ Features

- 🦾 **Dual 5-DOF Arms** — Independent left/right arm control with 5 joints each
- 🖐️ **8-DOF Dexterous Hand** — Per-finger control with preset gestures (grasp, thumbs-up, peace sign)
- 🔄 **Dual-Mode Hand Control** — Switch between grasp mode and gesture mode via keyboard
- 🚗 **Omnidirectional Base** — Holonomic movement (forward/back, strafe, rotate) using 3 omni-wheels
- ⚡ **Velocity Limiting** — Configurable servo speed to prevent jerky motion
- 🔧 **Byte-Order Auto-Fix** — Seamless multi-protocol support (STS3215 + SCS0009 on separate UART ports)
- 📊 **Data Recording** — Compatible with LeRobot dataset format for imitation learning

---

## 🔧 Hardware

### Bill of Materials

| Component | Model | Qty | Interface | Description |
|-----------|--------|-----|-----------|-------------|
| Main Controller | PC / Raspberry Pi | 1 | USB | Runs teleoperation loop |
| Arm Servo | Fe-etech STS3215 | 10 | UART (COM3) | 5 per arm, 12V, 15W |
| Gripper Servo | Fe-etech STS3215 | 1 | UART (COM3) | Right arm end-effector |
| Base Servo | Fe-etech STS3215 | 3 | UART (COM3) | Omni-wheel drive |
| Hand Servo | Fe-etech SCS0009 | 8 | UART (COM6) | 1 per finger joint |
| UART Adapter | USB-to-TTL | 2 | USB | One per bus |

### Servo Mapping

**Bus 1 — Main Body (COM3, Protocol 0, STS3215)**

| ID | Name | Mode | Description |
|----|------|------|-------------|
| 1 | arm_shoulder_pan (left) | Position | Shoulder rotation |
| 2 | arm_shoulder_lift (left) | Position | Shoulder elevation |
| 3 | arm_elbow_flex (left) | Position | Elbow flexion |
| 4 | arm_wrist_flex (left) | Position | Wrist pitch |
| 5 | arm_wrist_roll (left) | Position | Wrist roll |
| 7 | base_left_wheel | Velocity | Left omni-wheel |
| 8 | base_back_wheel | Velocity | Rear omni-wheel |
| 9 | base_right_wheel | Velocity | Right omni-wheel |
| 21 | arm_shoulder_pan (right) | Position | Shoulder rotation |
| 22 | arm_shoulder_lift (right) | Position | Shoulder elevation |
| 23 | arm_elbow_flex (right) | Position | Elbow flexion |
| 24 | arm_wrist_flex (right) | Position | Wrist pitch |
| 25 | arm_wrist_roll (right) | Position | Wrist roll |
| 26 | arm_right_gripper | Position | Parallel gripper |

**Bus 2 — Hand (COM6, Protocol 1, SCS0009)**

| ID | Name | Description |
|----|------|-------------|
| 11-18 | hand_finger_{id} | 8 finger joints, 1024-step resolution |

### Wiring Notes

- STS3215 uses **half-duplex UART** (TTL). All servos on the same bus share a single wire for TX/RX.
- SCS0009 uses a **different byte order** (endian) than STS3215. The software handles this automatically — see [Technical Details](#technical-details).
- Power: 12V DC, recommended 10A+ power supply for full system.

---

## 🎮 Usage

### Keyboard Mapping

#### Arm Control

| Key | Left Arm Joint | Key | Right Arm Joint |
|-----|-----------------|-----|------------------|
| `Y` / `H` | Shoulder Pan (±) | `T` / `G` | Shoulder Pan (±) |
| `U` / `J` | Shoulder Lift (±) | `F` / `R` | Shoulder Lift (±) |
| `I` / `K` | Elbow Flex (±) | `V` / `B` | Elbow Flex (±) |
| `O` / `L` | Wrist Flex (±) | `M` / `N` | Wrist Flex (±) |
| `P` / `.` | Wrist Roll (±) | `C` / `X` | Wrist Roll (±) |

#### Hand Control

| Key | Function |
|-----|----------|
| `[` / `]` | Gripper: Open / Close |
| `-` | **Mode Switch** (Grasp Mode ↔ Gesture Mode) |
| `=` | **Action** (context-dependent, see below) |

**Mode 1 — Grasp:** Press `=` to toggle open / close.  
**Mode 2 — Gesture:** Press `=` to cycle through: 👍 → ✊ → ✌️ → 👍 ...

#### Base Control

| Key | Function |
|-----|----------|
| `W` / `S` | Forward / Backward |
| `A` / `D` | Strafe Left / Right |
| `Q` / `E` | Rotate CCW / CW |
| `SPACE` | EMERGENCY STOP |
| `ESC` | Quit |

---

## ⚙️ Installation

### Prerequisites

- Python ≥ 3.9
- [LeRobot](https://github.com/huggingface/lerobot) (included as submodule/base)
- Fe-etech SDK: `scservo-sdk`

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/lerobot_hand.git
cd lerobot_hand

# 2. Install LeRobot and dependencies
pip install -e ".[all]"

# 3. Install Fe-etch SDK (if not already installed)
pip install scservo-sdk
```

### Verify Hardware Connection

```bash
# Check that COM3 and COM6 are visible
python -m serial.tools.list_ports
```

---

## 🚀 Quick Start

### 1. Calibrate the Arms (First Time Only)

```bash
python -m lerobot.robots.lekiwi.lekiwi --port COM3 --calibrate
```

This writes the calibration file to:
```
~/.cache/huggingface/lerobot/calibration/robots/lekiwi/my_lekiwi.json
```

### 2. Read Current Positions (Debug)

```bash
python examples/lekiwi/read_position.py
```

### 3. Launch Teleoperation

```bash
python examples/lekiwi/simple_teleop_with_hand_v3.py
```

---

## 📐 Technical Details

### Servo Speed Control

Arm servos (STS3215) use the `Goal_Velocity` register (address `0x2E`, 2 bytes) to limit per-motion speed. The value is in **deg/s**:

```
raw_speed = deg_per_sec × 4096 / 360
```

Default in code: `569` raw ≈ **50 deg/s**.

To change, edit `src/lerobot/robots/lekiwi/lekiwi.py`:

```python
# Line ~437, inside send_action()
arm_speed_raw = {motor: 569 for motor in self.arm_motors}  # ← change 569
self.bus.sync_write("Goal_Velocity", arm_speed_raw, normalize=False)
```

**Recommended values:**

| Raw | Speed (deg/s) | Feel |
|------|---------------|------|
| 400 | ~35 | Slow, stable |
| 569 | ~50 | Default, smooth |
| 850 | ~75 | Fast |
| 1130 | ~100 | Very fast |

### Multi-Protocol Byte Order Handling

STS3215 (Protocol 0) and SCS0009 (Protocol 1) use **different byte orders** for multi-byte registers. The `scservo_sdk` uses a global `SCS_END` flag.

**Problem:** After accessing COM6 (SCS), the global flag changes, causing COM3 (STS) reads to return wrong values.

**Solution:** The code saves/restores `SCS_GETEND()` / `SCS_SETEND()` around every hand bus operation. See `simple_teleop_with_hand_v3.py` lines 24-27 and 156.

### Base Kinematics

The 3-omniwheel base uses standard holonomic kinematics. The mapping from body velocity `(x, y, θ)` to wheel speeds is computed in `lekiwi.py:body_to_wheel_raw()`.

If your wheels move in wrong directions, adjust the wheel ID → physical position mapping in `config_lekiwi.py`.

---

## 📁 Project Structure

```
lerobot_hand/
├── examples/lekiwi/              # Example scripts
│   ├── simple_teleop_with_hand_v3.py  # ← Main teleop script (recommended)
│   ├── teleop_arm_only.py           # Arm-only teleoperation
│   ├── read_position.py             # Read all servo positions
│   └── record.py                    # Record dataset (LeRobot format)
├── src/lerobot/robots/lekiwi/   # Core robot logic
│   ├── lekiwi.py                  # Main robot class
│   ├── lekiwi_client.py           # Teleoperation client
│   └── config_lekiwi.py           # Robot configuration
├── docs/                          # Documentation and images
└── README.md                      # This file
```

---

## 🐛 Known Issues & Troubleshooting

### Arm jerks / shakes on keypress

**Cause:** Default servo acceleration is too high; servos reach target at different times.  
**Fix:** Lower `Goal_Velocity` (see [Servo Speed Control](#servo-speed-control)). Also make sure `P_Coefficient` is set to `16` (default is `32`, which is too aggressive).

### Hand servos stop responding after arm movement

**Cause:** Byte order corruption between Protocol 0 and Protocol 1 buses.  
**Fix:** Already handled in `simple_teleop_with_hand_v3.py`. Make sure you are using the latest version.

### Base moves in wrong direction

**Cause:** Physical wheel order doesn't match the kinematic matrix.  
**Fix:** Identify which physical wheel corresponds to ID 7/8/9, then update `body_to_wheel_raw()` in `lekiwi.py`.

---

## 📖 Documentation

- [LeRobot Documentation](https://lerobot.readthedocs.io/)
- [Fe-etch STS3215 Datasheet](http://doc.feetech.cn/#/prodinfodownload?srcType=FT-SMS-STS-emanual)
- [Fe-etch SCS0009 Datasheet](http://doc.feetech.cn/#/prodinfodownload?srcType=FT-SCSL-emanual)

---

## 🤝 Contributing

Contributions are welcome! Please open an issue or submit a pull request.

---

## 📄 License

This project is licensed under the Apache License 2.0 — see [LICENSE](LICENSE) for details.  
LeRobot core is also under Apache 2.0 (© HuggingFace Inc.).

---

<div align="center">

**Built with ❤️ for the open-source robotics community**

</div>
