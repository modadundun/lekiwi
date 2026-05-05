#!/usr/bin/env python

# Copyright 2024 The HuggingFace Inc. team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import os
import sys
import time
from queue import Queue
from typing import Any

from lerobot.processor import RobotAction
from lerobot.utils.decorators import check_if_already_connected, check_if_not_connected

from ..teleoperator import Teleoperator
from ..utils import TeleopEvents
from .configuration_keyboard import (
    KeyboardEndEffectorTeleopConfig,
    KeyboardRoverTeleopConfig,
    KeyboardTeleopConfig,
)

PYNPUT_AVAILABLE = True
try:
    if ("DISPLAY" not in os.environ) and ("linux" in sys.platform):
        logging.info("No DISPLAY set. Skipping pynput import.")
        raise ImportError("pynput blocked intentionally due to no display.")

    from pynput import keyboard
except ImportError:
    keyboard = None
    PYNPUT_AVAILABLE = False
except Exception as e:
    keyboard = None
    PYNPUT_AVAILABLE = False
    logging.info(f"Could not import pynput: {e}")


class KeyboardTeleop(Teleoperator):
    """
    Teleop class to use keyboard inputs for control.
    """

    config_class = KeyboardTeleopConfig
    name = "keyboard"

    def __init__(self, config: KeyboardTeleopConfig):
        super().__init__(config)
        self.config = config
        self.robot_type = config.type

        self.event_queue = Queue()
        self.current_pressed = {}
        self.listener = None
        self.logs = {}

    @property
    def action_features(self) -> dict:
        return {
            "dtype": "float32",
            "shape": (len(self.arm),),
            "names": {"motors": list(self.arm.motors)},
        }

    @property
    def feedback_features(self) -> dict:
        return {}

    @property
    def is_connected(self) -> bool:
        return PYNPUT_AVAILABLE and isinstance(self.listener, keyboard.Listener) and self.listener.is_alive()

    @property
    def is_calibrated(self) -> bool:
        pass

    @check_if_already_connected
    def connect(self) -> None:
        if PYNPUT_AVAILABLE:
            logging.info("pynput is available - enabling local keyboard listener.")
            self.listener = keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release,
            )
            self.listener.start()
        else:
            logging.info("pynput not available - skipping local keyboard listener.")
            self.listener = None

    def calibrate(self) -> None:
        pass

    def _on_press(self, key):
        if hasattr(key, "char"):
            self.event_queue.put((key.char, True))

    def _on_release(self, key):
        if hasattr(key, "char"):
            self.event_queue.put((key.char, False))
        if key == keyboard.Key.esc:
            logging.info("ESC pressed, disconnecting.")
            self.disconnect()

    def _drain_pressed_keys(self):
        while not self.event_queue.empty():
            key_char, is_pressed = self.event_queue.get_nowait()
            self.current_pressed[key_char] = is_pressed

    def configure(self):
        pass

    @check_if_not_connected
    def get_action(self) -> RobotAction:
        before_read_t = time.perf_counter()

        self._drain_pressed_keys()

        # Generate action based on current key states
        action = {key for key, val in self.current_pressed.items() if val}
        self.logs["read_pos_dt_s"] = time.perf_counter() - before_read_t

        return dict.fromkeys(action, None)

    def send_feedback(self, feedback: dict[str, Any]) -> None:
        pass

    @check_if_not_connected
    def disconnect(self) -> None:
        if self.listener is not None:
            self.listener.stop()


