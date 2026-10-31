# TÜBİTAK 2209-A ÜNİVERSİTE ÖĞRENCİLERİ ARAŞTIRMA PROJELERİ DESTEKLEME PROGRAMI
# PROJE ÖNERİ FORMU

---

## 1. PROJE BİLGİLERİ

* **Proje Başlığı:** Yapay Zekâ ve Bilgisayarlı Görü Tabanlı Akıllı Yaya Geçidi Kural İhlali Tespit ve Otomatik Ceza Tutanağı Düzenleme Sistemi
* **Tematik Alan:** Akıllı Şehirler ve Ulaşım Teknolojileri / Yapay Zekâ ve Veri Bilimi
* **Proje Süresi:** 6 Ay
* **Proje Yürütücüsü:** [Adınız Soyadınız] (Bölümünüz, Üniversiteniz)
* **Akademik Danışman:** [Danışman Hocanızın Unvanı, Adı Soyadı]

---

## 2. PROJE ÖZETİ (ÖZET VE ANAHTAR KELİMELER)

Trafik kazaları dünya genelinde ve Türkiye’de can ve mal kayıplarının en önemli nedenlerinden biridir. Emniyet Genel Müdürlüğü ve TÜİK verilerine göre, ölümlü ve yaralanmalı trafik kazalarının yaklaşık %22'si yayaya çarpma şeklinde gerçekleşmekte, bu kazaların büyük bir kısmı ise 2918 sayılı Karayolları Trafik Kanunu’nun 74. maddesinde düzenlenen "Yayalara Geçiş Hakkı Vermeme" kuralının ihlal edilmesinden kaynaklanmaktadır. Mevcut Elektronik Denetleme Sistemleri (EDS) ağırlıklı olarak hız ve kırmızı ışık ihlallerine odaklanmakta, sinyalizasyonsuz yaya geçitlerinde yayaya yol vermeme denetimi neredeyse tamamen manuel polis denetimine dayanmaktadır.

Bu projenin amacı; kontrolsüz yaya geçitlerinde yayaya yol vermeyen sürücüleri derin öğrenme tabanlı nesne tespiti (YOLOv8) ve nesne takip (ByteTrack) algoritmalarıyla gerçek zamanlı olarak tespit eden, aracın durma/yavaşlama kinetiğini yer değiştirme vektörleriyle ölçen ve ihlal anında otomatik delil fotoğrafı ile resmi ceza tutanağı (Excel formatında) üreten uçtan uca bir akıllı denetim sistemi geliştirmektir. Sistem; masaüstü operatör kontrol paneli (GUI) ve esnek geometrik kalibrasyon yeteneği ile donatılmış olup, düşük maliyetli tek kart bilgisayarlar (Edge AI) üzerinde çalışabilecek şekilde optimize edilmiştir.

**Anahtar Kelimeler:** Bilgisayarlı Görü, YOLOv8, Nesne Takibi, Akıllı Yaya Geçidi, Trafik Güvenliği, EDS, KTK Madde 74.

---

## 3. PROJENİN ÖNEMİ VE ÖZGÜN DEĞERİ

### 3.1. Literatür Özeti ve Mevcut Durum
Geleneksel trafik denetim sistemleri genellikle yol zeminine gömülü manyetik indüksiyon döngüleri (loop sensors) veya radar tabanlı sensörlerle çalışmaktadır. Ancak bu fiziksel altyapılar maliyetli olup yaya-araç etkileşimini anlama yeteneğine sahip değildir. Son yıllarda derin öğrenme (CNN) ve özellikle tek aşamalı nesne tespit modellerinin (YOLO ailesi) gelişmesiyle kamera tabanlı akıllı ulaşım sistemleri popülerlik kazanmıştır.

Literatürdeki mevcut akademik çalışmalar incelendiğinde iki temel eksiklik göze çarpmaktadır:
1. **Durma/Yavaşlama Kinetiğinin İhmali:** Birçok çalışma aracı sadece bir poligon alanına girdiği anda ihlal saymakta; aracın yayaya yol vermek üzere yavaşlayıp durmasını denetleyememektedir (yanlış alarm oranı yüksek).
2. **Kimlik Değişimi (ID Switching) ve Mükerrer Ceza:** Araçların anlık takibinin koptuğu durumlarda aynı araca tekrar tekrar ceza kesilmesi sorunu çözülememiştir.

