-- Agentic AI Online Pharmacy Platform - Database Schema
-- PostgreSQL 15+

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For fuzzy text search
CREATE EXTENSION IF NOT EXISTS "vector";   -- For pgvector (if using PostgreSQL for vectors)

-- ============================================
-- USERS & AUTHENTICATION
-- ============================================

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    date_of_birth DATE,
    role VARCHAR(20) NOT NULL DEFAULT 'customer' CHECK (role IN ('customer', 'pharmacist', 'admin', 'delivery')),
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    email_verified_at TIMESTAMP,
    phone_verified_at TIMESTAMP,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP  -- Soft delete for compliance
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_active ON users(is_active);

-- User addresses for delivery
CREATE TABLE user_addresses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    address_type VARCHAR(20) DEFAULT 'home' CHECK (address_type IN ('home', 'work', 'other')),
    street_address TEXT NOT NULL,
    apartment VARCHAR(50),
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    postal_code VARCHAR(20) NOT NULL,
    country VARCHAR(100) DEFAULT 'USA',
    is_default BOOLEAN DEFAULT FALSE,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_addresses_user ON user_addresses(user_id);
CREATE INDEX idx_addresses_default ON user_addresses(user_id, is_default);

-- User allergies and medical conditions
CREATE TABLE user_health_profile (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    allergies TEXT[],  -- Array of allergies
    medical_conditions TEXT[],
    current_medications TEXT[],
    emergency_contact_name VARCHAR(100),
    emergency_contact_phone VARCHAR(20),
    blood_type VARCHAR(5),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_health_profile_user ON user_health_profile(user_id);

-- ============================================
-- MEDICINE CATALOG
-- ============================================

CREATE TABLE categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    parent_id UUID REFERENCES categories(id),
    icon_url VARCHAR(500),
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_categories_parent ON categories(parent_id);
CREATE INDEX idx_categories_active ON categories(is_active);

CREATE TABLE medicines (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sku VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    generic_name VARCHAR(255),
    description TEXT,
    category_id UUID REFERENCES categories(id),
    manufacturer VARCHAR(255),
    
    -- Classification
    prescription_required BOOLEAN DEFAULT FALSE,
    controlled_substance BOOLEAN DEFAULT FALSE,
    controlled_schedule VARCHAR(10),  -- II, III, IV, V
    
    -- Pricing
    price DECIMAL(10, 2) NOT NULL,
    compare_at_price DECIMAL(10, 2),
    cost_price DECIMAL(10, 2),
    currency VARCHAR(3) DEFAULT 'USD',
    
    -- Physical attributes
    weight_grams DECIMAL(8, 2),
    dimensions_cm VARCHAR(50),  -- LxWxH
    
    -- Storage
    storage_conditions VARCHAR(100),
    temperature_requirements VARCHAR(50),
    
    -- Regulatory
    ndc_number VARCHAR(11),  -- National Drug Code
    upc_code VARCHAR(12),
    batch_number VARCHAR(50),
    expiry_date DATE,
    
    -- Media
    image_url VARCHAR(500),
    additional_images TEXT[],
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_featured BOOLEAN DEFAULT FALSE,
    requires_refrigeration BOOLEAN DEFAULT FALSE,
    
    -- SEO
    meta_title VARCHAR(255),
    meta_description TEXT,
    slug VARCHAR(255) UNIQUE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_medicines_sku ON medicines(sku);
CREATE INDEX idx_medicines_category ON medicines(category_id);
CREATE INDEX idx_medicines_name ON medicines USING gin(name gin_trgm_ops);
CREATE INDEX idx_medicines_generic ON medicines USING gin(generic_name gin_trgm_ops);
CREATE INDEX idx_medicines_prescription ON medicines(prescription_required);
CREATE INDEX idx_medicines_active ON medicines(is_active);
CREATE INDEX idx_medicines_price ON medicines(price);

-- Medicine details (ingredients, dosage, etc.)
CREATE TABLE medicine_details (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    medicine_id UUID UNIQUE NOT NULL REFERENCES medicines(id) ON DELETE CASCADE,
    active_ingredients JSONB,  -- [{"name": "", "strength": ""}]
    inactive_ingredients TEXT[],
    dosage_form VARCHAR(50),  -- tablet, capsule, syrup, etc.
    strength VARCHAR(100),
    pack_size VARCHAR(50),
    
    -- Usage
    indications TEXT,
    contraindications TEXT,
    warnings TEXT,
    precautions TEXT,
    
    -- Dosage
    adult_dosage TEXT,
    pediatric_dosage TEXT,
    geriatric_dosage TEXT,
    
    -- Side effects
    common_side_effects TEXT[],
    serious_side_effects TEXT[],
    
    -- Interactions
    drug_interactions TEXT[],
    food_interactions TEXT[],
    
    -- Special populations
    pregnancy_category VARCHAR(10),
    breastfeeding_notes TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_medicine_details_medicine ON medicine_details(medicine_id);

-- Drug interactions database
CREATE TABLE drug_interactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    medicine_id_1 UUID NOT NULL REFERENCES medicines(id),
    medicine_id_2 UUID NOT NULL REFERENCES medicines(id),
    interaction_type VARCHAR(50) NOT NULL CHECK (interaction_type IN ('minor', 'moderate', 'major', 'contraindicated')),
    description TEXT NOT NULL,
    mechanism TEXT,
    management TEXT,
    references TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_interactions_med1 ON drug_interactions(medicine_id_1);
CREATE INDEX idx_interactions_med2 ON drug_interactions(medicine_id_2);
CREATE INDEX idx_interactions_type ON drug_interactions(interaction_type);

-- ============================================
-- INVENTORY MANAGEMENT
-- ============================================

CREATE TABLE inventory (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    medicine_id UUID UNIQUE NOT NULL REFERENCES medicines(id),
    quantity_available INTEGER NOT NULL DEFAULT 0 CHECK (quantity_available >= 0),
    quantity_reserved INTEGER NOT NULL DEFAULT 0 CHECK (quantity_reserved >= 0),
    quantity_on_order INTEGER NOT NULL DEFAULT 0,
    reorder_level INTEGER DEFAULT 10,
    reorder_quantity INTEGER DEFAULT 50,
    warehouse_location VARCHAR(50),
    batch_number VARCHAR(50),
    expiry_date DATE,
    last_counted_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_inventory_medicine ON inventory(medicine_id);
CREATE INDEX idx_inventory_low ON inventory(quantity_available, reorder_level) WHERE quantity_available <= reorder_level;
CREATE INDEX idx_inventory_expiry ON inventory(expiry_date);

-- Inventory transactions (audit trail)
CREATE TABLE inventory_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    inventory_id UUID NOT NULL REFERENCES inventory(id),
    transaction_type VARCHAR(20) NOT NULL CHECK (transaction_type IN ('in', 'out', 'adjustment', 'return', 'expired')),
    quantity INTEGER NOT NULL,
    previous_quantity INTEGER NOT NULL,
    new_quantity INTEGER NOT NULL,
    reference_type VARCHAR(50),  -- order, prescription, manual
    reference_id UUID,
    notes TEXT,
    performed_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_inventory_tx_inventory ON inventory_transactions(inventory_id);
CREATE INDEX idx_inventory_tx_type ON inventory_transactions(transaction_type);
CREATE INDEX idx_inventory_tx_created ON inventory_transactions(created_at);

-- ============================================
-- PRESCRIPTIONS
-- ============================================

CREATE TABLE prescriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    
    -- Prescription info
    prescription_number VARCHAR(100),
    file_url VARCHAR(500),  -- S3 URL
    file_type VARCHAR(10) CHECK (file_type IN ('image', 'pdf')),
    
    -- Doctor info
    doctor_name VARCHAR(255),
    doctor_npi VARCHAR(10),
    doctor_license VARCHAR(50),
    doctor_phone VARCHAR(20),
    doctor_address TEXT,
    
    -- Patient info (as written on prescription)
    patient_name_on_rx VARCHAR(255),
    patient_dob_on_rx DATE,
    
    -- Dates
    issue_date DATE,
    expiration_date DATE,
    
    -- Validation
    validation_status VARCHAR(20) DEFAULT 'pending' CHECK (validation_status IN ('pending', 'valid', 'invalid', 'needs_review', 'expired')),
    validation_confidence DECIMAL(3, 2),
    validation_notes TEXT,
    validated_by UUID REFERENCES users(id),
    validated_at TIMESTAMP,
    
    -- OCR extracted data
    extracted_data JSONB,
    
    -- Status
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'used', 'expired', 'cancelled')),
    usage_count INTEGER DEFAULT 0,
    max_uses INTEGER DEFAULT 1,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_prescriptions_user ON prescriptions(user_id);
CREATE INDEX idx_prescriptions_status ON prescriptions(status);
CREATE INDEX idx_prescriptions_validation ON prescriptions(validation_status);
CREATE INDEX idx_prescriptions_expiry ON prescriptions(expiration_date);

-- Prescription items (medicines on prescription)
CREATE TABLE prescription_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prescription_id UUID NOT NULL REFERENCES prescriptions(id) ON DELETE CASCADE,
    medicine_id UUID REFERENCES medicines(id),
    medicine_name_on_rx VARCHAR(255),  -- As written on prescription
    dosage VARCHAR(100),
    quantity INTEGER,
    quantity_unit VARCHAR(20),
    frequency VARCHAR(100),
    duration VARCHAR(50),
    instructions TEXT,
    refills_allowed INTEGER DEFAULT 0,
    refills_remaining INTEGER DEFAULT 0,
    is_substitution_allowed BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_prescription_items_rx ON prescription_items(prescription_id);
CREATE INDEX idx_prescription_items_medicine ON prescription_items(medicine_id);

-- Pharmacist reviews
CREATE TABLE pharmacist_reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prescription_id UUID NOT NULL REFERENCES prescriptions(id),
    pharmacist_id UUID NOT NULL REFERENCES users(id),
    
    review_status VARCHAR(20) NOT NULL CHECK (review_status IN ('pending', 'approved', 'rejected', 'needs_info')),
    priority VARCHAR(10) DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
    
    -- Review details
    reviewed_at TIMESTAMP,
    notes TEXT,
    rejection_reason TEXT,
    
    -- Clinical checks
    allergy_checked BOOLEAN DEFAULT FALSE,
    interaction_checked BOOLEAN DEFAULT FALSE,
    contraindication_checked BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_reviews_prescription ON pharmacist_reviews(prescription_id);
CREATE INDEX idx_reviews_pharmacist ON pharmacist_reviews(pharmacist_id);
CREATE INDEX idx_reviews_status ON pharmacist_reviews(review_status);
CREATE INDEX idx_reviews_priority ON pharmacist_reviews(priority);

-- ============================================
-- ORDERS
-- ============================================

CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_number VARCHAR(50) UNIQUE NOT NULL,
    user_id UUID NOT NULL REFERENCES users(id),
    
    -- Address
    shipping_address_id UUID REFERENCES user_addresses(id),
    shipping_address_snapshot JSONB,  -- Snapshot at order time
    
    -- Prescription (if required)
    prescription_id UUID REFERENCES prescriptions(id),
    
    -- Financial
    subtotal DECIMAL(10, 2) NOT NULL,
    tax_amount DECIMAL(10, 2) NOT NULL DEFAULT 0,
    shipping_amount DECIMAL(10, 2) NOT NULL DEFAULT 0,
    discount_amount DECIMAL(10, 2) NOT NULL DEFAULT 0,
    total_amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    
    -- Coupon
    coupon_code VARCHAR(50),
    coupon_discount DECIMAL(10, 2),
    
    -- Status
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'processing', 'ready_for_pickup', 'shipped', 'delivered', 'cancelled', 'refunded')),
    payment_status VARCHAR(20) DEFAULT 'pending' CHECK (payment_status IN ('pending', 'authorized', 'captured', 'failed', 'refunded', 'partially_refunded')),
    
    -- Delivery
    shipping_method VARCHAR(50),
    tracking_number VARCHAR(100),
    carrier VARCHAR(50),
    estimated_delivery DATE,
    shipped_at TIMESTAMP,
    delivered_at TIMESTAMP,
    
    -- Notes
    customer_notes TEXT,
    internal_notes TEXT,
    
    -- Metadata
    ip_address INET,
    user_agent TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_orders_user ON orders(user_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_payment ON orders(payment_status);
CREATE INDEX idx_orders_number ON orders(order_number);
CREATE INDEX idx_orders_created ON orders(created_at);

-- Order items
CREATE TABLE order_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    medicine_id UUID REFERENCES medicines(id),
    
    -- Snapshot
    medicine_name VARCHAR(255) NOT NULL,
    medicine_sku VARCHAR(50) NOT NULL,
    
    -- Pricing
    unit_price DECIMAL(10, 2) NOT NULL,
    quantity INTEGER NOT NULL,
    total_price DECIMAL(10, 2) NOT NULL,
    
    -- Prescription item reference
    prescription_item_id UUID REFERENCES prescription_items(id),
    
    -- Fulfillment
    fulfilled_quantity INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_order_items_medicine ON order_items(medicine_id);

-- ============================================
-- PAYMENTS
-- ============================================

CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID NOT NULL REFERENCES orders(id),
    user_id UUID NOT NULL REFERENCES users(id),
    
    -- Payment details
    payment_method VARCHAR(20) NOT NULL CHECK (payment_method IN ('card', 'insurance', 'paypal', 'apple_pay', 'google_pay')),
    payment_provider VARCHAR(50),  -- stripe, etc.
    provider_payment_id VARCHAR(255),
    
    -- Amount
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    
    -- Card info (masked)
    card_last_four VARCHAR(4),
    card_brand VARCHAR(20),
    card_expiry_month VARCHAR(2),
    card_expiry_year VARCHAR(4),
    
    -- Status
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'authorized', 'captured', 'failed', 'refunded', 'partially_refunded', 'disputed')),
    
    -- Timestamps
    authorized_at TIMESTAMP,
    captured_at TIMESTAMP,
    refunded_at TIMESTAMP,
    
    -- Refund info
    refunded_amount DECIMAL(10, 2),
    refund_reason TEXT,
    
    -- Fraud check
    fraud_score DECIMAL(3, 2),
    fraud_flags TEXT[],
    
    -- Response
    provider_response JSONB,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_payments_order ON payments(order_id);
