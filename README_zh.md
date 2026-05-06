# LeKiWi：基于 LeRobot 的低成本双臂移动机器人遥操作系统

<div align="center">

[![License](https://img.shields.io/badge/license-Apache%202.0-green)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9+-blue)](https://www.python.org)
[![LeRobot](https://img.shields.io/badge/LeRobot-Compatible-orange)](https://github.com/huggingface/lerobot)

**在 LeRobot 开源框架基础上扩展的低成本双臂移动操作平台，支持灵巧手遥操作与数据集采集。**

[硬件介绍](#硬件介绍) • [功能特性](#功能特性) • [安装部署](#安装部署) • [快速开始](#快速开始) • [技术细节](#技术细节)

</div>

---

## 项目概述

LeKiWi（**Le**Robot + **Ki**wi + **Wi**reless）是一个面向**模仿学习（Imitation Learning）**与**遥操作研究**的开源机器人平台。

本项目基于 [HuggingFace LeRobot](https://github.com/huggingface/lerobot) 框架进行二次开发，在保留 LeRobot 数据集格式与控制接口的同时，扩展了以下能力：

- **双臂协同控制**：左右臂各 5 自由度，共 10 个位置模式舵机
- **灵巧手指**：8 自由度手掌，支持抓取与多种手势表达
- **全向移动底盘**：3 个全向轮，支持全向移动和原地旋转
- **多协议总线**：通过双 UART 总线分别控制 STS3215（协议 0）与 SCS0009（协议 1）舵机，软件自动处理字节序兼容问题


---

## 功能特性

| 功能 | 说明 |
|------|------|
| 🦾 **双臂 10 自由度** | 左右臂独立控制，每臂 5 个关节（肩旋 / 肩升 / 肘弯 / 腕俯 / 腕转） |
| 🖐️ **8 自由度灵巧手** | 每根手指独立控制，支持预设手势（抓取 / 点赞 / 比耶） |
| 🔀 **双模式切换** | 键盘 `-` 键切换「夹爪模式」与「手势模式」，`=` 键执行动作 |
| 🚗 **全向移动底盘** | WASD + QE 控制前进 / 后退 / 平移 / 旋转，支持原地转向 |
| ⚡ **速度平滑限制** | 手臂舵机统一限速（可配置），消除多舵机转速不一致导致的晃动 |
| 🔧 **字节序自动修复** | COM3（STS 协议）与 COM6（SCS 协议）字节序不同，代码自动保存 / 恢复全局状态 |
| 📊 **LeRobot 数据集兼容** | 录制的数据直接兼容 LeRobot 格式，可用于 ACT / Diffusion Policy 等模仿学习算法训练 |

---

## 硬件介绍

### 硬件清单

| 部件 | 型号 | 数量 | 接口 | 描述 |
|------|------|------|------|------|
| 主控制器 | PC / Raspberry Pi | 1 | USB | 运行遥操作主循环 |
| 手臂舵机 | Feetech STS3215 | 10 | UART (COM3) | 每臂 5 个，12V，15W |
| 右夹爪舵机 | Feetech STS3215 | 1 | UART (COM3) | 右臂末端平行夹爪 |
| 底盘舵机 | Feetech STS3215 | 3 | UART (COM3) | 全向轮驱动 |
| 手掌舵机 | Feetech SCS0009 | 8 | UART (COM6) | 每根手指 1 个关节，1024 步分辨率 |
| UART 转接板 | USB-to-TTL | 2 | USB | 每条总线各一块 |

### 舵机映射表

**总线 1 — 机身（COM3，协议 0，STS3215）**

| ID | 名称 | 模式 | 描述 |
|----|------|------|------|
| 1 | arm_shoulder_pan（左） | 位置 | 左肩旋转 |
| 2 | arm_shoulder_lift（左） | 位置 | 左肩升降 |
| 3 | arm_elbow_flex（左） | 位置 | 左肘弯曲 |
| 4 | arm_wrist_flex（左） | 位置 | 左腕俯仰 |
| 5 | arm_wrist_roll（左） | 位置 | 左腕旋转 |
| 7 | base_left_wheel | 速度 | 左全向轮 |
| 8 | base_back_wheel | 速度 | 后全向轮 |
| 9 | base_right_wheel | 速度 | 右全向轮 |
| 21 | arm_shoulder_pan（右） | 位置 | 右肩旋转 |
| 22 | arm_shoulder_lift（右） | 位置 | 右肩升降 |
| 23 | arm_elbow_flex（右） | 位置 | 右肘弯曲 |
| 24 | arm_wrist_flex（右） | 位置 | 右腕俯仰 |
| 25 | arm_wrist_roll（右） | 位置 | 右腕旋转 |
| 26 | arm_right_gripper | 位置 | 右夹爪开合 |

**总线 2 — 手掌（COM6，协议 1，SCS0009）**

| ID | 名称 | 描述 |
|----|------|------|
| 11 | hand_finger_11 | 手指关节 1 |
| 12 | hand_finger_12 | 手指关节 2 |
| 13 | hand_finger_13 | 手指关节 3 |
| 14 | hand_finger_14 | 手指关节 4 |
| 15 | hand_finger_15 | 手指关节 5 |
| 16 | hand_finger_16 | 手指关节 6 |
| 17 | hand_finger_17 | 手指关节 7 |
| 18 | hand_finger_18 | 手指关节 8 |

### 接线说明

- **STS3215** 采用半双工 UART（TTL），同一条总线上的所有舵机共享 TX/RX 一根信号线
- **SCS0009** 与 STS3215 通信协议相同，但**字节序（Endian）不同**
- **电源**：整机 12V DC 供电，建议 10A 以上电源
- **手绘系统连接图**（如果你有实物图或接线图，可以放到 `docs/images/` 下并引用）

---

## 功能特性详解

### 遥操作模式

系统支持两种手掌控制模式，通过键盘 `-` 键循环切换：

**Mode 1 — 夹爪模式**
- 按 `=` 键：交替执行「抓取」与「张开」
- 适用于物体抓取任务的数据采集

**Mode 2 — 手势模式**
- 按 `=` 键：循环切换 3 种手势
  - 👍 点赞手势
  - ✊ Fuck 手势（握拳）
  - ✌️ 比耶手势（V 字）
- 适用于人机交互、手势表达研究

### 速度平滑控制

舵机默认以最高速度响应位置指令，导致多舵机因转速不一致而产生晃动。本系统在每次写入目标位置的同时，统一写入 `Goal_Velocity` 寄存器，限制所有舵机以相同速度运动。

速度值说明见[技术细节](#技术细节)章节。

---

## 安装部署

### 环境要求

- Python ≥ 3.9
- [LeRobot](https://github.com/huggingface/lerobot) 框架（本项目已包含）
- Feetech SDK：`scservo-sdk`

### 安装步骤

```bash
# 1. 克隆本仓库
git clone https://github.com/YOUR_USERNAME/lerobot_hand.git
cd lerobot_hand

# 2. 安装 LeRobot 及依赖
pip install -e ".[all]"

# 3. 安装 Feetech SDK（如未安装）
pip install scservo-sdk
```

### 验证硬件连接

```bash
# 检查 COM3 和 COM6 是否可见
python -m serial.tools.list_ports
```

---

## 快速开始

### 1. 标定手臂（仅首次使用）

首次使用需要对舵机进行标定，确定每个关节的运动范围：

```bash
python -m lerobot.robots.lekiwi.lekiwi --port COM3 --calibrate
```

标定文件保存在：
```
~/.cache/huggingface/lerobot/calibration/robots/lekiwi/my_lekiwi.json
```

### 2. 读取当前位置（调试用）

```bash
python examples/lekiwi/read_position.py
```

### 3. 启动遥操作

```bash
python examples/lekiwi/simple_teleop_with_hand_v3.py
```

启动后按键盘控制，详见下方[键盘映射](#键盘映射)。

---

## 键盘映射

### 手臂控制

| 按键 | 左臂关节 | 按键 | 右臂关节 |
|-----|-----------|-----|-----------|
| `Y` / `H` | 肩旋 ± | `T` / `G` | 肩旋 ± |
| `U` / `J` | 肩升 ± | `F` / `R` | 肩升 ± |
| `I` / `K` | 肘弯 ± | `V` / `B` | 肘弯 ± |
| `O` / `L` | 腕俯 ± | `M` / `N` | 腕俯 ± |
| `P` / `.` | 腕转 ± | `C` / `X` | 腕转 ± |

> 按住对应按键，舵机持续向对应方向运动；松开即停。

### 夹爪与手掌

| 按键 | 功能 |
|-----|------|
| `[` / `]` | 右夹爪张开 / 闭合 |
| **`-`** | **手掌模式切换**（夹爪模式 ↔ 手势模式） |
| **`=`** | **执行当前模式动作**（见下方说明） |

**Mode 1（夹爪模式）**：按 `=` 交替抓取 / 张开  
**Mode 2（手势模式）**：按 `=` 循环切换 👍 → ✊ → ✌️ → 👍

### 底盘控制

| 按键 | 功能 |
|-----|------|
| `W` / `S` | 前进 / 后退 |
| `A` / `D` | 左平移 / 右平移 |
| `Q` / `E` | 逆时针旋转 / 顺时针旋转 |
| `SPACE` | 急停（所有运动归零） |
| `ESC` | 退出程序 |

---

## 技术细节

### 舵机速度控制

手臂舵机（STS3215）使用 `Goal_Velocity` 寄存器（地址 `0x2E`，2 字节）限制每次运动的速度。单位为 **deg/s（度/秒）**。

换算关系（STS3215 分辨率为 4096 步/转）：
```
raw_speed = deg_per_sec × 4096 / 360
deg_per_sec = raw_speed × 360 / 4096
```

代码中默认值（位于 `src/lerobot/robots/lekiwi/lekiwi.py`）：

```python
# 569 raw ≈ 50 deg/s
arm_speed_raw = {motor: 569 for motor in self.arm_motors}
self.bus.sync_write("Goal_Velocity", arm_speed_raw, normalize=False)
```

**推荐速度参考表：**

| raw 值 | 速度 (deg/s) | 感受 |
|--------|---------------|------|
| 400 | ~35 | 慢，很稳 |
| 569 | ~50 | 中等（默认值） |
| 850 | ~75 | 稍快 |
| 1130 | ~100 | 快 |

> 修改 `569` 即可调整手臂运动速度，值越大越快。

### 多协议字节序处理

STS3215（协议 0）与 SCS0009（协议 1）使用**不同的字节序（Endian）**处理多字节寄存器。

`scservo_sdk` 使用全局变量 `SCS_END` 控制字节序：
- `SCS_END = 0`：小端序（适用于 STS3215）
- `SCS_END = 1`：大端序（适用于 SCS0009）

**问题**：操作 COM6（SCS）后，全局 `SCS_END` 被改为 1，导致后续读取 COM3（STS）的位置时字节序错误，返回错误数值。

**解决方案**：在所有手掌总线操作前后，手动保存/恢复 `SCS_GETEND()` / `SCS_SETEND()`。相关代码位于 `simple_teleop_with_hand_v3.py` 第 24~27 行、第 156 行、第 188~194 行。

### 底盘运动学

3 个全向轮的底盘运动学矩阵位于 `lekiwi.py` 的 `body_to_wheel_raw()` 方法。

如果实际轮子运动方向与按键不符，请先确认物理轮子与 ID 7/8/9 的对应关系，然后修改运动学矩阵中的角度分配。

---

## 树莓派部署（Client-Server 架构）

LeKiWi 支持 PC 键盘远程控制树莓派上的机器人，实现输入端与控制端分离：

```
┌─────────────┐         WiFi          ┌──────────────────────┐
│  PC (Client) │  ──── ZMQ TCP ────→  │  树莓派 (Server)     │
│             │                       │                      │
│ 键盘/手柄输入 │  ←─── 摄像头 ────   │ COM3 → 手臂+底盘舵机  │
│ 摄像头画面显示 │                       │ COM6 → 手掌舵机       │
│ 手掌逻辑控制  │                       │ USB摄像头 → 图像采集   │
└─────────────┘                       └──────────────────────┘
```

### 脚本说明

| 脚本 | 运行位置 | 说明 |
|------|----------|------|
| `examples/lekiwi/lekiwi_server.py` | **树莓派** | Server 端，驱动舵机 + 回传摄像头 |
| `examples/lekiwi/lekiwi_client_pc.py` | **PC** | Client 端，读取键盘 + 显示画面 |

### 树莓派端（Server）

```bash
# 1. 确认串口设备名
ls /dev/ttyUSB*

# 2. 修改脚本中的设备路径（如有需要）
# 编辑 lekiwi_server.py 开头：
ARM_PORT = "/dev/ttyUSB0"   # 手臂总线
HAND_PORT = "/dev/ttyUSB1"  # 手掌总线

# 3. 启动 Server
python examples/lekiwi/lekiwi_server.py
```

> **首次使用**：需要先标定手臂，见上方「快速开始 → 标定手臂」。

### PC 端（Client）

```bash
# 1. 修改树莓派 IP 地址
# 编辑 lekiwi_client_pc.py 开头：
PI_IP = "192.168.x.x"   # <-- 改成你的树莓派 IP

# 2. 启动 Client
python examples/lekiwi/lekiwi_client_pc.py
```

### 键盘映射

| 按键 | 功能 |
|------|------|
| `W`/`S` | 前进 / 后退 |
| `A`/`D` | 左平移 / 右平移 |
| `Q`/`E` | 逆时针 / 顺时针旋转 |
| `Y/H` `U/J` `I/K` `O/L` `P/.` | 左臂各关节 |
| `T/G` `F/R` `V/B` `M/N` `C/X` | 右臂各关节 |
| `[` / `]` | 夹爪张开 / 闭合 |
| `-` | 手掌模式切换（夹爪 ↔ 手势） |
| `=` | 执行当前模式动作 |
| `R` / `F` | 速度加 / 减 |
| `SPACE` | 急停 |
| `Q` | 退出 |

> PC 端窗口内按 `Q` 或点击窗口 × 按钮退出。

---

## 项目结构

```
lerobot_hand/
├── examples/lekiwi/              # 示例脚本
│   ├── simple_teleop_with_hand_v3.py  # 本地遥操作（PC直连）
│   ├── lekiwi_server.py             # ← 树莓派 Server 端（远程控制）
│   ├── lekiwi_client_pc.py          # ← PC Client 端（远程控制）
│   ├── teleop_arm_only.py           # 仅手臂遥操作
│   ├── read_position.py             # 读取所有舵机位置（调试）
│   └── record.py                    # 录制数据集（LeRobot 格式）
├── src/lerobot/robots/lekiwi/   # 机器人核心逻辑
│   ├── lekiwi.py                  # 主机器人类
│   ├── lekiwi_client.py           # 遥操作客户端
│   └── config_lekiwi.py           # 机器人配置
├── docs/                          # 文档与图片
├── README.md                      # 英文 README（发布用）
├── README_zh.md                   # 中文 README（本文件）
└── LICENSE
```

---

## 已知问题与排查

### 按下键盘后手臂晃动严重

**原因**：舵机默认无速度限制，各舵机转速不一致，到达目标位置时间不同步。

**解决**：降低 `Goal_Velocity` 值（见[舵机速度控制](#舵机速度控制)）。同时确认 `P_Coefficient` 已设为 `16`（默认值 `32` 过于激进，会导致震荡）。

### 手掌舵机在手臂移动后无响应

**原因**：COM3（STS）与 COM6（SCS）字节序冲突，读取手掌位置时使用错误字节序。

**解决**：确保使用 `simple_teleop_with_hand_v3.py`（已包含字节序自动修复）。如使用其他脚本，需手动添加 `SCS_GETEND()` / `SCS_SETEND()` 保护。

### 底盘移动方向混乱

**原因**：代码默认 ID7=左轮、ID8=后轮、ID9=右轮，但实际物理接线可能不同。

**解决**：确认物理轮子与 ID 的对应关系，修改 `lekiwi.py` 中 `body_to_wheel_raw()` 的运动学矩阵。

---

## 参考文献

- [LeRobot — State-of-the-Art Robot Learning Libraries](https://github.com/huggingface/lerobot)
- [Feetech STS3215 数据手册](http://doc.feetech.cn/#/prodinfodownload?srcType=FT-SMS-STS-emanual)
- [Feetech SCS0009 数据手册](http://doc.feetech.cn/#/prodinfodownload?srcType=FT-SCSL-emanual)

---

## 开源协议

本项目采用 **Apache License 2.0** 开源协议 —— 详见 [LICENSE](LICENSE) 文件。

LeRobot 核心框架同样采用 Apache 2.0 协议（© HuggingFace Inc.）。

---

<div align="center">

**为开源机器人社区而作 ❤️**

</div>
