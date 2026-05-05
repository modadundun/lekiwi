#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
极简测试：直接写 RAW 值到舵机，绕过所有归一化
"""

import sys
import time
sys.path.insert(0, r"D:\Desktop\lerobot_hand\lerobot\src")
sys.path.insert(0, r"D:\Desktop\lerobot_hand")

from lerobot.robots.lekiwi import LeKiwi, LeKiwiConfig
from lerobot.motors import Motor, MotorNormMode

# 安全位置（你的手动设定）
SAFE_RAW = {
    "arm_shoulder_pan": 2047,
    "arm_shoulder_lift": 2034,
    "arm_elbow_flex": 2183,
    "arm_wrist_flex": 1871,
    "arm_wrist_roll": 2129,
    "arm_right_shoulder_pan": 1993,
    "arm_right_shoulder_lift": 2359,
    "arm_right_elbow_flex": 1885,
    "arm_right_wrist_flex": 2115,
    "arm_right_wrist_roll": 1966,
    "arm_right_gripper": 1980,
}

def main():
    config = LeKiwiConfig(
        port="COM3",
        id="my_lekiwi",
        disable_torque_on_disconnect=True,
        cameras={},
    )

    print("连接机器人（不重新标定）...")
    robot = LeKiwi(config)
    try:
        robot.connect(calibrate=False)
    except Exception as e:
        print(f"连接失败：{e}")
        return

    print("\n步骤1：关闭力矩...")
    robot.bus.disable_torque(robot.arm_motors)
    time.sleep(0.3)

    print("\n步骤2：直接写 RAW 值到 Goal_Position（归一化）...")
    for name, raw in SAFE_RAW.items():
        # 关键：每个电机单独写，normalize=False 表示 raw 值直接写寄存器
        robot.bus.write("Goal_Position", name, int(raw), normalize=False)
        print(f"  {name}: 写入 RAW={raw}")

    print("\n步骤3：使能力矩（舵机移动到指定位置）...")
    robot.bus.enable_torque(robot.arm_motors)

    time.sleep(1)  # 等待到位

    print("\n步骤4：读取当前位置，验证是否正确...")
    current = robot.bus.sync_read("Present_Position", robot.arm_motors, normalize=False)
    print(f"{'名称':<30} {'写入RAW':<10} {'当前RAW':<10} {'是否一致':<10}")
    print("-" * 65)
    all_ok = True
    for name in SAFE_RAW:
        wrote = SAFE_RAW[name]
        now = current.get(name, None)
        if now is not None:
            ok = abs(now - wrote) < 5  # 允许 5 个刻度的误差
            status = "✓" if ok else "✗"
            if not ok:
                all_ok = False
            print(f"  {name:<28} {wrote:<10} {now:<10} {status}")
        else:
            print(f"  {name:<28} {wrote:<10} N/A       ✗")
            all_ok = False

    print("\n" + "=" * 60)
    if all_ok:
        print("✓ 所有舵机都到达了指定位置！")
        print("  现在可以用键盘控制，且起始位置正确。")
    else:
        print("✗ 有舵机未到达指定位置，请检查：")
        print("  1. 舵机 ID 是否正确？")
        print("  2. 机械结构是否卡住？")
        print("  3. 标定参数是否和实际舵机匹配？")
    print("=" * 60)

    input("\n按 Enter 断开连接...")
    robot.disconnect()
    print("已断开。")


if __name__ == "__main__":
    main()
