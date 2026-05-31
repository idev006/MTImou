# Streaming KB + Result Report (2026-05-31)

## เป้าหมาย (Goal)

ให้กล้อง IMOU ส่งวิดีโอสตรีมเข้ามาที่โปรแกรมของเราได้จริงผ่าน remote relay โดยไม่ต้องมีเครื่องกลางที่บ้าน

## ขอบเขตระบบที่ยืนยันแล้ว

- Camera: IMOU Ranger 2 (firmware line `6.6.21001`)
- Path: `dh-p2p` (Python) + relay mode
- Local ingest URL:
  - `rtsp://127.0.0.1:554/cam/realmonitor?channel=1&subtype=0`
- Runtime:
  - Python venv: `F:\programming\python\MTImou\.venv`

## ผลการทดสอบล่าสุด (Result)

- Test runner: `run_monitor_relay.bat`
- รอบทดสอบ: `6` รอบ (interval 4 วินาที)
- ผลรวม: `SUCCESS 6/6 (100.0%)`
- Log หลัก:
  - `F:\programming\python\MTImou\logs\relay_monitor_20260531_133829.log`

## ปัญหาที่พบจริง + วิธีแก้ (Problem / Fix)

1. ปัญหา: RTSP บางรอบเปิดไม่ติดทั้งที่ tunnel ขึ้น `Ready to connect`
- อาการ: ได้ relay handshake แต่ OpenCV timeout / อ่านเฟรมไม่ได้
- วิธีแก้:
  - ใช้ retry หลาย attempt อัตโนมัติ (`run_relay_test.bat`, `relay_stream_test.py`)
  - ใช้ `subtype=0` เป็น default สำหรับกล้องตัวนี้

2. ปัญหา: พอร์ต `554` ถูกใช้งานค้างจาก process เก่า
- อาการ: `WinError 10048` bind port ไม่ได้
- วิธีแก้:
  - รัน `run_stop_all.bat` ก่อนทุกครั้ง
  - launcher เคลียร์ process และ port ที่ชนให้อัตโนมัติ

3. ปัญหา: หน้าต่าง OpenCV เคยค้าง (Not Responding)
- อาการ: ภาพค้าง/เวลาไม่ขยับ
- วิธีแก้:
  - แยก reader thread
  - เพิ่ม health guard และ restart เมื่อ no-frame ตามเวลา
  - ให้ `run_viewer.bat` ใช้ ffplay เป็น default viewer (เสถียรกว่า)

4. ปัญหา: relay cloud มีความแกว่งเป็นช่วง
- อาการ: บาง attempt ต้องลองใหม่ 1-3 รอบ
- วิธีแก้:
  - monitor แบบหลายรอบเพื่อวัดผลจริง
  - ยอมรับ retry เป็นส่วนหนึ่งของ design สำหรับ unofficial relay path

## ขั้นตอนปฏิบัติ (Runbook แบบสั้น)

1. เคลียร์ process ค้าง
```bat
F:\programming\python\MTImou\run_stop_all.bat
```

2. ทดสอบว่าสตรีมถึงโปรแกรมได้จริง
```bat
F:\programming\python\MTImou\run_relay_test.bat
```

3. เปิดดูวิดีโอ
```bat
F:\programming\python\MTImou\run_viewer.bat
```

4. ตรวจเสถียรภาพเป็นรอบ
```bat
set IMOU_MONITOR_RUNS=6
set IMOU_MONITOR_INTERVAL_SEC=4
F:\programming\python\MTImou\run_monitor_relay.bat
```

## ค่าคอนฟิกแนะนำ (Known Good)

- `IMOU_FORCE_RELAY=1`
- `IMOU_CAMERA_TYPE=1`
- `IMOU_RTSP_HOST=127.0.0.1`
- `IMOU_RTSP_PORT=554`
- `IMOU_RTSP_CHANNEL=1`
- `IMOU_RTSP_SUBTYPE=0`

## ความเสี่ยงคงค้าง (Residual Risk)

- โซลูชันนี้พึ่งพา reverse-engineered protocol
- ถ้า firmware/cloud behavior เปลี่ยน อาจทำให้ fallback/retry ถี่ขึ้นหรือสตรีมหยุดได้
- ควรรัน monitor report เป็นระยะเพื่อจับแนวโน้มเสถียรภาพ
