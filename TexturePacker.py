import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from PIL import Image, ImageTk
import os

# --- Constants ---
MAX_UNDO_STEPS = 32
FILTERS = {
    "Nearest Neighbor": Image.Resampling.NEAREST,
    "Bilinear": Image.Resampling.BILINEAR,
    "Bicubic": Image.Resampling.BICUBIC,
    "Lanczos": Image.Resampling.LANCZOS,
    "Box": Image.Resampling.BOX,
}

class TexturePackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Pro Texture Packer & Channel Manager")
        self.root.geometry("1100x750")
        
        # --- State Management ---
        self.current_image = None  # The processed PIL Image
        self.undo_stack = []       # List of PIL Images
        
        # --- UI Setup ---
        self._setup_styles()
        self._create_layout()
        
    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TButton", padding=5, font=('Helvetica', 10))
        style.configure("TLabel", font=('Helvetica', 10))
        style.configure("Header.TLabel", font=('Helvetica', 12, 'bold'))

    def _create_layout(self):
        # Top Bar (Session & Undo)
        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.pack(fill=tk.X)
        
        ttk.Button(top_frame, text="New Session", command=self.new_session).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="Undo", command=self.undo_action).pack(side=tk.LEFT, padx=5)
        ttk.Label(top_frame, text="(Max 32 steps)", font=("Arial", 8)).pack(side=tk.LEFT)

        # Main Content Area (Split into Controls and Preview)
        content_frame = ttk.Frame(self.root)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Left Side: Controls (Tabs)
        control_frame = ttk.Frame(content_frame, width=400)
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        self.notebook = ttk.Notebook(control_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Channel Packer
        self.tab_packer = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_packer, text="Channel Packer")
        self._init_packer_tab()

        # Tab 2: Inject Alpha
        self.tab_alpha = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_alpha, text="Inject Alpha")
        self._init_alpha_tab()

        # Tab 3: Channel Splitter
        self.tab_split = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_split, text="Channel Splitter")
        self._init_splitter_tab()

        # Right Side: Preview
        preview_frame = ttk.LabelFrame(content_frame, text="Result Preview")
        preview_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.preview_label = ttk.Label(preview_frame, text="No result generated yet.")
        self.preview_label.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Bottom Bar (Export)
        bottom_frame = ttk.LabelFrame(self.root, text="Export Settings", padding=10)
        bottom_frame.pack(fill=tk.X, padx=10, pady=10)
        self._init_export_controls(bottom_frame)

    # ----------------------------------------------------------------
    # TAB 1: CHANNEL PACKER
    # ----------------------------------------------------------------
    def _init_packer_tab(self):
        ttk.Label(self.tab_packer, text="Assign Grayscale Maps to Channels", style="Header.TLabel").pack(pady=(0, 10))
        
        self.pack_paths = {'R': tk.StringVar(), 'G': tk.StringVar(), 'B': tk.StringVar(), 'A': tk.StringVar()}
        
        for channel in ['R', 'G', 'B', 'A']:
            frame = ttk.Frame(self.tab_packer)
            frame.pack(fill=tk.X, pady=2)
            ttk.Label(frame, text=f"{channel} Channel:", width=10).pack(side=tk.LEFT)
            ttk.Entry(frame, textvariable=self.pack_paths[channel]).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            ttk.Button(frame, text="...", width=3, command=lambda c=channel: self.browse_file(self.pack_paths[c])).pack(side=tk.LEFT)

        # Alpha Fallback Options
        ttk.Separator(self.tab_packer, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        ttk.Label(self.tab_packer, text="If Alpha Channel is Empty:", style="Header.TLabel").pack(anchor='w')
        
        self.alpha_fallback = tk.StringVar(value="white")
        ttk.Radiobutton(self.tab_packer, text="Fill White (Opaque)", variable=self.alpha_fallback, value="white").pack(anchor='w')
        ttk.Radiobutton(self.tab_packer, text="Fill Black (Transparent)", variable=self.alpha_fallback, value="black").pack(anchor='w')

        ttk.Button(self.tab_packer, text="Execute Pack", command=self.process_packer).pack(pady=20, fill=tk.X)

    def process_packer(self):
        # Logic: Use Red Channel as the "Master" size, or G/B if R is missing
        paths = {k: v.get() for k, v in self.pack_paths.items()}
        
        # Find a master image to determine size
        master_img = None
        for key in ['R', 'G', 'B', 'A']:
            if os.path.exists(paths[key]):
                master_img = Image.open(paths[key])
                break
        
        if not master_img:
            messagebox.showerror("Error", "Please select at least one texture input.")
            return

        target_size = master_img.size
        mode = master_img.mode
        
        channels = []
        for char in ['R', 'G', 'B']:
            if os.path.exists(paths[char]):
                img = Image.open(paths[char]).convert("L") # Force grayscale
                img = img.resize(target_size, Image.Resampling.LANCZOS) # Match master size
                channels.append(img)
            else:
                # Default to black if RGB channel missing
                channels.append(Image.new("L", target_size, 0))

        # Handle Alpha
        if os.path.exists(paths['A']):
            img = Image.open(paths['A']).convert("L")
            img = img.resize(target_size, Image.Resampling.LANCZOS)
            channels.append(img)
        else:
            val = 255 if self.alpha_fallback.get() == "white" else 0
            channels.append(Image.new("L", target_size, val))

        # Merge
        result = Image.merge("RGBA", tuple(channels))
        self.push_to_history(result)

    # ----------------------------------------------------------------
    # TAB 2: INJECT ALPHA
    # ----------------------------------------------------------------
    def _init_alpha_tab(self):
        ttk.Label(self.tab_alpha, text="Inject Alpha into RGB Texture", style="Header.TLabel").pack(pady=(0, 10))
        
        self.inject_rgb_path = tk.StringVar()
        self.inject_alpha_path = tk.StringVar()

        # RGB Input
        ttk.Label(self.tab_alpha, text="Base RGB Texture:").pack(anchor='w')
        f1 = ttk.Frame(self.tab_alpha)
        f1.pack(fill=tk.X, pady=2)
        ttk.Entry(f1, textvariable=self.inject_rgb_path).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(f1, text="...", width=3, command=lambda: self.browse_file(self.inject_rgb_path)).pack(side=tk.LEFT)

        ttk.Separator(self.tab_alpha, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # Alpha Input
        ttk.Label(self.tab_alpha, text="Source for Alpha:").pack(anchor='w')
        
        self.alpha_mode = tk.StringVar(value="texture")
        
        # Option A: Texture
        ttk.Radiobutton(self.tab_alpha, text="Use Texture File", variable=self.alpha_mode, value="texture").pack(anchor='w')
        f2 = ttk.Frame(self.tab_alpha)
        f2.pack(fill=tk.X, pady=(0, 5), padx=20)
        ttk.Entry(f2, textvariable=self.inject_alpha_path).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(f2, text="...", width=3, command=lambda: self.browse_file(self.inject_alpha_path)).pack(side=tk.LEFT)

        # Option B: Constant Value
        ttk.Radiobutton(self.tab_alpha, text="Use Constant Value (0-255)", variable=self.alpha_mode, value="value").pack(anchor='w')
        self.alpha_val_entry = ttk.Entry(self.tab_alpha)
        self.alpha_val_entry.insert(0, "255")
        self.alpha_val_entry.pack(anchor='w', padx=20)

        ttk.Button(self.tab_alpha, text="Execute Injection", command=self.process_inject).pack(pady=20, fill=tk.X)

    def process_inject(self):
        if not os.path.exists(self.inject_rgb_path.get()):
            messagebox.showerror("Error", "Please select a Base RGB texture.")
            return

        try:
            rgb_img = Image.open(self.inject_rgb_path.get()).convert("RGB")
            target_size = rgb_img.size

            alpha_channel = None

            if self.alpha_mode.get() == "texture":
                if not os.path.exists(self.inject_alpha_path.get()):
                    messagebox.showerror("Error", "Please select an Alpha texture.")
                    return
                alpha_img = Image.open(self.inject_alpha_path.get()).convert("L")
                alpha_channel = alpha_img.resize(target_size, Image.Resampling.LANCZOS)
            else:
                # Constant Value
                try:
                    val = int(self.alpha_val_entry.get())
                    val = max(0, min(255, val)) # Clamp
                    alpha_channel = Image.new("L", target_size, val)
                except ValueError:
                    messagebox.showerror("Error", "Alpha value must be an integer (0-255).")
                    return

            rgb_img.putalpha(alpha_channel)
            self.push_to_history(rgb_img)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to process: {e}")

    # ----------------------------------------------------------------
    # TAB 3: CHANNEL SPLITTER
    # ----------------------------------------------------------------
    def _init_splitter_tab(self):
        ttk.Label(self.tab_split, text="Split RGB(A) into Grayscale", style="Header.TLabel").pack(pady=(0, 10))
        
        self.split_src_path = tk.StringVar()
        ttk.Label(self.tab_split, text="Source Image:").pack(anchor='w')
        f1 = ttk.Frame(self.tab_split)
        f1.pack(fill=tk.X, pady=2)
        ttk.Entry(f1, textvariable=self.split_src_path).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(f1, text="...", width=3, command=lambda: self.browse_file(self.split_src_path)).pack(side=tk.LEFT)

        ttk.Separator(self.tab_split, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        ttk.Label(self.tab_split, text="Select Channel to Extract:").pack(anchor='w')
        self.channel_to_extract = tk.StringVar(value="R")
        
        f_btns = ttk.Frame(self.tab_split)
        f_btns.pack(fill=tk.X, pady=5)
        ttk.Radiobutton(f_btns, text="Red", variable=self.channel_to_extract, value="R").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(f_btns, text="Green", variable=self.channel_to_extract, value="G").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(f_btns, text="Blue", variable=self.channel_to_extract, value="B").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(f_btns, text="Alpha", variable=self.channel_to_extract, value="A").pack(side=tk.LEFT, padx=5)

        ttk.Button(self.tab_split, text="Extract Channel", command=self.process_split).pack(pady=20, fill=tk.X)

    def process_split(self):
        if not os.path.exists(self.split_src_path.get()):
            messagebox.showerror("Error", "Please select a source image.")
            return

        try:
            img = Image.open(self.split_src_path.get())
            
            # Ensure we have the data required
            if self.channel_to_extract.get() == "A":
                img = img.convert("RGBA")
            else:
                img = img.convert("RGB")

            bands = img.split()
            
            target = self.channel_to_extract.get()
            result = None
            
            if target == "R": result = bands[0]
            elif target == "G": result = bands[1]
            elif target == "B": result = bands[2]
            elif target == "A": 
                if len(bands) > 3:
                    result = bands[3]
                else:
                    # Create white alpha if none exists
                    result = Image.new("L", img.size, 255)
            
            self.push_to_history(result)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to split: {e}")


    # ----------------------------------------------------------------
    # EXPORT CONTROLS
    # ----------------------------------------------------------------
    def _init_export_controls(self, parent):
        # Filter Selection
        ttk.Label(parent, text="Filter:").pack(side=tk.LEFT, padx=5)
        self.filter_var = tk.StringVar(value="Lanczos")
        ttk.OptionMenu(parent, self.filter_var, "Lanczos", *FILTERS.keys()).pack(side=tk.LEFT, padx=5)

        # Resolution Selection
        ttk.Label(parent, text="Resolution:").pack(side=tk.LEFT, padx=(20, 5))
        self.res_mode = tk.StringVar(value="Original")
        
        def toggle_res_entries():
            state = "normal" if self.res_mode.get() == "Custom" else "disabled"
            self.width_entry.config(state=state)
            self.height_entry.config(state=state)

        ttk.Radiobutton(parent, text="Original", variable=self.res_mode, value="Original", command=toggle_res_entries).pack(side=tk.LEFT)
        ttk.Radiobutton(parent, text="Custom", variable=self.res_mode, value="Custom", command=toggle_res_entries).pack(side=tk.LEFT, padx=5)
        
        self.width_entry = ttk.Entry(parent, width=6, state="disabled")
        self.width_entry.pack(side=tk.LEFT)
        ttk.Label(parent, text="x").pack(side=tk.LEFT)
        self.height_entry = ttk.Entry(parent, width=6, state="disabled")
        self.height_entry.pack(side=tk.LEFT)

        # Export Button
        ttk.Button(parent, text="Save Image As...", command=self.export_image).pack(side=tk.RIGHT, padx=10)

    def export_image(self):
        if not self.current_image:
            messagebox.showwarning("Warning", "No image to export.")
            return

        # Ask for save path
        file_types = [
            ("PNG", "*.png"), 
            ("Targa", "*.tga"), 
            ("JPEG", "*.jpg *.jpeg"), 
            ("TIFF", "*.tif *.tiff"),
            ("All Files", "*.*")
        ]
        
        save_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=file_types)
        if not save_path:
            return

        # Apply Resolution Changes
        img_to_save = self.current_image.copy()
        
        if self.res_mode.get() == "Custom":
            try:
                w = int(self.width_entry.get())
                h = int(self.height_entry.get())
                filter_type = FILTERS[self.filter_var.get()]
                img_to_save = img_to_save.resize((w, h), filter_type)
            except ValueError:
                messagebox.showerror("Error", "Invalid Resolution Dimensions")
                return

        # Handle format specific issues (JPEG no Alpha)
        ext = os.path.splitext(save_path)[1].lower()
        if ext in ['.jpg', '.jpeg'] and img_to_save.mode == 'RGBA':
            img_to_save = img_to_save.convert("RGB")

        try:
            img_to_save.save(save_path)
            messagebox.showinfo("Success", f"Saved to {save_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Save failed: {e}")

    # ----------------------------------------------------------------
    # UTILITIES
    # ----------------------------------------------------------------
    def browse_file(self, string_var):
        filename = filedialog.askopenfilename(filetypes=[("Images", "*.png;*.jpg;*.tga;*.tif;*.tiff;*.bmp")])
        if filename:
            string_var.set(filename)

    def push_to_history(self, image):
        """Adds image to undo stack and updates view"""
        if len(self.undo_stack) >= MAX_UNDO_STEPS:
            self.undo_stack.pop(0) # Remove oldest
        
        self.undo_stack.append(image)
        self.current_image = image
        self.update_preview()

    def undo_action(self):
        if len(self.undo_stack) > 1:
            self.undo_stack.pop() # Remove current state
            self.current_image = self.undo_stack[-1] # Set to previous
            self.update_preview()
            messagebox.showinfo("Undo", "Reverted to previous state.")
        elif len(self.undo_stack) == 1:
             # Clear everything
             self.undo_stack.pop()
             self.current_image = None
             self.preview_label.config(image='', text="No result generated yet.")
        else:
            messagebox.showinfo("Info", "Nothing to undo.")

    def new_session(self):
        confirm = messagebox.askyesno("New Session", "Are you sure? This will clear all history.")
        if confirm:
            self.undo_stack.clear()
            self.current_image = None
            self.preview_label.config(image='', text="No result generated yet.")
            # Reset fields
            for v in self.pack_paths.values(): v.set("")
            self.inject_rgb_path.set("")
            self.inject_alpha_path.set("")
            self.split_src_path.set("")

    def update_preview(self):
        if not self.current_image:
            return
        
        # Create a thumbnail for display
        display_img = self.current_image.copy()
        display_img.thumbnail((500, 500)) # Fit in preview window
        
        # Convert to TK format
        self.tk_img = ImageTk.PhotoImage(display_img)
        self.preview_label.config(image=self.tk_img, text="")

# --- Main Execution ---
if __name__ == "__main__":
    root = tk.Tk()
    app = TexturePackerApp(root)
    root.mainloop()