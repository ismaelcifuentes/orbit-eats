-- Orbit Eats - schema (MySQL 8)
DROP DATABASE IF EXISTS orbit_eats;
CREATE DATABASE orbit_eats;
USE orbit_eats;

CREATE TABLE customer (
    customer_id       INT AUTO_INCREMENT,
    first_name        VARCHAR(50)  NOT NULL,
    last_name         VARCHAR(50)  NOT NULL,
    address           VARCHAR(150) NOT NULL,
    phone             VARCHAR(15)  NOT NULL,
    email             VARCHAR(100) NOT NULL,
    registration_date DATE         NOT NULL DEFAULT (CURRENT_DATE),
    CONSTRAINT pk_customer PRIMARY KEY (customer_id),
    CONSTRAINT uq_customer_email UNIQUE (email)
);

CREATE TABLE employee (
    employee_id INT AUTO_INCREMENT,
    first_name  VARCHAR(50)  NOT NULL,
    last_name   VARCHAR(50)  NOT NULL,
    address     VARCHAR(150),
    phone       VARCHAR(15)  NOT NULL,
    area        VARCHAR(20)  NOT NULL,
    hire_date   DATE         NOT NULL,
    CONSTRAINT pk_employee PRIMARY KEY (employee_id),
    CONSTRAINT ck_employee_area CHECK (area IN ('kitchen', 'delivery', 'admin'))
);

CREATE TABLE product (
    product_id  INT AUTO_INCREMENT,
    name        VARCHAR(80)  NOT NULL,
    description VARCHAR(255),
    base_price  DECIMAL(8,2) NOT NULL,
    category    VARCHAR(30)  NOT NULL,
    available   BOOLEAN      NOT NULL DEFAULT TRUE,
    CONSTRAINT pk_product PRIMARY KEY (product_id),
    CONSTRAINT ck_product_base_price_positive CHECK (base_price > 0)
);

CREATE TABLE ingredient (
    ingredient_id   INT AUTO_INCREMENT,
    name            VARCHAR(60)   NOT NULL,
    unit_of_measure VARCHAR(10)   NOT NULL,
    current_stock   DECIMAL(10,2) NOT NULL DEFAULT 0,
    minimum_stock   DECIMAL(10,2) NOT NULL DEFAULT 0,
    CONSTRAINT pk_ingredient PRIMARY KEY (ingredient_id),
    CONSTRAINT uq_ingredient_name UNIQUE (name),
    CONSTRAINT ck_ingredient_stock_non_negative CHECK (current_stock >= 0 AND minimum_stock >= 0)
);

CREATE TABLE supplier (
    supplier_id INT AUTO_INCREMENT,
    first_name  VARCHAR(50)  NOT NULL,
    last_name   VARCHAR(50)  NOT NULL,
    company     VARCHAR(80)  NOT NULL,
    phone       VARCHAR(15)  NOT NULL,
    email       VARCHAR(100),
    CONSTRAINT pk_supplier PRIMARY KEY (supplier_id)
);

-- "orders" is plural because ORDER is a reserved word in SQL
CREATE TABLE orders (
    order_id         INT AUTO_INCREMENT,
    customer_id      INT           NOT NULL,
    employee_id      INT           NULL,
    order_datetime   DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    delivery_address VARCHAR(150)  NOT NULL,
    status           VARCHAR(20)   NOT NULL DEFAULT 'received',
    total            DECIMAL(10,2) NOT NULL DEFAULT 0,
    CONSTRAINT pk_orders PRIMARY KEY (order_id),
    CONSTRAINT fk_orders_customer FOREIGN KEY (customer_id) REFERENCES customer (customer_id),
    CONSTRAINT fk_orders_employee FOREIGN KEY (employee_id) REFERENCES employee (employee_id),
    CONSTRAINT ck_orders_status CHECK (status IN ('received', 'preparing', 'on_the_way', 'delivered', 'cancelled')),
    CONSTRAINT ck_orders_total_non_negative CHECK (total >= 0)
);

CREATE TABLE order_detail (
    order_detail_id INT AUTO_INCREMENT,
    order_id        INT           NOT NULL,
    product_id      INT           NOT NULL,
    quantity        INT           NOT NULL,
    unit_price      DECIMAL(8,2)  NOT NULL,
    subtotal        DECIMAL(10,2) NOT NULL,
    CONSTRAINT pk_order_detail PRIMARY KEY (order_detail_id),
    CONSTRAINT fk_order_detail_orders FOREIGN KEY (order_id) REFERENCES orders (order_id),
    CONSTRAINT fk_order_detail_product FOREIGN KEY (product_id) REFERENCES product (product_id),
    CONSTRAINT ck_order_detail_quantity_positive CHECK (quantity > 0)
);

CREATE TABLE product_ingredient (
    product_id        INT          NOT NULL,
    ingredient_id     INT          NOT NULL,
    quantity_required DECIMAL(8,2) NOT NULL,
    CONSTRAINT pk_product_ingredient PRIMARY KEY (product_id, ingredient_id),
    CONSTRAINT fk_product_ingredient_product FOREIGN KEY (product_id) REFERENCES product (product_id),
    CONSTRAINT fk_product_ingredient_ingredient FOREIGN KEY (ingredient_id) REFERENCES ingredient (ingredient_id),
    CONSTRAINT ck_product_ingredient_quantity_positive CHECK (quantity_required > 0)
);

CREATE TABLE supply (
    supply_id          INT AUTO_INCREMENT,
    supplier_id        INT          NOT NULL,
    ingredient_id      INT          NOT NULL,
    purchase_price     DECIMAL(8,2) NOT NULL,
    last_purchase_date DATE         NOT NULL,
    CONSTRAINT pk_supply PRIMARY KEY (supply_id),
    CONSTRAINT fk_supply_supplier FOREIGN KEY (supplier_id) REFERENCES supplier (supplier_id),
    CONSTRAINT fk_supply_ingredient FOREIGN KEY (ingredient_id) REFERENCES ingredient (ingredient_id),
    CONSTRAINT uq_supply_supplier_ingredient UNIQUE (supplier_id, ingredient_id),
    CONSTRAINT ck_supply_purchase_price_positive CHECK (purchase_price > 0)
);

CREATE INDEX idx_orders_customer_id ON orders (customer_id);
CREATE INDEX idx_orders_status ON orders (status);
