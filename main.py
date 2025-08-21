import os

from PySide6 import QtCore, QtGui, QtWidgets

from src.image_state import ImageState

RAW_DIR = 'raw'


class RectItem(QtWidgets.QGraphicsRectItem):
    HANDLE_SIZE = 16

    def __init__(
        self, rect: QtCore.QRectF | QtCore.QRect, parent: 'ImageState | None' = None
    ):
        super().__init__(rect)
        self.setAcceptHoverEvents(True)
        self._parent = parent
        self._resizing = False
        self._resizeDir = None

    def shape(self):
        # 只让边框区域响应鼠标事件
        path = QtGui.QPainterPath()
        rect = self.rect()
        path.addRect(rect)
        inner = rect.adjusted(
            self.HANDLE_SIZE, self.HANDLE_SIZE, -self.HANDLE_SIZE, -self.HANDLE_SIZE
        )
        if inner.width() > 0 and inner.height() > 0:
            path_inner = QtGui.QPainterPath()
            path_inner.addRect(inner)
            path = path.subtracted(path_inner)
        return path

    def hoverMoveEvent(self, event: QtWidgets.QGraphicsSceneHoverEvent):
        pos = event.pos()
        rect = self.rect()
        margin = self.HANDLE_SIZE
        # 判断鼠标是否在边缘
        if abs(pos.x() - rect.left()) < margin:
            self.setCursor(QtCore.Qt.CursorShape.SizeHorCursor)
            self._resizeDir = 'left'
        elif abs(pos.x() - rect.right()) < margin:
            self.setCursor(QtCore.Qt.CursorShape.SizeHorCursor)
            self._resizeDir = 'right'
        elif abs(pos.y() - rect.top()) < margin:
            self.setCursor(QtCore.Qt.CursorShape.SizeVerCursor)
            self._resizeDir = 'top'
        elif abs(pos.y() - rect.bottom()) < margin:
            self.setCursor(QtCore.Qt.CursorShape.SizeVerCursor)
            self._resizeDir = 'bottom'
        else:
            self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
            self._resizeDir = None
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent):
        if event.button() == QtCore.Qt.MouseButton.LeftButton and self._resizeDir:
            self._resizing = True
            self._startPos = event.pos()
            self._origRect = self.rect()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent):
        if self._resizing and self._resizeDir:
            delta = event.pos() - self._startPos
            rect = QtCore.QRectF(self._origRect)
            if self._resizeDir == 'left':
                rect.setLeft(rect.left() + delta.x())
            elif self._resizeDir == 'right':
                rect.setRight(rect.right() + delta.x())
            elif self._resizeDir == 'top':
                rect.setTop(rect.top() + delta.y())
            elif self._resizeDir == 'bottom':
                rect.setBottom(rect.bottom() + delta.y())
            # 限制最小尺寸
            if rect.width() > 10 and rect.height() > 10:
                self.setRect(rect.normalized())
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent):
        if not self._resizing:
            super().mouseReleaseEvent(event)
        self._resizing = False
        event.accept()
        if self._parent:
            self._parent.rects.remove(self._origRect)
            self._parent.rects.append(self.rect())


