"""
TÃœBÄ°TAK Projesi: Etiketleme AracÄ± (GerÃ§ek Ä°hlalleri Ä°ÅŸaretleme)
--------------------------------------------------------------
Videoyu izlerken GERÃ‡EK kural ihlallerinin olduÄŸu anlarÄ± iÅŸaretlersiniz.
Bu iÅŸaretler "doÄŸru cevap" (ground truth) olarak kaydedilir ve sistemin
doÄŸruluÄŸunu Ã¶lÃ§mek iÃ§in degerlendir.py tarafÄ±ndan kullanÄ±lÄ±r.

KullanÄ±m:
    python etiketle.py                 (video seÃ§me penceresi aÃ§Ä±lÄ±r)
    python etiketle.py video_yolu.mp4

TuÅŸlar:
    BOÅLUK  : Oynat / Duraklat
    i       : Åu anÄ± "GERÃ‡EK Ä°HLAL" olarak iÅŸaretle
    u       : Son iÅŸareti geri al
    a / d   : 1 kare geri / ileri (duraklatÄ±lmÄ±ÅŸken)
    j / l   : 2 saniye geri / ileri
    r       : Bu video iÃ§in yaya geÃ§idi + durma Ã§izgisi bÃ¶lgesini fareyle Ã§iz
    s       : Kaydet
    q       : Kaydet ve Ã§Ä±k

Ä°hlal sayÄ±lacak durum: geÃ§itte yaya varken, aracÄ±n durmayÄ±p geÃ§mesi.
AracÄ±n geÃ§itten Ã‡IKTIÄI an deÄŸil, geÃ§ide GÄ°RÄ°P durmadÄ±ÄŸÄ± an iÅŸaretlenmelidir.
"""

import cv2
import json
import os
import sys
import time
import numpy as np

KLASOR = os.path.dirname(os.path.abspath(__file__))
ETIKET_DIZINI = os.path.join(KLASOR, "etiketler")
MAX_W, MAX_H = 1100, 640


def video_sec():
    import tkinter as tk
    from tkinter import filedialog
    k = tk.Tk()
    k.withdraw()
    k.attributes("-topmost", True)
    yol = filedialog.askopenfilename(
        title="Etiketlenecek videoyu seÃ§",
        filetypes=[("Video", "*.mp4 *.avi *.mov *.mkv *.webm"), ("TÃ¼mÃ¼", "*.*")],
    )
    k.destroy()
    return yol


