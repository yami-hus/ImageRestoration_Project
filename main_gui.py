import sys
import os
import threading

import cv2

from PySide6.QtCore import Qt, QObject, Signal, QTimer
from PySide6.QtGui import QImage, QPixmap, QPainter
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QTabWidget, QPushButton, QLabel, QComboBox, QSlider, QScrollArea,
    QFileDialog, QMessageBox, QFrame, QStackedWidget, QSizePolicy
)

import filters
import metrics

class ImageLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = QPixmap()
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setObjectName("imgLabel")
        self.setText("Chưa có ảnh")
        self.setStyleSheet(
            "QLabel#imgLabel { background-color: #0F172A; border: 1px solid #2D3A4F;"
            " border-radius: 8px; color: #475569; }"
        )

    def set_cv_image(self, img):
        if img is None:
            self._pixmap = QPixmap()
            self.setText("Chưa có ảnh")
        else:
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            qimg = QImage(rgb.data, w, h, rgb.strides[0], QImage.Format_RGB888)
            self._pixmap = QPixmap.fromImage(qimg.copy())
            self.setText("") # Xóa chữ khi có ảnh
        
        # Gọi lệnh vẽ lại giao diện thay vì resize
        self.update() 

    def paintEvent(self, event):
        super().paintEvent(event)
        
        if not self._pixmap.isNull():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            
            rect = self.contentsRect()
            
            scaled_pixmap = self._pixmap.scaled(
                rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            
            x = rect.x() + (rect.width() - scaled_pixmap.width()) // 2
            y = rect.y() + (rect.height() - scaled_pixmap.height()) // 2
            
            painter.drawPixmap(x, y, scaled_pixmap)
            painter.end()


class ThreadDone(QObject):
    finished = Signal(str, object)


class ImageApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ứng Dụng Khôi Phục Ảnh Cũ")
        self.resize(1350, 850)

        self._apply_theme()

        self.t1_orig_cv = None
        self.t1_clean_cv = None
        self.t1_proc_cv = None

        self.t2_paths = []
        self.t2_video_path = None
        self.t2_vid_cap = None
        self.t2_vid_timer = QTimer(self)
        self.t2_vid_timer.timeout.connect(self._t2_video_step)

        self.t3_clean_cv = None
        self.t3_dam_cv = None

        # Timer chống giật lag khi kéo chuột
        self.t1_debounce_timer = QTimer(self)
        self.t1_debounce_timer.setSingleShot(True)
        self.t1_debounce_timer.timeout.connect(self._t1_apply_heavy)

        self.t2_debounce_timer = QTimer(self)
        self.t2_debounce_timer.setSingleShot(True)
        self.t2_debounce_timer.timeout.connect(self._t2_apply_preview_heavy)

        self.t3_gam_timer = QTimer(self)
        self.t3_gam_timer.setSingleShot(True)
        self.t3_gam_timer.timeout.connect(self._t3_run_gamma_heavy)

        self.t3_bit_timer = QTimer(self)
        self.t3_bit_timer.setSingleShot(True)
        self.t3_bit_timer.timeout.connect(self._t3_run_bit_heavy)

        self._build_ui()

    def _apply_theme(self):
        self.setStyleSheet("""
            QMainWindow, QWidget { background-color: #0B0F19; color: #E2E8F0;
                font-family: 'Segoe UI'; font-size: 13px; }
            QFrame#card { background-color: #1E293B; border: 1px solid #2D3A4F;
                border-radius: 12px; }
            QFrame#imgFrame { background-color: #1E293B; border: 1px solid #2D3A4F;
                border-radius: 12px; }
            QLabel { background: transparent; }
            QLabel#title { color: #94A3B8; font-weight: bold; font-size: 14px; }
            QLabel#metric { color: #38BDF8; font-weight: bold; font-size: 15px; }
            QLabel#boxTitle { color: #94A3B8; font-weight: bold; font-size: 14px; }
            
            QComboBox { 
                background-color: #0F172A; border: 1px solid #38BDF8;
                border-radius: 6px; padding: 8px 12px; min-height: 20px; font-weight: bold;
            }
            QComboBox::drop-down {
                border: none; width: 30px;
            }
            QComboBox::down-arrow {
                image: none; 
            }
            QComboBox QAbstractItemView { 
                background-color: #0F172A; color: #E2E8F0;
                border: 1px solid #38BDF8; border-radius: 4px;
                selection-background-color: #2563EB; selection-color: white;
                outline: 0px; 
            }
            QComboBox QAbstractItemView::item {
                min-height: 35px; 
                padding: 5px;
            }
            
            QSlider::groove:horizontal { height: 6px; background: #334155;
                border-radius: 3px; }
            QSlider::handle:horizontal { width: 16px; background: #38BDF8;
                margin: -5px 0; border-radius: 8px; }
                
            QScrollArea { border: none; background: transparent; }
            QScrollArea#t2Scroll { border: 1px solid #38BDF8; border-radius: 8px; background-color: #0F172A; }
            QScrollBar:vertical { 
                background: transparent; width: 12px; margin: 0px 0px 0px 4px; 
            }
            QScrollBar::handle:vertical { 
                background: #475569; border-radius: 4px; min-height: 40px; 
            }
            QScrollBar::handle:vertical:hover { background: #64748B; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { 
                height: 0px; background: transparent;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { 
                background: transparent; 
            }
            
            QTabWidget::pane { border: 1px solid #2D3A4F; border-radius: 12px;
                background: #0B0F19; }
            QTabBar::tab { background: #1E293B; color: #94A3B8;
                padding: 10px 18px; border-top-left-radius: 8px;
                border-top-right-radius: 8px; margin-right: 4px; font-weight: bold; }
            QTabBar::tab:selected { background: #2563EB; color: white; }
        """)

    def _set_button_style(self, btn, color1, color2):
        btn.setStyleSheet(
            f"QPushButton {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 {color1}, stop:1 {color2}); color: white; font-weight: bold;"
            f" border: none; border-radius: 8px; padding: 8px 14px; }}"
            f"QPushButton:hover {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 {color1}, stop:1 {color1}); }}"
            f"QPushButton:disabled {{ background: #334155; color: #94A3B8; }}"
        )

    def make_button(self, text, color1="#00c6ff", color2="#0072ff"):
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setMinimumHeight(42)
        self._set_button_style(btn, color1, color2)
        return btn

    def make_card(self, title=None):
        frame = QFrame()
        frame.setObjectName("card")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        if title:
            layout.addWidget(self._title_label(title))
        return frame, layout

    def _title_label(self, text):
        lbl = QLabel(text)
        lbl.setObjectName("title")
        return lbl

    def _metric_label(self):
        lbl = QLabel("PSNR: -- | SSIM: --")
        lbl.setObjectName("metric")
        return lbl

    def make_box(self, title, fixed_h=None, min_h=None):
        frame = QFrame()
        frame.setObjectName("imgFrame")
        if fixed_h:
            frame.setFixedHeight(fixed_h)
        if min_h:
            frame.setMinimumHeight(min_h)
            
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        header = QLabel(title)
        header.setObjectName("boxTitle")
        
        img = ImageLabel()
        
        layout.addWidget(header)
        layout.addWidget(img, 1)
        return frame, layout, img

    def _make_slider_row(self, name, lo, hi, val, on_change, fmt, integer=False):
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel("")
        lbl.setObjectName("metric")
        row.addWidget(lbl)

        slider = QSlider(Qt.Horizontal)
        if integer:
            slider.setMinimum(int(lo))
            slider.setMaximum(int(hi))
            slider.setValue(int(val))
            slider.setSingleStep(1)
            slider.setPageStep(1)
            slider.setTickPosition(QSlider.TicksBelow)
            slider.setTickInterval(1)
        else:
            slider.setMinimum(int(lo * 100))
            slider.setMaximum(int(hi * 100))
            slider.setValue(int(val * 100))
        
        slider.setToolTip(name)

        def update_label(*_):
            if integer:
                v = slider.value()
                lbl.setText(fmt.format(v))
            else:
                v = slider.value() / 100.0
                lbl.setText(fmt.format(v))

        update_label()
        slider.valueChanged.connect(update_label)
        slider.valueChanged.connect(on_change)
        row.addWidget(slider, 1)
        return container, lbl, slider

    def _build_ui(self):
        tabs = QTabWidget()
        tabs.addTab(self._build_tab1(), "PSNR & SSIM (Đơn Ảnh)")
        tabs.addTab(self._build_tab2(), "Batch Processing & Video")
        tabs.addTab(self._build_tab3(), "So sánh phương pháp")
        self.setCentralWidget(tabs)

    # ---------- TAB 1 ----------
    def _build_tab1(self):
        root = QWidget()
        layout = QHBoxLayout(root)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        ctrl_frame, ctrl_lay = self.make_card("THÔNG SỐ BỘ LỌC")

        btn_open_orig = self.make_button("Nạp Ảnh Cần Xử Lý", "#00c6ff", "#0072ff")
        btn_open_orig.clicked.connect(self._t1_open_orig)
        ctrl_lay.addWidget(btn_open_orig)

        btn_open_clean = self.make_button("Nạp Ảnh Chuẩn (Clean)", "#10B981", "#059669")
        btn_open_clean.clicked.connect(self._t1_open_clean)
        ctrl_lay.addWidget(btn_open_clean)

        btn_save = self.make_button("Lưu Kết Quả", "#F59E0B", "#D97706")
        btn_save.clicked.connect(self._t1_save)
        ctrl_lay.addWidget(btn_save)

        ctrl_lay.addSpacing(10)
        ctrl_lay.addWidget(self._title_label("Thay đổi tham số bộ lọc"))

        self.t1_filter_cb = QComboBox()
        self.t1_filter_cb.setMaxVisibleItems(10) 
        self.t1_filter_cb.addItem("Negative (Đảo ảnh)", "negative")
        self.t1_filter_cb.addItem("Log Transform", "log")
        self.t1_filter_cb.addItem("Gamma Transform", "gamma")
        self.t1_filter_cb.addItem("Bitplane Slicing", "bitplane")
        self.t1_filter_cb.currentIndexChanged.connect(self._t1_filter_changed)
        ctrl_lay.addWidget(self.t1_filter_cb)

        self.t1_gamma_row, self.t1_gamma_lbl, self.t1_gamma_slider = self._make_slider_row(
            "Gamma", 0.1, 5.0, 1.0, self._t1_apply, "Gamma: {:.2f}")
        ctrl_lay.addWidget(self.t1_gamma_row)
        self.t1_gamma_row.setVisible(False)

        self.t1_bit_row, self.t1_bit_lbl, self.t1_bit_slider = self._make_slider_row(
            "Bit", 0, 7, 7, self._t1_apply, "Bit: {}", integer=True)
        ctrl_lay.addWidget(self.t1_bit_row)
        self.t1_bit_row.setVisible(False)

        self.t1_metric_frame = QFrame()
        self.t1_metric_frame.setObjectName("card")
        mlay = QVBoxLayout(self.t1_metric_frame)
        mlay.setContentsMargins(14, 14, 14, 14)
        mlay.addWidget(self._title_label("Đánh Giá Kết Quả"))
        self.t1_psnr_lbl = QLabel("PSNR: --")
        self.t1_psnr_lbl.setObjectName("metric")
        self.t1_ssim_lbl = QLabel("SSIM: --")
        self.t1_ssim_lbl.setObjectName("metric")
        mlay.addWidget(self.t1_psnr_lbl)
        mlay.addWidget(self.t1_ssim_lbl)
        
        self.t1_metric_frame.setVisible(False) 

        ctrl_lay.addStretch(1)

        orig_frame, _, self.t1_img_orig = self.make_box("Ảnh Trước (Hỏng)", min_h=300)
        proc_frame, _, self.t1_img_proc = self.make_box("Ảnh Sau (Đã xử lý)", min_h=300)

        imgs_row = QHBoxLayout()
        imgs_row.setSpacing(16)
        imgs_row.addWidget(orig_frame, 1)
        imgs_row.addWidget(proc_frame, 1)

        ctrl_panel = QWidget()
        ctrl_panel.setFixedWidth(320)
        cl = QVBoxLayout(ctrl_panel)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.addWidget(ctrl_frame)
        cl.addWidget(self.t1_metric_frame)

        layout.addWidget(ctrl_panel)
        imgs_widget = QWidget()
        iw_lay = QVBoxLayout(imgs_widget)
        iw_lay.setContentsMargins(0, 0, 0, 0)
        iw_lay.addLayout(imgs_row)
        layout.addWidget(imgs_widget, 1)

        return root

    # ---------- TAB 2 ----------
    def _build_tab2(self):
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        btns = QHBoxLayout()
        btn_batch = self.make_button("Nạp Batch Ảnh", "#00c6ff", "#0072ff")
        btn_batch.clicked.connect(self._t2_open_batch)
        btn_batch.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.btn_t2_video = self.make_button("Nạp Video", "#8B5CF6", "#6D28D9")
        self.btn_t2_video.clicked.connect(self._t2_toggle_video)
        self.btn_t2_video.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        btn_save = self.make_button("Lưu Ảnh/Video", "#F59E0B", "#D97706")
        btn_save.clicked.connect(self._t2_save)
        btn_save.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        btns.addWidget(btn_batch)
        btns.addWidget(self.btn_t2_video)
        btns.addWidget(btn_save)
        layout.addLayout(btns)

        filt_row = QHBoxLayout()
        filt_row.addWidget(self._title_label("Bộ lọc:"))
        self.t2_filter_cb = QComboBox()
        self.t2_filter_cb.setMaxVisibleItems(10)
        for text, key in [("Negative (Đảo ảnh)", "negative"), ("Log Transform", "log"),
                          ("Gamma Transform", "gamma"), ("Bitplane Slicing", "bitplane")]:
            self.t2_filter_cb.addItem(text, key)
        self.t2_filter_cb.currentIndexChanged.connect(self._t2_filter_changed)
        filt_row.addWidget(self.t2_filter_cb)

        self.t2_gamma_row, self.t2_gamma_lbl, self.t2_gamma_slider = self._make_slider_row(
            "Gamma", 0.1, 5.0, 1.0, self._t2_apply_preview, "Gamma: {:.2f}")
        filt_row.addWidget(self.t2_gamma_row)
        self.t2_gamma_row.setVisible(False)

        self.t2_bit_row, self.t2_bit_lbl, self.t2_bit_slider = self._make_slider_row(
            "Bit", 0, 7, 7, self._t2_apply_preview, "Bit: {}", integer=True)
        filt_row.addWidget(self.t2_bit_row)
        self.t2_bit_row.setVisible(False)

        filt_row.addStretch(1)
        layout.addLayout(filt_row)

        self.t2_stack = QStackedWidget()

        scroll = QScrollArea()
        scroll.setObjectName("t2Scroll") 
        scroll.setWidgetResizable(True)
        self.t2_grid_container = QWidget()
        self.t2_grid_container.setStyleSheet("background-color: transparent;")
        self.t2_grid_lay = QVBoxLayout(self.t2_grid_container)
        self.t2_grid_lay.setContentsMargins(10, 10, 20, 10)
        self.t2_grid_lay.setSpacing(15)
        self.t2_grid_lay.addStretch(1)
        scroll.setWidget(self.t2_grid_container)

        self.t2_vid_label = ImageLabel()

        self.t2_stack.addWidget(scroll)
        self.t2_stack.addWidget(self.t2_vid_label)
        layout.addWidget(self.t2_stack, 1)

        return root

    # ---------- TAB 3 ----------
    def _build_tab3(self):
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        btns = QHBoxLayout()
        btn_clean = self.make_button("Tải Ảnh Chuẩn (Clean)", "#00c6ff", "#0072ff")
        btn_clean.clicked.connect(self._t3_open_clean)
        
        self.btn_t3_dam = self.make_button("Tải Ảnh Hỏng (Damaged)", "#EF4444", "#B91C1C")
        self.btn_t3_dam.clicked.connect(self._t3_open_dam)
        self.btn_t3_dam.setEnabled(False) 

        btns.addWidget(btn_clean)
        btns.addWidget(self.btn_t3_dam)
        btns.addStretch(1)
        layout.addLayout(btns)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        
        container_widget = QWidget()
        grid = QGridLayout(container_widget)
        grid.setSpacing(15)
        grid.setContentsMargins(5, 5, 20, 5) 

        f_clean, l_clean, self.t3_img_clean = self.make_box("Ảnh Chuẩn (Clean GT)", fixed_h=380)
        f_dam, l_dam, self.t3_img_dam = self.make_box("Ảnh Hỏng (Damaged)", fixed_h=380)
        f_neg, l_neg, self.t3_img_neg = self.make_box("Negative Transform", fixed_h=380)
        f_log, l_log, self.t3_img_log = self.make_box("Log Transform", fixed_h=380)
        f_gam, l_gam, self.t3_img_gam = self.make_box("Gamma Transform", fixed_h=380)
        f_bit, l_bit, self.t3_img_bit = self.make_box("Bitplane Slicing", fixed_h=380)

        self.t3_met_neg = self._metric_label()
        self.t3_met_log = self._metric_label()
        self.t3_met_gam = self._metric_label()
        self.t3_met_bit = self._metric_label()
        
        l_neg.addWidget(self.t3_met_neg)
        l_log.addWidget(self.t3_met_log)

        self.t3_gam_row, _, self.t3_gam_slider = self._make_slider_row(
            "Gamma", 0.1, 5.0, 2.0, self._t3_run_gamma, "Gamma: {:.2f}")
        l_gam.addWidget(self.t3_gam_row)
        l_gam.addWidget(self.t3_met_gam)

        self.t3_bit_row, _, self.t3_bit_slider = self._make_slider_row(
            "Bit", 0, 7, 7, self._t3_run_bit, "Bit: {}", integer=True)
        l_bit.addWidget(self.t3_bit_row)
        l_bit.addWidget(self.t3_met_bit)

        grid.addWidget(f_clean, 0, 0)
        grid.addWidget(f_dam, 0, 1)
        grid.addWidget(f_neg, 1, 0)
        grid.addWidget(f_log, 1, 1)
        grid.addWidget(f_gam, 2, 0)
        grid.addWidget(f_bit, 2, 1)

        scroll_area.setWidget(container_widget)
        layout.addWidget(scroll_area, 1)

        return root

    # ---------- LOGIC TAB 1 ----------
    def _t1_open_orig(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn ảnh cần xử lý", "", "Ảnh (*.png *.jpg *.jpeg)")
        if not path:
            return
        img = cv2.imread(path)
        if img is None:
            self._err("Không đọc được ảnh!")
            return
        self.t1_orig_cv = img
        self.t1_img_orig.set_cv_image(img)
        self._t1_apply_heavy()

    def _t1_open_clean(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn ảnh chuẩn (Clean)", "", "Ảnh (*.png *.jpg *.jpeg)")
        if not path:
            return
        img = cv2.imread(path)
        if img is None:
            self._err("Không đọc được ảnh Clean!")
            return
        self.t1_clean_cv = img
        self._info("Đã nạp ảnh Clean. Sẵn sàng tính PSNR/SSIM.")
        self._t1_apply_heavy()

    def _t1_save(self):
        if self.t1_proc_cv is None:
            self._err("Không có ảnh kết quả để lưu!")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Lưu ảnh kết quả", "ket_qua.png", "Ảnh (*.png *.jpg)")
        if not path:
            return
        cv2.imwrite(path, self.t1_proc_cv)
        self._info(f"Đã lưu kết quả: {path}")

    def _t1_filter_changed(self):
        key = self.t1_filter_cb.currentData()
        self.t1_gamma_row.setVisible(key == "gamma")
        self.t1_bit_row.setVisible(key == "bitplane")
        
        self.t1_metric_frame.setVisible(key in ("gamma", "bitplane"))
        
        self._t1_apply_heavy()

    def _t1_apply(self, *args):
        self.t1_debounce_timer.start(150)

    def _t1_apply_heavy(self):
        if self.t1_orig_cv is None:
            return
        key = self.t1_filter_cb.currentData()
        g = self.t1_gamma_slider.value() / 100.0
        b = int(self.t1_bit_slider.value()) 
        
        self.t1_proc_cv = self._apply_filter(self.t1_orig_cv, key, g, b)
        self.t1_img_proc.set_cv_image(self.t1_proc_cv)

        if self.t1_clean_cv is not None and key in ("gamma", "bitplane"):
            cln = cv2.resize(self.t1_clean_cv, self.t1_proc_cv.shape[:2][::-1])
            self.t1_psnr_lbl.setText(f"PSNR: {metrics.calc_psnr(cln, self.t1_proc_cv):.2f}")
            self.t1_ssim_lbl.setText(f"SSIM: {metrics.calc_ssim(cln, self.t1_proc_cv):.4f}")
        else:
            self.t1_psnr_lbl.setText("PSNR: --")
            self.t1_ssim_lbl.setText("SSIM: --")

    # ---------- LOGIC TAB 2 ----------
    def _apply_filter(self, img, key, gamma, bit):
        if key == "negative":
            return filters.apply_negative(img)
        if key == "log":
            return filters.apply_log_transform(img)
        if key == "gamma":
            return filters.apply_gamma_transform(img, gamma=gamma)
        if key == "bitplane":
            return filters.apply_bit_plane_slicing(img, bit=bit)
        return img.copy()

    def _t2_open_batch(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Chọn nhiều ảnh", "", "Ảnh (*.png *.jpg *.jpeg *.bmp)")
        if not paths:
            return
        self._t2_stop_video()
        self.t2_paths = paths
        self.t2_video_path = None
        self.t2_stack.setCurrentIndex(0)
        self._t2_build_grid_heavy()

    def _t2_build_grid_heavy(self):
        while self.t2_grid_lay.count() > 1:
            item = self.t2_grid_lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        key = self.t2_filter_cb.currentData()
        g = self.t2_gamma_slider.value() / 100.0
        b = int(self.t2_bit_slider.value())

        for path in self.t2_paths[:20]:
            img = cv2.imread(path)
            if img is None:
                continue
            proc = self._apply_filter(img, key, g, b)
            
            row = QWidget()
            row.setFixedHeight(340) 
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.setSpacing(16)

            for lbl_title, cv in (("Ảnh Gốc", img), ("Ảnh Xử Lý", proc)):
                frame = QFrame()
                frame.setObjectName("card")
                fl = QVBoxLayout(frame)
                fl.setContentsMargins(10, 8, 10, 8)
                fl.addWidget(self._title_label(lbl_title))
                
                lbl = ImageLabel()
                lbl.set_cv_image(cv)
                fl.addWidget(lbl)
                
                rl.addWidget(frame, 1)

            self.t2_grid_lay.insertWidget(self.t2_grid_lay.count() - 1, row)

    def _t2_toggle_video(self):
        if self.t2_vid_cap is not None:
            self._t2_stop_video()
        else:
            self._t2_open_video()

    def _t2_open_video(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn video", "", "Video (*.mp4 *.avi *.mov)")
        if not path:
            return
        self.t2_paths = []
        self.t2_video_path = path
        self.t2_stack.setCurrentIndex(1)
        self._t2_start_video()

    def _t2_start_video(self):
        self._t2_stop_video()
        self.t2_vid_cap = cv2.VideoCapture(self.t2_video_path)
        if not self.t2_vid_cap.isOpened():
            self._err("Không mở được video!")
            return
        self.t2_vid_timer.start(30)
        self.btn_t2_video.setText("Dừng Video")
        self._set_button_style(self.btn_t2_video, "#EF4444", "#B91C1C") 

    def _t2_stop_video(self):
        self.t2_vid_timer.stop()
        if self.t2_vid_cap is not None:
            self.t2_vid_cap.release()
            self.t2_vid_cap = None
        if hasattr(self, 'btn_t2_video'):
            self.btn_t2_video.setText("Nạp Video")
            self._set_button_style(self.btn_t2_video, "#8B5CF6", "#6D28D9") 

    def _t2_video_step(self):
        if self.t2_vid_cap is None:
            return
        ret, frame = self.t2_vid_cap.read()
        if not ret:
            self.t2_vid_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            return
        key = self.t2_filter_cb.currentData()
        g = self.t2_gamma_slider.value() / 100.0
        b = int(self.t2_bit_slider.value())
        proc = self._apply_filter(frame, key, g, b)
        self.t2_vid_label.set_cv_image(proc)

    def _t2_filter_changed(self):
        key = self.t2_filter_cb.currentData()
        self.t2_gamma_row.setVisible(key == "gamma")
        self.t2_bit_row.setVisible(key == "bitplane")
        self._t2_apply_preview_heavy()

    def _t2_apply_preview(self, *args):
        self.t2_debounce_timer.start(150)

    def _t2_apply_preview_heavy(self):
        if self.t2_paths:
            self._t2_build_grid_heavy()

    def _t2_save(self):
        if self.t2_video_path:
            self._t2_save_video()
        elif self.t2_paths:
            self._t2_save_batch()

    def _t2_save_batch(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục lưu ảnh batch")
        if not folder:
            return

        def work():
            key = self.t2_filter_cb.currentData()
            g = self.t2_gamma_slider.value() / 100.0
            b = int(self.t2_bit_slider.value())
            count = 0
            for path in self.t2_paths:
                img = cv2.imread(path)
                if img is None:
                    continue
                proc = self._apply_filter(img, key, g, b)
                cv2.imwrite(os.path.join(folder, f"processed_{os.path.basename(path)}"), proc)
                count += 1
            return count

        self._run_in_thread(work, self._t2_batch_done)

    def _t2_batch_done(self, status, result):
        if status == "err":
            self._err(f"Lỗi: {result}")
        else:
            self._info(f"Đã lưu thành công {result} ảnh!")

    def _t2_save_video(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Lưu video đã xử lý", "video_xu_ly.mp4", "Video (*.mp4 *.avi)")
        if not path:
            return
        self._info("Hệ thống đang Render Video... Vui lòng đợi!")

        def work():
            filters.save_processed_video(
                self.t2_video_path, path, self.t2_filter_cb.currentData(),
                gamma=self.t2_gamma_slider.value() / 100.0,
                bit=int(self.t2_bit_slider.value()),
            )
            return path

        self._run_in_thread(work, self._t2_video_done)

    def _t2_video_done(self, status, result):
        self._t2_stop_video()
        if status == "err":
            self._err(f"Lỗi khi lưu video: {result}")
        else:
            self._info(f"Đã xuất và lưu video: {result}")

    # ---------- LOGIC TAB 3 ----------
    def _t3_open_clean(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn ảnh chuẩn (Clean)", "", "Ảnh (*.png *.jpg *.jpeg *.bmp)")
        if not path:
            return
        img = cv2.imread(path)
        if img is None:
            self._err("Không đọc được ảnh Clean!")
            return
        self.t3_clean_cv = img
        self.t3_img_clean.set_cv_image(img)
        self.btn_t3_dam.setEnabled(True) 

        if self.t3_dam_cv is not None:
            self.t3_dam_cv = cv2.resize(self.t3_dam_cv, img.shape[:2][::-1])
            self.t3_img_dam.set_cv_image(self.t3_dam_cv)
        self._t3_run_all()

    def _t3_open_dam(self):
        if self.t3_clean_cv is None:
            self._err("Vui lòng tải Ảnh Chuẩn (Clean) trước!")
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn ảnh hỏng (Damaged)", "", "Ảnh (*.png *.jpg *.jpeg *.bmp)")
        if not path:
            return
        img = cv2.imread(path)
        if img is None:
            self._err("Không đọc được ảnh Hỏng!")
            return
        self.t3_dam_cv = cv2.resize(img, self.t3_clean_cv.shape[:2][::-1])
        self.t3_img_dam.set_cv_image(self.t3_dam_cv)
        self._t3_run_all()

    def _t3_set_metric(self, proc, lbl):
        if self.t3_clean_cv is None or proc is None:
            return
        psnr = metrics.calc_psnr(self.t3_clean_cv, proc)
        ssim = metrics.calc_ssim(self.t3_clean_cv, proc)
        lbl.setText(f"PSNR: {psnr:.2f} | SSIM: {ssim:.4f}")

    def _t3_run_all(self):
        if self.t3_dam_cv is None:
            return
        neg = filters.apply_negative(self.t3_dam_cv)
        self.t3_img_neg.set_cv_image(neg)
        self._t3_set_metric(neg, self.t3_met_neg)

        log = filters.apply_log_transform(self.t3_dam_cv)
        self.t3_img_log.set_cv_image(log)
        self._t3_set_metric(log, self.t3_met_log)

        self._t3_run_gamma_heavy()
        self._t3_run_bit_heavy()

    def _t3_run_gamma(self, *args):
        self.t3_gam_timer.start(150) 

    def _t3_run_gamma_heavy(self):
        if self.t3_dam_cv is None:
            return
        gam = filters.apply_gamma_transform(self.t3_dam_cv, gamma=self.t3_gam_slider.value() / 100.0)
        self.t3_img_gam.set_cv_image(gam)
        self._t3_set_metric(gam, self.t3_met_gam)

    def _t3_run_bit(self, *args):
        self.t3_bit_timer.start(150) 

    def _t3_run_bit_heavy(self):
        if self.t3_dam_cv is None:
            return
        bit = filters.apply_bit_plane_slicing(self.t3_dam_cv, bit=int(self.t3_bit_slider.value()))
        self.t3_img_bit.set_cv_image(bit)
        self._t3_set_metric(bit, self.t3_met_bit)

    # ---------- TIỆN ÍCH CHUNG ----------
    def _run_in_thread(self, fn, on_done):
        sig = ThreadDone()
        if on_done:
            sig.finished.connect(on_done)

        def wrapper():
            try:
                sig.finished.emit("ok", fn())
            except Exception as ex:
                sig.finished.emit("err", str(ex))

        threading.Thread(target=wrapper, daemon=True).start()

    def _info(self, msg):
        QMessageBox.information(self, "Thông báo", msg)

    def _err(self, msg):
        QMessageBox.warning(self, "Lỗi", msg)

    def closeEvent(self, event):
        self._t2_stop_video()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = ImageApp()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()