CREATE INDEX idx_payments_user ON payments(user_id);
CREATE INDEX idx_payments_status ON payments(status);
CREATE INDEX idx_payments_provider ON payments(provider_payment_id);

-- ============================================
-- CONVERSATIONS & CHAT
-- ============================================

CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    session_id VARCHAR(100),
    
    -- Conversation metadata
    title VARCHAR(255),
    conversation_type VARCHAR(20) DEFAULT 'general' CHECK (conversation_type IN ('general', 'prescription', 'order', 'support')),
    
    -- Status
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'closed', 'escalated')),
    
    -- Escalation
    escalated_to UUID REFERENCES users(id),
    escalated_at TIMESTAMP,
    escalation_reason TEXT,
    
    -- Satisfaction
    satisfaction_rating INTEGER CHECK (satisfaction_rating BETWEEN 1 AND 5),
    satisfaction_feedback TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP
);

CREATE INDEX idx_conversations_user ON conversations(user_id);
CREATE INDEX idx_conversations_status ON conversations(status);
CREATE INDEX idx_conversations_created ON conversations(created_at);

-- Chat messages
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    
    -- Message info
    message_type VARCHAR(20) NOT NULL CHECK (message_type IN ('user', 'agent', 'system', 'pharmacist')),
    agent_type VARCHAR(50),  -- which agent sent this
    
    -- Content
    content TEXT NOT NULL,
    content_html TEXT,  -- Rendered HTML
    
    -- Structured data (for agent responses)
    structured_data JSONB,
    
    -- Media
    attachments JSONB,  -- [{"type": "image", "url": ""}]
    
    -- Metadata
    tokens_used INTEGER,
    latency_ms INTEGER,
    
    -- Feedback
    helpful BOOLEAN,
    feedback_text TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_chat_messages_conversation ON chat_messages(conversation_id);
