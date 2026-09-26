# Power BI kurulumu

Bu klasörde hazır PBIX yoktur. CSV tabloları, veri modeli, DAX ölçüleri ve sayfa tasarımı vardır.
Power BI Desktop bu ortamda çalıştırılmadı; modelin son görsel doğrulaması Windows üzerinde yapılmalıdır.

## 1. Veriyi al

Başlangıç yolu: Power BI Desktop → Veri al → Metin/CSV → `outputs/marts/`.
`dim_customer`, `dim_product`, `dim_date`, `fact_sales`, `customer_scores` tablolarını yükle.
İleride SQL Server yüklemesinden sonra **SQL Server → Import** ile aynı tabloları seçebilirsin.
Otomatik ilişki oluşturma önerilerini kabul etmeden aşağıdaki ilişki listesini uygula.

Power Query'de dosyaları UTF-8 olarak al. Ondalık ayırıcı CSV içinde noktadır;
sayısal sütunları **Yerel ayar kullanarak → İngilizce (ABD)** ile dönüştür.
Tarihleri ISO yyyy-MM-dd olarak Date yap. `rfm_score`, müşteri/ürün/sipariş kimlikleri metin olarak kalmalı.
Pazarlama izni ve kimlik inceleme alanları True/False olmalı. Risk 0–1 arası ondalıktır.

## 2. İlişkiler

| Bir taraf | Çok taraf | Yön |
|---|---|---|
| dim_customer.customer_id | fact_sales.customer_id | Tek yön: boyut → olgu |
| dim_product.product_id | fact_sales.product_id | Tek yön: boyut → olgu |
| dim_date.date | fact_sales.event_date | Tek yön: boyut → olgu |
| dim_customer.customer_id | customer_scores.customer_id | Tek yön: boyut → skor |

`dim_date` tablosunu `date` alanıyla tarih tablosu olarak işaretle.
`fact_sales` tek satır = bir satış, iade veya iptal olayıdır. Sipariş sayısını COUNTROWS ile hesaplama.
`customer_scores` tek satır = müşteri + skor tarihidir; bütün tarihleri toplayarak LTV üretme.
Skor tarihi için ayrı, tek seçimli slicer kullan. Skor tarihi alışveriş tarihi değildir;
`dim_date` ile skor tablosuna aktif ilişki ekleme.

Bir müşterinin birden fazla skor tarihi olabileceğinden `customer_scores` müşteri boyutunun yerine geçmez.
Segment, risk ve değer görsellerini `customer_scores` tablosundan üret.
Segment dilimleyici satış tablosunu tek yönlü ilişkide filtrelemez; bunun için ayrıca
müşteri kimlikleri üzerinden kontrollü TREATAS ölçüsü gerekir. İlk sürümde iki sayfanın filtrelerini ayrı tut.
Gelecekte segmentleri geçmiş satışlara taşımak istiyorsan analiz sorusunu
“satış anındaki segment” veya “bugünkü segmente göre geçmiş satış” diye açıkça belirle.

## 3. Ölçüler ve sayfalar

`measures.dax` içindeki her tanımı ayrı ölçü olarak ekle. Risk/oranları yüzde,
parasal değerleri TRY olarak biçimlendir; oranları ham sütun toplamıyla gösterme.

| Sayfa | Görseller | Filtreler |
|---|---|---|
| Yönetici görünümü | Net ciro, brüt kâr, alışveriş yapan müşteri, aylık trend | İşlem tarihi, kanal, kategori, marka |
| Müşteri 360 | RFM dağılımı, risk dağılımı, müşteri detay tablosu | Tek skor tarihi, segment, şehir |
| Müşteri değeri | 90 günlük değer, 3 yıllık LTV senaryosu, risk/değer dağılımı | Tek skor tarihi |
| CRM deneyi | Ayrı CSV'den aday listesi, deney/kontrol sayısı | Grup, segment |
| Veri kalitesi | Karantina tablosu ve data_quality.json mutabakatı | Red nedeni |

`cohort_retention.csv` istersen ayrı analiz tablosu olarak yüklenebilir.
Matris: satır `cohort`, sütun `month_index`, değer `MAX(retention_rate)`;
bir hücre bir kohort/aydır. Ara toplamları kapat. Gelecek hücreleri sıfıra doldurma.

`Net Ortalama Sepet`: seçili olay döneminin iadeler sonrası cirosu / o dönemin satış siparişi.
İade önceki bir ayın satışına ait olabilir; bu ölçü sipariş kohortu net sepeti değildir.
`Iade Tutar Orani` da olay dönemi oranıdır, satışlara geriye dönük bağlanan nihai iade oranı değildir.

## 4. Yenileme

Python hattını tekrar çalıştır → Power BI Desktop Yenile.
Yerel SQL Server'ın Power BI Service üzerinden zamanlanmış yenilenmesi için
kuruma uygun veri ağ geçidi ve kimlik doğrulaması ayrıca yapılandırılmalıdır.
İlk sürümde Service bağlantısı veya zamanlanmış bulut yenilemesi kurulmamıştır.

Temel kaynaklar: [Microsoft yıldız şema rehberi](https://learn.microsoft.com/en-us/power-bi/guidance/star-schema),
[SQL Server bağlantısı](https://learn.microsoft.com/en-us/power-query/connectors/sql-server).
