"""架高測試：送固定 /cmd_vel，每 0.25 秒由 /odom/odom_raw 算出左右輪實際速度。"""
import time

import rclpy
from geometry_msgs.msg import Twist
from std_msgs.msg import Float32MultiArray

rclpy.init()
node = rclpy.create_node("speed_test")
pub = node.create_publisher(Twist, "cmd_vel", 10)
odom = [None]
node.create_subscription(Float32MultiArray, "odom/odom_raw", lambda m: odom.__setitem__(0, list(m.data)), 10)


def spin_for(sec):
    end = time.time() + sec
    while time.time() < end:
        rclpy.spin_once(node, timeout_sec=0.02)


def stop():
    for _ in range(5):
        pub.publish(Twist())
        spin_for(0.05)


def run(name, x, z, sec=3.0):
    msg = Twist()
    msg.linear.x, msg.angular.z = x, z
    print(f"== {name}  (cmd x={x} z={z})", flush=True)
    t0 = time.time()
    prev, prev_t = odom[0], t0
    while time.time() - t0 < sec:
        pub.publish(msg)
        spin_for(0.25)
        now = time.time()
        cur = odom[0]
        vl = (cur[0] - prev[0]) / (now - prev_t)
        vr = (cur[1] - prev[1]) / (now - prev_t)
        print(f"  t={now - t0:4.2f}s  左 {vl:+.3f} m/s  右 {vr:+.3f} m/s", flush=True)
        prev, prev_t = cur, now
    stop()
    spin_for(1.0)


try:
    spin_for(1.0)
    run("前進", 0.1, 0.0)
    run("原地左轉 1.0", 0.0, 1.0)
    run("原地右轉 1.0", 0.0, -1.0)
finally:
    stop()
    print("已送出停止指令", flush=True)
    node.destroy_node()
    rclpy.shutdown()
