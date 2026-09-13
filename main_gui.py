import customtkinter as ctk
from tkinter import filedialog, messagebox
import cv2
from PIL import Image
import os
import threading

import filters
import metrics

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

class ImageProcessingApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Ứng Dụng Khôi Phục Ảnh Cũ")
        self.geometry("1350x850")
        self.minsize(1100, 750)

        # Biến Tab 1
        self.original_image = None
        self.processed_image = None
        self.clean_image_t1 = None  
        self.process_job = None  
        
        # Biến Tab 2
        self.video_playing = False
        self.batch_preview_job = None
        self.preview_thread_id = 0  
        self.batch_header_frame = None 
        self.grid_container = None     
        self.current_video_path = None
        self.clean_dir_t2 = None  
        
        # Biến Tab 3
        self.clean_image = None
        self.damaged_image = None
        self.tab3_gamma_job = None
        self.tab3_bit_job = None

        self.tabview = ctk.CTkTabview(self, corner_radius=10)
        self.tabview.pack(padx=20, pady=10, expand=True, fill="both")
        
        self.tab_single = self.tabview.add("PSNR & SSIM (Đơn Ảnh)")
        self.tab_batch = self.tabview.add("Batch Processing & Video")
        self.tab_compare = self.tabview.add("So sánh phương pháp")

        self.setup_single_tab()
        self.setup_batch_tab()
        self.setup_compare_tab()

    # ==========================================
    # TAB 1: PSNR & SSIM (XỬ LÝ ĐƠN ẢNH)
    # ==========================================
    def setup_single_tab(self):
        sidebar_frame = ctk.CTkFrame(self.tab_single, width=280, corner_radius=12)
        sidebar_frame.pack(side="left", fill="y", padx=10, pady=10)

        btn_frame = ctk.CTkFrame(sidebar_frame, fg_color="transparent")
        btn_frame.pack(pady=20, padx=20, fill="x")
        
        ctk.CTkButton(btn_frame, text="Nạp Ảnh Cần Xử Lý", height=40, corner_radius=8, font=("Arial", 13, "bold"),
                      command=self.load_single_image).pack(pady=(0, 10), fill="x")
                      
        ctk.CTkButton(btn_frame, text="Nạp Ảnh Chuẩn", height=40, corner_radius=8, font=("Arial", 13, "bold"),
                      fg_color="#4CAF50", hover_color="#388E3C",
                      command=self.load_clean_t1).pack(pady=(0, 10), fill="x")
        
        ctk.CTkButton(btn_frame, text="Lưu Kết Quả", height=40, corner_radius=8, font=("Arial", 13, "bold"),
                      fg_color="#2B5B84", hover_color="#1E4363",
                      command=self.save_single_image).pack(fill="x")

        ctk.CTkLabel(sidebar_frame, text="Thay đổi tham số bộ lọc", text_color="gray", font=("Arial", 12, "bold")).pack(pady=(15, 0))
        self.filter_var = ctk.StringVar(value="negative")
        filters_list = ["negative", "log", "gamma", "bitplane"]
        ctk.CTkOptionMenu(sidebar_frame, variable=self.filter_var, values=filters_list, 
                          height=35, command=self.on_filter_select_t1).pack(pady=(5, 20), padx=20, fill="x")

        self.t1_slider_frame = ctk.CTkFrame(sidebar_frame, fg_color="transparent")
        self.t1_slider_frame.pack(fill="x", padx=20)
        
        self.lbl_gamma_val = ctk.CTkLabel(self.t1_slider_frame, text="Chỉnh Gamma: 1.00", font=("Arial", 13, "bold"), text_color="#5CE1E6")
        self.gamma_slider = ctk.CTkSlider(self.t1_slider_frame, from_=0.1, to=5.0, command=self.on_slider_change_t1)
        self.gamma_slider.set(1.0)
        self.lbl_bit_val = ctk.CTkLabel(self.t1_slider_frame, text="Chỉnh Bit (0-7): 7", font=("Arial", 13, "bold"), text_color="#5CE1E6")
        self.bit_slider = ctk.CTkSlider(self.t1_slider_frame, from_=0, to=7, number_of_steps=7, command=self.on_slider_change_t1)
        self.bit_slider.set(7)

        self.metrics_box = ctk.CTkFrame(sidebar_frame, corner_radius=10, fg_color="#2A2D30", border_width=1, border_color="#3D3D3D")
        
        ctk.CTkLabel(self.metrics_box, text="Đánh Giá Kết Quả", text_color="gray", font=("Arial", 13, "bold")).pack(pady=(10, 5))
        self.lbl_psnr = ctk.CTkLabel(self.metrics_box, text="PSNR: --", font=("Arial", 16, "bold"), text_color="#5CE1E6")
        self.lbl_psnr.pack(pady=2)
        self.lbl_ssim = ctk.CTkLabel(self.metrics_box, text="SSIM: --", font=("Arial", 16, "bold"), text_color="#5CE1E6")
        self.lbl_ssim.pack(pady=(2, 15))

        display_frame = ctk.CTkFrame(self.tab_single, fg_color="transparent")
        display_frame.pack(side="right", expand=True, fill="both", padx=10, pady=10)
        display_frame.columnconfigure(0, weight=1)
        display_frame.columnconfigure(1, weight=1)
        display_frame.rowconfigure(1, weight=1)

        ctk.CTkLabel(display_frame, text="Ảnh Trước (Hỏng)", font=("Arial", 16, "bold")).grid(row=0, column=0, pady=(0, 10))
        ctk.CTkLabel(display_frame, text="Ảnh Sau (Đã xử lý)", font=("Arial", 16, "bold")).grid(row=0, column=1, pady=(0, 10))

        frame_orig = ctk.CTkFrame(display_frame, corner_radius=8, fg_color="#1E1E1E", border_width=1, border_color="#3A3A3A")
        frame_orig.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.lbl_orig_img = ctk.CTkLabel(frame_orig, text="Chưa tải ảnh", text_color="gray")
        self.lbl_orig_img.pack(expand=True)

        frame_proc = ctk.CTkFrame(display_frame, corner_radius=8, fg_color="#1E1E1E", border_width=1, border_color="#3A3A3A")
        frame_proc.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)
        self.lbl_proc_img = ctk.CTkLabel(frame_proc, text="Chưa tải ảnh", text_color="gray")
        self.lbl_proc_img.pack(expand=True)
        
        self.update_slider_visibility_t1()

    def update_slider_visibility_t1(self):
        f = self.filter_var.get()
        self.lbl_gamma_val.pack_forget()
        self.gamma_slider.pack_forget()
        self.lbl_bit_val.pack_forget()
        self.bit_slider.pack_forget()
        self.metrics_box.pack_forget() 

        if f == "gamma":
            self.lbl_gamma_val.pack(pady=(0, 5), fill="x")
            self.gamma_slider.pack(pady=(0, 15), fill="x")
            self.metrics_box.pack(pady=20, padx=20, fill="x")
        elif f == "bitplane":
            self.lbl_bit_val.pack(pady=(0, 5), fill="x")
            self.bit_slider.pack(pady=(0, 15), fill="x")
            self.metrics_box.pack(pady=20, padx=20, fill="x")

    def load_single_image(self):
        filepath = filedialog.askopenfilename(title="Chọn ảnh hỏng cần xử lý", filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp")])
        if filepath:
            self.original_image = cv2.imread(filepath)
            self.display_cv_image(self.original_image, self.lbl_orig_img)
            self.apply_single_filter()
            
    def load_clean_t1(self):
        filepath = filedialog.askopenfilename(title="Chọn ảnh chuẩn để so sánh chấm điểm", filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp")])
        if filepath:
            self.clean_image_t1 = cv2.imread(filepath)
            messagebox.showinfo("Thành công", "Đã nạp ảnh Clean tham chiếu. PSNR và SSIM sẽ được tính toán!")
            self.apply_single_filter()

    def save_single_image(self):
        if self.processed_image is not None:
            filepath = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG file", "*.png"), ("JPEG file", "*.jpg"), ("All files", "*.*")]
            )
            if filepath:
                cv2.imwrite(filepath, self.processed_image)
                messagebox.showinfo("Thành công", "Đã lưu kết quả ảnh!")

    def on_filter_select_t1(self, value):
        self.update_slider_visibility_t1()
        self.apply_single_filter()

    def on_slider_change_t1(self, value=None):
        self.lbl_gamma_val.configure(text=f"Chỉnh Gamma: {self.gamma_slider.get():.2f}")
        self.lbl_bit_val.configure(text=f"Chỉnh Bit (0-7): {int(self.bit_slider.get())}")
        if self.process_job: self.after_cancel(self.process_job)
        self.process_job = self.after(150, self.apply_single_filter)

    def apply_single_filter(self):
        if self.original_image is None: return
        f_type = self.filter_var.get()
        try:
            if f_type == "negative":
                self.processed_image = filters.apply_negative(self.original_image)
            elif f_type == "log":
                self.processed_image = filters.apply_log_transform(self.original_image)
            elif f_type == "gamma":
                self.processed_image = filters.apply_gamma_transform(self.original_image, gamma=self.gamma_slider.get())
            elif f_type == "bitplane":
                self.processed_image = filters.apply_bit_plane_slicing(self.original_image, bit=int(self.bit_slider.get()))

            self.display_cv_image(self.processed_image, self.lbl_proc_img)
            
            if self.clean_image_t1 is not None and self.processed_image is not None and f_type in ["gamma", "bitplane"]:
                h, w = self.processed_image.shape[:2]
                clean_resized = cv2.resize(self.clean_image_t1, (w, h))
                psnr = metrics.calc_psnr(clean_resized, self.processed_image)
                ssim = metrics.calc_ssim(clean_resized, self.processed_image)
                self.lbl_psnr.configure(text=f"PSNR: {psnr:.2f}")
                self.lbl_ssim.configure(text=f"SSIM: {ssim:.4f}")
            else:
                self.lbl_psnr.configure(text="PSNR: Chờ ảnh Clean")
                self.lbl_ssim.configure(text="SSIM: Chờ ảnh Clean")

        except Exception as e:
            print(f"Lỗi: {e}")

    # ==========================================
    # TAB 2: BATCH PROCESSING & VIDEO
    # ==========================================
    def setup_batch_tab(self):
        sidebar_t2 = ctk.CTkFrame(self.tab_batch, width=280, corner_radius=12)
        sidebar_t2.pack(side="left", fill="y", padx=10, pady=10)
        
        ctk.CTkLabel(sidebar_t2, text="CÀI ĐẶT BỘ LỌC", font=("Arial", 14, "bold")).pack(pady=20)
        
        self.filter_var_t2 = ctk.StringVar(value="negative")
        filters_list = ["negative", "log", "gamma", "bitplane"]
        ctk.CTkOptionMenu(sidebar_t2, variable=self.filter_var_t2, values=filters_list, 
                          height=35, command=self.on_filter_select_t2).pack(pady=10, padx=20, fill="x")

        self.t2_slider_frame = ctk.CTkFrame(sidebar_t2, fg_color="transparent")
        self.t2_slider_frame.pack(fill="x", padx=20)
        
        self.gamma_slider_t2 = ctk.CTkSlider(self.t2_slider_frame, from_=0.1, to=5.0, command=self.on_slider_change_t2)
        self.gamma_slider_t2.set(1.0)
        self.lbl_gamma_val_t2 = ctk.CTkLabel(self.t2_slider_frame, text="Chỉnh Gamma: 1.00", font=("Arial", 13, "bold"), text_color="#5CE1E6")
        
        self.bit_slider_t2 = ctk.CTkSlider(self.t2_slider_frame, from_=0, to=7, number_of_steps=7, command=self.on_slider_change_t2)
        self.bit_slider_t2.set(7)
        self.lbl_bit_val_t2 = ctk.CTkLabel(self.t2_slider_frame, text="Chỉnh Bit (0-7): 7", font=("Arial", 13, "bold"), text_color="#5CE1E6")

        self.update_slider_visibility_t2()

        main_t2 = ctk.CTkFrame(self.tab_batch, fg_color="transparent")
        main_t2.pack(side="right", expand=True, fill="both")
        
        btn_frame = ctk.CTkFrame(main_t2, fg_color="transparent")
        btn_frame.pack(side="top", pady=(20, 10))
        
        ctk.CTkButton(btn_frame, text="Nạp Batch Ảnh", width=160, height=45, corner_radius=8, font=("Arial", 14, "bold"), 
                      command=self.select_batch_images).pack(side="left", padx=10)

        self.btn_video = ctk.CTkButton(btn_frame, text="Nạp Video", width=160, height=45, corner_radius=8, font=("Arial", 14, "bold"), 
                      command=self.play_video)
        self.btn_video.pack(side="left", padx=10)
        
        self.bottom_action_frame = ctk.CTkFrame(main_t2, fg_color="transparent", height=45)
        self.bottom_action_frame.pack(side="bottom", fill="x", pady=(0, 20))
        self.bottom_action_frame.pack_propagate(False)
        
        self.btn_save_batch = ctk.CTkButton(self.bottom_action_frame, text="Lưu Ảnh/Video", width=220, height=45, corner_radius=8, font=("Arial", 14, "bold"), 
                      command=self.run_save_batch, fg_color="#2B5B84", hover_color="#1E4363")
        self.btn_save_batch.pack_forget()

        self.btn_eval_batch = ctk.CTkButton(self.bottom_action_frame, text="Lưu File Đánh Giá PSNR/SSIM", width=220, height=45, corner_radius=8, font=("Arial", 14, "bold"), 
                      command=self.run_evaluate_batch, fg_color="#4CAF50", hover_color="#388E3C")
        self.btn_eval_batch.pack_forget()
        
        self.batch_preview_frame = ctk.CTkFrame(main_t2, corner_radius=10, fg_color="#1E1E1E", border_width=1, border_color="#3A3A3A")
        self.batch_preview_frame.pack(side="top", expand=True, fill="both", padx=30, pady=(10, 20))
        self.batch_preview_frame.pack_propagate(False)

        self.lbl_batch_status = ctk.CTkLabel(self.batch_preview_frame, text="Chưa nạp dữ liệu.", text_color="gray", font=("Arial", 16))
        self.lbl_batch_status.place(relx=0.5, rely=0.5, anchor="center")

        self.batch_filepaths = []
        self.batch_image_widgets = []

    def on_filter_select_t2(self, value=None):
        self.update_slider_visibility_t2()
        self.schedule_batch_preview()

    def on_slider_change_t2(self, value=None):
        self.lbl_gamma_val_t2.configure(text=f"Chỉnh Gamma: {self.gamma_slider_t2.get():.2f}")
        self.lbl_bit_val_t2.configure(text=f"Chỉnh Bit (0-7): {int(self.bit_slider_t2.get())}")
        self.schedule_batch_preview()

    def update_slider_visibility_t2(self, value=None):
        f = self.filter_var_t2.get()
        self.lbl_gamma_val_t2.pack_forget()
        self.gamma_slider_t2.pack_forget()
        self.lbl_bit_val_t2.pack_forget()
        self.bit_slider_t2.pack_forget()

        if f == "gamma":
            self.lbl_gamma_val_t2.pack(pady=(5, 0))
            self.gamma_slider_t2.pack(pady=(0, 10), fill="x")
        elif f == "bitplane":
            self.lbl_bit_val_t2.pack(pady=(5, 0))
            self.bit_slider_t2.pack(pady=(0, 10), fill="x")

    def schedule_batch_preview(self):
        if self.batch_preview_job:
            self.after_cancel(self.batch_preview_job)
        if self.video_playing: return
        self.batch_preview_job = self.after(150, self.update_batch_preview)

    def apply_filter_to_img(self, img, f_type, g_val, b_val):
        try:
            if f_type == "negative": return filters.apply_negative(img)
            elif f_type == "log": return filters.apply_log_transform(img)
            elif f_type == "gamma": return filters.apply_gamma_transform(img, gamma=g_val)
            elif f_type == "bitplane": return filters.apply_bit_plane_slicing(img, bit=b_val)
        except Exception:
            pass
        return img

    def update_batch_preview(self):
        if not hasattr(self, 'batch_filepaths') or not self.batch_filepaths or self.video_playing: 
            return
            
        f_type = self.filter_var_t2.get()
        g_val = self.gamma_slider_t2.get()
        b_val = int(self.bit_slider_t2.get())
        
        num_images = len(self.batch_filepaths)
        preview_limit = min(num_images, 30) 
        
        self.preview_thread_id += 1
        current_id = self.preview_thread_id

        def process_and_display():
            img_size = (450, 450)
            
            for index in range(preview_limit):
                if self.preview_thread_id != current_id: break 
                if index >= len(self.batch_image_widgets): break
                
                path = self.batch_filepaths[index]
                img = cv2.imread(path)
                if img is None: continue
                p_img = self.apply_filter_to_img(img, f_type, g_val, b_val)
                
                if self.preview_thread_id == current_id:
                    lbl_orig, lbl_proc = self.batch_image_widgets[index]
                    if lbl_orig.winfo_exists() and lbl_proc.winfo_exists():
                        self.after(0, self.display_cv_image, img, lbl_orig, img_size)
                        self.after(0, self.display_cv_image, p_img, lbl_proc, img_size)

        threading.Thread(target=process_and_display, daemon=True).start()

    def select_batch_images(self):
        filepaths = filedialog.askopenfilenames(title="Chọn danh sách ảnh cần xử lý (Batch)",
                                                filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp")])
        if not filepaths: 
            return
            
        self.batch_filepaths = list(filepaths)
        self.current_video_path = None
        
        self.btn_save_batch.configure(text="Lưu Ảnh Xử Lý")
        self.btn_save_batch.pack(side="left", padx=(100, 20), expand=True)
        self.btn_eval_batch.pack(side="right", padx=(20, 100), expand=True)
        
        if getattr(self, 'grid_container', None):
            self.grid_container.destroy()
            self.grid_container = None
        if getattr(self, 'batch_header_frame', None):
            self.batch_header_frame.destroy()
            self.batch_header_frame = None
            
        self.lbl_batch_status.place_forget()
        self.batch_image_widgets.clear()

        num_images = len(self.batch_filepaths)
        preview_limit = min(num_images, 30) 

        self.batch_header_frame = ctk.CTkFrame(self.batch_preview_frame, fg_color="transparent")
        self.batch_header_frame.pack(side="top", fill="x", pady=(10, 0))
        self.batch_header_frame.grid_columnconfigure(0, weight=1)
        self.batch_header_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(self.batch_header_frame, text="Ảnh Gốc (Trước)", font=("Arial", 16, "bold")).grid(row=0, column=0)
        ctk.CTkLabel(self.batch_header_frame, text="Ảnh Xử Lý (Sau)", font=("Arial", 16, "bold")).grid(row=0, column=1)

        self.grid_container = ctk.CTkScrollableFrame(self.batch_preview_frame, fg_color="transparent")
        self.grid_container.pack(expand=True, fill="both", padx=5, pady=5)
        self.grid_container.grid_columnconfigure(0, weight=1)
        self.grid_container.grid_columnconfigure(1, weight=1)

        for index in range(preview_limit):
            path = self.batch_filepaths[index]
            r = index
            filename = os.path.basename(path)
            
            display_name_orig = filename if len(filename) <= 35 else filename[:35] + "..."
            display_name_proc = f"processed_{filename}"
            display_name_proc = display_name_proc if len(display_name_proc) <= 35 else display_name_proc[:35] + "..."
            
            frame_orig = ctk.CTkFrame(self.grid_container, fg_color="transparent")
            frame_orig.grid(row=r, column=0, padx=15, pady=15, sticky="nsew")
            lbl_orig = ctk.CTkLabel(frame_orig, text="Đang tải...", text_color="gray")
            lbl_orig.pack(expand=True)
            name_lbl_orig = ctk.CTkLabel(frame_orig, text=display_name_orig, font=("Arial", 12))
            name_lbl_orig.pack(pady=(5,0))
            
            frame_proc = ctk.CTkFrame(self.grid_container, fg_color="transparent")
            frame_proc.grid(row=r, column=1, padx=15, pady=15, sticky="nsew")
            lbl_proc = ctk.CTkLabel(frame_proc, text="Đang xử lý...", text_color="gray")
            lbl_proc.pack(expand=True)
            name_lbl_proc = ctk.CTkLabel(frame_proc, text=display_name_proc, font=("Arial", 12))
            name_lbl_proc.pack(pady=(5,0))
            
            self.batch_image_widgets.append((lbl_orig, lbl_proc))
                
        self.update_batch_preview()

    def run_save_batch(self):
        if not self.batch_filepaths and not self.current_video_path:
            messagebox.showwarning("Cảnh báo", "Vui lòng nạp ảnh hoặc video để lưu!")
            return

        f_type = self.filter_var_t2.get()
        g_val = self.gamma_slider_t2.get()
        b_val = int(self.bit_slider_t2.get())

        if self.current_video_path:
            out_path = filedialog.asksaveasfilename(
                title="Lưu Video Xử Lý",
                defaultextension=".mp4",
                filetypes=[("MP4 file", "*.mp4"), ("AVI file", "*.avi")]
            )
            if not out_path: return

            self.btn_save_batch.configure(state="disabled", text="Đang Render Video...")

            def save_vid_task():
                try:
                    filters.save_processed_video(
                        self.current_video_path, out_path, f_type, gamma=g_val, bit=b_val
                    )
                    self.after(0, lambda: messagebox.showinfo("Hoàn Tất", "Đã xuất và lưu video thành công!"))
                except Exception as e:
                    self.after(0, lambda: messagebox.showerror("Lỗi", f"Không thể lưu video: {e}"))
                finally:
                    self.after(0, lambda: self.btn_save_batch.configure(state="normal", text="💾 Lưu Video Xử Lý"))

            threading.Thread(target=save_vid_task, daemon=True).start()

        elif self.batch_filepaths:
            out_dir = filedialog.askdirectory(title="Chọn thư mục để lưu ảnh đã xử lý")
            if not out_dir: return

            count = 0
            for path in self.batch_filepaths:
                img = cv2.imread(path)
                if img is None: continue
                p_img = self.apply_filter_to_img(img, f_type, g_val, b_val)
                filename = os.path.basename(path)
                cv2.imwrite(os.path.join(out_dir, f"processed_{filename}"), p_img)
                count += 1
                
            messagebox.showinfo("Hoàn Tất", f"Đã lưu thành công {count} ảnh!")

    def run_evaluate_batch(self):
        if not self.batch_filepaths:
            messagebox.showwarning("Cảnh báo", "Tính năng này chỉ dành cho Batch Ảnh!")
            return

        clean_dir = filedialog.askdirectory(title="Chọn thư mục chứa Ảnh Chuẩn")
        if not clean_dir: return

        csv_path = filedialog.asksaveasfilename(title="Chọn nơi lưu file đánh giá", defaultextension=".csv", filetypes=[("CSV file", "*.csv")])
        if not csv_path: return

        f_type = self.filter_var_t2.get()
        g_val = self.gamma_slider_t2.get()
        b_val = int(self.bit_slider_t2.get())

        self.btn_eval_batch.configure(state="disabled", text="Đang Chấm Điểm...")

        def eval_task():
            report_lines = ["Filename,PSNR,SSIM"]
            count = 0
            
            for path in self.batch_filepaths:
                filename = os.path.basename(path)
                clean_path = os.path.join(clean_dir, filename)
                
                if os.path.exists(clean_path):
                    img = cv2.imread(path)
                    if img is None: continue
                    p_img = self.apply_filter_to_img(img, f_type, g_val, b_val)
                    
                    clean_img = cv2.imread(clean_path)
                    h, w = p_img.shape[:2]
                    clean_img = cv2.resize(clean_img, (w, h))
                    
                    psnr_val = metrics.calc_psnr(clean_img, p_img)
                    ssim_val = metrics.calc_ssim(clean_img, p_img)
                    report_lines.append(f"{filename},{psnr_val:.2f},{ssim_val:.4f}")
                    count += 1
                else:
                    report_lines.append(f"{filename},Không tìm thấy file Clean tương ứng,")

            with open(csv_path, "w", encoding="utf-8-sig") as f:
                f.write("\n".join(report_lines))
                
            self.after(0, lambda: messagebox.showinfo("Hoàn Tất", f"Đã đánh giá thành công {count} ảnh.\nBảng điểm được lưu tại:\n{csv_path}"))
            self.after(0, lambda: self.btn_eval_batch.configure(state="normal", text="📊 Đánh Giá PSNR/SSIM"))

        threading.Thread(target=eval_task, daemon=True).start()

    def play_video(self):
        if self.video_playing:
            self.video_playing = False
            self.btn_video.configure(text="Nạp Video")
            return
            
        filepath = filedialog.askopenfilename(filetypes=[("Video", "*.mp4 *.avi *.mkv")])
        if not filepath: return
        
        self.batch_filepaths = []
        self.current_video_path = filepath
        
        self.btn_eval_batch.pack_forget()
        self.btn_save_batch.configure(text="Lưu Video Xử Lý")
        self.btn_save_batch.pack(anchor="center", pady=(0,0))
        
        if getattr(self, 'grid_container', None):
            self.grid_container.destroy()
            self.grid_container = None
        if getattr(self, 'batch_header_frame', None):
            self.batch_header_frame.destroy()
            self.batch_header_frame = None
            
        self.lbl_batch_status.place(relx=0.5, rely=0.5, anchor="center")
        
        self.video_playing = True
        self.btn_video.configure(text="Dừng phát Video")
        self.lbl_batch_status.configure(text="Đang chuẩn bị Video...", image="")
        
        def video_thread():
            cap = cv2.VideoCapture(self.current_video_path)
            try:
                while self.video_playing and cap.isOpened():
                    ret, frame = cap.read()
                    if not ret: 
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue
                    
                    f_type = self.filter_var_t2.get()
                    g_val = self.gamma_slider_t2.get()
                    b_val = int(self.bit_slider_t2.get())
                    
                    p_frame = self.apply_filter_to_img(frame, f_type, g_val, b_val)
                    self.after(0, self.display_cv_image, p_frame, self.lbl_batch_status, (900, 600))
                    cv2.waitKey(33) 
            except Exception as e: 
                print(f"Lỗi Video: {e}")
            finally:
                if cap: cap.release()
                self.video_playing = False
                self.after(0, lambda: self.btn_video.configure(text="Nạp Video"))
                
        threading.Thread(target=video_thread, daemon=True).start()

    # ==========================================
    # TAB 3: SO SÁNH PHƯƠNG PHÁP
    # ==========================================
    def setup_compare_tab(self):
        top_frame = ctk.CTkFrame(self.tab_compare, fg_color="transparent")
        top_frame.pack(fill="x", pady=10)
        
        ctk.CTkButton(top_frame, text="Tải Ảnh Chuẩn (Clean)", width=200, height=40, font=("Arial", 14, "bold"),
                      command=self.load_clean_img).pack(side="left", expand=True)
                      
        self.btn_load_damaged = ctk.CTkButton(top_frame, text="Tải Ảnh Hỏng (Damaged)", width=200, height=40, font=("Arial", 14, "bold"),
                      fg_color="#A33535", hover_color="#7A2424", command=self.load_damaged_img, state="disabled")
        self.btn_load_damaged.pack(side="right", expand=True)

        scroll_frame = ctk.CTkScrollableFrame(self.tab_compare)
        scroll_frame.pack(expand=True, fill="both", padx=10, pady=10)
        
        row1 = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        row1.pack(fill="x", pady=10)
        self.lbl_comp_clean, _ = self.create_compare_cell(row1, "Ảnh Chuẩn (Clean GT)", has_metrics=False)
        self.lbl_comp_dam, _ = self.create_compare_cell(row1, "Ảnh Hỏng (Damaged)", has_metrics=False)

        row2 = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        row2.pack(fill="x", pady=10)
        self.lbl_comp_neg, self.met_neg = self.create_compare_cell(row2, "Negative Transform")
        self.lbl_comp_log, self.met_log = self.create_compare_cell(row2, "Log Transform")

        row3 = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        row3.pack(fill="x", pady=10)
        
        self.lbl_comp_gam, self.met_gam, self.slide_gam, self.lbl_val_gam = self.create_compare_cell(
            row3, "Gamma Transform", has_slider=True, s_from=0.1, s_to=5.0, s_val=2.0, cmd=self.on_tab3_gamma, label_prefix="Chỉnh Gamma:")
        
        self.lbl_comp_bit, self.met_bit, self.slide_bit, self.lbl_val_bit = self.create_compare_cell(
            row3, "Bitplane Slicing", has_slider=True, s_from=0, s_to=7, s_val=7, cmd=self.on_tab3_bit, is_int=True, label_prefix="Chỉnh Bit (0-7):")

    def create_compare_cell(self, parent, title, has_slider=False, has_metrics=True, s_from=0, s_to=1, s_val=0, cmd=None, is_int=False, label_prefix=""):
        cell = ctk.CTkFrame(parent, fg_color="transparent")
        cell.pack(side="left", expand=True, fill="both", padx=10)
        
        ctk.CTkLabel(cell, text=title, font=("Arial", 15, "bold")).pack(pady=5)
        
        img_container = ctk.CTkFrame(cell, corner_radius=8, fg_color="#1E1E1E", border_width=1, border_color="#3A3A3A")
        img_container.pack(expand=True, fill="both")
        lbl_img = ctk.CTkLabel(img_container, text="Chưa tải", text_color="gray")
        lbl_img.pack(expand=True, pady=20)
        
        slider = None
        val_lbl = None
        if has_slider:
            val_lbl = ctk.CTkLabel(cell, text=f"{label_prefix} {s_val:.2f}" if not is_int else f"{label_prefix} {s_val}", font=("Arial", 13, "bold"), text_color="#5CE1E6")
            val_lbl.pack(pady=(10, 0))
            slider = ctk.CTkSlider(cell, from_=s_from, to=s_to, command=cmd)
            slider.set(s_val)
            if is_int: slider.configure(number_of_steps=s_to)
            slider.pack(pady=(0, 10), fill="x", padx=20)

        met_lbl = None
        if has_metrics:
            met_lbl = ctk.CTkLabel(cell, text="PSNR: -- | SSIM: --", text_color="#5CE1E6", font=("Arial", 13, "bold"))
            met_lbl.pack(pady=5)
            
        if has_slider:
            return lbl_img, met_lbl, slider, val_lbl
        else:
            return lbl_img, met_lbl

    def load_clean_img(self):
        filepath = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp")])
        if filepath:
            self.clean_image = cv2.imread(filepath)
            self.btn_load_damaged.configure(state="normal") # Mở khóa nút Tải Ảnh Hỏng
            
            if self.damaged_image is not None:
                h, w = self.clean_image.shape[:2]
                self.damaged_image = cv2.resize(self.damaged_image, (w, h))
                self.display_cv_image(self.damaged_image, self.lbl_comp_dam, size=(320, 320))
                
            self.display_cv_image(self.clean_image, self.lbl_comp_clean, size=(320, 320))
            self.process_all_compare()

    def load_damaged_img(self):
        if self.clean_image is None:
            messagebox.showwarning("Cảnh báo", "Vui lòng Tải Ảnh Chuẩn (Clean) trước!")
            return
            
        filepath = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp")])
        if filepath:
            self.damaged_image = cv2.imread(filepath)
            
            if self.clean_image is not None:
                h, w = self.clean_image.shape[:2]
                self.damaged_image = cv2.resize(self.damaged_image, (w, h))
                
            self.display_cv_image(self.damaged_image, self.lbl_comp_dam, size=(320, 320))
            self.process_all_compare()

    def update_metrics(self, processed_img, label_widget):
        if self.clean_image is None or processed_img is None:
            label_widget.configure(text="Thiếu ảnh Clean")
            return
        try:
            psnr = metrics.calc_psnr(self.clean_image, processed_img)
            ssim = metrics.calc_ssim(self.clean_image, processed_img)
            label_widget.configure(text=f"PSNR: {psnr:.2f} | SSIM: {ssim:.4f}")
        except Exception as e:
            label_widget.configure(text="Lỗi kích thước ảnh")

    def process_all_compare(self):
        if self.damaged_image is None: return
        
        neg_img = filters.apply_negative(self.damaged_image)
        self.display_cv_image(neg_img, self.lbl_comp_neg, size=(320, 320))
        self.update_metrics(neg_img, self.met_neg)

        log_img = filters.apply_log_transform(self.damaged_image)
        self.display_cv_image(log_img, self.lbl_comp_log, size=(320, 320))
        self.update_metrics(log_img, self.met_log)

        self.on_tab3_gamma() 
        self.on_tab3_bit()

    def on_tab3_gamma(self, value=None):
        if value is not None:
            self.lbl_val_gam.configure(text=f"Chỉnh Gamma: {float(value):.2f}")
        else:
            self.lbl_val_gam.configure(text=f"Chỉnh Gamma: {self.slide_gam.get():.2f}")
            
        if self.damaged_image is None: return
        
        if self.tab3_gamma_job: self.after_cancel(self.tab3_gamma_job)
        
        def do_gamma():
            g_img = filters.apply_gamma_transform(self.damaged_image, gamma=self.slide_gam.get())
            self.display_cv_image(g_img, self.lbl_comp_gam, size=(320, 320))
            self.update_metrics(g_img, self.met_gam)
            
        self.tab3_gamma_job = self.after(150, do_gamma)

    def on_tab3_bit(self, value=None):
        if value is not None:
            self.lbl_val_bit.configure(text=f"Chỉnh Bit (0-7): {int(float(value))}")
        else:
            self.lbl_val_bit.configure(text=f"Chỉnh Bit (0-7): {int(self.slide_bit.get())}")
            
        if self.damaged_image is None: return
        
        if self.tab3_bit_job: self.after_cancel(self.tab3_bit_job)
        
        def do_bit():
            b_img = filters.apply_bit_plane_slicing(self.damaged_image, bit=int(self.slide_bit.get()))
            self.display_cv_image(b_img, self.lbl_comp_bit, size=(320, 320))
            self.update_metrics(b_img, self.met_bit)
            
        self.tab3_bit_job = self.after(150, do_bit)

    # HÀM HỖ TRỢ HIỂN THỊ
    def display_cv_image(self, cv_img, label_widget, size=(500, 500)):
        if cv_img is None: return
        
        h, w = cv_img.shape[:2]
        max_w, max_h = size
        
        ratio = min(max_w / w, max_h / h)
        new_w = max(1, int(w * ratio))
        new_h = max(1, int(h * ratio))
        
        resized_img = cv2.resize(cv_img, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
        rgb_image = cv2.cvtColor(resized_img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb_image)
        
        ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(new_w, new_h))
        label_widget.configure(image=ctk_img, text="")
        label_widget.image = ctk_img 

if __name__ == "__main__":
    app = ImageProcessingApp()
    app.mainloop()