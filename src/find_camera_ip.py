from __future__ import annotations

import ipaddress
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed


def get_local_ipv4() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()


def port_open(ip: str, port: int, timeout: float = 0.3) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((ip, port))
        return True
    except Exception:
        return False
    finally:
        sock.close()


def rtsp_probe(ip: str, timeout: float = 0.8) -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((ip, 554))
        req = (
            f"OPTIONS rtsp://{ip}:554/cam/realmonitor?channel=1&subtype=0 RTSP/1.0\r\n"
            "CSeq: 1\r\n"
            "User-Agent: MTImou-IP-Finder\r\n\r\n"
        )
        sock.sendall(req.encode("ascii", errors="ignore"))
        data = sock.recv(1024).decode(errors="ignore")
        line = data.splitlines()[0] if data else ""
        return line.strip()
    except Exception:
        return ""
    finally:
        sock.close()


def main() -> int:
    local_ip = get_local_ipv4()
    net = ipaddress.ip_network(f"{local_ip}/24", strict=False)
    print(f"[INFO] Local IP: {local_ip}")
    print(f"[INFO] Scanning subnet: {net}")

    candidates: list[str] = []
    with ThreadPoolExecutor(max_workers=128) as ex:
        futures = {
            ex.submit(port_open, str(ip), 554): str(ip)
            for ip in net.hosts()
            if str(ip) != local_ip
        }
        for fut in as_completed(futures):
            ip = futures[fut]
            try:
                if fut.result():
                    candidates.append(ip)
            except Exception:
                pass

    if not candidates:
        print("[ERROR] No host with port 554 open in this /24 network.")
        return 1

    print("[INFO] Hosts with port 554 open:")
    for ip in sorted(candidates, key=lambda x: tuple(map(int, x.split(".")))):
        line = rtsp_probe(ip)
        if line:
            print(f"  - {ip}  ->  {line}")
        else:
            print(f"  - {ip}")

    print("\n[HINT] Try these IPs in run_lan_rtsp_test.bat (one by one).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

