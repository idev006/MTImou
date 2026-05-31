"""
setup.py — ดาวน์โหลด dh-p2p binary ให้ถูก platform อัตโนมัติ
รันครั้งเดียวก่อนใช้งาน
"""
import sys
import os
import stat
import platform
import urllib.request

REPO = "https://github.com/khoanguyen-3fc/dh-p2p"
# Releases URL format (ปรับตาม tag ที่มีจริง — ใช้ latest API)
RELEASE_API = "https://api.github.com/repos/khoanguyen-3fc/dh-p2p/releases/latest"

BINARY_NAME = "dh-p2p"
BINARY_PATH = os.path.join(os.path.dirname(__file__), BINARY_NAME)

def detect_platform():
    system = platform.system().lower()
    machine = platform.machine().lower()
    if system == "linux":
        if "aarch64" in machine or "arm64" in machine:
            return "dh-p2p-linux-aarch64"
        return "dh-p2p-linux-x86_64"
    elif system == "darwin":
        if "arm64" in machine:
            return "dh-p2p-macos-aarch64"
        return "dh-p2p-macos-x86_64"
    elif system == "windows":
        return "dh-p2p-windows-x86_64.exe"
    else:
        raise RuntimeError(f"Unsupported platform: {system}/{machine}")

def download_binary():
    if os.path.exists(BINARY_PATH):
        print(f"✅ Binary มีอยู่แล้ว: {BINARY_PATH}")
        return True

    print("📥 กำลังดาวน์โหลด dh-p2p binary...")

    # ดึง latest release info
    import json
    try:
        req = urllib.request.Request(RELEASE_API, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            release = json.loads(resp.read())
    except Exception as e:
        print(f"❌ ไม่สามารถดึง release info ได้: {e}")
        print(f"   กรุณาดาวน์โหลด binary ด้วยตนเองจาก: {REPO}/releases")
        return False

    asset_name = detect_platform()
    assets = release.get("assets", [])
    url = None
    for asset in assets:
        if asset["name"] == asset_name:
            url = asset["browser_download_url"]
            break

    if not url:
        # ถ้าไม่มี prebuilt binary (repo นี้ยังไม่มี releases)
        print("⚠️  ไม่พบ prebuilt binary ใน releases")
        print(f"   repo: {REPO}")
        print("")
        print("   วิธีแก้: build จาก source ด้วย Rust:")
        print("   1. ติดตั้ง Rust: https://rustup.rs")
        print("   2. git clone https://github.com/khoanguyen-3fc/dh-p2p")
        print("   3. cd dh-p2p && cargo build --release")
        print("   4. copy target/release/dh-p2p มาไว้ใน folder นี้")
        return False

    print(f"   ดาวน์โหลด: {asset_name}")
    output_path = BINARY_PATH
    if platform.system().lower() == "windows":
        output_path = BINARY_PATH + ".exe"

    urllib.request.urlretrieve(url, output_path)

    # ให้ permission execute บน Unix
    if platform.system().lower() != "windows":
        st = os.stat(output_path)
        os.chmod(output_path, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    print(f"✅ ดาวน์โหลดสำเร็จ: {output_path}")
    return True

if __name__ == "__main__":
    ok = download_binary()
    if ok:
        print("\n✅ Setup เสร็จแล้ว — รัน stream.py ได้เลย")
    else:
        print("\n❌ Setup ไม่สำเร็จ — ดูข้อความด้านบนเพื่อแก้ไข")
        sys.exit(1)