CREATE INDEX idx_chat_messages_created ON chat_messages(created_at);
CREATE INDEX idx_chat_messages_agent ON chat_messages(agent_type);

-- ============================================
-- AGENT LOGS & AUDIT
-- ============================================

CREATE TABLE agent_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Agent info
    agent_type VARCHAR(50) NOT NULL,
    agent_instance_id VARCHAR(100),
    
    -- Request/Response
    conversation_id UUID REFERENCES conversations(id),
    user_id UUID REFERENCES users(id),
    
    input_payload JSONB,
    output_payload JSONB,
    
    -- Performance
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    latency_ms INTEGER,
    
    -- Status
    status VARCHAR(20) NOT NULL CHECK (status IN ('success', 'error', 'timeout', 'retry')),
    error_message TEXT,
    error_stack TEXT,
    
    -- LLM specific
    model_name VARCHAR(50),
    tokens_input INTEGER,
    tokens_output INTEGER,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_agent_logs_agent ON agent_logs(agent_type);
CREATE INDEX idx_agent_logs_conversation ON agent_logs(conversation_id);
CREATE INDEX idx_agent_logs_user ON agent_logs(user_id);
CREATE INDEX idx_agent_logs_status ON agent_logs(status);
CREATE INDEX idx_agent_logs_created ON agent_logs(created_at);

