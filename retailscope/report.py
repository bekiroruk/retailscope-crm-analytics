"""Self-contained offline report: no CDN, tracking or external requests."""
import json
from pathlib import Path

import pandas as pd


def write_report(directory: Path, template: Path, events, scores, campaign, cohorts, quality, metrics, config):
    monthly = events.assign(month=events.event_time.dt.strftime("%Y-%m")).groupby("month", as_index=False).agg(
        net_revenue=("net_revenue", "sum"), gross_margin=("gross_margin", "sum"))
    category = events.groupby("category", as_index=False).net_revenue.sum().sort_values("net_revenue", ascending=False)
    columns = ["customer_id", "segment", "city", "recency_days", "frequency_365", "net_revenue_365",
               "inactive_risk90", "expected_margin90", "top_category", "top_brand", "marketing_consent"]
    payload = dict(config=config, quality=quality, metrics=metrics,
                   totals=dict(net_revenue=float(events.net_revenue.sum()), gross_margin=float(events.gross_margin.sum()),
                               sales_orders=int(events.loc[events.event_type.eq("sale"), "order_id"].nunique()),
                               scored_customers=len(scores), campaign_size=len(campaign)),
                   monthly=monthly.round(2).to_dict("records"), categories=category.round(2).to_dict("records"),
                   customers=scores[columns].round(4).to_dict("records"), campaign=campaign.round(4).to_dict("records"),
                   cohorts=cohorts.round(4).to_dict("records"))
    data = json.dumps(payload, ensure_ascii=False, allow_nan=False).replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    html = template.read_text(encoding="utf-8").replace("__REPORT_DATA__", data)
    (directory / "dashboard.html").write_text(html, encoding="utf-8")
    cm, vm = metrics["test_classification"], metrics["test_value"]
    base = metrics["test_value_baseline"]
    body = f"""# RetailScope — Çalıştırma sonuçları

Bu rapor yalnızca tohum değeri {config['seed']} ile üretilmiş kurgusal verinin sonuçlarını gösterir.
ebebek'in gerçek müşterileri, cirosu veya model başarısı hakkında bilgi içermez.

## İş sorusu

Son 180 günde alışverişi bulunan hangi müşteriler önümüzdeki 90 günde alışveriş yapmayabilir?
Bu müşterilerin hangi segment, kategori ve markaya ilgisi var; hangileri kontrollü bir kampanya deneyi için adaydır?

## Veri ve kalite

| Ölçüm | Sonuç |
|---|---:|
| Ham müşteri kaydı | {quality['raw_customer_records']:,} |
| Tekil müşteri | {quality['unified_customers']:,} |
| Birleştirilen ek kayıt | {quality['collapsed_records']:,} |
| Ham işlem satırı | {quality['raw_rows']:,} |
| Tam tekrar nedeniyle çıkarılan satır | {quality['exact_duplicates_removed']:,} |
| Karantinaya alınan satır | {quality['quarantined_rows']:,} |
| Kabul edilen işlem satırı | {quality['accepted_rows']:,} |
| Skorlanan müşteri | {len(scores):,} |
| Kampanya deneyi adayı | {len(campaign):,} |

Kalite mutabakatı: ham satır = tam tekrar + karantina + kabul edilen satır.
İade olayları tarihindeki net ciro ve brüt kârı azaltır; iptaller sıfır parasal katkıyla saklanır.
Tamamen iade edilen satış da gerçekleşmiş satın alma etkileşimi sayılır; iade işlemi yeni satın alma değildir.

## Model değerlendirmesi

| Metrik | Model | Basit karşılaştırma |
|---|---:|---:|
| Risk Average Precision | {cm['average_precision']:.4f} | Önsel olasılık: {metrics['test_classification_baseline']['average_precision']:.4f} |
| Risk ROC-AUC | {cm['roc_auc']:.4f} | Önsel olasılık: {metrics['test_classification_baseline']['roc_auc']:.4f} |
| İlk %20 için lift | {cm['lift_at_20pct']:.3f} | Recency sıralaması: {metrics['test_recency_ranking']['lift_at_20pct']:.3f} |
| Brier kaybı (düşük iyi) | {cm['brier']:.4f} | Önsel olasılık: {metrics['test_classification_baseline']['brier']:.4f} |
| 90 günlük brüt kâr MAE (TL) | {vm['mae']:.2f} | Eğitim ortalaması: {base['mae']:.2f} |
| 90 günlük brüt kâr WAPE | {vm['wape']:.3f} | Eğitim ortalaması: {base['wape']:.3f} |

Test toplamında gerçek brüt kâr {vm['actual_sum']:.2f} TL, tahmin {vm['predicted_sum']:.2f} TL'dir.
Toplam tahmin yanlılığı %{100 * (vm['predicted_sum'] / vm['actual_sum'] - 1):.1f}.
Değer modeli ortalama baseline'dan düşük MAE üretse de yüksek bireysel hata ve toplam yanlılık
nedeniyle bütçe/teklif kararı için hazır kabul edilmemelidir.

Sınıflandırıcı: `{metrics['selected_classifier']}`. Değer modeli: `{metrics['selected_value_model']}`.
Model seçimi yalnızca doğrulama dönemi sonuçlarıyla yapılır. Daha basit model seçilirse sonuç aynen korunur.
Test başlangıcı {config['test_cutoff']}; takip penceresi 90 gün. Test metrikleri gerçek veri başarısı veya gelir artışı kanıtı değildir.
Müşteriler farklı zaman dilimlerinde tekrar bulunabilir; ölçülen hedef mevcut müşteri kitlesinin ileriki dönemde skorlanmasıdır.

## CRM aksiyonu

Kampanya adayı: güncel pazarlama izni var; kimlik çakışması yok; son alışveriş en az 30 gün önce;
risk en az %50; tahmini 90 günlük brüt kâr pozitif. Öncelik = risk × pozitif tahmini brüt kâr.
Bu öncelik bir iş kuralıdır; kampanyanın nedensel ek etkisini tahmin etmez.
Seçilen adaylar rastgele treatment/control gruplarına atanır. Hiçbir ileti gönderilmez.
Önerilen deney ölçümü: 90 günlük müşteri başına net ek brüt kâr; indirim ve iletişim maliyeti dahil.
Henüz kampanya sonucu, uplift veya ROI ölçülmemiştir.

## Müşteri değeri ve sınırlar

`expected_margin90`: önümüzdeki 90 gündeki brüt kâr tahmini; tam yaşam boyu değer değildir.
`ltv_3year_scenario`: bu tahminin 12 çeyrek, %70 çeyreklik devamlılık, %2,5 çeyreklik iskonto
ve sıfır edinme maliyeti varsayımlarıyla uzatıldığı senaryo. Parametreler öğrenilmemiştir.
Brüt kârdan personel, kira, lojistik ve müşteri hizmetleri giderleri düşülmemiştir.
Fiyatlar ve maliyetler sentetiktir. RFM parasal eşikleri gerçek veri/enflasyon koşullarında yeniden belirlenmelidir.

## Sonraki kabul kapıları

1. Gerçek işlem verisinde şema, döviz, iade, müşteri kimliği ve zaman alanlarını doğrula.
2. Yeni veride zaman temelli geri test ve olasılık kalibrasyonu yap; basit modelleri karşılaştır.
3. SQL Server yüklemesini ve Power BI ilişkileri/ölçülerini Windows ortamında çalıştır.
4. Kampanya maliyeti, örneklem büyüklüğü ve minimum anlamlı etki ile A/B deneyi tasarla.
5. Gerçek sonuçlar gelince artan brüt kârı ve güven aralıklarını raporla.
"""
    (directory / "BUSINESS_REPORT.md").write_text(body, encoding="utf-8")
