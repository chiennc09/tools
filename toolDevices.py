import os
import time
import threading
import subprocess
import base64
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

# Cấu hình logging để print ra console đẹp hơn và có màu
logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s | %(levelname)s | %(message)s', 
    datefmt='%H:%M:%S'
)

class Auto:
    def __init__(self, handle):
        self.handle = handle

    def screen_capture(self):
        try:
            # Ưu tiên bắt luồng bytes trực tiếp (rất nhanh nhưng dễ kẹt trên Win)
            result = subprocess.run(
                f'adb -s {self.handle} exec-out screencap -p',
                shell=True,
                capture_output=True,
                timeout=3
            )
            image_bytes = result.stdout
            
            if not image_bytes:
                return None
                
            arr = np.frombuffer(image_bytes, np.uint8)
            if len(arr) == 0:
                raise ValueError("Buffer trống")
                
            return cv2.imdecode(arr, cv2.IMREAD_COLOR)

        except (subprocess.TimeoutExpired, ValueError):
            # Nếu exec-out bị treo / lag (Lỗi rất phổ biến của giả lập LDPlayer trên Windows)
            # >> Cứu hộ bằng cách chụp lưu vào ổ cứng giả lập rồi kéo ra ngoài
            try:
                subprocess.run(f'adb -s {self.handle} shell screencap -p /sdcard/tmp_cap.png', shell=True, timeout=5)
                subprocess.run(f'adb -s {self.handle} pull /sdcard/tmp_cap.png screen_{self.handle}.png', capture_output=True, shell=True, timeout=5)
                
                if os.path.exists(f'screen_{self.handle}.png'):
                    img = cv2.imread(f'screen_{self.handle}.png')
                    return img
            except Exception as e2:
                logging.error(f"[{self.handle}] Lỗi chụp hình Cứu hộ: {e2}")
            return None
        except Exception as e:
            logging.error(f"[{self.handle}] Lỗi screencap: {e}")
            return None

    def click(self, x, y):
        subprocess.run(f'adb -s {self.handle} shell input tap {x} {y}', shell=True)

    def swipe(self, x1, y1, x2, y2):
        subprocess.run(f"adb -s {self.handle} shell input touchscreen swipe {x1} {y1} {x2} {y2} 1000", shell=True)

    def back(self):
        subprocess.run(f"adb -s {self.handle} shell input keyevent 3", shell=True)

    def delete_cache(self, package):
        subprocess.run(f"adb -s {self.handle} shell pm clear {package}", shell=True)

    def off(self, package="com.facebook.katana"):
        subprocess.run(f"adb -s {self.handle} shell am force-stop {package}", shell=True)

    def InpuText(self, text=None, VN=""):
        # Chuyển hoàn toàn sang dùng Native ADB (Không xài Broadcast ADBKeyboard nữa)
        text_to_send = text if text is not None else VN
        
        # ADB 'input text' yêu cầu thay khoảng trắng bằng %s và escape dấu nháy đơn
        safe_text = str(text_to_send).replace("'", "\\'").replace(" ", "%s")
        
        # Gửi ký tự
        subprocess.run(f"adb -s {self.handle} shell input text '{safe_text}'", shell=True)

    def find(self, img_name, threshold=0.80):
        # Hạ threshold xuống 0.80 (độ chính xác 80%) thay vì 0.95 để thích ứng với giao diện FB hiện tại
        img_path = os.path.join(os.path.dirname(__file__) or '.', img_name)
        if not os.path.exists(img_path):
            return []
            
        template = cv2.imread(img_path)
        screen = self.screen_capture()
        if screen is None or template is None:
            return []
            
        try:
            result = cv2.matchTemplate(template, screen, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            
            # Gỡ lỗi: Lưu lại giá trị khớp cao nhất nếu nó gần đạt ngưỡng
            if 0.5 < max_val < threshold:
                logging.debug(f"[{self.handle}] Gần giống {img_name}: {max_val*100:.1f}% (Cần > {threshold*100}%)")

            loc = np.where(result >= threshold)
            retVal = list(zip(*loc[::-1]))
            return retVal
        except Exception as e:
            logging.error(f"[{self.handle}] Lỗi OpenCV: {e}")
            return []

def get_devices():
    try:
        output = subprocess.check_output("adb devices", shell=True).decode('utf-8')
        lines = output.strip().split('\n')[1:] # Bỏ đi dòng 'List of devices attached'
        devices = []
        for line in lines:
            if 'device' in line and 'offline' not in line:
                devices.append(line.split('\t')[0].strip())
        return devices
    except Exception as e:
        print(f"Lỗi lấy ID thiết bị: {e}")
        return []

class Worker(threading.Thread):
    def __init__(self, device_id, min_sleep, max_sleep, comments):
        super().__init__()
        self.device_id = device_id
        self.min_sleep = min_sleep
        self.max_sleep = max_sleep
        self.comments = comments
        self.d = Auto(device_id)
        self.is_running = True
        
        # Format tên đơn giản Phone-XXXX (Lấy 4 kí tự cuối của id ADB)
        self.name_ld = f"Phone-{device_id[-4:]}"

    def log(self, msg):
        logging.info(f"[{self.name_ld}] {msg}")

    def run(self):
        # Sử dụng State Machine, các biến trạng thái, tránh Đệ Quy Gọi lồng hàm
        state = 1
        error_count = 0

        while self.is_running:
            try:
                # Tính năng tự giải cứu khi bị crash fb hoặc lag mất element
                if error_count >= 10:
                    self.log("Lỗi liên tục 10 lần. Đang reset lại quy trình FB...")
                    self.d.off()
                    time.sleep(2)
                    state = 1
                    error_count = 0
                    continue

                if state == 1:
                    poin3 = self.d.find('img\\5.png', 0.80)
                    if poin3:
                        x, y = poin3[0][0], poin3[0][1]
                        self.d.swipe(x, y, x, y + 1500)
                        self.log("Vuốt đóng popup về NewFeed (5.png)")
                        time.sleep(1)
                        error_count = 0
                        continue

                    poin = self.d.find('img\\3.png', 0.80)
                    if poin:
                        self.d.click(poin[0][0], poin[0][1])
                        self.log("Mở App Facebook (3.png)")
                        state = 2
                        error_count = 0
                        time.sleep(1)
                        continue

                    poin2 = self.d.find('img\\1.png', 0.80)
                    if poin2:
                        self.d.click(poin2[0][0], poin2[0][1])
                        self.log("Phát hiện nút Like (1.png)")
                        state = 3
                        error_count = 0
                        time.sleep(1)
                        continue

                    error_count += 1
                    time.sleep(1)

                elif state == 2:
                    poin3 = self.d.find('img\\5.png', 0.80)
                    if poin3:
                        x, y = poin3[0][0], poin3[0][1]
                        self.d.swipe(x, y, x, y + 1500)
                        self.log("Vuốt đóng popup về NewFeed (5.png)")
                        error_count = 0
                        time.sleep(1)
                        continue

                    poin2 = self.d.find('img\\3.png', 0.80)
                    if poin2:
                        self.d.click(poin2[0][0], poin2[0][1])
                        self.log("Mở Feed Facebook (3.png)")
                        error_count = 0
                        time.sleep(1)
                        continue

                    poin = self.d.find('img\\1.png', 0.80)
                    if poin:
                        self.d.click(poin[0][0], poin[0][1])
                        self.log("Bấm LIKE bài viết !! (1.png)")
                        state = 3
                        error_count = 0
                        time.sleep(1)
                        continue

                    # Nếu không thấy các nút trên, thực hiện Lướt
                    self.log("Lướt New Feed (Swipe)...")
                    self.d.swipe(268, 705, 268, 362)
                    time.sleep(2)
                    self.d.swipe(268, 705, 268, 362)
                    time.sleep(1)
                    error_count += 1

                elif state == 3:
                    cmt_text = random.choice(self.comments).strip() if self.comments else "Tương tác tốt nhé"
                    self.current_cmt = cmt_text

                    poin7 = self.d.find('img\\7.png', 0.80)
                    if poin7:
                        self.d.click(poin7[0][0], poin7[0][1])
                        time.sleep(1)
                        self.log(f"Bấm ô nhập Cmt (7.png) - Gõ: [{cmt_text}]")
                        self.d.InpuText(VN=cmt_text) 
                        time.sleep(2)
                        state = 4
                        error_count = 0
                        continue

                    poin = self.d.find('img\\2.png', 0.80)
                    if poin:
                        self.d.click(poin[0][0], poin[0][1])
                        time.sleep(2)
                        self.log("Bấm Icon Bình Luận để mở Popup (2.png)")
                        error_count = 0
                        continue
                    
                    error_count += 1
                    time.sleep(1)

                elif state == 4:
                    poin6 = self.d.find('img\\6.png', 0.80)
                    if poin6:
                        self.log("Đã thấy nút Gửi (6.png), Bấm Gửi!")
                        self.d.click(poin6[0][0], poin6[0][1])
                        time.sleep(2)
                        error_count = 0

                    poin3 = self.d.find('img\\5.png', 0.80)
                    if poin3:
                        x, y = poin3[0][0], poin3[0][1]
                        self.d.swipe(x, y, x, y + 1500)
                        self.log("Vuốt Đóng Popup Comment về Feed (5.png)")
                        time.sleep(1)
                        
                        sleep_time = random.randint(self.min_sleep, self.max_sleep)
                        self.log(f"HOÀN THÀNH - Đang chờ ngủ ({sleep_time}s) để cày bài tiếp theo...")
                        time.sleep(sleep_time)
                        
                        state = 2 # Chuyển lại trạng thái lướt Feed
                        error_count = 0
                        continue

                    poin2 = self.d.find('img\\4.png', 0.80)
                    if poin2:
                        self.d.click(poin2[0][0], poin2[0][1])
                        self.log("Bấm Trở Về / Tắt Cmt (4.png)")
                        time.sleep(1)
                        
                        sleep_time = random.randint(self.min_sleep, self.max_sleep)
                        self.log(f"HOÀN THÀNH - Đang chờ ngủ ({sleep_time}s) để cày bài tiếp theo...")
                        time.sleep(sleep_time)
                        
                        state = 2
                        error_count = 0
                        continue

                    error_count += 1
                    time.sleep(1)

            except Exception as e:
                self.log(f"Lỗi Script: {e}")
                error_count += 1
                time.sleep(2)

def main():
    print("="*60)
    print("          TOOL FACEBOOK AUTOMATION NEW PRO (2026)")
    print("="*60)
    
    devices = get_devices()
    if not devices:
        print("[-] Không tìm thấy thiết bị ADB nào đang kết nối! Hãy chạy 'adb devices' để check.")
        return

    print(f"[+] Tìm thấy {len(devices)} thiết bị: {', '.join(devices)}")

    lis_cm = ["Tương tác nha!", "Chấm mút nha", "Cho mình xin giá"]
    try:
        if os.path.exists('cmt.txt'):
            with open('cmt.txt', 'r', encoding='utf-8') as f:
                lis_cm = [l.strip() for l in f.readlines() if l.strip()]
            print(f"[+] Đã tải {len(lis_cm)} bình luận từ file cmt.txt.")
        else:
            print("[-] Không có file cmt.txt, tự động tạo mới.")
            with open('cmt.txt', 'w', encoding='utf-8') as f:
                f.write("\n".join(lis_cm))
    except Exception as e:
        print(f"[-] Lỗi đọc file cmt.txt: {e}")

    min_sleep = 10
    max_sleep = 30
    print(f"[+] Sử dụng thời gian nghỉ mặc định: {min_sleep}s - {max_sleep}s (do chế độ IDE debug thường không cho gõ phím).")

    threads = []
    print(f"[+] Đang khởi chạy hệ thống ĐA LUỒNG trên {len(devices)} thiết bị...")
    for dev in devices:
        worker = Worker(dev, min_sleep, max_sleep, lis_cm)
        worker.daemon = True # Nếu tắt tiến trình chính thì dừng hết
        worker.start()
        threads.append(worker)

    try:
        # Giữ main console thread chạy tiếp
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[-] Đã dừng tool theo yêu cầu người dùng (CTRL+C).")

if __name__ == '__main__':
    main()