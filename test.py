
import cv2, subprocess, numpy as np, os
try:
    print('Testing adb shell screencap...')
    subprocess.run('adb -s emulator-5554 shell screencap -p /sdcard/tmp_cap.png', shell=True, timeout=5)
    subprocess.run('adb -s emulator-5554 pull /sdcard/tmp_cap.png screen_test.png', shell=True, timeout=5)
    img = cv2.imread('screen_test.png')
    if img is not None:
        print('Shape:', img.shape)
        tmpl = cv2.imread('img/3.png')
        if tmpl is not None:
            res = cv2.matchTemplate(tmpl, img, cv2.TM_CCOEFF_NORMED)
            print('Max val 3:', cv2.minMaxLoc(res)[1])
        else:
            print('Template 3.png missing')
        tmpl1 = cv2.imread('img/1.png')
        print('Max val 1:', cv2.minMaxLoc(cv2.matchTemplate(tmpl1, img, cv2.TM_CCOEFF_NORMED))[1])
        print('Max val 5:', cv2.minMaxLoc(cv2.matchTemplate(cv2.imread('img/5.png'), img, cv2.TM_CCOEFF_NORMED))[1])
    else:
        print('Failed to load screen_test.png')
except Exception as e:
    print('Error:', e)

