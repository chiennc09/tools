import subprocess
import cv2
import numpy as np
import random
import os

class AdbHelper:
    def __init__(self, device_id):
        self.device_id = device_id
        self.has_adb_keyboard = None

    def capture(self):
        try:
            result = subprocess.run(
                f'adb -s {self.device_id} exec-out screencap -p',
                shell=True,
                capture_output=True,
                timeout=3
            )
            image_bytes = result.stdout
            
            if not image_bytes:
                return None
                
            arr = np.frombuffer(image_bytes, np.uint8)
            if len(arr) == 0:
                return None
                
            return cv2.imdecode(arr, cv2.IMREAD_COLOR)

        except (subprocess.TimeoutExpired, ValueError):
            try:
                # Fallback file saving method
                subprocess.run(f'adb -s {self.device_id} shell screencap -p /sdcard/tmp_{self.device_id}.png', shell=True, timeout=5)
                subprocess.run(f'adb -s {self.device_id} pull /sdcard/tmp_{self.device_id}.png screen_{self.device_id}.png', capture_output=True, shell=True, timeout=5)
                
                if os.path.exists(f'screen_{self.device_id}.png'):
                    screen = cv2.imread(f'screen_{self.device_id}.png')
                    os.remove(f'screen_{self.device_id}.png')
                    return screen
            except Exception:
                pass
            return None
        except Exception:
            return None

    def click(self, x, y):
        rx = x + random.randint(-5, 5)
        ry = y + random.randint(-5, 5)
        subprocess.run(f'adb -s {self.device_id} shell input tap {rx} {ry}', shell=True)

    def swipe(self, x1, y1, x2, y2, duration=None):
        rx1 = x1 + random.randint(-20, 20)
        ry1 = y1 + random.randint(-20, 20)
        rx2 = x2 + random.randint(-20, 20)
        ry2 = y2 + random.randint(-20, 20)
        
        if duration is None:
            # Tốc độ lướt nhanh hơn, ngẫu nhiên từ 150ms đến 450ms
            duration = random.randint(150, 450)
        else:
            duration = duration + random.randint(-50, 100)
            
        subprocess.run(f"adb -s {self.device_id} shell input touchscreen swipe {rx1} {ry1} {rx2} {ry2} {duration}", shell=True)

    def force_stop(self, package="com.facebook.katana"):
        subprocess.run(f"adb -s {self.device_id} shell am force-stop {package}", shell=True)

    def remove_accents(self, input_str):
        s1 = u'ÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚÝàáâãèéêìíòóôõùúýĂăĐđĨĩŨũƠơƯưẠạẢảẤấẦầẨẩẪẫẬậẮắẰằẲẳẴẵẶặẸẹẺẻẼẽẾếỀềỂểỄễỆệỈỉỊịỌọỎỏỐốỒồỔổỖỗỘộỚớỜờỞởỠỡỢợỤụỦủỨứỪừỬửỮữỰựỲỳỴỵỶỷỸỹ'
        s0 = u'AAAAEEEIIOOOOUUYaaaaeeeiioooouuyAaDdIiUuOoUuAaAaAaAaAaAaAaAaAaAaAaAaEeEeEeEeEeEeEeEeIiIiOoOoOoOoOoOoOoOoOoOoOoOoUuUuUuUuUuUuUuUuYyYyYyYy'
        s = ''
        for c in str(input_str):
            if c in s1:
                s += s0[s1.index(c)]
            else:
                s += c
        return s

    def input_text(self, text):
        import base64
        
        if self.has_adb_keyboard is None:
            try:
                res = subprocess.run(f"adb -s {self.device_id} shell pm list packages", shell=True, capture_output=True, text=True)
                self.has_adb_keyboard = "adbkeyboard" in res.stdout.lower()
            except Exception:
                self.has_adb_keyboard = False

        if self.has_adb_keyboard:
            b64_text = base64.b64encode(str(text).encode('utf-8')).decode('utf-8')
            subprocess.run(f"adb -s {self.device_id} shell am broadcast -a ADB_INPUT_B64 --es msg '{b64_text}'", shell=True)
        else:
            safe_text = self.remove_accents(text)
            safe_text = safe_text.replace("'", "\\'").replace(" ", "%s")
            subprocess.run(f"adb -s {self.device_id} shell input text '{safe_text}'", shell=True)