-- Audit log for compliance
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Who
    user_id UUID REFERENCES users(id),
    user_role VARCHAR(20),
    session_id VARCHAR(100),
    ip_address INET,
    user_agent TEXT,
    
    -- What
    action VARCHAR(100) NOT NULL,  -- prescription_viewed, order_created, etc.
    resource_type VARCHAR(50),  -- prescription, order, user, etc.
    resource_id UUID,
    
    -- Details
    before_state JSONB,
    after_state JSONB,
    changes_summary TEXT,
    
    -- Compliance
    pii_involved BOOLEAN DEFAULT FALSE,
    data_access_reason TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at);

-- ============================================
-- NOTIFICATIONS & REMINDERS
-- ============================================

CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Content
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    notification_type VARCHAR(50) NOT NULL,  -- order_update, refill_reminder, etc.
    
    -- Delivery
    channel VARCHAR(20) CHECK (channel IN ('push', 'email', 'sms', 'in_app')),
    
    -- Status
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP,
    
    -- Action
    action_url VARCHAR(500),
    action_text VARCHAR(100),
    
    -- Metadata
    related_type VARCHAR(50),  -- order, prescription, etc.
    related_id UUID,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_notifications_read ON notifications(user_id, is_read);
CREATE INDEX idx_notifications_type ON notifications(notification_type);

