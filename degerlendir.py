"""
TÃœBÄ°TAK Projesi: BaÅŸarÄ± DeÄŸerlendirme AracÄ±
--------------------------------------------------------------
etiketler/ klasÃ¶rÃ¼ndeki "gerÃ§ek ihlal" iÅŸaretlerini, sistemin otomatik
tespitleriyle karÅŸÄ±laÅŸtÄ±rÄ±r ve doÄŸruluk metriklerini hesaplar:

    Kesinlik (Precision) : Sistemin "ihlal" dediklerinin kaÃ§Ä± gerÃ§ekten ihlal?
    DuyarlÄ±lÄ±k (Recall)  : GerÃ§ek ihlallerin kaÃ§Ä±nÄ± sistem yakaladÄ±?
    F1 Skoru             : Ä°kisinin dengesi

KullanÄ±m:
    python degerlendir.py
    python degerlendir.py --tolerans 3.0
    python degerlendir.py --video Yaya_Gecidi_Test_1

Ã–nce etiketle.py ile videolarÄ± etiketleyin.
"""

import argparse
import csv
import glob
import json
import os
import time
from datetime import datetime

import cv2
from ultralytics import YOLO

from tespit_cekirdegi import YayaGecidiCekirdek

KLASOR = os.path.dirname(os.path.abspath(__file__))
ETIKET_DIZINI = os.path.join(KLASOR, "etiketler")
CIKTI_DIZINI = os.path.join(KLASOR, "output", "degerlendirme")
BOLGE_AYAR_DOSYASI = os.path.join(KLASOR, "bolge_ayarlari.json")


def ortak_bolge_yukle():
    if os.path.exists(BOLGE_AYAR_DOSYASI):
        try:
            with open(BOLGE_AYAR_DOSYASI, "r", encoding="utf-8-sig") as f:
                v = json.load(f)
            if v.get("yaya_oranlari") and v.get("durma_oranlari"):
                return v["yaya_oranlari"], v["durma_oranlari"]
        except Exception:
            pass
    return None, None


def videoyu_calistir(model, yol, yaya, durma):
    """Videoyu arayÃ¼zsÃ¼z iÅŸler; (tespit_saniyeleri, kare_sayisi, sure) dÃ¶ndÃ¼rÃ¼r."""
    cap = cv2.VideoCapture(yol)
    if not cap.isOpened():
        raise RuntimeError(f"Video aÃ§Ä±lamadÄ±: {yol}")
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    toplam = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    cekirdek = YayaGecidiCekirdek(model, w, h, fps, yaya, durma)
    tespitler = []
    baslangic = time.time()
    kare = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        kare += 1
        sonuc = cekirdek.kare_isle(frame, cizim=False)
        for olay in sonuc["ihlaller"]:
            tespitler.append(olay["sn"])
        if kare % 100 == 0:
            print(f"    ... {kare}/{toplam} kare")
    cap.release()
    return tespitler, kare, time.time() - baslangic


def eslestir(gercek, tespit, tolerans):
    """Her gerÃ§ek ihlali, tolerans iÃ§indeki en yakÄ±n tespitle eÅŸleÅŸtirir."""
    kullanilan = set()
    dogru, kacirilan = [], []
    for g in sorted(gercek):
        en_iyi, fark = None, 1e9
        for i, t in enumerate(tespit):
            if i in kullanilan:
                continue
            d = abs(t - g)
            if d <= tolerans and d < fark:
                en_iyi, fark = i, d
        if en_iyi is None:
            kacirilan.append(g)
        else:
            kullanilan.add(en_iyi)
            dogru.append((g, tespit[en_iyi]))
    yanlis_alarm = [t for i, t in enumerate(tespit) if i not in kullanilan]
    return dogru, kacirilan, yanlis_alarm


def oran(a, b):
    return a / b if b > 0 else None


