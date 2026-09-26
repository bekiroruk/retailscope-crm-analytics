let
    Source = Csv.Document(File.Contents(Text.Combine({DataRoot, "dim_customer.csv"}, "\")), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Headers, {{"customer_id", type text}, {"country", type text}}, "en-US")
in
    Typed