### 3.2. Projenin Özgün Değeri
* **Bağıl Hız ve Durma Vektör Analizi:** Sistemimiz, araç genişliğini referans alarak kameranın optik derinliğinden bağımsız normalize edilmiş bir hız hesaplar ($v_{norm} = \frac{\Delta d}{\Delta t \cdot W_{arac}}$). Böylece araç geçide yaklaşırken durmuşsa ihlal yazılmaz, yalnızca hareketine devam ederse ceza uygulanır.
* **Mekânsal-Zamansal Hafıza (Spatio-Temporal De-duplication):** Takip motorunda yaşanabilecek anlık ID kayıplarında, aracın koordinat geçmişi incelenerek aynı araca mükerrer ceza kesilmesi kesin olarak önlenir.
* **İnteraktif Çoklu-Poligon Kalibrasyonu:** Sistem sabit bir kamera açısına bağımlı değildir; operatörün fareyle tıklayarak yaya geçidini ve durma çizgisini her sokağa göre 5 saniyede kalibre etmesini sağlar.
* **Uç Bilişim (Edge AI) Uyumluluğu:** Model nano ölçekli ağırlıklarla ($yolov8n.pt$) çalıştığı için pahalı GPU sunucularına ihtiyaç duymadan, enerji tüketimi düşük uç cihazlarda (NVIDIA Jetson, Raspberry Pi 5) 25-30 FPS bandında çalışabilmektedir.

---

## 4. AMAÇ VE HEDEFLER

### Ana Amaç:
Sinyalizasyonsuz yaya geçitlerinde yayaya yol vermeyen motorlu taşıtları yapay zekâ ile anlık olarak denetleyen, sürücü davranışlarını kayıt altına alan ve trafik güvenliğini artıran milli ve düşük maliyetli bir akıllı sistem geliştirmek.

### Ölçülebilir Hedefler:
1. Yaya ve araç tespitinde en az **%85 duyarlılık (Recall)** ve **%80 kesinlik (Precision)** elde etmek.
2. Duran ve geçen araç ayrımını hız vektörü filtresiyle yaparak yanlış alarm oranını **%10'un altına indirmek**.
3. Gerçek zamanlı kamera akışında en az **20 FPS** çalışma hızına ulaşmak.
4. Kural ihlali yapan araçları zaman damgalı ekran görüntüsü ve resmi KTK Madde 74 tutanağıyla Excel/CSV ortamına eksiksiz aktarmak.

---

## 5. YÖNTEM

Proje 5 ana metodolojik aşamadan oluşmaktadır:

```
[Kamera Akışı / Video] 
           │
           ▼
[1. Aşama: Nesne Tespiti (YOLOv8)] ──► Yayalar (cls=0) ve Taşıtlar (cls=2,3,5,7)
           │
           ▼
[2. Aşama: Kararlı Nesne Takibi (ByteTrack)] ──► Benzersiz Taşıt ve Yaya ID Ataması
           │
           ▼
[3. Aşama: Geometrik Bölge Kesişimi (OpenCV pointPolygonTest)]
     ├── Bölge A: Yaya Geçidi Poligonu (Yeşil Alan)
     └── Bölge B: Araç Durma Çizgisi Poligonu (Mavi Alan)
           │
           ▼
[4. Aşama: Bağıl Hız ve İhlal Karar Motoru]
     ├── Şart 1: Yaya Geçidi Bölgesi'nde en az bir yaya bulunması
     ├── Şart 2: Aracın Durma Çizgisi veya Geçit poligonuna temas etmesi
     └── Şart 3: Aracın hızının durma eşiğinden yüksek olması (V_norm > 0.3)
           │
           ▼
[5. Aşama: Çıktı ve Raporlama]
     ├── Delil Fotoğrafının Kaydedilmesi (output/ihlaller/)
     └── Resmi Excel Ceza Tutanağına İşlenmesi (xlsxwriter)
```

