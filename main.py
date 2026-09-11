#!/usr/bin/env python3
import sys
import os
import subprocess
import threading
from pathlib import Path

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GLib, Gdk

VCP_BRIGHTNESS   = "10"
VCP_CONTRAST     = "12"
VCP_COLOR_PRESET = "14"
VCP_RED          = "16"
VCP_GREEN        = "18"
VCP_BLUE         = "1a"
VCP_VOLUME       = "62"

BASE_DIR = Path(__file__).resolve().parent

class MonitorControllerWindow(Adw.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.set_title("Gigabyte Monitor Controller")
        # Tamanho inicial ideal para caber perfeitamente tanto no 1366x768 quanto no 1920x1080
        self.set_default_size(980, 620)

        self.user_color_preset_active = False
        self.night_mode_active = False
        self.extra_dark_active = False

        self.saved_rgb = {"16": 100, "18": 100, "1a": 100}
        self.saved_brightness = 45
        self.saved_contrast = 50

        self.debounce_timers = {}
        self.scales = {}
        self.value_labels = {}

        self.build_ui()
        self.apply_css()

        threading.Thread(target=self.load_initial_values, daemon=True).start()

    def apply_css(self):
        css_file = BASE_DIR / "style.css"
        if css_file.exists():
            provider = Gtk.CssProvider()
            provider.load_from_path(str(css_file))
            display = Gdk.Display.get_default()
            if display:
                Gtk.StyleContext.add_provider_for_display(
                    display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
                )

    def build_ui(self):
        root_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(root_box)

        header = Adw.HeaderBar()
        header.set_show_title(False)
        root_box.append(header)

        body_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True, vexpand=True)
        root_box.append(body_box)

        # 1. Sidebar
        sidebar = self.build_sidebar()
        body_box.append(sidebar)

        # 2. Content Area
        self.stack = Gtk.Stack()
        self.stack.set_hexpand(True)
        self.stack.set_vexpand(True)

        home_page = self.build_home_page()
        self.stack.add_named(home_page, "home")

        settings_page = self.build_placeholder_page("Configurações", "Opções de inicialização, detecção de portas DDC/CI e calibração.")
        self.stack.add_named(settings_page, "settings")

        about_page = self.build_placeholder_page("Sobre", "Gigabyte Monitor Controller v1.0.0\nControle de hardware via DDC/CI em Linux Wayland.")
        self.stack.add_named(about_page, "about")

        body_box.append(self.stack)

        # 3. Footer
        self.footer = self.build_footer()
        root_box.append(self.footer)

    def build_sidebar(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.add_css_class("sidebar")
        box.set_size_request(200, -1)

        # App Brand
        brand_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        brand_icon = Gtk.Image.new_from_icon_name("video-display-symbolic")
        brand_icon.set_pixel_size(26)
        brand_box.append(brand_icon)

        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        lbl_title = Gtk.Label(label="Gigabyte", xalign=0)
        lbl_title.add_css_class("sidebar-title")
        lbl_sub = Gtk.Label(label="Monitor Controller", xalign=0)
        lbl_sub.add_css_class("sidebar-subtitle")
        text_box.append(lbl_title)
        text_box.append(lbl_sub)
        brand_box.append(text_box)
        box.append(brand_box)

        box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        # Navigation
        nav_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.btn_nav_home = self.create_nav_button("go-home-symbolic", "Início", "home", active=True)
        self.btn_nav_settings = self.create_nav_button("emblem-system-symbolic", "Configurações", "settings")
        self.btn_nav_about = self.create_nav_button("help-about-symbolic", "Sobre", "about")

        nav_box.append(self.btn_nav_home)
        nav_box.append(self.btn_nav_settings)
        nav_box.append(self.btn_nav_about)
        box.append(nav_box)

        spacer = Gtk.Box(vexpand=True)
        box.append(spacer)

        # Monitor preview badge
        device_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        device_box.add_css_class("device-badge-box")

        preview_img = BASE_DIR / "assets" / "monitor_preview.png"
        if preview_img.exists():
            img_widget = Gtk.Image.new_from_file(str(preview_img))
            img_widget.set_pixel_size(100)
            device_box.append(img_widget)
        else:
            def_icon = Gtk.Image.new_from_icon_name("video-display-symbolic")
            def_icon.set_pixel_size(42)
            device_box.append(def_icon)

        lbl_dev = Gtk.Label(label="Gigabyte GS25F2", xalign=0.5)
        lbl_dev.add_css_class("device-name")
        lbl_specs = Gtk.Label(label="Monitor 25\" · Full HD · 180Hz", xalign=0.5)
        lbl_specs.add_css_class("device-specs")

        device_box.append(lbl_dev)
        device_box.append(lbl_specs)
        box.append(device_box)

        return box

    def create_nav_button(self, icon_name, label_text, target_page, active=False):
        btn = Gtk.Button()
        btn.add_css_class("nav-button")
        if active:
            btn.add_css_class("active")

        h_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        img = Gtk.Image.new_from_icon_name(icon_name)
        lbl = Gtk.Label(label=label_text, xalign=0)
        h_box.append(img)
        h_box.append(lbl)
        btn.set_child(h_box)

        btn.connect("clicked", lambda b: self.switch_page(target_page, btn))
        return btn

    def switch_page(self, page_name, active_button):
        self.stack.set_visible_child_name(page_name)
        for b in [self.btn_nav_home, self.btn_nav_settings, self.btn_nav_about]:
            b.remove_css_class("active")
        active_button.add_css_class("active")

    def build_home_page(self):
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content.add_css_class("content-area")
        scrolled.set_child(content)

        # Header Top
        top_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        
        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        page_title = Gtk.Label(label="Controle total do seu monitor", xalign=0)
        page_title.add_css_class("page-title")
        page_sub = Gtk.Label(label="Ajuste o brilho, áudio, cores e muito mais, diretamente do seu desktop.", xalign=0)
        page_sub.add_css_class("page-subtitle")
        title_box.append(page_title)
        title_box.append(page_sub)
        top_box.append(title_box)

        pill_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, valign=Gtk.Align.CENTER, halign=Gtk.Align.END, hexpand=True)
        pill_box.add_css_class("status-badge")
        dot = Gtk.Label(label="●")
        dot.add_css_class("status-dot")
        txt = Gtk.Label(label="Monitor conectado")
        pill_box.append(dot)
        pill_box.append(txt)
        top_box.append(pill_box)

        content.append(top_box)

        # Responsive Grid 2x2
        grid = Gtk.Grid(column_spacing=16, row_spacing=16, hexpand=True)
        grid.set_column_homogeneous(True)
        content.append(grid)

        card1 = self.build_card_essenciais()
        card2 = self.build_card_quarto_escuro()
        card3 = self.build_card_modo_noturno()
        card4 = self.build_card_calibracao_rgb()

        grid.attach(card1, 0, 0, 1, 1)
        grid.attach(card2, 1, 0, 1, 1)
        grid.attach(card3, 0, 1, 1, 1)
        grid.attach(card4, 1, 1, 1, 1)

        return scrolled

    # --- CARD 1: CONTROLES ESSENCIAIS ---
    def build_card_essenciais(self):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        card.add_css_class("feature-card")

        h_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        icon_box = Gtk.Box(halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        icon_box.add_css_class("card-icon-box")
        icon_box.add_css_class("card-icon-blue")
        icon = Gtk.Image.new_from_icon_name("weather-clear-symbolic")
        icon_box.append(icon)
        h_box.append(icon_box)

        t_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        t_box.append(Gtk.Label(label="Controles Essenciais", xalign=0, css_classes=["card-title"]))
        t_box.append(Gtk.Label(label="Ajuste o que você mais usa.", xalign=0, css_classes=["card-desc"]))
        h_box.append(t_box)
        card.append(h_box)

        card.append(self.create_slider_row("Brilho (Backlight)", "display-brightness-symbolic", VCP_BRIGHTNESS, 0, 100, "slider-blue"))
        card.append(self.create_slider_row("Contraste", "contrast-symbolic", VCP_CONTRAST, 0, 100, "slider-purple"))
        card.append(self.create_slider_row("Volume P2", "audio-volume-high-symbolic", VCP_VOLUME, 0, 100, "slider-cyan"))

        return card

    # --- CARD 2: MODO QUARTO ESCURO ---
    def build_card_quarto_escuro(self):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        card.add_css_class("feature-card")

        h_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        icon_box = Gtk.Box(halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        icon_box.add_css_class("card-icon-box")
        icon_box.add_css_class("card-icon-purple")
        icon = Gtk.Image.new_from_icon_name("weather-clear-night-symbolic")
        icon_box.append(icon)
        h_box.append(icon_box)

        t_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1, hexpand=True)
        t_box.append(Gtk.Label(label="Modo Quarto Escuro", xalign=0, css_classes=["card-title"]))
        t_box.append(Gtk.Label(label="Reduza o brilho residual do monitor em ambientes escuros.", xalign=0, css_classes=["card-desc"]))
        h_box.append(t_box)

        sw_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, valign=Gtk.Align.CENTER)
        self.sw_dark = Gtk.Switch()
        self.sw_dark_lbl = Gtk.Label(label="Desativado", css_classes=["switch-label"])
        self.sw_dark.connect("state-set", self.on_switch_dark_toggled)
        sw_box.append(self.sw_dark)
        sw_box.append(self.sw_dark_lbl)
        h_box.append(sw_box)

        card.append(h_box)

        card.append(self.create_slider_row("Atenuação Extra (Dimmer)", "night-light-symbolic", "dimmer", 10, 90, "slider-purple", is_internal=True, default_val=60))

        info_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        info_box.add_css_class("info-banner")
        i_icon = Gtk.Image.new_from_icon_name("dialog-information-symbolic")
        i_lbl = Gtk.Label(
            label="Ao ativar, o monitor será configurado para o modo escuro e a atenuação extra será aplicada, reduzindo ainda mais o brilho residual.",
            wrap=True, xalign=0, hexpand=True
        )
        info_box.append(i_icon)
        info_box.append(i_lbl)
        card.append(info_box)

        return card

    # --- CARD 3: MODO NOTURNO ---
    def build_card_modo_noturno(self):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        card.add_css_class("feature-card")

        h_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        icon_box = Gtk.Box(halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        icon_box.add_css_class("card-icon-box")
        icon_box.add_css_class("card-icon-amber")
        icon = Gtk.Image.new_from_icon_name("find-location-symbolic")
        icon_box.append(icon)
        h_box.append(icon_box)

        t_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1, hexpand=True)
        t_box.append(Gtk.Label(label="Modo Noturno (Luz Azul)", xalign=0, css_classes=["card-title"]))
        t_box.append(Gtk.Label(label="Proteja seus olhos durante a noite.", xalign=0, css_classes=["card-desc"]))
        h_box.append(t_box)

        sw_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, valign=Gtk.Align.CENTER)
        self.sw_night = Gtk.Switch()
        self.sw_night_lbl = Gtk.Label(label="Desativado", css_classes=["switch-label"])
        self.sw_night.connect("state-set", self.on_switch_night_toggled)
        sw_box.append(self.sw_night)
        sw_box.append(self.sw_night_lbl)
        h_box.append(sw_box)

        card.append(h_box)

        card.append(self.create_slider_row("Calor / Âmbar", "weather-clear-symbolic", "warmth", 0, 100, "slider-amber", is_internal=True, default_val=50))

        info_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        info_box.add_css_class("info-banner")
        i_icon = Gtk.Image.new_from_icon_name("dialog-information-symbolic")
        i_lbl = Gtk.Label(
            label="O modo noturno reduz a emissão de luz azul e adiciona um tom mais quente à imagem, ajudando a diminuir o cansaço visual.",
            wrap=True, xalign=0, hexpand=True
        )
        info_box.append(i_icon)
        info_box.append(i_lbl)
        card.append(info_box)

        return card

    # --- CARD 4: CALIBRAÇÃO DE CORES (RGB) ---
    def build_card_calibracao_rgb(self):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        card.add_css_class("feature-card")

        h_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        icon_box = Gtk.Box(halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        icon_box.add_css_class("card-icon-box")
        icon_box.add_css_class("card-icon-rgb")
        icon = Gtk.Image.new_from_icon_name("color-select-symbolic")
        icon_box.append(icon)
        h_box.append(icon_box)

        t_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        t_box.append(Gtk.Label(label="Calibração de Cores", xalign=0, css_classes=["card-title"]))
        t_box.append(Gtk.Label(label="Ajuste o ganho de cada canal de cor (RGB).", xalign=0, css_classes=["card-desc"]))
        h_box.append(t_box)
        card.append(h_box)

        card.append(self.create_slider_row("Vermelho (R)", None, VCP_RED, 0, 100, "slider-red", is_rgb=True, badge_letter="R", badge_class="badge-r"))
        card.append(self.create_slider_row("Verde (G)", None, VCP_GREEN, 0, 100, "slider-green", is_rgb=True, badge_letter="G", badge_class="badge-g"))
        card.append(self.create_slider_row("Azul (B)", None, VCP_BLUE, 0, 100, "slider-blue-solid", is_rgb=True, badge_letter="B", badge_class="badge-b"))

        return card

    def create_slider_row(self, title, icon_name, key, min_val, max_val, color_class, is_internal=False, is_rgb=False, default_val=50, badge_letter=None, badge_class=None):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)

        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        if badge_letter:
            badge = Gtk.Label(label=badge_letter)
            badge.add_css_class("badge-tag")
            badge.add_css_class(badge_class)
            top_row.append(badge)
        elif icon_name:
            ico = Gtk.Image.new_from_icon_name(icon_name)
            top_row.append(ico)

        lbl_title = Gtk.Label(label=title, xalign=0, hexpand=True)
        lbl_title.add_css_class("card-desc")
        top_row.append(lbl_title)

        val_lbl = Gtk.Label(label=f"{default_val}%" if not is_rgb else f"{default_val}")
        val_lbl.add_css_class("val-indicator")
        top_row.append(val_lbl)
        box.append(top_row)

        scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, min_val, max_val, 1)
        scale.set_value(default_val)
        scale.set_draw_value(False)
        scale.set_hexpand(True)
        scale.add_css_class(color_class)
        scale.connect("value-changed", lambda s: self.on_scale_changed(key, s.get_value(), val_lbl, is_internal, is_rgb))
        box.append(scale)

        self.scales[key] = scale
        self.value_labels[key] = val_lbl

        return box

    def build_footer(self):
        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        footer.add_css_class("bottom-bar")

        self.footer_dot = Gtk.Label(label="●")
        self.footer_dot.add_css_class("status-dot")
        self.footer_status = Gtk.Label(label="Sincronizando com o monitor...", xalign=0)
        footer.append(self.footer_dot)
        footer.append(self.footer_status)

        spacer = Gtk.Box(hexpand=True)
        footer.append(spacer)

        dev_lbl = Gtk.Label(label="Gigabyte GS25F2 · DDC/CI via HDMI", xalign=1)
        footer.append(dev_lbl)

        gear = Gtk.Image.new_from_icon_name("emblem-system-symbolic")
        footer.append(gear)

        return footer

    def build_placeholder_page(self, title, desc):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14, halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        lbl = Gtk.Label(label=title)
        lbl.add_css_class("page-title")
        sub = Gtk.Label(label=desc, justify=Gtk.Justification.CENTER)
        sub.add_css_class("card-desc")
        box.append(lbl)
        box.append(sub)
        return box

    def set_status(self, text):
        def _update():
            self.footer_status.set_label(text)
        GLib.idle_add(_update)

    def on_scale_changed(self, key, val, label_widget, is_internal, is_rgb):
        val_int = int(val)
        suffix = "%" if not is_rgb else ""
        label_widget.set_label(f"{val_int}{suffix}")

        if key in self.debounce_timers:
            self.debounce_timers[key].cancel()

        if is_internal:
            if key == "dimmer" and self.extra_dark_active:
                t = threading.Timer(0.2, self.apply_extra_dark, args=(val_int,))
                self.debounce_timers[key] = t
                t.start()
            elif key == "warmth":
                if self.extra_dark_active:
                    dim = int(self.scales["dimmer"].get_value())
                    self.apply_extra_dark(dim)
                elif self.night_mode_active:
                    t = threading.Timer(0.2, self.apply_hardware_night_mode, args=(val_int,))
                    self.debounce_timers[key] = t
                    t.start()
        else:
            if is_rgb and not self.night_mode_active and not self.extra_dark_active:
                self.saved_rgb[key] = val_int
            elif key == VCP_BRIGHTNESS and not self.extra_dark_active:
                self.saved_brightness = val_int
            elif key == VCP_CONTRAST and not self.extra_dark_active:
                self.saved_contrast = val_int

            t = threading.Timer(0.2, self.send_vcp, args=(key, val_int, is_rgb))
            self.debounce_timers[key] = t
            t.start()

    def send_vcp(self, vcp_code, val, is_rgb=False):
        if is_rgb and not self.user_color_preset_active:
            subprocess.run(["ddcutil", "setvcp", VCP_COLOR_PRESET, "0x0b", "--sleep-multiplier", "0.3"], capture_output=True)
            self.user_color_preset_active = True

        self.set_status(f"Enviando ao monitor: VCP 0x{vcp_code} = {val}...")
        res = subprocess.run(
            ["ddcutil", "setvcp", vcp_code, str(val), "--sleep-multiplier", "0.3"],
            capture_output=True, text=True
        )
        if res.returncode == 0:
            self.set_status("Monitor sincronizado com sucesso!")
        else:
            self.set_status("Aviso ao comunicar com o monitor.")

    def on_switch_dark_toggled(self, switch, state):
        self.extra_dark_active = state
        self.sw_dark_lbl.set_label("Ativado" if state else "Desativado")

        if state:
            dim = int(self.scales["dimmer"].get_value())
            threading.Thread(target=self.apply_extra_dark, args=(dim,), daemon=True).start()
        else:
            threading.Thread(target=self.restore_after_extra_dark, daemon=True).start()
        return True

    def on_switch_night_toggled(self, switch, state):
        self.night_mode_active = state
        self.sw_night_lbl.set_label("Ativado" if state else "Desativado")

        if state:
            if self.extra_dark_active:
                dim = int(self.scales["dimmer"].get_value())
                threading.Thread(target=self.apply_extra_dark, args=(dim,), daemon=True).start()
            else:
                warmth = int(self.scales["warmth"].get_value())
                threading.Thread(target=self.apply_hardware_night_mode, args=(warmth,), daemon=True).start()
        else:
            if self.extra_dark_active:
                dim = int(self.scales["dimmer"].get_value())
                threading.Thread(target=self.apply_extra_dark, args=(dim,), daemon=True).start()
            else:
                threading.Thread(target=self.restore_normal_colors, daemon=True).start()
        return True

    def apply_extra_dark(self, dim_pct):
        factor = (100 - dim_pct) / 100.0
        base_r = self.saved_rgb.get("16", 100)
        base_g = self.saved_rgb.get("18", 100)
        base_b = self.saved_rgb.get("1a", 100)

        if self.night_mode_active:
            warmth = int(self.scales["warmth"].get_value()) / 100.0
            base_g = int(100 - (warmth * 25))
            base_b = int(100 - (warmth * 85))

        target_r = max(10, int(base_r * factor))
        target_g = max(10, int(base_g * factor))
        target_b = max(10, int(base_b * factor))
        target_c = max(20, int(self.saved_contrast * factor))

        if not self.user_color_preset_active:
            subprocess.run(["ddcutil", "setvcp", VCP_COLOR_PRESET, "0x0b", "--sleep-multiplier", "0.3"], capture_output=True)
            self.user_color_preset_active = True

        subprocess.run(["ddcutil", "setvcp", VCP_BRIGHTNESS, "0", "--sleep-multiplier", "0.3"], capture_output=True)
        subprocess.run(["ddcutil", "setvcp", VCP_CONTRAST, str(target_c), "--sleep-multiplier", "0.3"], capture_output=True)
        subprocess.run(["ddcutil", "setvcp", VCP_RED, str(target_r), "--sleep-multiplier", "0.3"], capture_output=True)
        subprocess.run(["ddcutil", "setvcp", VCP_GREEN, str(target_g), "--sleep-multiplier", "0.3"], capture_output=True)
        subprocess.run(["ddcutil", "setvcp", VCP_BLUE, str(target_b), "--sleep-multiplier", "0.3"], capture_output=True)

        GLib.idle_add(lambda: self.update_scale_ui(VCP_BRIGHTNESS, 0))
        GLib.idle_add(lambda: self.update_scale_ui(VCP_CONTRAST, target_c))
        GLib.idle_add(lambda: self.update_scale_ui(VCP_RED, target_r))
        GLib.idle_add(lambda: self.update_scale_ui(VCP_GREEN, target_g))
        GLib.idle_add(lambda: self.update_scale_ui(VCP_BLUE, target_b))
        self.set_status(f"Modo Quarto Escuro ativo (Atenuação {dim_pct}%)")

    def restore_after_extra_dark(self):
        br = self.saved_brightness
        ct = self.saved_contrast
        subprocess.run(["ddcutil", "setvcp", VCP_BRIGHTNESS, str(br), "--sleep-multiplier", "0.3"], capture_output=True)
        subprocess.run(["ddcutil", "setvcp", VCP_CONTRAST, str(ct), "--sleep-multiplier", "0.3"], capture_output=True)

        GLib.idle_add(lambda: self.update_scale_ui(VCP_BRIGHTNESS, br))
        GLib.idle_add(lambda: self.update_scale_ui(VCP_CONTRAST, ct))

        if self.night_mode_active:
            warmth = int(self.scales["warmth"].get_value())
            self.apply_hardware_night_mode(warmth)
        else:
            self.restore_normal_colors()

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

        GLib.idle_add(lambda: self.update_scale_ui(VCP_RED, target_r))
        GLib.idle_add(lambda: self.update_scale_ui(VCP_GREEN, target_g))
        GLib.idle_add(lambda: self.update_scale_ui(VCP_BLUE, target_b))
        self.set_status(f"Modo Noturno ativo: Luz azul reduzida em {warmth}%")

    def restore_normal_colors(self):
        r = self.saved_rgb.get("16", 100)
        g = self.saved_rgb.get("18", 100)
        b = self.saved_rgb.get("1a", 100)

        subprocess.run(["ddcutil", "setvcp", VCP_RED, str(r), "--sleep-multiplier", "0.3"], capture_output=True)
        subprocess.run(["ddcutil", "setvcp", VCP_GREEN, str(g), "--sleep-multiplier", "0.3"], capture_output=True)
        subprocess.run(["ddcutil", "setvcp", VCP_BLUE, str(b), "--sleep-multiplier", "0.3"], capture_output=True)

        GLib.idle_add(lambda: self.update_scale_ui(VCP_RED, r))
        GLib.idle_add(lambda: self.update_scale_ui(VCP_GREEN, g))
        GLib.idle_add(lambda: self.update_scale_ui(VCP_BLUE, b))
        self.set_status("Monitor sincronizado com sucesso!")

    def update_scale_ui(self, key, val):
        if key in self.scales:
            self.scales[key].set_value(val)
        if key in self.value_labels:
            suffix = "" if key in [VCP_RED, VCP_GREEN, VCP_BLUE] else "%"
            self.value_labels[key].set_label(f"{int(val)}{suffix}")

    def load_initial_values(self):
        cp_res = subprocess.run(["ddcutil", "getvcp", VCP_COLOR_PRESET, "--terse"], capture_output=True, text=True)
        if cp_res.returncode == 0:
            parts = cp_res.stdout.strip().split()
            if len(parts) >= 4 and parts[3] in ["11", "0x0b"]:
                self.user_color_preset_active = True

        for vcp_code in [VCP_BRIGHTNESS, VCP_CONTRAST, VCP_VOLUME, VCP_RED, VCP_GREEN, VCP_BLUE]:
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
                        GLib.idle_add(self.update_scale_ui, vcp_code, val)
                    except ValueError:
                        pass
        self.set_status("Monitor sincronizado com sucesso!")


class MonitorApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="io.github.diassisfilho.gigabyte_monitor_controller",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = MonitorControllerWindow(application=self)
        win.present()

if __name__ == "__main__":
    app = MonitorApp()
    sys.exit(app.run(sys.argv))
