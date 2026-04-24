import pyautogui
import time
import random
import os
import sys
import signal
import threading
from PIL import Image
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget
from PyQt5.QtCore import Qt, QTimer
import win32gui
import win32con

# Disable ImageNotFoundException so locateOnScreen returns None instead of raising an error
# This is needed for newer versions of PyAutoGUI (0.9.41+)
pyautogui.useImageNotFoundException(False)

# --- MODE SELECTION ---
# Available modes: 'order', 'cook', 'harvest'
# You can select multiple modes, e.g., ['cook', 'harvest']
# MODES = ['order', 'cook', 'harvest']
MODES = []
MODES.append('order')
MODES.append('cook')
MODES.append('harvest')



# --- CONFIGURATION ---
# Target image dictionary for each mode
MODE_IMAGES = {
    'cook': [
        'assets/cook/cook_button_1.png',
        'assets/cook/cook_button_2.png',
        'assets/cook/cook_button_3.png',
        'assets/cook/cook_button_4.png',
        'assets/cook/cook_button_5.png',
        'assets/cook/cook_button_6.png',
        'assets/cook/cook_button_7.png',
        'assets/cook/cook_button_8.png'
    ],
    'order': [
        'assets/order/order_button_1.png'
    ],
    'harvest': [
        'assets/harvest/harvest_button_1.png',
        'assets/harvest/harvest_button_2.png',
        'assets/harvest/harvest_button_3.png'
    ],
    'order_secondary': [
        'assets/order_seconday/order_seconday_1.png',
        'assets/order_seconday/order_seconday_2.png'
    ]
}

# Aggregate all target images from selected modes
TARGET_IMAGES = []
for mode in MODES:
    TARGET_IMAGES.extend(MODE_IMAGES.get(mode, []))
# Accuracy threshold (0.02 to 0.25). 0.9 is usually the "sweet spot"
CONFIDENCE_LEVEL = 0.6 
# --- SCREEN SETTINGS ---
# Get actual screen resolution dynamically
SCREEN_WIDTH, SCREEN_HEIGHT = pyautogui.size()

# Target a centered search area (10000o match box.py)
SEARCH_WIDTH = 600
SEARCH_HEIGHT = 200
# SEARCH_WIDTH = 1500
# SEARCH_HEIGHT = 250

# Vertical offset from center (negative is up, positive is down)
VERTICAL_OFFSET = -100 