### Kullanılan Araç ve Teknolojiler:
* **Programlama Dili:** Python 3.10+
* **Derin Öğrenme:** PyTorch, Ultralytics YOLOv8
* **Görüntü İşleme:** OpenCV (Open Source Computer Vision)
* **Kullanıcı Arayüzü:** Tkinter (Modern Koyu Tema, Çift Tıkla Başlatıcı)
* **Raporlama:** XlsxWriter (Kurumsal EGM/EDS formatı)

---

## 6. İŞ-ZAMAN ÇİZELGESİ (İŞ PAKETLERİ)

Proje süresi toplam **6 Ay** olarak planlanmıştır:

| İş Paketi (İP) | İş Paketi Adı | Süre (Ay) | 1. Ay | 2. Ay | 3. Ay | 4. Ay | 5. Ay | 6. Ay |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **İP 1** | Literatür Taraması ve Veri Seti Hazırlığı (Saha ve Simülasyon Videoları) | 1 Ay | ████ | | | | | |
| **İP 2** | Yapay Zekâ Modelinin Entegrasyonu ve Takip Algoritması Optimizasyonu | 2 Ay | | ████ | ████ | | | |
| **İP 3** | Geometrik Bölge Analizi ve Bağıl Hız Algoritmasının Geliştirilmesi | 2 Ay | | | ████ | ████ | | |
| **İP 4** | Masaüstü Arayüzü (GUI), Kalibrasyon Modülü ve Otomatik Tutanak Sistemi | 1 Ay | | | | | ████ | |
| **İP 5** | Saha / Video Testleri, Metrik Ölçümleri (F1, FPS) ve Sonuç Raporu | 1 Ay | | | | | | ████ |

---

## 7. RİSK YÖNETİMİ VE B PLANI

| Olası Risk | Etki Düzeyi | B Planı (Alternatif Çözüm) |
| :--- | :---: | :--- |
| **Hava Koşulları ve Gece Görüşü:** Yağmurlu/karanlık sahnelerde yaya tespitinin zorlaşması. | Orta | Görüntü ön işleme katmanına Histogram Eşitleme (CLAHE) ve kontrast artırıcı filtreler eklenecektir. |
| **Takip ID Kopması (ID Switching):** Kalabalık trafikte araç numaralarının değişmesi. | Yüksek | Geliştirdiğimiz mekânsal-zamansal hafıza filtresi (son 4 sn içindeki koordinat yakınlığı) ile mükerrer ceza engellenmiştir. |
| **Kamera Açısı Değişiklikleri:** Farklı yollarda geçit açısının değişmesi. | Düşük | İnteraktif fare kalibrasyon aracıyla operatör 4 köşe seçerek sistemi her açıya adapte edebilir. |

---

## 8. YAYGIN ETKİ VE ÇIKTILAR

* **Toplumsal Fayda:** Trafikte yayaya yol verme kültürünün artırılması, okul ve hastane önlerinde ölümlü/yaralanmalı yaya kazalarının minimize edilmesi.
* **Akademik Çıktı:** Proje sonuçlarının ulusal/uluslararası bir öğrenci kongresinde veya IEEE/SIU konferansında bildiri olarak sunulması.
* **Uygulanabilirlik:** Emniyet Genel Müdürlüğü (EGM) ve Belediyelerin Akıllı Trafik Yönetim Merkezlerine entegre edilebilir yerli yazılım prototipi.

---

## 9. BÜTÇE TALEBİ VE GEREKÇESİ (Örnek Talep)

*(TÜBİTAK 2204/2209-A kapsamında öğrenciye sağlanan hibe desteği için talep edilebilecek örnek kalemler)*

1. **Gömülü Sistem Kartı (NVIDIA Jetson Orin Nano / Raspberry Pi 5):** Sistemin bağımsız bir trafik direğinde uçta çalışmasını test etmek için.
2. **Geniş Açılı USB/IP Kamera:** Gerçek cadde testleri için.
3. **Tripod ve Montaj Aparatları:** Saha testlerinde kamerayı güvenli sabitlemek için.
4. **Taşınabilir SSD / Depolama:** Yüksek çözünürlüklü test videolarının arşivlenmesi için.
