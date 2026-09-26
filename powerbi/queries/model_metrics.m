let
    Source = Csv.Document(File.Contents(Text.Combine({DataRoot, "model_metrics.csv"}, "\")), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"metric", type text}, {"label", type text}, {"value", type number},
        {"baseline", type number}, {"unit", type text}, {"split", type text}
    }, "en-US")
in
    Typed
