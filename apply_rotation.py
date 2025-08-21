import os

from PIL import Image

from src.image_state import ImageState

from .main import RAW_DIR


def apply_rotation(states_path="image_states.txt", img_dir=RAW_DIR):
    # 加载所有图片状态
    images = [
        ImageState(os.path.join(img_dir, f))
        for f in sorted(os.listdir(img_dir))
        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))
    ]
    # 读取状态文件
    ImageState.load_all(images, states_path)
    # 旋转图片并清除angle
    for img_state in images:
        if img_state.angle % 360 == 0:
            continue
        img_path = img_state.path
        if not os.path.exists(img_path):
            print(f"未找到图片: {img_path}")
            continue
        img = Image.open(img_path)
        img = img.rotate(-img_state.angle, expand=True)
        img.save(img_path)
        print(f"{os.path.basename(img_path)} 已旋转 {img_state.angle} 度并覆盖原图")
        img_state.angle = 0  # 清除angle
    # 保存回文件
    ImageState.save_all(images, states_path)
    print("所有旋转已应用，angle 已清除。")


if __name__ == "__main__":
    apply_rotation()
