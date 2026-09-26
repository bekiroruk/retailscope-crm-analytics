let
    Source = Csv.Document(File.Contents(Text.Combine({DataRoot, "fact_sales.csv"}, "\")), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"event_id", type text}, {"order_id", type text}, {"customer_id", type text},
        {"product_id", type text}, {"event_type", type text}, {"signed_quantity", Int64.Type},
        {"unit_price", Currency.Type}, {"net_revenue", Currency.Type}, {"event_date", type date}
    }, "en-US")
in
    Typed
