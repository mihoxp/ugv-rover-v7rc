# UGV Rover：ROS2 + V7RC 遙控（General Driver 驅動板版）

讓 Waveshare **UGV Rover**（Raspberry Pi 4 + **General Driver for Robots** 驅動板）可以：

- 在 Docker 裡的 **ROS2 Humble** 讀取 IMU、電池電壓、編碼器里程，並用 `/cmd_vel` 控制馬達
- 用手機 **V7RC App** 遙控，支援 **WiFi（UDP）** 與 **藍牙（BLE）**
- 開機自動啟動

## 背景

Waveshare 的 ROS2 套件（`ugv_ws`，在 Docker 映像 `dudulrx0601/ugv_rpi_ros_humble` 裡）是配合 **ROS Driver** 驅動板與
`ugv_base_ros` 韌體寫的（IMU：ICM-20948，回報含 `ax..mz`、`odl/odr`）。

這台車用的是 **General Driver** 驅動板（IMU：QMI8658 + AK09918），韌體是 `ugv_base_general`，
`T:1001` 回報只有 `L, R`（編碼器輪速 m/s）、`r, p, y`、`temp`、`v`，直接跑 `ugv_bringup` 會 `KeyError: 'ax'`。
`ugv_base_ros` 的所有版本都只支援 ICM-20948，所以改在 Pi 端轉接，不動韌體。

## 架構

```
手機 V7RC ──WiFi UDP:6188──────────────┐
手機 V7RC ──BLE (Nordic UART)──> v7rc_ble_relay.py ──UDP 127.0.0.1:6188──┐
                                                                  ▼
                       ┌──────────── Docker: ugv_rpi_ros_humble ────────────┐
                       │ v7rc_bridge ──/cmd_vel──> ugv_driver ──┐            │
                       │                                        │ /dev/ttyAMA0
                       │ ugv_bringup (已修改) <── T:1001/T:1002 ─┤ ──> ESP32 驅動板
                       │   └─> /imu/data_raw /imu/mag /odom/odom_raw /voltage │
                       └─────────────────────────────────────────────────────┘
```

## 目錄

| 路徑 | 說明 |
|---|---|
| `ugv_bringup_patch/ugv_bringup_general_driver.patch` | 讓 `ugv_bringup` 支援 General Driver 韌體的修改（對 Waveshare 原檔的 patch） |
| `ros2_ws/src/v7rc_bridge/` | ROS2 套件：V7RC（車輛模式 `SRV`）→ `/cmd_vel`，含斷線停車 |
| `scripts/ugv_v7rc_start.sh` | 在容器內啟動 `ugv_bringup`、`ugv_driver`、`v7rc_bridge` |
| `scripts/v7rc_ble_relay.py` | 主機端 BLE 服務（BlueZ D-Bus），把 V7RC 藍牙指令轉成 UDP |
| `systemd/ugv-v7rc.service` | 開機啟動容器與 ROS2 節點 |
| `systemd/v7rc-ble.service` | 開機啟動 BLE 轉接 |
| `tools/` | 測試工具：序列埠探測、架高馬達測試、地面校正、轉向記錄 |

## ugv_bringup 修改內容

- 啟動時送 `{"T":143,"cmd":0}`（關回音）、`{"T":131,"cmd":1}`（開持續回報）
- 看門狗：1 秒沒收到回報就重送上述指令（驅動板斷電重開後自動恢復）
- 序列埠讀取逾時就返回，讓 ROS timer 能執行
- 每收到 `T:1001`：輪速 `L/R`（m/s）× 時間積分成里程 `odl/odr`（cm），並送 `{"T":126}` 查 IMU
- 收到 `T:1002`：加速度 mg → 8192/g、角速度 °/s → 16.4/(°/s)，維持原本發布程式的單位
- 地面校正：`ODOM_SCALE = 0.50 / 0.519`（量測 50 cm，里程顯示 51.9 cm）

## v7rc_bridge 參數

| 參數 | 預設 | 說明 |
|---|---|---|
| `port` | 6188 | UDP 埠 |
| `max_linear` | 0.3 | 最高前後速度 (m/s) |
| `max_angular` | 3.0 | 最高轉速 (rad/s)；1.5 時原地轉輪子推不動 |
| `min_spin_wheel_speed` | 0.18 | 原地轉時每輪最低速度 (m/s)，輕推也能轉 |
| `spin_linear_limit` | 0.03 | 前後速度低於此值視為原地轉 |
| `track_width` | 0.172 | 輪距 (m) |
| `deadband` | 0.06 | 搖桿死區（滿行程比例） |
| `timeout` | 0.5 | 幾秒沒收到封包就停車 |
| `steer_span` / `throttle_span` | 500 / 500 | 1500 到推到底的數值差 |
| `invert_linear` / `invert_angular` | false / true | 方向反轉 |
| `log_channels` | false | 記錄 App 送出的 CH1/CH2 |