class ImageView(QtWidgets.QGraphicsView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._empty = True
        self.setDragMode(QtWidgets.QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(
            QtWidgets.QGraphicsView.ViewportAnchor.AnchorUnderMouse
        )
        self.setResizeAnchor(QtWidgets.QGraphicsView.ViewportAnchor.AnchorUnderMouse)

    def wheelEvent(self, event: QtGui.QWheelEvent):
        if event.angleDelta().y() > 0:
            factor = 1.25
        else:
            factor = 0.8
        self.scale(factor, factor)

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.setDragMode(QtWidgets.QGraphicsView.DragMode.ScrollHandDrag)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        self.setDragMode(QtWidgets.QGraphicsView.DragMode.ScrollHandDrag)
        super().mouseReleaseEvent(event)

    def reset_zoom(self):
        self.resetTransform()


class ImageSplitterApp(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("图片分割工具")
        self.cur_idx = 0

        # 设置主窗口大小并居中
        self.resize(1200, 800)
        qr = self.frameGeometry()
        cp = QtWidgets.QApplication.primaryScreen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

        # 设置全局字体
        font = QtGui.QFont("微软雅黑", 11)
        QtWidgets.QApplication.setFont(font)

        # 设置主窗口背景色
        self.setStyleSheet("QMainWindow { background: #f7f7fa; }")

        self.images = [
            ImageState(os.path.join(RAW_DIR, f))
            for f in sorted(os.listdir(RAW_DIR))
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))
        ]

        self.scene = QtWidgets.QGraphicsScene()
        self.img_view = ImageView(self.scene)
        # 设置QGraphicsView背景色
        self.img_view.setBackgroundBrush(QtGui.QColor("#e6e6ed"))
        self.setCentralWidget(self.img_view)

        # 美化工具栏
        toolbar = QtWidgets.QToolBar()
        toolbar.setMovable(False)
        toolbar.setStyleSheet(
            """
            QToolBar {
                spacing: 12px;
                background: #f0f0f6;
                border-bottom: 1px solid #cccccc;
            }
            QToolButton {
                background: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 6px;
                padding: 6px 18px;
                margin: 4px;
                min-width: 80px;
                font-weight: bold;
            }
            QToolButton:hover {
                background: #e0e7ff;
                border: 1.5px solid #7baaf7;
            }
            QToolButton:pressed {
                background: #bdd7fa;
            }
        """
        )
        self.addToolBar(toolbar)

        # 添加工具栏按钮并加分隔符
        prev_act = QtGui.QAction(QtGui.QIcon.fromTheme("go-previous"), "上一张", self)
        next_act = QtGui.QAction(QtGui.QIcon.fromTheme("go-next"), "下一张", self)
        rotate_act = QtGui.QAction(
            QtGui.QIcon.fromTheme("object-rotate-right"), "旋转", self
        )
        load_act = QtGui.QAction(
            QtGui.QIcon.fromTheme("document-open"), "加载状态", self
        )
        save_act = QtGui.QAction(
            QtGui.QIcon.fromTheme("document-save"), "保存状态", self
        )
        crop_act = QtGui.QAction(
            QtGui.QIcon.fromTheme("edit-cut"), "保存分割图片", self
        )

        prev_act.triggered.connect(self.prev_image)
        next_act.triggered.connect(self.next_image)
        rotate_act.triggered.connect(self.rotate_image)
        load_act.triggered.connect(self.load_states)
        save_act.triggered.connect(self.save_states)
        crop_act.triggered.connect(self.save_crops)

        toolbar.addAction(prev_act)
        toolbar.addAction(next_act)
        toolbar.addSeparator()
        toolbar.addAction(rotate_act)
        toolbar.addSeparator()
        toolbar.addAction(load_act)
        toolbar.addAction(save_act)
        toolbar.addSeparator()
        toolbar.addAction(crop_act)

        self.img_view.setMouseTracking(True)
        self.img_view.viewport().installEventFilter(self)
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
        self.img_view.setSceneRect(QtCore.QRectF(pixmap.rect()))
        # 添加所有框
        for rect in self.cur_image.rects:
            self.scene.addItem(RectItem(rect, self.cur_image))
        # 优雅地恢复状态：只有transform和center都为None时才自适应
        if self.cur_image.transform is not None and self.cur_image.center is not None:
            self.img_view.setTransform(self.cur_image.transform)
            self.img_view.centerOn(self.cur_image.center)
        else:
            self.img_view.reset_zoom()
            self.img_view.fitInView(
                self.scene.sceneRect(), QtCore.Qt.AspectRatioMode.KeepAspectRatio
            )
            # 保存自适应后的transform和center，避免下次再自适应
            self.cur_image.transform = self.img_view.transform()
            self.cur_image.center = self.img_view.mapToScene(
                self.img_view.viewport().rect().center()
            )

    def save_current_state(self):
        # 保存当前图片的缩放、中心、框
        self.cur_image.transform = self.img_view.transform()
        self.cur_image.center = self.img_view.mapToScene(
            self.img_view.viewport().rect().center()
        )
        # 框
        self.cur_image.rects = [
            rect_item.rect()
            for rect_item in self.scene.items()
            if isinstance(rect_item, RectItem)
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
            for rect in img_state.rects:
                x, y, w_rect, h_rect = rect.x(), rect.y(), rect.width(), rect.height()
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

    def eventFilter(self, object: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if object is not self.img_view.viewport():
            return super().eventFilter(object, event)
        if not isinstance(event, QtGui.QMouseEvent):
            return super().eventFilter(object, event)

        if event.type() == QtCore.QEvent.Type.MouseButtonPress:
            if (
                event.button() == QtCore.Qt.MouseButton.LeftButton
                and event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier
            ):
                self.drawing = True
                self.start = self.img_view.mapToScene(event.position().toPoint())
                self.temp_rect = RectItem(QtCore.QRectF(self.start, self.start))
                self.scene.addItem(self.temp_rect)
                self.img_view.setDragMode(QtWidgets.QGraphicsView.DragMode.NoDrag)
                return True
            else:
                self.img_view.setDragMode(
                    QtWidgets.QGraphicsView.DragMode.ScrollHandDrag
                )
                self.drawing = False
                self.temp_rect = None
        elif event.type() == QtCore.QEvent.Type.MouseMove:
            if self.drawing and self.temp_rect:
                end = self.img_view.mapToScene(event.position().toPoint())
                rect = QtCore.QRectF(self.start, end).normalized()
                self.temp_rect.setRect(rect)
                return True
        elif event.type() == QtCore.QEvent.Type.MouseButtonRelease:
            if self.drawing and self.temp_rect:
                end = self.img_view.mapToScene(event.position().toPoint())
                rect = QtCore.QRectF(self.start, end).normalized()
                if rect.width() > 10 and rect.height() > 10:
                    self.cur_image.rects.append(rect)
                self.scene.removeItem(self.temp_rect)
                self.temp_rect = None
                self.drawing = False
                self.img_view.setDragMode(
                    QtWidgets.QGraphicsView.DragMode.ScrollHandDrag
                )
                # 先保存当前缩放和中心
                self.cur_image.transform = self.img_view.transform()
                self.cur_image.center = self.img_view.mapToScene(
                    self.img_view.viewport().rect().center()
                )
                self.display_image()
                return True
        return super().eventFilter(object, event)

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        # Ctrl+Z 撤销上一步框选
        if (
            event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier
            and event.key() == QtCore.Qt.Key.Key_Z
        ):
            if self.cur_image.rects:
                self.cur_image.rects.pop()
                # 先保存当前缩放和中心
                self.cur_image.transform = self.img_view.transform()
                self.cur_image.center = self.img_view.mapToScene(
                    self.img_view.viewport().rect().center()
                )
                self.display_image()
        else:
            super().keyPressEvent(event)


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    win = ImageSplitterApp()
    win.show()
    sys.exit(app.exec())
