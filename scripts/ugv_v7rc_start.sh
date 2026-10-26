#!/bin/bash
# Runs inside the ugv_rpi_ros_humble container (started by ugv-v7rc.service on the host).
# Starts the UGV base nodes and the V7RC bridge, and stops them all when this script is stopped.
source /opt/ros/humble/setup.bash
source /home/ws/ugv_ws/install/setup.bash
export UGV_MODEL=ugv_rover LDLIDAR_MODEL=ld19

# Clean up copies left over from a manual start
pkill -f "lib/ugv_bringup/ugv_bringup|lib/ugv_bringup/ugv_driver|lib/v7rc_bridge/v7rc_bridge"
sleep 1

LOG=/tmp/ugv_v7rc
mkdir -p $LOG
ros2 run ugv_bringup ugv_bringup > $LOG/ugv_bringup.log 2>&1 &
ros2 run ugv_bringup ugv_driver > $LOG/ugv_driver.log 2>&1 &
ros2 run v7rc_bridge v7rc_bridge > $LOG/v7rc_bridge.log 2>&1 &

trap 'kill $(jobs -p) 2>/dev/null; wait; exit 0' TERM INT
echo "UGV base + V7RC bridge started, logs in $LOG"
# If any node exits, stop the rest so systemd restarts everything together
wait -n
echo "A node exited, stopping the others"
kill $(jobs -p) 2>/dev/null
wait
exit 1
