let
    Source = Csv.Document(File.Contents(Text.Combine({DataRoot, "customer_scores.csv"}, "\")), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"customer_id", type text}, {"snapshot_date", type date}, {"segment", type text},
        {"rfm_score", type text}, {"r_score", Int64.Type}, {"f_score", Int64.Type},
        {"m_score", Int64.Type}, {"recency_days", type number}, {"frequency_365", Int64.Type},
        {"net_revenue_365", Currency.Type}, {"inactive_risk90", type number},
        {"expected_revenue90", Currency.Type}, {"top_product_id", type text},
        {"top_product_name", type text}, {"activation_eligible", type logical},
        {"activation_exclusion_reason", type text}, {"analysis_priority", Currency.Type}
    }, "en-US")
in
    Typed
