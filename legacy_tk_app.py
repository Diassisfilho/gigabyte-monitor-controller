#!/usr/bin/env python3
import subprocess
import threading
import tkinter as tk
from tkinter import ttk

VCP_BRIGHTNESS   = "10"
VCP_CONTRAST     = "12"
VCP_COLOR_PRESET = "14"
VCP_RED          = "16"
VCP_GREEN        = "18"
VCP_BLUE         = "1a"
VCP_VOLUME       = "62"

class MonitorControlApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Controle Gigabyte GS25F2")
        self.geometry("500x750")
        self.resizable(False, False)

        self.configure(bg="#1e1e2e")
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", background="#1e1e2e", foreground="#cdd6f4", font=("Sans", 10))
        style.configure("TLabel", background="#1e1e2e", foreground="#cdd6f4")
        style.configure("Header.TLabel", font=("Sans", 13, "bold"), foreground="#89b4fa")
        style.configure("SubHeader.TLabel", font=("Sans", 11, "bold"), foreground="#fab387")
        style.configure("Status.TLabel", font=("Sans", 8), foreground="#a6adc8", background="#181825")
        
        style.configure("NightOn.TButton", font=("Sans", 9, "bold"), background="#fab387", foreground="#11111b")
        style.configure("NightOff.TButton", font=("Sans", 9), background="#313244", foreground="#cdd6f4")
        style.configure("PitchOn.TButton", font=("Sans", 9, "bold"), background="#cba6f7", foreground="#11111b")
        style.configure("PitchOff.TButton", font=("Sans", 9), background="#313244", foreground="#cdd6f4")

        self.sliders = {}
        self.debounce_timers = {}
        self.user_color_preset_active = False
        self.night_mode_active = False
        self.extra_dark_active = False

        # Guarda valores para restauração
        self.saved_rgb = {"16": 100, "18": 100, "1a": 100}
        self.saved_brightness = 45
        self.saved_contrast = 50

        header = ttk.Label(self, text="Controle do Monitor Gigabyte GS25F2", style="Header.TLabel")
        header.pack(pady=10)

        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(fill="both", expand=True, padx=24, pady=2)

        # 1. Controles Padrão
        self.create_slider("Brilho (Lâmpada)", VCP_BRIGHTNESS, 0, 100)
        self.create_slider("Contraste", VCP_CONTRAST, 0, 100)
        self.create_slider("Volume", VCP_VOLUME, 0, 100)

        # 2. Modo Quarto Escuro / Extra Escuro (Dimmer Profundo)
        sep_dark = ttk.Separator(self.main_frame, orient="horizontal")
        sep_dark.pack(fill="x", pady=10)

        dark_header = ttk.Frame(self.main_frame)
        dark_header.pack(fill="x", pady=(0, 4))
        dark_title = ttk.Label(dark_header, text="Modo Quarto Escuro (Ultra Baixo)", style="SubHeader.TLabel")
        dark_title.pack(side="left")

        self.dark_btn = ttk.Button(dark_header, text="Desativado", style="PitchOff.TButton", command=self.toggle_extra_dark)
        self.dark_btn.pack(side="right")

        dark_frame = ttk.Frame(self.main_frame)
        dark_frame.pack(fill="x", pady=4)
        lbl_dark = ttk.Label(dark_frame, text="Atenuação Extra", width=14, anchor="w")
        lbl_dark.pack(side="left")
        self.dim_lbl = ttk.Label(dark_frame, text="60%", width=7, anchor="e")
        self.dim_lbl.pack(side="right")
        self.dim_scale = ttk.Scale(
            dark_frame,
            from_=10,
            to=90,
            orient="horizontal",
            command=self.on_dim_slider_change
        )
        self.dim_scale.set(60)
        self.dim_scale.pack(side="left", fill="x", expand=True, padx=8)

        # 3. Modo Noturno (Filtro Luz Azul)
        sep1 = ttk.Separator(self.main_frame, orient="horizontal")
        sep1.pack(fill="x", pady=10)

        night_header_frame = ttk.Frame(self.main_frame)
        night_header_frame.pack(fill="x", pady=(0, 4))
        night_title = ttk.Label(night_header_frame, text="Modo Noturno (Luz Azul)", style="SubHeader.TLabel")
        night_title.pack(side="left")

        self.night_btn = ttk.Button(night_header_frame, text="Desativado", style="NightOff.TButton", command=self.toggle_night_mode)
        self.night_btn.pack(side="right")

        nl_frame = ttk.Frame(self.main_frame)
        nl_frame.pack(fill="x", pady=4)
        nl_lbl = ttk.Label(nl_frame, text="Calor / Âmbar", width=14, anchor="w")
        nl_lbl.pack(side="left")
        self.warmth_lbl = ttk.Label(nl_frame, text="50%", width=7, anchor="e")
        self.warmth_lbl.pack(side="right")
        self.warmth_scale = ttk.Scale(
            nl_frame,
            from_=0,
            to=100,
            orient="horizontal",
            command=self.on_warmth_slider_change
        )
        self.warmth_scale.set(50)
        self.warmth_scale.pack(side="left", fill="x", expand=True, padx=8)

        # 4. Ajuste RGB Fino
        sep2 = ttk.Separator(self.main_frame, orient="horizontal")
        sep2.pack(fill="x", pady=10)

        rgb_label = ttk.Label(self.main_frame, text="Cores Hardware (RGB Gain)", style="SubHeader.TLabel")
        rgb_label.pack(anchor="w", pady=(0, 4))

        self.create_slider("Vermelho (R)", VCP_RED, 0, 100, is_rgb=True)
        self.create_slider("Verde (G)", VCP_GREEN, 0, 100, is_rgb=True)
        self.create_slider("Azul (B)", VCP_BLUE, 0, 100, is_rgb=True)

        self.status = ttk.Label(self, text="Sincronizando com o monitor...", style="Status.TLabel", relief="sunken", anchor="w", padding=(6, 4))
        self.status.pack(side="bottom", fill="x")

        threading.Thread(target=self.load_initial_values, daemon=True).start()

    def create_slider(self, label_text, vcp_code, min_v, max_v, is_rgb=False):
        frame = ttk.Frame(self.main_frame)
        frame.pack(fill="x", pady=3)

        lbl = ttk.Label(frame, text=label_text, width=14, anchor="w")
        lbl.pack(side="left")

        val_lbl = ttk.Label(frame, text="--", width=7, anchor="e")
        val_lbl.pack(side="right")

        scale = ttk.Scale(
            frame,
            from_=min_v,
            to=max_v,
            orient="horizontal",
            command=lambda v, c=vcp_code, l=val_lbl, rgb=is_rgb: self.on_slider_change(c, v, l, rgb)
        )
        scale.pack(side="left", fill="x", expand=True, padx=8)

        self.sliders[vcp_code] = {"scale": scale, "label": val_lbl}

    def on_slider_change(self, vcp_code, val, label_widget, is_rgb=False):
        val_int = int(float(val))
        label_widget.config(text=str(val_int))

        if is_rgb and not self.night_mode_active and not self.extra_dark_active:
            self.saved_rgb[vcp_code] = val_int
        elif vcp_code == VCP_BRIGHTNESS and not self.extra_dark_active:
            self.saved_brightness = val_int
        elif vcp_code == VCP_CONTRAST and not self.extra_dark_active:
            self.saved_contrast = val_int

        if vcp_code in self.debounce_timers:
            self.debounce_timers[vcp_code].cancel()

        t = threading.Timer(0.2, self.send_vcp, args=(vcp_code, val_int, is_rgb))
        self.debounce_timers[vcp_code] = t
        t.start()

    def send_vcp(self, vcp_code, val, is_rgb=False):
        if is_rgb and not self.user_color_preset_active:
            subprocess.run(["ddcutil", "setvcp", VCP_COLOR_PRESET, "0x0b", "--sleep-multiplier", "0.4"], capture_output=True)
            self.user_color_preset_active = True

        self.set_status(f"Enviando: VCP 0x{vcp_code} = {val}...")
        res = subprocess.run(
            ["ddcutil", "setvcp", vcp_code, str(val), "--sleep-multiplier", "0.4"],
            capture_output=True,
            text=True
        )
        if res.returncode == 0:
            self.set_status("Aplicado com sucesso")
        else:
            err = res.stderr.strip() or res.stdout.strip()
            self.set_status(f"Aviso: {err[:60]}")

    # --- Modo Quarto Escuro (Ultra Baixo) ---
    def toggle_extra_dark(self):
        self.extra_dark_active = not self.extra_dark_active
        if self.extra_dark_active:
            self.dark_btn.config(text="Ativado (ON)", style="PitchOn.TButton")
            dim = int(float(self.dim_scale.get()))
            threading.Thread(target=self.apply_extra_dark, args=(dim,), daemon=True).start()
        else:
            self.dark_btn.config(text="Desativado (OFF)", style="PitchOff.TButton")
            threading.Thread(target=self.restore_after_extra_dark, daemon=True).start()

    def on_dim_slider_change(self, val):
        dim = int(float(val))
        self.dim_lbl.config(text=f"{dim}%")
        if self.extra_dark_active:
            if "dim_debounce" in self.debounce_timers:
                self.debounce_timers["dim_debounce"].cancel()
            t = threading.Timer(0.2, self.apply_extra_dark, args=(dim,))
            self.debounce_timers["dim_debounce"] = t
            t.start()

    def apply_extra_dark(self, dim_pct):
        # 1. Zera o backlight do monitor
        subprocess.run(["ddcutil", "setvcp", VCP_BRIGHTNESS, "0", "--sleep-multiplier", "0.3"], capture_output=True)
        # 2. Diminui o ganho do painel de cristal líquido (LCD Gain)
        # Se dim_pct = 60%, intensidade cai para 40% da luminosidade normal
        factor = (100 - dim_pct) / 100.0
        
        base_r = self.saved_rgb.get("16", 100)
        base_g = self.saved_rgb.get("18", 100)
        base_b = self.saved_rgb.get("1a", 100)

        # Se o modo noturno também estiver ligado, respeita o tom quente
        if self.night_mode_active:
            warmth = int(float(self.warmth_scale.get())) / 100.0
            base_g = int(100 - (warmth * 25))
            base_b = int(100 - (warmth * 85))

        target_r = max(10, int(base_r * factor))
        target_g = max(10, int(base_g * factor))
        target_b = max(10, int(base_b * factor))

        # Reduz contraste para diminuir ofuscamento de fundos brancos
        target_c = max(20, int(self.saved_contrast * factor))

        if not self.user_color_preset_active:
            subprocess.run(["ddcutil", "setvcp", VCP_COLOR_PRESET, "0x0b", "--sleep-multiplier", "0.3"], capture_output=True)
            self.user_color_preset_active = True

        subprocess.run(["ddcutil", "setvcp", VCP_CONTRAST, str(target_c), "--sleep-multiplier", "0.3"], capture_output=True)
        subprocess.run(["ddcutil", "setvcp", VCP_RED, str(target_r), "--sleep-multiplier", "0.3"], capture_output=True)
        subprocess.run(["ddcutil", "setvcp", VCP_GREEN, str(target_g), "--sleep-multiplier", "0.3"], capture_output=True)
        subprocess.run(["ddcutil", "setvcp", VCP_BLUE, str(target_b), "--sleep-multiplier", "0.3"], capture_output=True)

        self.after(0, lambda: self.apply_val(self.sliders[VCP_BRIGHTNESS]["scale"], self.sliders[VCP_BRIGHTNESS]["label"], 0))
        self.after(0, lambda: self.apply_val(self.sliders[VCP_CONTRAST]["scale"], self.sliders[VCP_CONTRAST]["label"], target_c))
        self.after(0, lambda: self.apply_val(self.sliders[VCP_RED]["scale"], self.sliders[VCP_RED]["label"], target_r))
        self.after(0, lambda: self.apply_val(self.sliders[VCP_GREEN]["scale"], self.sliders[VCP_GREEN]["label"], target_g))
        self.after(0, lambda: self.apply_val(self.sliders[VCP_BLUE]["scale"], self.sliders[VCP_BLUE]["label"], target_b))
        self.set_status(f"Modo Quarto Escuro ativo: Brilho 0 + Atenuação {dim_pct}%")

    def restore_after_extra_dark(self):
        self.set_status("Restaurando brilho e contraste anteriores...")
        br = self.saved_brightness
        ct = self.saved_contrast
        subprocess.run(["ddcutil", "setvcp", VCP_BRIGHTNESS, str(br), "--sleep-multiplier", "0.3"], capture_output=True)
        subprocess.run(["ddcutil", "setvcp", VCP_CONTRAST, str(ct), "--sleep-multiplier", "0.3"], capture_output=True)

        self.after(0, lambda: self.apply_val(self.sliders[VCP_BRIGHTNESS]["scale"], self.sliders[VCP_BRIGHTNESS]["label"], br))
        self.after(0, lambda: self.apply_val(self.sliders[VCP_CONTRAST]["scale"], self.sliders[VCP_CONTRAST]["label"], ct))

        if self.night_mode_active:
            warmth = int(float(self.warmth_scale.get()))
            self.apply_hardware_night_mode(warmth)
        else:
            self.restore_normal_colors()

    # --- Modo Noturno (Luz Azul) ---
    def on_warmth_slider_change(self, val):
        warmth = int(float(val))
        self.warmth_lbl.config(text=f"{warmth}%")
        if self.night_mode_active and not self.extra_dark_active:
            if "night_debounce" in self.debounce_timers:
                self.debounce_timers["night_debounce"].cancel()
            t = threading.Timer(0.2, self.apply_hardware_night_mode, args=(warmth,))
            self.debounce_timers["night_debounce"] = t
            t.start()
        elif self.extra_dark_active:
            dim = int(float(self.dim_scale.get()))
            self.apply_extra_dark(dim)

    def toggle_night_mode(self):
        self.night_mode_active = not self.night_mode_active
        if self.night_mode_active:
            self.night_btn.config(text="Ativado (ON)", style="NightOn.TButton")
            if self.extra_dark_active:
                dim = int(float(self.dim_scale.get()))
                threading.Thread(target=self.apply_extra_dark, args=(dim,), daemon=True).start()
            else:
                warmth = int(float(self.warmth_scale.get()))
                threading.Thread(target=self.apply_hardware_night_mode, args=(warmth,), daemon=True).start()
        else:
            self.night_btn.config(text="Desativado (OFF)", style="NightOff.TButton")
            if self.extra_dark_active:
                dim = int(float(self.dim_scale.get()))
                threading.Thread(target=self.apply_extra_dark, args=(dim,), daemon=True).start()
            else:
                threading.Thread(target=self.restore_normal_colors, daemon=True).start()

    def apply_hardware_night_mode(self, warmth):
        factor = warmth / 100.0
        target_r = 100
        target_g = int(100 - (factor * 25))
        target_b = int(100 - (factor * 85))

        if not self.user_color_preset_active:
            subprocess.run(["ddcutil", "setvcp", VCP_COLOR_PRESET, "0x0b", "--sleep-multiplier", "0.3"], capture_output=True)
            self.user_color_preset_active = True

        subprocess.run(["ddcutil", "setvcp", VCP_RED, str(target_r), "--sleep-multiplier", "0.3"], capture_output=True)
        subprocess.run(["ddcutil", "setvcp", VCP_GREEN, str(target_g), "--sleep-multiplier", "0.3"], capture_output=True)
        subprocess.run(["ddcutil", "setvcp", VCP_BLUE, str(target_b), "--sleep-multiplier", "0.3"], capture_output=True)

        self.after(0, lambda: self.apply_val(self.sliders[VCP_RED]["scale"], self.sliders[VCP_RED]["label"], target_r))
        self.after(0, lambda: self.apply_val(self.sliders[VCP_GREEN]["scale"], self.sliders[VCP_GREEN]["label"], target_g))
        self.after(0, lambda: self.apply_val(self.sliders[VCP_BLUE]["scale"], self.sliders[VCP_BLUE]["label"], target_b))
        self.set_status(f"Modo Noturno ativo: Luz azul reduzida em {warmth}%")

    def restore_normal_colors(self):
        self.set_status("Restaurando cores normais...")
        r = self.saved_rgb.get("16", 100)
        g = self.saved_rgb.get("18", 100)
        b = self.saved_rgb.get("1a", 100)

        subprocess.run(["ddcutil", "setvcp", VCP_RED, str(r), "--sleep-multiplier", "0.3"], capture_output=True)
        subprocess.run(["ddcutil", "setvcp", VCP_GREEN, str(g), "--sleep-multiplier", "0.3"], capture_output=True)
        subprocess.run(["ddcutil", "setvcp", VCP_BLUE, str(b), "--sleep-multiplier", "0.3"], capture_output=True)

        self.after(0, lambda: self.apply_val(self.sliders[VCP_RED]["scale"], self.sliders[VCP_RED]["label"], r))
        self.after(0, lambda: self.apply_val(self.sliders[VCP_GREEN]["scale"], self.sliders[VCP_GREEN]["label"], g))
        self.after(0, lambda: self.apply_val(self.sliders[VCP_BLUE]["scale"], self.sliders[VCP_BLUE]["label"], b))
        self.set_status("Cores normais restauradas")

    def load_initial_values(self):
        cp_res = subprocess.run(["ddcutil", "getvcp", VCP_COLOR_PRESET, "--terse"], capture_output=True, text=True)
        if cp_res.returncode == 0:
            parts = cp_res.stdout.strip().split()
            if len(parts) >= 4 and parts[3] in ["11", "0x0b"]:
                self.user_color_preset_active = True

        for vcp_code, item in self.sliders.items():
            res = subprocess.run(["ddcutil", "getvcp", vcp_code, "--terse"], capture_output=True, text=True)
            if res.returncode == 0:
                parts = res.stdout.strip().split()
                if len(parts) >= 4:
                    try:
                        val = int(parts[3])
                        if vcp_code in ["16", "18", "1a"]:
                            self.saved_rgb[vcp_code] = val
                        elif vcp_code == VCP_BRIGHTNESS:
                            self.saved_brightness = val
                        elif vcp_code == VCP_CONTRAST:
                            self.saved_contrast = val
                        self.after(0, lambda s=item["scale"], l=item["label"], v=val: self.apply_val(s, l, v))
                    except ValueError:
                        pass
        self.set_status("Pronto e sincronizado!")

    def apply_val(self, scale, label, val):
        scale.set(val)
        label.config(text=str(val))

    def set_status(self, text):
        self.after(0, lambda: self.status.config(text=text))

if __name__ == "__main__":
    app = MonitorControlApp()
    app.mainloop()
