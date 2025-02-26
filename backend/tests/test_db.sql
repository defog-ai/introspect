-- Create tables if they don't exist
CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ticket_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ticket_sales (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id),
    ticket_type_id INTEGER REFERENCES ticket_types(id),
    purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    valid_until TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'used', 'expired'))
);

-- Insert sample data
INSERT INTO customers (name, email) VALUES
    ('John Doe', 'john@example.com'),
    ('Jane Smith', 'jane@example.com'),
    ('Bob Wilson', 'bob@example.com'),
    ('Alice Brown', 'alice@example.com')
ON CONFLICT (email) DO NOTHING;

INSERT INTO ticket_types (name, description, price) VALUES
    ('Standard', 'Regular admission ticket', 50.00),
    ('VIP', 'VIP access with special perks', 150.00),
    ('Student', 'Discounted ticket for students', 25.00)
ON CONFLICT DO NOTHING;

-- Insert sample ticket sales
INSERT INTO ticket_sales (customer_id, ticket_type_id, valid_until, status)
SELECT 
    c.id,
    tt.id,
    CURRENT_TIMESTAMP + INTERVAL '30 days',
    'active'
FROM customers c
CROSS JOIN ticket_types tt
WHERE c.email IN ('john@example.com', 'jane@example.com')
AND tt.name IN ('Standard', 'VIP')
ON CONFLICT DO NOTHING;