def main():
    yol = sys.argv[1] if len(sys.argv) > 1 else video_sec()
    if not yol or not os.path.exists(yol):
        print("[HATA] Video seÃ§ilmedi veya bulunamadÄ±.")
        return

    cap = cv2.VideoCapture(yol)
    if not cap.isOpened():
        print("[HATA] Video aÃ§Ä±lamadÄ±.")
        return

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    toplam = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    os.makedirs(ETIKET_DIZINI, exist_ok=True)
    ad = os.path.splitext(os.path.basename(yol))[0]
    etiket_yolu = os.path.join(ETIKET_DIZINI, ad + ".json")

    veri = {"video_yolu": os.path.abspath(yol), "ihlaller_sn": [],
            "yaya_oranlari": None, "durma_oranlari": None}
    if os.path.exists(etiket_yolu):
        with open(etiket_yolu, "r", encoding="utf-8-sig") as f:
            veri.update(json.load(f))
        print(f"[BÄ°LGÄ°] Mevcut etiketler yÃ¼klendi: {len(veri['ihlaller_sn'])} ihlal")

    oran = min(MAX_W / w, MAX_H / h, 2.0)
    gw, gh = int(w * oran), int(h * oran)

    durum = {"bolge_modu": False, "tiklar": []}

    def fare(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN and durum["bolge_modu"] and len(durum["tiklar"]) < 8:
            durum["tiklar"].append((x / gw, y / gh))

    pencere = "Etiketleme Araci - " + ad
    cv2.namedWindow(pencere, cv2.WINDOW_AUTOSIZE)
    cv2.setMouseCallback(pencere, fare)

    def kare_oku(i):
        i = max(0, min(i, max(toplam - 1, 0)))
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ret, f = cap.read()
        return i, (f if ret else None)

    def kaydet():
        veri["ihlaller_sn"] = sorted(veri["ihlaller_sn"])
        with open(etiket_yolu, "w", encoding="utf-8") as f:
            json.dump(veri, f, ensure_ascii=False, indent=2)
        print(f"[KAYDEDÄ°LDÄ°] {etiket_yolu} | {len(veri['ihlaller_sn'])} ihlal")

    def poligon_ciz(ekran, oranlar, renk):
        pts = np.array([[int(x * gw), int(y * gh)] for x, y in oranlar], np.int32)
        cv2.polylines(ekran, [pts], len(pts) == 4, renk, 2)
        for p in pts:
            cv2.circle(ekran, tuple(int(c) for c in p), 4, renk, -1)

    kare, frame = kare_oku(0)
    oynuyor = False
    flash_bitis = 0.0

    while True:
        if oynuyor:
            ret, f = cap.read()
            if ret:
                frame = f
                kare += 1
            else:
                oynuyor = False
        if frame is None:
            break

        ekran = cv2.resize(frame, (gw, gh))

        # BÃ¶lgeler (kayÄ±tlÄ±)
        if veri["yaya_oranlari"] and veri["durma_oranlari"] and not durum["bolge_modu"]:
            poligon_ciz(ekran, veri["yaya_oranlari"], (0, 255, 0))
            poligon_ciz(ekran, veri["durma_oranlari"], (255, 140, 0))

        # BÃ¶lge Ã§izim modu
        if durum["bolge_modu"]:
            t = durum["tiklar"]
            if t[:4]:
                poligon_ciz(ekran, t[:4], (0, 255, 0))
            if t[4:]:
                poligon_ciz(ekran, t[4:], (255, 140, 0))
            if len(t) < 4:
                mesaj = f"YAYA GECIDI: 4 kosesine tiklayin ({len(t)}/4)"
            elif len(t) < 8:
                mesaj = f"DURMA CIZGISI: 4 kosesine tiklayin ({len(t) - 4}/4)"
            else:
                mesaj = "ENTER=kaydet | BACKSPACE=geri al | ESC=iptal"
            cv2.rectangle(ekran, (0, gh - 30), (gw, gh), (0, 0, 0), -1)
            cv2.putText(ekran, mesaj, (10, gh - 9), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        else:
            cv2.rectangle(ekran, (0, gh - 30), (gw, gh), (0, 0, 0), -1)
            yardim = "SPACE:oynat  i:ISARETLE  u:geri al  a/d:kare  j/l:2sn  r:bolge  s:kaydet  q:cik"
            cv2.putText(ekran, yardim, (10, gh - 9), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        # Ãœst bilgi Ã§ubuÄŸu
        sn = kare / fps
        yakin = [x for x in veri["ihlaller_sn"] if abs(x - sn) < 1.0]
        cv2.rectangle(ekran, (0, 0), (gw, 32), (0, 0, 0), -1)
        bilgi = (f"{sn:6.2f}s | kare {kare}/{toplam} | "
                 f"{'OYNUYOR' if oynuyor else 'DURAKLADI'} | ISARET: {len(veri['ihlaller_sn'])}")
        cv2.putText(ekran, bilgi, (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        if yakin:
            cv2.putText(ekran, "[ISARETLI ANA YAKIN]", (gw - 260, 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        if time.time() < flash_bitis:
            cv2.putText(ekran, "ISARETLENDI!", (gw // 2 - 110, gh // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)

        cv2.imshow(pencere, ekran)
        bekle = max(1, int(1000 / fps)) if oynuyor else 30
        tus = cv2.waitKey(bekle) & 0xFF

        if cv2.getWindowProperty(pencere, cv2.WND_PROP_VISIBLE) < 1:
            break

        if durum["bolge_modu"]:
            if tus == 13 and len(durum["tiklar"]) == 8:
                veri["yaya_oranlari"] = durum["tiklar"][:4]
                veri["durma_oranlari"] = durum["tiklar"][4:]
                durum["bolge_modu"] = False
                print("[BÄ°LGÄ°] Bu video iÃ§in bÃ¶lgeler kaydedildi (s ile dosyaya yazÄ±lÄ±r).")
            elif tus == 8 and durum["tiklar"]:
                durum["tiklar"].pop()
            elif tus == 27:
                durum["bolge_modu"] = False
            continue

        if tus == ord(" "):
            oynuyor = not oynuyor
        elif tus == ord("i"):
            veri["ihlaller_sn"].append(round(sn, 2))
            flash_bitis = time.time() + 0.8
            print(f"[ISARET] {sn:.2f}. saniye")
        elif tus == ord("u") and veri["ihlaller_sn"]:
            silinen = veri["ihlaller_sn"].pop()
            print(f"[GERÄ° ALINDI] {silinen}. saniye")
        elif tus == ord("d"):
            oynuyor = False
            kare, frame = kare_oku(kare + 1)
        elif tus == ord("a"):
            oynuyor = False
            kare, frame = kare_oku(kare - 1)
        elif tus == ord("l"):
            kare, frame = kare_oku(kare + int(2 * fps))
        elif tus == ord("j"):
            kare, frame = kare_oku(kare - int(2 * fps))
        elif tus == ord("r"):
            oynuyor = False
            durum["bolge_modu"] = True
            durum["tiklar"] = []
        elif tus == ord("s"):
            kaydet()
        elif tus == ord("q"):
            break

    kaydet()
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
