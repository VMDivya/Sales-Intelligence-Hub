-- Branches table
CREATE TABLE branches (
    branch_id SERIAL PRIMARY KEY,
    branch_name VARCHAR(100) NOT NULL,
    branch_admin_name VARCHAR(100) NOT NULL
);

-- Customer Sales table
CREATE TABLE customer_sales (
    sale_id SERIAL PRIMARY KEY,
    branch_id INT REFERENCES branches(branch_id),
    date DATE NOT NULL,
    name VARCHAR(100) NOT NULL,
    mobile_number VARCHAR(15) UNIQUE,
    product_name VARCHAR(30),
    gross_sales NUMERIC(12,2) NOT NULL,
    received_amount NUMERIC(12,2) DEFAULT 0,
    pending_amount NUMERIC(12,2) GENERATED ALWAYS AS (gross_sales - received_amount) STORED,
    status VARCHAR(10) DEFAULT 'Open'
);

-- Users table
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    password VARCHAR(255) NOT NULL,
    branch_id INT REFERENCES branches(branch_id),
    role VARCHAR(20) CHECK (role IN ('Super Admin','Admin')),
    email VARCHAR(255) UNIQUE NOT NULL
);

-- Payment Splits table
CREATE TABLE payment_splits (
    payment_id SERIAL PRIMARY KEY,
    sale_id INT REFERENCES customer_sales(sale_id),
    payment_date DATE NOT NULL,
    amount_paid NUMERIC(12,2) NOT NULL,
    payment_method VARCHAR(50)
	
);



SELECT * FROM branches;
SELECT * FROM customer_sales;
SELECT * FROM users;
SELECT * FROM payment_splits ;


CREATE OR REPLACE FUNCTION update_received_amount()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE customer_sales
    SET received_amount = (
        SELECT COALESCE(SUM(amount_paid), 0)
        FROM payment_splits
        WHERE sale_id = NEW.sale_id
    )
    WHERE sale_id = NEW.sale_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_received_amount
AFTER INSERT ON payment_splits
FOR EACH ROW
EXECUTE FUNCTION update_received_amount();

CREATE OR REPLACE FUNCTION update_status()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE customer_sales
    SET status = CASE
        WHEN received_amount >= gross_sales THEN 'Close'
        ELSE 'Open'
    END
    WHERE sale_id = NEW.sale_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_status
AFTER UPDATE OF received_amount ON customer_sales
FOR EACH ROW
EXECUTE FUNCTION update_status();

SELECT * FROM customer_sales;

TRUNCATE TABLE payment_splits RESTART IDENTITY CASCADE;
TRUNCATE TABLE customer_sales RESTART IDENTITY CASCADE;
TRUNCATE TABLE branches RESTART IDENTITY CASCADE;

ALTER TABLE customer_sales ADD COLUMN mobile_number VARCHAR(20);

SELECT setval('customer_sales_sale_id_seq', (SELECT MAX(sale_id) FROM customer_sales)+1);
-- 1
ALTER TABLE customer_sales ADD COLUMN received_amount NUMERIC(12,2) DEFAULT 0;

SELECT setval(
    pg_get_serial_sequence('payment_splits', 'payment_id'),
    (SELECT MAX(payment_id) FROM payment_splits)
);

