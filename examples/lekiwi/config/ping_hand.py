#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
最小测试：检查 COM6 上能不能 ping 到 SCS0009 舵机（ID 11-18）
直接用 scservo_sdk，绕过 LeRobot 握手逻辑
"""
import sys, os

script_dir = os.path.dirname(os.path.abspath(__file__))
lerobot_dir = os.path.dirname(os.path.dirname(script_dir))
src_dir = os.path.join(lerobot_dir, "src")
sys.path.insert(0, src_dir)

from lerobot.motors.feetech import FeetechMotorsBus
from lerobot.motors import Motor, MotorNormMode

PORT = "COM6"
PROTOCOL = 1
IDS = list(range(11, 19))

print(f"创建总线对象：{PORT}，protocol={PROTOCOL}")
print("=" * 50)

motors = {}
for mid in IDS:
    motors[f"hand_{mid}"] = Motor(mid, "scs0009", MotorNormMode.RANGE_0_100)

bus = FeetechMotorsBus(port=PORT, motors=motors, protocol_version=PROTOCOL)

# 手动打开端口，绕过 handshake
import scservo_sdk as scs
bus.port_handler = scs.PortHandler(PORT)
bus.packet_handler = scs.PacketHandler(PROTOCOL)
bus.port_handler.openPort()
bus.port_handler.setBaudRate(1_000_000)
print(f"✓ {PORT} 打开成功（波特率 1M）\n")

# 逐个 ping
print("逐个 Ping ID 11~18：")
found = {}
for mid in IDS:
    model_number, comm, error = bus.packet_handler.ping(bus.port_handler, mid)
    if comm == scs.COMM_SUCCESS:
        print(f"  ✓ ID {mid}: model={model_number}, error=0x{error:02X}")
        found[mid] = model_number
    else:
        print(f"  ✗ ID {mid}: 无响应 (comm={comm})")

print(f"\n找到 {len(found)}/{len(IDS)} 个舵机：{found}")

# 尝试读位置（验证通信）
if found:
    print("\n读取找到舵机的当前位置（Present_Position）：")
    for mid in found:
        # Present_Position 地址 = 56，长度 = 2 字节
        data = scs.Uint16Param()
        comm = bus.packet_handler.read2ByteTxRx(bus.port_handler, mid, 56, data)
        if comm == scs.COMM_SUCCESS:
            print(f"  ID {mid}: position={data.value}")
        else:
            print(f"  ID {mid}: 读取失败 (comm={comm})")

bus.port_handler.closePort()
print("\n完成。")
