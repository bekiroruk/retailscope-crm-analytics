let
    Source = Csv.Document(File.Contents(Text.Combine({DataRoot, "data_quality_metrics.csv"}, "\")), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"metric", type text}, {"label", type text}, {"value", Int64.Type},
        {"unit", type text}, {"status", type text}
    }, "en-US")
in
    Typed
