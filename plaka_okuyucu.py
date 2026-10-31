"""
Akıllı Yaya Geçidi Kural İhlali Tespit Sistemi
Otomatik Plaka Tanıma (ANPR / YOLOv8-Plate + EasyOCR) Modülü
--------------------------------------------------------------
Özel eğitilmiş YOLOv8 Plaka Tespit Modeli (plaka_yolov8.pt) ile araç
üzerindeki plaka bölgesini milisaniyeler içinde bulur ve sadece plaka
kesiti üzerinde EasyOCR + Akıllı Karakter Düzeltme çalıştırır.
"""

import os
import re
import cv2
import numpy as np


class PlakaOkuyucu:
    # OCR harf <-> rakam benzerlik düzeltme tabloları
    HARFTEN_RAKAMA = {'O': '0', 'I': '1', 'J': '3', 'A': '4', 'G': '6', 'S': '5', 'Z': '2', 'B': '8', 'L': '4', 'T': '7'}
    RAKAMDAN_HARFE = {'0': 'O', '1': 'I', '3': 'J', '4': 'A', '6': 'G', '5': 'S', '8': 'B'}

    def __init__(self, gpu=False):
        self.gpu = gpu
        self.reader = None
        self.plaka_modeli = None
        self._hazir = False
        self.ana_dizin = os.path.dirname(os.path.abspath(__file__))

    def _model_yukle(self):
        """YOLOv8 Plaka Dedektörü ve EasyOCR modellerini başlatır."""
        if self.reader is None:
            try:
                import easyocr
                from ultralytics import YOLO

                self.reader = easyocr.Reader(['en'], gpu=self.gpu, verbose=False)
                plaka_pt = os.path.join(self.ana_dizin, "plaka_yolov8.pt")
                if os.path.exists(plaka_pt):
                    self.plaka_modeli = YOLO(plaka_pt)
                self._hazir = True
            except Exception as e:
                print(f"[UYARI] Plaka okuyucu modeli yüklenemedi: {e}")
                self._hazir = False
        return self._hazir

    def _plaka_formatla(self, ham_metin):
        """
        Ham OCR çıktısını temizler, ülke kodu şeritlerini (BY, TR, NL vb.) ayıklar
        ve plaka standardına göre (TR / Avrupa / UK) karakter düzeltmesi yapar.
        """
        if not ham_metin:
            return None

        ust = ham_metin.upper().strip()
        # Ülke kodu şeridi öneklerini temizle (örn: "BY 5379MX-4" -> "5379MX-4")
        ust = re.sub(r'^(BY|TR|NL|UK|GB|DE|FR)\s+', '', ust)

        # Tire ve boşlukları koruyarak temizle
        temiz_ham = re.sub(r'[^A-Z0-9\-\s]', '', ust).strip(' -')
        sadece_alnum = re.sub(r'[^A-Z0-9]', '', temiz_ham)

        if len(sadece_alnum) < 4 or len(sadece_alnum) > 10:
            return None

        # Sol mavi ülke şeridinden kaynaklanan tek harfli 'E' veya 'I' önekini temizle (örn: E3O66MP -> 3066MP)
        if len(sadece_alnum) >= 7 and sadece_alnum[0] in ('E', 'I') and sadece_alnum[1].isdigit():
            aday_kisa = sadece_alnum[1:]
            if aday_kisa[0].isdigit():
                sadece_alnum = aday_kisa
                temiz_ham = temiz_ham[1:].strip(' -')

        # 1. Hollanda / Avrupa Tireli Format (örn: R-183-JF, XX-123-XX)
        tireli = re.search(r'^([A-Z]{1,3})\-([0-9]{2,4})\-([A-Z]{1,3})$', temiz_ham.replace(' ', ''))
        if tireli:
            return f"{tireli.group(1)}-{tireli.group(2)}-{tireli.group(3)}"

        # 2. 4 Rakam + 2 Harf + Opsiyonel Tire/Rakam Formatı (örn: 5379 MX-4, 3066 MP)
        # Başındaki olası mavi şerit gürültüsünü (BY, BX, R, E vb.) yoksayarak eşleştir
        m_by = re.search(r'(?:^[A-Z]{1,2}\s+)?([0-9OIZSB]{4})\s*([A-Z]{2})\s*\-?\s*([0-9OIZSBL]?)$', temiz_ham)
        if m_by:
            d4, l2, son = m_by.groups()
            d4_duz = "".join(self.HARFTEN_RAKAMA.get(c, c) for c in d4)
            if d4_duz.isdigit():
                if son:
                    son_harita = {**self.HARFTEN_RAKAMA, 'L': '4'}
                    son_duz = son_harita.get(son, son)
                    if son_duz.isdigit():
                        return f"{d4_duz} {l2}-{son_duz}"
                return f"{d4_duz} {l2}"

        # 3. İngiltere / Avrupa 7 Karakter Formatı: 2 Harf + 2 Rakam + 3 Harf (örn: GX15 OGJ, MW51 VSU, KH05 ZZK)
        if len(sadece_alnum) == 7:
            l1 = "".join(self.RAKAMDAN_HARFE.get(c, c) for c in sadece_alnum[0:2])
            d1 = "".join(self.HARFTEN_RAKAMA.get(c, c) for c in sadece_alnum[2:4])
            l2 = "".join(self.RAKAMDAN_HARFE.get(c, c) for c in sadece_alnum[4:7])
            if l1.isalpha() and d1.isdigit() and l2.isalpha():
                return f"{l1}{d1} {l2}"

        # 4. Türkiye Standart Plaka Formatı: 2 Rakam (01-81) + 1-3 Harf + 2-4 Rakam (örn: 34 EDS 074)
        tr_eslesme = re.search(r'^([0-8][0-9])([A-Z]{1,3})([0-9OIZSB]{2,4})$', sadece_alnum)
        if tr_eslesme:
            il, harf, num = tr_eslesme.groups()
            num_duz = "".join(self.HARFTEN_RAKAMA.get(c, c) for c in num)
            if num_duz.isdigit():
                return f"{il} {harf} {num_duz}"

        # Gerçek plakada en az 6 karakter, en az 2 harf ve en az 2 rakam bulunmalıdır
        if len(sadece_alnum) < 6:
            return None
        harf_sayisi = sum(1 for c in sadece_alnum if c.isalpha())
        rakam_sayisi = sum(1 for c in sadece_alnum if c.isdigit())
        if harf_sayisi < 2 or rakam_sayisi < 2:
            return None

        gruplar = re.findall(r'[A-Z]+|[0-9]+', temiz_ham)
        if len(gruplar) >= 2:
            return " ".join(gruplar)

        return sadece_alnum

    def _kesitten_ocr_oku(self, plaka_crop):
        """Kırpılmış dar plaka kutusu üzerinde hızlı OCR çalıştırır."""
        if plaka_crop is None or plaka_crop.size == 0:
            return None, 0.0

        ch, cw = plaka_crop.shape[:2]
        if ch < 10 or cw < 20:
            return None, 0.0

        # Küçük plaka kesitini netleştirmek için 2 kat büyüt
        scale = 2.0 if ch < 55 else 1.5
        buyuk = cv2.resize(plaka_crop, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        allow_chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ- '

        adaylar = []

        # Deneme 1: Doğrudan büyütülmüş plaka kesiti
        try:
            res = self.reader.readtext(buyuk, allowlist=allow_chars, width_ths=0.9, detail=1)
            if res:
                birlesik_metin = " ".join(r[1] for r in res)
                ort_guven = max(float(r[2]) for r in res)
                bicimli = self._plaka_formatla(birlesik_metin)
                if bicimli:
                    adaylar.append((bicimli, ort_guven))
                for _, parca, g in res:
                    b_parca = self._plaka_formatla(parca)
                    if b_parca:
                        adaylar.append((b_parca, float(g)))
        except Exception:
            pass

        # Deneme 2: Eğer güven düşükse veya bulunamadıysa Gri + Kontrast/Threshold dene
        if not adaylar or adaylar[0][1] < 0.55:
            try:
                gri = cv2.cvtColor(buyuk, cv2.COLOR_BGR2GRAY)
                norm = cv2.normalize(gri, None, 0, 255, cv2.NORM_MINMAX)
                res2 = self.reader.readtext(norm, allowlist=allow_chars, width_ths=0.9, detail=1)
                if res2:
                    birlesik_metin = " ".join(r[1] for r in res2)
                    ort_guven = max(float(r[2]) for r in res2)
                    bicimli = self._plaka_formatla(birlesik_metin)
                    if bicimli:
                        adaylar.append((bicimli, ort_guven))
            except Exception:
                pass

        if adaylar:
            adaylar.sort(key=lambda x: (len(x[0]) >= 6, x[1]), reverse=True)
            return adaylar[0]

        return None, 0.0

    def plaka_oku(self, frame, arac_bbox=None):
        """
        Verilen frame veya araç bölgesinden önce YOLOv8 plaka dedektörü ile
        plakanın tam kutusunu bulur, ardından sadece o kutuyu OCR ile okur.
        """
        if not self._model_yukle():
            return {"plaka": "OCR_DEVRE_DISI", "guven": 0.0, "bulundu": False, "kutu": None}

        h, w = frame.shape[:2]

        if arac_bbox is not None:
            bx1, by1, bx2, by2 = map(int, arac_bbox)
            bx1, by1 = max(0, bx1), max(0, by1)
            bx2, by2 = min(w, bx2), min(h, by2)
            arac_roi = frame[by1:by2, bx1:bx2]
            off_x, off_y = bx1, by1
        else:
            arac_roi = frame
            off_x, off_y = 0, 0

        if arac_roi is None or arac_roi.size == 0 or arac_roi.shape[0] < 20 or arac_roi.shape[1] < 30:
            return {"plaka": "PLAKA OKUNAMADI", "guven": 0.0, "bulundu": False, "kutu": None}

        rh, rw = arac_roi.shape[:2]

        # 1. AŞAMA: YOLOv8 Plaka Tespit Modeli ile plakanın tam koordinatını bul (~200-400 ms)
        if self.plaka_modeli is not None:
            try:
                sonuc = self.plaka_modeli(arac_roi, conf=0.14, imgsz=320, verbose=False)[0]
                if sonuc.boxes is not None and len(sonuc.boxes) > 0:
                    kutular = sonuc.boxes.xyxy.cpu().numpy()
                    skorlar = sonuc.boxes.conf.cpu().numpy()
                    sirali = sorted(zip(kutular, skorlar), key=lambda x: x[1], reverse=True)

                    for pkutu, _ in sirali[:3]:
                        px1, py1, px2, py2 = map(int, pkutu)
                        # Başka aracın kutu köşesine giren plakalarını engellemek için konum kontrolü
                        if arac_bbox is not None:
                            merkez_x = ((px1 + px2) / 2.0) / max(1, rw)
                            merkez_y = ((py1 + py2) / 2.0) / max(1, rh)
                            if merkez_x < 0.08 or merkez_x > 0.92 or merkez_y < 0.25:
                                continue
                        # Küçük kenar payı ekle
                        cx1, cy1 = max(0, px1 - 4), max(0, py1 - 4)
                        cx2, cy2 = min(rw, px2 + 4), min(rh, py2 + 4)
                        plaka_crop = arac_roi[cy1:cy2, cx1:cx2]

                        plaka_metni, guven = self._kesitten_ocr_oku(plaka_crop)
                        if plaka_metni:
                            tam_kutu = (off_x + px1, off_y + py1, off_x + px2, off_y + py2)
                            return {
                                "plaka": plaka_metni,
                                "guven": round(guven * 100, 1),
                                "bulundu": True,
                                "kutu": tam_kutu
                            }
            except Exception:
                pass

        # 2. AŞAMA (Yedek): Tampon bölgesinde doğrudan OCR
        alt_y = int(rh * 0.40)
        tampon_roi = arac_roi[alt_y:, :]
        if tampon_roi.shape[0] >= 15 and tampon_roi.shape[1] >= 30:
            # Çok büyükse 240px yüksekliğe sınırla ki CPU'yu yormasın
            th, tw = tampon_roi.shape[:2]
            scale = 1.0
            if th > 220:
                scale = 200.0 / th
                tampon_islem = cv2.resize(tampon_roi, (int(tw * scale), 200), interpolation=cv2.INTER_AREA)
            else:
                tampon_islem = tampon_roi

            try:
                res = self.reader.readtext(tampon_islem, allowlist='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ- ', width_ths=0.8, detail=1)
                for bbox, metin, guven in res:
                    if float(guven) < 0.25:
                        continue
                    bicimli = self._plaka_formatla(metin)
                    if bicimli:
                        xs = [pt[0] / scale + off_x for pt in bbox]
                        ys = [pt[1] / scale + off_y + alt_y for pt in bbox]
                        tam_kutu = (int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys)))
                        return {
                            "plaka": bicimli,
                            "guven": round(float(guven) * 100, 1),
                            "bulundu": True,
                            "kutu": tam_kutu
                        }
            except Exception:
                pass

        return {"plaka": "PLAKA OKUNAMADI", "guven": 0.0, "bulundu": False, "kutu": None}
