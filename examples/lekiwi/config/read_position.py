#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
读取 COM3 总线上所有舵机的当前位置（RAW 值）
直接使用 FeetechMotorsBus，不依赖 LeRobot 机器人封装
"""

import sys
sys.path.insert(0, r"D:\Desktop\lerobot_hand\lerobot\src")
sys.path.insert(0, r"D:\Desktop\lerobot_hand")

from lerobot.motors import Motor, MotorNormMode
from lerobot.motors.feetech import FeetechMotorsBus
from lerobot.motors.motors_bus import MotorCalibration
import json

# ========== 标定文件路径 ==========
CALIB_FILE = r"C:\Users\Administrator\.cache\huggingface\lerobot\calibration\robots\lekiwi\my_lekiwi.json"

# ========== 定义所有电机 ==========
ALL_MOTORS = {
    "arm_shoulder_pan":    Motor(1,  "sts3215", MotorNormMode.RANGE_M100_100),
    "arm_shoulder_lift":   Motor(2,  "sts3215", MotorNormMode.RANGE_M100_100),
    "arm_elbow_flex":      Motor(3,  "sts3215", MotorNormMode.RANGE_M100_100),
    "arm_wrist_flex":      Motor(4,  "sts3215", MotorNormMode.RANGE_M100_100),
    "arm_wrist_roll":      Motor(5,  "sts3215", MotorNormMode.RANGE_M100_100),
    "base_left_wheel":     Motor(7,  "sts3215", MotorNormMode.RANGE_M100_100),
    "base_back_wheel":     Motor(8,  "sts3215", MotorNormMode.RANGE_M100_100),
    "base_right_wheel":    Motor(9,  "sts3215", MotorNormMode.RANGE_M100_100),
    "arm_right_shoulder_pan":  Motor(21, "sts3215", MotorNormMode.RANGE_M100_100),
    "arm_right_shoulder_lift": Motor(22, "sts3215", MotorNormMode.RANGE_M100_100),
    "arm_right_elbow_flex":    Motor(23, "sts3215", MotorNormMode.RANGE_M100_100),
    "arm_right_wrist_flex":    Motor(24, "sts3215", MotorNormMode.RANGE_M100_100),
    "arm_right_wrist_roll":    Motor(25, "sts3215", MotorNormMode.RANGE_M100_100),
    "arm_right_gripper":       Motor(26, "sts3215", MotorNormMode.RANGE_M100_100),
}


def load_calibration(bus):
    """
    从磁盘加载标定文件，写入 bus.calibration
    """
    with open(CALIB_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)

    calib = {}
    for name, cal in raw.items():
        calib[name] = MotorCalibration(
            id=cal["id"],
            drive_mode=cal["drive_mode"],
            homing_offset=cal["homing_offset"],
            range_min=cal["range_min"],
            range_max=cal["range_max"],
        )
    bus.calibration = calib
    print(f"✓ 标定文件已加载：{CALIB_FILE}\n")


def main():
    bus = FeetechMotorsBus(
        port="COM3",
        motors=ALL_MOTORS,
        protocol_version=0,
    )

    print("正在连接 COM3...")
    try:
        bus.connect(handshake=True)
    except Exception as e:
        print(f"连接失败：{e}")
        return

    # 加载标定（必须，否则 normalize=True 会报错）
    try:
        load_calibration(bus)
    except Exception as e:
        print(f"⚠ 加载标定失败：{e}")
        print("   将跳过归一化显示，只显示 RAW 值。\n")

    print("\n" + "=" * 70)
    print("COM3 总线上的舵机位置（RAW 值）")
    print("=" * 70)

    try:
        raw_pos = bus.sync_read("Present_Position", list(ALL_MOTORS.keys()), normalize=False)
    except Exception as e:
        print(f"读取失败：{e}")
        import traceback
        traceback.print_exc()
        bus.disconnect()
        return

    # 尝试读取归一化值（需要标定）
    norm_pos = {}
    try:
        norm_pos = bus.sync_read("Present_Position", list(ALL_MOTORS.keys()), normalize=True)
    except Exception:
        pass  # 无标定时不显示归一化值

    print(f"\n{'ID':<5} {'名称':<30} {'RAW':<8} {'归一化':<10}")
    print("-" * 65)
    for name, motor in ALL_MOTORS.items():
        raw = raw_pos.get(name, "N/A")
        norm = norm_pos.get(name, "N/A")
        if isinstance(raw, (int, float)) and isinstance(norm, (int, float)):
            print(f"  {motor.id:<4} {name:<30} {int(raw):<8} {norm:.2f}")
        else:
            print(f"  {motor.id:<4} {name:<30} {str(raw):<8} {str(norm):<10}")

    print("\n" + "=" * 70)
    print("说明：")
    print("  RAW 值 = 舵机软件里看到的 Position 值（0~4095）")
    print("  归一化  = LeRobot 内部用的 [-100, 100] 值")
    print("  请把上面的 RAW 值整理后，替换进 SAFE_RAW_POSITIONS")
    print("=" * 70)

    bus.disconnect()
    print("\n已断开连接。")


if __name__ == "__main__":
    main()
