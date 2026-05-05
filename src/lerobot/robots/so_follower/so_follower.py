#!/usr/bin/env python
import logging
import time
import sys
from functools import cached_property
from typing import TypeAlias

from lerobot.robots.amazinghand.amazinghand_controller import AmazingHandController
from lerobot.cameras.utils import make_cameras_from_configs
from lerobot.motors import Motor, MotorCalibration, MotorNormMode
from lerobot.motors.feetech import FeetechMotorsBus, OperatingMode
from lerobot.processor import RobotAction, RobotObservation
from lerobot.utils.decorators import check_if_already_connected, check_if_not_connected

from ..robot import Robot
from ..utils import ensure_safe_goal_position
from .config_so_follower import SOFollowerRobotConfig

logger = logging.getLogger(__name__)


class SOFollower(Robot):
    config_class = SOFollowerRobotConfig
    name = "so_follower"

    def __init__(self, config: SOFollowerRobotConfig):
        super().__init__(config)
        self.config = config

        norm_mode_body = (
            MotorNormMode.DEGREES if config.use_degrees else MotorNormMode.RANGE_M100_100
        )

        # motor6 保留结构（features/兼容），但运行时可能由 AmazingHand 接管
        self.bus = FeetechMotorsBus(
            port=self.config.port,
            motors={
                "shoulder_pan": Motor(1, "sts3215", norm_mode_body),
                "shoulder_lift": Motor(2, "sts3215", norm_mode_body),
                "elbow_flex": Motor(3, "sts3215", norm_mode_body),
                "wrist_flex": Motor(4, "sts3215", norm_mode_body),
                "wrist_roll": Motor(5, "sts3215", norm_mode_body),
                # "gripper": Motor(6, "sts3215", MotorNormMode.RANGE_0_100), #bob
            },
            calibration=self.calibration,
        )

        self.cameras = make_cameras_from_configs(config.cameras)

        # AmazingHand (optional)
        self.amazinghand: AmazingHandController | None = None

    # =============================
    # features
    # =============================
    @property
    def _motors_ft(self):
        return {f"{motor}.pos": float for motor in self.bus.motors}

    @property
    def _cameras_ft(self):
        return {
            cam: (self.config.cameras[cam].height, self.config.cameras[cam].width, 3)
            for cam in self.cameras
        }

    # @cached_property
    # def observation_features(self):
    #     return {**self._motors_ft, **self._cameras_ft}


    @cached_property
    def observation_features(self):
        feats = {**self._motors_ft, **self._cameras_ft}
        feats["gripper.pos"] = float  # ⭐⭐⭐ 手动补回
        return feats

    # @cached_property
    # def action_features(self):
    #     return self._motors_ft

    @cached_property
    def action_features(self):
        feats = dict(self._motors_ft)
        feats["gripper.pos"] = float  # ⭐⭐⭐ 手动补回 bob
        return feats


    @property
    def is_connected(self) -> bool:
        return self.bus.is_connected and all(cam.is_connected for cam in self.cameras.values())

    # =============================
    # connect
    # =============================
    @check_if_already_connected
    def connect(self, calibrate: bool = True) -> None:
        self.bus.connect()

        # ⭐⭐⭐ 关键：过滤掉 calibration 里的 gripper bob
        self._filter_calibration_for_existing_motors()

        if not self.is_calibrated and calibrate:
            logger.info("Calibration mismatch detected.")
            # 优先：直接把(过滤后的) calibration 写入到现存电机，避免进入交互校准
            try:
                if self.calibration:
                    self.bus.write_calibration(self.calibration)
                else:
                    self.calibrate()
            except Exception as e:
                logger.warning(f"Write calibration failed, fallback to calibrate(). err={e}")
                self.calibrate()


        for cam in self.cameras.values():
            cam.connect()

        # ===== connect AmazingHand =====
        try:
            self.amazinghand = AmazingHandController(
                port="/dev/ttyACM0",
                side=1,
                max_speed=7,
                close_speed=3,
            )
            logger.info("AmazingHand connected on /dev/ttyACM0")
        except Exception as e:
            self.amazinghand = None
            logger.warning(f"AmazingHand unavailable, fallback to motor gripper: {e}")

        self.configure()

        # 额外兜底：如果 AmazingHand 在用，确保 gripper 电机不抢控制
        if self.amazinghand is not None:
            try:
                self.bus.write("Torque_Enable", "gripper", 0)
            except Exception:
                pass

        logger.info(f"{self} connected.")

    # =============================
    # calibration
    # =============================
    @property
    def is_calibrated(self) -> bool:
        return self.bus.is_calibrated

    def calibrate(self) -> None:
        # if self.calibration:
        #     user_input = input(
        #         f"Press ENTER to use calibration for id {self.id}, or type 'c' to recalibrate: "
        #     )
        #     if user_input.strip().lower() != "c":
        #         self.bus.write_calibration(self.calibration)
        #         return
 
        if self.calibration:
            # ⭐⭐⭐ 非交互模式：直接使用已有校准（并过滤 gripper）
            if not sys.stdin.isatty():
                self._filter_calibration_for_existing_motors()
                logger.info(f"Non-interactive mode: using existing calibration for id {self.id}")
                self.bus.write_calibration(self.calibration)
                return

            user_input = input(
                f"Press ENTER to use calibration for id {self.id}, or type 'c' to recalibrate: "
            )
            if user_input.strip().lower() != "c":
                self._filter_calibration_for_existing_motors()
                logger.info(f"Writing filtered calibration for id {self.id}")
                self.bus.write_calibration(self.calibration)
                return


        logger.info(f"Running calibration of {self}")
        self.bus.disable_torque()

        for motor in self.bus.motors:
            self.bus.write("Operating_Mode", motor, OperatingMode.POSITION.value)

        input("Move robot to middle and press ENTER...")
        homing_offsets = self.bus.set_half_turn_homings()

        full_turn_motor = "wrist_roll"
        unknown_range_motors = [motor for motor in self.bus.motors if motor != full_turn_motor]

        input("Move joints through full range then press ENTER...")
        range_mins, range_maxes = self.bus.record_ranges_of_motion(unknown_range_motors)

        range_mins[full_turn_motor] = 0
        range_maxes[full_turn_motor] = 4095

        self.calibration = {}
        for motor, m in self.bus.motors.items():
            self.calibration[motor] = MotorCalibration(
                id=m.id,
                drive_mode=0,
                homing_offset=homing_offsets[motor],
                range_min=range_mins[motor],
                range_max=range_maxes[motor],
            )

        self.bus.write_calibration(self.calibration)
        self._save_calibration()

    # =============================
    # configure
    # =============================
    def configure(self) -> None:
        with self.bus.torque_disabled():
            self.bus.configure_motors()
            for motor in self.bus.motors:
                self.bus.write("Operating_Mode", motor, OperatingMode.POSITION.value)
                self.bus.write("P_Coefficient", motor, 16)
                self.bus.write("I_Coefficient", motor, 0)
                self.bus.write("D_Coefficient", motor, 32)

        # ⭐关键：AmazingHand 接管时，配置完再次确保 gripper torque 关闭
        if self.amazinghand is not None:
            try:
                self.bus.write("Torque_Enable", "gripper", 0)
            except Exception:
                pass

    # =============================
    # observation
    # =============================
    @check_if_not_connected
    def get_observation(self) -> RobotObservation:
        obs_dict = self.bus.sync_read("Present_Position")
        obs_dict = {f"{motor}.pos": val for motor, val in obs_dict.items()}

        # ⭐ gripper: LeRobot 语义 0=open 100=close
        if self.amazinghand is not None:
            open01 = float(self.amazinghand.get_open_ratio())
            close01 = 1.0 - open01
            obs_dict["gripper.pos"] = close01 * 100.0

        for cam_key, cam in self.cameras.items():
            obs_dict[cam_key] = cam.async_read()

        return obs_dict

    # =============================
    # action
    # =============================
    @check_if_not_connected
    def send_action(self, action: RobotAction) -> RobotAction:
        goal_pos = {
            key.removesuffix(".pos"): val
            for key, val in action.items()
            if key.endswith(".pos")
        }

        # 拿出 gripper（避免发到 Feetech motor6）
        gripper_val = goal_pos.pop("gripper", None)

        # 相对目标限幅（只对关节 1~5）
        if self.config.max_relative_target is not None:
            present_pos = self.bus.sync_read("Present_Position")
            present_pos.pop("gripper", None)

            goal_present_pos = {k: (g_pos, present_pos[k]) for k, g_pos in goal_pos.items()}
            goal_pos = ensure_safe_goal_position(goal_present_pos, self.config.max_relative_target)

        # 发送关节
        if goal_pos:
            self.bus.sync_write("Goal_Position", goal_pos)

        # 发送夹爪：优先 AmazingHand
        # if gripper_val is not None:
        #     if self.amazinghand is not None:
        #         self.amazinghand.set_grip(float(gripper_val) / 100.0)  # 0..1 close ratio
        #     else:
        #         self.bus.sync_write("Goal_Position", {"gripper": gripper_val})

        # ===== AmazingHand =====
        if gripper_val is not None:
            if self.amazinghand is not None:

                # # ⭐⭐⭐ 放大映射（核心）
                # gain = 2.0
                # scaled = float(gripper_val) * gain
                # scaled = max(0.0, min(100.0, scaled))

                # self.amazinghand.set_grip(scaled / 100.0)


                # x = float(gripper_val) / 100.0
                # scaled01 = x * x      # 二次曲线（更细腻）
                # self.amazinghand.set_grip(scaled01)

                # ===== AmazingHand (Figure-grade mapping) =====
                gain = 2.0  # ⭐ 灵敏度放大

                # 1️⃣ 放大到 0~100 域
                scaled = float(gripper_val) * gain
                scaled = max(0.0, min(100.0, scaled))

                # 2️⃣ 归一化到 0~1
                x = scaled / 100.0

                # 3️⃣ 非线性曲线（更像人手）
                # 可选曲线：
                #   x*x        → 更柔
                #   x**1.5     → 推荐 ⭐⭐⭐⭐⭐
                #   sqrt(x)    → 更激进

                scaled01 = x ** 1.5   # ⭐⭐⭐⭐⭐ Figure 推荐

                # 4️⃣ 只发送一次！！！
                self.amazinghand.set_grip(scaled01)

            else:
                self.bus.sync_write("Goal_Position", {"gripper": gripper_val})


        sent = {f"{motor}.pos": val for motor, val in goal_pos.items()}
        if gripper_val is not None:
            sent["gripper.pos"] = gripper_val
        return sent

    # =============================
    # disconnect
    # =============================
    @check_if_not_connected
    def disconnect(self):
        self.bus.disconnect(self.config.disable_torque_on_disconnect)
        for cam in self.cameras.values():
            cam.disconnect()
        logger.info(f"{self} disconnected.")

    def _filter_calibration_for_existing_motors(self) -> None:
        """Drop calibration entries that don't exist in current bus motors (e.g. gripper)."""
        if not self.calibration:
            return
        self.calibration = {k: v for k, v in self.calibration.items() if k in self.bus.motors}


SO100Follower: TypeAlias = SOFollower
SO101Follower: TypeAlias = SOFollower
