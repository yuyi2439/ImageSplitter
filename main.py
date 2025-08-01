import os

from PIL import Image
from PyQt6 import QtCore, QtGui, QtWidgets

RAW_DIR = 'raw'


class RectItem(QtWidgets.QGraphicsRectItem):
    def __init__(self, *args):
        super().__init__(*args)
        self.setPen(QtGui.QPen(QtCore.Qt.GlobalColor.red, 2))


class ImageView(QtWidgets.QGraphicsView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._zoom = 0
        self._empty = True
        self.setDragMode(QtWidgets.QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(
            QtWidgets.QGraphicsView.ViewportAnchor.AnchorUnderMouse
        )
        self.setResizeAnchor(QtWidgets.QGraphicsView.ViewportAnchor.AnchorUnderMouse)

    def wheelEvent(self, event):
        assert event
        if event.angleDelta().y() > 0:
            factor = 1.25
            self._zoom += 1
        else:
            factor = 0.8
            self._zoom -= 1
        self.scale(factor, factor)

    def mousePressEvent(self, event):
        assert event
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.setDragMode(QtWidgets.QGraphicsView.DragMode.ScrollHandDrag)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self.setDragMode(QtWidgets.QGraphicsView.DragMode.ScrollHandDrag)
        super().mouseReleaseEvent(event)

    def reset_zoom(self):
        self.resetTransform()
        self._zoom = 0


class ImageState:
    def __init__(self, path):
        self.path = path
        self.image = Image.open(path)
        self.angle = 0
        self.rects = []
        self._transform: 'QtGui.QTransform | None' = None
        self.center: 'QtCore.QPointF | None' = None

    def get_display_image(self):
        return self.image.rotate(-self.angle, expand=True)

    def to_rect_items(self):
        return [RectItem(QtCore.QRectF(x, y, w, h)) for (x, y, w, h) in self.rects]

    @staticmethod
    def save_all(states, save_path):
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
                for x, y, w, h in img_state.rects:
                    f.write(f"rect: {int(x)},{int(y)},{int(w)},{int(h)}\n")
                f.write("\n")

    @staticmethod
    def load_all(states, load_path):
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
                    cur_img.rects.append((x, y, w, h))
                except Exception:
                    pass
        return True


class ImageSplitterApp(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("图片分割工具")
        self.cur_idx = 0

        self.images = [
            ImageState(os.path.join(RAW_DIR, f))
            for f in sorted(os.listdir(RAW_DIR))
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))
        ]

        self.scene = QtWidgets.QGraphicsScene()
        self.view = ImageView(self.scene)
        self.setCentralWidget(self.view)

        toolbar = QtWidgets.QToolBar()
        self.addToolBar(toolbar)
        toolbar.addAction("上一张", self.prev_image)
        toolbar.addAction("下一张", self.next_image)
        toolbar.addAction("旋转", self.rotate_image)
        toolbar.addAction("加载状态", self.load_states)
        toolbar.addAction("保存状态", self.save_states)
        toolbar.addAction("保存分割图片", self.save_crops)

        self.view.setMouseTracking(True)

        binding = self.view.viewport()
        assert binding
        binding.installEventFilter(self)
        self.drawing = False
        self.start = QtCore.QPointF()
        self.temp_rect = None

        self.display_image()

    @property
    def cur_image(self):
        return self.images[self.cur_idx]

    def display_image(self):
        img = self.cur_image.get_display_image().convert("RGBA")
        data = img.tobytes("raw", "RGBA")
        qimg = QtGui.QImage(
            data, img.width, img.height, QtGui.QImage.Format.Format_RGBA8888
        )
        pixmap = QtGui.QPixmap.fromImage(qimg)
        self.scene.clear()
        self.scene.addPixmap(pixmap)
        self.view.setSceneRect(QtCore.QRectF(pixmap.rect()))
        # 添加所有框
        for rect_item in self.cur_image.to_rect_items():
            self.scene.addItem(rect_item)
        # 优雅地恢复状态：只有transform和center都为None时才自适应
        if self.cur_image._transform is not None and self.cur_image.center is not None:
            self.view.setTransform(self.cur_image._transform)
            self.view.centerOn(self.cur_image.center)
        else:
            self.view.reset_zoom()
            self.view.fitInView(
                self.scene.sceneRect(), QtCore.Qt.AspectRatioMode.KeepAspectRatio
            )
            # 保存自适应后的transform和center，避免下次再自适应
            self.cur_image._transform = self.view.transform()
            binding = self.view.viewport()
            assert binding
            self.cur_image.center = self.view.mapToScene(binding.rect().center())

    def save_current_state(self):
        # 保存当前图片的缩放、中心、框
        self.cur_image._transform = self.view.transform()
        binding = self.view.viewport()
        assert binding
        self.cur_image.center = self.view.mapToScene(binding.rect().center())
        # 框
        self.cur_image.rects = [
            (
                rect.rect().x(),
                rect.rect().y(),
                rect.rect().width(),
                rect.rect().height(),
            )
            for rect in self.scene.items()
            if isinstance(rect, RectItem)
        ]

    def prev_image(self):
        self.save_current_state()
        if self.cur_idx > 0:
            self.cur_idx -= 1
            self.display_image()

    def next_image(self):
        self.save_current_state()
        if self.cur_idx < len(self.images) - 1:
            self.cur_idx += 1
            self.display_image()

    def rotate_image(self):
        self.cur_image.angle = (self.cur_image.angle + 90) % 360
        self.display_image()

    def save_states(self):
        save_path = os.path.join("image_states.txt")
        ImageState.save_all(self.images, save_path)
        QtWidgets.QMessageBox.information(
            self, "保存成功", "所有图片的状态已保存到 image_states.txt"
        )

    def load_states(self):
        state_path = os.path.join("image_states.txt")
        if not os.path.exists(state_path):
            QtWidgets.QMessageBox.warning(self, "未找到", "image_states.txt 文件不存在")
            return
        success = ImageState.load_all(self.images, state_path)
        if success:
            self.display_image()
            QtWidgets.QMessageBox.information(
                self, "加载成功", "图片状态已从 image_states.txt 加载"
            )

    def save_crops(self):
        os.makedirs("output", exist_ok=True)
        all_saved_rects = set()
        for img_state in self.images:
            img = img_state.get_display_image()
            img_name = os.path.basename(img_state.path)
            w_img, h_img = img.size
            for x, y, w_rect, h_rect in img_state.rects:
                x0 = max(0, int(x))
                y0 = max(0, int(y))
                x1 = min(w_img, int(x + w_rect))
                y1 = min(h_img, int(y + h_rect))
                if x1 <= x0 or y1 <= y0:
                    raise ValueError(
                        f"Invalid rectangle for image {img_name}: ({x0}, {y0}, {x1}, {y1})"
                    )
                rect_key = (img_name, x0, y0, x1, y1)
                if rect_key in all_saved_rects:
                    continue
                all_saved_rects.add(rect_key)
                cropped = img.crop((x0, y0, x1, y1))
                out_name = f"{os.path.splitext(img_name)[0]}_{x0}_{y0}_{x1}_{y1}.png"
                cropped.save(os.path.join("output", out_name))
        QtWidgets.QMessageBox.information(
            self, "保存成功", "所有分割图片已保存到output文件夹"
        )

    def eventFilter(  # pyright: ignore[reportIncompatibleMethodOverride]
        self, source, event
    ):
        if source is self.view.viewport():
            if event.type() == QtCore.QEvent.Type.MouseButtonPress:
                if (
                    event.button() == QtCore.Qt.MouseButton.LeftButton
                    and event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier
                ):
                    self.drawing = True
                    self.start = self.view.mapToScene(event.pos())
                    self.temp_rect = RectItem(QtCore.QRectF(self.start, self.start))
                    self.scene.addItem(self.temp_rect)
                    self.view.setDragMode(QtWidgets.QGraphicsView.DragMode.NoDrag)
                    return True
                else:
                    self.view.setDragMode(
                        QtWidgets.QGraphicsView.DragMode.ScrollHandDrag
                    )
                    self.drawing = False
                    self.temp_rect = None
            elif event.type() == QtCore.QEvent.Type.MouseMove:
                if self.drawing and self.temp_rect:
                    end = self.view.mapToScene(event.pos())
                    rect = QtCore.QRectF(self.start, end).normalized()
                    self.temp_rect.setRect(rect)
                    return True
            elif event.type() == QtCore.QEvent.Type.MouseButtonRelease:
                if self.drawing and self.temp_rect:
                    end = self.view.mapToScene(event.pos())
                    rect = QtCore.QRectF(self.start, end).normalized()
                    if rect.width() > 10 and rect.height() > 10:
                        self.cur_image.rects.append(
                            (rect.x(), rect.y(), rect.width(), rect.height())
                        )
                    self.scene.removeItem(self.temp_rect)
                    self.temp_rect = None
                    self.drawing = False
                    self.view.setDragMode(
                        QtWidgets.QGraphicsView.DragMode.ScrollHandDrag
                    )
                    # 先保存当前缩放和中心
                    self.cur_image._transform = self.view.transform()
                    binding = self.view.viewport()
                    assert binding
                    self.cur_image.center = self.view.mapToScene(
                        binding.rect().center()
                    )
                    self.display_image()
                    return True
        return super().eventFilter(source, event)

    def keyPressEvent(self, event):  # pyright: ignore[reportIncompatibleMethodOverride]
        # Ctrl+Z 撤销上一步框选
        if (
            event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier
            and event.key() == QtCore.Qt.Key.Key_Z
        ):
            if self.cur_image.rects:
                self.cur_image.rects.pop()
                # 先保存当前缩放和中心
                self.cur_image._transform = self.view.transform()
                binding = self.view.viewport()
                assert binding
                self.cur_image.center = self.view.mapToScene(binding.rect().center())
                self.display_image()
        else:
            super().keyPressEvent(event)


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    win = ImageSplitterApp()
    win.show()
    sys.exit(app.exec())
