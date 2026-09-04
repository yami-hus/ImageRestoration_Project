import customtkinter as ctk
from tkinter import filedialog, messagebox
import cv2
from PIL import Image
import os
import threading

# Import các module của team
import filters
import metrics


# Thiết lập Theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

class ImageProcessingApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Ứng Dụng Xử Lý Ảnh - Nhóm IP")
        self.geometry("1350x850")
        self.minsize(1100, 750)

        self.original_image = None
        self.processed_image = None
        self.video_playing = False
        self.process_job = None
        
        self.clean_image = None
        self.damaged_image = None
        self.tab3_gamma_job = None
        self.tab3_bit_job = None

        self.tabview = ctk.CTkTabview(self, corner_radius=10)
        self.tabview.pack(padx=20, pady=10, expand=True, fill="both")
        
        self.tab_single = self.tabview.add("Xử lý Đơn ảnh")
        self.tab_batch = self.tabview.add("Batch & Video")
        self.tab_compare = self.tabview.add("So sánh phương pháp")

        self.setup_single_tab()
        self.setup_batch_tab()
        self.setup_compare_tab()

    # TAB 1: XỬ LÝ ĐƠN ẢNH
    def setup_single_tab(self):
        sidebar_frame = ctk.CTkFrame(self.tab_single, width=280, corner_radius=12)
        sidebar_frame.pack(side="left", fill="y", padx=10, pady=10)

        btn_frame = ctk.CTkFrame(sidebar_frame, fg_color="transparent")
        btn_frame.pack(pady=20, padx=20, fill="x")
        
        ctk.CTkButton(btn_frame, text="Mở File Ảnh", height=45, corner_radius=8, font=("Arial", 14, "bold"),
                      command=self.load_single_image).pack(pady=(0, 15), fill="x")
        
        ctk.CTkButton(btn_frame, text="Lưu Kết Quả", height=45, corner_radius=8, font=("Arial", 14, "bold"),
                      fg_color="#2B5B84", hover_color="#1E4363",
                      command=self.save_single_image).pack(fill="x")

        ctk.CTkLabel(sidebar_frame, text="Bộ lọc hiện tại", text_color="gray").pack(pady=(15, 0))
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

        metrics_box = ctk.CTkFrame(sidebar_frame, corner_radius=10, fg_color="#2A2D30", border_width=1, border_color="#3D3D3D")
        metrics_box.pack(pady=20, padx=20, fill="x")
        
        ctk.CTkLabel(metrics_box, text="Quality Indicators", text_color="gray").pack(pady=(10, 5))
        self.lbl_psnr = ctk.CTkLabel(metrics_box, text="PSNR: --", font=("Arial", 16, "bold"), text_color="#5CE1E6")
        self.lbl_psnr.pack(pady=2)
        self.lbl_ssim = ctk.CTkLabel(metrics_box, text="SSIM: --", font=("Arial", 16, "bold"), text_color="#5CE1E6")
        self.lbl_ssim.pack(pady=(2, 15))

        display_frame = ctk.CTkFrame(self.tab_single, fg_color="transparent")
        display_frame.pack(side="right", expand=True, fill="both", padx=10, pady=10)
        display_frame.columnconfigure(0, weight=1)
        display_frame.columnconfigure(1, weight=1)
        display_frame.rowconfigure(1, weight=1)

        ctk.CTkLabel(display_frame, text="Hình ảnh Gốc", font=("Arial", 16, "bold")).grid(row=0, column=0, pady=(0, 10))
        ctk.CTkLabel(display_frame, text="Hình ảnh Đã Xử Lý", font=("Arial", 16, "bold")).grid(row=0, column=1, pady=(0, 10))

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

        if f == "gamma":
            self.lbl_gamma_val.pack(pady=(0, 5), fill="x")
            self.gamma_slider.pack(pady=(0, 15), fill="x")
        elif f == "bitplane":
            self.lbl_bit_val.pack(pady=(0, 5), fill="x")
            self.bit_slider.pack(pady=(0, 15), fill="x")

    def load_single_image(self):
        filepath = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp")])
        if filepath:
            self.original_image = cv2.imread(filepath)
            self.display_cv_image(self.original_image, self.lbl_orig_img)
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
            self.lbl_psnr.configure(text=f"PSNR: {metrics.calc_psnr(self.original_image, self.processed_image):.2f}")
            self.lbl_ssim.configure(text=f"SSIM: {metrics.calc_ssim(self.original_image, self.processed_image):.4f}")
        except Exception as e:
            print(f"Lỗi: {e}")

    # TAB 2: BATCH & VIDEO
    def setup_batch_tab(self):
        sidebar_t2 = ctk.CTkFrame(self.tab_batch, width=280, corner_radius=12)
        sidebar_t2.pack(side="left", fill="y", padx=10, pady=10)
        
        ctk.CTkLabel(sidebar_t2, text="CÀI ĐẶT BỘ LỌC", font=("Arial", 14, "bold")).pack(pady=20)
        
        self.filter_var_t2 = ctk.StringVar(value="negative")
        filters_list = ["negative", "log", "gamma", "bitplane"]
        ctk.CTkOptionMenu(sidebar_t2, variable=self.filter_var_t2, values=filters_list, 
                          height=35, command=self.update_slider_visibility_t2).pack(pady=10, padx=20, fill="x")

        self.t2_slider_frame = ctk.CTkFrame(sidebar_t2, fg_color="transparent")
        self.t2_slider_frame.pack(fill="x", padx=20)
        
        self.gamma_slider_t2 = ctk.CTkSlider(self.t2_slider_frame, from_=0.1, to=5.0)
        self.gamma_slider_t2.set(1.0)
        self.lbl_gamma_val_t2 = ctk.CTkLabel(self.t2_slider_frame, text="Gamma (kéo để chỉnh)", text_color="#5CE1E6")
        
        self.bit_slider_t2 = ctk.CTkSlider(self.t2_slider_frame, from_=0, to=7, number_of_steps=7)
        self.bit_slider_t2.set(7)
        self.lbl_bit_val_t2 = ctk.CTkLabel(self.t2_slider_frame, text="Bitplane (0-7)", text_color="#5CE1E6")

        self.update_slider_visibility_t2()

        main_t2 = ctk.CTkFrame(self.tab_batch, fg_color="transparent")
        main_t2.pack(side="right", expand=True, fill="both")
        
        btn_frame = ctk.CTkFrame(main_t2, fg_color="transparent")
        btn_frame.pack(pady=(20, 10))
        
        ctk.CTkButton(btn_frame, text="Chọn nhiều Ảnh để xử lý", width=250, height=45, corner_radius=8, font=("Arial", 14, "bold"), 
                      command=self.run_batch).pack(side="left", padx=15)
        self.btn_video = ctk.CTkButton(btn_frame, text="Chọn Video để xử lý", width=250, height=45, corner_radius=8, font=("Arial", 14, "bold"), 
                      command=self.play_video)
        self.btn_video.pack(side="left", padx=15)
        
        video_frame = ctk.CTkFrame(main_t2, corner_radius=10, fg_color="#1E1E1E", border_width=1, border_color="#3A3A3A")
        video_frame.pack(expand=True, fill="both", padx=30, pady=20)
        self.lbl_video = ctk.CTkLabel(video_frame, text="Màn hình hiển thị Video", text_color="gray", font=("Arial", 16))
        self.lbl_video.pack(expand=True)

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

    def run_batch(self):
        filepaths = filedialog.askopenfilenames(title="Chọn các ảnh cần xử lý (Có thể chọn nhiều)",
                                                filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp")])
        if not filepaths: return
        
        out_dir = filedialog.askdirectory(title="Chọn thư mục để Lưu kết quả")
        if not out_dir: return

        f_type = self.filter_var_t2.get()
        g_val = self.gamma_slider_t2.get()
        b_val = int(self.bit_slider_t2.get())
        count = 0

        for path in filepaths:
            img = cv2.imread(path)
            if img is None: continue
            
            if f_type == "negative": p_img = filters.apply_negative(img)
            elif f_type == "log": p_img = filters.apply_log_transform(img)
            elif f_type == "gamma": p_img = filters.apply_gamma_transform(img, gamma=g_val)
            elif f_type == "bitplane": p_img = filters.apply_bit_plane_slicing(img, bit=b_val)

            filename = os.path.basename(path)
            cv2.imwrite(os.path.join(out_dir, f"processed_{filename}"), p_img)
            count += 1
            
        messagebox.showinfo("Hoàn Tất", f"Đã xử lý và lưu thành công {count} ảnh!")

    def play_video(self):
        if self.video_playing:
            self.video_playing = False
            self.btn_video.configure(text="Chọn Video để xử lý")
            return
        filepath = filedialog.askopenfilename(filetypes=[("Video", "*.mp4 *.avi *.mkv")])
        if not filepath: return
        
        self.video_playing = True
        self.btn_video.configure(text="Dừng phát Video")
        
        def video_thread():
            try:
                f_type = self.filter_var_t2.get()
                g_val = self.gamma_slider_t2.get()
                b_val = int(self.bit_slider_t2.get())
                
                gen = filters.process_video_generator(filepath, f_type, gamma=g_val, bit=b_val)
                for frame in gen:
                    if not self.video_playing: break
                    self.after(0, self.display_cv_image, frame, self.lbl_video, (800, 600))
                    cv2.waitKey(33) 
            except Exception as e: print(e)
            finally:
                self.video_playing = False
                self.after(0, lambda: self.btn_video.configure(text="🎬 Chọn Video để xử lý"))
        threading.Thread(target=video_thread, daemon=True).start()

    # TAB 3: SO SÁNH PHƯƠNG PHÁP (Yêu cầu 5 - ĐẠI TU)
    def setup_compare_tab(self):
        top_frame = ctk.CTkFrame(self.tab_compare, fg_color="transparent")
        top_frame.pack(fill="x", pady=10)
        
        ctk.CTkButton(top_frame, text="Tải Ảnh Chuẩn (Clean)", width=200, height=40, font=("Arial", 14, "bold"),
                      command=self.load_clean_img).pack(side="left", expand=True)
        ctk.CTkButton(top_frame, text="Tải Ảnh Hỏng (Damaged)", width=200, height=40, font=("Arial", 14, "bold"),
                      fg_color="#A33535", hover_color="#7A2424", command=self.load_damaged_img).pack(side="right", expand=True)
        scroll_frame = ctk.CTkScrollableFrame(self.tab_compare)
        scroll_frame.pack(expand=True, fill="both", padx=10, pady=10)
        
        row1 = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        row1.pack(fill="x", pady=10)
        self.lbl_comp_clean, _ = self.create_compare_cell(row1, "1. Ảnh Chuẩn (Clean)", has_metrics=False)
        self.lbl_comp_dam, _ = self.create_compare_cell(row1, "2. Ảnh Hỏng (Damaged)", has_metrics=False)

        row2 = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        row2.pack(fill="x", pady=10)
        self.lbl_comp_neg, self.met_neg = self.create_compare_cell(row2, "Negative Transform")
        self.lbl_comp_log, self.met_log = self.create_compare_cell(row2, "Log Transform")

        row3 = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        row3.pack(fill="x", pady=10)
        
        self.lbl_comp_gam, self.met_gam, self.slide_gam = self.create_compare_cell(
            row3, "Gamma Transform", has_slider=True, s_from=0.1, s_to=5.0, s_val=2.0, cmd=self.on_tab3_gamma)
        
        self.lbl_comp_bit, self.met_bit, self.slide_bit = self.create_compare_cell(
            row3, "Bitplane Slicing", has_slider=True, s_from=0, s_to=7, s_val=7, cmd=self.on_tab3_bit, is_int=True)

    def create_compare_cell(self, parent, title, has_slider=False, has_metrics=True, s_from=0, s_to=1, s_val=0, cmd=None, is_int=False):
        cell = ctk.CTkFrame(parent, fg_color="transparent")
        cell.pack(side="left", expand=True, fill="both", padx=10)
        
        ctk.CTkLabel(cell, text=title, font=("Arial", 15, "bold")).pack(pady=5)
        
        img_container = ctk.CTkFrame(cell, corner_radius=8, fg_color="#1E1E1E", border_width=1, border_color="#3A3A3A")
        img_container.pack(expand=True, fill="both")
        lbl_img = ctk.CTkLabel(img_container, text="Chưa tải", text_color="gray")
        lbl_img.pack(expand=True, pady=20)
        
        slider = None
        if has_slider:
            slider = ctk.CTkSlider(cell, from_=s_from, to=s_to, command=cmd)
            slider.set(s_val)
            if is_int: slider.configure(number_of_steps=s_to)
            slider.pack(pady=(10, 0), fill="x", padx=20)

        met_lbl = None
        if has_metrics:
            met_lbl = ctk.CTkLabel(cell, text="PSNR: -- | SSIM: --", text_color="#5CE1E6", font=("Arial", 13, "bold"))
            met_lbl.pack(pady=5)
            
        if has_slider:
            return lbl_img, met_lbl, slider
        else:
            return lbl_img, met_lbl

    def load_clean_img(self):
        filepath = filedialog.askopenfilename()
        if filepath:
            self.clean_image = cv2.imread(filepath)
            self.display_cv_image(self.clean_image, self.lbl_comp_clean, size=(320, 320))
            self.process_all_compare()

    def load_damaged_img(self):
        filepath = filedialog.askopenfilename()
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
        if self.damaged_image is None: return
        if self.tab3_gamma_job: self.after_cancel(self.tab3_gamma_job)
        
        def do_gamma():
            g_img = filters.apply_gamma_transform(self.damaged_image, gamma=self.slide_gam.get())
            self.display_cv_image(g_img, self.lbl_comp_gam, size=(320, 320))
            self.update_metrics(g_img, self.met_gam)
            
        self.tab3_gamma_job = self.after(150, do_gamma)

    def on_tab3_bit(self, value=None):
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
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb_image)
        pil_img.thumbnail(size) 
        ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=pil_img.size)
        label_widget.configure(image=ctk_img, text="")
        label_widget.image = ctk_img 

if __name__ == "__main__":
    app = ImageProcessingApp()
    app.mainloop()