"""
tunnel.py — จัดการ dh-p2p process (Dahua P2P → RTSP localhost tunnel)
รัน binary ใน background พร้อม auto-restart เมื่อ crash
"""
import subprocess
import threading
import platform
import time
import os
import sys
import socket
import logging

logger = logging.getLogger("tunnel")

BINARY_NAME = "dh-p2p" + (".exe" if platform.system().lower() == "windows" else "")
BINARY_PATH = os.path.join(os.path.dirname(__file__), BINARY_NAME)

# ถ้าไม่มีในโฟลเดอร์เดียวกัน ลองหาใน PATH
if not os.path.exists(BINARY_PATH):
    import shutil
    found = shutil.which("dh-p2p")
    if found:
        BINARY_PATH = found


class DHP2PTunnel:
    """
    เปิด tunnel จาก Dahua P2P cloud มาเป็น RTSP localhost

    ใช้งาน:
        tunnel = DHP2PTunnel(serial="6L3BXXXXXXXX", username="admin", password="pass")
        tunnel.start()
        # รอให้พร้อม
        if tunnel.wait_ready():
            # ต่อ RTSP ได้ที่ rtsp://admin:pass@127.0.0.1:1554/cam/realmonitor?channel=1&subtype=0
            ...
        tunnel.stop()
    """

    def __init__(self, serial: str, username: str, password: str,
                 local_port: int = 1554, remote_port: int = 554,
                 auto_restart: bool = True):
        self.serial      = serial
        self.username    = username
        self.password    = password
        self.local_port  = local_port
        self.remote_port = remote_port
        self.auto_restart = auto_restart

        self._proc: subprocess.Popen | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._ready_event = threading.Event()
        self.running = False

    # ------------------------------------------------------------------
    def _build_cmd(self) -> list[str]:
        """สร้าง command ที่ใช้รัน dh-p2p"""
        if not os.path.exists(BINARY_PATH):
            raise FileNotFoundError(
                f"ไม่พบ dh-p2p binary ที่: {BINARY_PATH}\n"
                "กรุณารัน setup.py ก่อน หรือดาวน์โหลด binary ด้วยตนเอง"
            )
        return [
            BINARY_PATH,
            "--port", f"127.0.0.1:{self.local_port}:{self.remote_port}",
            self.serial,
        ]

    # ------------------------------------------------------------------
    def _run_loop(self):
        """รันใน thread แยก — auto-restart เมื่อ process ตาย"""
        consecutive_fails = 0
        while not self._stop_event.is_set():
            cmd = self._build_cmd()
            logger.info(f"🔄 เริ่ม tunnel: {' '.join(cmd)}")
            try:
                self._proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )
                # อ่าน stdout เพื่อตรวจสอบ
                for line in self._proc.stdout:
                    line = line.rstrip()
                    if line:
                        logger.debug(f"[dh-p2p] {line}")
                    # ถ้า process พิมพ์ว่า listening หรือ ready
                    if any(kw in line.lower() for kw in ["listening", "ready", "accept", "bind"]):
                        self._ready_event.set()

                self._proc.wait()
                ret = self._proc.returncode
                logger.warning(f"⚠️  dh-p2p หยุด (exit code {ret})")
                consecutive_fails += 1

            except Exception as e:
                logger.error(f"❌ Error รัน tunnel: {e}")
                consecutive_fails += 1

            if self._stop_event.is_set():
                break

            if not self.auto_restart:
                break

            # backoff ถ้า crash ติดกันหลายครั้ง
            wait = min(3 * consecutive_fails, 30)
            logger.info(f"⏳ restart ใน {wait} วินาที...")
            self._stop_event.wait(timeout=wait)

            # ถ้า port พร้อมใช้ได้จริงแล้วก็ถือว่า ready
            if self._check_port():
                self._ready_event.set()
                consecutive_fails = 0

    # ------------------------------------------------------------------
    def _check_port(self, timeout: float = 1.0) -> bool:
        """ตรวจว่า localhost:local_port ตอบสนองหรือยัง"""
        try:
            with socket.create_connection(("127.0.0.1", self.local_port), timeout=timeout):
                return True
        except OSError:
            return False

    # ------------------------------------------------------------------
    def start(self):
        """เริ่ม tunnel (non-blocking)"""
        if self.running:
            logger.warning("Tunnel รันอยู่แล้ว")
            return
        self._stop_event.clear()
        self._ready_event.clear()
        self.running = True

        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="dh-p2p-tunnel")
        self._thread.start()
        logger.info(f"🚀 Tunnel เริ่มแล้ว — รอ port {self.local_port}...")

    # ------------------------------------------------------------------
    def wait_ready(self, timeout: float = 20.0) -> bool:
        """
        รอจนกว่า tunnel จะพร้อม (port เปิดแล้ว)
        คืนค่า True ถ้าพร้อม, False ถ้า timeout
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self._check_port(timeout=1.0):
                self._ready_event.set()
                logger.info(f"✅ Tunnel พร้อมแล้วที่ 127.0.0.1:{self.local_port}")
                return True
            time.sleep(1)
        logger.error(f"❌ Tunnel ไม่พร้อมภายใน {timeout} วินาที")
        return False

    # ------------------------------------------------------------------
    def stop(self):
        """หยุด tunnel"""
        self._stop_event.set()
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        self.running = False
        logger.info("🛑 Tunnel หยุดแล้ว")

    # ------------------------------------------------------------------
    def rtsp_url(self, channel: int = 1, subtype: int = 0) -> str:
        """คืน RTSP URL ที่ใช้เชื่อมต่อ"""
        return (
            f"rtsp://{self.username}:{self.password}"
            f"@127.0.0.1:{self.local_port}"
            f"/cam/realmonitor?channel={channel}&subtype={subtype}"
        )

    # ------------------------------------------------------------------
    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *_):
        self.stop()
