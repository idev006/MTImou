from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterable

import cv2
import numpy as np
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import WebDriverException

from venv_guard import enforce_venv_python


ROOT_DIR = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT_DIR / "logs" / "router_live"
DEFAULT_URL = "http://192.168.1.1/"
DEFAULT_BRAVE = Path(r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe")
DEFAULT_TESSERACT = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Live router browser control via Brave.")
    parser.add_argument("--url", default=os.environ.get("ROUTER_URL", DEFAULT_URL))
    parser.add_argument("--username", default=os.environ.get("ROUTER_USERNAME", "admin"))
    parser.add_argument("--password", default=os.environ.get("ROUTER_PASSWORD", "admin"))
    parser.add_argument("--brave", default=os.environ.get("BRAVE_EXE", str(DEFAULT_BRAVE)))
    parser.add_argument("--tesseract", default=os.environ.get("TESSERACT_EXE", str(DEFAULT_TESSERACT)))
    parser.add_argument("--show", action="store_true", help="Show the browser window.")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between visible actions.")
    parser.add_argument("--keep-open", action="store_true", help="Leave the browser open after the script exits.")
    parser.add_argument("--login-only", action="store_true", help="Stop after login succeeds.")
    parser.add_argument("--attempts", type=int, default=6, help="Captcha/login retry attempts.")
    parser.add_argument("--manual-captcha", action="store_true", help="Wait for captcha answer file instead of OCR.")
    parser.add_argument(
        "--answer-file",
        default=str(LOG_DIR / "captcha_answer.txt"),
        help="Path to a text file containing the captcha answer for manual-captcha mode.",
    )
    parser.add_argument("--answer-wait-sec", type=int, default=90, help="How long to wait for captcha answer file.")
    parser.add_argument(
        "--click-ids",
        default="",
        help="Comma-separated menu element ids to click after login, e.g. internet,ethWanStatus,smNAT,portForwarding,ddns",
    )
    parser.add_argument("--pf-alias", default="", help="Create/update a port-forward rule alias after login.")
    parser.add_argument("--pf-lan-ip", default="", help="LAN IP target for port-forward rule.")
    parser.add_argument("--pf-wan-port", default="", help="External WAN port for port-forward rule.")
    parser.add_argument("--pf-lan-port", default="", help="Internal LAN port for port-forward rule.")
    parser.add_argument("--pf-protocol", default="BOTH", help="Protocol for port-forward rule: TCP, UDP, BOTH.")
    return parser.parse_args()


def slow(delay: float) -> None:
    if delay > 0:
        time.sleep(delay)


def detect_brave(path: str) -> str:
    brave = Path(path)
    if brave.exists():
        return str(brave)
    raise FileNotFoundError(f"Brave not found: {path}")


def detect_tesseract(path: str) -> str:
    tess = Path(path)
    if tess.exists():
        return str(tess)
    raise FileNotFoundError(f"Tesseract not found: {path}")


def build_driver(brave_exe: str, show: bool, keep_open: bool) -> webdriver.Chrome:
    options = Options()
    options.binary_location = brave_exe
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--allow-insecure-localhost")
    options.add_argument("--window-size=1440,1000")
    if not show:
        options.add_argument("--headless=new")
    if keep_open:
        options.add_experimental_option("detach", True)
    return webdriver.Chrome(options=options)


def preprocess_variants(image: np.ndarray) -> Iterable[np.ndarray]:
    for scale in (4, 6, 8):
        up = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        yield up

        hsv = cv2.cvtColor(up, cv2.COLOR_BGR2HSV)
        blue = cv2.inRange(hsv, (70, 15, 40), (140, 255, 255))
        inv = 255 - blue
        yield cv2.cvtColor(inv, cv2.COLOR_GRAY2BGR)

        blur = cv2.GaussianBlur(inv, (3, 3), 0)
        _, otsu = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        yield cv2.cvtColor(otsu, cv2.COLOR_GRAY2BGR)


def tesseract_read(image: np.ndarray, tesseract_exe: str) -> list[str]:
    candidates: list[str] = []
    for idx, variant in enumerate(preprocess_variants(image), start=1):
        tmp = LOG_DIR / f"captcha_variant_{idx}.png"
        cv2.imwrite(str(tmp), variant)
        for psm in ("7", "8", "13"):
            result = subprocess.run(
                [
                    tesseract_exe,
                    str(tmp),
                    "stdout",
                    "--psm",
                    psm,
                    "-c",
                    "tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            text = re.sub(r"[^A-Z0-9]", "", result.stdout.upper())
            if text:
                candidates.append(text)
    # prefer five-char candidates that occur more than once
    deduped: list[str] = []
    for item in sorted(set(candidates), key=lambda s: (-candidates.count(s), abs(len(s) - 5), s)):
        deduped.append(item[:5])
    return deduped


def capture_captcha(driver: webdriver.Chrome, suffix: str) -> tuple[Path, list[str]]:
    captcha_el = driver.find_element(By.ID, "captchaImg")
    img_path = LOG_DIR / f"captcha_{suffix}.png"
    img_path.write_bytes(captcha_el.screenshot_as_png)
    image = cv2.imread(str(img_path))
    if image is not None:
        zoom = cv2.resize(image, None, fx=8, fy=8, interpolation=cv2.INTER_CUBIC)
        cv2.imwrite(str(LOG_DIR / f"captcha_{suffix}_zoom.png"), zoom)
    return img_path, image


def is_login_success(driver: webdriver.Chrome) -> bool:
    body = driver.find_element(By.TAG_NAME, "body").text
    return "Please login." not in body and "Validate code is not correct." not in body


def save_page(driver: webdriver.Chrome, name: str) -> None:
    driver.save_screenshot(str(LOG_DIR / f"{name}.png"))
    (LOG_DIR / f"{name}.html").write_text(driver.page_source, encoding="utf-8")


def click_menu_if_present(driver: webdriver.Chrome, text: str, delay: float) -> bool:
    links = driver.find_elements(By.LINK_TEXT, text)
    if not links:
        return False
    driver.execute_script("arguments[0].click();", links[0])
    slow(delay)
    save_page(driver, f"menu_{text.lower().replace(' ', '_')}")
    return True


def click_id_if_present(driver: webdriver.Chrome, element_id: str, delay: float) -> bool:
    try:
        element = driver.find_element(By.ID, element_id)
    except Exception:
        return False
    driver.execute_script("arguments[0].click();", element)
    slow(max(delay, 1.0))
    save_page(driver, f"id_{element_id}")
    try:
        body = driver.find_element(By.TAG_NAME, "body").text[:2000]
        print(f"[INFO] Body snapshot for {element_id}:")
        print(body)
    except Exception:
        pass
    return True


def find_visible_by_candidates(driver: webdriver.Chrome, tag: str, candidates: list[str]):
    for candidate in candidates:
        if candidate.endswith(":"):
            selector = f"{tag}[id^='{candidate}']"
        else:
            selector = f"{tag}#{candidate}"
        for element in driver.find_elements(By.CSS_SELECTOR, selector):
            try:
                if element.is_displayed() and element.is_enabled():
                    return element
            except WebDriverException:
                continue
    return None


def find_visible_by_prefix(driver: webdriver.Chrome, tag: str, prefix: str):
    for element in driver.find_elements(By.CSS_SELECTOR, f"{tag}[id^='{prefix}']"):
        try:
            if element.is_displayed() and element.is_enabled():
                return element
        except WebDriverException:
            continue
    return None


def expand_port_forward_rows(driver: webdriver.Chrome) -> None:
    for selector in ("span.instName.collapsibleInst", "span.instName.collapsibleInst.instNameExp"):
        for el in driver.find_elements(By.CSS_SELECTOR, selector):
            try:
                if el.is_displayed():
                    driver.execute_script("arguments[0].click();", el)
            except Exception:
                continue


def create_new_port_forward_item(driver: webdriver.Chrome) -> None:
    try:
        add_bar = driver.find_element(By.ID, "addInstBar_PortForwarding")
        driver.execute_script("arguments[0].click();", add_bar)
    except Exception:
        return


def reveal_hidden_port_forward_template(driver: webdriver.Chrome) -> None:
    driver.execute_script(
        """
        var root = document.getElementById('template_PortForwarding');
        if (root) { root.style.display = 'block'; }
        var area = document.getElementById('changeArea_PortForwarding');
        if (area) { area.style.display = 'block'; }
        var top = document.getElementById('topLine_PortForwarding');
        if (top) { top.style.display = 'block'; }
        """
    )


def set_field_value_by_candidates(driver: webdriver.Chrome, candidates: list[str], value: str) -> None:
    element = find_visible_by_candidates(driver, "input", candidates)
    if element is None:
        raise RuntimeError(f"Visible field not found for candidates: {candidates}")
    try:
        element.clear()
        element.send_keys(value)
    except Exception:
        driver.execute_script("arguments[0].value = arguments[1];", element, value)


def select_value_by_candidates(driver: webdriver.Chrome, candidates: list[str], value: str) -> None:
    element = find_visible_by_candidates(driver, "select", candidates)
    if element is None:
        raise RuntimeError(f"Visible select not found for candidates: {candidates}")
    Select(element).select_by_value(value)


def configure_port_forward(
    driver: webdriver.Chrome,
    delay: float,
    alias: str,
    lan_ip: str,
    wan_port: str,
    lan_port: str,
    protocol: str,
) -> None:
    for element_id in ("internet", "smNAT", "portForwarding"):
        if not click_id_if_present(driver, element_id, delay):
            raise RuntimeError(f"Required port-forward menu not found: {element_id}")

    expand_port_forward_rows(driver)
    slow(delay)
    create_new_port_forward_item(driver)
    slow(delay)
    expand_port_forward_rows(driver)
    slow(delay)
    if find_visible_by_candidates(driver, "input", ["Alias", "Alias:"]) is None:
        reveal_hidden_port_forward_template(driver)
        slow(delay)

    set_field_value_by_candidates(driver, ["Alias", "Alias:"], alias)
    select_value_by_candidates(driver, ["Protocol", "Protocol:"], protocol.upper())
    select_value_by_candidates(driver, ["S_Interface", "S_Interface:"], "WANAll")
    set_field_value_by_candidates(driver, ["InternalClient", "InternalClient:"], lan_ip)
    set_field_value_by_candidates(driver, ["ExternalPort", "ExternalPort:"], wan_port)
    set_field_value_by_candidates(driver, ["ExternalPortEndRange", "ExternalPortEndRange:"], wan_port)
    set_field_value_by_candidates(driver, ["InternalPort", "InternalPort:"], lan_port)
    set_field_value_by_candidates(driver, ["InternalPortEndRange", "InternalPortEndRange:"], lan_port)
    slow(delay)
    apply_btn = find_visible_by_candidates(
        driver,
        "input",
        ["Btn_apply_PortForwarding", "Btn_apply_PortForwarding:"],
    )
    if apply_btn is None:
        raise RuntimeError("Visible Port Forward apply button not found")
    driver.execute_script("arguments[0].click();", apply_btn)
    slow(max(delay, 3.0))

    try:
        confirm_ok = driver.find_element(By.ID, "confirmOK")
        if confirm_ok.is_displayed():
            driver.execute_script("arguments[0].click();", confirm_ok)
            slow(max(delay, 2.0))
    except Exception:
        pass

    save_page(driver, "port_forward_applied")
    body = driver.find_element(By.TAG_NAME, "body").text
    print("[INFO] Body snapshot after port-forward apply:")
    print(body[:2500])
    if "Your data have been stored!" in body:
        print("[SUCCESS] Port-forward rule stored.")
    else:
        print("[WARN] Port-forward save confirmation text not found; inspect saved page.")


def wait_for_answer_file(answer_path: Path, timeout_sec: int) -> str:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if answer_path.exists():
            answer = answer_path.read_text(encoding="utf-8").strip().upper()
            if answer:
                answer_path.unlink(missing_ok=True)
                return answer
        time.sleep(0.5)
    raise TimeoutException(f"Timed out waiting for captcha answer file: {answer_path}")


def main() -> int:
    enforce_venv_python()
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    args = parse_args()
    brave_exe = detect_brave(args.brave)
    tesseract_exe = detect_tesseract(args.tesseract)
    answer_path = Path(args.answer_file)

    driver = build_driver(brave_exe, args.show, args.keep_open)
    wait = WebDriverWait(driver, 20)
    keep_browser = args.keep_open
    try:
        print(f"[INFO] Opening router UI: {args.url}")
        driver.get(args.url)
        wait.until(EC.presence_of_element_located((By.ID, "Frm_Username")))
        save_page(driver, "login_initial")

        for attempt in range(1, args.attempts + 1):
            captcha_path, captcha_img = capture_captcha(driver, f"attempt_{attempt}")
            user_el = driver.find_element(By.ID, "Frm_Username")
            pass_el = driver.find_element(By.ID, "Frm_Password")
            code_el = driver.find_element(By.ID, "Frm_captchaCode")
            user_el.clear()
            slow(args.delay / 2)
            user_el.send_keys(args.username)
            slow(args.delay)
            pass_el.clear()
            pass_el.send_keys(args.password)
            slow(args.delay)
            code_el.clear()
            if args.manual_captcha:
                answer_path.parent.mkdir(parents=True, exist_ok=True)
                answer_path.unlink(missing_ok=True)
                print(f"[INFO] Manual captcha mode. Saved image: {captcha_path}")
                print(f"[INFO] Write the captcha answer to: {answer_path}")
                candidate = wait_for_answer_file(answer_path, args.answer_wait_sec)
            else:
                candidates = tesseract_read(captcha_img, tesseract_exe)
                print(f"[INFO] Captcha attempt {attempt}: {captcha_path.name} candidates={candidates[:5]}")
                if not candidates:
                    driver.find_element(By.ID, "captchaImg").click()
                    slow(args.delay)
                    continue
                candidate = candidates[0]
            # Re-find the captcha input after waiting; some router pages rerender the login form.
            code_el = driver.find_element(By.ID, "Frm_captchaCode")
            code_el.clear()
            code_el.send_keys(candidate)
            slow(args.delay)
            print(f"[INFO] Submitting login with captcha={candidate}")
            driver.execute_script("document.getElementById('LoginId').click();")
            slow(max(args.delay, 2.0))
            save_page(driver, f"login_post_attempt_{attempt}")
            if is_login_success(driver):
                print("[SUCCESS] Router login succeeded.")
                break

            body = driver.find_element(By.TAG_NAME, "body").text
            if "Validate code is not correct." in body:
                print("[WARN] Captcha rejected; refreshing and retrying.")
                driver.find_element(By.ID, "captchaImg").click()
                slow(args.delay)
                continue
            print("[WARN] Login still on login page; stopping retries.")
            print(body[:1000])
            return 2
        else:
            print("[ERROR] Unable to solve captcha/login after retries.")
            return 3

        if args.login_only:
            print("[INFO] Login-only mode complete.")
            return 0

        clicked_ids = [item.strip() for item in args.click_ids.split(",") if item.strip()]
        for element_id in clicked_ids:
            if click_id_if_present(driver, element_id, args.delay):
                print(f"[INFO] Opened id: {element_id}")
            else:
                print(f"[WARN] Could not find id: {element_id}")

        if args.pf_alias and args.pf_lan_ip and args.pf_wan_port and args.pf_lan_port:
            configure_port_forward(
                driver,
                args.delay,
                args.pf_alias,
                args.pf_lan_ip,
                args.pf_wan_port,
                args.pf_lan_port,
                args.pf_protocol,
            )

        # Quick visible inventory to help the next step.
        for menu_text in ("Internet", "Local Network", "Management & Diagnosis"):
            if click_menu_if_present(driver, menu_text, args.delay):
                print(f"[INFO] Opened menu: {menu_text}")

        print("[INFO] Browser session ready for further router work.")
        return 0
    finally:
        if not keep_browser:
            driver.quit()


if __name__ == "__main__":
    raise SystemExit(main())
