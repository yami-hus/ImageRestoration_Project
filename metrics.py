# %% [KHAI BÁO THƯ VIỆN]
import numpy as np
from skimage.metrics import peak_signal_noise_ratio, structural_similarity

# %% [HÀM TÍNH PSNR]
def calc_psnr(original, processed):
    """Tính chỉ số PSNR (Peak Signal-to-Noise Ratio) giữa ảnh gốc và ảnh đã xử lý"""
    if original is None or processed is None:
        raise ValueError("Ảnh đầu vào không hợp lệ")
    if original.shape != processed.shape:
        raise ValueError("Hai ảnh phải cùng kích thước để so sánh")

    return float(peak_signal_noise_ratio(original, processed, data_range=255))

# %% [HÀM TÍNH SSIM]
def calc_ssim(original, processed):
    """Tính chỉ số SSIM (Structural Similarity Index) giữa ảnh gốc và ảnh đã xử lý"""
    if original is None or processed is None:
        raise ValueError("Ảnh đầu vào không hợp lệ")
    if original.shape != processed.shape:
        raise ValueError("Hai ảnh phải cùng kích thước để so sánh")

    is_color = len(original.shape) == 3
    score = structural_similarity(
        original, processed,
        channel_axis=2 if is_color else None,
        data_range=255
    )
    return float(score)