def yuzde(x):
    return "-" if x is None else f"%{x * 100:.1f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tolerans", type=float, default=2.5,
                    help="Tespit ile iÅŸaret arasÄ±nda kabul edilen en bÃ¼yÃ¼k fark (saniye)")
    ap.add_argument("--video", nargs="*", help="Sadece bu etiket adlarÄ±nÄ± deÄŸerlendir")
    args = ap.parse_args()

    dosyalar = sorted(glob.glob(os.path.join(ETIKET_DIZINI, "*.json")))
    if args.video:
        dosyalar = [d for d in dosyalar if os.path.splitext(os.path.basename(d))[0] in args.video]
    if not dosyalar:
        print("[HATA] etiketler/ klasÃ¶rÃ¼nde etiket yok. Ã–nce 'python etiketle.py' ile videolarÄ± etiketleyin.")
        return

    ortak_yaya, ortak_durma = ortak_bolge_yukle()
    print("[BÄ°LGÄ°] Model yÃ¼kleniyor...")
    model = YOLO(os.path.join(KLASOR, "yolov8n.pt"))

    satirlar = []
    for d in dosyalar:
        with open(d, "r", encoding="utf-8-sig") as f:
            etiket = json.load(f)
        ad = os.path.splitext(os.path.basename(d))[0]
        yol = etiket.get("video_yolu")
        if not yol or not os.path.exists(yol):
            print(f"[ATLANDI] {ad}: video dosyasÄ± bulunamadÄ± ({yol})")
            continue

        if etiket.get("yaya_oranlari") and etiket.get("durma_oranlari"):
            yaya, durma, kaynak = etiket["yaya_oranlari"], etiket["durma_oranlari"], "videoya Ã¶zel"
        elif ortak_yaya:
            yaya, durma, kaynak = ortak_yaya, ortak_durma, "ortak ayar"
        else:
            yaya, durma, kaynak = None, None, "varsayÄ±lan"

        print(f"[Ä°ÅLENÄ°YOR] {ad} (bÃ¶lge: {kaynak})")
        tespit, kare, sure = videoyu_calistir(model, yol, yaya, durma)
        gercek = etiket.get("ihlaller_sn", [])
        dogru, kacirilan, yanlis = eslestir(gercek, tespit, args.tolerans)

        tp, fn, fp = len(dogru), len(kacirilan), len(yanlis)
        satirlar.append({
            "video": ad, "bolge": kaynak, "gercek": len(gercek), "tespit": len(tespit),
            "tp": tp, "fp": fp, "fn": fn,
            "kesinlik": oran(tp, tp + fp), "duyarlilik": oran(tp, tp + fn),
            "isleme_fps": kare / sure if sure > 0 else 0,
            "dogru": dogru, "kacirilan": kacirilan, "yanlis": yanlis,
        })
        print(f"    GerÃ§ek: {len(gercek)} | Tespit: {len(tespit)} | DoÄŸru: {tp} | "
              f"YanlÄ±ÅŸ alarm: {fp} | KaÃ§Ä±rÄ±lan: {fn}")

    if not satirlar:
        print("[HATA] DeÄŸerlendirilecek video kalmadÄ±.")
        return

    T_TP = sum(s["tp"] for s in satirlar)
    T_FP = sum(s["fp"] for s in satirlar)
    T_FN = sum(s["fn"] for s in satirlar)
    kes = oran(T_TP, T_TP + T_FP)
    duy = oran(T_TP, T_TP + T_FN)
    f1 = oran(2 * kes * duy, kes + duy) if kes is not None and duy is not None and (kes + duy) > 0 else None
    ort_fps = sum(s["isleme_fps"] for s in satirlar) / len(satirlar)

    os.makedirs(CIKTI_DIZINI, exist_ok=True)

    # CSV
    csv_yolu = os.path.join(CIKTI_DIZINI, "degerlendirme.csv")
    with open(csv_yolu, "w", newline="", encoding="utf-8-sig") as f:
        yz = csv.writer(f, delimiter=";")
        yz.writerow(["Video", "BÃ¶lge", "GerÃ§ek Ä°hlal", "Tespit", "DoÄŸru (TP)", "YanlÄ±ÅŸ Alarm (FP)",
                     "KaÃ§Ä±rÄ±lan (FN)", "Kesinlik", "DuyarlÄ±lÄ±k", "Ä°ÅŸleme FPS"])
        for s in satirlar:
            yz.writerow([s["video"], s["bolge"], s["gercek"], s["tespit"], s["tp"], s["fp"], s["fn"],
                         yuzde(s["kesinlik"]), yuzde(s["duyarlilik"]), f"{s['isleme_fps']:.1f}"])
        yz.writerow(["TOPLAM", "", sum(s["gercek"] for s in satirlar), sum(s["tespit"] for s in satirlar),
                     T_TP, T_FP, T_FN, yuzde(kes), yuzde(duy), f"{ort_fps:.1f}"])

    # Markdown rapor
    md = []
    md.append("# BaÅŸarÄ± DeÄŸerlendirme Raporu\n")
    md.append(f"- Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    md.append(f"- EÅŸleÅŸme toleransÄ±: Â±{args.tolerans} saniye")
    md.append(f"- Durma eÅŸiÄŸi: {YayaGecidiCekirdek.DURMA_ESIGI} (araÃ§ geniÅŸliÄŸi/sn)")
    md.append(f"- DeÄŸerlendirilen video sayÄ±sÄ±: {len(satirlar)}\n")
    md.append("## Genel SonuÃ§\n")
    md.append("| Ã–lÃ§Ã¼t | DeÄŸer |")
    md.append("| :--- | :--- |")
    md.append(f"| GerÃ§ek ihlal sayÄ±sÄ± | {sum(s['gercek'] for s in satirlar)} |")
    md.append(f"| DoÄŸru tespit (TP) | {T_TP} |")
    md.append(f"| YanlÄ±ÅŸ alarm (FP) | {T_FP} |")
    md.append(f"| KaÃ§Ä±rÄ±lan ihlal (FN) | {T_FN} |")
    md.append(f"| **Kesinlik (Precision)** | **{yuzde(kes)}** |")
    md.append(f"| **DuyarlÄ±lÄ±k (Recall)** | **{yuzde(duy)}** |")
    md.append(f"| **F1 Skoru** | **{yuzde(f1)}** |")
    md.append(f"| Ortalama iÅŸleme hÄ±zÄ± | {ort_fps:.1f} kare/sn |\n")
    md.append("## Videolara GÃ¶re\n")
    md.append("| Video | BÃ¶lge | GerÃ§ek | Tespit | TP | FP | FN | Kesinlik | DuyarlÄ±lÄ±k |")
    md.append("| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for s in satirlar:
        md.append(f"| {s['video']} | {s['bolge']} | {s['gercek']} | {s['tespit']} | {s['tp']} | {s['fp']} | "
                  f"{s['fn']} | {yuzde(s['kesinlik'])} | {yuzde(s['duyarlilik'])} |")
    md.append("\n## Hata Analizi (Hangi anlarda yanÄ±ldÄ±?)\n")
    for s in satirlar:
        md.append(f"### {s['video']}")
        md.append(f"- KaÃ§Ä±rÄ±lan ihlaller (saniye): {s['kacirilan'] or 'yok'}")
        md.append(f"- YanlÄ±ÅŸ alarmlar (saniye): {s['yanlis'] or 'yok'}\n")
    md_yolu = os.path.join(CIKTI_DIZINI, "degerlendirme_raporu.md")
    with open(md_yolu, "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    print("\n" + "=" * 54)
    print(f" GENEL: Kesinlik {yuzde(kes)} | DuyarlÄ±lÄ±k {yuzde(duy)} | F1 {yuzde(f1)}")
    print(f" TP={T_TP}  FP={T_FP}  FN={T_FN}  | HÄ±z: {ort_fps:.1f} kare/sn")
    print("=" * 54)
    print(f"Rapor : {md_yolu}")
    print(f"Excel : {csv_yolu}")


if __name__ == "__main__":
    main()
