#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
LeKiWi 标定脚本
运行一次标定，之后所有脚本都能正常使用归一化功能。
"""

import sys
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
lerobot_dir = os.path.dirname(os.path.dirname(script_dir))
src_dir = os.path.join(lerobot_dir, "src")
sys.path.insert(0, src_dir)
sys.path.insert(0, lerobot_dir)

from lerobot.robots.lekiwi import LeKiwi, LeKiwiConfig


def main():
    print("=" * 60)
    print("LeKiWi 标定工具")
    print("=" * 60)

    robot_config = LeKiwiConfig(
        port="COM3",  # 修改为你的串口号
        id="my_lekiwi",
        disable_torque_on_disconnect=True,
        cameras={},
    )

    robot = LeKiwi(robot_config)

    print("\n步骤说明：")
    print("  1. 上电后，手臂会保持当前位置")
    print("  2. 程序将关闭手臂力矩，请手动把手臂摆到中间位置")
    print("  3. 按回车确认中间位（设置归零偏移）")
    print("  4. 然后手动把每个关节走到最大/最小极限")
    print("  5. 走完后按回车，程序记录范围并完成标定")
    print("=" * 60)

    input("\n按回车开始标定...")

    robot.connect(calibrate=True)

    print("\n✓ 标定完成！标定文件已保存到：")
    print(f"  {robot.calibration_fpath}")
    print("\n之后运行遥操作脚本时，使用 connect(calibrate=True)")
    print("程序会自动加载标定文件，不需要重新标定。")

    robot.disconnect()


if __name__ == "__main__":
    main()
