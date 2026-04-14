import threading
import os
import random
import time

from core.adb_helper import AdbHelper
from core.image_matcher import ImageMatcher
from core.utils.swipe_logic import (
    sleep_random, get_swipe_coords_2_7_up, 
    get_swipe_coords_top_down, get_swipe_close_popup
)

class BotWorker(threading.Thread):
    def __init__(self, device_id, mode, resolution, base_resolution_str, min_sleep, max_sleep, log_callback):
        super().__init__()
        self.device_id = device_id
        self.mode = mode
        self.resolution = resolution
        self.min_sleep = min_sleep
        self.max_sleep = max_sleep
        self.log_callback = log_callback
        
        self.is_running = True
        self.adb = AdbHelper(device_id)
        self.newfeed_swipes = 0
        
        # Parse base_resolution
        try:
            bw, bh = map(int, base_resolution_str.lower().split('x'))
        except (ValueError, AttributeError):
            bw, bh = 720, 1280
            
        self.matcher = ImageMatcher(base_resolution=(bw, bh), current_resolution=resolution)
        
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.cmt_dir = os.path.join(self.base_dir, "comment")
        self.cmt_file = os.path.join(self.cmt_dir, f"cmt_{device_id[-4:]}.txt")
        self.setup_comment_file()

        # Try extract resolution bounds for swiping
        try:
            self.screen_w, self.screen_h = map(int, resolution.lower().split('x'))
        except:
            self.screen_w, self.screen_h = 720, 1280

    def setup_comment_file(self):
        if not os.path.exists(self.cmt_dir):
            os.makedirs(self.cmt_dir)
        if not os.path.exists(self.cmt_file):
            default_cmts = ["Xin chào", "Xin cảm ơn", "Thông tin hữu ích"]
            with open(self.cmt_file, 'w', encoding='utf-8') as f:
                f.write("\n".join(default_cmts))

    def get_comment(self):
        try:
            with open(self.cmt_file, 'r', encoding='utf-8') as f:
                lines = [l.strip() for l in f.readlines() if l.strip()]
            if lines:
                return random.choice(lines)
        except Exception:
            pass
        return "Tuyệt vời"

    def log(self, msg):
        self.log_callback(self.device_id, msg)

    def run(self):
        self.log(f"Khởi động chế độ {self.mode}")
        state = 'ENTER_APP'
        error_count = 0

        while self.is_running:
            try:
                if error_count > 10:
                    self.log("Lỗi định vị 10 lần. Dừng Facebook và bắt đầu lại...")
                    self.adb.force_stop()
                    sleep_random(1, 2)
                    state = 'ENTER_APP'
                    error_count = 0
                
                screen = self.adb.capture()
                if screen is None:
                    error_count += 1
                    sleep_random(1, 2)
                    continue

                # ENTER APP LOGIC
                if state == 'ENTER_APP':
                    pt = self.matcher.find_image(screen, os.path.join(self.base_dir, 'img', 'fb.png'))
                    if pt:
                        self.log("Đã tìm thấy app Facebook. Đang mở...")
                        self.adb.click(*pt)
                        sleep_random(10, 15) # Chờ app load
                        self.newfeed_swipes = 0
                        if 'NEWFEED' in self.mode or 'COMMENT' in self.mode:
                            state = 'NEWFEED_SPACE'
                        elif 'REELS' in self.mode:
                            state = 'REELS_INIT'
                        else:
                            state = 'NEWFEED_SPACE'
                        error_count = 0
                    else:
                        self.log("Đang tìm fb.png...")
                        error_count += 1
                        sleep_random(1, 2)

                # MODE: NEWFEED_SPACE
                elif state == 'NEWFEED_SPACE':
                    if 'NEWFEED' in self.mode:
                        pt_like = self.matcher.find_image(screen, os.path.join(self.base_dir, 'img', 'newfeed', 'like.png'))
                        if pt_like and random.random() < 0.2:
                            self.log("Thấy nút Like. Tiến hành thả tim!")
                            self.adb.click(*pt_like)
                            sleep_random(1, 2)
                            
                    if 'COMMENT' in self.mode and self.newfeed_swipes >= 2:
                        pt_cmt = self.matcher.find_image(screen, os.path.join(self.base_dir, 'img', 'comment', 'comment.png'))
                        if pt_cmt and random.random() < 0.2:
                            self.log("Đã thấy mục Comment. Bấm vào...")
                            self.adb.click(*pt_cmt)
                            sleep_random(5, 10)
                            state = 'COMMENT_TYPING'
                            self.newfeed_swipes = 0
                            error_count = 0
                            continue
                            
                    if 'REELS' in self.mode and random.random() < 0.1:
                        self.log("Chuyển sang luồng Reels...")
                        state = 'REELS_INIT'
                        continue
                        
                    self.log("Lướt Newfeed...")
                    x1, y1, x2, y2 = get_swipe_coords_2_7_up(self.screen_w, self.screen_h)
                    self.adb.swipe(x1, y1, x2, y2)
                    self.newfeed_swipes += 1
                    sleep_time = random.uniform(self.min_sleep, self.max_sleep)
                    self.log(f"Đọc newfeed {sleep_time:.1f}s")
                    sleep_random(sleep_time, sleep_time + 1)
                    error_count = 0

                # Quá trình đồng bộ chuyển sang Reels
                elif state == 'REELS_INIT':
                    self.log("Lướt ngược để hiện thanh bar tab...")
                    x1, y1, x2, y2 = get_swipe_coords_top_down(self.screen_w, self.screen_h)
                    self.adb.swipe(x1, y1, x2, y2)
                    sleep_random(1, 2)
                    
                    screen2 = self.adb.capture()
                    if screen2 is not None:
                        pt_reels = self.matcher.find_image(screen2, os.path.join(self.base_dir, 'img', 'reels', 'reels.png'))
                        if not pt_reels:
                            pt_reels = self.matcher.find_image(screen2, os.path.join(self.base_dir, 'img', 'reels', 'reels2.png'))
                            if not pt_reels:
                                pt_reels = self.matcher.find_image(screen2, os.path.join(self.base_dir, 'img', 'reels', 'reels3.png'))
                            
                        if pt_reels:
                            self.log("Bấm sang tab Reels")
                            self.adb.click(*pt_reels)
                            state = 'REELS_SPACE'
                            sleep_random(3, 5)
                            error_count = 0
                            continue
                        else:
                            self.log("Không thấy icon Reels, lướt ngược làm lại...")
                            error_count += 1
                            sleep_random(1, 2)
                    else:
                        error_count += 1

                # MODE: REELS_SPACE
                elif state == 'REELS_SPACE':
                    if ('NEWFEED' in self.mode or 'COMMENT' in self.mode) and random.random() < 0.05:
                        pt_home = self.matcher.find_image(screen, os.path.join(self.base_dir, 'img', 'reels', 'home.png'))
                        if pt_home:
                            self.log("Đã xem đủ Reels, bấm Home để về lại Newfeed...")
                            self.adb.click(*pt_home)
                            state = 'NEWFEED_SPACE'
                            self.newfeed_swipes = 0
                            sleep_random(3, 5)
                            continue

                    sleep_time = random.uniform(self.min_sleep, self.max_sleep)
                    self.log(f"Đang xem Reels {sleep_time:.1f}s...")
                    sleep_random(sleep_time, sleep_time + 1)

                    self.log("Lướt Next Reels")
                    x1, y1, x2, y2 = get_swipe_coords_2_7_up(self.screen_w, self.screen_h)
                    self.adb.swipe(x1, y1, x2, y2)
                    error_count = 0

                elif state == 'COMMENT_TYPING':
                    pt_type = self.matcher.find_image(screen, os.path.join(self.base_dir, 'img', 'comment', 'type.png'))
                    if pt_type:
                        self.log("Nháy vào ô input...")
                        self.adb.click(*pt_type)
                        sleep_random(3, 5)
                        
                        cmt_text = self.get_comment()
                        self.log(f"Gõ nội dung: {cmt_text}")
                        self.adb.input_text(cmt_text)
                        sleep_random(3, 5)
                        
                        state = 'COMMENT_SENDING'
                        error_count = 0
                    else:
                        error_count += 1
                        sleep_random(3, 5)

                elif state == 'COMMENT_SENDING':
                    pt_send = self.matcher.find_image(screen, os.path.join(self.base_dir, 'img', 'comment', 'send.png'))
                    if pt_send:
                        self.log("Đã bấm Gửi comment")
                        self.adb.click(*pt_send)
                        
                        sleep_time = random.uniform(self.min_sleep, self.max_sleep)
                        self.log(f"Ngắm nội dung bình luận trong form {sleep_time:.1f}s...")
                        sleep_random(sleep_time, sleep_time + 1)
                        
                        self.log("Kéo đóng popup comment...")
                        x1, y1, x2, y2 = get_swipe_close_popup(self.screen_w, self.screen_h)
                        self.adb.swipe(x1, y1, x2, y2, duration=1500)
                        sleep_random(1, 2)
                        
                        # Về lại việc tìm bài đăng khác
                        state = 'NEWFEED_SPACE'
                        self.newfeed_swipes = 0
                        error_count = 0
                        
                        sleep_time = random.uniform(self.min_sleep, self.max_sleep)
                        self.log(f"Nán lại ngắm bài đăng vừa comment {sleep_time:.1f}s...")
                        sleep_random(sleep_time, sleep_time + 1)
                    else:
                        # Nếu ko thấy nút gửi, có khi dã nhập lỗi or che màn, gạt xuống để đóng
                        self.log("Chưa thấy nút gửi, kéo đóng popup thử...")
                        x1, y1, x2, y2 = get_swipe_close_popup(self.screen_w, self.screen_h)
                        self.adb.swipe(x1, y1, x2, y2, duration=1500)
                        sleep_random(1, 2)
                        state = 'NEWFEED_SPACE'
                        self.newfeed_swipes = 0
                        error_count += 1

            except Exception as e:
                self.log(f"Exception lặp: {e}")
                error_count += 1
                sleep_random(1, 2)

    def stop(self):
        self.is_running = False
        self.log("Yêu cầu dừng thiết bị...")
