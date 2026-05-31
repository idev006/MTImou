"""
stream.py — รับ stream จาก IMOU Ranger 2 ผ่าน Dahua P2P
ไม่ต้องมีเครื่องกลาง ไม่เสียค่าใช้จ่าย ใช้ได้จากทุกที่

ใช้งาน:
    python stream.py

ต้องแก้ค่า CONFIG ด้านล่างก่อน
"""

import os
import sys
import time
import logging

# ── กำหนดค่าของกล้อง ──────────────────────────────────────────
CONFIG = {
    "serial":    "6L3BXXXXXXXX",   # Serial Number จาก IMOU Life App
    "username":  "admin",
    "password":  "YOUR_PASSWORD",  # รหัสผ่านกล้อง
    "channel":   1,
    "subtype":   0,                # 0=main stream (HD), 1=sub stream (ความละเอียดต่ำ)
    "local_port": 1554,
    "timeout":   30,               # วินาที รอ tunnel พร้อม
    "show_window": True,           # False = headless (ไม่แสดงหน้าต่าง)
    "save_video": False,           # True = บันทึก output.mp4 ด้วย
}
# ────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s — %(message)s",
    datefmt="%H:%M:%S"
)

def check_dependencies():
    missing = []
    try:
        import cv2
    except ImportError:
        missing.append("opencv-python")
    if missing:
        print("❌ ขาด dependencies:")
        for m in missing:
            print(f"   pip install {m}")
        sys.exit(1)

def check_binary():
    import shutil, platform
    name = "dh-p2p" + (".exe" if platform.system().lower() == "windows" else "")
    here = os.path.join(os.path.dirname(__file__), name)
    path = shutil.which("dh-p2p")
    if not os.path.exists(here) and not path:
        print("❌ ไม่พบ dh-p2p binary")
        print("   รัน: python setup.py  เพื่อดาวน์โหลด")
        print("   หรือ build เอง: https://github.com/khoanguyen-3fc/dh-p2p")
        sys.exit(1)

def validate_config(cfg):
    if "XXXXXXXX" in cfg["serial"]:
        print("❌ กรุณาแก้ไข serial ใน CONFIG ก่อน")
        sys.exit(1)
    if cfg["password"] == "YOUR_PASSWORD":
        print("❌ กรุณาแก้ไข password ใน CONFIG ก่อน")
        sys.exit(1)

def main():
    check_dependencies()
    check_binary()
    validate_config(CONFIG)

    import cv2
    from tunnel import DHP2PTunnel

    # ── เริ่ม P2P tunnel ─────────────────────────────────────────
    tunnel = DHP2PTunnel(
        serial=CONFIG["serial"],
        username=CONFIG["username"],
        password=CONFIG["password"],
        local_port=CONFIG["local_port"],
        auto_restart=True,
    )

    tunnel.start()
    print(f"⏳ รอ tunnel พร้อม (สูงสุด {CONFIG['timeout']} วินาที)...")

    if not tunnel.wait_ready(timeout=CONFIG["timeout"]):
        print("❌ Tunnel ไม่พร้อม — ตรวจสอบ:")
        print("   • Serial Number ถูกต้องไหม")
        print("   • กล้องต่อ internet อยู่ไหม (ตรวจใน IMOU Life App)")
        print("   • network ของเครื่องนี้ออก internet ได้ไหม")
        tunnel.stop()
        sys.exit(1)

    rtsp_url = tunnel.rtsp_url(channel=CONFIG["channel"], subtype=CONFIG["subtype"])
    print(f"✅ Tunnel พร้อม — RTSP URL: {rtsp_url}")

    # ── เปิด RTSP stream ─────────────────────────────────────────
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"

    cap = None
    writer = None
    reconnect_delay = 2
    frame_count = 0

    def open_capture():
        c = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
        if c.isOpened():
            w  = int(c.get(cv2.CAP_PROP_FRAME_WIDTH))
            h  = int(c.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = c.get(cv2.CAP_PROP_FPS) or 15.0
            print(f"📹 stream เปิดแล้ว: {w}×{h} @ {fps:.1f}fps")
            return c, w, h, fps
        c.release()
        return None, 0, 0, 15.0

    print("📺 เปิด video stream...")
    cap, W, H, FPS = open_capture()
    if cap is None:
        # ลอง subtype=1 (sub stream)
        print("⚠️  Main stream ไม่ได้ — ลอง sub stream...")
        old = CONFIG["subtype"]
        CONFIG["subtype"] = 1
        rtsp_url = tunnel.rtsp_url(channel=CONFIG["channel"], subtype=1)
        cap, W, H, FPS = open_capture()
        if cap is None:
            print("❌ ไม่สามารถเปิด stream ได้เลย")
            tunnel.stop()
            sys.exit(1)

    # ── setup VideoWriter (optional) ─────────────────────────────
    if CONFIG["save_video"] and W > 0:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter("output.mp4", fourcc, FPS, (W, H))
        print("🎬 บันทึก video ไปที่ output.mp4")

    # ── main loop ────────────────────────────────────────────────
    print("▶  กด Q เพื่อออก")
    fail_count = 0

    try:
        while True:
            ret, frame = cap.read()

            if not ret:
                fail_count += 1
                print(f"⚠️  อ่าน frame ไม่ได้ (ครั้งที่ {fail_count}) — reconnect...")
                cap.release()
                time.sleep(reconnect_delay)

                # ถ้า tunnel หลุดด้วย รอให้ restart
                if not tunnel._check_port():
                    print("🔄 รอ tunnel reconnect...")
                    tunnel.wait_ready(timeout=20)

                cap, W, H, FPS = open_capture()
                if cap is None:
                    time.sleep(reconnect_delay)
                continue

            fail_count = 0
            frame_count += 1

            if CONFIG["save_video"] and writer:
                writer.write(frame)

            if CONFIG["show_window"]:
                # overlay: FPS counter
                cv2.putText(frame, f"Frame: {frame_count}", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.imshow("IMOU Ranger 2 — P2P Stream", frame)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), ord("Q"), 27):  # Q หรือ ESC
                    break

    except KeyboardInterrupt:
        print("\n⏹  หยุดโดย Ctrl+C")

    finally:
        if cap:
            cap.release()
        if writer:
            writer.release()
        if CONFIG["show_window"]:
            cv2.destroyAllWindows()
        tunnel.stop()
        print(f"✅ จบ — อ่านไปทั้งหมด {frame_count} frames")


if __name__ == "__main__":
    main()
