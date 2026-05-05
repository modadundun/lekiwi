#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
LeKiWi 键盘遥操作 - 完整版 v3（手臂 + 手掌）
修复：保存/恢复 scservo_sdk 的全局字节序状态 SCS_END
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
from lerobot.motors.feetech import FeetechMotorsBus, OperatingMode

# ========== 关键修复：导入 scservo_sdk 的全局状态 ==========
import scservo_sdk as scs
from scservo_sdk.scservo_def import SCS_GETEND, SCS_SETEND

# ========== 手掌配置 ==========
HAND_PORT = "COM6"
HAND_BAUDRATE = 1_000_000
HAND_IDS = list(range(11, 19))  # ID 11~18

# 实测开合位置（Mode 1 - 夹爪）
FINGER_OPEN = {
    11: 420, 12: 612, 13: 398, 14: 587,
    15: 405, 16: 624, 17: 377, 18: 610,
}
FINGER_CLOSE = {
    11: 775, 12: 254, 13: 752, 14: 233,
    15: 762, 16: 268, 17: 477, 18: 298,
}

# 手势位置（Mode 2 - 手势）
GESTURE_LIKE  = {11: 771, 12: 257, 13: 752, 14: 232, 15: 760, 16: 272, 17: 378, 18: 609}  # 点赞
GESTURE_FUCK  = {11: 771, 12: 256, 13: 398, 14: 587, 15: 761, 16: 272, 17: 731, 18: 262}  # Fuck
GESTURE_PEACE = {11: 424, 12: 610, 13: 398, 14: 587, 15: 761, 16: 272, 17: 730, 18: 262}  # 比耶

GESTURE_LIST  = [GESTURE_LIKE, GESTURE_FUCK, GESTURE_PEACE]
GESTURE_NAMES = ["点赞 👍", "Fuck ✊", "比耶 ✌️"]

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


def make_hand_bus():
    """创建手掌总线对象"""
    motors = {}
    for mid in HAND_IDS:
        name = f"hand_finger_{mid}"
        motors[name] = Motor(mid, "scs0009", MotorNormMode.RANGE_0_100)
    bus = FeetechMotorsBus(
        port=HAND_PORT,
        motors=motors,
        protocol_version=1,
    )
    return bus


