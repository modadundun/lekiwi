# LeKiWi: Low-Cost Dual-Arm Mobile Robot Teleoperation System

<div align="center">

[![License](https://img.shields.io/badge/license-Apache%202.0-green)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9+-blue)](https://www.python.org)
[![LeRobot](https://img.shields.io/badge/LeRobot-Compatible-orange)](https://github.com/huggingface/lerobot)
[![Hardware](https://img.shields.io/badge/Hardware-Custom%20Build-blueviolet)](#hardware-list)

**A low-cost dual-arm mobile manipulation platform based on the HuggingFace LeRobot framework, supporting teleoperation, imitation learning training, and autonomous execution.**

[中文文档](README_zh.md) · [Project Background](#project-background) · [Hardware](#hardware-list) · [Quick Start](#quick-start) · [Dataset](#dataset) · [Development Plan](#development-plan)

</div>

---

## 📺 Demo Video

> Click the image to watch the demo on Bilibili

[![LeKiWi Teleoperation Demo](docs/images/video_thumbnail.png)](https://www.bilibili.com/video/BVxxxxxx)

**Video Contents:**
- 00:00 - Dual-arm cooperative grasping demo
- 00:30 - Dexterous hand gesture switching
- 01:00 - Omnidirectional base movement
- 01:30 - YOLO object detection integration

---

<details>
<summary><b>👀 Appendix: V1 Prototype Grasping Demo (Click to expand)</b></summary>
<br>
This is our early V1 prototype. It successfully validated the closed-loop pipeline of mobility and object grasping, paving the way for our current dual-arm system:

| Grasping Test 1 | Grasping Test 2 | Grasping Test 3 |
| :---: | :---: | :---: |
| <img src="docs/demo/videos/<8bc6e6dde0a5207cc4dc6357102c3346>.gif" width="250" alt="V1 Demo 1"/> | <img src="docs/demo/videos/<559b8d2ccab68f621cae5b665b05a586>.gif" width="250" alt="V1 Demo 2"/> | <img src="docs/demo/videos/<f949633e9e6dca416e328e7f400637f5>.gif" width="250" alt="V1 Demo 3"/> |

</details>

## 🎯 Project Background

### Research Motivation

Dual-arm mobile robots are a major research focus in robotics, with broad applications in home service, logistics, and healthcare assistance. However, commercial dual-arm platforms (e.g., Fetch, TIAGo) cost $20,000–$100,000, which limits participation from academic researchers and individual developers.

We aim to build a **fully functional, cost-controlled** dual-arm mobile robot platform that enables more people to participate in robot learning research.

### Solution

LeKiWi is built on the following open-source technologies and low-cost hardware:

| Component | Technology | Cost Reference |
|-----------|------------|----------------|
| Robot Framework | [HuggingFace LeRobot](https://github.com/huggingface/lerobot) | Open-source (Free) |
| Main Controller | Raspberry Pi 4B / PC | ¥300–600 |
| Robotic Arms | Bionic arm + STS3215 servos | ¥800–1200 |
| Dexterous Hands | Humanoid hand + SCS0009 servos | ¥400–600 |
| Mobile Base | Omnidirectional wheels + servos | ¥300–500 |
| **Total** | | **¥1,800 – 2,900** |

Compared to commercial platforms, the **cost is reduced by 90%+**, while retaining full imitation learning data collection capabilities.

### Technical Highlights

- **10-DOF Dual Arms**: 5 DOF per arm, supporting independent and cooperative control
- **8-DOF Dexterous Hands**: Independent finger control, supporting grasping and multiple gestures
- **Omnidirectional Mobile Base**: 3 omnidirectional wheels, supporting forward/backward, lateral movement, and rotation
- **Native LeRobot Support**: Recorded data can be directly used for ACT, Diffusion Policy, and other algorithm training — **end-to-end imitation learning已实现**
- **Remote Teleoperation**: Client-Server architecture, supporting WiFi remote control

---

## 🔧 Hardware List

### Core Components

| Component | Model | Qty | Unit Price (Ref.) | Purchase Link |
|-----------|-------|-----|-------------------|---------------|
| **Main Controller** | Raspberry Pi 4B (4GB) | 1 | ¥450 | [Taobao](https://item.taobao.com/item.htm?id=688878446695) / JD.com |
| **Robotic Arms** | Bionic dual-arm (DIY kit) | 1 | ¥800–1200 | [Taobao](https://item.taobao.com/item.htm?id=887529352123) |
| **Mobile Base** | Omnidirectional wheel base (3-wheel) | 1 | ¥300–500 | [Taobao](https://item.taobao.com/item.htm?id=912818508659) |
| **Dexterous Hands** | Humanoid hand (8 servos) | 1 | ¥400–600 | [Taobao](https://item.taobao.com/item.htm?id=979784661887) |

**Purchasing Tips:**

- Search Taobao for "Feetech Flagship Store" or "UBTech Servos"
- It is recommended to purchase from the same store to ensure accessory compatibility
- Consider buying 2–3 extra servos as spares

### Communication Modules

| Component | Model | Qty | Purpose |
|-----------|-------|-----|---------|
| USB to TTL Serial | CH340 / FT232 | 2 | Connect to servo bus |
| USB Camera | Logitech C270 / C920 | 1 | Image capture |

### Power Supply

| Component | Spec | Qty | Purpose |
|-----------|------|-----|---------|
| DC Power Supply | 12V 10A | 1 | Main power |
| Buck Converter | 12V→5V 3A | 1 | Raspberry Pi power |

### Wiring Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        PC / Laptop                          │
│                    (Running Client)                         │
└─────────────────────┬───────────────────────────────────────┘
                      │ WiFi (ZMQ TCP)
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                     Raspberry Pi 4B                          │
│                   (Running Server)                           │
│                                                             │
│   ┌─────────────┐              ┌─────────────┐            │
│   │  USB (CH340) │              │  USB (CH340) │            │
│   │   COM3       │              │   COM6       │            │
│   └──────┬──────┘              └──────┬──────┘            │
│          │                             │                     │
│   ┌──────▼──────┐              ┌──────▼──────┐            │
│   │  STS3215 x14 │              │  SCS0009 x8 │            │
│   │   Arms+Base   │              │    Hands     │            │
│   └─────────────┘              └─────────────┘            │
│                                                             │
│   ┌─────────────┐                                          │
│   │ USB Camera   │                                          │
│   └─────────────┘                                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### 1. Environment Setup

```bash
# Clone the repository
git clone https://github.com/modadundun/lerobot_hand.git
cd lerobot_hand


# Create conda environment
conda create -n lekiwi python=3.9
conda activate lekiwi

# Install dependencies
pip install -e ".[all]"
pip install scservo-sdk
```

### 2. Raspberry Pi Deployment

```bash
# 1. SSH into the Raspberry Pi
ssh pi@192.168.31.109

# 2. Install the same dependencies
git clone https://github.com/Eastdo/lerobot_hand.git
cd lekiwi
pip install -e ".[all]"

# 3. Modify serial port configuration (based on actual device names)
vim examples/lekiwi/lekiwi_server.py
# ARM_PORT = "/dev/ttyACM1"  # Arm bus
# HAND_PORT = "/dev/ttyACM0" # Hand bus

# 4. Start the Server
python examples/lekiwi/lekiwi_server.py
```

### 3. PC Client Startup

```bash
# Modify the Raspberry Pi IP address
vim examples/lekiwi/lekiwi_client_pc.py
# PI_IP = "192.168.31.109"

# Start the Client
python examples/lekiwi/lekiwi_client_pc.py
```

### 4. Keyboard Control

| Key | Function | Key | Function |
|-----|----------|-----|----------|
| `W`/`S` | Forward/Backward | `A`/`D` | Left/Right |
| `Q`/`E` | Rotate Left/Right | `Y`/`H` | Left shoulder rotation |
| `U`/`J` | Left shoulder up/down | `I`/`K` | Left elbow bend/extend |
| `O`/`L` | Left wrist pitch | `P`/`.` | Left wrist roll |
| `T`/`G` | Right shoulder rotation | `F`/`R` | Right shoulder up/down |
| `V`/`B` | Right elbow bend/extend | `M`/`N` | Right wrist pitch |
| `C`/`X` | Right wrist roll | `[`/`]` | Gripper open/close |
| `-` | Switch hand mode | `=` | Execute gesture |
| `Z` | Toggle YOLO | `SPACE` | Emergency Stop |

---

## 📊 Dataset

### LeRobot Dataset Format

LeKiWi recorded data is compatible with the official LeRobot dataset format and can be directly used for imitation learning training.

### Recording Data

```bash
# Record on the Raspberry Pi
python examples/lekiwi/record.py \
    --robot-url "lekiwi" \
    --output-dir "./data/my_dataset" \
    --fps 30 \
    --num-episodes 10
```

### Usage Example

```python
from lerobot.common.datasets import load_dataset

# Load local dataset
dataset = load_dataset(
    repo_id="your_username/lekiwi_sim_demo",
    root="./data/my_dataset"
)

# View dataset structure
print(dataset)

# Dataset contains the following fields:
# - observation.images.phone: Camera image
# - observation.state: Joint angles (14 dimensions)
# - action: Target joint angles
# - episode_index: Episode index
```

### Dataset Format Description

| Field | Type | Description |
|-------|------|-------------|
| `observation.state` | float32[14] | Normalized positions of 14 servos |
| `observation.images.phone` | uint8[240,320,3] | Camera RGB image |
| `action` | float32[14] | Target joint angles |

## 📋 Development Plan

### ✅ Completed Features

| Feature | Status | Description |
|---------|--------|-------------|
| 10-DOF dual-arm control | ✅ Done | Independent/cooperative control |
| 8-DOF dexterous hands | ✅ Done | Gesture/grasp modes |
| Omnidirectional base movement | ✅ Done | Forward/sideways/rotation |
| Keyboard teleoperation | ✅ Done | PC-side control |
| Remote control architecture | ✅ Done | ZMQ WiFi control |
| YOLO object detection | ✅ Done | Real-time detection display |
| Data recording | ✅ Done | LeRobot format compatible |
| Imitation learning algorithms | ✅ Done | ACT / Diffusion Policy training & inference |

### 🔄 In Progress

| Feature | Status | Expected Completion |
|---------|--------|---------------------|
| Gamepad teleoperation | 🔄 In Progress | 2026 Q2 |
| ROS2 integration | 🔄 In Progress | 2026 Q2 |
| Mobile picking task | 🔄 In Progress | 2026 Q3 |

### 📅 To Be Developed

| Feature | Priority | Description |
|---------|-----------|-------------|
| GR00T integration | ⭐⭐⭐ | NVIDIA GR00T unified interface |
| 3D Diffusion Policy | ⭐⭐⭐ | Point-cloud based diffusion policy |
| Tactile feedback | ⭐⭐ | End-effector force/tactile sensors |
| Vision-Language-Action (VLA) | ⭐⭐ | LLM instruction-driven |
| Multi-robot collaboration | ⭐ | Multiple LeKiWi units cooperating |

### 🎯 Long-Term Goals

- [ ] Integrate simulation environment (Isaac Lab / MuJoCo)
- [ ] Release pre-trained model weights
- [ ] Support multi-robot collaboration tasks
- [ ] Build LeKiWi-specific large-scale dataset

---

## 🤝 Contributing

We welcome all forms of contribution!

### How to Contribute

1. **Fork this repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Commit your changes**: `git commit -m 'Add amazing feature'`
4. **Push to the branch**: `git push origin feature/amazing-feature`
5. **Create a Pull Request**

### Open Issues

| Issue | Difficulty | Description |
|-------|------------|-------------|
| #12 | 🟢 Easy | Add gamepad/joystick teleoperation support |
| #15 | 🟡 Medium | Optimize image transmission latency |
| #19 | 🟡 Medium | Integrate simulation environment (Isaac Lab / MuJoCo) |
| #21 | 🔴 Hard | GR00T model interface integration |

### Data Collection

If you have a LeKiWi robot, you are welcome to participate in the data collection project!

**Collection Tasks (to be opened):**
- [ ] Grasping objects of different shapes
- [ ] Moving to specified positions
- [ ] Human-robot handover tasks

**Data contributors will receive:**
- GitHub contributor recognition
- Priority access to pre-trained models
- Research collaboration opportunities

---

## 🙏 Acknowledgements

The design and development of this project was significantly inspired by the **[XLeRobot](https://github.com/Vector-Wangel/XLeRobot)** project. XLeRobot is a low-cost dual-arm mobile home robot platform led by Gaotian/Vector Wang (RobotPi Lab, Rice University). With a cost of under $660 and an assembly time of less than 4 hours, it has become one of the benchmark projects in the open-source embodied AI field.

> ⭐ **Special thanks to the XLeRobot team** for their contributions to the open-source community, and for providing valuable references in hardware design, teleoperation architecture, and imitation learning pipelines.

---

## 📚 Related Projects

- [XLeRobot](https://github.com/Vector-Wangel/XLeRobot) - **Low-cost dual-arm mobile home robot (⭐5.1k), core reference for this project**
- [LeRobot](https://github.com/huggingface/lerobot) - HuggingFace robot learning framework
- [LeKiwi (SIGRobotics)](https://github.com/SIGRobotics-UIUC/LeKiwi) - Original LeKiwi omnidirectional base solution
- [SO-ARM100](https://github.com/TheRobotStudio/SO-ARM100) - SO-100/SO-101 robotic arm open-source solution
- [ALOHA](https://github.com/tonyzhaozh/act) - Dual-hand teleoperation platform
- [Mobile ALOHA](https://mobile-aloha.github.io) - Mobile dual-arm robot
- [piui](https://github.com/jyLeo/piui) - Raspberry Pi control interface

---

## 📄 License

This project is licensed under the **Apache License 2.0**.

---

## 📧 Contact

- **Project Homepage**: https://github.com/your_username/lekiwi
- **Issue Tracker**: https://github.com/your_username/lekiwi/issues
- **Discussions**: https://github.com/your_username/lekiwi/discussions

---

<div align="center">

**Made with ❤️ for the open-source robotics community**

</div>
