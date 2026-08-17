# %% [KHAI BÁO THƯ VIỆN]
import cv2
import numpy as np
import matplotlib.pyplot as plt
import os

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
    c = 255.0 / np.log(256.0)
    lut = np.array([c * np.log1p(i) for i in range(256)])
    lut = np.clip(lut, 0, 255).astype(np.uint8)
    return cv2.LUT(image, lut)

# %% [HÀM BIẾN ĐỔI GAMMA]
def apply_gamma_transform(image, gamma):
    """Thực hiện biến đổi Gamma (Power-Law): s = 255 * (r/255)^gamma"""
    if image is None or not isinstance(image, np.ndarray):
        raise ValueError("Input image must be a valid numpy array")
    if gamma <= 0:
        raise ValueError(f"Gamma must be positive, got {gamma}")
    lut = np.array([255.0 * ((i / 255.0) ** gamma) for i in range(256)])
    lut = np.clip(lut, 0, 255).astype(np.uint8)
    return cv2.LUT(image, lut)

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
