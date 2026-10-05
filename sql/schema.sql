-- The warehouse: the areas we read, the client's own units, every competitor unit seen on
-- realestate.eg (listing), every asking price seen (price_observation, append-only), the rows that
-- failed a check (quarantine) and the views the report and Power BI read. Prices are in EGP.
-- Safe to run again: the load_reference step runs it at the start of every weekly run.

CREATE TABLE IF NOT EXISTS area (             -- the areas we read (data/areas.csv)
    area_id     text PRIMARY KEY,             -- the site's slug, e.g. 'new-cairo'
    name        text NOT NULL,
    location_id integer NOT NULL UNIQUE       -- the site's ?location= id
);

CREATE TABLE IF NOT EXISTS our_unit (         -- the client's own units for sale (data/our_units.csv, generated)
    unit_code    text PRIMARY KEY,
    area_id      text NOT NULL REFERENCES area,
    compound     text NOT NULL,
    unit_type    text NOT NULL,               -- spelled as the site's badge, e.g. 'Town House'
    bedrooms     integer NOT NULL,
    size_m2      numeric(10, 2) NOT NULL CHECK (size_m2 > 0),
    asking_price numeric(14, 2) NOT NULL CHECK (asking_price > 0),
    price_per_m2 numeric(14, 2) GENERATED ALWAYS AS (round(asking_price / size_m2, 2)) STORED
);

CREATE TABLE IF NOT EXISTS listing (          -- one competitor unit on the site; no contact data of any kind
    listing_id bigint PRIMARY KEY,            -- the number at the start of the unit page's path
    url        text NOT NULL,
    area_id    text NOT NULL REFERENCES area,
    compound   text,                          -- the site's compound name as shown (with area and developer words)
    developer  text,
    unit_type  text NOT NULL,
    bedrooms   integer,
    bathrooms  integer,
    size_m2    numeric(10, 2) NOT NULL CHECK (size_m2 > 0),
    first_seen date NOT NULL,
    last_seen  date NOT NULL
);

CREATE TABLE IF NOT EXISTS price_observation ( -- every asking price seen, never updated or deleted
    listing_id   bigint NOT NULL REFERENCES listing,
    observed_on  date NOT NULL,               -- the day the unit page was read (UTC)
    asking_price numeric(14, 2) NOT NULL CHECK (asking_price > 0),
    price_per_m2 numeric(14, 2) NOT NULL,
    fetched_at   timestamptz NOT NULL,
    run_week     date NOT NULL,               -- the weekly run that read it (the Sunday its week starts)
    PRIMARY KEY (listing_id, observed_on)
);

CREATE TABLE IF NOT EXISTS quarantine (       -- a card or unit page that failed a check, kept with its reason
    id         bigserial PRIMARY KEY,
    run_week   date NOT NULL,
    fetched_at timestamptz NOT NULL,
    url        text NOT NULL,
    reason     text NOT NULL,
    payload    jsonb NOT NULL,                -- what was read from the card and the page
    UNIQUE (run_week, url, reason)            -- a rerun in the same week adds nothing
);

-- One row per listing: its most recent asking price, with the listing's description.
CREATE OR REPLACE VIEW latest_price AS
SELECT DISTINCT ON (o.listing_id)
       o.listing_id, l.area_id, l.compound, l.developer, l.unit_type, l.bedrooms, l.bathrooms,
       l.size_m2, o.observed_on, o.asking_price, o.price_per_m2, o.run_week, l.url
FROM price_observation o
JOIN listing l USING (listing_id)
ORDER BY o.listing_id, o.observed_on DESC;

-- The market per area and unit type in the latest run: the median, lowest and highest asking price per m².
CREATE OR REPLACE VIEW area_benchmark AS
SELECT area_id, unit_type, count(*) AS listings,
       (percentile_cont(0.5) WITHIN GROUP (ORDER BY price_per_m2))::numeric AS median_price_per_m2,
       min(price_per_m2) AS min_price_per_m2, max(price_per_m2) AS max_price_per_m2
FROM latest_price
WHERE run_week = (SELECT max(run_week) FROM price_observation)
GROUP BY area_id, unit_type;

-- One row per unit of ours: its price per m² against the latest run's median of the same type in its
-- area, and the share of those competitor listings priced below ours per m². No listing to compare: NULLs.
CREATE OR REPLACE VIEW unit_gap AS
SELECT u.unit_code, u.area_id, u.compound, u.unit_type, u.size_m2, u.asking_price, u.price_per_m2,
       b.median_price_per_m2,
       round((u.price_per_m2 - b.median_price_per_m2) / b.median_price_per_m2 * 100, 1) AS gap_pct,
       count(p.listing_id) AS listings_compared,
       round(avg((p.price_per_m2 < u.price_per_m2)::int) * 100, 1) AS pct_listings_cheaper
FROM our_unit u
LEFT JOIN area_benchmark b USING (area_id, unit_type)
LEFT JOIN latest_price p ON p.area_id = u.area_id AND p.unit_type = u.unit_type
                       AND p.run_week = (SELECT max(run_week) FROM price_observation)
GROUP BY u.unit_code, b.median_price_per_m2;

-- Every asking price change: an observation whose price differs from the listing's previous one.
-- caught_week is the run that had both prices, so the first run that could see the change.
CREATE OR REPLACE VIEW price_change AS
SELECT t.listing_id, l.area_id, l.compound, l.developer, l.unit_type, t.observed_on,
       t.old_price, t.asking_price AS new_price,
       round((t.asking_price - t.old_price) / t.old_price * 100, 1) AS change_pct,
       t.caught_week, t.asking_price < t.old_price AS is_cut
FROM (
    SELECT o.*,
           lag(o.asking_price) OVER w AS old_price,
           greatest(o.run_week, lag(o.run_week) OVER w) AS caught_week
    FROM price_observation o
    WINDOW w AS (PARTITION BY o.listing_id ORDER BY o.observed_on)
) t
JOIN listing l USING (listing_id)
WHERE t.old_price IS NOT NULL AND t.asking_price <> t.old_price;

-- The market per compound in the latest run: the median asking price per m² by area, compound and developer.
CREATE OR REPLACE VIEW compound_benchmark AS
SELECT area_id, compound, developer, count(*) AS listings,
       (percentile_cont(0.5) WITHIN GROUP (ORDER BY price_per_m2))::numeric AS median_price_per_m2
FROM latest_price
WHERE run_week = (SELECT max(run_week) FROM price_observation)
GROUP BY area_id, compound, developer;
