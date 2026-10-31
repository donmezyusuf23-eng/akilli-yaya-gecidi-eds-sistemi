"""
Akıllı Yaya Geçidi Kural İhlali Tespit Sistemi
Ceza ve Denetim Raporu Yöneticisi
--------------------------------------------------------------
İhlal tespit edilen araçların verilerini ve okunan plakalarını depolar,
tek tıkla resmi formatta Excel (.xlsx) ceza tutanağı oluşturur.
"""

import os
import json
from datetime import datetime
import xlsxwriter

class RaporYoneticisi:
    def __init__(self, cikti_klasoru="output"):
        self.cikti_klasoru = cikti_klasoru
        self.json_yolu = os.path.join(cikti_klasoru, "ihlal_kayitlari.json")
        self.excel_yolu = os.path.join(cikti_klasoru, "EDS_Yaya_Gecidi_Ihlal_Raporu.xlsx")
        os.makedirs(cikti_klasoru, exist_ok=True)
        self.kayitlar = self._kayitlari_yukle()

    def _kayitlari_yukle(self):
        if os.path.exists(self.json_yolu):
            try:
                with open(self.json_yolu, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def _kayitlari_kaydet(self):
        try:
            with open(self.json_yolu, "w", encoding="utf-8") as f:
                json.dump(self.kayitlar, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[HATA] İhlal JSON kaydedilemedi: {e}")

    def ihlal_ekle(self, arac_id, arac_turu, kanit_yolu, plaka="PLAKA OKUNAMADI", guven=0.0):
        """Yeni bir ihlal gerçekleştiğinde kaydı ekler ve Excel'i günceller."""
        simdi = datetime.now()
        tarih_saat = simdi.strftime("%d.%m.%Y %H:%M:%S")
        
        yeni_kayit = {
            "sira_no": len(self.kayitlar) + 1,
            "tarih_saat": tarih_saat,
            "ihlal_maddesi": "KTK Madde 74 (Yayaya Yol Vermeme)",
            "plaka": plaka if plaka else "PLAKA OKUNAMADI",
            "plaka_guven": guven,
            "arac_id": f"Araç #{arac_id}",
            "arac_turu": arac_turu,
            "kanit_dosyasi": os.path.basename(kanit_yolu),
            "tam_kanit_yolu": kanit_yolu,
            "durum": "Onaylandı (Tutanak Kesildi)"
        }
        
        self.kayitlar.append(yeni_kayit)
        self._kayitlari_kaydet()
        self.excel_olustur()
        return yeni_kayit

    def excel_olustur(self):
        """Kurumsal formatta resmi görünümlü Excel raporu üretir."""
        workbook = xlsxwriter.Workbook(self.excel_yolu)
        worksheet = workbook.add_worksheet("EDS_İhlal_Tutanağı")

        # Görünüm Ayarları
        worksheet.hide_gridlines(False)

        # Stiller
        stil_ana_baslik = workbook.add_format({
            "bold": True,
            "font_size": 14,
            "font_name": "Segoe UI",
            "align": "center",
            "valign": "vcenter",
            "bg_color": "#1F4E79",
            "font_color": "#FFFFFF"
        })

        stil_alt_baslik = workbook.add_format({
            "italic": True,
            "font_size": 10,
            "font_name": "Segoe UI",
            "align": "center",
            "valign": "vcenter",
            "bg_color": "#D9E1F2",
            "font_color": "#1F4E79"
        })

        stil_tablo_baslik = workbook.add_format({
            "bold": True,
            "font_size": 10,
            "font_name": "Segoe UI",
            "align": "center",
            "valign": "vcenter",
            "bg_color": "#2F5597",
            "font_color": "#FFFFFF",
            "border": 1
        })

        stil_hucre_sol = workbook.add_format({
            "font_size": 9,
            "font_name": "Segoe UI",
            "align": "left",
            "valign": "vcenter",
            "border": 1
        })

        stil_hucre_orta = workbook.add_format({
            "font_size": 9,
            "font_name": "Segoe UI",
            "align": "center",
            "valign": "vcenter",
            "border": 1
        })

        stil_plaka = workbook.add_format({
            "bold": True,
            "font_size": 10,
            "font_name": "Consolas",
            "align": "center",
            "valign": "vcenter",
            "bg_color": "#F3F4F6",
            "font_color": "#1E293B",
            "border": 1
        })

        stil_durum = workbook.add_format({
            "bold": True,
            "font_size": 9,
            "font_name": "Segoe UI",
            "align": "center",
            "valign": "vcenter",
            "bg_color": "#FCE4D6",
            "font_color": "#C00000",
            "border": 1
        })

        # Başlık Blokları (A'dan H'ye)
        worksheet.merge_range("A1:H1", "T.C. İÇİŞLERİ BAKANLIĞI EMNİYET GENEL MÜDÜRLÜĞÜ", stil_ana_baslik)
        worksheet.merge_range("A2:H2", "TRAFİK BAŞKANLIĞI - AKILLI EDS YAYA GEÇİDİ KURAL İHLALİ DENETİM RAPORU", stil_ana_baslik)
        worksheet.merge_range("A3:H3", f"Rapor Oluşturulma Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')} | Elektronik Denetleme Sistemi (EDS + ANPR)", stil_alt_baslik)

        # Tablo Sütun Başlıkları (Satır 5)
        basliklar = [
            ("A5", "Sıra No", 8),
            ("B5", "İhlal Tarihi ve Saati", 22),
            ("C5", "İhlal Maddesi", 28),
            ("D5", "Tespit Edilen Plaka", 20),
            ("E5", "Araç Takip ID", 14),
            ("F5", "Araç Türü", 16),
            ("G5", "Fotoğrafik Kanıt Dosyası", 32),
            ("H5", "Tutanak Durumu", 22)
        ]

        for hucre, baslik_metni, genislik in basliklar:
            sutun_harfi = hucre[0]
            worksheet.set_column(f"{sutun_harfi}:{sutun_harfi}", genislik)
            worksheet.write(hucre, baslik_metni, stil_tablo_baslik)

        # Veri Satırlarını Yaz
        satir = 5
        if not self.kayitlar:
            worksheet.merge_range("A6:H6", "Henüz kaydedilmiş kural ihlali bulunmamaktadır.", stil_hucre_orta)
        else:
            for k in self.kayitlar:
                plaka_yazi = k.get("plaka", "PLAKA OKUNAMADI")
                if k.get("plaka_guven", 0) > 0:
                    plaka_yazi += f" (%{k['plaka_guven']})"

                worksheet.write(satir, 0, k.get("sira_no", satir - 4), stil_hucre_orta)
                worksheet.write(satir, 1, k.get("tarih_saat", "-"), stil_hucre_orta)
                worksheet.write(satir, 2, k.get("ihlal_maddesi", "KTK Madde 74"), stil_hucre_sol)
                worksheet.write(satir, 3, plaka_yazi, stil_plaka)
                worksheet.write(satir, 4, k.get("arac_id", "-"), stil_hucre_orta)
                worksheet.write(satir, 5, k.get("arac_turu", "Araç"), stil_hucre_orta)
                worksheet.write(satir, 6, k.get("kanit_dosyasi", "-"), stil_hucre_sol)
                worksheet.write(satir, 7, k.get("durum", "Onaylandı"), stil_durum)
                satir += 1

        workbook.close()
        return self.excel_yolu
