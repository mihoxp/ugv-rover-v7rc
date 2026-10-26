"""架高測試：送 /cmd_vel，觀察 /odom/odom_raw 左右輪里程變化。結束一定送停止。"""
import time

import rclpy
from geometry_msgs.msg import Twist
from std_msgs.msg import Float32MultiArray

rclpy.init()
node = rclpy.create_node("motion_test")
pub = node.create_publisher(Twist, "cmd_vel", 10)
odom = [None]
node.create_subscription(Float32MultiArray, "odom/odom_raw", lambda m: odom.__setitem__(0, list(m.data)), 10)


def spin_for(sec):
    end = time.time() + sec
    while time.time() < end:
        rclpy.spin_once(node, timeout_sec=0.02)


def drive(x, z, sec):
    msg = Twist()
    msg.linear.x, msg.angular.z = x, z
    end = time.time() + sec
    while time.time() < end:
        pub.publish(msg)
        spin_for(0.1)


def stop():
    for _ in range(5):
        pub.publish(Twist())
        spin_for(0.05)


def run(name, x, z, sec, expect):
    spin_for(0.5)
    before = odom[0]
    drive(x, z, sec)
    stop()
    spin_for(1.0)  # 等輪子停下、里程穩定
    after = odom[0]
    dl, dr = after[0] - before[0], after[1] - before[1]
    print(f"{name}: 左輪 {dl:+.3f} m, 右輪 {dr:+.3f} m   (預期約 {expect})", flush=True)


try:
    spin_for(1.0)
    if odom[0] is None:
        raise SystemExit("沒有收到 /odom/odom_raw，ugv_bringup 沒在跑？")
    run("前進 0.1 m/s x 2 s", 0.1, 0.0, 2.0, "左右都 +0.20")
    run("原地左轉 0.5 rad/s x 2 s", 0.0, 0.5, 2.0, "左 -0.09、右 +0.09")
    run("後退 0.1 m/s x 2 s", -0.1, 0.0, 2.0, "左右都 -0.20")
finally:
    stop()
    print("已送出停止指令", flush=True)
    node.destroy_node()
    rclpy.shutdown()
