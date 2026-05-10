# LeKiWi：低成本双臂移动机器人遥操作系统

<div align="center">

[![License](https://img.shields.io/badge/license-Apache%202.0-green)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9+-blue)](https://www.python.org)
[![LeRobot](https://img.shields.io/badge/LeRobot-Compatible-orange)](https://github.com/huggingface/lerobot)
[![Hardware](https://img.shields.io/badge/Hardware-Custom%20Build-blueviolet)](#硬件清单)

**基于 HuggingFace LeRobot 框架的低成本双臂移动操作平台，支持遥操作、模仿学习训练与自主执行。**

[English](README.md) · [项目背景](#项目背景) · [硬件清单](#硬件清单) · [快速开始](#快速开始) · [数据集](#数据集) · [开发计划](#开发计划)

</div>

---

## 📺 演示视频

> 点击图片跳转至 Bilibili 演示视频

[![LeKiWi 遥操作演示](docs/images/video_thumbnail.png)](https://www.bilibili.com/video/BVxxxxxx)

**视频内容：**
- 00:00 - 双臂协同抓取演示
- 00:30 - 灵巧手手势切换
- 01:00 - 全向底盘移动
- 01:30 - YOLO 目标检测集成

---

## 🎯 项目背景

### 研究动机

双臂移动机器人是当前机器人研究的热点方向，在家庭服务、物流搬运、医疗辅助等领域有广泛应用。然而，商用双臂机器人平台（如 Fetch、TIAGo）价格高昂（$20,000 - $100,000），限制了学术研究和个人开发者的参与。

我们希望打造一个 **功能完整、成本可控** 的双臂移动机器人平台，让更多人能够参与到机器人学习的研究中。

### 解决方案

LeKiWi 基于以下开源技术与低成本硬件构建：

| 组件 | 技术选型 | 成本参考 |
|------|----------|----------|
| 机器人框架 | [HuggingFace LeRobot](https://github.com/huggingface/lerobot) | 开源免费 |
| 主控制器 | Raspberry Pi 4B / PC | ¥300-600 |
| 机械臂 | 仿生机械臂 + STS3215 舵机 | ¥800-1200 |
| 灵巧手 | 仿人手结构 + SCS0009 舵机 | ¥400-600 |
| 移动底盘 | 全向轮 + 舵机 | ¥300-500 |
| **总计** | | **¥1,800 - 2,900** |

相比商用平台，**成本降低 90%+**，同时保留了完整的模仿学习数据采集能力。

### 技术特色

- **双臂 10 自由度**：左右臂各 5 自由度，支持独立与协同控制
- **8 自由度灵巧手**：每根手指独立控制，支持抓取与多种手势
- **全向移动底盘**：3 个全向轮，支持前进、侧移、旋转
- **LeRobot 原生支持**：录制数据直接用于 ACT、Diffusion Policy 等算法训练，**已实现端到端模仿学习**

- **远程遥操作**：Client-Server 架构，支持 WiFi 远程控制

---

## 🔧 硬件清单

### 核心部件

| 部件 | 型号 | 数量 | 单价参考 | 购买渠道 |
|------|------|------|----------|----------|
| **主控制器** | Raspberry Pi 4B (4GB) | 1 | ¥350 | [淘宝](https://s.click.taobao.com/xxx) / 京东 |
| **机械臂** | 仿生双臂机械臂（DIY套件） | 1 | ¥800-1200 | [淘宝](https://s.click.taobao.com/xxx) |
| **底盘** | 全向轮底盘（3轮） | 1 | ¥300-500 | [淘宝](https://s.click.taobao.com/xxx) |
| **手掌** | 仿人手灵巧手（8舵机） | 1 | ¥400-600 | [淘宝](https://s.click.taobao.com/xxx) |

### 舵机清单

| 类型 | 型号 | 数量 | 电压 | 扭矩 | 单价 | 购买渠道 |
|------|------|------|------|------|------|----------|
| 手臂/夹爪/底盘 | Feetech STS3215 | 14 | 12V | 25KG·cm | ¥35 | [官方淘宝店](https://feetech.taobao.com) |
| 灵巧手 | Feetech SCS0009 | 8 | 6-8.4V | 9.4KG·cm | ¥25 | [官方淘宝店](https://feetech.taobao.com) |

**购买建议：**
- 淘宝搜索 "Feetech 旗舰店" 或 "优必选舵机"
- 建议从同一店铺购买，保证配件兼容性
- 舵机可多买 2-3 个备用

### 通信模块

| 部件 | 型号 | 数量 | 用途 |
|------|------|------|------|
| USB 转 TTL 串口 | CH340 / FT232 | 2 | 连接舵机总线 |
| USB 摄像头 | 罗技 C270 / C920 | 1 | 图像采集 |

### 电源

| 部件 | 规格 | 数量 | 用途 |
|------|------|------|------|
| DC 电源 | 12V 10A | 1 | 总供电 |
| 降压模块 | 12V→5V 3A | 1 | 树莓派供电 |

### 接线图

```
┌─────────────────────────────────────────────────────────────┐
│                        PC / Laptop                          │
│                    (运行 Client 端)                          │
└─────────────────────┬───────────────────────────────────────┘
                      │ WiFi (ZMQ TCP)
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                     Raspberry Pi 4B                          │
│                   (运行 Server 端)                           │
│                                                             │
│   ┌─────────────┐              ┌─────────────┐            │
│   │  USB (CH340) │              │  USB (CH340) │            │
│   │   COM3       │              │   COM6       │            │
│   └──────┬──────┘              └──────┬──────┘            │
│          │                             │                     │
│   ┌──────▼──────┐              ┌──────▼──────┐            │
│   │  STS3215 x14 │              │  SCS0009 x8 │            │
│   │  手臂+底盘   │              │    手掌     │            │
│   └─────────────┘              └─────────────┘            │
│                                                             │
│   ┌─────────────┐                                          │
│   │ USB 摄像头   │                                          │
│   └─────────────┘                                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 快速开始

### 1. 环境安装

```bash
# 克隆仓库
git clone https://github.com/your_username/lekiwi.git
cd lekiwi

# 创建 conda 环境
conda create -n lekiwi python=3.9
conda activate lekiwi

# 安装依赖
pip install -e ".[all]"
pip install scservo-sdk
```

### 2. 树莓派端部署

```bash
# 1. 通过 SSH 连接到树莓派
ssh pi@192.168.31.109

# 2. 安装相同依赖
git clone https://github.com/your_username/lekiwi.git
cd lekiwi
pip install -e ".[all]"

# 3. 修改串口配置（根据实际设备名）
vim examples/lekiwi/lekiwi_server.py
# ARM_PORT = "/dev/ttyACM1"  # 手臂总线
# HAND_PORT = "/dev/ttyACM0" # 手掌总线

# 4. 启动 Server
python examples/lekiwi/lekiwi_server.py
```

### 3. PC 端启动

```bash
# 修改树莓派 IP 地址
vim examples/lekiwi/lekiwi_client_pc.py
# PI_IP = "192.168.31.109"

# 启动 Client
python examples/lekiwi/lekiwi_client_pc.py
```

### 4. 键盘控制

| 按键 | 功能 | 按键 | 功能 |
|------|------|------|------|
| `W`/`S` | 前进/后退 | `A`/`D` | 左移/右移 |
| `Q`/`E` | 左旋/右旋 | `Y/H` | 左肩旋 |
| `U/J` | 左肩升/降 | `I/K` | 左肘弯/伸 |
| `O/L` | 左腕俯/仰 | `P/.` | 左腕转 |
| `T/G` | 右肩旋 | `F/R` | 右肩升/降 |
| `V/B` | 右肘弯/伸 | `M/N` | 右腕俯/仰 |
| `C/X` | 右腕转 | `[`/`]` | 夹爪张/合 |
| `-` | 切换手掌模式 | `=` | 执行手势 |
| `Z` | 开关 YOLO | `SPACE` | 急停 |

---

## 📊 数据集

### LeRobot 数据集格式

LeKiWi 录制的数据兼容 LeRobot 官方数据集格式，可直接用于模仿学习训练。

### 录制数据

```bash
# 在树莓派上录制
python examples/lekiwi/record.py \
    --robot-url "lekiwi" \
    --output-dir "./data/my_dataset" \
    --fps 30 \
    --num-episodes 10
```

### 使用示例

```python
from lerobot.common.datasets import load_dataset

# 加载本地数据集
dataset = load_dataset(
    repo_id="your_username/lekiwi_sim_demo",
    root="./data/my_dataset"
)

# 查看数据集结构
print(dataset)

# 数据集包含以下字段：
# - observation.images.phone: 摄像头图像
# - observation.state: 关节角度 (14维)
# - action: 目标关节角度
# - episode_index: episode 索引
```

### 数据集格式说明

| 字段 | 类型 | 描述 |
|------|------|------|
| `observation.state` | float32[14] | 14 个舵机的归一化位置 |
| `observation.images.phone` | uint8[240,320,3] | 摄像头 RGB 图像 |
| `action` | float32[14] | 目标关节角度 |

### 公开数据集

| 数据集 | 描述 | 规模 | 链接 |
|--------|------|------|------|
| lekiwi_sim_demo | 仿真环境演示 | 100 episodes | [HuggingFace](https://huggingface.co/datasets/...) |

---

## 📋 开发计划

### ✅ 已完成功能

| 功能 | 状态 | 说明 |
|------|------|------|
| 双臂 10 自由度控制 | ✅ 完成 | 独立/协同控制 |
| 8 自由度灵巧手 | ✅ 完成 | 手势/抓取模式 |
| 全向底盘移动 | ✅ 完成 | 前进/侧移/旋转 |
| 键盘遥操作 | ✅ 完成 | PC 端控制 |
| 远程控制架构 | ✅ 完成 | ZMQ WiFi 控制 |
| YOLO 目标检测 | ✅ 完成 | 实时检测显示 |
| 数据录制 | ✅ 完成 | LeRobot 格式兼容 |
| 模仿学习算法 | ✅ 完成 | ACT / Diffusion Policy 训练与推理 |

### 🔄 开发中

| 功能 | 状态 | 预计完成 |
|------|------|----------|
| 手柄遥操作 | 🔄 进行中 | 2026 Q2 |
| ROS2 集成 | 🔄 进行中 | 2026 Q2 |
| 移动捡取任务 | 🔄 进行中 | 2026 Q3 |

### 📅 待开发

| 功能 | 优先级 | 说明 |
|------|--------|------|
| GR00T 集成 | ⭐⭐⭐ | NVIDIA GR00T 统一接口 |
| 3D Diffusion Policy | ⭐⭐⭐ | 点云输入的扩散策略 |
| 触觉反馈 | ⭐⭐ | 末端力/触觉传感器 |
| 视觉-语言-动作（VLA） | ⭐⭐ | 大模型指令驱动 |
| 多机器人协作 | ⭐ | 多台 LeKiWi 协同 |

### 🎯 长期目标

- [ ] 集成仿真环境（Isaac Lab / MuJoCo）
- [ ] 发布预训练模型权重
- [ ] 支持多机器人协作任务
- [ ] 构建 LeKiWi 专属大规模数据集

---

## 🤝 贡献指南

我们欢迎所有形式的贡献！

### 如何参与

1. **Fork 本仓库**
2. **创建特性分支**：`git checkout -b feature/amazing-feature`
3. **提交更改**：`git commit -m 'Add amazing feature'`
4. **推送分支**：`git push origin feature/amazing-feature`
5. **创建 Pull Request**

### 待认领任务

| Issue | 难度 | 描述 |
|-------|------|------|
| #12 | 🟢 简单 | 添加手柄/游戏手柄遥操作支持 |
| #15 | 🟡 中等 | 优化图像传输延迟 |
| #19 | 🟡 中等 | 集成仿真环境（Isaac Lab / MuJoCo） |
| #21 | 🔴 困难 | GR00T 模型接口对接 |

### 数据采集

如果您有 LeKiWi 机器人，欢迎参与数据采集项目！

**采集任务（待开放）：**

- [ ] 抓取不同形状物体
- [ ] 移动到指定位置
- [ ] 人机交接任务

**数据贡献者将获得：**
- GitHub 贡献者认证
- 预训练模型优先使用权
- 研究合作机会

---

## 🙏 致谢

本项目在设计与开发过程中受到了 **[XLeRobot](https://github.com/Vector-Wangel/XLeRobot)** 项目的重要启发。XLeRobot 是由 Gaotian/Vector Wang（Rice 大学 RobotPi Lab）主导开发的低成本双臂移动家庭机器人平台，以不到 $660 的成本和 4 小时组装时间，成为了开源具身 AI 领域的标杆项目之一。

> ⭐ **特别感谢 XLeRobot 团队**对开源社区的贡献，以及其在硬件设计、遥操作架构和模仿学习流程上提供的宝贵参考。

---

## 📚 相关项目

- [XLeRobot](https://github.com/Vector-Wangel/XLeRobot) - **低成本双臂移动家庭机器人（⭐5.1k），本项目核心参考来源**
- [LeRobot](https://github.com/huggingface/lerobot) - HuggingFace 机器人学习框架
- [LeKiwi (SIGRobotics)](https://github.com/SIGRobotics-UIUC/LeKiwi) - 原始 LeKiwi 全向底盘方案
- [SO-ARM100](https://github.com/TheRobotStudio/SO-ARM100) - SO-100/SO-101 机械臂开源方案
- [ALOHA](https://github.com/tonyzhaozh/act) - 双手遥操作平台
- [Mobile ALOHA](https://mobile-aloha.github.io) - 移动双臂机器人
- [piui](https://github.com/jyLeo/piui) - 树莓派控制界面

---

## 📄 开源协议

本项目采用 **Apache License 2.0** 开源协议。

---

## 📧 联系方式

- **项目主页**: https://github.com/your_username/lekiwi
- **问题反馈**: https://github.com/your_username/lekiwi/issues
- **讨论交流**: https://github.com/your_username/lekiwi/discussions

---

<div align="center">

**为开源机器人社区而作 ❤️**

</div>
