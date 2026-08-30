import customtkinter as ctk
from tkinter import filedialog, messagebox
import cv2
from PIL import Image
import threading

import filters
import metrics

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

class ImageProcessingApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Ứng Dụng Xử Lý Ảnh - Nhóm IP")
        self.geometry("1280x800")
        self.minsize(1000, 700)

        # Biến lưu trữ dữ liệu
        self.original_image = None
        self.processed_image = None
        self.video_playing = False
        
        self.process_job = None

        self.tabview = ctk.CTkTabview(self, corner_radius=10)
        self.tabview.pack(padx=20, pady=20, expand=True, fill="both")
        
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
        self.filter_var = ctk.StringVar(value="bitplane")
        filters_list = ["negative", "log", "gamma", "bitplane"]
        ctk.CTkOptionMenu(sidebar_frame, variable=self.filter_var, values=filters_list, 
                          height=35, command=self.on_filter_select).pack(pady=(5, 20), padx=20, fill="x")

        ctk.CTkLabel(sidebar_frame, text="Thông số điều chỉnh", text_color="gray").pack(pady=(5, 5))
        
        self.lbl_gamma_val = ctk.CTkLabel(sidebar_frame, text="Chỉnh Gamma: 1.00", font=("Arial", 13, "bold"), text_color="#5CE1E6")
        self.lbl_gamma_val.pack()
        self.gamma_slider = ctk.CTkSlider(sidebar_frame, from_=0.1, to=5.0, command=self.on_slider_change)
        self.gamma_slider.set(1.0)
        self.gamma_slider.pack(pady=(0, 15), padx=20, fill="x")

        self.lbl_bit_val = ctk.CTkLabel(sidebar_frame, text="Chỉnh Bit (0-7): 7", font=("Arial", 13, "bold"), text_color="#5CE1E6")
        self.lbl_bit_val.pack()
        self.bit_slider = ctk.CTkSlider(sidebar_frame, from_=0, to=7, number_of_steps=7, command=self.on_slider_change)
        self.bit_slider.set(7)
        self.bit_slider.pack(pady=(0, 20), padx=20, fill="x")

        metrics_box = ctk.CTkFrame(sidebar_frame, corner_radius=10, fg_color="#2A2D30", border_width=1, border_color="#3D3D3D")
        metrics_box.pack(pady=10, padx=20, fill="x")
        
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

    def load_single_image(self):
        filepath = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp")])
        if filepath:
            self.original_image = cv2.imread(filepath)
            self.display_cv_image(self.original_image, self.lbl_orig_img)
            self.apply_single_filter()

    def save_single_image(self):
        if self.processed_image is not None:
            filepath = filedialog.asksaveasfilename(defaultextension=".png")
            if filepath:
                cv2.imwrite(filepath, self.processed_image)
                messagebox.showinfo("Thành công", "Đã lưu kết quả ảnh!")

    def on_filter_select(self, value):
        self.apply_single_filter()

    def on_slider_change(self, value=None):
        self.lbl_gamma_val.configure(text=f"Chỉnh Gamma: {self.gamma_slider.get():.2f}")
        self.lbl_bit_val.configure(text=f"Chỉnh Bit (0-7): {int(self.bit_slider.get())}")
        if self.process_job is not None:
            self.after_cancel(self.process_job)
            
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

    # TAB 2: BATCH & VIDEO (Tối ưu Threading)
    def setup_batch_tab(self):
        ctk.CTkLabel(self.tab_batch, text="Xử Lý Hàng Loạt (Batch & Video)", font=("Arial", 22, "bold")).pack(pady=(30, 20))
        
        btn_frame = ctk.CTkFrame(self.tab_batch, fg_color="transparent")
        btn_frame.pack(pady=10)
        
        ctk.CTkButton(btn_frame, text="Xử lý nhiều ảnh cùng lúc", width=280, height=45, corner_radius=8, font=("Arial", 14, "bold"), 
                      command=self.run_batch).pack(side="left", padx=15)
        self.btn_video = ctk.CTkButton(btn_frame, text="Chọn Video để xử lý", width=280, height=45, corner_radius=8, font=("Arial", 14, "bold"), 
                      command=self.play_video)
        self.btn_video.pack(side="left", padx=15)
        
        video_frame = ctk.CTkFrame(self.tab_batch, corner_radius=10, fg_color="#1E1E1E", border_width=1, border_color="#3A3A3A")
        video_frame.pack(expand=True, fill="both", padx=60, pady=30)
        
        self.lbl_video = ctk.CTkLabel(video_frame, text="Màn hình hiển thị Video", text_color="gray", font=("Arial", 16))
        self.lbl_video.pack(expand=True)

    def run_batch(self):
        in_dir = filedialog.askdirectory(title="Chọn thư mục chứa ảnh gốc")
        if not in_dir: return
        out_dir = filedialog.askdirectory(title="Chọn thư mục lưu kết quả")
        if not out_dir: return
        count = filters.process_batch_images(in_dir, out_dir, self.filter_var.get(), gamma=self.gamma_slider.get(), bit=int(self.bit_slider.get()))
        messagebox.showinfo("Hoàn Tất", f"Đã xử lý {count} ảnh!")

    def play_video(self):
        if self.video_playing:
            self.video_playing = False
            self.btn_video.configure(text="Lưu Video")
            return

        filepath = filedialog.askopenfilename(filetypes=[("Video", "*.mp4 *.avi *.mkv")])
        if not filepath: return
        
        self.video_playing = True
        self.btn_video.configure(text="Dừng Video")
        
        def video_thread():
            try:
                gen = filters.process_video_generator(filepath, self.filter_var.get(), gamma=self.gamma_slider.get())
                for frame in gen:
                    if not self.video_playing: break
                    self.after(0, self.display_cv_image, frame, self.lbl_video, (800, 600))
                    cv2.waitKey(33)
                    
            except Exception as e: print(e)
            finally:
                self.video_playing = False
                self.after(0, lambda: self.btn_video.configure(text="Mở Video (Generator)"))

        threading.Thread(target=video_thread, daemon=True).start()

    # TAB 3: SO SÁNH PHƯƠNG PHÁP
    def setup_compare_tab(self):
        ctk.CTkButton(self.tab_compare, text="Tải Ảnh So Sánh", width=300, height=45, corner_radius=8, font=("Arial", 14, "bold"), 
                      command=self.load_compare_image).pack(pady=(20, 10))
        
        comp_frame = ctk.CTkFrame(self.tab_compare, fg_color="transparent")
        comp_frame.pack(expand=True, fill="both", padx=10, pady=10)

        def create_col(parent, title):
            col = ctk.CTkFrame(parent, fg_color="transparent")
            col.pack(side="left", expand=True, fill="both", padx=10)
            
            ctk.CTkLabel(col, text=title, font=("Arial", 16, "bold")).pack(pady=(0, 10))
            
            img_container = ctk.CTkFrame(col, corner_radius=8, fg_color="#1E1E1E", border_width=1, border_color="#3A3A3A")
            img_container.pack(expand=True, fill="both")
            lbl_img = ctk.CTkLabel(img_container, text="Chưa tải ảnh", text_color="gray")
            lbl_img.pack(expand=True)
            
            lbl_met = ctk.CTkLabel(col, text="PSNR: -- \nSSIM: --", text_color="#5CE1E6", font=("Arial", 14, "bold"))
            lbl_met.pack(pady=15)
            return lbl_img, lbl_met

        self.lbl_comp_orig, _ = create_col(comp_frame, "Ảnh Gốc")
        self.lbl_comp_log, self.lbl_metric_log = create_col(comp_frame, "Log Transform")
        self.lbl_comp_gamma, self.lbl_metric_gamma = create_col(comp_frame, "Gamma Transform (2.0)")

    def load_compare_image(self):
        filepath = filedialog.askopenfilename()
        if not filepath: return
        orig = cv2.imread(filepath)
        log_img = filters.apply_log_transform(orig)
        gamma_img = filters.apply_gamma_transform(orig, gamma=2.0)

        self.display_cv_image(orig, self.lbl_comp_orig, size=(380, 380))
        self.display_cv_image(log_img, self.lbl_comp_log, size=(380, 380))
        self.display_cv_image(gamma_img, self.lbl_comp_gamma, size=(380, 380))

        self.lbl_metric_log.configure(text=f"PSNR: {metrics.calc_psnr(orig, log_img):.2f}\nSSIM: {metrics.calc_ssim(orig, log_img):.4f}")
        self.lbl_metric_gamma.configure(text=f"PSNR: {metrics.calc_psnr(orig, gamma_img):.2f}\nSSIM: {metrics.calc_ssim(orig, gamma_img):.4f}")


    # HÀM HỖ TRỢ HIỂN THỊ ẢNH (Tối Ưu Garbage Collection)
    def display_cv_image(self, cv_img, label_widget, size=(600, 600)):
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