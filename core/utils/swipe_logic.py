import random
import time

def sleep_random(min_s, max_s):
    time.sleep(random.uniform(min_s, max_s))

def get_swipe_coords_2_7_up(screen_w, screen_h):
    # Lướt từ dưới lên trên (dài và có độ chéo giống tay người)
    # Bắt đầu tự do trên trục x (khoảng 20% đến 80% chiều rộng)
    x1 = random.randint(int(screen_w * 0.2), int(screen_w * 0.8))
    # Kết thúc trục x cũng ngẫu nhiên để tạo thành đường chéo
    x2 = random.randint(int(screen_w * 0.2), int(screen_w * 0.8))
    
    # Kéo dài hành trình vuốt (từ tận 85% chiều cao dưới màn hình lên tới 15% chiều cao trên)
    y1 = random.randint(int(screen_h * 0.75), int(screen_h * 0.85))
    y2 = random.randint(int(screen_h * 0.15), int(screen_h * 0.3))
    return x1, y1, x2, y2

def get_swipe_coords_top_down(screen_w, screen_h):
    # Lướt từ trên xuống để hiện tab bar
    x1 = random.randint(int(screen_w * 0.2), int(screen_w * 0.8))
    x2 = random.randint(int(screen_w * 0.2), int(screen_w * 0.8))
    y1 = random.randint(int(screen_h * 0.1), int(screen_h * 0.25))
    y2 = random.randint(int(screen_h * 0.5), int(screen_h * 0.7))
    return x1, y1, x2, y2

def get_swipe_close_popup(screen_w, screen_h):
    # Vuốt từ nửa trên xuống dưới để tắt
    x1 = random.randint(int(screen_w * 0.2), int(screen_w * 0.8))
    x2 = random.randint(int(screen_w * 0.2), int(screen_w * 0.8))
    y1 = random.randint(int(screen_h * 0.04), int(screen_h * 0.06))
    y2 = random.randint(int(screen_h * 0.8), int(screen_h * 0.91))
    return x1, y1, x2, y2
