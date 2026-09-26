-- Run in a dedicated user database (not master). Non-destructive DDL.
SET XACT_ABORT ON;
GO
IF SCHEMA_ID(N'retailscope') IS NULL EXEC(N'CREATE SCHEMA retailscope');
GO
IF OBJECT_ID(N'retailscope.dim_customer', N'U') IS NULL
CREATE TABLE retailscope.dim_customer (
    customer_id varchar(17) NOT NULL PRIMARY KEY,
    city nvarchar(80) NOT NULL,
    marketing_consent bit NOT NULL,
    identity_review_required bit NOT NULL,
    source_records int NOT NULL CHECK (source_records > 0)
);
GO
IF OBJECT_ID(N'retailscope.dim_product', N'U') IS NULL
CREATE TABLE retailscope.dim_product (
    product_id varchar(20) NOT NULL PRIMARY KEY,
    product_name nvarchar(160) NOT NULL,
    category nvarchar(100) NOT NULL,
    brand nvarchar(100) NOT NULL,
    list_price decimal(18,2) NOT NULL,
    unit_cost decimal(18,2) NOT NULL
);
GO
IF OBJECT_ID(N'retailscope.dim_date', N'U') IS NULL
CREATE TABLE retailscope.dim_date (
    [date] date NOT NULL PRIMARY KEY,
    [year] int NOT NULL,
    [month] int NOT NULL,
    year_month char(7) NOT NULL
);
GO
IF OBJECT_ID(N'retailscope.fact_sales', N'U') IS NULL
CREATE TABLE retailscope.fact_sales (
    event_id varchar(30) NOT NULL PRIMARY KEY,
    order_id varchar(30) NOT NULL,
    customer_id varchar(17) NOT NULL REFERENCES retailscope.dim_customer(customer_id),
    product_id varchar(20) NOT NULL REFERENCES retailscope.dim_product(product_id),
    event_type varchar(12) NOT NULL CHECK(event_type IN ('sale','return','cancelled')),
    channel varchar(12) NOT NULL,
    signed_quantity int NOT NULL,
    net_revenue decimal(18,2) NOT NULL,
    gross_margin decimal(18,2) NOT NULL,
    event_date date NOT NULL REFERENCES retailscope.dim_date([date])
);
GO
IF OBJECT_ID(N'retailscope.customer_scores', N'U') IS NULL
CREATE TABLE retailscope.customer_scores (
    customer_id varchar(17) NOT NULL REFERENCES retailscope.dim_customer(customer_id),
    snapshot_date date NOT NULL,
    segment nvarchar(80) NOT NULL,
    rfm_score char(3) NOT NULL,
    r_score int NOT NULL,
    f_score int NOT NULL,
    m_score int NOT NULL,
    recency_days float NOT NULL,
    frequency_365 int NOT NULL,
    net_revenue_365 decimal(18,2) NOT NULL,
    gross_margin_365 decimal(18,2) NOT NULL,
    inactive_risk90 float NOT NULL CHECK(inactive_risk90 BETWEEN 0 AND 1),
    expected_margin90 decimal(18,2) NOT NULL,
    ltv_3year_scenario decimal(18,2) NOT NULL,
    top_category nvarchar(100) NULL,
    top_brand nvarchar(100) NULL,
    top_product_id varchar(20) NULL,
    CONSTRAINT PK_customer_scores PRIMARY KEY(customer_id,snapshot_date)
);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID(N'retailscope.fact_sales') AND name=N'IX_sales_customer_date')
CREATE INDEX IX_sales_customer_date ON retailscope.fact_sales(customer_id,event_date) INCLUDE(event_type,net_revenue,gross_margin,order_id);
GO
CREATE OR ALTER VIEW retailscope.v_monthly_performance AS
SELECT d.year_month, f.channel,
       SUM(f.net_revenue) AS net_revenue,
       SUM(f.gross_margin) AS gross_margin,
       COUNT(DISTINCT CASE WHEN f.event_type='sale' THEN f.order_id END) AS sale_orders,
       COUNT(DISTINCT CASE WHEN f.event_type='sale' THEN f.customer_id END) AS purchasing_customers
FROM retailscope.fact_sales AS f
JOIN retailscope.dim_date AS d ON d.[date]=f.event_date
GROUP BY d.year_month,f.channel;
GO
CREATE OR ALTER VIEW retailscope.v_customer360 AS
SELECT s.*, c.city, c.marketing_consent, c.identity_review_required
FROM retailscope.customer_scores AS s
JOIN retailscope.dim_customer AS c ON c.customer_id=s.customer_id;
GO
