"""
Akıllı Yaya Geçidi Kural İhlali Tespit Sistemi
Algılama Çekirdeği
--------------------------------------------------------------
Arayüzden (gui_app.py) bağımsız çalışan ihlal tespit mantığı.
Hem canlı arayüz hem de başarı ölçümü (degerlendir.py) AYNI kodu kullanır,
böylece ölçülen doğruluk, arayüzde çalışan sistemin doğruluğudur.
"""

import cv2
import numpy as np
from collections import deque

# Varsayılan bölgeler (videonun genişlik/yüksekliğine göre yüzde oranları)
VARSAYILAN_YAYA = [(0.25, 0.45), (0.75, 0.45), (0.90, 0.85), (0.10, 0.85)]
VARSAYILAN_DURMA = [(0.20, 0.35), (0.80, 0.35), (0.75, 0.44), (0.25, 0.44)]

# COCO sınıfları: 0=yaya | 2=otomobil, 3=motosiklet, 5=otobüs, 7=kamyon
ARAC_SINIFLARI = {2: "Otomobil", 3: "Motosiklet", 5: "Otobüs", 7: "Kamyon"}


def bolge_piksel(oranlar, genislik, yukseklik):
    """Yüzdelik oranları gerçek piksel koordinatlarına çevirir."""
    return np.array([[int(x * genislik), int(y * yukseklik)] for x, y in oranlar], np.int32)


