import time
import serial

s = serial.Serial("/dev/ttyAMA0", 115200, timeout=0.2)


def send(cmd, sec=1.0):
    s.reset_input_buffer()
    s.write((cmd + "\n").encode())
    buf, t = b"", time.time()
    while time.time() - t < sec:
        buf += s.read(4096)
    lines = [l for l in buf.decode(errors="replace").splitlines() if l.strip()]
    print(f"{cmd} ->")
    for l in lines[:3]:
        print("   ", l[:300])


send('{"T":131,"cmd":0}', 0.5)  # stop continuous feedback so replies are readable
send('{"T":126}')               # IMU data
send('{"T":130}')               # base feedback
send('{"T":4,"cmd":0}')         # module type query (no-op if unsupported)
send('{"T":131,"cmd":1}', 0.3)  # turn continuous feedback back on
