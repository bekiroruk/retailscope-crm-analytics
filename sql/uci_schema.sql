-- Run in a dedicated user database. Non-destructive DDL for UCI Online Retail II marts.
SET XACT_ABORT ON;
GO
IF SCHEMA_ID(N'retailscope_uci') IS NULL EXEC(N'CREATE SCHEMA retailscope_uci');
GO
IF OBJECT_ID(N'retailscope_uci.dim_customer', N'U') IS NULL
CREATE TABLE retailscope_uci.dim_customer (
    customer_id varchar(20) NOT NULL PRIMARY KEY,
    country nvarchar(100) NOT NULL
);
GO
IF OBJECT_ID(N'retailscope_uci.dim_product', N'U') IS NULL
CREATE TABLE retailscope_uci.dim_product (
    product_id varchar(30) NOT NULL PRIMARY KEY,
    product_name nvarchar(255) NOT NULL
);
GO
IF OBJECT_ID(N'retailscope_uci.dim_date', N'U') IS NULL
CREATE TABLE retailscope_uci.dim_date (
    [date] date NOT NULL PRIMARY KEY,
    [year] int NOT NULL,
    [month] int NOT NULL,
    year_month char(7) NOT NULL
);
GO
IF OBJECT_ID(N'retailscope_uci.fact_sales', N'U') IS NULL
CREATE TABLE retailscope_uci.fact_sales (
    event_id varchar(40) NOT NULL PRIMARY KEY,
    order_id varchar(30) NOT NULL,
    customer_id varchar(20) NOT NULL REFERENCES retailscope_uci.dim_customer(customer_id),
    product_id varchar(30) NOT NULL REFERENCES retailscope_uci.dim_product(product_id),
    event_type varchar(12) NOT NULL CHECK(event_type IN ('sale','return')),
    signed_quantity int NOT NULL,
    unit_price decimal(18,4) NOT NULL,
    net_revenue decimal(18,4) NOT NULL,
    event_date date NOT NULL REFERENCES retailscope_uci.dim_date([date])
);
GO
IF OBJECT_ID(N'retailscope_uci.customer_scores', N'U') IS NULL
CREATE TABLE retailscope_uci.customer_scores (
    customer_id varchar(20) NOT NULL REFERENCES retailscope_uci.dim_customer(customer_id),
    snapshot_date date NOT NULL,
    segment nvarchar(80) NOT NULL,
    rfm_score char(3) NOT NULL,
    r_score int NOT NULL,
    f_score int NOT NULL,
    m_score int NOT NULL,
    recency_days float NOT NULL,
    frequency_365 int NOT NULL,
    net_revenue_365 decimal(18,4) NOT NULL,
    inactive_risk90 float NOT NULL CHECK(inactive_risk90 BETWEEN 0 AND 1),
    expected_revenue90 decimal(18,4) NOT NULL,
    top_product_id varchar(30) NULL,
    top_product_name nvarchar(255) NULL,
    activation_eligible bit NOT NULL CHECK(activation_eligible = 0),
    activation_exclusion_reason nvarchar(200) NOT NULL,
    analysis_priority decimal(18,4) NOT NULL,
    CONSTRAINT PK_uci_customer_scores PRIMARY KEY(customer_id,snapshot_date)
);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID(N'retailscope_uci.fact_sales') AND name=N'IX_uci_sales_customer_date')
CREATE INDEX IX_uci_sales_customer_date ON retailscope_uci.fact_sales(customer_id,event_date)
INCLUDE(event_type,net_revenue,order_id);
GO
CREATE OR ALTER VIEW retailscope_uci.v_monthly_performance AS
SELECT d.year_month,
       SUM(f.net_revenue) AS net_revenue,
       COUNT(DISTINCT CASE WHEN f.event_type='sale' THEN f.order_id END) AS sale_orders,
       COUNT(DISTINCT CASE WHEN f.event_type='sale' THEN f.customer_id END) AS purchasing_customers
FROM retailscope_uci.fact_sales AS f
JOIN retailscope_uci.dim_date AS d ON d.[date]=f.event_date
GROUP BY d.year_month;
GO
CREATE OR ALTER VIEW retailscope_uci.v_customer360 AS
SELECT s.*, c.country
FROM retailscope_uci.customer_scores AS s
JOIN retailscope_uci.dim_customer AS c ON c.customer_id=s.customer_id;
GO
