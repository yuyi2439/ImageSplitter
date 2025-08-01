import os

import cv2
import numpy as np

RAW_DIR = 'raw'
OUTPUT_DIR = 'output'


def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)


def split_image_by_blank(img, min_blank_height=30):
    """按空白行分割图片，返回每个题目的图片列表"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY)
    # 统计每一行的白色像素数
    row_sums = np.sum(thresh == 255, axis=1)
    blank_rows = np.where(row_sums > 0.98 * img.shape[1])[0]

    # 找到连续的空白行区间
    splits = []
    last = 0
    for i in range(1, len(blank_rows)):
        if blank_rows[i] - blank_rows[i - 1] > 1:
            if blank_rows[i - 1] - last > min_blank_height:
                splits.append((last, blank_rows[i - 1]))
            last = blank_rows[i]
    # 最后一段
    if img.shape[0] - last > min_blank_height:
        splits.append((last, img.shape[0] - 1))

    # 分割图片
    images = []
    prev_end = 0
    for start, end in splits:
        if end - prev_end > min_blank_height:
            crop = img[prev_end:end, :]
            images.append(crop)
        prev_end = end
    return images


def process_images():
    ensure_dir(OUTPUT_DIR)
    for fname in os.listdir(RAW_DIR):
        if fname.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
            img_path = os.path.join(RAW_DIR, fname)
            img = cv2.imread(img_path)
            if img is None:
                continue
            sub_imgs = split_image_by_blank(img)
            for idx, sub_img in enumerate(sub_imgs):
                out_name = f"{os.path.splitext(fname)[0]}_q{idx+1}.png"
                out_path = os.path.join(OUTPUT_DIR, out_name)
                cv2.imwrite(out_path, sub_img)
            print(f"{fname} 分割为 {len(sub_imgs)} 题")


if __name__ == '__main__':
    process_images()
