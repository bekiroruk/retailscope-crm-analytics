let
    Source = Csv.Document(File.Contents(Text.Combine({DataRoot, "cohort_retention.csv"}, "\")), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"cohort", type text}, {"month_index", Int64.Type}, {"cohort_size", Int64.Type},
        {"active_customers", Int64.Type}, {"retention_rate", type number}
    }, "en-US")
in
    Typed