## 安裝（在 Pi 上，使用者 `ws`）

> 前提：Waveshare UGV Rover 映像，`~/ugv_ws` 與容器 `ugv_rpi_ros_humble` 已存在。

1. **停用網頁 App**（`app.py` 會佔用 `/dev/ttyAMA0`）：
   ```bash
   crontab -l > ~/crontab.bak
   crontab -l | sed 's|^@reboot .*ugv_rpi/app.py|#&|' | crontab -
   ```
2. **套用 patch 與複製套件**（先備份原檔）：
   ```bash
   cp ~/ugv_ws/src/ugv_main/ugv_bringup/ugv_bringup/ugv_bringup.py ~/ugv_bringup.py.orig
   cd ~/ugv_ws && git apply /path/to/ugv_bringup_patch/ugv_bringup_general_driver.patch
   cp -r /path/to/ros2_ws/src/v7rc_bridge ~/ugv_ws/src/
   cp /path/to/scripts/ugv_v7rc_start.sh /path/to/scripts/v7rc_ble_relay.py ~/ugv_ws/
   chmod +x ~/ugv_ws/ugv_v7rc_start.sh
   ```
3. **在容器內編譯**：
   ```bash
   sudo docker start ugv_rpi_ros_humble
   sudo docker exec -w /home/ws/ugv_ws ugv_rpi_ros_humble bash -c \
     "source /opt/ros/humble/setup.bash && colcon build --packages-select ugv_bringup v7rc_bridge"
   ```
4. **開機自動啟動（WiFi 模式）**：
   ```bash
   sudo cp systemd/ugv-v7rc.service /etc/systemd/system/
   sudo systemctl daemon-reload && sudo systemctl enable --now ugv-v7rc
   ```
   容器會掛載桌面音訊 socket `/run/user/1000/pulse/native`，所以服務會等 `ws` 桌面登入後才啟動容器（需要桌面自動登入）。
5. **藍牙（選用）**：Pi 4 內建藍牙預設和 `ttyAMA0` 共用，Waveshare 映像用 `disable-bt` 關掉了。
   改成讓藍牙走 mini-UART，驅動板維持在 `ttyAMA0`。編輯 `/boot/firmware/config.txt`（先備份）：
   ```
   dtparam=uart0=on
   dtoverlay=miniuart-bt   # 取代 dtoverlay=disable-bt
   core_freq=500
   core_freq_min=500
   ```
   解除 rfkill 封鎖並啟用服務，然後重開機：
   ```bash
   sudo systemctl enable bluetooth
   echo 0 | sudo tee /sys/class/rfkill/rfkill0/soft
   echo 0 | sudo tee /var/lib/systemd/rfkill/platform-fe215040.serial:bluetooth
   sudo cp systemd/v7rc-ble.service /etc/systemd/system/
   sudo systemctl daemon-reload && sudo systemctl enable v7rc-ble
   sudo reboot
   ```

## V7RC App 設定

- 介面：**車輛（Car）** 模式（`SRV` 指令）
- **WiFi**：IP `192.168.0.107`（AccessPopup 熱點模式時 `192.168.50.5`），埠 `6188`
- **藍牙**：掃描並選 **`UGV-Rover`**（不需在系統設定配對）
- 不要同時用 WiFi 與藍牙遙控

## 常用指令

```bash
systemctl status ugv-v7rc v7rc-ble
sudo journalctl -u v7rc-ble -f
sudo docker exec ugv_rpi_ros_humble tail -f /tmp/ugv_v7rc/v7rc_bridge.log
sudo systemctl restart ugv-v7rc
```

## 測試紀錄

| 項目 | 結果 |
|---|---|
| IMU | 約 35.7 Hz，靜止 z ≈ 9.72 m/s² |
| 電池 | 11.1–11.5 V |
| 地面直線 0.1 m/s | 里程 0.519 m / 實測約 0.50 m → 校正係數 0.963 |
| 原地轉 1.5 rad/s（每輪 0.13 m/s） | 輪子卡住 → 改為 3.0 rad/s 與最低輪速 0.18 m/s |
| 原地轉輕推（z ≈ 2.2–2.6） | 每輪實際 0.10–0.18 m/s，持續轉動 |

## 已知限制

- 里程由編碼器輪速積分，非原始脈衝計數；長距離會累積誤差
- 車上沒有光達與攝影機，無法 SLAM / 導航
- 官方 `UGV_RoverFACTORY-260706` 韌體是 ICM-20948 版，**不適用** General Driver（燒錄後會卡在 IMU 初始化）
