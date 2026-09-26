# Model kartı — v0.1

## Amaç ve hedef evren

Son 180 günde en az bir gerçekleşmiş satışı bulunan müşterilerin gelecek 90 günlük davranışını tahmin etmek.
Kimliği olmayan ziyaretçiler ve tamamen yeni müşteriler bu evrene dahil değildir.
Pazar, kurum veya gerçek müşteri davranışı hakkında doğrulanmış başarı iddiası yoktur.

Hedefler: satış yapmama olasılığı (`inactive_next90`) ve toplam brüt kâr (`margin_next90`).
Tam iade edilen satış da gerçekleşmiş satın alma sayılır. Bu etiket seçimi iş birimiyle gerçek veride yeniden kararlaştırılmalıdır.
“Alışveriş yapmama” sözleşmeli abonelik iptali veya kesin marka terk etme değildir.

## Zaman tasarımı

| Kullanım | Kesit başlangıcı | Hedefin hariç bitişi |
|---|---|---|
| Eğitim | 2025-01-01 | 2025-04-01 |
| Eğitim | 2025-04-01 | 2025-06-30 |
| Eğitim | 2025-07-01 | 2025-09-29 |
| Doğrulama | 2025-10-01 | 2025-12-30 |
| Test | 2026-01-01 | 2026-04-01 |
| Güncel skorlama | 2026-04-01 | Etiketi yok; gelecek tahmini |

Özellikler `[kesit − 365 gün, kesit)` içindeki olaylardan türetilir.
Tenure için kesit öncesindeki bütün gözlenen satışlar kullanılır.
Etiketler `[kesit, kesit + 90 gün)` içindedir; eksik takip varsa üretim reddedilir.
Scaler yalnızca modelin eğitim verisinde fit edilir. Müşteri kimliği, etiket, segment,
güncel izin ve sentetik üreticinin gizli yaşam döngüsü parametreleri modele girmez.

Önce eğitim verisiyle adaylar öğrenilir; seçim doğrulama AP / MAE sonuçlarına göre yapılır.
Seçilen modeller eğitim + doğrulama ile yeniden eğitilir ve sonraki test döneminde değerlendirilir.
Son skorlama için test dönemi sonuçları artık tamamlanmış olduğundan bütün etiketli kesitler kullanılır.
Raporlanan test sonuçları son modelin eğitim-içi performansı değil, test öncesi fit edilmiş modelin performansıdır.

Aynı müşteri birden fazla kesitte bulunabilir. Bu mevcut müşteriyi ileriki tarihte skorlamayı ölçer.
Yeni müşteriye genellenebilirlik için ayrı müşteri gruplarıyla değerlendirme gerekir.
Sentetik kimlikler sabittir. Gerçek kimlik birleştirme geçmişinde geçmişe dönük bilgi sızıntısı ayrıca önlenmelidir.

## Metrikler ve yorum

- Average Precision: riskli müşterileri sıralama başarısı; rastgele/önsel referans etiket prevalansıdır.
- ROC-AUC: genel ayırma; tek başına iş değeri değildir.
- Precision@20% ve lift@20%: en riskli %20 içindeki gerçek hareketsizlik / kitlenin hareketsizliği.
- Brier: olasılık tahmin hatası; düşük daha iyi. Bu sürüm ayrı olasılık kalibrasyonu uygulamaz.
- MAE: müşteri başına brüt kâr tahmininin TL hata büyüklüğü.
- WAPE: mutlak hataların toplamı / mutlak gerçek değerlerin toplamı. Bireysel yüzde hatası değildir.
- R²: ortalama tahminine göre varyans açıklama; negatif çıkabilir ve aynen raporlanır.

Top-%20 ölçümü model değerlendirmesi içindir. Kampanya uygunluğu ayrıca izin,
kimlik tutarlılığı, 30+ gün recency, %50+ risk ve pozitif tahmini değer koşullarını kullanır.
Kampanya kapasitesi gerçek bütçeden öğrenilmemiştir; v0.1'de 150 adaydır.
Eşit risklerde sıralama sabit girdi sırasıyla çözülür; özellikle önsel baseline için top-k değeri buna duyarlıdır.

## Açıklanabilirlik

Test üzerinde permutation importance, AP düşüşü olarak üç tekrar ile raporlanır.
Bu yalnızca tanısal açıklamadır; test sonucuyla özellik seçilip model yeniden ayarlanmaz.
Korelasyonlu özellikler önem paylarını bölüşebilir; nedensellik sonucu çıkarılmaz.
Kampanya listesindeki gerekçe alanı iş kuralı açıklamasıdır, modelin kişi bazlı SHAP açıklaması değildir.

## LTV senaryosu

`v` = önümüzdeki 90 günlük tahmini brüt kâr; `q` = çeyreklik devamlılık varsayımı;
`d` = çeyreklik iskonto oranı; `K` = çeyrek sayısı.

`Değer = Σ[k=0..K−1] v × q^k / (1+d)^(k+1) − edinme_maliyeti`

Varsayılan q=.70, d=.025, K=12, edinme maliyeti=0.
v zaten önümüzdeki dönem davranışına ilişkin koşulsuz tahmindir;
q sonraki çeyreklerde bu tutarın varsayımsal azalışıdır. Parametreler tahmin edilmiş değildir.
Bu sınırlı ufuklu senaryo tam yaşam boyu değer değildir.
Gerçek uzun dönem model için BG/NBD gibi işlem modelleri, survival veya uygun alternatifler
verinin satın alma süreci ve varsayımları değerlendirilerek ayrı geri testten geçirilmelidir.

## Sınırlamalar ve izleme

Veri üretimi alışveriş sıklığı ve doğal çıkış üzerinden yapıldığından sentetik başarı kolaylaşabilir.
Kampanya yanıtı üretilmediği için uplift/ROI yoktur. Bebek yaşı/sağlık gibi veriler bulunmaz.
Enflasyon, rekabet, stok yokluğu, değişen maliyetler ve sezon etkileri gerçekçi modellenmemiştir.
İlk değer modelinin hata büyüklüğü ve toplam tahmin yanlılığı BUSINESS_REPORT.md içinde görünürdür;
satış bütçesi veya bireysel teklif miktarı belirlemek için doğrulanmış kabul edilmemelidir.
Gerçek veride daha fazla tarihli geri test, kategori bazlı hata, kalibrasyon, etiket kayması ve veri tazeliği izlenmelidir.
