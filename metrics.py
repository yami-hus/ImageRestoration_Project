"""
metrics.py
- PSNR — kỹ thuật bắt buộc #2 của đề bài
- SSIM — kỹ thuật bắt buộc #3 của đề bài
- So sánh các phương pháp — kỹ thuật bắt buộc #4 của đề bài
"""

import cv2
from skimage.metrics import structural_similarity as ssim


def compute_psnr(reference, processed):
    """
    PSNR (dB) — càng cao càng ít khác biệt so với ảnh reference.
    reference: ảnh gốc "sạch" nếu có, hoặc chính ảnh cũ đầu vào nếu không có ảnh gốc
    (xem báo cáo phần giải thích cách đọc PSNR/SSIM khi không có ground truth).
    """
    return cv2.PSNR(reference, processed)


def compute_ssim(reference, processed):
    """SSIM (0-1) — đo độ giống nhau về CẤU TRÚC (khác PSNR chỉ đo sai khác pixel)."""
    gray1 = cv2.cvtColor(reference, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
    score, _ = ssim(gray1, gray2, full=True)
    return score


def compare_methods(reference, methods: dict):
    """
    So sánh nhiều phương pháp phục hồi trên cùng 1 ảnh.
    methods: dict {"ten_phuong_phap": anh_da_xu_ly}
    Trả về list dict đã sắp xếp theo SSIM giảm dần, dùng để in bảng trong GUI/báo cáo.

    Ví dụ:
        results = compare_methods(img, {
            "denoise": restore_denoise(img),
            "clahe": restore_clahe(img),
            "pipeline": restore_pipeline(img),
        })
    """
    rows = []
    for name, processed in methods.items():
        rows.append({
            "method": name,
            "psnr": compute_psnr(reference, processed),
            "ssim": compute_ssim(reference, processed),
        })
    return sorted(rows, key=lambda r: r["ssim"], reverse=True)
