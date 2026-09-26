# Proje planı ve kabul ölçütleri

## İş problemi

Aynı müşteri farklı kanallarda birden çok kayıtla görünebilir. CRM ekibi müşteri sayısını,
alışveriş geçmişini ve kampanya önceliklerini güvenilir biçimde görmek ister.
Projenin çıktısı yalnızca model metriği değildir: tutarlı veri, açıklanabilir müşteri profili,
rapor ve ölçülebilir kampanya deneyi birlikte teslim edilir.

## Aşamalar

| Aşama | Durum | Somut çıktı | Kabul ölçütü |
|---|---|---|---|
| 1. Veri sözleşmesi ve sentetik kaynak | v0.1 hazır | Müşteri, ürün, işlem olayları | Şema, zaman ve para birimi açık |
| 2. Kimlik ve veri kalitesi | v0.1 hazır | Tekil müşteri, karantina, denetim tablosu | Tam satır mutabakatı; çakışma sessizce birleştirilmez |
| 3. Müşteri analitiği | v0.1 hazır | RFM, kanal, kategori/marka/ürün tercihleri, kohort | Hesaplar işlem seviyesine geri izlenebilir |
| 4. Risk ve değer modeli | v0.1 hazır | Zaman ayrılmış test, baseline, model kartı | Etiket pencereleri tam; gelecek veri özelliğe sızmaz |
| 5. Raporlama | HTML hazır; SQL Server CI doğrulandı | Filtreli rapor, SQL şeması, DAX | Power BI Desktop eşleştirmesi Windows ortamında bekliyor |
| 6. Gerçek veri adaptasyonu | v0.2 hazır | UCI adaptörü ve zaman temelli geri test | Kaynak/currency/iade/müşteri anlamları korunur |
| 7. CRM deneyi | Aday/grup ataması hazır | Deney tasarımı ve sonuç analizi | Etki, maliyet ve belirsizlik birlikte raporlanır |
| 8. Operasyon | Planlandı | Günlük yükleme, izleme, yeniden eğitim | Veri tazeliği, kimlik sürekliliği, alarm ve geri alma |

## Çalışma önerisi — yaklaşık 4–6 hafta, hızına göre

| Hafta | Çalışma | Görüşmede anlatılacak yetkinlik |
|---|---|---|
| 1 | Veri sözlüğü, tekilleştirme, iadeler, SQL sorguları | Veri doğruluğu ve müşteri 360 |
| 2 | RFM, kategori/marka analizi, Power BI sayfaları | CRM ve iş birimlerine içgörü |
| 3 | Risk modeli, zaman pencereleri, metrikler | Sızıntısız model değerlendirmesi |
| 4 | 90 günlük değer, LTV varsayımları, kampanya deneyi | İş değerini modellemeye bağlama |
| 5 | Gerçek veri adaptörü, yeni geri testler | Sentetik ortamdan gerçek veriye geçiş |
| 6 | İzleme, otomasyon, GitHub sunumu | Tekrarlanabilir ve yönetilebilir analitik |

Bu süreler öğrenme planı önerisidir; teslim edilen sürümler için geliştirme süresi beyanı değildir.

## Gerçek veriye geçişte kararlar

- UCI Online Retail II ile satın alma, RFM, kohort ve gelecek harcama tahmini doğrulanabilir.
  Bu veri anne-bebek perakendesi değildir; marka, ürün kategorisi, pazarlama izni ve ürün maliyeti hazır kabul edilemez.
- Ürün maliyeti yoksa brüt kâr ve kâr bazlı LTV ölçülmez; sonraki 90 gün net ciro hedefi kullanılır.
- İşlem para birimi GBP ise TL etiketi konmaz. Kur dönüştürmesi yapılırsa kaynak ve tarih açıklanır.
- Müşteri kimliği eksik satırlar müşteri tahmininde ayrı ele alınır; anonim işlemler toplam satış raporundan gerekçesiz çıkarılmaz.
- Sipariş iptali/iade kodları ve negatif miktarlar kaynak dokümanına göre yorumlanır.
- Aile üyelerinin ortak iletişim bilgisi olabilir. Tek telefon veya tek e-posta yeterli eşleştirme kanıtı değildir.
- Kimlik değişimleri ve birleştirme geçmişi varsa geçmiş tarihte bilinen kimlik grafiği korunmalıdır.
- Küçük çocukların yaşı, sağlık durumu veya benzeri bilgiler bu proje için gerekli değildir.

## CRM deneyinin sonucu nasıl hesaplanır?

Hedef kitle, müdahale, takip penceresi ve ana metrik deney başlamadan kaydedilir.
Bu sürümde 150 adayın %20'si kontrol grubu olarak ayrılır; bu oran ve sayı bir güç analizi sonucu değildir.
Gerçek uygulamada minimum anlamlı etki, baz dönüşüm, maliyet ve test gücüne göre örneklem hesaplanır.

Birincil metrik: kişi başına gerçekleşen 90 günlük brüt kâr − kampanya/iletişim maliyeti.
Atanan bütün kişiler, alışveriş yapmasalar bile kendi grubunda tutulur (intention-to-treat).
Deney ortalaması − kontrol ortalaması ek etki tahminidir; güven aralığı ayrıca hesaplanır.
İndirim zaten net ciroda varsa ikinci kez maliyet olarak düşülmez.

Risk yüksekliği kampanyaya olumlu yanıt verme olasılığıyla aynı şey değildir.
Uplift modeli ancak geçmiş randomize müdahale verisi veya uygun nedensel tasarım varsa değerlendirilebilir.

## BT ve CRM ile sorulacak sorular

1. Asıl müşteri anahtarı nedir; hangi kaynaktaki kimlik doğrulaması güvenilir?
2. İşlem zamanı sipariş, fatura, teslimat veya iade tarihi mi?
3. Net gelir ve maliyet tanımları vergileri/iadeleri nasıl ele alıyor?
4. 90 gün hareketsizlik her kategori için anlamlı mı?
5. Kampanya bütçesi, iletişim sıklığı ve güncel izin kaynağı nedir?
6. İşletme kazanım için hangi metriği kullanacak: dönüşüm, ek gelir veya ek katkı kârı?

## Operasyonel geliştirmeler

Önce günlük veri yüklemesini, skor tarihini ve model sürümünü kaydet.
Geciken iade ve geriye dönük düzeltmeler için yeniden hesaplama politikası belirle.
Kalıcı müşteri anahtar kayıt defteri, izin geçmişi ve SCD2 gerektiğinde eklenmeli.
Özellik/model kayması, etiket oranı, kalibrasyon ve kohort performansı izlenmeli.
Yeni model ancak önceki sürüm ve basit modelle ileri tarihli karşılaştırmadan sonra seçilmeli.
Bu üretim altyapısı henüz kurulmuş değildir.
