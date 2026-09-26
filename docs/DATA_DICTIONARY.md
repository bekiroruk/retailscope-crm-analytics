# Veri sözlüğü

## Ham kaynak

| Dosya | Satır birimi | Anahtar | Alanların anlamı |
|---|---|---|---|
| customers.csv | Bir kaynak sistemindeki müşteri kaydı | record_id | loyalty_id ve doğrulama bayrakları; sentetik iletişim; şehir; güncel izin |
| products.csv | Ürün | product_id | Kategori, kurgusal marka, liste fiyatı ve birim maliyet |
| events.csv | Tek ürün için satış/iade/iptal olayı | event_id | order_id, zaman, kaynak müşteri, ürün, tür, miktar, fiyat, indirim, maliyet, kanal, iade kökeni |
| metadata.json | Veri kümesi tanımı | — | Kaynak, tohum, para birimi ve gözlemin hariç bitiş tarihi |

Zamanlar sentetik yerel saat olup tek zaman diliminde değerlendirilir; saat dilimi dönüşümü yoktur.
Fiyat ve maliyetler TRY cinsindedir; vergi ayrı modellenmez. Gerçek veri bağlantısında zaman dilimi ve vergi sözleşmesi gerekir.
Miktar ham kayıtta pozitiftir; parasal işaret olay türü ile uygulanır.
İade, önceki geçerli satışın aynı ürün, müşteri kaydı, fiyat ve indirim koşullarına referans vermelidir.
Bir satışa bağlı kümülatif iade miktarı satış miktarını geçemez.

## Analitik tablolar

| Tablo | Satır birimi | Kullanımı |
|---|---|---|
| dim_customer | Tekil müşteri | Şehir, güncel izin, kimlik inceleme durumu, birleşen kayıt sayısı |
| identity_audit | Kaynak müşteri kaydı | Tekil kimlik ve eşleştirme kuralı; ham iletişim rapora taşınmaz |
| dim_product | Ürün | Kategori/marka/ürün kırılımı |
| dim_date | Takvim günü | Satış tarihleri; skor tarihlerinden ayrı |
| fact_sales | İşlem olayı | İadeler negatif, iptaller sıfır; bir sipariş çok satır içerebilir |
| customer_scores | Müşteri + skor tarihi | RFM, risk, 90 günlük brüt kâr, LTV senaryosu, ürün ilgisi |
| campaign_candidates | Skor tarihinde deney adayı | Gerekçe, öncelik, deney veya kontrol grubu |
| cohort_retention | İlk satış ayı + izleyen ay indeksi | İlk ay müşteri sayısı, aktif müşteri sayısı, dönem devamlılığı |
| labeled_snapshots | Müşteri + geçmiş kesit tarihi | Eğitim için özellikler ve tamamlanmış 90 günlük hedefler |
| quarantine | Reddedilen işlem olayı | İlk saptanan red nedeni; kaynak kayıt korunur |

## Özellikler ve hedefler

| Alan | Tanım |
|---|---|
| recency_days | Skor tarihi eksi son gerçekleşmiş satış; ondalıklı gün |
| tenure_days | Skor tarihi eksi gözlem içindeki ilk satış; gerçek müşteri yaşam süresi olduğu iddia edilmez |
| frequency_365 / frequency_90 | İlgili geriye bakış aralığında farklı satış siparişi sayısı |
| frequency_previous90 | Skor tarihinden 180–90 gün önceki farklı satış siparişi sayısı |
| net_revenue_365 / net_revenue_90 | Olay tarihine göre satış − iade tutarı |
| gross_margin_365 | Net ciro − işaretli ürün maliyeti |
| average_order_value | 365 günlük satış tutarı / satış siparişi; iadeler bu özelliğin payında düşülmez |
| online_share / discount_share | Satış satırlarının online / indirimli olan oranı; sipariş bazlı oran değildir |
| return_unit_rate | 365 gündeki iade miktarı / satış miktarı; geçmiş pencere dışındaki satışların iadeleri oranı etkileyebilir |
| category_count / brand_count | 365 günlük satışlarda farklı kategori / marka sayısı |
| order_trend | (Son 90 gün siparişi + 1) / (önceki 90 gün siparişi + 1) |
| inactive_next90 | Gelecek 90 günde hiç satış yoksa 1; iade ve iptal satın alma sayılmaz |
| margin_next90 | Gelecek 90 günde kaydedilen brüt kâr toplamı; sadece iade varsa negatif olabilir |
| inactive_risk90 | Gelecek 90 günde satış olmaması için model olasılığı |
| expected_margin90 | Gelecek 90 gündeki brüt kâr tahmini; negatif değerler korunur |
| top_category / top_brand / top_product_id | Önceki 365 gün satış tutarında en yüksek paya sahip alan; iadeler tercih sıralamasında düşülmez |
| ltv_3year_scenario | 90 günlük tahmini brüt kârın belirtilmiş devamlılık/iskonto varsayımlarıyla genişletilmesi |

## Önemli ayrımlar

- “Şampiyon” gibi segmentler kural tabanlıdır; kümeleme algoritması sonucu değildir.
- RFM yalnızca son 180 günde satış yapmış müşteriler için raporlanır; tüm tarihsel müşteriler aynı segment evreninde değildir.
- city, iletişim/izin bilgileri ve sentetik kimlikler model girdisi değildir.
- Müşteri hash'i anonimlik garantisi değildir. Bu sürüm yalnızca kurgusal kaynaklarla çalışır.
- Anahtarlar aynı kanıtta sıralamadan bağımsızdır; yeni bir doğrulama kanıtı geldiğinde değişebilir.
  Canlı entegrasyon için kalıcı anahtar kayıt defteri ve birleşim geçmişi gerekir.
- Güncel izin müşteri grubu içinde AND ile birleştirilir; tek opt-out adaylığı engeller.
  Gerçek izin yönetimi için kanal ve zaman bazlı izin kaydı gerekir; bu alan hukuki uygunluk beyanı değildir.
