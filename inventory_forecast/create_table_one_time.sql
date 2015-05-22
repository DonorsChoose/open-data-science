-- run this to create an 'inventory_forecast' table on your Redshift db
DROP TABLE IF EXISTS inventory_forecast;
CREATE TABLE inventory_forecast (
    date_of_interest timestamp without time zone,
    project_count integer,
    CONSTRAINT inventory_forecast_pkey PRIMARY KEY (date_of_interest)
)
sortkey(date_of_interest);
GRANT ALL ON TABLE inventory_forecast TO your_username;