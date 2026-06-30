CREATE TABLE IF NOT EXISTS customers (
  id BIGSERIAL PRIMARY KEY,
  telegram TEXT UNIQUE NOT NULL,
  full_name TEXT NOT NULL,
  email TEXT,
  phone TEXT,
  city TEXT,
  preferred_tone TEXT NOT NULL DEFAULT '╤Б╨┐╨╛╨║╨╛╨╣╨╜╤Л╨╣',
  risk_flags TEXT NOT NULL DEFAULT '╨╜╨╡╤В',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS orders (
  id BIGSERIAL PRIMARY KEY,
  order_number TEXT UNIQUE NOT NULL,
  customer_id BIGINT NOT NULL REFERENCES customers(id),
  created_at TIMESTAMPTZ NOT NULL,
  status TEXT NOT NULL,
  delivery_city TEXT NOT NULL,
  delivery_method TEXT NOT NULL,
  tracking_number TEXT,
  expected_delivery_date DATE,
  delivered_at TIMESTAMPTZ,
  total_rub NUMERIC(12,2) NOT NULL,
  paid_status TEXT NOT NULL,
  payment_method TEXT NOT NULL,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS products (
  id BIGSERIAL PRIMARY KEY,
  sku TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  category TEXT NOT NULL,
  price_rub NUMERIC(12,2) NOT NULL,
  sensitive_skin_ok BOOLEAN NOT NULL DEFAULT false,
  active_ingredients TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS order_items (
  id BIGSERIAL PRIMARY KEY,
  order_id BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  product_id BIGINT NOT NULL REFERENCES products(id),
  quantity INTEGER NOT NULL CHECK (quantity > 0),
  unit_price_rub NUMERIC(12,2) NOT NULL,
  UNIQUE(order_id, product_id)
);

CREATE TABLE IF NOT EXISTS support_tickets (
  id BIGSERIAL PRIMARY KEY,
  ticket_number TEXT UNIQUE NOT NULL,
  customer_id BIGINT REFERENCES customers(id),
  order_id BIGINT REFERENCES orders(id),
  source TEXT NOT NULL DEFAULT 'telegram',
  category TEXT NOT NULL,
  priority TEXT NOT NULL,
  status TEXT NOT NULL,
  customer_message TEXT NOT NULL,
  assigned_to TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  resolved_at TIMESTAMPTZ,
  needs_human BOOLEAN NOT NULL DEFAULT false,
  internal_note TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS faq_cards (
  id BIGSERIAL PRIMARY KEY,
  topic TEXT UNIQUE NOT NULL,
  keywords TEXT NOT NULL,
  answer TEXT NOT NULL,
  clarify TEXT NOT NULL,
  handoff_rule TEXT NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_customers_telegram ON customers(telegram);
CREATE INDEX IF NOT EXISTS idx_orders_order_number ON orders(order_number);
CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON support_tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_needs_human ON support_tickets(needs_human);
CREATE INDEX IF NOT EXISTS idx_faq_topic ON faq_cards(topic);