class YayaGecidiCekirdek:
    # Hız analizi ayarları (araç genişliği / saniye cinsinden, kamera uzaklığından bağımsız)
    HIZ_PENCERE = 8        # Hız hesabında kullanılan son kare sayısı
    HIZ_MIN_KARE = 5       # Karar vermek için gereken en az kare sayısı
    DURMA_ESIGI = 0.3      # Bu değerin altı "durdu" sayılır (araç genişliği/sn)

    # Mükerrer ceza engelleme (video zamanına göre, işlem hızından bağımsız)
    TEKRAR_MESAFE = 160    # Piksel
    TEKRAR_SURE = 4.0      # Saniye

    def __init__(self, model, genislik, yukseklik, fps, yaya_oranlari=None, durma_oranlari=None, guven=0.35):
        self.model = model
        self.fps = fps if fps and 1 <= fps <= 120 else 30.0
        self.guven = guven
        self.yaya_bolgesi = bolge_piksel(yaya_oranlari or VARSAYILAN_YAYA, genislik, yukseklik)
        self.durma_bolgesi = bolge_piksel(durma_oranlari or VARSAYILAN_DURMA, genislik, yukseklik)

        self.kare_no = 0
        self.arac_gecmisi = {}      # {vid: deque[(kare, x, y, genislik)]}
        self.ihlal_idleri = set()
        self.ihlal_konumlari = []   # [(x, y, sn, vid)]
        self.arac_plakalari = {}    # {vid: {"plaka": str, "guven": float, "rel_kutu": (rx1, ry1, rx2, ry2)}}

        # Önceki videodan kalan takip (tracker) durumunu sıfırla
        self.model.predictor = None

    def plaka_kaydet(self, vid, plaka_sonuc, arac_bbox=None):
        """Arka planda okunan plakayı araç ID'si ile eşleştirip hafızaya alır."""
        if not plaka_sonuc or not plaka_sonuc.get("bulundu"):
            return

        yeni_plaka = plaka_sonuc["plaka"]
        # Başka bir araca zaten atanmış olan plakayı ikinci bir araca kopyalama
        for diger_vid, bilgi in self.arac_plakalari.items():
            if diger_vid != vid and bilgi.get("plaka") == yeni_plaka:
                return

        rel_kutu = None
        kutu = plaka_sonuc.get("kutu")
        if kutu and arac_bbox:
            bx1, by1, bx2, by2 = arac_bbox
            bw = max(1, bx2 - bx1)
            bh = max(1, by2 - by1)
            px1, py1, px2, py2 = kutu
            rel_kutu = (
                (px1 - bx1) / bw,
                (py1 - by1) / bh,
                (px2 - bx1) / bw,
                (py2 - by1) / bh
            )

        mevcut = self.arac_plakalari.get(vid)
        if mevcut and mevcut.get("guven", 0) >= plaka_sonuc.get("guven", 0):
            if rel_kutu and mevcut.get("plaka") == yeni_plaka:
                mevcut["rel_kutu"] = rel_kutu
            return

        self.arac_plakalari[vid] = {
            "plaka": yeni_plaka,
            "guven": plaka_sonuc["guven"],
            "rel_kutu": rel_kutu
        }

    def _hiz_hesapla(self, vid, cx, cy, genislik):
        """
        Aracın hızını 'araç genişliği / saniye' olarak hesaplar.
        Yeterli kare birikmediyse None döner (karar verilemez).
        """
        gecmis = self.arac_gecmisi.setdefault(vid, deque(maxlen=self.HIZ_PENCERE))
        gecmis.append((self.kare_no, cx, cy, genislik))
        if len(gecmis) < self.HIZ_MIN_KARE:
            return None

        k0, x0, y0, _ = gecmis[0]
        k1, x1, y1, _ = gecmis[-1]
        kare_farki = k1 - k0
        if kare_farki <= 0:
            return None

        ort_genislik = max(sum(g[3] for g in gecmis) / len(gecmis), 1.0)
        mesafe = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
        return (mesafe / kare_farki) * self.fps / ort_genislik

    def _ayni_arac_mi(self, mx, my, vid, sn):
        """Takip ID'si değişse bile konum + zaman yakınlığından aynı aracı tanır."""
        if vid in self.ihlal_idleri:
            return True
        for gx, gy, gsn, _ in self.ihlal_konumlari:
            if sn - gsn < self.TEKRAR_SURE:
                if ((mx - gx) ** 2 + (my - gy) ** 2) ** 0.5 < self.TEKRAR_MESAFE:
                    self.ihlal_idleri.add(vid)
                    return True
        return False

    def _icinde(self, bolge, nokta):
        return cv2.pointPolygonTest(bolge, (float(nokta[0]), float(nokta[1])), False) >= 0

    def kare_isle(self, frame, cizim=True):
        """
        Tek bir kareyi işler.
        Döndürür: {"yaya_var": bool, "ihlaller": [...], "araclar": [...]}
        cizim=True ise kutular, plakalar ve bölgeler kare üzerine çizilir.
        """
        self.kare_no += 1
        sn = self.kare_no / self.fps

        sonuc = self.model.track(frame, persist=True, tracker="bytetrack.yaml",
                                 conf=self.guven, verbose=False)[0]

        yayalar = []   # (x1, y1, x2, y2, gecitte_mi)
        araclar = []
        gecitteki_yaya_sayisi = 0

        if sonuc.boxes is not None and len(sonuc.boxes) > 0:
            kutular = sonuc.boxes.xyxy.cpu().numpy()
            siniflar = sonuc.boxes.cls.cpu().numpy().astype(int)
            if sonuc.boxes.id is not None:
                idler = sonuc.boxes.id.cpu().numpy().astype(int)
            else:
                idler = list(range(len(kutular)))

            for kutu, cls_id, vid in zip(kutular, siniflar, idler):
                x1, y1, x2, y2 = map(int, kutu)
                alt_orta = ((x1 + x2) // 2, y2)
                if cls_id == 0:
                    gecitte = self._icinde(self.yaya_bolgesi, alt_orta)
                    yayalar.append((x1, y1, x2, y2, gecitte))
                    if gecitte:
                        gecitteki_yaya_sayisi += 1
                elif cls_id in ARAC_SINIFLARI:
                    araclar.append((x1, y1, x2, y2, int(vid), alt_orta, cls_id))

        yaya_var = gecitteki_yaya_sayisi > 0

        if cizim:
            overlay = frame.copy()
            yaya_renk = (0, 165, 255) if yaya_var else (0, 255, 0)
            cv2.polylines(frame, [self.yaya_bolgesi], True, yaya_renk, 2)
            cv2.fillPoly(overlay, [self.yaya_bolgesi], yaya_renk)
            cv2.polylines(frame, [self.durma_bolgesi], True, (255, 100, 0), 2)
            cv2.fillPoly(overlay, [self.durma_bolgesi], (255, 100, 0))
            cv2.addWeighted(overlay, 0.25, frame, 0.75, 0, frame)
            for x1, y1, x2, y2, gecitte in yayalar:
                renk = (0, 0, 255) if gecitte else (255, 255, 0)
                cv2.rectangle(frame, (x1, y1), (x2, y2), renk, 2)

        ihlaller = []
        gorunen_araclar = []

        for x1, y1, x2, y2, vid, alt_orta, cls_id in araclar:
            tur_adi = ARAC_SINIFLARI.get(cls_id, "Motorlu Araç")
            gorunen_araclar.append({"vid": vid, "bbox": (x1, y1, x2, y2), "tur": tur_adi})

            bolgede = self._icinde(self.durma_bolgesi, alt_orta) or self._icinde(self.yaya_bolgesi, alt_orta)
            hiz = self._hiz_hesapla(vid, alt_orta[0], alt_orta[1], max(x2 - x1, 1))
            hareketli = hiz is not None and hiz > self.DURMA_ESIGI
            durdu = hiz is not None and hiz <= self.DURMA_ESIGI

            # İhlal: geçitte yaya var + araç bölgede + araç DURMUYOR (hareket halinde)
            ihlal = yaya_var and bolgede and hareketli

            if ihlal:
                mx, my = (x1 + x2) // 2, (y1 + y2) // 2
                if not self._ayni_arac_mi(mx, my, vid, sn):
                    self.ihlal_idleri.add(vid)
                    self.ihlal_konumlari.append((mx, my, sn, vid))
                    ihlaller.append({
                        "vid": vid,
                        "tur": tur_adi,
                        "sn": round(sn, 2),
                        "kare": self.kare_no,
                        "merkez": (mx, my),
                        "bbox": (x1, y1, x2, y2),
                    })

            if cizim:
                plaka_bilgi = self.arac_plakalari.get(vid)
                plaka_metin = plaka_bilgi["plaka"] if plaka_bilgi else None

                if ihlal or (vid in self.ihlal_idleri):
                    kutu_renk = (0, 0, 255)
                    kalinlik = 3
                    ust_etiket = f"IHLAL! #{vid}" + (f" [{plaka_metin}]" if plaka_metin else "")
                elif yaya_var and bolgede and durdu:
                    kutu_renk = (255, 200, 0)
                    kalinlik = 2
                    ust_etiket = f"DURDU #{vid}" + (f" [{plaka_metin}]" if plaka_metin else "")
                else:
                    kutu_renk = (0, 255, 0)
                    kalinlik = 2
                    ust_etiket = f"#{vid} {tur_adi}" + (f" | {plaka_metin}" if plaka_metin else "")

                cv2.rectangle(frame, (x1, y1), (x2, y2), kutu_renk, kalinlik)

                # Okunaklı etiket arka planı ve metni çiz
                (tw, th), _ = cv2.getTextSize(ust_etiket, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
                ey = max(y1, th + 10)
                cv2.rectangle(frame, (x1, ey - th - 8), (x1 + tw + 10, ey), kutu_renk, -1)
                yazi_renk = (255, 255, 255) if kutu_renk == (0, 0, 255) else (0, 0, 0)
                cv2.putText(frame, ust_etiket, (x1 + 5, ey - 4),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, yazi_renk, 2)

                # Eğer plaka okunduysa araç üzerinde plaka kutusunu da mavi çerçeveyle vurgula
                if plaka_bilgi:
                    rel = plaka_bilgi.get("rel_kutu")
                    if rel:
                        bw, bh = x2 - x1, y2 - y1
                        px1 = int(x1 + rel[0] * bw)
                        py1 = int(y1 + rel[1] * bh)
                        px2 = int(x1 + rel[2] * bw)
                        py2 = int(y1 + rel[3] * bh)
                        cv2.rectangle(frame, (px1, py1), (px2, py2), (255, 140, 0), 2)
                        cv2.putText(frame, f"PLAKA: {plaka_metin}", (px1, max(15, py1 - 6)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 200, 0), 2)

        # Eski araç geçmişlerini periyodik temizle
        if self.kare_no % 150 == 0:
            for eski in [k for k, g in self.arac_gecmisi.items() if self.kare_no - g[-1][0] > 90]:
                del self.arac_gecmisi[eski]

        return {"yaya_var": yaya_var, "ihlaller": ihlaller, "araclar": gorunen_araclar}