def main():
    print("=" * 60)
    print("LeKiWi 键盘遥操作 - 完整版 v3（手臂 + 手掌）")
    print("=" * 60)

    # --------------------------------------------------------
    # 0. 保存全局字节序状态
    # --------------------------------------------------------
    original_scs_end = SCS_GETEND()
    print(f"\n[0/7] 保存 scservo 全局状态: SCS_END = {original_scs_end}")

    # --------------------------------------------------------
    # 1. 连接手臂（COM3）
    # --------------------------------------------------------
    print("\n[1/7] 连接机器人（COM3）...")
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
    # 2. 写入安全位置
    # --------------------------------------------------------
    print("\n[2/7] 写安全位置...")
    robot.bus.disable_torque(ALL_ARM)
    time.sleep(0.3)

    for name, raw in ORIGINAL_SAFE_RAW.items():
        robot.bus.write("Goal_Position", name, int(raw), normalize=False)
    print(f"  ✓ 已写入")

    robot.bus.enable_torque(ALL_ARM)
    print("  等待舵机移动到位...")
    time.sleep(2.0)

    # --------------------------------------------------------
    # 3. 读取当前实际位置
    # --------------------------------------------------------
    print("\n[3/7] 读取当前实际位置（RAW）...")
    actual_raw = robot.bus.sync_read("Present_Position", ALL_ARM, normalize=False)
    print("  实际RAW位置：")
    for name in ALL_ARM:
        print(f"    {name}: {actual_raw[name]}")

    # --------------------------------------------------------
    # 4. 配置轮子
    # --------------------------------------------------------
    print("\n[4/7] 配置轮子...")
    for name in BASE_MOTORS:
        robot.bus.write("Operating_Mode", name, OperatingMode.VELOCITY.value)
    robot.bus.enable_torque(BASE_MOTORS)
    print("  ✓ 轮子已配置")

    # --------------------------------------------------------
    # 5. 连接手掌（关键：恢复 SCS_END）
    # --------------------------------------------------------
    print("\n[5/7] 连接手掌（COM6）...")

    # 保存当前位置
    saved_positions = dict(actual_raw)

    # 连接手掌（这会改变 SCS_END）
    print("  创建手掌总线...")
    hand_bus = make_hand_bus()
    print("  打开COM6端口...")
    hand_bus.connect(handshake=False)
    print(f"  ✓ 手掌总线已连接, 当前 SCS_END = {SCS_GETEND()}")

    # 【关键修复】恢复 SCS_END 到原始状态
    SCS_SETEND(original_scs_end)
    print(f"  ✓ 已恢复 SCS_END = {SCS_GETEND()}")

    # 验证手臂位置读取是否正常
    test_read = robot.bus.sync_read("Present_Position", ALL_ARM, normalize=False)
    print("  验证手臂读取（SCS_END恢复后）：")
    all_ok = True
    for name in ALL_ARM:
        diff = abs(saved_positions[name] - test_read[name])
        status = "✓" if diff < 50 else "⚠"
        if diff >= 50:
            all_ok = False
        print(f"    {status} {name}: 保存={saved_positions[name]}, 当前={test_read[name]}, 差={diff}")

    if all_ok:
        print("  ✓ 手臂读取正常！SCS_END 恢复成功！")
    else:
        print("  ⚠ 部分位置有偏差")
        # 再试一次恢复
        SCS_SETEND(original_scs_end)
        time.sleep(0.1)
        test_read2 = robot.bus.sync_read("Present_Position", ALL_ARM, normalize=False)
        for name in ALL_ARM:
            diff = abs(saved_positions[name] - test_read2[name])
            if diff >= 50:
                print(f"    ⚠ {name}: 仍有偏差 {diff}")

    # 【重要】对手掌操作时需要 SCS_END = 1
    # 先保存当前手臂的 SCS_END 状态
    arm_scs_end = SCS_GETEND()
    
    # 初始化手掌到张开位置
    SCS_SETEND(1)  # 切换到手掌的字节序
    hand_bus.enable_torque()
    for mid in HAND_IDS:
        name = f"hand_finger_{mid}"
        hand_bus.write("Goal_Position", name, FINGER_OPEN[mid], normalize=False)
    SCS_SETEND(arm_scs_end)  # 恢复手臂的字节序
    print("  ✓ 手掌已初始化到张开位置")
    
    # 手掌模式状态
    hand_mode = 1  # 1=夹爪模式, 2=手势模式
    hand_closed = False  # 夹爪模式: False=张开, True=闭合
    gesture_idx = 0  # 手势模式: 当前手势索引

    # --------------------------------------------------------
    # 6. 初始化键盘
    # --------------------------------------------------------
    print("\n[6/7] 初始化键盘...")
    keyboard_config = KeyboardTeleopConfig(
        id="my_lekiwi_keyboard",
        arm_delta=5.0,
        linear_speed=0.3,
        angular_speed=60,
        strafe_speed=0.2,
    )
    keyboard = LeKiwiKeyboardTeleop(keyboard_config)
    keyboard.connect()

    # 同步键盘到当前实际位置
    actual_norm = robot.bus.sync_read("Present_Position", ALL_ARM, normalize=True)
    keyboard.sync_arm_position(actual_norm)
    print("  ✓ 键盘已同步到当前实际位置")
    print("  当前手臂位置（归一化）：")
    for name, pos in sorted(actual_norm.items()):
        print(f"    {name}: {pos:.2f}")

    # --------------------------------------------------------
    # 7. 显示控制说明
    # --------------------------------------------------------
    print("\n" + "=" * 60)
    print("LeKiWi 键盘遥操作已启动！")
    print("=" * 60)
    print("\n  左臂：Y/H 肩旋  U/J 肩升  I/K 肘  O/L 腕  P/. 转")
    print("  右臂：T/G 肩旋  F/R 肩升  V/B 肘  M/N 腕  C/X 转")
    print("  夹爪：[ 张开  ] 闭合")
    print("  手掌：- 模式切换  = 执行动作")
    print("        Mode 1(夹爪): = 抓取/张开")
    print("        Mode 2(手势): = 点赞→Fuck→比耶")
    print("  轮子：W/S 前进  A/D 平移  Q/E 旋转")
    print("  系统：SPACE 急停  ESC 退出")
    print("=" * 60)
    print("\n主循环运行中...\n")

    # --------------------------------------------------------
    # 8. 主循环
    # --------------------------------------------------------

    def move_hand(target_dict):
        """移动手掌到目标位置"""
        arm_scs_end = SCS_GETEND()  # 保存当前字节序
        SCS_SETEND(1)  # 切换到手掌字节序
        for mid in HAND_IDS:
            name = f"hand_finger_{mid}"
            hand_bus.write("Goal_Position", name, target_dict[mid], normalize=False)
        SCS_SETEND(arm_scs_end)  # 恢复手臂字节序

    _prev_eq = False
    _prev_minus = False
    _debug_frame = 0

    try:
        while True:
            t0 = time.perf_counter()

            # 检测 "-" 键边沿 → 模式切换
            _curr_minus = '-' in keyboard.pressed_keys
            if _curr_minus and not _prev_minus:
                hand_mode = 2 if hand_mode == 1 else 1
                if hand_mode == 1:
                    print(f"  -> 模式切换: Mode 2(手势) → Mode 1(夹爪)")
                else:
                    print(f"  -> 模式切换: Mode 1(夹爪) → Mode 2(手势)")
            _prev_minus = _curr_minus

            # 检测 "=" 键边沿 → 执行动作
            _curr_eq = '=' in keyboard.pressed_keys
            if _curr_eq and not _prev_eq:
                if hand_mode == 1:
                    # Mode 1: 夹爪抓取/张开
                    hand_closed = not hand_closed
                    move_hand(FINGER_CLOSE if hand_closed else FINGER_OPEN)
                    print(f"  -> Mode 1 夹爪: {'闭合' if hand_closed else '张开'}")
                else:
                    # Mode 2: 循环手势
                    gesture_idx = (gesture_idx + 1) % len(GESTURE_LIST)
                    move_hand(GESTURE_LIST[gesture_idx])
                    print(f"  -> Mode 2 手势: {GESTURE_NAMES[gesture_idx]}")
            _prev_eq = _curr_eq

            action = keyboard.get_action()
            robot.send_action(action)

            # 每120帧诊断一次
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
        try:
            hand_bus.disable_torque()
            hand_bus.disconnect()
        except:
            pass
        print("已退出。")


if __name__ == "__main__":
    main()
