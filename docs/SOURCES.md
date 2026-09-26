# Kaynaklar ve veri stratejisi

Kaynaklar 26 Eylül 2026 tarihinde kontrol edildi.

## 1. Gerçek veri: UCI Online Retail II

[UCI Online Retail II](https://archive.ics.uci.edu/dataset/502/online%2Bretail%2Bii)
iki yıllık Birleşik Krallık çevrimiçi perakende işlemlerini içerir.
Kaynakta 1.067.371 kayıt, eksik değerler ve GBP birim fiyat bilgisi tanımlanır.
CC BY 4.0 lisanslıdır; atıf korunmalıdır. Anne-bebek mağazası verisi değildir.

Atıf: Chen, D. (2012). *Online Retail II [Dataset]*. UCI Machine Learning Repository.
DOI: https://doi.org/10.24432/C5CG6D.

`retailscope/uci.py` iki çalışma sayfasını birleştirir; tam tekrarları ayırır,
müşteri kimliği bulunmayan satırları müşteri modelinden karantinaya alır ve
zaman temelli RFM/risk/gelir analizini çalıştırır. Kaynakta bulunmayan maliyet,
kategori, marka, iletişim ve izin alanları uydurulmaz. Ham çalışma kitabı ve
üretilen çıktılar lisans/boyut nedeniyle Git'e eklenmez; indirme betiği resmî
kaynağı kullanır ve SHA-256 doğrulaması yapar.

## 2. Sentetik referans veri

`retailscope/synthetic.py` ile üretilen veri kimlik çözümleme, izin kontrollü
kampanya tasarımı ve brüt kâr senaryolarını göstermek için korunur. Gerçek kişi,
ebebek ürünü, şirket satışı veya kampanya sonucu içermez. E-posta adresleri
`example.invalid`, telefonlar `SYNTH` belirteci kullanır ve veri sabit tohumla
yeniden üretilebilir.

## 3. Tasarım kaynakları

- [Microsoft — Power BI yıldız şema rehberi](https://learn.microsoft.com/en-us/power-bi/guidance/star-schema):
  tutarlı satır birimi, boyut ve olgu tablolarının ayrımı, bire-çok ilişkiler.
- [Microsoft — Power Query SQL Server connector](https://learn.microsoft.com/en-us/power-query/connectors/sql-server):
  SQL Server'dan Power Query bağlantısı.
- [scikit-learn — Common pitfalls](https://scikit-learn.org/stable/common_pitfalls.html):
  veri sızıntısını önleme ve yalnızca eğitim verisinde dönüşüm öğrenme.

Bu kaynaklar proje modelinin başarı garantisi değildir. Kullanılan model, eşik ve deney kapasitesi
bu portföy çalışmasının açıkça belgelenen tasarım seçimleridir.
