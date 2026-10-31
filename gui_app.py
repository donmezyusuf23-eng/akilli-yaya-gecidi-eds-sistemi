"""
Akıllı Yaya Geçidi Kural İhlali Tespit Sistemi
Modern EDS Komuta ve Kontrol Merkezi (GUI)
--------------------------------------------------------------
Tek tıkla çalıştırılabilen, canlı kamera ve video akışını yapay zekâ
(YOLOv8 + ByteTrack) ile denetleyen, gerçek zamanlı hız analizi yapan,
sesli uyarı veren ve resmi Excel tutanağı üreten profesyonel EDS arayüzü.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
from PIL import Image, ImageTk
import numpy as np
import os
import json
import time
from datetime import datetime
import threading
import winsound
from ultralytics import YOLO
from rapor_yoneticisi import RaporYoneticisi
from tespit_cekirdegi import YayaGecidiCekirdek
from plaka_okuyucu import PlakaOkuyucu

class EDSPanelUygulamasi:
    def __init__(self, pencere):
        self.pencere = pencere
        self.pencere.title("Akıllı Yaya Geçidi EDS Kontrol Merkezi - v2.0")
        self.pencere.geometry("1280x800")
        self.pencere.configure(bg="#0b0f19")
        self.pencere.minsize(1100, 700)

        # Proje dizinleri
        self.ana_dizin = os.path.dirname(os.path.abspath(__file__))
        self.model_yolu = os.path.join(self.ana_dizin, "yolov8n.pt")
        self.cikti_dizini = os.path.join(self.ana_dizin, "output")
        self.ihlal_klasoru = os.path.join(self.cikti_dizini, "ihlaller")
        os.makedirs(self.ihlal_klasoru, exist_ok=True)

        # Raporlama Motoru
        self.raporcu = RaporYoneticisi(self.cikti_dizini)
        self.plaka_okuyucu = PlakaOkuyucu(gpu=False)
        threading.Thread(target=self.plaka_okuyucu._model_yukle, daemon=True).start()

        # Durum Değişkenleri
        self.model = None
        self.cap = None
        self.calisiyor = False
        self.thread = None
        self.toplam_ihlal = 0
        self.ses_aktif = True  # Sesli ikaz açık/kapalı

        # Özel Bölge Koordinatları (Kalibrasyon)
        self.ayar_dosyasi = os.path.join(self.ana_dizin, "bolge_ayarlari.json")
        self.ozel_yaya_oranlari = None
        self.ozel_durma_oranlari = None
        self.son_acilan_kaynak = os.path.join(self.ana_dizin, "data", "ornek_trafik.mp4")
        self._ayarlari_yukle()

        # Arayüzü İnşa Et
        self._arayuz_olustur()

        # Canlı Dijital Saat Döngüsü
        self._saat_guncelle()

        # Modeli arka planda yükle
        threading.Thread(target=self._model_yukle, daemon=True).start()

        # Kapatma temizliği
        self.pencere.protocol("WM_DELETE_WINDOW", self._cikis_yap)

    def _hover_efekti(self, buton, normal_bg, hover_bg):
        """Butonların üzerine fare gelince parlamasını sağlar."""
        buton.bind("<Enter>", lambda e: buton.config(bg=hover_bg) if str(buton['state']) != 'disabled' else None)
        buton.bind("<Leave>", lambda e: buton.config(bg=normal_bg) if str(buton['state']) != 'disabled' else None)

    def _saat_guncelle(self):
        """Üst bardaki canlı dijital saati saniye saniye günceller."""
        simdi = datetime.now()
        tarih_metni = simdi.strftime("%d.%m.%Y")
        saat_metni = simdi.strftime("%H:%M:%S")
        self.lbl_saat.config(text=f"📅 {tarih_metni}  |  ⏰ {saat_metni}")
        self.pencere.after(1000, self._saat_guncelle)

    def _log_ekle(self, mesaj, tur="bilgi"):
        """Canlı olay akışı konsoluna yeni bir satır ekler."""
        zaman = datetime.now().strftime("%H:%M:%S")
        renk_tag = tur
        self.txt_log.config(state=tk.NORMAL)
        self.txt_log.insert(tk.END, f"[{zaman}] {mesaj}\n", renk_tag)
        self.txt_log.see(tk.END)
        self.txt_log.config(state=tk.DISABLED)

    def _model_yukle(self):
        self._log_ekle("YOLOv8 Yapay Zekâ Modeli belleğe yükleniyor...", "bilgi")
        self.durum_yaz("YOLOv8 Yükleniyor...", "#f59e0b")
        try:
            self.model = YOLO(self.model_yolu)
            self.durum_yaz("Sistem Hazır", "#10b981")
            self._log_ekle("YOLOv8n derin öğrenme modeli ve ByteTrack hazır.", "basari")
        except Exception as e:
            self.durum_yaz(f"Model Hatası: {e}", "#ef4444")
            self._log_ekle(f"Model yüklenirken hata oluştu: {e}", "hata")

    def _arayuz_olustur(self):
        # 1. ÜST BAŞLIK BARI (HEADER)
        baslik_frame = tk.Frame(self.pencere, bg="#111827", height=65, bd=1, relief=tk.FLAT)
        baslik_frame.pack(side=tk.TOP, fill=tk.X)

        # Sol Başlık ve Rozet
        sol_baslik = tk.Frame(baslik_frame, bg="#111827")
        sol_baslik.pack(side=tk.LEFT, padx=20, pady=12)

        tk.Label(
            sol_baslik, 
            text="🚦 AKILLI YAYA GEÇİDİ EDS DENETİM MERKEZİ", 
            font=("Segoe UI", 13, "bold"), 
            fg="#f8fafc", 
            bg="#111827"
        ).pack(side=tk.LEFT)

        tk.Label(
            sol_baslik,
            text=" v2.0 PRO ",
            font=("Segoe UI", 8, "bold"),
            fg="#06b6d4",
            bg="#082f49",
            bd=1,
            relief=tk.SOLID
        ).pack(side=tk.LEFT, padx=10)

        # Orta Dijital Saat
        self.lbl_saat = tk.Label(
            baslik_frame,
            text="📅 --.--.----  |  ⏰ --:--:--",
            font=("Consolas", 10, "bold"),
            fg="#94a3b8",
            bg="#111827"
        )
        self.lbl_saat.pack(side=tk.LEFT, expand=True)

        # Sağ Durum Rozeti
        sag_durum_frame = tk.Frame(baslik_frame, bg="#111827")
        sag_durum_frame.pack(side=tk.RIGHT, padx=20)

        self.lbl_durum_isik = tk.Label(
            sag_durum_frame,
            text="●",
            font=("Segoe UI", 12),
            fg="#f59e0b",
            bg="#111827"
        )
        self.lbl_durum_isik.pack(side=tk.LEFT, padx=(0, 5))

        self.lbl_durum = tk.Label(
            sag_durum_frame, 
            text="Başlatılıyor...", 
            font=("Segoe UI", 10, "bold"), 
            fg="#f59e0b", 
            bg="#111827"
        )
        self.lbl_durum.pack(side=tk.LEFT)

        # 2. ALT BUTON BARI (COMMAND DOCK)
        kontrol_frame = tk.Frame(self.pencere, bg="#111827", height=70, bd=1, relief=tk.FLAT)
        kontrol_frame.pack(side=tk.BOTTOM, fill=tk.X)

        btn_stil = {
            "font": ("Segoe UI", 9, "bold"),
            "relief": tk.FLAT,
            "cursor": "hand2",
            "padx": 13,
            "pady": 7,
            "bd": 0
        }

        # Sol Buton Grubu (Kaynak ve Denetim)
        sol_btn_frame = tk.Frame(kontrol_frame, bg="#111827")
        sol_btn_frame.pack(side=tk.LEFT, padx=15, pady=12)

        self.btn_ornek = tk.Button(sol_btn_frame, text="▶️ Demo Video", bg="#1e293b", fg="#f8fafc",
                                   command=self._ornek_video_baslat, **btn_stil)
        self.btn_ornek.pack(side=tk.LEFT, padx=4)
        self._hover_efekti(self.btn_ornek, "#1e293b", "#334155")

        self.btn_dosya = tk.Button(sol_btn_frame, text="📁 Video Seç", bg="#3b82f6", fg="#ffffff",
                                   command=self._video_dosyasi_sec, **btn_stil)
        self.btn_dosya.pack(side=tk.LEFT, padx=4)
        self._hover_efekti(self.btn_dosya, "#3b82f6", "#2563eb")

        self.btn_webcam = tk.Button(sol_btn_frame, text="📹 Canlı Kamera", bg="#0284c7", fg="#ffffff",
                                    command=self._webcam_baslat, **btn_stil)
        self.btn_webcam.pack(side=tk.LEFT, padx=4)
        self._hover_efekti(self.btn_webcam, "#0284c7", "#0369a1")

        self.btn_durdur = tk.Button(sol_btn_frame, text="⏹️ Durdur", bg="#ef4444", fg="#ffffff",
                                    command=self._durdur, state=tk.DISABLED, **btn_stil)
        self.btn_durdur.pack(side=tk.LEFT, padx=8)
        self._hover_efekti(self.btn_durdur, "#ef4444", "#dc2626")

        # Orta Buton Grubu (Kalibrasyon)
        orta_btn_frame = tk.Frame(kontrol_frame, bg="#111827")
        orta_btn_frame.pack(side=tk.LEFT, padx=10, pady=12)

        self.btn_kalibre = tk.Button(orta_btn_frame, text="🎯 Bölgeleri Çiz", bg="#8b5cf6", fg="#ffffff",
                                     command=self._fareyle_bolge_ciz, **btn_stil)
        self.btn_kalibre.pack(side=tk.LEFT, padx=4)
        self._hover_efekti(self.btn_kalibre, "#8b5cf6", "#7c3aed")

        self.btn_sifirla = tk.Button(orta_btn_frame, text="🔄 Sıfırla", bg="#334155", fg="#cbd5e1",
                                     command=self._bolgeleri_sifirla, **btn_stil)
        self.btn_sifirla.pack(side=tk.LEFT, padx=4)
        self._hover_efekti(self.btn_sifirla, "#334155", "#475569")

        # Sağ Buton Grubu (Çıktılar & Ses)
        sag_btn_frame = tk.Frame(kontrol_frame, bg="#111827")
        sag_btn_frame.pack(side=tk.RIGHT, padx=15, pady=12)

        self.btn_ses = tk.Button(sag_btn_frame, text="🔊 Ses: AÇIK", bg="#f59e0b", fg="#000000",
                                 command=self._ses_degistir, **btn_stil)
        self.btn_ses.pack(side=tk.LEFT, padx=4)
        self._hover_efekti(self.btn_ses, "#f59e0b", "#d97706")

        self.btn_rapor = tk.Button(sag_btn_frame, text="📋 Excel Tutanağı", bg="#10b981", fg="#ffffff",
                                   command=self._excel_raporunu_ac, **btn_stil)
        self.btn_rapor.pack(side=tk.LEFT, padx=4)
        self._hover_efekti(self.btn_rapor, "#10b981", "#059669")

        self.btn_klasor = tk.Button(sag_btn_frame, text="📂 Kanıt Klasörü", bg="#1e293b", fg="#f8fafc",
                                    command=self._ihlal_klasorunu_ac, **btn_stil)
        self.btn_klasor.pack(side=tk.LEFT, padx=4)
        self._hover_efekti(self.btn_klasor, "#1e293b", "#334155")

        # 3. ORTA ALAN: SOLDA VİDEO EKRANI, SAĞDA PANEL
        orta_frame = tk.Frame(self.pencere, bg="#0b0f19")
        orta_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=16, pady=12)

        # Sağ Panel: Canlı İstatistikler + Kanıt Kartı + Canlı Konsol
        sag_panel = tk.Frame(orta_frame, bg="#111827", width=340, bd=1, relief=tk.SOLID)
        sag_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(12, 0))
        sag_panel.pack_propagate(False)

        # Kart 1: İhlal Sayacı Kartı
        kart1 = tk.Frame(sag_panel, bg="#1f2937", bd=1, relief=tk.SOLID)
        kart1.pack(fill=tk.X, padx=12, pady=(12, 6))

        tk.Label(kart1, text="🚨 TOPLAM KURAL İHLALİ", font=("Segoe UI", 9, "bold"), fg="#f87171", bg="#1f2937").pack(anchor=tk.W, padx=12, pady=(8, 0))
        self.lbl_ihlal_sayisi = tk.Label(kart1, text="0", font=("Segoe UI", 24, "bold"), fg="#ef4444", bg="#1f2937")
        self.lbl_ihlal_sayisi.pack(anchor=tk.W, padx=12, pady=(0, 6))

        # Kart 2: Yaya Geçidi Durumu Rozeti
        kart2 = tk.Frame(sag_panel, bg="#1f2937", bd=1, relief=tk.SOLID)
        kart2.pack(fill=tk.X, padx=12, pady=6)

        tk.Label(kart2, text="🚸 YAYA GEÇİDİ DURUMU", font=("Segoe UI", 9, "bold"), fg="#94a3b8", bg="#1f2937").pack(anchor=tk.W, padx=12, pady=(8, 2))
        self.lbl_yaya_durum = tk.Label(kart2, text="Geçit Boş (Yol Açık)", font=("Segoe UI", 11, "bold"), fg="#10b981", bg="#1f2937")
        self.lbl_yaya_durum.pack(anchor=tk.W, padx=12, pady=(0, 8))

        # Kart 3: Son İhlal Önizleme Kartı
        kart3 = tk.Frame(sag_panel, bg="#1f2937", bd=1, relief=tk.SOLID)
        kart3.pack(fill=tk.X, padx=12, pady=6)

        tk.Label(kart3, text="📸 SON İHLAL DELİLİ", font=("Segoe UI", 9, "bold"), fg="#38bdf8", bg="#1f2937").pack(anchor=tk.W, padx=12, pady=(8, 4))
        
        self.lbl_son_ihlal = tk.Label(
            kart3, 
            bg="#0b0f19", 
            width=290, 
            height=130, 
            text="Henüz İhlal Tespit Edilmedi", 
            fg="#64748b", 
            font=("Segoe UI", 9)
        )
        self.lbl_son_ihlal.pack(padx=10, pady=4)

        self.lbl_son_ihlal_bilgi = tk.Label(
            kart3, 
            text="Tutanak Durumu: Beklemede", 
            font=("Segoe UI", 8), 
            fg="#94a3b8", 
            bg="#1f2937"
        )
        self.lbl_son_ihlal_bilgi.pack(padx=10, pady=(2, 8))

        # Kart 4: Canlı EDS Olay Konsolu (Terminal Feed)
        kart4 = tk.Frame(sag_panel, bg="#1f2937", bd=1, relief=tk.SOLID)
        kart4.pack(fill=tk.BOTH, expand=True, padx=12, pady=(6, 12))

        tk.Label(kart4, text="📟 CANLI DENETİM GÜNLÜĞÜ", font=("Segoe UI", 9, "bold"), fg="#a78bfa", bg="#1f2937").pack(anchor=tk.W, padx=12, pady=(8, 4))

        log_kapsayici = tk.Frame(kart4, bg="#0b0f19")
        log_kapsayici.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        self.txt_log = tk.Text(
            log_kapsayici,
            bg="#0b0f19",
            fg="#e2e8f0",
            font=("Consolas", 8),
            wrap=tk.WORD,
            bd=0,
            highlightthickness=0,
            state=tk.DISABLED
        )
        self.txt_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Log renk etiketleri
        self.txt_log.tag_config("bilgi", foreground="#94a3b8")
        self.txt_log.tag_config("basari", foreground="#34d399")
        self.txt_log.tag_config("ihlal", foreground="#f87171")
        self.txt_log.tag_config("uyari", foreground="#fbbf24")
        self.txt_log.tag_config("hata", foreground="#ef4444")

        # Sol Video Ekranı Kapsayıcısı
        self.video_kapsayici = tk.Frame(orta_frame, bg="#0b0f19", bd=1, relief=tk.SOLID)
        self.video_kapsayici.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.video_kapsayici.pack_propagate(False)

        self.lbl_video = tk.Label(
            self.video_kapsayici, 
            bg="#0b0f19", 
            text="▶️ Video akışı başlatılmadı.\nLütfen alttaki butonlardan bir video seçin veya canlı kamerayı başlatın.",
            fg="#64748b", 
            font=("Segoe UI", 11)
        )
        self.lbl_video.pack(expand=True)

    def _ses_degistir(self):
        """Sesli ikazı açıp kapatır."""
        self.ses_aktif = not self.ses_aktif
        if self.ses_aktif:
            self.btn_ses.config(text="🔊 Ses: AÇIK", bg="#f59e0b", fg="#000000")
            self._log_ekle("Sesli ikaz sistemi AÇILDI.", "uyari")
        else:
            self.btn_ses.config(text="🔇 Ses: KAPALI", bg="#475569", fg="#cbd5e1")
            self._log_ekle("Sesli ikaz sistemi KAPATILDI.", "bilgi")

    def _sesli_uyari_cal(self):
        """İhlal anında kısa ve net bir uyarı sesi verir."""
        if self.ses_aktif:
            threading.Thread(target=lambda: winsound.Beep(1400, 250), daemon=True).start()

    def durum_yaz(self, mesaj, renk="#f8fafc"):
        self.lbl_durum.config(text=mesaj, fg=renk)
        self.lbl_durum_isik.config(fg=renk)

    def _ayarlari_yukle(self):
        if os.path.exists(self.ayar_dosyasi):
            try:
                with open(self.ayar_dosyasi, "r", encoding="utf-8") as f:
                    veri = json.load(f)
                    self.ozel_yaya_oranlari = veri.get("yaya_oranlari")
                    self.ozel_durma_oranlari = veri.get("durma_oranlari")
            except Exception:
                pass

    def _ayarlari_kaydet(self):
        try:
            veri = {
                "yaya_oranlari": self.ozel_yaya_oranlari,
                "durma_oranlari": self.ozel_durma_oranlari
            }
            with open(self.ayar_dosyasi, "w", encoding="utf-8") as f:
                json.dump(veri, f, indent=2)
        except Exception as e:
            print("Ayar kaydedilemedi:", e)

    def _bolgeleri_sifirla(self):
        self.ozel_yaya_oranlari = None
        self.ozel_durma_oranlari = None
        if os.path.exists(self.ayar_dosyasi):
            try:
                os.remove(self.ayar_dosyasi)
            except Exception:
                pass
        messagebox.showinfo("Bilgi", "Bölge koordinatları varsayılan ayarlara sıfırlandı.")
        self.durum_yaz("Bölgeler Sıfırlandı", "#34d399")
        self._log_ekle("Yaya geçidi ve durma çizgisi varsayılan oranlara sıfırlandı.", "bilgi")

    def _fareyle_bolge_ciz(self):
        if self.calisiyor:
            self._durdur()

        cap = cv2.VideoCapture(self.son_acilan_kaynak)
        frame = None
        ret = False
        for _ in range(5):
            ret, frame = cap.read()
            if ret:
                break
        cap.release()

        if not ret or frame is None:
            messagebox.showwarning("Uyarı", "Görüntü okunamadı! Önce bir video veya kamera seçiniz.")
            return

        h, w = frame.shape[:2]
        ekran_w = self.pencere.winfo_screenwidth()
        ekran_h = self.pencere.winfo_screenheight()
        oran = min(int(ekran_w * 0.85) / w, int(ekran_h * 0.70) / h, 2.0)
        gw, gh = max(1, int(w * oran)), max(1, int(h * oran))

        pencere = tk.Toplevel(self.pencere)
        pencere.title("Hassas Bölge Kalibrasyonu")
        pencere.configure(bg="#0b0f19")
        pencere.resizable(False, False)
        pencere.transient(self.pencere)

        lbl_bilgi = tk.Label(pencere, text="", font=("Segoe UI", 11, "bold"), fg="#34d399", bg="#0b0f19")
        lbl_bilgi.pack(pady=(10, 5))

        canvas = tk.Canvas(pencere, width=gw, height=gh, bg="black", highlightthickness=0, cursor="crosshair")
        canvas.pack(padx=10, pady=5)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        resim = Image.fromarray(rgb).resize((gw, gh), Image.Resampling.BILINEAR)
        foto = ImageTk.PhotoImage(resim)
        canvas.create_image(0, 0, anchor=tk.NW, image=foto)
        canvas.foto = foto

        yaya_noktalari = []
        durma_noktalari = []

        def ciz_bolge(noktalar, renk):
            for (px, py) in noktalar:
                canvas.create_oval(px - 5, py - 5, px + 5, py + 5, fill=renk, outline="white", tags="cizim")
            if len(noktalar) > 1:
                duz = [c for p in noktalar for c in p]
                if len(noktalar) == 4:
                    canvas.create_polygon(*duz, fill="", outline=renk, width=3, tags="cizim")
                else:
                    canvas.create_line(*duz, fill=renk, width=3, tags="cizim")

        def yenile():
            canvas.delete("cizim")
            ciz_bolge(yaya_noktalari, "#10b981")
            ciz_bolge(durma_noktalari, "#f59e0b")
            if len(yaya_noktalari) < 4:
                lbl_bilgi.config(text=f"ADIM 1/2: YAYA GEÇİDİNİN 4 Köşesine Tıklayın ({len(yaya_noktalari)}/4)", fg="#34d399")
            elif len(durma_noktalari) < 4:
                lbl_bilgi.config(text=f"ADIM 2/2: ARAÇ DURMA ÇİZGİSİNİN 4 Köşesine Tıklayın ({len(durma_noktalari)}/4)", fg="#fbbf24")
            else:
                lbl_bilgi.config(text="Bölgeler Tamamlandı! Kaydet butonuna basınız.", fg="#38bdf8")
            btn_kaydet.config(state=tk.NORMAL if len(durma_noktalari) == 4 else tk.DISABLED)

        def tikla(event):
            if len(yaya_noktalari) < 4:
                yaya_noktalari.append((event.x, event.y))
            elif len(durma_noktalari) < 4:
                durma_noktalari.append((event.x, event.y))
            yenile()

        def geri_al():
            if durma_noktalari:
                durma_noktalari.pop()
            elif yaya_noktalari:
                yaya_noktalari.pop()
            yenile()

        def bastan():
            yaya_noktalari.clear()
            durma_noktalari.clear()
            yenile()

        def kaydet():
            if len(yaya_noktalari) == 4 and len(durma_noktalari) == 4:
                self.ozel_yaya_oranlari = [(px / gw, py / gh) for px, py in yaya_noktalari]
                self.ozel_durma_oranlari = [(px / gw, py / gh) for px, py in durma_noktalari]
                self._ayarlari_kaydet()
                self.durum_yaz("Özel Bölge Aktif", "#a78bfa")
                self._log_ekle("Yeni özel yaya geçidi ve durma çizgisi koordinatları kaydedildi.", "basari")
                pencere.destroy()
                messagebox.showinfo("Başarılı", "Yeni bölge koordinatları başarıyla kaydedildi!")

        canvas.bind("<Button-1>", tikla)

        butonlar = tk.Frame(pencere, bg="#0b0f19")
        butonlar.pack(pady=(6, 12))
        stil = {"font": ("Segoe UI", 9, "bold"), "relief": tk.FLAT, "cursor": "hand2", "padx": 14, "pady": 6}

        tk.Button(butonlar, text="↩️ Geri Al", bg="#334155", fg="#f8fafc", command=geri_al, **stil).pack(side=tk.LEFT, padx=5)
        tk.Button(butonlar, text="🗑️ Baştan Başla", bg="#1e293b", fg="#f8fafc", command=bastan, **stil).pack(side=tk.LEFT, padx=5)
        btn_kaydet = tk.Button(butonlar, text="💾 Kaydet", bg="#10b981", fg="#ffffff", command=kaydet, state=tk.DISABLED, **stil)
        btn_kaydet.pack(side=tk.LEFT, padx=5)
        tk.Button(butonlar, text="❌ İptal", bg="#ef4444", fg="#ffffff", command=pencere.destroy, **stil).pack(side=tk.LEFT, padx=5)

        yenile()
        pencere.update_idletasks()
        px = max(0, (ekran_w - pencere.winfo_width()) // 2)
        py = max(0, (ekran_h - pencere.winfo_height()) // 2 - 20)
        pencere.geometry(f"+{px}+{py}")
        pencere.grab_set()

    def _ornek_video_baslat(self):
        ornek_yol = os.path.join(self.ana_dizin, "data", "ornek_trafik.mp4")
        if not os.path.exists(ornek_yol):
            messagebox.showerror("Hata", "Örnek video bulunamadı!")
            return
        self._baslat_kaynak(ornek_yol, "Demo Trafik Videosu")

    def _video_dosyasi_sec(self):
        dosya = filedialog.askopenfilename(
            title="Trafik / Yaya Geçidi Videosu Seç",
            filetypes=[("Video Dosyaları", "*.mp4 *.avi *.mov *.mkv *.webm"), ("Tüm Dosyalar", "*.*")]
        )
        if dosya:
            self._baslat_kaynak(dosya, os.path.basename(dosya))

    def _webcam_baslat(self):
        self._baslat_kaynak(0, "Canlı Kamera (Webcam)")

    def _baslat_kaynak(self, kaynak, baslik):
        if self.model is None:
            messagebox.showwarning("Uyarı", "Yapay zekâ modeli henüz yükleniyor, lütfen birkaç saniye bekleyin.")
            return

        self._durdur()
        self.calisiyor = True
        self.son_acilan_kaynak = kaynak
        self.btn_durdur.config(state=tk.NORMAL)
        self.btn_ornek.config(state=tk.DISABLED)
        self.btn_dosya.config(state=tk.DISABLED)
        self.btn_webcam.config(state=tk.DISABLED)
        
        self.durum_yaz("CANLI DENETİM", "#10b981")
        self._log_ekle(f"Denetim başlatıldı: {baslik}", "basari")

        self.thread = threading.Thread(target=self._video_dongusu, args=(kaynak,), daemon=True)
        self.thread.start()

    def _durdur(self):
        self.calisiyor = False
        if self.cap:
            self.cap.release()
            self.cap = None
        self.btn_durdur.config(state=tk.DISABLED)
        self.btn_ornek.config(state=tk.NORMAL)
        self.btn_dosya.config(state=tk.NORMAL)
        self.btn_webcam.config(state=tk.NORMAL)
        self.durum_yaz("Durduruldu", "#ef4444")
        self._log_ekle("Kamera/Video denetimi durduruldu.", "uyari")

    def _ihlal_klasorunu_ac(self):
        if os.path.exists(self.ihlal_klasoru):
            os.startfile(self.ihlal_klasoru)
        else:
            messagebox.showinfo("Bilgi", "Henüz kaydedilmiş bir ihlal yok.")

    def _excel_raporunu_ac(self):
        excel_yolu = self.raporcu.excel_olustur()
        if os.path.exists(excel_yolu):
            os.startfile(excel_yolu)
            self._log_ekle("Resmi Excel ceza tutanağı açıldı.", "bilgi")
        else:
            messagebox.showinfo("Bilgi", "Henüz rapor oluşturulamadı.")

    def _video_dongusu(self, kaynak):
        self.cap = cv2.VideoCapture(kaynak)
        if not self.cap.isOpened():
            self.pencere.after(0, lambda: messagebox.showerror("Hata", "Video kaynağı açılamadı!"))
            self.pencere.after(0, self._durdur)
            return

        w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        video_fps = self.cap.get(cv2.CAP_PROP_FPS)

        cekirdek = YayaGecidiCekirdek(self.model, w, h, video_fps,
                                      self.ozel_yaya_oranlari, self.ozel_durma_oranlari)
        self.ocr_mesgul = False
        deneme_sayilari = {}

        while self.calisiyor and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                break

            # Çizimsiz ham kareyi OCR için sakla
            ham_kare = frame.copy()
            sonuc = cekirdek.kare_isle(frame, cizim=True)

            # Canlı Araç Plaka Tarama (İhlal olmasa bile ekrandaki araçların plakasını okuyup kutu üstünde gösterir)
            if not self.ocr_mesgul and sonuc.get("araclar"):
                adaylar = []
                for a in sonuc["araclar"]:
                    vid = a["vid"]
                    bx1, by1, bx2, by2 = a["bbox"]
                    genislik = bx2 - bx1
                    if vid not in cekirdek.arac_plakalari and deneme_sayilari.get(vid, 0) < 4 and genislik >= 65:
                        adaylar.append((genislik * (by2 - by1), a))
                if adaylar:
                    adaylar.sort(key=lambda x: x[0], reverse=True)
                    secilen = adaylar[0][1]
                    svid = secilen["vid"]
                    deneme_sayilari[svid] = deneme_sayilari.get(svid, 0) + 1
                    self.ocr_mesgul = True
                    threading.Thread(
                        target=self._canli_plaka_tara,
                        args=(ham_kare, secilen, cekirdek),
                        daemon=True
                    ).start()

            # Yeni İhlal Olayları
            for olay in sonuc["ihlaller"]:
                self.toplam_ihlal += 1
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                kanit_yolu = os.path.join(self.ihlal_klasoru, f"ihlal_{ts}_arac{olay['vid']}.jpg")
                cv2.imwrite(kanit_yolu, frame)
                
                # Sesli Alarm
                self._sesli_uyari_cal()

                hazir_plaka = cekirdek.arac_plakalari.get(olay["vid"])
                if hazir_plaka:
                    p_metin = hazir_plaka["plaka"]
                    p_guven = hazir_plaka["guven"]
                    self.raporcu.ihlal_ekle(olay["vid"], olay["tur"], kanit_yolu, plaka=p_metin, guven=p_guven)
                    self.pencere.after(0, self._arayuz_ihlal_guncelle, kanit_yolu, olay["vid"], olay["tur"], p_metin, p_guven)
                    self.pencere.after(0, self._log_ekle, f"🚨 İHLAL! {olay['tur']} #{olay['vid']} [{p_metin}] durmadı! Ceza kesildi.", "ihlal")
                else:
                    self.pencere.after(0, self._arayuz_ihlal_guncelle, kanit_yolu, olay["vid"], olay["tur"], "Okunuyor...", 0.0)
                    self.pencere.after(0, self._log_ekle, f"🚨 İHLAL! {olay['tur']} #{olay['vid']} durmadı! Kanıt kaydedildi.", "ihlal")
                    threading.Thread(
                        target=self._arka_plan_plaka_isle,
                        args=(ham_kare, olay, kanit_yolu, cekirdek),
                        daemon=True
                    ).start()

            self.pencere.after(0, self._durum_metinlerini_guncelle, sonuc["yaya_var"])

            # Görüntüyü çiz
            self._frame_ciz(frame)
            time.sleep(0.025)

        if self.cap:
            self.cap.release()
        self.pencere.after(0, self._durdur)

    def _canli_plaka_tara(self, ham_kare, arac_bilgi, cekirdek):
        try:
            vid = arac_bilgi["vid"]
            bbox = arac_bilgi["bbox"]
            plaka_res = self.plaka_okuyucu.plaka_oku(ham_kare, bbox)
            if plaka_res["bulundu"]:
                cekirdek.plaka_kaydet(vid, plaka_res, bbox)
                p_metin = plaka_res["plaka"]
                p_guven = plaka_res["guven"]
                self.pencere.after(0, self._log_ekle, f"🔍 Araç #{vid} Plaka Okundu: {p_metin} (%{p_guven})", "basari")
        except Exception:
            pass
        finally:
            self.ocr_mesgul = False

    def _durum_metinlerini_guncelle(self, yaya_var):
        if yaya_var:
            self.lbl_yaya_durum.config(text="⚠️ GEÇİTTE YAYA VAR! (DUR)", fg="#ef4444")
        else:
            self.lbl_yaya_durum.config(text="Geçit Boş (Yol Açık)", fg="#10b981")

    def _arka_plan_plaka_isle(self, ham_kare, olay, kanit_yolu, cekirdek):
        bbox = olay.get("bbox")
        plaka_res = self.plaka_okuyucu.plaka_oku(ham_kare, bbox)
        plaka_metni = plaka_res["plaka"]
        plaka_guven = plaka_res["guven"]

        if plaka_res["bulundu"]:
            cekirdek.plaka_kaydet(olay["vid"], plaka_res, bbox)

        # Rapor ve Excel kaydı
        self.raporcu.ihlal_ekle(olay["vid"], olay["tur"], kanit_yolu, plaka=plaka_metni, guven=plaka_guven)

        # Kart ve Log güncellemesi
        self.pencere.after(0, self._arayuz_ihlal_guncelle, kanit_yolu, olay["vid"], olay["tur"], plaka_metni, plaka_guven)
        if plaka_res["bulundu"]:
            self.pencere.after(0, self._log_ekle, f"🚗 Araç #{olay['vid']} Plaka: {plaka_metni} (Güven: %{plaka_guven})", "basari")

    def _arayuz_ihlal_guncelle(self, kanit_yolu, vid, arac_turu, plaka="PLAKA OKUNAMADI", guven=0.0):
        self.lbl_ihlal_sayisi.config(text=str(self.toplam_ihlal))
        plaka_satiri = f"\nPlaka: {plaka}"
        if guven > 0:
            plaka_satiri += f" (%{guven})"
        self.lbl_son_ihlal_bilgi.config(
            text=f"Son Ceza: {arac_turu} #{vid}{plaka_satiri}\nMadde: KTK 74 (Yaya Önceliği)", 
            fg="#f87171"
        )
        try:
            img = Image.open(kanit_yolu)
            img.thumbnail((280, 130))
            foto = ImageTk.PhotoImage(img)
            self.lbl_son_ihlal.config(image=foto, text="")
            self.lbl_son_ihlal.image = foto
        except Exception:
            pass

    def _frame_ciz(self, frame):
        try:
            max_w = self.video_kapsayici.winfo_width() - 8
            max_h = self.video_kapsayici.winfo_height() - 8

            if max_w > 50 and max_h > 50:
                frame_h, frame_w = frame.shape[:2]
                oran = min(max_w / frame_w, max_h / frame_h)
                hedef_w = max(1, int(frame_w * oran))
                hedef_h = max(1, int(frame_h * oran))

                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                img = img.resize((hedef_w, hedef_h), Image.Resampling.BILINEAR)
                foto = ImageTk.PhotoImage(image=img)
                self.lbl_video.config(image=foto, text="")
                self.lbl_video.image = foto
        except Exception:
            pass

    def _cikis_yap(self):
        self._durdur()
        self.pencere.destroy()

if __name__ == "__main__":
    kok = tk.Tk()
    uygulama = EDSPanelUygulamasi(kok)
    kok.mainloop()
