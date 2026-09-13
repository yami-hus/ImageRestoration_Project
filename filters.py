# %% [KHAI BÁO THƯ VIỆN]
import cv2
import numpy as np
import os
from functools import lru_cache


_LOG_LUT = np.clip(
    255.0 / np.log(256.0) * np.log1p(np.arange(256, dtype=np.float32)),
    0,
    255,
).astype(np.uint8)


@lru_cache(maxsize=32)
def _gamma_lut(gamma):
    values = 255.0 * (np.arange(256, dtype=np.float32) / 255.0) ** gamma
    return np.clip(values, 0, 255).astype(np.uint8)

# %% [HÀM ĐẢO ẢNH (NEGATIVE)]
def apply_negative(image):
    """Thực hiện phép đảo ảnh: s = 255 - r"""
    if image is None or not isinstance(image, np.ndarray):
        raise ValueError("Input image must be a valid numpy array")
    return 255 - image

# %% [HÀM BIẾN ĐỔI LOGARIT]
def apply_log_transform(image):
    """Thực hiện biến đổi Logarit: s = c * log(1 + r)"""
    if image is None or not isinstance(image, np.ndarray):
        raise ValueError("Input image must be a valid numpy array")
    return cv2.LUT(image, _LOG_LUT)

# %% [HÀM BIẾN ĐỔI GAMMA]
def apply_gamma_transform(image, gamma):
    """Thực hiện biến đổi Gamma (Power-Law): s = 255 * (r/255)^gamma"""
    if image is None or not isinstance(image, np.ndarray):
        raise ValueError("Input image must be a valid numpy array")
    if gamma <= 0:
        raise ValueError(f"Gamma must be positive, got {gamma}")
    return cv2.LUT(image, _gamma_lut(float(gamma)))

# %% [HÀM CẮT MẶT PHẲNG BIT]
def apply_bit_plane_slicing(image, bit):
    """Thực hiện cắt mặt phẳng bit từ 0 đến 7"""
    if image is None or not isinstance(image, np.ndarray):
        raise ValueError("Input image must be a valid numpy array")
    if not isinstance(bit, int) or bit < 0 or bit > 7:
        raise ValueError(f"Bit must be an integer between 0 and 7, got {bit}")
    
    is_color = len(image.shape) == 3
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if is_color else image
    bit_plane = (gray_image >> bit) & 1
    bit_plane_vis = (bit_plane * 255).astype(np.uint8)
    
    return cv2.cvtColor(bit_plane_vis, cv2.COLOR_GRAY2BGR) if is_color else bit_plane_vis

# %% [XỬ LÝ HÀNG LOẠT (BATCH PROCESSING)]
def process_batch_images(input_dir, output_dir, filter_name, **kwargs):
    """Xử lý hàng loạt toàn bộ ảnh trong thư mục"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    valid_extensions = ('.png', '.jpg', '.jpeg', '.bmp')
    success_count = 0
    for filename in os.listdir(input_dir):
        if filename.lower().endswith(valid_extensions):
            try:
                img_path = os.path.join(input_dir, filename)
                img = cv2.imread(img_path)
                if img is None: 
                    continue
                
                if filter_name == 'negative': 
                    processed_img = apply_negative(img)
                elif filter_name == 'log': 
                    processed_img = apply_log_transform(img)
                elif filter_name == 'gamma': 
                    processed_img = apply_gamma_transform(img, gamma=kwargs.get('gamma', 1.0))
                elif filter_name == 'bitplane': 
                    processed_img = apply_bit_plane_slicing(img, bit=kwargs.get('bit', 7))
                else: 
                    processed_img = img
                
                cv2.imwrite(os.path.join(output_dir, f"processed_{filename}"), processed_img)
                success_count += 1
            except Exception as e:
                print(f"Lỗi {filename}: {e}")
    return success_count

# %% [XỬ LÝ VIDEO GENERATOR]
def process_video_generator(video_path, filter_name, **kwargs):
    """Generator đọc và xử lý Video theo từng frame"""
    if not video_path or not isinstance(video_path, str):
        raise ValueError("Đường dẫn video không hợp lệ")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Không thể mở video: {video_path}")
    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: 
                break
            try:
                if filter_name == 'negative': 
                    processed_frame = apply_negative(frame)
                elif filter_name == 'log': 
                    processed_frame = apply_log_transform(frame)
                elif filter_name == 'gamma': 
                    processed_frame = apply_gamma_transform(frame, gamma=kwargs.get('gamma', 1.0))
                elif filter_name == 'bitplane': 
                    processed_frame = apply_bit_plane_slicing(frame, bit=kwargs.get('bit', 7))
                else: 
                    processed_frame = frame
                yield processed_frame
            except Exception:
                yield frame
    finally:
        cap.release()


def save_processed_video(input_video_path, output_video_path, filter_name, **kwargs):
    """Xử lý video và lưu kết quả ra file video mới."""
    if not input_video_path or not isinstance(input_video_path, str):
        raise ValueError("Đường dẫn video đầu vào không hợp lệ")
    if not output_video_path or not isinstance(output_video_path, str):
        raise ValueError("Đường dẫn video đầu ra không hợp lệ")

    os.makedirs(os.path.dirname(output_video_path) or ".", exist_ok=True)

    cap = cv2.VideoCapture(input_video_path)
    if not cap.isOpened():
        raise ValueError(f"Không thể mở video: {input_video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 25.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    if width <= 0 or height <= 0:
        raise ValueError(f"Kích thước video không hợp lệ: {input_video_path}")

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))
    if not writer.isOpened():
        cap.release()
        raise ValueError(f"Không thể tạo video đầu ra: {output_video_path}")

    try:
        for processed_frame in process_video_generator(input_video_path, filter_name, **kwargs):
            writer.write(processed_frame)
        return output_video_path
    finally:
        writer.release()
        cap.release()


if __name__ == "__main__":
    import matplotlib.pyplot as plt

    current_dir = os.path.dirname(os.path.abspath(__file__))
    dataset_path = os.path.join(current_dir, "dataset", "z8059496394582_d29a8d50b68f0dca7d51e2edef948211.jpg")
    img_test = cv2.imread(dataset_path)

    if img_test is None:
        raise FileNotFoundError(f"Khong tim thay anh test tai {dataset_path}")

    img_rgb = cv2.cvtColor(img_test, cv2.COLOR_BGR2RGB)
    print("Da nap anh test thanh cong, san sang kiem thu tung ham!")

    test_images = [
        ("Dao anh (Negative)", apply_negative(img_test)),
        ("Bien doi Logarit", apply_log_transform(img_test)),
        ("Bien doi Gamma 0.5", apply_gamma_transform(img_test, gamma=0.5)),
        ("Bit-Plane Slicing (Bit 7)", apply_bit_plane_slicing(img_test, bit=7)),
    ]
    for title, result in test_images:
        plt.figure(figsize=(8, 4))
        plt.subplot(1, 2, 1)
        plt.title("Anh goc")
        plt.imshow(img_rgb)
        plt.axis("off")
        plt.subplot(1, 2, 2)
        plt.title(title)
        plt.imshow(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
        plt.axis("off")
        plt.show()














