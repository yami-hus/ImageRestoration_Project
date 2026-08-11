"""
filters.py
- I/O ảnh (đọc/lưu/liệt kê) — dựa trên Lab01 Phần A
- Brightness/Contrast — dựa trên Lab01 Bài 19-20 (công thức g = alpha*f + beta)
- Batch Processing — 1 trong 4 kỹ thuật bắt buộc của đề (Chủ đề 2 - Project 1)
- Các kỹ thuật phục hồi ảnh cũ: denoise, sharpen, histogram equalization, CLAHE
"""

import os
import cv2
import numpy as np


# ---------------------------------------------------------------------------
# I/O ảnh — Lab01 Phần A (Bài 1-3)
# ---------------------------------------------------------------------------

def read_image(path):
    """Đọc 1 ảnh. Luôn kiểm tra None vì imread không raise lỗi khi đọc thất bại (Lab01 Bài 1)."""
    img = cv2.imread(path)
    if img is None:
        print(f"[LỖI] Không đọc được ảnh: {path}")
    return img


def save_image(img, path):
    """Lưu ảnh, tự tạo thư mục nếu chưa có."""
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    cv2.imwrite(path, img)


def list_images(folder, exts=(".jpg", ".jpeg", ".png", ".bmp")):
    """Liệt kê toàn bộ file ảnh trong 1 thư mục."""
    return [
        os.path.join(folder, f)
        for f in sorted(os.listdir(folder))
        if f.lower().endswith(exts)
    ]


# ---------------------------------------------------------------------------
# Brightness / Contrast — Lab01 Bài 19-20
# g(x,y) = alpha * f(x,y) + beta, clip về [0,255] trước khi ép uint8 (Lab01 Bài 21: overflow)
# ---------------------------------------------------------------------------

def adjust_brightness_contrast(img, alpha=1.0, beta=0):
    """alpha: hệ số tương phản (contrast). beta: độ dịch sáng (brightness)."""
    result = img.astype(np.float32) * alpha + beta
    result = np.clip(result, 0, 255)
    return result.astype(np.uint8)


# ---------------------------------------------------------------------------
# Các kỹ thuật phục hồi ảnh cũ (đề bài yêu cầu: tham số chỉnh được, hiện trước/sau)
# ---------------------------------------------------------------------------

def restore_denoise(img, strength=8):
    """Khử nhiễu hạt / nhiễu do ảnh cũ xuống cấp theo thời gian."""
    return cv2.fastNlMeansDenoisingColored(img, None, strength, strength, 7, 21)


def restore_sharpen(img, amount=0.3):
    """Tăng độ nét bằng unsharp masking."""
    blurred = cv2.GaussianBlur(img, (0, 0), sigmaX=3)
    return cv2.addWeighted(img, 1 + amount, blurred, -amount, 0)


def restore_histogram_eq(img):
    """Cân bằng histogram toàn ảnh trên kênh độ sáng (YCrCb)."""
    ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
    ycrcb[:, :, 0] = cv2.equalizeHist(ycrcb[:, :, 0])
    return cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)


def restore_clahe(img, clip_limit=2.0, tile_size=8):
    """CLAHE - cân bằng tương phản cục bộ, tự nhiên hơn histogram eq thường."""
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_size, tile_size))
    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def restore_pipeline(img, denoise_strength=8, sharpen_amount=0.3, use_clahe=True):
    """
    Pipeline kết hợp: denoise -> tăng tương phản -> sharpen.
    QUAN TRỌNG: phải denoise trước rồi mới tăng tương phản — nếu làm ngược lại,
    CLAHE/Histogram Eq sẽ khuếch đại nhiễu thay vì làm ảnh đẹp hơn.
    Tham số mặc định được chọn qua thử nghiệm (denoise=8, sharpen=0.3, clahe=True).
    """
    out = restore_denoise(img, strength=denoise_strength)
    out = restore_clahe(out) if use_clahe else restore_histogram_eq(out)
    out = restore_sharpen(out, amount=sharpen_amount)
    return out


# ---------------------------------------------------------------------------
# Batch Processing — kỹ thuật bắt buộc #1 của đề bài
# ---------------------------------------------------------------------------

def batch_process(input_folder, output_folder, process_fn, **params):
    """
    Áp dụng process_fn lên toàn bộ ảnh trong input_folder, lưu vào output_folder.
    Ví dụ: batch_process("data/raw", "data/results", restore_pipeline, denoise_strength=8)
    """
    results = []
    for path in list_images(input_folder):
        img = read_image(path)
        if img is None:
            continue

        processed = process_fn(img, **params)

        out_path = os.path.join(output_folder, os.path.basename(path))
        save_image(processed, out_path)
        results.append({"input": path, "output": out_path})

    print(f"[OK] Đã xử lý {len(results)} ảnh -> {output_folder}")
    return results
