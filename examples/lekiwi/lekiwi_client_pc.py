#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
LeKiWi PC Client - 运行在 PC 上
直接读取键盘，通过网络发送给树莓派，接收并显示摄像头画面

用法：
  1. 修改 PI_IP 为树莓派 IP
  2. python examples/lekiwi/lekiwi_client_pc.py
"""

import base64
import json
import logging
import os
import sys
import time

script_dir = os.path.dirname(os.path.abspath(__file__))
lerobot_dir = os.path.dirname(os.path.dirname(script_dir))
src_dir = os.path.join(lerobot_dir, "src")
sys.path.insert(0, src_dir)
sys.path.insert(0, lerobot_dir)

import zmq
import cv2
import numpy as np
from lerobot.utils.robot_utils import precise_sleep

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ============================================================
# 网络配置（修改为你的树莓派 IP）
# ============================================================
PI_IP = "192.168.31.109"     # <-- 修改为树莓派的 IP 地址
ZMQ_PORT_CMD = 5555
ZMQ_PORT_OBS = 5556

FPS = 30

# ============================================================
# 手臂控制配置
# ============================================================
ARM_DELTA = 5.0  # 每次按键的增量（归一化值 [-100, +100]）

# 手臂关节键位映射 (key: (motor_name, sign))
# sign: +1 = 按下增加, -1 = 按下减少
ARM_KEY_MAP = {
    # 左臂
    "y": ("arm_shoulder_pan.pos",        +1),
    "h": ("arm_shoulder_pan.pos",        -1),
    "u": ("arm_shoulder_lift.pos",       +1),
    "j": ("arm_shoulder_lift.pos",       -1),
    "i": ("arm_elbow_flex.pos",          +1),
    "k": ("arm_elbow_flex.pos",          -1),
    "o": ("arm_wrist_flex.pos",          +1),
    "l": ("arm_wrist_flex.pos",          -1),
    "p": ("arm_wrist_roll.pos",          +1),
    ".": ("arm_wrist_roll.pos",          -1),
    # 右臂
    "t": ("arm_right_shoulder_pan.pos",  +1),
    "g": ("arm_right_shoulder_pan.pos",  -1),
    "f": ("arm_right_shoulder_lift.pos", +1),
    "r": ("arm_right_shoulder_lift.pos", -1),
    "v": ("arm_right_elbow_flex.pos",    +1),
    "b": ("arm_right_elbow_flex.pos",    -1),
    "m": ("arm_right_wrist_flex.pos",    +1),
    "n": ("arm_right_wrist_flex.pos",    -1),
    "c": ("arm_right_wrist_roll.pos",    +1),
    "x": ("arm_right_wrist_roll.pos",    -1),
    # 右臂夹爪（ID 26）
    "[": ("arm_right_gripper.pos",       +1),  # 张开
    "]": ("arm_right_gripper.pos",       -1),  # 闭合
}

# 底盘键位
LINEAR_SPEED = 0.3   # m/s
STRAFE_SPEED = 0.2   # m/s
ANGULAR_SPEED = 60   # deg/s（和 teleop_with_hand.py 一致）

BASE_KEY_MAP = {
    "w": ("x.vel",  LINEAR_SPEED),
    "s": ("x.vel", -LINEAR_SPEED),
    "a": ("y.vel",  STRAFE_SPEED),
    "d": ("y.vel", -STRAFE_SPEED),
    "q": ("theta.vel",  ANGULAR_SPEED),
    "e": ("theta.vel", -ANGULAR_SPEED),
}

# ============================================================
# pynput 键盘监听
# ============================================================
try:
    from pynput import keyboard as pynput_keyboard
    PYNPUT_OK = True
except ImportError:
    PYNPUT_OK = False
    logging.warning("pynput 未安装，Client 将无法读取键盘输入")


class KeyboardReader:
    """轻量级键盘读取器，直接维护 pressed_keys 集合"""

    def __init__(self):
        self.pressed_keys: set = set()
        self._listener = None
        if PYNPUT_OK:
            self._listener = pynput_keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release,
            )
            self._listener.start()
            logging.info("键盘监听已启动")

    def _on_press(self, key):
        try:
            char = key.char
        except AttributeError:
            char = str(key)
        self.pressed_keys.add(char)
        # ESC 和 space 立即处理
        if char == "q":
            logging.info("Q 键退出")
            self._cleanup()
            sys.exit(0)
        if char == " ":
            logging.info("SPACE 急停")
            self.pressed_keys.add(" _space_")

    def _on_release(self, key):
        try:
            char = key.char
        except AttributeError:
            char = str(key)
        self.pressed_keys.discard(char)
        self.pressed_keys.discard(" _space_")

    def _cleanup(self):
        if self._listener:
            self._listener.stop()
            self._listener = None

    def is_pressed(self, char: str) -> bool:
        return char in self.pressed_keys

    def stop(self):
        self._cleanup()


def main():
    # --------------------------------------------------------
    # 1. 连接 ZMQ Server（树莓派）
    # --------------------------------------------------------
    logging.info(f"连接树莓派 {PI_IP}...")
    ctx = zmq.Context()

    sock_cmd = ctx.socket(zmq.PUSH)
    sock_cmd.connect(f"tcp://{PI_IP}:{ZMQ_PORT_CMD}")
    sock_cmd.setsockopt(zmq.CONFLATE, 1)

    sock_obs = ctx.socket(zmq.PULL)
    sock_obs.connect(f"tcp://{PI_IP}:{ZMQ_PORT_OBS}")
    sock_obs.setsockopt(zmq.RCVTIMEO, 100)
    logging.info("ZMQ 连接成功")

    # --------------------------------------------------------
    # 2. 初始化键盘
    # --------------------------------------------------------
    kb = KeyboardReader()
    time.sleep(0.5)  # 等待监听器启动

    # --------------------------------------------------------
    # 3. 初始化显示窗口
    # --------------------------------------------------------
    window_name = "LeKiWi Camera [按 Q 退出]"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    logging.info("显示窗口已创建")

    # --------------------------------------------------------
    # 4. 手臂状态初始化（归一化值）
    # --------------------------------------------------------
    # 初始值设为 0（中立位置），Server 启动后会同步
    arm_pos = {
        "arm_shoulder_pan.pos":        0.0,
        "arm_shoulder_lift.pos":        0.0,
        "arm_elbow_flex.pos":           0.0,
        "arm_wrist_flex.pos":           0.0,
        "arm_wrist_roll.pos":           0.0,
        "arm_right_shoulder_pan.pos":  0.0,
        "arm_right_shoulder_lift.pos": 0.0,
        "arm_right_elbow_flex.pos":    0.0,
        "arm_right_wrist_flex.pos":    0.0,
        "arm_right_wrist_roll.pos":    0.0,
        "arm_right_gripper.pos":       0.0,  # 右臂夹爪（ID 26）
    }

    # --------------------------------------------------------
    # 5. 显示控制说明
    # --------------------------------------------------------
    print("\n" + "=" * 60)
    print("LeKiWi PC Client 已启动！")
    print("=" * 60)
    print(f"\n  连接目标: {PI_IP}:{ZMQ_PORT_CMD}")
    print("\n  左臂：Y/H 肩旋  U/J 肩升  I/K 肘  O/L 腕  P/. 转")
    print("  右臂：T/G 肩旋  F/R 肩升  V/B 肘  M/N 腕  C/X 转")
    print("        [/] 右臂夹爪（张/合）")
    print("  手掌：- 模式切换  = 执行动作")
    print("        Mode 1(夹爪): = 抓取/张开  Mode 2(手势): = 点赞→Fuck→比耶")
    print("  轮子：W/S 前进  A/D 平移  Q/E 旋转")
    print("  系统：SPACE 急停  Q 退出")
    print("=" * 60)

    # --------------------------------------------------------
    # 6. 主循环
    # --------------------------------------------------------
    hand_mode = 1       # 1=夹爪模式, 2=手势模式
    hand_closed = False
    gesture_idx = 0
    last_frame = None

    _prev_eq = False
    _prev_minus = False
    _prev_space = False

    try:
        while True:
            t0 = time.perf_counter()

            # --- 接收图像 ---
            try:
                msg = sock_obs.recv_string(zmq.NOBLOCK)
                obs = json.loads(msg)
                if "image" in obs and obs["image"]:
                    img_data = base64.b64decode(obs["image"])
                    np_arr = np.frombuffer(img_data, dtype=np.uint8)
                    last_frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            except (zmq.Again, json.JSONDecodeError):
                pass

            # 显示图像
            if last_frame is not None:
                cv2.imshow(window_name, last_frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q") or cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                    break

            # --- 手臂增量控制 ---
            for key, (motor, sign) in ARM_KEY_MAP.items():
                if kb.is_pressed(key):
                    arm_pos[motor] += sign * ARM_DELTA
                    arm_pos[motor] = max(-100.0, min(100.0, arm_pos[motor]))

            # --- 底盘速度 ---
            x_vel = 0.0
            y_vel = 0.0
            theta_vel = 0.0
            for key, (vel_key, speed) in BASE_KEY_MAP.items():
                if kb.is_pressed(key):
                    if vel_key == "x.vel":
                        x_vel = speed
                    elif vel_key == "y.vel":
                        y_vel = speed
                    elif vel_key == "theta.vel":
                        theta_vel = speed

            # --- 手掌 "-" 模式切换 ---
            _curr_minus = kb.is_pressed("-")
            if _curr_minus and not _prev_minus:
                hand_mode = 2 if hand_mode == 1 else 1
                hand_closed = False
                gesture_idx = 0
                print(f"  -> 模式切换: Mode {hand_mode}")
                sock_cmd.send_string(json.dumps({"hand_action": "mode_switch"}))
            _prev_minus = _curr_minus

            # --- 手掌 "=" 执行动作 ---
            _curr_eq = kb.is_pressed("=")
            if _curr_eq and not _prev_eq:
                sock_cmd.send_string(json.dumps({"hand_action": "gripper"}))
                if hand_mode == 1:
                    hand_closed = not hand_closed
                    print(f"  -> Mode 1 夹爪: {'闭合' if hand_closed else '张开'}")
                else:
                    gesture_idx = (gesture_idx + 1) % 3
                    names = ["👍 点赞", "✊ Fuck", "✌️ 比耶"]
                    print(f"  -> Mode 2 手势: {names[gesture_idx]}")
            _prev_eq = _curr_eq

            # --- 急停 SPACE ---
            _curr_space = kb.is_pressed(" _space_")
            if _curr_space and not _prev_space:
                x_vel = 0.0
                y_vel = 0.0
                theta_vel = 0.0
                for motor in arm_pos:
                    arm_pos[motor] = 0.0
                sock_cmd.send_string(json.dumps({"emergency_stop": True}))
                print("  -> 急停！")
            _prev_space = _curr_space

            # --- 构造并发送指令 ---
            action = {
                **arm_pos,
                "x.vel": x_vel,
                "y.vel": y_vel,
                "theta.vel": theta_vel,
            }
            sock_cmd.send_string(json.dumps(action))

            # 控制帧率
            dt = time.perf_counter() - t0
            if dt < 1.0 / FPS:
                precise_sleep(1.0 / FPS - dt)

    except KeyboardInterrupt:
        logging.info("收到退出信号")
    finally:
        logging.info("关闭 Client...")
        kb.stop()
        cv2.destroyAllWindows()
        sock_cmd.close()
        sock_obs.close()
        ctx.term()
        logging.info("Client 已关闭")


if __name__ == "__main__":
    print(f"\n目标树莓派 IP: {PI_IP}")
    main()
