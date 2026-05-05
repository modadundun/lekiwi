#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
LeKiWi 键盘遥操作 - 简化版（仅手臂控制，无手掌）
步骤：
1. 机器人先回到一个大致安全的位置（直接写用户原始SAFE_RAW，normalize=False）
2. 等待到位
3. 读取当前实际RAW位置作为基准
4. 用这个基准初始化键盘
5. 主循环：用归一化值控制手臂
"""


import time
import sys
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
lerobot_dir = os.path.dirname(os.path.dirname(script_dir))
src_dir = os.path.join(lerobot_dir, "src")
sys.path.insert(0, src_dir)
sys.path.insert(0, lerobot_dir)

from lerobot.robots.lekiwi import LeKiwi, LeKiwiConfig
from lerobot.teleoperators.keyboard.teleop_keyboard import LeKiwiKeyboardTeleop, KeyboardTeleopConfig
from lerobot.utils.robot_utils import precise_sleep
from lerobot.motors import Motor, MotorNormMode
from lerobot.motors.feetech import FeetechMotorsBus
from lerobot.motors.feetech import OperatingMode

FPS = 30

# 用户原始记录的安全位置（直接写，不做任何转换）
ORIGINAL_SAFE_RAW = {
    "arm_shoulder_pan":    2047,
    "arm_shoulder_lift":   2034,
    "arm_elbow_flex":      2183,
    "arm_wrist_flex":      1871,
    "arm_wrist_roll":      2129,
    "arm_right_shoulder_pan":  1993,
    "arm_right_shoulder_lift":  2359,
    "arm_right_elbow_flex":     1885,
    "arm_right_wrist_flex":     2115,
    "arm_right_wrist_roll":     1966,
    "arm_right_gripper":        1980,
}

ALL_ARM = list(ORIGINAL_SAFE_RAW.keys())
BASE_MOTORS = ["base_left_wheel", "base_back_wheel", "base_right_wheel"]


def main():
    print("=" * 60)
    print("LeKiWi 键盘遥操作 - 手臂版（无手掌）")
    print("=" * 60)

    # --------------------------------------------------------
    # 1. 连接
    # --------------------------------------------------------
    print("\n[1/6] 连接机器人（COM3）...")
    robot_config = LeKiwiConfig(
        port="COM3",
        id="my_lekiwi",
        disable_torque_on_disconnect=True,
        cameras={},
    )
    robot = LeKiwi(robot_config)
    robot.bus.connect()

    if os.path.exists(robot.calibration_fpath):
        robot._load_calibration()
        robot.bus.calibration = robot.calibration
        print(f"  ✓ 标定已加载")

    # --------------------------------------------------------
    # 2. 关闭力矩，直接写原始RAW值
    # --------------------------------------------------------
    print("\n[2/6] 写安全位置（直接写原始RAW，normalize=False）...")
    robot.bus.disable_torque(ALL_ARM)
    time.sleep(0.3)

    for name, raw in ORIGINAL_SAFE_RAW.items():
        robot.bus.write("Goal_Position", name, int(raw), normalize=False)
    print(f"  ✓ 已写入：{ORIGINAL_SAFE_RAW}")

    robot.bus.enable_torque(ALL_ARM)
    print("  等待舵机移动到位...")
    time.sleep(2.0)

    # --------------------------------------------------------
    # 3. 读取当前实际位置
    # --------------------------------------------------------
    print("\n[3/6] 读取当前实际位置（RAW）...")
    actual_raw = robot.bus.sync_read("Present_Position", ALL_ARM, normalize=False)
    print("  实际RAW位置：")
    for name in ALL_ARM:
        orig = ORIGINAL_SAFE_RAW[name]
        act = actual_raw[name]
        diff = abs(orig - act)
        status = "✓" if diff < 20 else "⚠"
        print(f"    {status} {name}: 原始={orig}, 实际={act}, 差={diff}")

    # 诊断：手臂归一化位置是否正常（如果在±100以内就OK）
    actual_norm_check = robot.bus.sync_read("Present_Position", ALL_ARM, normalize=True)
    print("\n  诊断 - 归一化位置（应该在±100以内）：")
    for name, pos in sorted(actual_norm_check.items()):
        flag = "" if -100 <= pos <= 100 else " ⚠️超出范围！"
        print(f"    {name}: {pos:.2f}{flag}")

    # --------------------------------------------------------
    # 4. 配置轮子
    # --------------------------------------------------------
    print("\n[4/6] 配置轮子...")
    for name in BASE_MOTORS:
        robot.bus.write("Operating_Mode", name, OperatingMode.VELOCITY.value)
    robot.bus.enable_torque(BASE_MOTORS)
    print("  ✓ 轮子已配置")

    # --------------------------------------------------------
    # 5. 初始化键盘
    # --------------------------------------------------------
    print("\n[5/6] 初始化键盘...")
    keyboard_config = KeyboardTeleopConfig(
        id="my_lekiwi_keyboard",
        arm_delta=5.0,
        linear_speed=0.3,
        angular_speed=0.5,
        strafe_speed=0.2,
    )
    keyboard = LeKiwiKeyboardTeleop(keyboard_config)
    keyboard.connect()

    # 用实际归一化位置同步键盘
    actual_norm = robot.bus.sync_read("Present_Position", ALL_ARM, normalize=True)
    keyboard.sync_arm_position(actual_norm)
    print("  ✓ 键盘已同步到当前实际位置")
    print("  当前手臂位置（归一化）：")
    for name, pos in sorted(actual_norm.items()):
        print(f"    {name}: {pos:.2f}")

    # --------------------------------------------------------
    # 6. 显示控制说明
    # --------------------------------------------------------
    print("\n" + "=" * 60)
    print("LeKiWi 键盘遥操作已启动！")
    print("=" * 60)
    print("\n  左臂：Y/H 肩旋  U/J 肩升  I/K 肘  O/L 腕  P/. 转")
    print("  右臂：T/G 肩旋  F/R 肩升  V/B 肘  M/N 腕  C/X 转")
    print("  轮子：W/S 前进  A/D 平移  Q/E 旋转")
    print("  系统：SPACE 急停  ESC 退出")
    print("=" * 60)
    print("\n主循环运行中...\n")

    # --------------------------------------------------------
    # 7. 主循环
    # --------------------------------------------------------
    _debug_frame = 0

    try:
        while True:
            t0 = time.perf_counter()

            action = keyboard.get_action()
            robot.send_action(action)

            # 每120帧（约4秒）打印一次诊断：显示当前手臂归一化位置
            _debug_frame += 1
            if _debug_frame % 120 == 0:
                diag = robot.bus.sync_read("Present_Position", ALL_ARM, normalize=True)
                print(f"  [诊断 t={_debug_frame//30:.0f}s] 手臂位置: ", end="")
                print(", ".join(f"{n}={v:.0f}" for n, v in sorted(diag.items()) if abs(v) > 50))

            dt = time.perf_counter() - t0
            if dt < 1.0 / FPS:
                precise_sleep(1.0 / FPS - dt)

    except KeyboardInterrupt:
        print("\n\n收到退出信号...")
    except Exception as e:
        print(f"\n\n发生错误：{e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n断开连接...")
        try:
            robot.bus.sync_write("Goal_Velocity", dict.fromkeys(BASE_MOTORS, 0))
        except:
            pass
        robot.disconnect()
        keyboard.disconnect()
        print("已退出。")


if __name__ == "__main__":
    main()