class KeyboardEndEffectorTeleop(KeyboardTeleop):
    """
    Teleop class to use keyboard inputs for end effector control.
    Designed to be used with the `So100FollowerEndEffector` robot.
    """

    config_class = KeyboardEndEffectorTeleopConfig
    name = "keyboard_ee"

    def __init__(self, config: KeyboardEndEffectorTeleopConfig):
        super().__init__(config)
        self.config = config
        self.misc_keys_queue = Queue()

    @property
    def action_features(self) -> dict:
        if self.config.use_gripper:
            return {
                "dtype": "float32",
                "shape": (4,),
                "names": {"delta_x": 0, "delta_y": 1, "delta_z": 2, "gripper": 3},
            }
        else:
            return {
                "dtype": "float32",
                "shape": (3,),
                "names": {"delta_x": 0, "delta_y": 1, "delta_z": 2},
            }

    @check_if_not_connected
    def get_action(self) -> RobotAction:
        self._drain_pressed_keys()
        delta_x = 0.0
        delta_y = 0.0
        delta_z = 0.0
        gripper_action = 1.0

        # Generate action based on current key states
        for key, val in self.current_pressed.items():
            if key == keyboard.Key.up:
                delta_y = -int(val)
            elif key == keyboard.Key.down:
                delta_y = int(val)
            elif key == keyboard.Key.left:
                delta_x = int(val)
            elif key == keyboard.Key.right:
                delta_x = -int(val)
            elif key == keyboard.Key.shift:
                delta_z = -int(val)
            elif key == keyboard.Key.shift_r:
                delta_z = int(val)
            elif key == keyboard.Key.ctrl_r:
                # Gripper actions are expected to be between 0 (close), 1 (stay), 2 (open)
                gripper_action = int(val) + 1
            elif key == keyboard.Key.ctrl_l:
                gripper_action = int(val) - 1
            elif val:
                # If the key is pressed, add it to the misc_keys_queue
                # this will record key presses that are not part of the delta_x, delta_y, delta_z
                # this is useful for retrieving other events like interventions for RL, episode success, etc.
                self.misc_keys_queue.put(key)

        self.current_pressed.clear()

        action_dict = {
            "delta_x": delta_x,
            "delta_y": delta_y,
            "delta_z": delta_z,
        }

        if self.config.use_gripper:
            action_dict["gripper"] = gripper_action

        return action_dict

    def get_teleop_events(self) -> dict[str, Any]:
        """
        Get extra control events from the keyboard such as intervention status,
        episode termination, success indicators, etc.

        Keyboard mappings:
        - Any movement keys pressed = intervention active
        - 's' key = success (terminate episode successfully)
        - 'r' key = rerecord episode (terminate and rerecord)
        - 'q' key = quit episode (terminate without success)

        Returns:
            Dictionary containing:
                - is_intervention: bool - Whether human is currently intervening
                - terminate_episode: bool - Whether to terminate the current episode
                - success: bool - Whether the episode was successful
                - rerecord_episode: bool - Whether to rerecord the episode
        """
        if not self.is_connected:
            return {
                TeleopEvents.IS_INTERVENTION: False,
                TeleopEvents.TERMINATE_EPISODE: False,
                TeleopEvents.SUCCESS: False,
                TeleopEvents.RERECORD_EPISODE: False,
            }

        # Check if any movement keys are currently pressed (indicates intervention)
        movement_keys = [
            keyboard.Key.up,
            keyboard.Key.down,
            keyboard.Key.left,
            keyboard.Key.right,
            keyboard.Key.shift,
            keyboard.Key.shift_r,
            keyboard.Key.ctrl_r,
            keyboard.Key.ctrl_l,
        ]
        is_intervention = any(self.current_pressed.get(key, False) for key in movement_keys)

        # Check for episode control commands from misc_keys_queue
        terminate_episode = False
        success = False
        rerecord_episode = False

        # Process any pending misc keys
        while not self.misc_keys_queue.empty():
            key = self.misc_keys_queue.get_nowait()
            if key == "s":
                success = True
            elif key == "r":
                terminate_episode = True
                rerecord_episode = True
            elif key == "q":
                terminate_episode = True
                success = False

        return {
            TeleopEvents.IS_INTERVENTION: is_intervention,
            TeleopEvents.TERMINATE_EPISODE: terminate_episode,
            TeleopEvents.SUCCESS: success,
            TeleopEvents.RERECORD_EPISODE: rerecord_episode,
        }


