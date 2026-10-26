"""地面校正：以 0.1 m/s 前進，直到里程顯示 0.5 m 就停（最多 10 秒）。結束一定送停止。"""
import time

import rclpy
from geometry_msgs.msg import Twist
from std_msgs.msg import Float32MultiArray

TARGET = 0.5   # m
SPEED = 0.1    # m/s
TIMEOUT = 10.0  # s

rclpy.init()
node = rclpy.create_node("floor_test")
pub = node.create_publisher(Twist, "cmd_vel", 10)
odom = [None]
node.create_subscription(Float32MultiArray, "odom/odom_raw", lambda m: odom.__setitem__(0, list(m.data)), 10)


def spin_for(sec):
    end = time.time() + sec
    while time.time() < end:
        rclpy.spin_once(node, timeout_sec=0.01)


def stop():
    for _ in range(10):
        pub.publish(Twist())
        spin_for(0.03)


def travelled(start):
    return ((odom[0][0] - start[0]) + (odom[0][1] - start[1])) / 2


try:
    spin_for(1.0)
    start = odom[0]
    msg = Twist()
    msg.linear.x = SPEED
    t0 = time.time()
    while travelled(start) < TARGET and time.time() - t0 < TIMEOUT:
        pub.publish(msg)
        spin_for(0.05)
    stop()
    t_drive = time.time() - t0
    spin_for(1.5)  # 等車子完全停下
    dl, dr = odom[0][0] - start[0], odom[0][1] - start[1]
    print(f"行駛時間 {t_drive:.2f} s（平均 {travelled(start) / t_drive:.3f} m/s）")
    print(f"停止後里程：左 {dl:.3f} m，右 {dr:.3f} m，平均 {(dl + dr) / 2:.3f} m")
finally:
    stop()
    print("已送出停止指令", flush=True)
    node.destroy_node()
    rclpy.shutdown()
