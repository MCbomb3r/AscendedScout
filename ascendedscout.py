import cv2
import numpy as np
import pytesseract
from mss import mss
import time
import re
import os
import unicodedata

# --------------------------------------------------------------------
# 1) TESSERACT CONFIG
# --------------------------------------------------------------------
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# --------------------------------------------------------------------
# 2) LOGS PATHS
# --------------------------------------------------------------------
base_log_path = os.path.join(os.path.dirname(__file__), "logs")
tribemembers_log_path = os.path.join(base_log_path, "tribemembers_log.txt")
players_log_path      = os.path.join(base_log_path, "players_log.txt")
center_log_path       = os.path.join(base_log_path, "center_log.txt")

# --------------------------------------------------------------------
# 2.1) CLEAR LOGS FILES ON STARTUP
# --------------------------------------------------------------------
def clear_log_files():
    os.makedirs(base_log_path, exist_ok=True)
    for p in (tribemembers_log_path, players_log_path, center_log_path):
        try:
            if os.path.exists(p):
                os.remove(p)
            with open(p, 'w', encoding='utf-8'):
                pass
        except Exception as e:
            print(f"[WARN] Unable to clear {p}: {e}")

# --------------------------------------------------------------------
# 3) OCR PREPROCESSING
# --------------------------------------------------------------------
def preprocess_image_for_colored_text(image, color="red"):
    hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    if color == "red":
        lower1 = np.array([0, 50, 50]); upper1 = np.array([10, 255, 255])
        lower2 = np.array([170, 50, 50]); upper2 = np.array([180, 255, 255])
        mask1 = cv2.inRange(hsv_image, lower1, upper1)
        mask2 = cv2.inRange(hsv_image, lower2, upper2)
        color_mask = cv2.bitwise_or(mask1, mask2)
    elif color == "blue":
        lower = np.array([100, 50, 50]); upper = np.array([140, 255, 255])
        color_mask = cv2.inRange(hsv_image, lower, upper)
    elif color == "green":
        lower = np.array([40, 50, 50]); upper = np.array([80, 255, 255])
        color_mask = cv2.inRange(hsv_image, lower, upper)
    else:
        raise ValueError(f"Unsupported color: {color}")
    colored_text_image = cv2.bitwise_and(image, image, mask=color_mask)
    gray_image = cv2.cvtColor(colored_text_image, cv2.COLOR_BGR2GRAY)
    _, binary_image = cv2.threshold(gray_image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    binary_image = cv2.resize(binary_image, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    return binary_image

def preprocess_image_general(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary

def preprocess_line_top(image_bgra):
    bgr = cv2.cvtColor(image_bgra, cv2.COLOR_BGRA2BGR)
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    g = cv2.resize(g, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    g = cv2.bilateralFilter(g, 7, 55, 55)
    _, bw = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    kernel = np.ones((2, 2), np.uint8)
    bw = cv2.dilate(bw, kernel, iterations=1)
    return bw

def normalize_ocr_text(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("\r", " ").replace("\n", " ")
    s = re.sub(r"[*\[\]\|\u200b\u200c\u200d]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

# --------------------------------------------------------------------
# 4) CHANGE DETECTION
# --------------------------------------------------------------------
def has_new_notification(current_frame, previous_frame, threshold=50):
    frame_delta = cv2.absdiff(current_frame, previous_frame)
    gray_delta = cv2.cvtColor(frame_delta, cv2.COLOR_BGR2GRAY)
    _, thresh_delta = cv2.threshold(gray_delta, 30, 255, cv2.THRESH_BINARY)
    change_level = np.sum(thresh_delta)
    return change_level > threshold

# --------------------------------------------------------------------
# 5) CENTER: NORMALIZATION + EXTRACTION (DESTROYED) + TIMESTAMP DEDUP
# --------------------------------------------------------------------

RE_TS = re.compile(r"Day\s+(\d+),\s+(\d{2})[.:](\d{2})[.:](\d{2})", re.IGNORECASE)

RE_OBJ = re.compile(r"Your\s+'([^']{2,80})'\s+was\s+destroyed!?", re.IGNORECASE)

CENTER_SEEN_TS = set()

def _center_ts_key_from_match(m: re.Match) -> str:
    day, hh, mm, ss = m.groups()
    return f"{int(day)}-{hh}:{mm}:{ss}"

def _normalize_center_ocr(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = (s.replace("'", "'").replace("'", "'").replace("´", "'").replace("`", "'")
           .replace(""", '"').replace(""", '"'))

    s = s.replace("Waed", "Wood").replace("¥", "Y")

    s = s.replace(" ,", ", ").replace("..", ".").replace("::", ":")

    s = s.replace("\n", " ").replace("\r", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _ocr_center_all(image_bgra) -> str:
    texts = []
    for color in ("red", "blue", "green"):
        try:
            pre = preprocess_image_for_colored_text(image_bgra, color=color)
            txt = pytesseract.image_to_string(pre, config="--oem 3 --psm 6 -l eng").strip()
            if txt:
                texts.append(txt)
        except Exception as e:
            print(f"[OCR center {color}] error: {e}")
    try:
        pre = preprocess_image_general(image_bgra)
        txt = pytesseract.image_to_string(pre, config="--oem 3 --psm 6 -l eng").strip()
        if txt:
            texts.append(txt)
    except Exception as e:
        print(f"[OCR center general] error: {e}")
    fused = " ".join(texts)
    if fused:
        print(f"[OCR center | fused] => {fused}")
    return fused

def _valid_object(name: str) -> bool:
    name = name.strip()
    if not (3 <= len(name) <= 80):
        return False

    if not re.search(r"[A-Za-z]", name):
        return False

    if re.fullmatch(r"[-/\\.,:;!_()\s]+", name):
        return False
    return True

def process_center_frame(image_bgra):
    """
    - Fused OCR (colors + general)
    - Normalization
    - Split by timestamp: for EACH segment, search for
      "Your 'OBJ' was destroyed!" ; if nothing -> ignore (no more empty lines)
    - Dedup by timestamp (key = Day-HH:MM:SS)
    """
    raw = _ocr_center_all(image_bgra)
    if not raw:
        return

    text = _normalize_center_ocr(raw)
    ts_matches = list(RE_TS.finditer(text))
    if not ts_matches:
        return

    for i, m in enumerate(ts_matches):
        seg_start = m.start()
        seg_end   = ts_matches[i+1].start() if i+1 < len(ts_matches) else len(text)
        seg = text[seg_start:seg_end].strip()

        obj_m = RE_OBJ.search(seg)
        if not obj_m:

            continue

        obj = obj_m.group(1).strip()
        if not _valid_object(obj):
            continue

        key = _center_ts_key_from_match(m)
        if key in CENTER_SEEN_TS:
            continue

        line = f"Day {key.split('-')[0]}, {key.split('-')[1]}: Your '{obj}' was destroyed!"
        write_to_file(center_log_path, line)
        CENTER_SEEN_TS.add(key)
        print(f"[CENTER DESTROY] => {line}")

# --------------------------------------------------------------------
# 6) TOP: joined/left (tolerant regex) — no filter
# --------------------------------------------------------------------
PAT_TRIBE = re.compile(
    r"""
    (?:(tribe|tebe|troe)member\s+)?
    ([A-Za-z0-9][A-Za-z0-9_.-]{0,31})\s+
    h(?:a|e)s\s+
    (joined|left)\s+this(?:\s+ark)?\.?
    """,
    re.IGNORECASE | re.VERBOSE
)

def process_top_line(text):
    text_clean = normalize_ocr_text(text)
    for match in PAT_TRIBE.finditer(text_clean):
        tribemember_flag = bool(match.group(1))
        player = match.group(2)
        action = match.group(3).lower()
        tribemember = "Tribemember " if tribemember_flag else ""
        log_text = f"{tribemember}{player} has {action} this Ark."
        file_path = tribemembers_log_path if tribemember_flag else players_log_path
        write_to_file(file_path, log_text)
        print(f"[TRIBE/PLAYER] => {log_text}")

# --------------------------------------------------------------------
# 7) OCR ROUTING
# --------------------------------------------------------------------
def process_notification(image_bgra, zone):
    try:
        if zone == "top":
            pre = preprocess_line_top(image_bgra)
            cfg = "--oem 3 --psm 7 -l eng"
            txt = pytesseract.image_to_string(pre, config=cfg).strip()
            if not txt:
                return
            print(f"[OCR top | general] => {txt}")
            process_top_line(txt)
        elif zone == "center":
            process_center_frame(image_bgra)
    except Exception as e:
        print(f"OCR error: {e}")

# --------------------------------------------------------------------
# 8) FILE WRITING
# --------------------------------------------------------------------
def write_to_file(file_path, text):
    if not text.strip():
        return
    dir_path = os.path.dirname(file_path)
    if dir_path and not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)
    with open(file_path, 'a', encoding='utf-8') as f:
        f.write(text + "\n")

# --------------------------------------------------------------------
# 9) MAIN LOOP
# --------------------------------------------------------------------
def main():
    clear_log_files()

    top_zone    = {'top': 0,   'left': 750, 'width': 550, 'height': 100}
    center_zone = {'top': 211, 'left': 772, 'width': 374, 'height': 539}

    sct = mss()
    previous_frame_top = None
    previous_frame_center = None

    try:
        while True:

            scr_top = sct.grab(top_zone)
            cur_top = np.array(scr_top)
            if previous_frame_top is not None and has_new_notification(cur_top, previous_frame_top):
                process_notification(cur_top, "top")
            previous_frame_top = cur_top

            scr_center = sct.grab(center_zone)
            cur_center = np.array(scr_center)
            if previous_frame_center is not None and has_new_notification(cur_center, previous_frame_center):
                process_notification(cur_center, "center")
            previous_frame_center = cur_center

            time.sleep(1)
    except KeyboardInterrupt:
        print("Interrupted by user.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        print("AscendedScout stopped.")

# --------------------------------------------------------------------
# 10) ENTRY POINT
# --------------------------------------------------------------------
if __name__ == "__main__":
    main()