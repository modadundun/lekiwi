#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
LeKiWi Server - 运行在树莓派上
接收 PC Client 的指令，驱动手臂+手掌+底盘，回传摄像头画面

用法：
  1. 确认 /dev/ttyUSB* 设备名
  2. python examples/lekiwi/lekiwi_server.py
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
import scservo_sdk as scs
from scservo_sdk.scservo_def import SCS_GETEND, SCS_SETEND

from lerobot.robots.lekiwi import LeKiwi, LeKiwiConfig
from lerobot.motors import Motor, MotorNormMode
from lerobot.motors.feetech import FeetechMotorsBus, OperatingMode
from lerobot.cameras.opencv.configuration_opencv import OpenCVCameraConfig

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ============================================================
# 硬件配置（根据你的实际接线修改）
# ============================================================
ARM_PORT = "/dev/ttyACM1"      # 手臂总线（树莓派上的设备名）
HAND_PORT = "/dev/ttyACM0"      # 手掌总线
HAND_IDS = list(range(11, 19)) # 手掌舵机 ID 11~18

# 手掌开合位置
FINGER_OPEN = {
    11: 420, 12: 612, 13: 398, 14: 587,
    15: 405, 16: 624, 17: 377, 18: 610,
}
FINGER_CLOSE = {
    11: 775, 12: 254, 13: 752, 14: 233,
    15: 762, 16: 268, 17: 477, 18: 298,
}

# 手势位置
GESTURE_LIKE  = {11: 771, 12: 257, 13: 752, 14: 232, 15: 760, 16: 272, 17: 378, 18: 609}
GESTURE_FUCK  = {11: 771, 12: 256, 13: 398, 14: 587, 15: 761, 16: 272, 17: 731, 18: 262}
GESTURE_PEACE = {11: 424, 12: 610, 13: 398, 14: 587, 15: 761, 16: 272, 17: 730, 18: 262}
GESTURE_LIST  = [GESTURE_LIKE, GESTURE_FUCK, GESTURE_PEACE]

# 安全位置（手臂归零时的初始位置）
SAFE_RAW = {
    "arm_shoulder_pan":       2047,
    "arm_shoulder_lift":      2034,
    "arm_elbow_flex":         2183,
    "arm_wrist_flex":         1871,
    "arm_wrist_roll":         2129,
    "arm_right_shoulder_pan":  1993,
    "arm_right_shoulder_lift":  2359,
    "arm_right_elbow_flex":      1885,
    "arm_right_wrist_flex":      2115,
    "arm_right_wrist_roll":      1966,
    "arm_right_gripper":          1980,
}
ALL_ARM = list(SAFE_RAW.keys())
BASE_MOTORS = ["base_left_wheel", "base_back_wheel", "base_right_wheel"]

# ============================================================
# ZMQ / 网络配置
# ============================================================
ZMQ_PORT_CMD = 5555
ZMQ_PORT_OBS = 5556
CAMERA_INDEX = 0            # 摄像头设备号（修改为你的）
MAX_LOOP_HZ = 30
WATCHDOG_TIMEOUT_MS = 500  # 超过此时间无指令则急停


def make_hand_bus():
    """创建手掌总线"""
    motors = {}
    for mid in HAND_IDS:
        name = f"hand_finger_{mid}"
        motors[name] = Motor(mid, "scs0009", MotorNormMode.RANGE_0_100)
    bus = FeetechMotorsBus(port=HAND_PORT, motors=motors, protocol_version=1)
    return bus


def move_hand_raw(hand_bus, target_dict):
    """写入手掌目标位置（自动处理字节序）"""
    arm_scs_end = SCS_GETEND()
    SCS_SETEND(1)  # SCS0009 用大端序
    for mid in HAND_IDS:
        name = f"hand_finger_{mid}"
        hand_bus.write("Goal_Position", name, target_dict[mid], normalize=False)
    SCS_SETEND(arm_scs_end)


