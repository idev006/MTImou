# IMOU Ranger 2 — P2P Remote Stream

รับ stream จากกล้อง IMOU Ranger 2 จากทุกที่บนโลก
ฟรี 100% ไม่มีเครื่องกลาง ไม่ต้อง port forward

## โครงสร้างไฟล์

```
imou_stream/
├── setup.py         ← ดาวน์โหลด dh-p2p binary (รันครั้งแรก)
├── tunnel.py        ← จัดการ P2P tunnel (library)
├── stream.py        ← โปรแกรมหลัก (แก้ CONFIG แล้วรันได้เลย)
├── requirements.txt ← Python dependencies
└── README.md
```

## วิธีใช้

### 1. ติดตั้ง Python dependency
```bash
pip install -r requirements.txt
```

### 2. ดาวน์โหลด dh-p2p binary
```bash
python setup.py
```
> ถ้าไม่มี prebuilt binary ใน releases ให้ build จาก source:
> ```bash
> # ต้องมี Rust: https://rustup.rs
> git clone https://github.com/khoanguyen-3fc/dh-p2p
> cd dh-p2p && cargo build --release
> # copy target/release/dh-p2p มาไว้ใน folder นี้
> ```

### 3. แก้ค่าใน stream.py
```python
CONFIG = {
    "serial":   "6L3BXXXXXXXX",  # ← SN จาก IMOU Life App (กล้อง → Device Info)
    "username": "admin",
    "password": "YOUR_PASSWORD", # ← รหัสผ่านที่ตั้งไว้
    ...
}
```

### 4. รัน
```bash
python stream.py
```

## หาก Serial Number ของกล้อง

เปิด **IMOU Life** → เลือกกล้อง → กดฟันเฟือง ⚙️ → Device Info → Serial Number

## Architecture

```
กล้อง IMOU Ranger 2
  ↕  UDP (Dahua PTCP protocol)
  ↕  ผ่าน easy4ipcloud.com (NAT traversal ฟรี)
  ↕
dh-p2p binary (รันบนเครื่องผู้ดู)
  ↕  RTSP @ 127.0.0.1:1554
OpenCV / Python
```

กล้องไม่ต้องมี public IP ไม่ต้อง port forward
เครื่องผู้ดูอยู่ที่ไหนก็ได้บนโลก

## ข้อจำกัด

- `dh-p2p` เป็น PoC (Proof of Concept) — อาจ unstable
- รองรับ 1 client ต่อครั้ง (Python version)
- ใช้ได้กับกล้อง IMOU / Dahua / KBVision ที่ใช้ P2P ของ Dahua
- Dahua อาจ update protocol ทำให้ใช้ไม่ได้โดยไม่แจ้งล่วงหน้า
