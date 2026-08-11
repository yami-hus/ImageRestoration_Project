

import io
import os
import zipfile

import streamlit as st
import cv2
import numpy as np

from filters import (
    restore_denoise, restore_sharpen, restore_clahe, restore_histogram_eq,
    restore_pipeline, adjust_brightness_contrast,
)
from metrics import compute_psnr, compute_ssim, compare_methods

st.set_page_config(page_title="Ứng dụng khôi phục ảnh cũ", layout="wide")
st.title("Ứng dụng khôi phục ảnh cũ")
st.caption("Chủ đề 2 - Project 1: Batch Processing, PSNR, SSIM, So sánh các phương pháp")

DEFAULT_DENOISE = 8
DEFAULT_SHARPEN = 0.3

tab_single, tab_batch = st.tabs(["Ảnh đơn", "Batch Processing"])

# ---------------------------------------------------------------------------
# TAB 1: 1 ảnh — chỉnh tham số, xem trước/sau, bảng so sánh phương pháp
# ---------------------------------------------------------------------------
with tab_single:
    uploaded = st.file_uploader("Mở ảnh cũ", type=["jpg", "jpeg", "png", "bmp"], key="single")

    if uploaded is not None:
        file_bytes = np.asarray(bytearray(uploaded.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        st.sidebar.header("Tham số (ảnh đơn)")
        denoise_strength = st.sidebar.slider("Denoise strength", 0, 30, DEFAULT_DENOISE)
        sharpen_amount = st.sidebar.slider("Sharpen amount", 0.0, 2.0, DEFAULT_SHARPEN)
        use_clahe = st.sidebar.checkbox("Dùng CLAHE (thay vì Histogram Eq)", value=True)
        beta = st.sidebar.slider("Brightness (beta)", -80, 80, 0)
        alpha = st.sidebar.slider("Contrast (alpha)", 0.5, 2.0, 1.0)

        processed = restore_pipeline(
            img, denoise_strength=denoise_strength,
            sharpen_amount=sharpen_amount, use_clahe=use_clahe,
        )
        if alpha != 1.0 or beta != 0:
            processed = adjust_brightness_contrast(processed, alpha=alpha, beta=beta)

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Trước")
            st.image(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        with col2:
            st.subheader("Sau")
            st.image(cv2.cvtColor(processed, cv2.COLOR_BGR2RGB))

        st.subheader("So sánh các phương pháp")
        methods = {
            "denoise": restore_denoise(img, strength=denoise_strength),
            "clahe": restore_clahe(img),
            "histogram_eq": restore_histogram_eq(img),
            "sharpen": restore_sharpen(img, amount=sharpen_amount),
            "pipeline (kết hợp)": processed,
        }
        st.table(compare_methods(img, methods))

        buf = cv2.imencode(".jpg", processed)[1].tobytes()
        st.download_button("Lưu ảnh kết quả", buf, file_name="restored.jpg", mime="image/jpeg")
    else:
        st.info("Mở 1 ảnh để bắt đầu.")

# ---------------------------------------------------------------------------
# TAB 2: Batch Processing — kỹ thuật bắt buộc #1
# ---------------------------------------------------------------------------
with tab_batch:
    st.write("Mở nhiều ảnh cùng lúc, áp dụng cùng tham số, tải kết quả về dạng .zip.")

    uploaded_batch = st.file_uploader(
        "Mở nhiều ảnh cũ", type=["jpg", "jpeg", "png", "bmp"],
        accept_multiple_files=True, key="batch",
    )

    st.sidebar.header("Tham số (batch)")
    b_denoise = st.sidebar.slider("Denoise strength (batch)", 0, 30, DEFAULT_DENOISE, key="b_denoise")
    b_sharpen = st.sidebar.slider("Sharpen amount (batch)", 0.0, 2.0, DEFAULT_SHARPEN, key="b_sharpen")
    b_clahe = st.sidebar.checkbox("Dùng CLAHE (batch)", value=True, key="b_clahe")

    if uploaded_batch:
        st.write(f"Đã chọn {len(uploaded_batch)} ảnh.")
        if st.button("Xử lý hàng loạt"):
            zip_buffer = io.BytesIO()
            progress = st.progress(0)
            preview_cols = st.columns(4)

            with zipfile.ZipFile(zip_buffer, "w") as zf:
                for i, file in enumerate(uploaded_batch):
                    file_bytes = np.asarray(bytearray(file.read()), dtype=np.uint8)
                    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                    processed = restore_pipeline(
                        img, denoise_strength=b_denoise,
                        sharpen_amount=b_sharpen, use_clahe=b_clahe,
                    )
                    out_bytes = cv2.imencode(".jpg", processed)[1].tobytes()
                    zf.writestr(f"restored_{file.name}", out_bytes)

                    if i < 4:
                        with preview_cols[i]:
                            st.image(cv2.cvtColor(processed, cv2.COLOR_BGR2RGB), caption=file.name)

                    progress.progress((i + 1) / len(uploaded_batch))

            st.success(f"Đã xử lý xong {len(uploaded_batch)} ảnh.")
            st.download_button(
                "Tải toàn bộ kết quả (.zip)", zip_buffer.getvalue(),
                file_name="restored_batch.zip", mime="application/zip",
            )
    else:
        st.info("Chưa chọn ảnh nào.")