# Automatically calculate the centered region with offset
left = (SCREEN_WIDTH - SEARCH_WIDTH) // 2
top = ((SCREEN_HEIGHT - SEARCH_HEIGHT) // 2) + VERTICAL_OFFSET
SEARCH_REGION = (left, top, SEARCH_WIDTH, SEARCH_HEIGHT)

# --- ORDER SECONDARY SEARCH REGION ---
ORDER_SECONDARY_SEARCH_WIDTH = 250
ORDER_SECONDARY_SEARCH_HEIGHT = 100
ORDER_SECONDARY_VERTICAL_OFFSET = -100  # Adjust as needed

# Automatically calculate the secondary region at bottom right corner
secondary_left = SCREEN_WIDTH - ORDER_SECONDARY_SEARCH_WIDTH - 450
secondary_top = SCREEN_HEIGHT - ORDER_SECONDARY_SEARCH_HEIGHT - 110
ORDER_SECONDARY_SEARCH_REGION = (secondary_left, secondary_top, ORDER_SECONDARY_SEARCH_WIDTH, ORDER_SECONDARY_SEARCH_HEIGHT)

# Delay before the first click starts (seconds)
# Delay applied before starting each detection loop iteration (seconds)
DETECTION_DELAY = 0.02
# Deprecated: previously used to pause before clicking. Kept for compatibility but set to 0.
PRE_CLICK_DELAY = 0.0
# Delay after the entire click sequence is finished (cooldown)
POST_ACTION_DELAY = 0.01
# Number of clicks when target is found (e.g., 1 or 2)
CLICKS_PER_ACTION = 1
# Extra delay between individual clicks if CLICKS_PER_ACTION > 1
INTER_CLICK_DELAY = 0.02

# --- ORDER MODE CONFIG ---
# Delay after clicking the order button before performing the secondary click
ORDER_POST_CLICK_DELAY = 1.1
# Delay after the secondary click
POST_ORDER_SECONDARY_DELAY = 0.15
# Number of attempts to click the secondary order button if it remains visible
MAX_SECONDARY_CLICK_ATTEMPTS = 2
# Delay before rechecking the secondary button after a click
SECONDARY_RECHECK_DELAY = 0.25
# Speed of mouse movement (seconds). Lower is faster.
MOUSE_MOVE_DURATION = 0.02

# --- OVERLAY UI ---
class SquareOverlay(QMainWindow):
    def __init__(self, w, h, offset=VERTICAL_OFFSET, color="red", x=None, y=None):
        super().__init__()

        # 1. ตั้งค่าพื้นฐาน: ไม่มีขอบ, อยู่บนสุด, เป็น Tool window
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 2. คำนวณหาตำแหน่ง (Centered with offset) หรือใช้ตำแหน่งที่กำหนด
        screen = QApplication.primaryScreen().geometry()
        if x is None or y is None:
            x = (screen.width() - w) // 2
            y = ((screen.height() - h) // 2) + offset
        
        # กำหนดตำแหน่งและขนาดหน้าต่าง
        self.setGeometry(x, y, w, h)

        # 3. สร้างตัวกล่องสี่เหลี่ยม (Widget)
        self.square = QWidget(self)
        self.square.setGeometry(0, 0, w, h)
        # ตั้งค่าสี: พื้นหลังสีแดง (กึ่งโปร่งใส) และเส้นขอบสีขาว
        self.square.setStyleSheet(f"""
            background-color: transparent; 
            border: 2px dashed {color};
        """)

    def set_click_through(self):
        # ทำให้เมาส์คลิกทะลุกล่องนี้ไปโดนเกม
        hwnd = self.winId()
        styles = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, 
                               styles | win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT)

secondary_overlay = None

secondary_click_lock = threading.Lock()

def show_secondary_overlay():
    if secondary_overlay is not None:
        QTimer.singleShot(0, secondary_overlay.show)


def hide_secondary_overlay():
    if secondary_overlay is not None:
        QTimer.singleShot(0, secondary_overlay.hide)


def handle_order_secondary_click():
    if not secondary_click_lock.acquire(blocking=False):
        print("[ORDER] Secondary click already in progress, skipping duplicate handling.")
        return

    def locate_secondary_button():
        for image_path in MODE_IMAGES.get('order_secondary', []):
            if not os.path.exists(image_path):
                continue

            try:
                with Image.open(image_path) as img:
                    img_w, img_h = img.size
            except Exception as e:
                print(f"[ERROR] Could not open secondary image {image_path}: {e}")
                continue

            current_region = ORDER_SECONDARY_SEARCH_REGION
            if img_w > ORDER_SECONDARY_SEARCH_WIDTH or img_h > ORDER_SECONDARY_SEARCH_HEIGHT:
                if img_w <= SCREEN_WIDTH and img_h <= SCREEN_HEIGHT:
                    current_region = None
                else:
                    continue

            location = pyautogui.locateOnScreen(
                image_path,
                confidence=CONFIDENCE_LEVEL,
                grayscale=True,
                region=current_region
            )
            if location is not None:
                return location, image_path

        return None, None

    try:
        print(f"[ORDER] Waiting {ORDER_POST_CLICK_DELAY}s before secondary click...")
        time.sleep(ORDER_POST_CLICK_DELAY)

        print("[ORDER] Displaying secondary search overlay...")
        show_secondary_overlay()

        attempt = 1
        while attempt <= MAX_SECONDARY_CLICK_ATTEMPTS:
            secondary_location, secondary_found_image = locate_secondary_button()
            if secondary_location is None:
                if attempt == 1:
                    print("[ORDER] Secondary button not found. Skipping secondary click.")
                else:
                    print("[ORDER] Secondary button disappeared after click. Assuming success.")
                break

            secondary_center = pyautogui.center(secondary_location)
            secondary_target_x = secondary_center.x + random.randint(-5, 5)
            secondary_target_y = secondary_center.y + random.randint(-5, 5)

            print(f"[ORDER] Moving to secondary button at {secondary_center} (using {secondary_found_image}). Attempt {attempt}.")
            pyautogui.moveTo(secondary_target_x, secondary_target_y, duration=MOUSE_MOVE_DURATION)
            pyautogui.mouseDown()
            time.sleep(random.uniform(0.02, 0.02))
            pyautogui.mouseUp()
            print("[ORDER] Secondary click performed.")

            time.sleep(POST_ORDER_SECONDARY_DELAY)
            attempt += 1

            if attempt <= MAX_SECONDARY_CLICK_ATTEMPTS:
                print("[ORDER] Rechecking secondary button visibility after click...")
                time.sleep(SECONDARY_RECHECK_DELAY)
        else:
            print("[ORDER] Maximum secondary click attempts reached.")
    finally:
        hide_secondary_overlay()
        secondary_click_lock.release()


def auto_bot():
    active_modes = ", ".join(m.upper() for m in MODES)
    print(f"--- Heartopia [{active_modes}] Bot Started ---")
    print(f"Current modes: {MODES}")
    print("!!! MAKE SURE TO RUN THIS SCRIPT AS ADMINISTRATOR !!!")
    print("Press Ctrl+C to stop the script.")
    
    if not TARGET_IMAGES:
        print(f"[INFO] Selected modes {MODES} have no target images. Staying idle...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[STOPPED] Script terminated by user.")
        return

    # Pre-check image dimensions to avoid PyAutoGUI ValueError
    image_dims = {}
    valid_images = []
    for path in TARGET_IMAGES:
        if os.path.exists(path):
            try:
                with Image.open(path) as img:
                    image_dims[path] = img.size
                    valid_images.append(path)
            except Exception as e:
                print(f"[ERROR] Could not open image {path}: {e}")
        else:
            print(f"[WARN] Image not found: {path}")

    try:
        while True:
            # 1. Delay before starting detection, then search for each image in the list
            time.sleep(DETECTION_DELAY)
            location = None
            found_image = None
            
            for image_path in valid_images:
                img_w, img_h = image_dims[image_path]
                
                # Determine search region: use centered region if image fits, else full screen
                current_region = SEARCH_REGION
                if img_w > SEARCH_WIDTH or img_h > SEARCH_HEIGHT:
                    if img_w <= SCREEN_WIDTH and img_h <= SCREEN_HEIGHT:
                        current_region = None # Search entire screen
                    else:
                        # Image is even larger than the screen itself
                        continue

                # grayscale=True makes the search faster
                location = pyautogui.locateOnScreen(
                    image_path, 
                    confidence=CONFIDENCE_LEVEL, 
                    grayscale=True,
                    region=current_region
                )
                if location is not None:
                    found_image = image_path
                    # Identify which mode this image belongs to
                    found_mode = None
                    for mode, imgs in MODE_IMAGES.items():
                        if image_path in imgs:
                            found_mode = mode
                            break
                    break # Stop searching once an image is found

            if location is not None:
                # 2. Get the center coordinates of the found image
                button_center = pyautogui.center(location)
                
                # 3. Add a small random offset to the click for human-like behavior
                target_x = button_center.x + random.randint(-5, 5)
                target_y = button_center.y + random.randint(-5, 5)

                # 4. (No pre-click pause) Click immediately when detected.

                # 5. Perform the click (using mouseDown/mouseUp for game compatibility)
                # Moving the mouse smoothly is often required by games
                pyautogui.moveTo(target_x, target_y, duration=MOUSE_MOVE_DURATION)
                
                # Perform clicks based on parameter
                num_clicks = CLICKS_PER_ACTION
                for i in range(num_clicks):
                    pyautogui.mouseDown()
                    # Key for games: hold for a split second (randomized for anti-cheat)
                    time.sleep(random.uniform(0.02, 0.02))
                    pyautogui.mouseUp()
                    if i < num_clicks - 1:
                        time.sleep(INTER_CLICK_DELAY) # Delay between clicks
                
                print(f"[ACTION] Button found at {button_center} (using {found_image}). Clicked {num_clicks} times.")

                # --- SPECIAL ORDER MODE LOGIC ---
                if found_mode == 'order':
                    threading.Thread(target=handle_order_secondary_click, daemon=True).start()
                    print("[ORDER] Secondary click handler started in background thread.")

                # 6. Wait for the game animation to finish/cooldown
                time.sleep(POST_ACTION_DELAY)
            else:
                # Optional: print a dot to show the script is still alive
                # print(".", end="", flush=True)
                time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n[STOPPED] Script terminated by user.")
    except Exception as e:
        import traceback
        print(f"\n[ERROR] An unexpected error occurred: {type(e).__name__}")
        if str(e):
            print(f"Message: {e}")
        print("\nFull Traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    print("--- Heartopia All-in-One Bot Starting ---")
    print("Switch to the game window now...")
    
    # 1. Initialize PyQt App
    app = QApplication(sys.argv)
    
    # 2. Setup Overlay (matching SEARCH_WIDTH/HEIGHT)
    overlay = SquareOverlay(SEARCH_WIDTH, SEARCH_HEIGHT)
    overlay.show()
    overlay.set_click_through()
    
    # Setup secondary overlay for order mode at bottom-right position
    secondary_overlay = SquareOverlay(
        ORDER_SECONDARY_SEARCH_WIDTH,
        ORDER_SECONDARY_SEARCH_HEIGHT,
        color="yellow",
        x=secondary_left,
        y=secondary_top
    )
    secondary_overlay.set_click_through()
    # Keep the secondary overlay hidden until an order button is clicked
    secondary_overlay.hide()
    
    # 3. Start Bot in Background Thread
    bot_thread = threading.Thread(target=auto_bot, daemon=True)
    bot_thread.start()

    # 3a. Allow Ctrl+C to interrupt the Qt event loop on Windows
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    timer = QTimer()
    timer.start(100)
    timer.timeout.connect(lambda: None)
    
    # 4. Start UI Event Loop
    sys.exit(app.exec_())
