let
    Source = Csv.Document(File.Contents(Text.Combine({DataRoot, "dim_date.csv"}, "\")), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Headers, {{"date", type date}, {"year", Int64.Type}, {"month", Int64.Type}, {"year_month", type text}}, "en-US")
in
    Typed
