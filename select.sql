-- Стоит ли инвесторам делать депозит в данный волт ? 

-- 1. Общая доходность за весь период:
SELECT  
    MAX(share_price) as start_share_price, 
    MIN(share_price) as min_share_price, 
    ((MAX(share_price) - MIN(share_price)) / MIN(share_price)) * 100 as total_share_price_percent
FROM vault_metrics;

-- start_share_price  | min_share_price | total_share_price_percent 
--------------------+-----------------+---------------------------
-- 1.0340069061560646 |               1 |         3.400690615606461

-- total_share_price_percent = 3.4 %  
-- Общая доходность за весь период больше нуля. Это значит, что вольт успешно генерирует доход 


-- 2. Динамика TVL (приток/отток средств): 
SELECT 
    MAX(tvl_assets) as max_tvl_assets,
    MIN(tvl_assets) as min_tvl_assets,
    (MAX(tvl_assets) - MIN(tvl_assets)) / MIN(tvl_assets) * 100 as total_tvl_change_percent 
FROM vault_metrics
WHERE tvl_assets > 0;


--  max_tvl_assets   | min_tvl_assets  | total_tvl_change_percent 
-------------------+-----------------+--------------------------
 32489511770.29747 | 111854.89738775 |       29046023.620024543


-- Для анализа целесообразности депозита лучще взять выборку за последние 3 месяца.

SELECT 
    MAX(tvl_assets) as max_tvl_assets, 
    MIN(tvl_assets) as min_tvl_assets, 
    (MAX(tvl_assets) - MIN(tvl_assets)) / MIN(tvl_assets) * 100 as tvl_change_percent 
FROM vault_metrics 
WHERE timestamp > current_date - interval '3 months' ;


--  max_tvl_assets   |  min_tvl_assets   | tvl_change_percent 
-------------------+-------------------+--------------------
 32489511770.29747 | 17489439740.40693 |  85.76645251382725


SELECT 
    MAX(share_price) as max_share_price, 
    min(share_price) as min_share_price,
 ((MAX(share_price) - MIN(share_price)) / MIN(share_price)) * 100 as share_price_percent 
FROM vault_metrics
WHERE timestamp > current_date - interval '3 months' ;


-- max_share_price   |  min_share_price   | share_price_percent 
--------------------+--------------------+---------------------
 1.0345397387129067 | 1.0124618102727339 |   2.180618391347085


-- tvl_change_percent показавает рост активов на 85.7% и стабильный рост цены доли на 2.18% за 3 месяца
-- что подтверждает эффективность стратегии 


-- 3. Расчет APR (Annual Percentage Rate) Годовая доходность

-- APR = (share_price_percent / кол-во дней сбора) * 365 


WITH stats AS (
    SELECT 
        MIN(timestamp) as start_time,
        MAX(timestamp) as end_time,
        MIN(share_price) as start_price,
        MAX(share_price) as end_price
    FROM vault_metrics
    where timestamp > current_date - interval '3 months' 
),
calculations AS (
    SELECT 
        EXTRACT(EPOCH FROM (end_time - start_time)) / 86400 as days_diff,
        (end_price - start_price) / start_price as total_return
    FROM stats
)
SELECT 
    total_return * 100 as total_return_pct,
    (total_return / NULLIF(days_diff, 0)) * 365 * 100 as current_apr
FROM calculations;


-- total_return_pct  |    current_apr    
-------------------+-------------------
 2.180618391347085 | 8.929343485000505

-- Результат APR 8.9% для вольта на стейблкоинах (sbUSD) это сильный показатель.



-- итоговый вывод : стоит инвестировать 