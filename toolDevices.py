import os
import time
import threading
import subprocess
import random
import logging

try:
    import numpy as np
    import cv2
except ImportError:
    print("[-] Đang cài đặt thư viện cần thiết... (opencv-python, numpy bản mới)")
    subprocess.run("pip install opencv-python numpy --upgrade", shell=True)
    import numpy as np
    import cv2

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s | %(levelname)s | %(message)s', 
    datefmt='%H:%M:%S'
)

class Auto:
    def __init__(self, handle):
        self.handle = handle
        self.current_screen = None # Cache màn hình cục bộ mỗi nhịp
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.has_adb_keyboard = None # Caching ADBKeyboard check

    def capture(self):
        try:
            result = subprocess.run(
                f'adb -s {self.handle} exec-out screencap -p',
                shell=True,
                capture_output=True,
                timeout=3
            )
            image_bytes = result.stdout
            
            if not image_bytes:
                self.current_screen = None
                return None
                
            arr = np.frombuffer(image_bytes, np.uint8)
            if len(arr) == 0:
                self.current_screen = None
                return None
                
            self.current_screen = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            return self.current_screen

        except (subprocess.TimeoutExpired, ValueError):
            try:
                subprocess.run(f'adb -s {self.handle} shell screencap -p /sdcard/tmp_cap.png', shell=True, timeout=5)
                subprocess.run(f'adb -s {self.handle} pull /sdcard/tmp_cap.png screen_{self.handle}.png', capture_output=True, shell=True, timeout=5)
                
                if os.path.exists(f'screen_{self.handle}.png'):
                    self.current_screen = cv2.imread(f'screen_{self.handle}.png')
                    return self.current_screen
            except Exception:
                pass
            self.current_screen = None
            return None
        except Exception:
            self.current_screen = None
            return None

    def click(self, x, y):
        # Thêm random biên độ nhỏ (5 px) để không click vào đúng 1 điểm tĩnh như máy
        rx = x + random.randint(-5, 5)
        ry = y + random.randint(-5, 5)
        subprocess.run(f'adb -s {self.handle} shell input tap {rx} {ry}', shell=True)

    def swipe(self, x1, y1, x2, y2, duration=1000):
        # Hỗ trợ random thẳng ở cấp độ ADB swipe tránh nhận diện tool
        rx1 = x1 + random.randint(-5, 5)
        ry1 = y1 + random.randint(-5, 5)
        rx2 = x2 + random.randint(-5, 5)
        ry2 = y2 + random.randint(-5, 5)
        actual_duration = duration + random.randint(-50, 100)
        subprocess.run(f"adb -s {self.handle} shell input touchscreen swipe {rx1} {ry1} {rx2} {ry2} {actual_duration}", shell=True)

    def off(self, package="com.facebook.katana"):
        subprocess.run(f"adb -s {self.handle} shell am force-stop {package}", shell=True)

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

    def InpuText(self, text=None, VN=""):
        import base64
        text_to_send = text if text is not None else VN
        
        if self.has_adb_keyboard is None:
            try:
                res = subprocess.run(f"adb -s {self.handle} shell pm list packages", shell=True, capture_output=True, text=True)
                self.has_adb_keyboard = "adbkeyboard" in res.stdout.lower()
            except Exception:
                self.has_adb_keyboard = False

        if self.has_adb_keyboard:
            b64_text = base64.b64encode(str(text_to_send).encode('utf-8')).decode('utf-8')
            subprocess.run(f"adb -s {self.handle} shell am broadcast -a ADB_INPUT_B64 --es msg '{b64_text}'", shell=True)
        else:
            safe_text = self.remove_accents(text_to_send)
            safe_text = safe_text.replace("'", "\\'").replace(" ", "%s")
            subprocess.run(f"adb -s {self.handle} shell input text '{safe_text}'", shell=True)

    def find(self, img_name, threshold=0.80):
        img_path = os.path.join(self.base_dir, img_name)
        if not os.path.exists(img_path):
            return []
            
        template = cv2.imread(img_path)
        screen = self.current_screen
        if screen is None or template is None:
            return []
            
        try:
            result = cv2.matchTemplate(template, screen, cv2.TM_CCOEFF_NORMED)
            loc = np.where(result >= threshold)
            matches = list(zip(*loc[::-1]))
            if not matches:
                return []
            
            h, w = template.shape[:2]
            # Trả về TÂM CỦA ẢNH thay vì góc trái trên để click chuẩn và không bị out viền
            return [(x + w//2, y + h//2) for x, y in matches]
        except Exception:
            return []

def get_devices():
    try:
        output = subprocess.check_output("adb devices", shell=True).decode('utf-8')
        lines = output.strip().split('\n')[1:] 
        devices = []
        for line in lines:
            if 'device' in line and 'offline' not in line:
                devices.append(line.split('\t')[0].strip())
        return devices
    except Exception as e:
        print(f"Lỗi lấy ID thiết bị: {e}")
        return []

def random_sleep(min_s, max_s):
    # Hàm sleep random nhanh chóng 
    time.sleep(random.uniform(min_s, max_s))

class Worker(threading.Thread):
    def __init__(self, device_id, min_sleep, max_sleep, cmt_file):
        super().__init__()
        self.device_id = device_id
        self.min_sleep = min_sleep
        self.max_sleep = max_sleep
        self.cmt_file = cmt_file
        self.d = Auto(device_id)
        self.is_running = True
        self.name_ld = f"Phone-{device_id[-4:]}"

    def log(self, msg):
        logging.info(f"[{self.name_ld}] {msg}")

    def get_dynamic_comment(self):
        try:
            if os.path.exists(self.cmt_file):
                with open(self.cmt_file, 'r', encoding='utf-8') as f:
                    lines = [l.strip() for l in f.readlines() if l.strip()]
                if lines:
                    return random.choice(lines)
        except Exception as e:
            self.log(f"Lỗi tải comment: {e}")
            pass
        return "Tương tác tốt nhé"

    def run(self):
        state = 1
        error_count = 0

        while self.is_running:
            try:
                if error_count >= 10:
                    self.log("Lỗi định vị hình ảnh 10 lần. Đang reset lại quy trình FB...")
                    self.d.off()
                    random_sleep(1.0, 2.0)
                    state = 1
                    error_count = 0
                    continue

                screen = self.d.capture()
                if screen is None:
                    error_count += 1
                    random_sleep(0.5, 1.0)
                    continue

                if state == 1:
                    poin3 = self.d.find('img\\5.png', 0.80)
                    if poin3:
                        x, y = poin3[0][0], poin3[0][1]
                        # Vuốt random cự ly và toạ độ
                        self.d.swipe(x, y, x + random.randint(-30, 30), y + random.randint(1200, 1600), random.randint(300, 700))
                        self.log("Vuốt đóng popup về NewFeed (5.png)")
                        random_sleep(0.5, 1.0)
                        error_count = 0
                        continue

                    poin = self.d.find('img\\3.png', 0.80)
                    if poin:
                        self.d.click(poin[0][0], poin[0][1])
                        self.log("Mở App Facebook (3.png)")
                        state = 2
                        error_count = 0
                        random_sleep(1.0, 2.0)
                        continue

                    poin2 = self.d.find('img\\1.png', 0.80)
                    if poin2:
                        self.d.click(poin2[0][0], poin2[0][1])
                        self.log("Phát hiện nút Like (1.png)")
                        state = 3
                        error_count = 0
                        random_sleep(0.5, 1.0)
                        continue

                    error_count += 1
                    random_sleep(0.5, 1.0)

                elif state == 2:
                    poin3 = self.d.find('img\\5.png', 0.80)
                    if poin3:
                        x, y = poin3[0][0], poin3[0][1]
                        self.d.swipe(x, y, x + random.randint(-30, 30), y + random.randint(1200, 1600), random.randint(300, 700))
                        self.log("Vuốt đóng popup về NewFeed (5.png)")
                        error_count = 0
                        random_sleep(0.5, 1.0)
                        continue

                    poin2 = self.d.find('img\\3.png', 0.80)
                    if poin2:
                        self.d.click(poin2[0][0], poin2[0][1])
                        self.log("Mở Feed Facebook (3.png)")
                        error_count = 0
                        random_sleep(0.8, 1.5)
                        continue

                    poin = self.d.find('img\\1.png', 0.80)
                    if poin:
                        self.d.click(poin[0][0], poin[0][1])
                        self.log("Bấm LIKE bài viết !! (1.png)")
                        state = 3
                        error_count = 0
                        random_sleep(0.5, 1.2)
                        continue

                    self.log("Lướt New Feed...")
                    for _ in range(2):
                        x1 = random.randint(200, 400)
                        y1 = random.randint(700, 950)
                        x2 = x1 + random.randint(-40, 40)
                        y2 = random.randint(100, 300)
                        duration = random.randint(300, 750)
                        self.d.swipe(x1, y1, x2, y2, duration)
                        random_sleep(1.0, 2.0)
                    error_count += 1

                elif state == 3:
                    poin7 = self.d.find('img\\7.png', 0.80)
                    if poin7:
                        cmt_text = self.get_dynamic_comment()
                        self.d.click(poin7[0][0], poin7[0][1])
                        random_sleep(0.5, 1.0)
                        self.log(f"Bấm ô nhập Cmt (7.png) - Gõ: [{cmt_text}]")
                        self.d.InpuText(VN=cmt_text) 
                        random_sleep(1.0, 1.5)
                        state = 4
                        error_count = 0
                        continue

                    poin = self.d.find('img\\2.png', 0.80)
                    if poin:
                        self.d.click(poin[0][0], poin[0][1])
                        random_sleep(1.0, 1.8)
                        self.log("Bấm Icon Bình Luận để mở Popup (2.png)")
                        error_count = 0
                        continue
                    
                    error_count += 1
                    random_sleep(0.5, 1.0)

                elif state == 4:
                    poin6 = self.d.find('img\\6.png', 0.80)
                    if poin6:
                        self.log("Đã thấy nút Gửi (6.png), Bấm Gửi!")
                        self.d.click(poin6[0][0], poin6[0][1])
                        random_sleep(2.5, 3.5)
                        error_count = 0

                        continue

                    poin3 = self.d.find('img\\5.png', 0.80)
                    if poin3:
                        x, y = poin3[0][0], poin3[0][1]
                        self.d.swipe(x, y, x + random.randint(-30, 30), y + random.randint(1200, 1600), random.randint(300, 700))
                        self.log("Vuốt Đóng Popup Comment về Feed (5.png)")
                        random_sleep(0.5, 1.0)
                        
                        sleep_time = random.randint(self.min_sleep, self.max_sleep)
                        self.log(f"HOÀN THÀNH - Đang chờ cày tiếp ({sleep_time}s)")
                        random_sleep(sleep_time, sleep_time + 2) 
                        
                        state = 2
                        error_count = 0
                        continue

                    poin2 = self.d.find('img\\4.png', 0.80)
                    if poin2:
                        self.d.click(poin2[0][0], poin2[0][1])
                        self.log("Bấm Trở Về / Tắt Cmt (4.png)")
                        random_sleep(0.5, 1.0)
                        
                        sleep_time = random.randint(self.min_sleep, self.max_sleep)
                        self.log(f"HOÀN THÀNH - Đang chờ ({sleep_time}s)")
                        random_sleep(sleep_time, sleep_time + 2)
                        
                        state = 2
                        error_count = 0
                        continue

                    error_count += 1
                    random_sleep(0.5, 1.5)

            except Exception as e:
                self.log(f"Lỗi Script: {e}")
                error_count += 1
                random_sleep(1.0, 2.0)

def main():
    print("="*60)
    print("      TOOL AUTOMATION")
    print("="*60)
    
    devices = get_devices()
    if not devices:
        print("[-] Không tìm thấy thiết bị ADB nào đang kết nối! Hãy chạy 'adb devices' để check.")
        return

    print(f"[+] Tìm thấy {len(devices)} thiết bị: {', '.join(devices)}")

    min_sleep = 3
    max_sleep = 8
    print(f"[+] Thời gian nghỉ: ngẫu nhiên {min_sleep}s - {max_sleep}s.")

    threads = []
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    print(f"[+] Đang khởi chạy hệ thống ĐA LUỒNG trên {len(devices)} thiết bị...")
    for dev in devices:
        dev_short = dev[-4:] if len(dev) >= 4 else dev
        cmt_file = os.path.join(base_dir, f"cmt_{dev_short}.txt")
        
        if not os.path.exists(cmt_file):
            default_cmts = ["Tương tác nha!", "Chấm mút nha", "Cho mình xin giá"]
            try:
                with open(cmt_file, 'w', encoding='utf-8') as f:
                    f.write("\n".join(default_cmts))
                print(f"[+] Đã tạo file comment {cmt_file} cho Phone-{dev_short}")
            except Exception as e:
                print(f"[-] Lỗi tạo file {cmt_file}: {e}")
        else:
            print(f"[+] Đã tìm thấy file comment {cmt_file} cho Phone-{dev_short}")

        worker = Worker(dev, min_sleep, max_sleep, cmt_file)
        worker.daemon = True
        worker.start()
        threads.append(worker)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[-] Đã dừng tool theo yêu cầu người dùng (CTRL+C).")

if __name__ == '__main__':
    main()