# Doğrulama kaydı — 18 Eylül 2026

## Çalıştırılanlar

- Python 3.12.14; requirements.txt içindeki sürümlerle `python -m retailscope all` başarıyla tamamlandı.
- 14 unittest geçti: gelecekteki veriden özellik bağımsızlığı, tam takip şartı,
  kesit sınırı, negatif iade değeri, kimlik çakışması, izin, kampanya ayrımı ve muhasebe mutabakatı.
- Python modülleri, yükleme betiği ve testler sözdizimi kontrolünden geçti.
- HTML içindeki veri JSON'u ayrıştırıldı; JavaScript Node sözdizimi kontrolünden geçti.
- CSV / HTML toplamları, benzersiz anahtarlar, müşteri dış anahtarları ve olasılık aralıkları tutarlı.

## Veri sonucu

| Ölçüm | Sonuç |
|---|---:|
| Ham müşteri kaydı | 2.266 |
| Tekil müşteri | 1.800 |
| Birleştirilen ek kayıt | 466 |
| Ham olay satırı | 81.526 |
| Tam tekrar | 35 |
| Karantina | 2 |
| Kabul edilen olay | 81.489 |
| Skorlanan müşteri | 1.368 |
| Deney / kontrol grubu | 120 / 30 |

## Model sonucu — yalnızca kurgusal veri

Risk modeli doğrulama döneminde Logistic Regression olarak seçildi.
Değer modeli HistGradientBoosting olarak seçildi.

| Test ölçümü | Sonuç |
|---|---:|
| Test müşterisi | 1.499 |
| Alışveriş yapmama oranı | %19,95 |
| Average Precision | 0,7300 |
| ROC-AUC | 0,8727 |
| Brier | 0,0937 |
| İlk %20 precision | %65,00 |
| İlk %20 lift | 3,259 |
| Recency baseline lift | 3,192 |
| Değer MAE | 1.706,12 TL |
| Ortalama baseline MAE | 2.060,41 TL |
| Değer WAPE | %73,93 |
| Değer R² | 0,1432 |
| Toplam değer tahmini yanlılığı | yaklaşık +%29,3 |

Risk modelinin basit recency sıralamasına göre artışı sınırlıdır.
Değer modelinin hata oranı ve toplam yanlılığı yüksektir; gerçek bütçe/teklif kararı için uygunluğu gösterilmemiştir.
Bu metrikler modelin kusurlarını görünür kılan başlangıç sonuçlarıdır; gerçek müşterilere taşınamaz.

## Bu ortamda doğrulanmayanlar

- SQL Server bağlantısı, ODBC sürücüsü, T-SQL yürütmesi ve gerçek transaction yüklemesi.
- Power BI Desktop içe aktarma, ilişkiler, DAX yürütmesi ve PBIX görsel doğrulaması.
- Windows PowerShell betiğinin Windows üzerinde çalışması; Python hattı Linux ortamında çalıştırıldı.
- Tarayıcıda görsel ve etkileşim testi: tarayıcı yürütülebilir dosyası ortamda bulunmadığı için çalıştırılamadı.
  HTML veri/sözdizimi kontrolleri görsel test yerine geçmez.
- GitHub Actions uzak çalıştırması; yalnızca workflow dosyası hazırlanmıştır.
- Gerçek veri adaptörü, gerçek kampanya, nedensel ek etki, iş sonucu ve üretim otomasyonu.

Dosya içindeki sonuçlar tohum 42 ve varsayılan config içindir. Konfigürasyon değiştirilirse
güncel kaynak `outputs/reports/metrics.json`, `data_quality.json` ve `run_manifest.json` olacaktır.
