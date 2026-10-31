# 🚦 Akıllı Yaya Geçidi EDS & Plaka Tanıma (ANPR) Denetim Sistemi

Bu proje, ışıksız yaya geçitlerinde yayaların geçiş üstünlüğünü korumak, yayaya yol vermeyen araçları **YOLOv8 + ByteTrack** ile gerçek zamanlı tespit etmek, **özel eğitilmiş YOLOv8 Plaka Dedektörü + EasyOCR** ile araç plakalarını otomatik okumak ve resmi **Excel (`.xlsx`) / JSON İhlal Tutanak Raporu** oluşturmak amacıyla geliştirilmiş uçtan uca bir Bilgisayarlı Görü (Computer Vision) uygulamasıdır.

---

## ✨ Temel Özellikler

- **Gerçek Zamanlı Nesne & Hız Analizi (`YOLOv8n` + `ByteTrack`):** Yaya geçidi ve durma çizgisi bölgelerindeki (ROI) yayaları ve motorlu araçları takip eder; duran araç ile durmayıp ihlal yapan aracı hız vektörüyle ayırt eder.
- **İki Aşamalı Yapay Zekâ Plaka Okuma (`plaka_yolov8.pt` + `EasyOCR`):**
  1. Özel eğitilmiş YOLOv8 plaka tespit modeli araç üzerindeki plakanın tam koordinatlarını bulur ve mavi çerçeve içine alır (`PLAKA: ...`).
  2. Asenkron arka plan iş parçacığı (thread) ile video akışını dondurmadan plakayı metne döker ve karakter düzeltmesi uygular.
- **Modern Koyu Tema (Dark Mode) EDS Kontrol Merkezi (`gui_app.py`):**
  - Canlı FPS, aktif durum rozeti, toplam ihlal sayacı ve ihlal kanıt galerisi.
  - Koyu tema canlı sistem konsolu (`[BİLGİ]`, `[PLAKA]`, `[İHLAL]`).
  - Fare ile video üzerinde canlı **Yaya Geçidi / Durma Bölgesi Çizim Modu**.
- **Otomatik Excel & JSON Raporlama (`rapor_yoneticisi.py`):**
  - Her ihlali zaman damgası, araç türü, okunan plaka, OCR güven skoru ve kanıt fotoğrafı yolu ile birlikte `output/EDS_Yaya_Gecidi_Ihlal_Raporu.xlsx` ve `output/ihlal_kayitlari.json` dosyalarına kaydeder.

---

## 📂 Proje Dosya Yapısı

```text
├── gui_app.py                          # Modern Koyu Tema Masaüstü EDS Kontrol Merkezi Arayüzü
├── tespit_cekirdegi.py                 # YOLOv8 + ByteTrack yaya/araç/hız/ihlal analiz çekirdeği
├── plaka_okuyucu.py                    # YOLOv8 Plaka Tespiti + EasyOCR otomatik plaka okuma modülü
├── rapor_yoneticisi.py                 # Otomatik Excel (.xlsx) ve JSON ihlal tutanak yöneticisi
├── yaya_ihlal_tespiti.py               # Komut satırı (CLI) hızlı çalıştırma betiği
├── etiketle.py                         # Veri seti bölge (poligon) etiketleme aracı
├── degerlendir.py                      # Precision / Recall / F1 akademik performans ölçüm aracı
├── yolov8n.pt                          # Genel nesne tespiti (yaya/araç) model ağırlıkları
├── plaka_yolov8.pt                     # Özel eğitilmiş araç plaka tespiti model ağırlıkları
├── Baslat.bat                          # Tek tıkla masaüstü başlatıcı
├── requirements.txt                    # Gerekli Python kütüphaneleri
├── data/                               # Gerçek HD test videoları
│   ├── 1_Gercek_Trafik_ve_Plaka_Okuma_HD.mp4
│   ├── 2_Otoyol_Coklu_Arac_Plaka_Okuma_1080p.mp4
│   ├── 3_Yakin_Plan_Arac_Plaka_Denetimi_HD.mp4
│   ├── 4_Sehir_Ici_Kavsak_Yaya_Gecidi_1080p.mp4
│   └── 5_Cadde_Yaya_Gecidi_ve_Araclar_HD.mp4
└── output/
    ├── EDS_Yaya_Gecidi_Ihlal_Raporu.xlsx
    ├── ihlal_kayitlari.json
    └── ihlaller/                       # İhlal anı kanıt fotoğrafları
```

---

## 🚀 Kurulum ve Çalıştırma

### 1. Gereksinimleri Yükleyin
```bash
pip install -r requirements.txt
```

### 2. Masaüstü Kontrol Merkezini Başlatın
Windows üzerinde doğrudan **`Baslat.bat`** dosyasına çift tıklayabilir veya terminalden çalıştırabilirsiniz:
```bash
python gui_app.py
```
