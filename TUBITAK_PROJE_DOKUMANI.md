# TÜBİTAK PROJE ÖNERİ FORMU VE TEKNİK DOKÜMANTASYON

## 1. PROJE ADI
**Yapay Zekâ ve Bilgisayarlı Görü Tabanlı Akıllı Yaya Geçidi Kural İhlali Tespit ve Erken Uyarı Sistemi**

---

## 2. PROJENİN AMACI
Trafik kazalarında can kaybı ve yaralanmaların önemli bir bölümü yaya geçitlerinde meydana gelmektedir. Karayolları Trafik Kanunu’nda yayaların geçiş üstünlüğü açıkça belirtilmiş olmasına rağmen sürücülerin yayalara yol vermeme oranı oldukça yüksektir.

Bu projenin amacı:
* Trafik ışığı bulunmayan kontrolsüz yaya geçitlerinde yayaya yol vermeyen araçları **YOLOv8** derin öğrenme modeli ve nesne takip algoritmalarıyla **gerçek zamanlı (real-time)** olarak tespit etmek,
* İhlal yapan araçların görsel kanıtlarını zaman damgalı olarak otomatik arşivlemek,
* İlerleyen aşamalarda hızla yaklaşan ve durmayan araçlar karşısında yayayı **sesli/ışıklı ikazlarla uyararak** kazaları oluşmadan önleyen çift yönlü bir akıllı ulaşım sistemi geliştirmektir.

---

## 3. ÖZGÜN DEĞER (Projeyi Diğerlerinden Ayıran Yönler)
1. **Mevcut Sistemlerin Eksikliği:** Mevcut EDS (Elektronik Denetleme Sistemleri) ağırlıklı olarak hız ve kırmızı ışık ihlallerine odaklanmaktadır; yaya geçitlerinde yayaya yol vermeme ihlallerinin denetimi neredeyse tamamen insan gücüne (trafik polislerine) dayanmaktadır.
2. **Uçta Hesaplama (Edge AI) Uyumluluğu:** Model mimarisi, yüksek maliyetli sunucular yerine düşük maliyetli tek kart bilgisayarlarda (Raspberry Pi 5 / NVIDIA Jetson) çalışabilecek hafiflikte optimize edilmiştir.
3. **Önleyici Güvenlik Vizyonu:** Sistem sadece ceza kesici değil, yayanın hayatını kurtarmaya yönelik "Aktif Kaza Önleme" hedefi taşır.

---

## 4. YÖNTEM VE ALGORİTMA MİMARİSİ

Proje 4 ana teknik katmandan oluşmaktadır:

```
[Kamera Akışı (Webcam / IP Kamera / Video)]
                      │
                      ▼
[1. Katman: Nesne Tespiti (YOLOv8)] ───► (Yayalar ve Araçlar Sınıflandırılır)
                      │
                      ▼
[2. Katman: Nesne Takibi (ByteTrack)] ──► (Her araca ve yayaya benzersiz ID atanır)
                      │
                      ▼
[3. Katman: Geometrik Bölge Analizi (ROI)]
     ├── Yaya Geçidi Bölgesi (Yaya varlığı kontrolü)
     └── Durma Çizgisi Bölgesi (Araç kesişim kontrolü)
                      │
                      ▼
[4. Katman: Karar Motoru & Kanıt Kaydı]
     ├── İhlal Durumu: (Yaya Geçitte == True) VE (Araç Çizgiyi Geçti == True)
     ├── Çıktı: Kırmızı İkaz + Zaman Damgalı Fotoğraf Kaydı (`output/ihlaller/`)
     └── Mükerrer Kayıt Engelleme: Araç ID bazlı tekil kayıt
```

---

## 5. KULLANILAN TEKNOLOJİLER
* **Programlama Dili:** Python 3
* **Yapay Zekâ Çatısı:** Ultralytics YOLOv8 (You Only Look Once - v8 nano)
* **Görüntü İşleme:** OpenCV (Open Source Computer Vision Library)
* **Matematiksel Hesaplama:** NumPy (Poligon kesişim ve vektör hesaplamaları)

---

## 6. BEKLENEN ETKİ VE SONUÇLAR
* Yaya geçitlerinde sürücü farkındalığını ve yayaya yol verme oranını artırmak.
* Okul çevreleri, hastane önleri ve ana arterlerde yaya güvenliğini en üst düzeye çıkarmak.
* Yerli ve milli yazılım çözümleriyle akıllı şehir (Smart City) altyapılarına entegre edilebilir bir modül sunmak.