class KeyboardRoverTeleop(KeyboardTeleop):
    """
    Keyboard teleoperator for mobile robots like EarthRover Mini Plus.

    Provides intuitive WASD-style controls for driving a mobile robot:
    - Linear movement (forward/backward)
    - Angular movement (turning/rotation)
    - Speed adjustment
    - Emergency stop

    Keyboard Controls:
        Movement:
            - W: Move forward
            - S: Move backward
            - A: Turn left (with forward motion)
            - D: Turn right (with forward motion)
            - Q: Rotate left in place
            - E: Rotate right in place
            - X: Emergency stop

        Speed Control:
            - +/=: Increase speed
            - -: Decrease speed

        System:
            - ESC: Disconnect teleoperator

    Attributes:
        config: Teleoperator configuration
        current_linear_speed: Current linear velocity magnitude
        current_angular_speed: Current angular velocity magnitude

    Example:
        ```python
        from lerobot.teleoperators.keyboard import KeyboardRoverTeleop, KeyboardRoverTeleopConfig

        teleop = KeyboardRoverTeleop(
            KeyboardRoverTeleopConfig(linear_speed=1.0, angular_speed=1.0, speed_increment=0.1)
        )
        teleop.connect()

        while teleop.is_connected:
            action = teleop.get_action()
            robot.send_action(action)
        ```
    """

    config_class = KeyboardRoverTeleopConfig
    name = "keyboard_rover"

    def __init__(self, config: KeyboardRoverTeleopConfig):
        super().__init__(config)
        # Add rover-specific speed settings
        self.current_linear_speed = config.linear_speed
        self.current_angular_speed = config.angular_speed

    @property
    def action_features(self) -> dict:
        """Return action format for rover (linear and angular velocities)."""
        return {
            "linear.vel": float,
            "angular.vel": float,
        }

    @property
    def is_calibrated(self) -> bool:
        """Rover teleop doesn't require calibration."""
        return True

    def _drain_pressed_keys(self):
        """Update current_pressed state from event queue without clearing held keys"""
        while not self.event_queue.empty():
            key_char, is_pressed = self.event_queue.get_nowait()
            if is_pressed:
                self.current_pressed[key_char] = True
            else:
                # Only remove key if it's being released
                self.current_pressed.pop(key_char, None)

    @check_if_not_connected
    def get_action(self) -> RobotAction:
        """
        Get the current action based on pressed keys.

        Returns:
            RobotAction with 'linear.vel' and 'angular.vel' keys
        """
        before_read_t = time.perf_counter()

        self._drain_pressed_keys()

        linear_velocity = 0.0
        angular_velocity = 0.0

        # Check which keys are currently pressed (not released)
        active_keys = {key for key, is_pressed in self.current_pressed.items() if is_pressed}

        # Linear movement (W/S) - these take priority
        if "w" in active_keys:
            linear_velocity = self.current_linear_speed
        elif "s" in active_keys:
            linear_velocity = -self.current_linear_speed

        # Turning (A/D/Q/E)
        if "d" in active_keys:
            angular_velocity = -self.current_angular_speed
            if linear_velocity == 0:  # If not moving forward/back, add slight forward motion
                linear_velocity = self.current_linear_speed * self.config.turn_assist_ratio
        elif "a" in active_keys:
            angular_velocity = self.current_angular_speed
            if linear_velocity == 0:  # If not moving forward/back, add slight forward motion
                linear_velocity = self.current_linear_speed * self.config.turn_assist_ratio
        elif "q" in active_keys:
            angular_velocity = self.current_angular_speed
            linear_velocity = 0  # Rotate in place
        elif "e" in active_keys:
            angular_velocity = -self.current_angular_speed
            linear_velocity = 0  # Rotate in place

        # Stop (X) - overrides everything
        if "x" in active_keys:
            linear_velocity = 0
            angular_velocity = 0

        # Speed adjustment
        if "+" in active_keys or "=" in active_keys:
            self.current_linear_speed += self.config.speed_increment
            self.current_angular_speed += self.config.speed_increment * self.config.angular_speed_ratio
            logging.info(
                f"Speed increased: linear={self.current_linear_speed:.2f}, angular={self.current_angular_speed:.2f}"
            )
        if "-" in active_keys:
            self.current_linear_speed = max(
                self.config.min_linear_speed, self.current_linear_speed - self.config.speed_increment
            )
            self.current_angular_speed = max(
                self.config.min_angular_speed,
                self.current_angular_speed - self.config.speed_increment * self.config.angular_speed_ratio,
            )
            logging.info(
                f"Speed decreased: linear={self.current_linear_speed:.2f}, angular={self.current_angular_speed:.2f}"
            )

        self.logs["read_pos_dt_s"] = time.perf_counter() - before_read_t

        return {
            "linear.vel": linear_velocity,
            "angular.vel": angular_velocity,
        }