-- Refill reminders
CREATE TABLE refill_reminders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    medicine_id UUID NOT NULL REFERENCES medicines(id),
    prescription_id UUID REFERENCES prescriptions(id),
    
    -- Reminder settings
    reminder_date DATE NOT NULL,
    days_supply INTEGER NOT NULL,
    days_before INTEGER DEFAULT 7,
    
    -- Status
    is_sent BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMP,
    is_acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMP,
    
    -- Order created from reminder
    order_id UUID REFERENCES orders(id),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_refill_reminders_user ON refill_reminders(user_id);
CREATE INDEX idx_refill_reminders_date ON refill_reminders(reminder_date);
CREATE INDEX idx_refill_reminders_sent ON refill_reminders(is_sent);

-- ============================================
-- VECTOR STORE (if using pgvector)
-- ============================================

CREATE TABLE medicine_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    medicine_id UUID UNIQUE NOT NULL REFERENCES medicines(id),
    embedding VECTOR(1536),  -- OpenAI embedding dimension
    content_hash VARCHAR(64),  -- To detect changes
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_medicine_embeddings ON medicine_embeddings USING ivfflat (embedding vector_cosine_ops);

-- Conversation embeddings for semantic search
CREATE TABLE conversation_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    message_id UUID UNIQUE NOT NULL REFERENCES chat_messages(id),
    embedding VECTOR(1536),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_conversation_embeddings ON conversation_embeddings USING ivfflat (embedding vector_cosine_ops);