def main():
    logging.info("=" * 50)
    logging.info("LeKiwi Server 启动中...")
    logging.info("=" * 50)

    # --------------------------------------------------------
    # 1. 保存全局字节序状态
    # --------------------------------------------------------
    original_scs_end = SCS_GETEND()
    logging.info(f"SCS_END 初始值: {original_scs_end}")

    # --------------------------------------------------------
    # 2. 连接手臂
    # --------------------------------------------------------
    logging.info(f"连接手臂总线 {ARM_PORT}...")
    robot_config = LeKiwiConfig(
        port=ARM_PORT,
        id="my_lekiwi",
        disable_torque_on_disconnect=True,
         cameras={
        #     "front": OpenCVCameraConfig(
        #         index_or_path=CAMERA_INDEX,
        #         fps=30,
        #         width=640,
        #         height=480,
        #     )
         },
    )
    robot = LeKiwi(robot_config)
    robot.connect()


    if os.path.exists(robot.calibration_fpath):
        robot._load_calibration()
        robot.bus.calibration = robot.calibration
        logging.info("标定已加载")
    else:
        logging.warning("未找到标定文件，将使用手动归一化转换")

    # --------------------------------------------------------
    # 3. 写入安全位置
    # --------------------------------------------------------
    logging.info("写入安全位置...")
    robot.bus.disable_torque(ALL_ARM)
    time.sleep(0.3)
    for name, raw in SAFE_RAW.items():
        robot.bus.write("Goal_Position", name, int(raw), normalize=False)
    robot.bus.enable_torque(ALL_ARM)
    time.sleep(2.0)
    logging.info("安全位置写入完成")

    # --------------------------------------------------------
    # 4. 配置底盘轮子为速度模式
    # --------------------------------------------------------
    logging.info("配置底盘轮子为速度模式...")
    for name in BASE_MOTORS:
        robot.bus.write("Operating_Mode", name, OperatingMode.VELOCITY.value)
    robot.bus.enable_torque(BASE_MOTORS)
    logging.info("底盘配置完成")

    # --------------------------------------------------------
    # 5. 连接手掌
    # --------------------------------------------------------
    logging.info(f"连接手掌总线 {HAND_PORT}...")
    hand_bus = make_hand_bus()
    hand_bus.connect(handshake=False)
    SCS_SETEND(original_scs_end)  # 恢复手臂字节序
    logging.info("手掌总线已连接")

    # 初始化手掌到张开位置
    SCS_SETEND(1)
    hand_bus.enable_torque()
    for mid in HAND_IDS:
        name = f"hand_finger_{mid}"
        hand_bus.write("Goal_Position", name, FINGER_OPEN[mid], normalize=False)
    SCS_SETEND(original_scs_end)
    logging.info("手掌初始化完成")

    # --------------------------------------------------------
    # 6. 启动摄像头
    # --------------------------------------------------------
    logging.info(f"打开摄像头 {CAMERA_INDEX}...")
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        logging.warning(f"无法打开摄像头 {CAMERA_INDEX}，将不发送图像")
    else:
        logging.info("摄像头已打开")

    # --------------------------------------------------------
    # 7. 启动 ZMQ Server
    # --------------------------------------------------------
    logging.info(f"启动 ZMQ Server (cmd={ZMQ_PORT_CMD}, obs={ZMQ_PORT_OBS})...")
    ctx = zmq.Context()
    sock_cmd = ctx.socket(zmq.PULL)
    sock_cmd.setsockopt(zmq.CONFLATE, 1)
    sock_cmd.bind(f"tcp://*:{ZMQ_PORT_CMD}")

    sock_obs = ctx.socket(zmq.PUSH)
    sock_obs.setsockopt(zmq.CONFLATE, 1)
    sock_obs.bind(f"tcp://*:{ZMQ_PORT_OBS}")
    logging.info("ZMQ Server 启动完成，等待 PC 连接...")

    # --------------------------------------------------------
    # 8. 主循环
    # --------------------------------------------------------
    last_cmd_time = time.time()
    hand_mode = 1
    hand_closed = False
    gesture_idx = 0

    logging.info("=" * 50)
    logging.info("LeKiwi Server 运行中，等待 PC 端指令...")
    logging.info("=" * 50)

    try:
        while True:
            t_loop = time.time()

            # --- 接收 PC 发来的指令 ---
            try:
                msg = sock_cmd.recv_string(zmq.NOBLOCK)
                cmd = json.loads(msg)
                last_cmd_time = time.time()

                # 急停
                if cmd.get("emergency_stop"):
                    logging.warning("[Server] 急停触发！")
                    robot.stop_base()
                    # 所有手臂归零
                    for name in SAFE_RAW:
                        robot.bus.write("Goal_Position", name, SAFE_RAW[name], normalize=False)

                # 手掌指令（独立于 robot.send_action）
                if cmd.get("hand_action") == "mode_switch":
                    hand_mode = 2 if hand_mode == 1 else 1
                    hand_closed = False
                    gesture_idx = 0
                    logging.info(f"[Server] 模式切换: Mode {hand_mode}")

                elif cmd.get("hand_action") == "gripper":
                    if hand_mode == 1:
                        hand_closed = not hand_closed
                        move_hand_raw(hand_bus, FINGER_CLOSE if hand_closed else FINGER_OPEN)
                        logging.info(f"[Server] Mode 1 夹爪: {'闭合' if hand_closed else '张开'}")
                    else:
                        gesture_idx = (gesture_idx + 1) % len(GESTURE_LIST)
                        move_hand_raw(hand_bus, GESTURE_LIST[gesture_idx])
                        names = ["👍 点赞", "✊ Fuck", "✌️ 比耶"]
                        logging.info(f"[Server] Mode 2 手势: {names[gesture_idx]}")

                # 手臂 + 底盘指令：直接调用 robot.send_action()
                # send_action() 会自动处理：
                #   - 手臂：归一化 → raw → Goal_Position + 速度限制
                #   - 底盘：body velocity → wheel velocity → Goal_Velocity
                _ = robot.send_action(cmd)

            except zmq.Again:
                pass
            except json.JSONDecodeError as e:
                logging.error(f"JSON 解析错误: {e}")

            # --- 看门狗：超时无指令则急停 ---
            if time.time() - last_cmd_time > WATCHDOG_TIMEOUT_MS / 1000:
                robot.stop_base()

            # --- 采集摄像头画面并发送 ---
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    obs = {"image": base64.b64encode(buf).decode("utf-8")}
                    try:
                        sock_obs.send_string(json.dumps(obs), flags=zmq.NOBLOCK)
                    except zmq.Again:
                        pass

            # 控制循环频率
            elapsed = time.time() - t_loop
            sleep_t = max(1 / MAX_LOOP_HZ - elapsed, 0)
            if sleep_t > 0:
                time.sleep(sleep_t)

    except KeyboardInterrupt:
        logging.info("收到退出信号")
    finally:
        logging.info("关闭 Server...")
        sock_cmd.close()
        sock_obs.close()
        ctx.term()
        cap.release()
        robot.disconnect()
        try:
            hand_bus.disable_torque()
            hand_bus.disconnect()
        except Exception:
            pass
        logging.info("Server 已关闭")


if __name__ == "__main__":
    main()
