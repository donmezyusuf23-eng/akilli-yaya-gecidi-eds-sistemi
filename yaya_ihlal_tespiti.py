"""
Akıllı Yaya Geçidi Kural İhlali Tespit Sistemi
--------------------------------------------------------------
Yazarlar: Öğrenci & Antigravity
Amaç: Yaya geçidinde yaya varken durmayan / yayaya yol vermeyen
      araçları yapay zekâ (YOLOv8) ve görüntü işleme algoritmalarıyla
      otomatik olarak tespit edip kanıt görüntüsü ve log kaydetmek.
"""

import cv2
import numpy as np
from datetime import datetime
import os
import time
import argparse
from ultralytics import YOLO

class YayaGecidiDenetleyici:
    def __init__(self, model_yolu="yolov8n.pt", kayit_dizini="output"):
        print("[BİLGİ] YOLOv8 yapay zekâ modeli yükleniyor...")
        self.model = YOLO(model_yolu)
        self.kayit_dizini = kayit_dizini
        self.ihlal_klasoru = os.path.join(kayit_dizini, "ihlaller")
        os.makedirs(self.ihlal_klasoru, exist_ok=True)
        
        # COCO Sınıf Kodları:
        # 0: person (yaya)
        # 1: bicycle (bisiklet)
        # 2: car, 3: motorcycle, 5: bus, 7: truck (araçlar)
        self.yaya_siniflari = [0]
        self.arac_siniflari = [2, 3, 5, 7]
        
        # İstatistikler
        self.toplam_ihlal = 0
        self.ihlal_arac_idleri = set() # Aynı araca mükerrer ceza kesmemek için

    def oranlari_koordinata_cevir(self, oran_listesi, genislik, yukseklik):
        """Yüzdelik oranları [0.0 - 1.0] ekranın gerçek piksel koordinatlarına dönüştürür."""
        noktalar = []
        for x_oran, y_oran in oran_listesi:
            noktalar.append([int(x_oran * genislik), int(y_oran * yukseklik)])
        return np.array(noktalar, np.int32)

    def nokta_bolgede_mi(self, nokta, bolge):
        """Bir noktanın (x, y) poligon alanı içinde olup olmadığını test eder."""
        return cv2.pointPolygonTest(bolge, (float(nokta[0]), float(nokta[1])), False) >= 0

    def calistir(self, kaynak=0, ekranda_goster=True, video_kaydet=True):
        """
        kaynak: Bir video dosyası yolu ("data/ornek_trafik.mp4") veya webcam için 0
        """
        cap = cv2.VideoCapture(kaynak)
        
        if not cap.isOpened():
            print(f"[HATA] Video kaynağı açılamadı: {kaynak}")
            return

        genislik = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        yukseklik = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        kaynak_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        
        print(f"[BİLGİ] Video Boyutu: {genislik}x{yukseklik} | FPS: {kaynak_fps:.1f}")

        # Her çözünürlüğe otomatik uyarlanan dinamik bölgeler:
        # 1. Yaya Geçidi Bölgesi
        yaya_oranlari = [(0.25, 0.45), (0.75, 0.45), (0.90, 0.85), (0.10, 0.85)]
        yaya_bolgesi = self.oranlari_koordinata_cevir(yaya_oranlari, genislik, yukseklik)

        # 2. Araç Durma Çizgisi Bölgesi (Geçidin hemen önü)
        durma_oranlari = [(0.20, 0.35), (0.80, 0.35), (0.75, 0.44), (0.25, 0.44)]
        durma_bolgesi = self.oranlari_koordinata_cevir(durma_oranlari, genislik, yukseklik)

        # Çıkış videosu kaydedici (Opsiyonel)
        video_yazici = None
        if video_kaydet:
            cikti_video_yolu = os.path.join(self.kayit_dizini, "denetim_sonucu.mp4")
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            video_yazici = cv2.VideoWriter(cikti_video_yolu, fourcc, kaynak_fps, (genislik, yukseklik))
            print(f"[BİLGİ] İşlenmiş video kaydediliyor: {cikti_video_yolu}")

        print("[BİLGİ] Sistem aktif! Pencereyi kapatmak için görüntü penceresindeyken 'q' tuşuna basınız.")
        fps_zaman = time.time()
        fps = 0
        kare_no = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                print("[BİLGİ] Video akışı sona erdi.")
                break

            kare_no += 1
            
            # Nesne Tespiti ve Takip (Ultralytics ByteTrack)
            sonuclar = self.model.track(frame, persist=True, verbose=False)[0]

            yaya_kutulari = []
            arac_kutulari = []
            gecitteki_yayalar = []

            if sonuclar.boxes is not None:
                kutular = sonuclar.boxes.xyxy.cpu().numpy()
                siniflar = sonuclar.boxes.cls.cpu().numpy().astype(int)
                
                # Takip ID'leri
                if sonuclar.boxes.id is not None:
                    takip_idleri = sonuclar.boxes.id.cpu().numpy().astype(int)
                else:
                    takip_idleri = [i for i in range(len(kutular))]

                for kutu, sinif_id, takip_id in zip(kutular, siniflar, takip_idleri):
                    x1, y1, x2, y2 = map(int, kutu)
                    alt_orta_nokta = ((x1 + x2) // 2, y2) # Nesnenin yere temas ettiği nokta

                    if sinif_id in self.yaya_siniflari:
                        yaya_kutulari.append((x1, y1, x2, y2, takip_id))
                        if self.nokta_bolgede_mi(alt_orta_nokta, yaya_bolgesi):
                            gecitteki_yayalar.append((x1, y1, x2, y2, takip_id))

                    elif sinif_id in self.arac_siniflari:
                        arac_kutulari.append((x1, y1, x2, y2, takip_id, alt_orta_nokta))

            # Yaya geçidinde yaya var mı?
            yaya_gecitte_var = len(gecitteki_yayalar) > 0

            # Bölgeleri yarı saydam çiz
            overlay = frame.copy()
            yaya_renk = (0, 165, 255) if yaya_gecitte_var else (0, 255, 0)
            cv2.polylines(frame, [yaya_bolgesi], True, yaya_renk, 2)
            cv2.fillPoly(overlay, [yaya_bolgesi], yaya_renk)

            cv2.polylines(frame, [durma_bolgesi], True, (255, 100, 0), 2)
            cv2.fillPoly(overlay, [durma_bolgesi], (255, 100, 0))

            cv2.addWeighted(overlay, 0.25, frame, 0.75, 0, frame)

            # Yayaları Çiz
            for x1, y1, x2, y2, pid in yaya_kutulari:
                gecitte_mi = any(pid == y[4] for y in gecitteki_yayalar)
                renk = (0, 0, 255) if gecitte_mi else (255, 255, 0)
                cv2.rectangle(frame, (x1, y1), (x2, y2), renk, 2)
                etiket = f"Yaya #{pid} (GECITTE)" if gecitte_mi else f"Yaya #{pid}"
                cv2.putText(frame, etiket, (x1, max(y1 - 8, 15)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, renk, 2)

            # Araçları ve İhlal Durumunu İncele
            for x1, y1, x2, y2, vid, alt_nokta in arac_kutulari:
                arac_durma_alaninda = self.nokta_bolgede_mi(alt_nokta, durma_bolgesi)
                arac_yaya_alaninda = self.nokta_bolgede_mi(alt_nokta, yaya_bolgesi)

                # İhlal Kriteri: Yaya geçitteyken araç durma çizgisini aşarsa
                ihlal = yaya_gecitte_var and (arac_durma_alaninda or arac_yaya_alaninda)

                if ihlal:
                    renk = (0, 0, 255)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), renk, 3)
                    cv2.putText(frame, f"IHLAL! Arac #{vid}", (x1, max(y1 - 8, 15)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, renk, 2)

                    if vid not in self.ihlal_arac_idleri:
                        self.ihlal_arac_idleri.add(vid)
                        self.toplam_ihlal += 1
                        
                        zaman_damgasi = datetime.now().strftime("%Y%m%d_%H%M%S")
                        kanit_dosyasi = os.path.join(self.ihlal_klasoru, f"ihlal_{zaman_damgasi}_arac{vid}.jpg")
                        cv2.imwrite(kanit_dosyasi, frame)
                        print(f"-> [CEZA/İHLAL] Araç #{vid} durmadı! Kanıt kaydedildi: {kanit_dosyasi}")
                else:
                    renk = (0, 255, 0)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), renk, 2)
                    cv2.putText(frame, f"Arac #{vid}", (x1, max(y1 - 8, 15)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, renk, 1)

            # FPS Hesaplama
            simdiki_zaman = time.time()
            fps = int(1 / (simdiki_zaman - fps_zaman + 1e-6))
            fps_zaman = simdiki_zaman

            # Sol Üst Bilgi Paneli
            self._bilgi_paneli_ciz(frame, yaya_gecitte_var, fps)

            # Video Kaydet
            if video_yazici:
                video_yazici.write(frame)

            # Canlı Gösterim
            if ekranda_goster:
                cv2.imshow("Akilli Yaya Gecidi Denetimi", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

        cap.release()
        if video_yazici:
            video_yazici.release()
        if ekranda_goster:
            cv2.destroyAllWindows()

        print("-" * 50)
        print(f"[SONUÇ RAPORU] İşlem tamamlandı.")
        print(f"Toplam Tespit Edilen İhlal Sayısı: {self.toplam_ihlal}")
        if self.ihlal_arac_idleri:
            print(f"İhlal Yapan Araç ID'leri: {list(self.ihlal_arac_idleri)}")
        print("-" * 50)

    def _bilgi_paneli_ciz(self, frame, yaya_var, fps):
        cv2.rectangle(frame, (10, 10), (380, 115), (20, 20, 20), -1)
        cv2.rectangle(frame, (10, 10), (380, 115), (100, 100, 100), 2)

        cv2.putText(frame, "AKILLI YAYA GECIDI DENETIMI", (20, 32),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

        durum_metni = "GECITTE YAYA VAR" if yaya_var else "Gecit Bos"
        durum_renk = (0, 140, 255) if yaya_var else (0, 255, 0)
        cv2.putText(frame, f"Durum: {durum_metni}", (20, 58),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, durum_renk, 2)

        cv2.putText(frame, f"Toplam Ihlal Sayisi: {self.toplam_ihlal}", (20, 84),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

        cv2.putText(frame, f"FPS: {fps} | Cikis: 'q'", (20, 105),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (180, 180, 180), 1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Akıllı Yaya Geçidi Kural İhlali Tespit Sistemi")
    parser.add_argument("--webcam", action="store_true", help="Webcam kamerasını kullan")
    parser.add_argument("--video", type=str, default=None, help="Özel video dosyasının yolu")
    parser.add_argument("--no-gui", action="store_true", help="Ekranda pencere açmadan arka planda işle")
    args = parser.parse_args()

    script_dizini = os.path.dirname(os.path.abspath(__file__))
    model_dosyasi = os.path.join(script_dizini, "yolov8n.pt")
    
    denetleyici = YayaGecidiDenetleyici(
        model_yolu=model_dosyasi, 
        kayit_dizini=os.path.join(script_dizini, "output")
    )

    if args.webcam:
        kaynak = 0
        print("[BAŞLANGIÇ] Webcam (0) başlatılıyor...")
    elif args.video:
        kaynak = args.video
        print(f"[BAŞLANGIÇ] Belirtilen video işleniyor: {kaynak}")
    else:
        kaynak = os.path.join(script_dizini, "data", "ornek_trafik.mp4")
        print(f"[BAŞLANGIÇ] Örnek video işleniyor: {kaynak}")

    denetleyici.calistir(kaynak=kaynak, ekranda_goster=not args.no_gui, video_kaydet=True)