class LeKiwiKeyboardTeleop(Teleoperator):
    """
    Keyboard teleoperator for LeKiwi robot (dual arms + base).

    Controls:
        Left Arm (position mode, motors 1-5, normalized [-100, 100]):
            Y/H       - Shoulder pan (joint 1)
            U/J       - Shoulder lift (joint 2)
            I/K       - Elbow flex (joint 3)
            O/L       - Wrist flex (joint 4)
            P / .     - Wrist roll (joint 5)

        Right Arm (position mode, motors 21-25, normalized [-100, 100]):
            T/G       - Shoulder pan (joint 21)
            F/R       - Shoulder lift (joint 22)
            V/B       - Elbow flex (joint 23)
            M/N       - Wrist flex (joint 24)
            C/X       - Wrist roll (joint 25)
            [/]       - Right gripper open/close (joint 26): [ = open, ] = close

        Base (velocity mode, motors 7-9):
            W/S       - Move forward/backward
            A/D       - Strafe left/right
            Q/E       - Rotate left/right in place

        System:
            SPACE     - Emergency stop (set all to 0)
            ESC       - Quit

    Output format:
        Arm positions: [-100, 100] (LeRobot RANGE_M100_100 normalization)
        Base velocities: x.vel, y.vel (m/s), theta.vel (rad/s)
    """

    config_class = KeyboardTeleopConfig
    name = "lekiwi_keyboard"

    def __init__(self, config: KeyboardTeleopConfig):
        super().__init__(config)
        self.config = config

        self.event_queue = Queue()
        self.listener = None
        self.logs = {}
        self.emergency_stop = False

        # --- Left Arm: cumulative normalized positions [-100, 100] ---
        self.arm_pos: dict[str, float] = {
            "arm_shoulder_pan": 0.0,
            "arm_shoulder_lift": 0.0,
            "arm_elbow_flex": 0.0,
            "arm_wrist_flex": 0.0,
            "arm_wrist_roll": 0.0,
            # Right Arm
            "arm_right_shoulder_pan": 0.0,
            "arm_right_shoulder_lift": 0.0,
            "arm_right_elbow_flex": 0.0,
            "arm_right_wrist_flex": 0.0,
            "arm_right_wrist_roll": 0.0,
            "arm_right_gripper": 0.0,
        }

        # Map keys to (motor_name, delta_sign)
        self.arm_key_map = {
            # Left Arm
            "y": ("arm_shoulder_pan", 1),
            "h": ("arm_shoulder_pan", -1),
            "u": ("arm_shoulder_lift", 1),
            "j": ("arm_shoulder_lift", -1),
            "i": ("arm_elbow_flex", 1),
            "k": ("arm_elbow_flex", -1),
            "o": ("arm_wrist_flex", 1),
            "l": ("arm_wrist_flex", -1),
            "p": ("arm_wrist_roll", 1),
            ".": ("arm_wrist_roll", -1),
            # Right Arm
            "t": ("arm_right_shoulder_pan", 1),
            "g": ("arm_right_shoulder_pan", -1),
            "f": ("arm_right_shoulder_lift", 1),
            "r": ("arm_right_shoulder_lift", -1),
            "v": ("arm_right_elbow_flex", 1),
            "b": ("arm_right_elbow_flex", -1),
            "m": ("arm_right_wrist_flex", 1),
            "n": ("arm_right_wrist_flex", -1),
            "c": ("arm_right_wrist_roll", 1),
            "x": ("arm_right_wrist_roll", -1),
            # Right Gripper (ID 26): [ = open (-), ] = close (+)
            "[": ("arm_right_gripper", -1),
            "]": ("arm_right_gripper", 1),
        }

        # --- Base velocity ---
        self.linear_speed = getattr(config, "linear_speed", 0.5)    # m/s
        self.angular_speed = getattr(config, "angular_speed", 1.0)    # rad/s
        self.strafe_speed = getattr(config, "strafe_speed", 0.3)     # m/s

        # --- Current pressed keys ---
        self.pressed_keys: set = set()

    @property
    def action_features(self) -> dict:
        return {
            "dtype": "float32",
            "shape": (14,),
            "names": {
                # Left Arm
                "arm_shoulder_pan.pos": 0,
                "arm_shoulder_lift.pos": 1,
                "arm_elbow_flex.pos": 2,
                "arm_wrist_flex.pos": 3,
                "arm_wrist_roll.pos": 4,
                # Right Arm
                "arm_right_shoulder_pan.pos": 5,
                "arm_right_shoulder_lift.pos": 6,
                "arm_right_elbow_flex.pos": 7,
                "arm_right_wrist_flex.pos": 8,
                "arm_right_wrist_roll.pos": 9,
                # Right Gripper
                "arm_right_gripper.pos": 10,
                # Base
                "x.vel": 11,
                "y.vel": 12,
                "theta.vel": 13,
            },
        }

    @property
    def feedback_features(self) -> dict:
        return {}

    @property
    def is_connected(self) -> bool:
        return PYNPUT_AVAILABLE and isinstance(self.listener, keyboard.Listener) and self.listener.is_alive()

    @property
    def is_calibrated(self) -> bool:
        return True

    @check_if_already_connected
    def connect(self) -> None:
        if PYNPUT_AVAILABLE:
            logging.info("pynput is available - enabling local keyboard listener.")
            self.listener = keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release,
            )
            self.listener.start()
        else:
            logging.info("pynput not available - skipping local keyboard listener.")
            self.listener = None

        # Reset arm to center on connect
        for k in self.arm_pos:
            self.arm_pos[k] = 0.0

    def calibrate(self) -> None:
        pass

    def _on_press(self, key):
        if hasattr(key, "char") and key.char is not None:
            char = key.char.lower()
        elif hasattr(key, "name"):
            char = key.name.lower()
            if char == "space":
                char = "space"
            elif char == "escape":
                char = "esc"
            else:
                return
        else:
            return

        if char not in self.pressed_keys:
            self.pressed_keys.add(char)

    def _on_release(self, key):
        if hasattr(key, "char") and key.char is not None:
            char = key.char.lower()
        elif hasattr(key, "name"):
            char = key.name.lower()
            if char == "space":
                char = "space"
            elif char == "escape":
                char = "esc"
            else:
                return
        else:
            return

        self.pressed_keys.discard(char)

        if char == "space":
            logging.info("Emergency stop triggered!")
            self.emergency_stop = True
            for k in self.arm_pos:
                self.arm_pos[k] = 0.0

        if char == "esc":
            logging.info("ESC pressed, disconnecting.")
            self.disconnect()

    def configure(self) -> None:
        pass

    def sync_arm_position(self, arm_pos: dict[str, float]) -> None:
        """
        Sync the current arm position from robot observation.
        Call this before starting teleop to set the initial position.
        """
        for motor, pos in arm_pos.items():
            if motor in self.arm_pos:
                self.arm_pos[motor] = float(pos)

    def sync_dual_arm_position(self, left_arm_pos: dict[str, float], right_arm_pos: dict[str, float]) -> None:
        """
        Sync the current dual arm positions from robot observation.
        Call this before starting teleop to set the initial position.
        """
        for motor, pos in left_arm_pos.items():
            if motor in self.arm_pos:
                self.arm_pos[motor] = float(pos)
        for motor, pos in right_arm_pos.items():
            if motor in self.arm_pos:
                self.arm_pos[motor] = float(pos)

    @check_if_not_connected
    def get_action(self) -> RobotAction:
        before_read_t = time.perf_counter()

        if self.emergency_stop:
            self.emergency_stop = False
            return self._build_action()

        # --- Update arm positions (cumulative) ---
        delta = getattr(self.config, "arm_delta_deg", 15.0)
        for key, (motor, sign) in self.arm_key_map.items():
            if key in self.pressed_keys:
                self.arm_pos[motor] += sign * delta
                self.arm_pos[motor] = max(-100.0, min(100.0, self.arm_pos[motor]))

        # --- Base velocity ---
        x_vel = 0.0
        y_vel = 0.0
        theta_vel = 0.0
        if "w" in self.pressed_keys:
            x_vel = self.linear_speed
        if "s" in self.pressed_keys:
            x_vel = -self.linear_speed
        if "a" in self.pressed_keys:
            y_vel = self.strafe_speed
        if "d" in self.pressed_keys:
            y_vel = -self.strafe_speed
        if "q" in self.pressed_keys:
            theta_vel = self.angular_speed
        if "e" in self.pressed_keys:
            theta_vel = -self.angular_speed

        self.logs["read_pos_dt_s"] = time.perf_counter() - before_read_t

        return {
            # Left Arm
            "arm_shoulder_pan.pos": self.arm_pos["arm_shoulder_pan"],
            "arm_shoulder_lift.pos": self.arm_pos["arm_shoulder_lift"],
            "arm_elbow_flex.pos": self.arm_pos["arm_elbow_flex"],
            "arm_wrist_flex.pos": self.arm_pos["arm_wrist_flex"],
            "arm_wrist_roll.pos": self.arm_pos["arm_wrist_roll"],
            # Right Arm
            "arm_right_shoulder_pan.pos": self.arm_pos["arm_right_shoulder_pan"],
            "arm_right_shoulder_lift.pos": self.arm_pos["arm_right_shoulder_lift"],
            "arm_right_elbow_flex.pos": self.arm_pos["arm_right_elbow_flex"],
            "arm_right_wrist_flex.pos": self.arm_pos["arm_right_wrist_flex"],
            "arm_right_wrist_roll.pos": self.arm_pos["arm_right_wrist_roll"],
            # Right Gripper
            "arm_right_gripper.pos": self.arm_pos["arm_right_gripper"],
            # Base
            "x.vel": x_vel,
            "y.vel": y_vel,
            "theta.vel": theta_vel,
        }

    def _build_action(self) -> RobotAction:
        return {
            # Left Arm
            "arm_shoulder_pan.pos": self.arm_pos["arm_shoulder_pan"],
            "arm_shoulder_lift.pos": self.arm_pos["arm_shoulder_lift"],
            "arm_elbow_flex.pos": self.arm_pos["arm_elbow_flex"],
            "arm_wrist_flex.pos": self.arm_pos["arm_wrist_flex"],
            "arm_wrist_roll.pos": self.arm_pos["arm_wrist_roll"],
            # Right Arm
            "arm_right_shoulder_pan.pos": self.arm_pos["arm_right_shoulder_pan"],
            "arm_right_shoulder_lift.pos": self.arm_pos["arm_right_shoulder_lift"],
            "arm_right_elbow_flex.pos": self.arm_pos["arm_right_elbow_flex"],
            "arm_right_wrist_flex.pos": self.arm_pos["arm_right_wrist_flex"],
            "arm_right_wrist_roll.pos": self.arm_pos["arm_right_wrist_roll"],
            # Right Gripper
            "arm_right_gripper.pos": self.arm_pos["arm_right_gripper"],
            # Base
            "x.vel": 0.0,
            "y.vel": 0.0,
            "theta.vel": 0.0,
        }

    def send_feedback(self, feedback: dict[str, Any]) -> None:
        pass

    @check_if_not_connected
    def disconnect(self) -> None:
        if self.listener is not None:
            self.listener.stop()
