import cv2
import numpy as np
import os

class ImageMatcher:
    def __init__(self, base_resolution=(720, 1280), current_resolution=None):
        self.base_w, self.base_h = base_resolution
        if current_resolution:
            try:
                self.curr_w, self.curr_h = map(int, current_resolution.lower().split('x'))
            except:
                self.curr_w, self.curr_h = self.base_w, self.base_h
        else:
            self.curr_w, self.curr_h = self.base_w, self.base_h

        # Calculate ratios for X and Y
        self.ratio_x = self.curr_w / self.base_w
        self.ratio_y = self.curr_h / self.base_h

    def find_image(self, screen_img, template_path, threshold=0.80):
        if screen_img is None or not os.path.exists(template_path):
            return None

        template = cv2.imread(template_path)
        if template is None:
            return None

        # Resize template if resolution differs from base
        if self.ratio_x != 1.0 or self.ratio_y != 1.0:
            new_w = int(template.shape[1] * self.ratio_x)
            new_h = int(template.shape[0] * self.ratio_y)
            # Avoid resizing to 0
            if new_w > 0 and new_h > 0:
                template = cv2.resize(template, (new_w, new_h))

        try:
            result = cv2.matchTemplate(template, screen_img, cv2.TM_CCOEFF_NORMED)
            loc = np.where(result >= threshold)
            matches = list(zip(*loc[::-1]))
            if not matches:
                return None
            
            h, w = template.shape[:2]
            # Return center of the matched area
            return (matches[0][0] + w//2, matches[0][1] + h//2)
        except Exception as e:
            print(f"Error in image matching: {e}")
            return None
