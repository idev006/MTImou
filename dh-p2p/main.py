"""
DH-P2P + PTCP Implementation
"""
import argparse
import datetime
import random
import select
import socket
import subprocess
import sys
import time
from urllib.parse import quote

from helpers import (
    MAIN_PORT,
    MAIN_SERVER,
    UDP,
    PTCPPayload,
    get_auth,
    get_dec,
    get_enc,
    get_key,
    get_nonce,
)


def main(serial, dtype=0, username=None, password=None, debug=False, relay=False):
    def rewrite_rtsp_host(payload: bytes, host_override: str | None) -> bytes:
        if not host_override:
            return payload
        try:
            text = payload.decode("ascii", errors="ignore")
        except Exception:
            return payload

        if "RTSP/" not in text:
            return payload

        lines = text.split("\r\n")
        if not lines:
            return payload

        first = lines[0]
        for method in ("OPTIONS ", "DESCRIBE ", "SETUP ", "PLAY ", "TEARDOWN "):
            if first.startswith(method):
                first = first.replace("rtsp://127.0.0.1", f"rtsp://{host_override}")
                first = first.replace("rtsp://localhost", f"rtsp://{host_override}")
                lines[0] = first
                break

        for idx, line in enumerate(lines):
            if line.lower().startswith("host: "):
                lines[idx] = f"Host: {host_override}"

        rewritten = "\r\n".join(lines)
        return rewritten.encode("ascii", errors="ignore")

    socketserver = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socketserver.bind(("0.0.0.0", 554))
    socketserver.listen(5)
    print("Listening on port 554")

    if debug:
        subprocess.Popen(
            [
                "ffplay",
                "-rtsp_transport",
                "tcp",
                "-i",
                f"rtsp://{username}:{quote(password)}@127.0.0.1/cam/realmonitor?channel=6&subtype=0",
            ]
        )

    main_remote = UDP(MAIN_SERVER, MAIN_PORT, debug)
    res = main_remote.request("/probe/p2psrv")

    res = main_remote.request(f"/online/p2psrv/{serial}")

    p2psrv_server, p2psrv_port = res["data"]["body"]["US"].split(":")
    p2psrv_port = int(p2psrv_port)

    relay_remote = UDP(p2psrv_server, p2psrv_port, debug)
    res = relay_remote.request(f"/probe/device/{serial}")
    res = relay_remote.request(f"/info/device/{serial}")

    res = main_remote.request("/online/relay")
    relay_server, relay_port = res["data"]["body"]["Address"].split(":")
    relay_port = int(relay_port)

    laddr = f"127.0.0.1:{main_remote.lport}"
    ipaddr = f"<IpEncrpt>true</IpEncrpt><LocalAddr>{laddr}</LocalAddr>"
    auth = ""
    aid = random.randbytes(8)

    if dtype > 0:
        key = get_key(username, password)
        nonce = get_nonce()

        laddr = get_enc(key, nonce, laddr)
        ipaddr = f"<IpEncrptV2>true</IpEncrptV2><LocalAddr>{laddr}</LocalAddr>"
        auth = "" if dtype == 0 else get_auth(username, key, nonce, laddr)

    res = main_remote.request(
        f"/device/{serial}/p2p-channel",
        f"<body>{auth}<Identify>{' '.join(f'{b:x}' for b in aid)}</Identify>{ipaddr}<version>5.0.0</version></body>",
        should_read=False,
    )

    relay_remote.rhost = relay_server
    relay_remote.rport = relay_port
    res = relay_remote.request("/relay/agent")
    token = res["data"]["body"]["Token"]
    agent_server, agent_port = res["data"]["body"]["Agent"].split(":")
    agent_port = int(agent_port)

    relay_remote.rhost = agent_server
    relay_remote.rport = agent_port
    res = relay_remote.request(
        f"/relay/start/{token}",
        "<body><Client>:0</Client></body>",
    )

    relay_only = relay
    try:
        # Wait for channel callback from p2p-channel request.
        # Some cameras respond with an interim 1xx packet first.
        res = main_remote.read(return_error=True, timeout=60)
        if res["code"] < 200:
            res = main_remote.read(return_error=True, timeout=60)
    except TimeoutError:
        if relay_only:
            print("Warning: p2p-channel callback timed out in relay mode.")
        else:
            print(
                "Warning: p2p-channel callback timed out. Falling back to relay-only mode."
            )
            relay_only = True

    if not relay_only:
        if res["code"] >= 400:
            print("Error:", res["status"])

            if dtype == 0 and res["code"] == 403:
                print("Device requires authentication when creating P2P channel.")
                print("Try again with:")
                print(
                    f"main.py --type 1 --username <username> --password <password> {serial}"
                )

            sys.exit(1)

        device_laddr = res["data"]["body"]["LocalAddr"]
        session_nonce = None
        if dtype > 0:
            session_nonce = res["data"]["body"].get("Nonce")
            if session_nonce:
                device_laddr = get_dec(key, session_nonce, device_laddr)
            else:
                print("Warning: device response missing Nonce; using raw LocalAddr.")

        device_server, device_port = res["data"]["body"]["PubAddr"].split(":")
        device_port = int(device_port)
        device_remote = main_remote
        device_remote.rhost = device_server
        device_remote.rport = device_port
    else:
        device_remote = relay_remote
        session_nonce = None

    relay_remote.rhost = MAIN_SERVER
    relay_remote.rport = MAIN_PORT

    if dtype > 0 and not relay_only and session_nonce:
        auth = get_auth(username, key, session_nonce)
    elif dtype > 0 and not relay_only:
        print("Warning: skip relay-channel auth due to missing Nonce.")
        auth = ""
    else:
        auth = ""

    res = relay_remote.request(
        f"/device/{serial}/relay-channel",
        f"<body>{auth}<agentAddr>{agent_server}:{agent_port}</agentAddr></body>",
        should_read=False,
    )

    relay_remote.rhost = agent_server
    relay_remote.rport = agent_port
    # TODO check timeout
    try:
        res = relay_remote.read(timeout=60)
    except TimeoutError:
        if relay_only:
            print("Warning: relay-channel response timeout in relay-only mode, trying PTCP anyway.")
            res = None
        else:
            print("Warning: relay-channel timeout in direct mode; falling back to relay-only mode.")
            relay_only = True
            res = None

    relay_remote.request_ptcp(b"\x00\x03\x01\x00")
    res = relay_remote.read_ptcp()

    if relay_only:
        relay_rtsp_host = None
        try:
            local_addr_hint = res["data"]["body"].get("LocalAddr", "")
            # example: 192.168.1.108,192.168.1.2:25850
            parts = local_addr_hint.split(",")
            if len(parts) >= 2:
                relay_rtsp_host = parts[1].split(":")[0].strip()
            elif len(parts) == 1 and ":" in parts[0]:
                relay_rtsp_host = parts[0].split(":")[0].strip()
        except Exception:
            relay_rtsp_host = None
        if relay_rtsp_host:
            print(f"Relay RTSP host override: {relay_rtsp_host}")

        relay_remote.request_ptcp(b"\x00\x03\x01\x00")
        try:
            res = relay_remote.read_ptcp(timeout=5)
            while len(res.body) == 0:
                res = relay_remote.read_ptcp(timeout=5)
            if res.body != b"\x00\x03\x01\x00":
                print("Warning: unexpected PTCP sync response in relay-only mode.")
                print("Body:", "".join(f"\\x{b:02X}" for b in res.body))
        except TimeoutError:
            print("Warning: no PTCP sync response in relay-only mode; continuing anyway.")

        # Some firmware expects sign negotiation even in relay path.
        try:
            relay_remote.request_ptcp(
                b"\x17\x00\x00\x00" + b"\x00\x00\x00\x00\x00\x00\x00\x00"
            )
            sign_res = relay_remote.read_ptcp(timeout=3)
            while len(sign_res.body) == 0:
                sign_res = relay_remote.read_ptcp(timeout=3)
            if sign_res.body[0] == 0x18:
                sign = sign_res.body[12:]
                print("Relay sign negotiation succeeded.")
                relay_remote.request_ptcp()
                relay_remote.request_ptcp(
                    b"\x19\x00\x00\x00"
                    + b"\x00\x00\x00\x00"
                    + b"\x00\x00\x00\x00"
                    + sign
                )
                auth_res = relay_remote.read_ptcp(timeout=5)
                while len(auth_res.body) == 0:
                    auth_res = relay_remote.read_ptcp(timeout=5)
                if auth_res.body[0] != 0x1A:
                    print(
                        f"Warning: relay auth step expected 0x1A but got 0x{auth_res.body[0]:02X}"
                    )
                else:
                    print("Relay auth step 0x19/0x1A succeeded.")
                relay_remote.request_ptcp(
                    b"\x1b\x00\x00\x00"
                    + b"\x00\x00\x00\x00"
                    + b"\x00\x00\x00\x00"
                )
                try:
                    _ = relay_remote.read_ptcp(timeout=3)
                except TimeoutError:
                    pass
            else:
                print(
                    f"Warning: relay sign negotiation unexpected type: 0x{sign_res.body[0]:02X}"
                )
        except TimeoutError:
            print("Warning: relay sign negotiation timeout; continue with best effort.")

        print("Ready to connect (relay-only mode)")
        print("Test with: rtsp://127.0.0.1/cam/realmonitor?channel=1&subtype=0")
        heartbeat_body = b"\x13" + b"\x00" * 11
        last_heartbeat = time.monotonic()
        while True:
            ready, _, _ = select.select([socketserver], [], [], 0.1)

            if not ready:
                if time.monotonic() - last_heartbeat >= 5:
                    relay_remote.request_ptcp(heartbeat_body)
                    last_heartbeat = time.monotonic()

                ptcp_ready, _, _ = select.select([device_remote], [], [], 0)

                if not ptcp_ready:
                    continue

                # only simplex, duplex is not supported
                res = device_remote.read_ptcp()
                if len(res.body) == 0:
                    continue

                if res.body[0] != 0x13:
                    print(
                        f"Warning: unexpected PTCP packet type in relay-only mode: 0x{res.body[0]:02X}"
                    )
                    continue
                device_remote.request_ptcp()

                continue

            socketclient, address = socketserver.accept()
            print(f"Connection from {address}")

            realm_id = random.randint(0x00000000, 0xFFFFFFFF)
            device_remote.request_ptcp(
                b"\x11\x00\x00\x00"
                + realm_id.to_bytes(4, "big")
                + b"\x00\x00\x00\x00"
                + b"\x00\x00\x02\x2A"
                + b"\x7f\x00\x00\x01",
            )
            realm_ready = False
            res = None
            realm_deadline = time.monotonic() + 12
            while time.monotonic() < realm_deadline:
                try:
                    res = device_remote.read_ptcp(timeout=1)
                except TimeoutError:
                    # keep PTCP alive while waiting for realm ACK
                    device_remote.request_ptcp(heartbeat_body)
                    continue

                if len(res.body) == 0:
                    continue

                ptype = res.body[0]
                print(
                    f"Relay realm handshake packet type=0x{ptype:02X} len={len(res.body)}"
                )
                if ptype == 0x12:
                    device_remote.request_ptcp()
                    realm_ready = True
                    print("Relay realm established.")
                    break
                if ptype == 0x13:
                    device_remote.request_ptcp()
                    continue

                device_remote.request_ptcp()

            if not realm_ready:
                body_hex = (
                    "".join(f"\\x{b:02X}" for b in res.body)
                    if res is not None
                    else "<timeout>"
                )
                print(
                    "Warning: failed to establish relay realm (expected 0x12 within timeout)."
                )
                print("Body:", body_hex)
                socketclient.close()
                continue

            try:
                payload_rx_count = 0
                client_tx_count = 0
                status_rx_count = 0
                while True:
                    ptcp_ready, _, _ = select.select([device_remote], [], [], 0.1)

                    while ptcp_ready:
                        res = device_remote.read_ptcp()

                        if len(res.body) == 0:
                            continue

                        device_remote.request_ptcp()

                        if res.body[0] != 0x10:
                            if res.body[0] == 0x12:
                                status_rx_count += 1
                                realm = (
                                    int.from_bytes(res.body[4:8], "big")
                                    if len(res.body) >= 8
                                    else 0
                                )
                                status_text = (
                                    res.body[12:].decode(errors="ignore")
                                    if len(res.body) > 12
                                    else ""
                                )
                                if status_rx_count <= 10:
                                    print(
                                        f"Relay status rx#{status_rx_count} realm=0x{realm:08X} text={status_text!r}"
                                    )
                            print(
                                f"Relay data-plane PTCP type=0x{res.body[0]:02X} len={len(res.body)}"
                            )
                            continue

                        body = PTCPPayload.parse(res.body)
                        payload_rx_count += 1
                        if payload_rx_count <= 5:
                            preview = body.payload[:120].decode(errors="ignore")
                            preview = preview.split("\r\n")[0] if preview else ""
                            print(
                                f"Relay payload rx#{payload_rx_count} realm=0x{body.realm:08X} bytes={len(body.payload)} first={preview!r}"
                            )
                        socketclient.send(body.payload)
                        ptcp_ready, _, _ = select.select([device_remote], [], [], 0.1)

                    client_ready, _, _ = select.select([socketclient], [], [], 0)
                    if not client_ready:
                        continue

                    data = socketclient.recv(4096)
                    if not data:
                        print("Connection closed?")
                        break

                    client_tx_count += 1
                    if client_tx_count <= 5:
                        req_preview = data[:120].decode(errors="ignore")
                        req_preview = req_preview.split("\r\n")[0] if req_preview else ""
                        print(
                            f"Relay client tx#{client_tx_count} realm=0x{realm_id:08X} bytes={len(data)} first={req_preview!r}"
                        )
                    data = rewrite_rtsp_host(data, relay_rtsp_host)
                    device_remote.request_ptcp(bytes(PTCPPayload(realm_id, data)))

            except ConnectionResetError:
                print("Connection reset by peer")
            except ConnectionAbortedError:
                print("Connection aborted by local host stack")
            except BrokenPipeError:
                print("Broken pipe")
            finally:
                print("Cleaning up connection")
                device_remote.request_ptcp(
                    b"\x12\x00\x00\x00"
                    + realm_id.to_bytes(4, "big")
                    + b"\x00\x00\x00\x00"
                    + b"DISC"
                )

                res = device_remote.read_ptcp()

                while len(res.body) == 0 or res.body[0] == 0x10:
                    if len(res.body) > 0:
                        device_remote.request_ptcp()

                    res = device_remote.read_ptcp()

                if len(res.body) == 0 or res.body[0] != 0x12:
                    body_hex = "".join(f"\\x{b:02X}" for b in res.body)
                    print("Warning: unexpected PTCP disconnect ack.")
                    print("Body:", body_hex)
                else:
                    device_remote.request_ptcp()

                socketclient.close()
                print("Connection closed")
        return

    relay_remote.request_ptcp(
        b"\x17\x00\x00\x00" + b"\x00\x00\x00\x00\x00\x00\x00\x00"
    )
    res = relay_remote.read_ptcp()
    while len(res.body) == 0:
        res = relay_remote.read_ptcp()
    sign = res.body[12:]

    relay_remote.request_ptcp()

    device_remote.rhost = device_server
    device_remote.rport = device_port

    aid = bytes(0xFF - b for b in aid)
    cookie = random.randbytes(4)
    trasn_id = random.randbytes(12)
    eaddr = device_port.to_bytes(2) + socket.inet_aton(device_server)
    eaddr = bytes(0xFF - b for b in eaddr)

    data = (
        b"\xff\xfe\xff\xe7"
        + cookie
        + trasn_id
        + b"\x7f\xd5\xff\xf7"
        + aid
        + b"\xff\xfb\xff\xf7\xff\xfe"
        + eaddr
    )
    print(f":{device_remote.lport} >>> {device_remote.rhost}:{device_remote.rport}")
    print("".join(f"\\x{b:02X}" for b in data))
    device_remote.send(data)

    try:
        data = device_remote.recv(timeout=5)
    except socket.timeout:
        print("Timeout occurred while waiting for a response from the device.")
        print("If the issue persists, you may need to use relay mode with this device.")
        print("Note: Relay mode is currently not implemented for Python.")
        sys.exit(1)

    print("Data <<<")
    print("".join(f"\\x{b:02X}" for b in data))

    rtrans_id = data[8:20]
    ip, port = device_laddr.split(":")
    port = int(port)
    eaddr = port.to_bytes(2) + socket.inet_aton(ip)

    data = (
        b"\xfe\xfe\xff\xe7"
        + cookie
        + rtrans_id
        + b"\x7f\xd6\xff\xf7"
        + aid
        + b"\xff\xfb\xff\xf7\xff\xfe"
        + eaddr
    )
    print("Request >>>")
    print("".join(f"\\x{b:02X}" for b in data))
    device_remote.send(data)

    if dtype > 0:
        data = device_remote.recv()
        print("Data <<<")
        print("".join(f"\\x{b:02X}" for b in data))

        data = (
            b"\xfe\xfe\xff\xf3"
            + cookie
            + rtrans_id
            + b"\x7f\xd6\xff\xf7"
            + aid
            + b"\xff\xfb\xff\xf7\xff\xfe"
            + b"\xa8\x13\x3f\x57\xfe\x37"
        )

        for _ in range(5):
            print("Request >>>")
            print("".join(f"\\x{b:02X}" for b in data))
            device_remote.send(data)

    for _ in range(5):
        data = device_remote.recv()
        print("Data <<<")
        print("".join(f"\\x{b:02X}" for b in data))

    device_remote.request_ptcp(b"\x00\x03\x01\x00")
    res = device_remote.read_ptcp()
    assert res.body == b"\x00\x03\x01\x00"

    device_remote.request_ptcp(
        b"\x19\x00\x00\x00" + b"\x00\x00\x00\x00" + b"\x00\x00\x00\x00" + sign
    )
    res = device_remote.read_ptcp()
    if len(res.body) == 0:
        res = device_remote.read_ptcp()
    assert res.body[0] == 0x1A

    device_remote.request_ptcp(
        b"\x1b\x00\x00\x00" + b"\x00\x00\x00\x00" + b"\x00\x00\x00\x00"
    )
    res = device_remote.read_ptcp()
    assert len(res.body) == 0

    print("Ready to connect")
    print("Test with: rtsp://127.0.0.1/cam/realmonitor?channel=1&subtype=0")
    while True:
        ready, _, _ = select.select([socketserver], [], [], 0.1)

        if not ready:
            ptcp_ready, _, _ = select.select([device_remote], [], [], 0)

            if not ptcp_ready:
                continue

            # only simplex, duplex is not supported
            res = device_remote.read_ptcp()
            if len(res.body) == 0:
                continue

            assert res.body[0] == 0x13
            device_remote.request_ptcp()

            continue

        socketclient, address = socketserver.accept()
        print(f"Connection from {address}")

        realm_id = random.randint(0x00000000, 0xFFFFFFFF)
        device_remote.request_ptcp(
            b"\x11\x00\x00\x00"
            + realm_id.to_bytes(4, "big")
            + b"\x00\x00\x00\x00"
            # port 554
            + b"\x00\x00\x02\x2A"
            + b"\x7f\x00\x00\x01",
        )
        res = device_remote.read_ptcp()
        if len(res.body) == 0:
            res = device_remote.read_ptcp()
        assert res.body[0] == 0x12

        try:
            while True:
                ptcp_ready, _, _ = select.select([device_remote], [], [], 0.1)

                # if ptcp_ready:
                while ptcp_ready:
                    res = device_remote.read_ptcp()

                    if len(res.body) == 0:
                        continue

                    device_remote.request_ptcp()

                    if res.body[0] != 0x10:
                        continue

                    body = PTCPPayload.parse(res.body)

                    if debug:
                        print()
                        print(body)
                        print(f"[{datetime.datetime.now().isoformat()}]")
                        print("Data <<<")
                        print(body.payload)
                        print()

                    socketclient.send(body.payload)

                    ptcp_ready, _, _ = select.select([device_remote], [], [], 0.1)

                client_ready, _, _ = select.select([socketclient], [], [], 0)

                if not client_ready:
                    continue

                data = socketclient.recv(4096)

                if not data:
                    print("Connection closed?")
                    break

                if debug:
                    print()
                    print(f"[{datetime.datetime.now().isoformat()}]")
                    print("Data >>>")
                    print(data)
                    print()

                device_remote.request_ptcp(bytes(PTCPPayload(realm_id, data)))

        # handle connection reset by peer
        except ConnectionResetError:
            print("Connection reset by peer")
        except BrokenPipeError:
            print("Broken pipe")
        finally:
            print("Cleaning up connection")
            device_remote.request_ptcp(
                b"\x12\x00\x00\x00"
                + realm_id.to_bytes(4, "big")
                + b"\x00\x00\x00\x00"
                + b"DISC"
            )

            res = device_remote.read_ptcp()

            while len(res.body) == 0 or res.body[0] == 0x10:
                if len(res.body) > 0:
                    device_remote.request_ptcp()

                res = device_remote.read_ptcp()

            assert res.body[0] == 0x12
            device_remote.request_ptcp()

            socketclient.close()
            print("Connection closed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("serial", help="Serial number of the camera")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("-t", "--type", type=int, help="Type of the camera", default=0)
    parser.add_argument("-u", "--username", help="Username of the camera")
    parser.add_argument("-p", "--password", help="Password of the camera")
    parser.add_argument("-r", "--relay", action="store_true", help="Force relay mode")
    args = parser.parse_args()

    if args.username is None or args.password is None:
        if args.type > 0:
            parser.error("Username and password are required for type > 0")
        elif args.debug:
            parser.error("Username and password are required in debug mode")

    if args.serial:
        main(args.serial, args.type, args.username, args.password, args.debug, args.relay)
