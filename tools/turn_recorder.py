"""記錄 90 秒：每 0.25 秒印出目前 /cmd_vel 指令，以及由 /odom/odom_raw 算出的左右輪實際速度。"""
import time

import rclpy
from geometry_msgs.msg import Twist
from std_msgs.msg import Float32MultiArray

TRACK_WIDTH = 0.172  # m, UGV Rover

rclpy.init()
node = rclpy.create_node("turn_recorder")
cmd = [0.0, 0.0]
odom = [None]
node.create_subscription(Twist, "cmd_vel", lambda m: cmd.__setitem__(slice(0, 2), [m.linear.x, m.angular.z]), 10)
node.create_subscription(Float32MultiArray, "odom/odom_raw", lambda m: odom.__setitem__(0, list(m.data)), 10)

t0 = time.time()
prev, prev_t = None, None
while time.time() - t0 < 90:
    rclpy.spin_once(node, timeout_sec=0.02)
    now = time.time()
    if odom[0] is None or (prev_t and now - prev_t < 0.25):
        continue
    if prev is not None:
        vl = (odom[0][0] - prev[0]) / (now - prev_t)
        vr = (odom[0][1] - prev[1]) / (now - prev_t)
        x, z = cmd
        want_l, want_r = x - z * TRACK_WIDTH / 2, x + z * TRACK_WIDTH / 2
        if abs(x) > 0.01 or abs(z) > 0.01 or abs(vl) > 0.01 or abs(vr) > 0.01:
            print(f"{now - t0:5.1f}s cmd x={x:+.2f} z={z:+.2f} | 目標 左{want_l:+.3f} 右{want_r:+.3f} | 實際 左{vl:+.3f} 右{vr:+.3f}", flush=True)
    prev, prev_t = list(odom[0]), now
node.destroy_node()
rclpy.shutdown()
