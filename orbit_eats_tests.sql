-- Orbit Eats - test cases (run after orbit_eats_schema.sql)
-- Run with: mysql -u root -p --force < orbit_eats_tests.sql
-- (--force keeps going after the statements that are expected to fail)
USE orbit_eats;

-- ---------- Sample data ----------
INSERT INTO employee (first_name, last_name, phone, area, hire_date) VALUES
  ('Luis',  'Paredes', '0991112222', 'delivery', '2026-01-10'),
  ('Marta', 'Vega',    '0993334444', 'kitchen',  '2026-02-01');

INSERT INTO product (name, description, base_price, category) VALUES
  ('Classic Burger', 'Beef burger with cheese', 6.50, 'burgers'),
  ('Fries',          'Medium portion',          2.00, 'sides');

INSERT INTO ingredient (name, unit_of_measure, current_stock, minimum_stock) VALUES
  ('Burger bun',   'unit', 40,   20),
  ('Beef patty',   'unit', 8,    15),
  ('Cheese slice', 'unit', 50,   20),
  ('Potato',       'kg',   12.5, 5);

INSERT INTO product_ingredient (product_id, ingredient_id, quantity_required) VALUES
  (1, 1, 1), (1, 2, 1), (1, 3, 1),
  (2, 4, 0.25);

INSERT INTO supplier (first_name, last_name, company, phone, email) VALUES
  ('Andrea', 'Mora', 'Carnes del Valle', '0995556666', 'ventas@carnesvalle.com'),
  ('Pedro',  'Ruiz', 'Panaderia Central', '0997778888', NULL);

INSERT INTO supply (supplier_id, ingredient_id, purchase_price, last_purchase_date) VALUES
  (1, 2, 1.20, '2026-11-02'),
  (2, 1, 0.30, '2026-11-05');

-- ---------- TC-01 (FR-01): register a customer ----------
INSERT INTO customer (first_name, last_name, address, phone, email)
VALUES ('Ana', 'Lopez', 'Av. Amazonas N24-10', '0981234567', 'ana.lopez@mail.com');
SELECT customer_id, first_name, email, registration_date FROM customer WHERE email = 'ana.lopez@mail.com';

-- ---------- TC-02 (FR-01): duplicate email is rejected ----------
INSERT INTO customer (first_name, last_name, address, phone, email)
VALUES ('Ana', 'Perez', 'Calle 10', '0980000000', 'ana.lopez@mail.com');
-- expected: ERROR 1062 Duplicate entry ... for key 'uq_customer_email'

-- ---------- TC-03 (FR-02): record an order with its products ----------
INSERT INTO orders (customer_id, employee_id, delivery_address, status)
VALUES (1, 1, 'Av. Amazonas N24-10', 'received');
INSERT INTO order_detail (order_id, product_id, quantity, unit_price, subtotal) VALUES
  (1, 1, 2, 6.50, 13.00),
  (1, 2, 1, 2.00,  2.00);
UPDATE orders SET total = (SELECT SUM(subtotal) FROM order_detail WHERE order_id = 1) WHERE order_id = 1;
SELECT o.order_id, c.first_name, p.name, od.quantity, od.subtotal, o.total, o.status
FROM orders o
JOIN customer c      ON c.customer_id = o.customer_id
JOIN order_detail od ON od.order_id   = o.order_id
JOIN product p       ON p.product_id  = od.product_id
WHERE o.order_id = 1;

-- ---------- TC-04 (FR-02): invalid status and unknown customer are rejected ----------
UPDATE orders SET status = 'lost' WHERE order_id = 1;
-- expected: ERROR 4025/3819 CONSTRAINT ck_orders_status failed
INSERT INTO orders (customer_id, delivery_address) VALUES (999, 'Nowhere 123');
-- expected: ERROR 1452 foreign key constraint fails (fk_orders_customer)

-- ---------- TC-05 (FR-03): list the recipe of a product ----------
SELECT p.name AS product, i.name AS ingredient, pi.quantity_required, i.unit_of_measure
FROM product_ingredient pi
JOIN product p    ON p.product_id    = pi.product_id
JOIN ingredient i ON i.ingredient_id = pi.ingredient_id
WHERE p.name = 'Classic Burger';
-- expected: 3 rows (Burger bun, Beef patty, Cheese slice)

-- ---------- TC-06 (FR-04): ingredients below minimum stock ----------
SELECT name, current_stock, minimum_stock
FROM ingredient
WHERE current_stock < minimum_stock;
-- expected: 1 row (Beef patty 8 < 15)

-- ---------- TC-07 (FR-05): suppliers of an ingredient ----------
SELECT i.name AS ingredient, s.company, sp.purchase_price, sp.last_purchase_date
FROM supply sp
JOIN supplier s   ON s.supplier_id   = sp.supplier_id
JOIN ingredient i ON i.ingredient_id = sp.ingredient_id
WHERE i.name = 'Beef patty';
INSERT INTO supply (supplier_id, ingredient_id, purchase_price, last_purchase_date)
VALUES (1, 2, 1.25, '2026-11-10');
-- expected: ERROR 1062 Duplicate entry for key 'uq_supply_supplier_ingredient'

-- ---------- TC-08 (FR-06): price at purchase is kept after a price change ----------
UPDATE product SET base_price = 7.00 WHERE product_id = 1;
SELECT p.name, p.base_price AS current_price, od.unit_price AS price_paid
FROM order_detail od
JOIN product p ON p.product_id = od.product_id
WHERE od.order_id = 1 AND od.product_id = 1;
-- expected: current_price = 7.00, price_paid = 6.50
