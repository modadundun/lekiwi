import time
import logging
import numpy as np
from rustypot import Scs0009PyController

logger = logging.getLogger(__name__)


class AmazingHandController:
    """
    Continuous gripper controller for AmazingHand.

    LeRobot domain:
        0.0 -> fully open
        1.0 -> fully closed
    """

    def __init__(
        self,
        port: str = "/dev/ttyACM0",
        side: int = 1,  # 1=right, 2=left
        max_speed: int = 7,
        close_speed: int = 3,
        middle_pos_deg=None,
        deadband: float = 0.01,
        min_interval_s: float = 0.03,
        ema_alpha: float = 0.25,
    ):
        self.port = port
        self.side = int(side)
        self.max_speed = int(max_speed)
        self.close_speed = int(close_speed)

        if middle_pos_deg is None:
            middle_pos_deg = [0, 0, -10, 5, -10, 0, -10, 10]
        if len(middle_pos_deg) != 8:
            raise ValueError("middle_pos_deg must have length 8")

        self.middle_pos_deg = np.array(middle_pos_deg, dtype=float)

        self.deadband = float(deadband)
        self.min_interval_s = float(min_interval_s)
        self.alpha = float(ema_alpha)

        # runtime state
        self._last_grip = None
        self._filtered = None
        self._next_send_t = 0.0

        # ================= controller =================
        self.c = Scs0009PyController(
            serial_port=self.port,
            baudrate=1000000,
            timeout=0.5,
        )

        # # enable torque
        # for mid in range(1, 9):
        #     try:
        #         self.c.write_torque_enable(mid, 1)
        #     except Exception as e:
        #         logger.warning(f"Torque enable failed for motor {mid}: {e}")


        # ===== 力矩限制（强烈推荐）=====
        TORQUE_LIMIT = 350      # ⭐ 默认1023，建议300~450
        OVERLOAD_TORQUE = 20    # ⭐ 过载保护
        PROTECTION_CURRENT = 200

        for mid in range(1, 9):
            try:
                # 最大力矩限制
                self.c.write_max_torque(mid, TORQUE_LIMIT)

                # 过载保护
                self.c.write_overload_torque(mid, OVERLOAD_TORQUE)

                # 电流保护（如果固件支持）
                try:
                    self.c.write_protection_current(mid, PROTECTION_CURRENT)
                except Exception:
                    pass

            except Exception as e:
                logger.warning(f"Torque limit set failed for motor {mid}: {e}")


        # ================= relative poses =================
        self.open_pose_deg = np.array(
            [-35, 35, -35, 35, -35, 35, -35, 35], dtype=float
        )
        self.close_pose_deg = np.array(
            [90, -90, 90, -90, 90, -90, 90, -90], dtype=float
        )

        logger.info(f"AmazingHandController ready on {self.port}")

    # ============================================================
    # read state
    # ============================================================
    def get_open_ratio(self) -> float:
        """Estimate current open ratio from motor 1."""
        try:
            pos_rad = self.c.read_present_position(1)
            pos_deg_abs = float(np.rad2deg(pos_rad))

            open_abs = float(self.middle_pos_deg[0] + self.open_pose_deg[0])
            close_abs = float(self.middle_pos_deg[0] + self.close_pose_deg[0])

            if abs(close_abs - open_abs) < 1e-6:
                return 0.0

            ratio = (pos_deg_abs - open_abs) / (close_abs - open_abs)
            return float(np.clip(ratio, 0.0, 1.0))

        except Exception:
            if self._last_grip is not None:
                return float(self._last_grip)
            return 0.0

    # ============================================================
    # main control
    # ============================================================
    def set_grip(self, grip01: float) -> None:
        """Industrial-grade continuous grip control."""

        # ---------- 输入保护 ----------
        grip01 = 1.0 - float(np.clip(grip01, 0.0, 1.0))

        # ---------- deadband ----------
        if self._last_grip is not None:
            if abs(grip01 - self._last_grip) < self.deadband:
                return

        # ---------- EMA smoothing ----------
        if self._filtered is None:
            self._filtered = grip01
        else:
            self._filtered = (
                self.alpha * grip01 + (1 - self.alpha) * self._filtered
            )
        grip01 = self._filtered

        # ---------- rate limit ----------
        now = time.time()
        if now < self._next_send_t:
            return
        self._next_send_t = now + self.min_interval_s

        # ---------- 插值 ----------
        rel_deg = self.open_pose_deg + grip01 * (
            self.close_pose_deg - self.open_pose_deg
        )
        abs_deg = self.middle_pos_deg + rel_deg

        # ⭐ 连续速度（非常关键）
        speed = self.max_speed + grip01 * (
            self.close_speed - self.max_speed
        )

        # ---------- 下发 ----------
        for i, mid in enumerate(range(1, 9)):
            try:
                self.c.write_goal_speed(mid, int(speed))
                self.c.write_goal_position(mid, np.deg2rad(abs_deg[i]))
            except Exception as e:
                logger.warning(f"AmazingHand motor {mid} write failed: {e}")

        self._last_grip = grip01