-- ============================================
-- CONFIGURATION & SETTINGS
-- ============================================

CREATE TABLE system_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key VARCHAR(100) UNIQUE NOT NULL,
    value JSONB NOT NULL,
    description TEXT,
    is_encrypted BOOLEAN DEFAULT FALSE,
    updated_by UUID REFERENCES users(id),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_settings_key ON system_settings(key);

-- Agent configuration
CREATE TABLE agent_configurations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_type VARCHAR(50) UNIQUE NOT NULL,
    
    -- LLM settings
    model_name VARCHAR(50),
    temperature DECIMAL(3, 2) DEFAULT 0.7,
    max_tokens INTEGER,
    top_p DECIMAL(3, 2) DEFAULT 1.0,
    
    -- Behavior
    system_prompt TEXT,
    tools_enabled TEXT[],
    
    -- Limits
    rate_limit_per_minute INTEGER DEFAULT 60,
    max_conversation_length INTEGER DEFAULT 50,
    
    -- Features
    features_enabled JSONB,
    
    updated_by UUID REFERENCES users(id),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- TRIGGERS FOR UPDATED_AT
-- ============================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply to all tables with updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_addresses_updated_at BEFORE UPDATE ON user_addresses FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_health_profile_updated_at BEFORE UPDATE ON user_health_profile FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_categories_updated_at BEFORE UPDATE ON categories FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_medicines_updated_at BEFORE UPDATE ON medicines FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_medicine_details_updated_at BEFORE UPDATE ON medicine_details FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_inventory_updated_at BEFORE UPDATE ON inventory FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_prescriptions_updated_at BEFORE UPDATE ON prescriptions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_orders_updated_at BEFORE UPDATE ON orders FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_payments_updated_at BEFORE UPDATE ON payments FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_conversations_updated_at BEFORE UPDATE ON conversations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_chat_messages_updated_at BEFORE UPDATE ON chat_messages FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_notifications_updated_at BEFORE UPDATE ON notifications FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- SEED DATA
-- ============================================

-- Default categories
INSERT INTO categories (name, description, display_order) VALUES
('Pain Relief', 'Medicines for pain management', 1),
('Cold & Flu', 'Remedies for cold and flu symptoms', 2),
('Allergy', 'Antihistamines and allergy relief', 3),
('Digestive Health', 'Medicines for digestive issues', 4),
('Vitamins & Supplements', 'Daily vitamins and health supplements', 5),
('First Aid', 'First aid supplies and treatments', 6),
('Prescription Medications', 'Prescription-only medicines', 7),
('Diabetes Care', 'Diabetes management products', 8),
('Heart Health', 'Cardiovascular health medicines', 9),
('Skin Care', 'Dermatological treatments', 10);

-- Default admin user (password: admin123 - change in production!)
-- Hash generated with bcrypt
INSERT INTO users (email, password_hash, first_name, last_name, role, is_verified, email_verified_at) VALUES
('admin@pharmacy.ai', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VTtYA.qGZvKG6G', 'System', 'Admin', 'admin', TRUE, CURRENT_TIMESTAMP);

-- Default system settings
INSERT INTO system_settings (key, value, description) VALUES
('site_name', '"PharmacyAI"', 'Website name'),
('site_description', '"Your AI-Powered Pharmacy"', 'Website description'),
('currency', '"USD"', 'Default currency'),
('tax_rate', '0.08', 'Default tax rate'),
('free_shipping_threshold', '35.00', 'Free shipping minimum order value'),
('shipping_flat_rate', '5.99', 'Flat rate shipping cost'),
('prescription_required_message', '"This medication requires a valid prescription. Please upload your prescription to proceed."', 'Message shown for prescription medicines'),
('chat_welcome_message', '"Hello! I\'m your AI pharmacist assistant. How can I help you today?"', 'Welcome message for chat'),
('refill_reminder_days', '7', 'Days before refill to send reminder'),
('max_prescription_upload_size_mb', '10', 'Maximum prescription file size');
