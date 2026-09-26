# Kaynaklar ve veri stratejisi

Kaynaklar 18 Eylül 2026 tarihinde kontrol edildi. Bağlantılar teknik tasarımı ve sonraki veri aşamasını destekler.

## 1. Mevcut veri: tamamen sentetik

İlk sürümde yalnızca `retailscope/synthetic.py` ile üretilen veri kullanıldı.
Gerçek kişiler, ebebek ürün veritabanı, satış verileri veya kampanya sonuçları kullanılmadı.
E-posta adresleri example.invalid alanında, telefonlar SYNTH belirteci şeklindedir.
Veri seti sabit tohumla yeniden üretilebilir. UCI verisi indirilmemiş ve projeye dahil edilmemiştir.

## 2. Gerçek veriyle ikinci aşama

[UCI Online Retail II](https://archive.ics.uci.edu/dataset/502/online+retail+ii)
iki yıllık Birleşik Krallık çevrimiçi perakende işlemlerini içerir.
Kaynakta 1.067.371 kayıt, eksik değerler ve GBP birim fiyat bilgisi tanımlanır.
CC BY 4.0 lisanslıdır; atıf korunmalıdır. Anne-bebek mağazası verisi değildir.

Atıf: Chen, D. (2012). *Online Retail II [Dataset]*. UCI Machine Learning Repository.
DOI: https://doi.org/10.24432/C5CG6D.

İlk kullanım amacı: sipariş/iade temizliği, RFM, kohort ve sonraki 90 gün net harcama geri testi.
Maliyet ve izin gibi kaynakta bulunmayan alanlar gerçek gözlem gibi doldurulmayacak.
Dosyanın adaptörü ve yeni dönem konfigürasyonu sonraki geliştirme aşamasıdır.

## 3. Tasarım kaynakları

- [Microsoft — Power BI yıldız şema rehberi](https://learn.microsoft.com/en-us/power-bi/guidance/star-schema):
  tutarlı satır birimi, boyut ve olgu tablolarının ayrımı, bire-çok ilişkiler.
- [Microsoft — Power Query SQL Server connector](https://learn.microsoft.com/en-us/power-query/connectors/sql-server):
  SQL Server'dan Power Query bağlantısı.
- [scikit-learn — Common pitfalls](https://scikit-learn.org/stable/common_pitfalls.html):
  veri sızıntısını önleme ve yalnızca eğitim verisinde dönüşüm öğrenme.

Bu kaynaklar proje modelinin başarı garantisi değildir. Kullanılan model, eşik ve deney kapasitesi
bu portföy çalışmasının açıkça belgelenen tasarım seçimleridir.
