import os
from pathlib import Path

from PIL import Image
from PySide6 import QtCore, QtGui


class ImageState:
    def __init__(self, path: Path | str):
        self.path = path
        self.image = Image.open(path)
        self.angle = 0
        self.rects: list[QtCore.QRectF] = []
        self.transform: 'QtGui.QTransform | None' = None
        self.center: 'QtCore.QPointF | None' = None

    def get_display_image(self):
        return self.image.rotate(-self.angle, expand=True)

    @staticmethod
    def save_all(states: list['ImageState'], save_path):
        with open(save_path, "w", encoding="utf-8") as f:
            for img_state in states:
                has_angle = img_state.angle != 0
                has_rects = bool(img_state.rects)
                if not has_angle and not has_rects:
                    continue
                img_name = os.path.basename(img_state.path)
                f.write(f"{img_name}\n")
                if has_angle:
                    f.write(f"angle: {img_state.angle}\n")
                for rect in img_state.rects:
                    f.write(
                        f"rect: {int(rect.x())},{int(rect.y())},{int(rect.width())},{int(rect.height())}\n"
                    )
                f.write("\n")

    @staticmethod
    def load_all(states: list['ImageState'], load_path):
        if not os.path.exists(load_path):
            return False
        with open(load_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        img_map = {os.path.basename(img_state.path): img_state for img_state in states}
        cur_img = None
        for line in lines:
            line = line.strip()
            if not line:
                cur_img = None
                continue
            if (
                line.endswith(".jpg")
                or line.endswith(".png")
                or line.endswith(".jpeg")
                or line.endswith(".bmp")
            ):
                cur_img = img_map.get(line)
                if cur_img:
                    cur_img.angle = 0
                    cur_img.rects = []
                continue
            if cur_img is None:
                continue
            if line.startswith("angle:"):
                try:
                    cur_img.angle = int(line.split(":", 1)[1].strip())
                except Exception:
                    pass
            elif line.startswith("rect:"):
                try:
                    vals = line.split(":", 1)[1].strip().split(",")
                    x, y, w, h = map(int, vals)
                    cur_img.rects.append(QtCore.QRectF(x, y, w, h))
                except Exception:
                    pass
        return True
