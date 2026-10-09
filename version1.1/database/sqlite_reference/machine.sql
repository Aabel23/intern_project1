-- FlexMix: schema SQLite tham chiếu cho DB nội bộ máy, sau khi bỏ admin_gui.
-- machine.sql là nguồn tạo file SQLite machine.db trong thư mục này.
-- Chỉ tạo database rỗng; runtime version1.1 vẫn dùng MySQL, chưa đổi driver.
-- Kiểm: python3 database/sqlite_reference/check_machine_db.py
--
-- Kết quả dò nguồn máy trước khi chuyển vào version1.1 (139 file nguồn:
-- Python, JS, HTML, SQL, SH, JSON):
--   store_gui/sync_menu.py: drink, category, drink_category_mapping,
--                           store_setting, recipe, ingredient, order_ticket.
--   database/export_data.py -> order/qr_to_recipe.py:
--                           drink, glass, drink_type, recipe, recipe_action,
--                           ingredient; giữ đủ thông tin cho bartender_gui.
--   database/order_ticket.py -> store_gui/serve.py, order/run_flow.py:
--                           phát vé, claim nguyên tử, hết hạn, kết thúc, retry.
--   database/inventory_service.py -> order/process_runner.py:
--                           trừ tồn theo lượng đã dùng, không theo recipe gốc.
--   database/error_log.py -> order/run_flow.py, process_runner.py,
--                           pump_control/prime_all.py: lưu lỗi để không mất.
--   database/admin_functions/ingredients.py: max_gram cần cho lệnh nạp đầy
--                           khi chuyển quản trị lên server; không bỏ cột này.
--   database/migrate.py: schema_migration; chỉ giữ sổ phiên bản schema.
--
-- Bỏ: admin_user, role_permission; glass.capacity_ml, glass.sort_order;
--     drink_type.sort_order; category.description; store_setting.updated_at.
-- Không chép: ALTER/migration cũ, bảng legacy, seed món/công thức/tồn kho mẫu.
-- Không thêm bảng menu/nhiều máy/tài khoản/media/audit/lịch sử tồn kho.
-- Agent FM1 chưa có khi lập schema này: agent_state/agent_ledger chưa thuộc
-- baseline này; khi triển khai agent, cần thêm claim bền trước lệnh có tác dụng.
--
-- Giữ in_stock và threshold_gram vì runtime hiện tại đọc/ghi các cột này.
-- in_stock của nguyên liệu là cột sinh từ amount và threshold_gram.
-- Triggers giữ trạng thái món nhất quán, không tạo stock ledger.
-- max_gram NULL = chưa khai báo dung tích; không seed lượng tồn giả.
-- Tên/giá trên vé là lúc bán; vé và lỗi không FK đến drink để giữ lịch sử.
-- order_mode, display_mode, calibration, media và current_recipe vẫn ở file.
--
-- Trước khi bỏ admin_gui khỏi runtime:
--   store_gui/serve.py: bỏ import/dispatch/upload admin_api, tách GET order-mode.
--   deploy/install.sh: bỏ tạo tài khoản admin và import admin_gui.auth.
--   configuration/served_paths.py: bỏ đường dẫn admin_gui.
-- Không chạy bootstrap/migration baseline cũ với schema này: chúng tạo lại
-- bảng quản trị và seed các cột đã bỏ. Cần đổi bootstrap khi tích hợp runtime.
-- File này không tự sửa các caller đó và không di chuyển dữ liệu đang chạy.

PRAGMA foreign_keys = ON;

CREATE TABLE schema_migration (
    version CHAR(4) NOT NULL PRIMARY KEY,
    name VARCHAR(80) NOT NULL,
    checksum CHAR(64) NOT NULL,
    applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Thong tin ly/cach pha van duoc bartender_gui hien thi qua current_recipe.
CREATE TABLE glass (
    glass_id INTEGER PRIMARY KEY AUTOINCREMENT,
    glass_name VARCHAR(60) NOT NULL UNIQUE,
    art VARCHAR(40) NOT NULL
);

CREATE TABLE drink_type (
    drink_type_id INTEGER PRIMARY KEY AUTOINCREMENT,
    type_name VARCHAR(60) NOT NULL,
    art VARCHAR(40) NOT NULL UNIQUE,
    method VARCHAR(60) NULL,
    detail VARCHAR(200) NULL
);

-- May chi giu menu da nhan; khong can menu_id hay machine_id tren tung mon.
-- available = duoc ban; in_stock = pha duoc; khong gop hai y nghia nay.
-- deleted_at van can vi luong quet loai mon da xoa mem.
CREATE TABLE drink (
    drink_id INTEGER PRIMARY KEY AUTOINCREMENT,
    drink_name VARCHAR(100) NOT NULL UNIQUE,
    image VARCHAR(255) NULL,
    price DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    available BOOLEAN NOT NULL DEFAULT TRUE,
    in_stock BOOLEAN NOT NULL DEFAULT FALSE,
    featured BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at DATETIME NULL,
    glass_id INT NULL,
    drink_type_id INT NULL,
    garnish VARCHAR(120) NULL,
    CONSTRAINT ck_drink_price CHECK (price >= 0),
    CONSTRAINT fk_drink_glass FOREIGN KEY (glass_id)
        REFERENCES glass (glass_id) ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_drink_drink_type FOREIGN KEY (drink_type_id)
        REFERENCES drink_type (drink_type_id) ON DELETE SET NULL ON UPDATE CASCADE
);

CREATE TABLE category (
    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_name VARCHAR(255) NOT NULL UNIQUE
);

CREATE TABLE drink_category_mapping (
    drink_id INT NOT NULL,
    category_id INT NOT NULL,
    PRIMARY KEY (drink_id, category_id),
    CONSTRAINT fk_drink_category_drink FOREIGN KEY (drink_id)
        REFERENCES drink (drink_id) ON DELETE CASCADE,
    CONSTRAINT fk_drink_category_category FOREIGN KEY (category_id)
        REFERENCES category (category_id) ON DELETE CASCADE
);

-- sync_menu doc bang nay cho featured/bestseller/layout: khong chi admin doc.
-- Bang rong dung defaults san co trong sync_menu; khong can seed cau hinh.
CREATE TABLE store_setting (
    setting_key VARCHAR(64) NOT NULL PRIMARY KEY,
    setting_value VARCHAR(255) NOT NULL
);

-- GPIO va ton kho thuoc may; khong doi id nguyen lieu khi doi menu.
CREATE TABLE ingredient (
    ingredient_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ingredient_name VARCHAR(100) NOT NULL UNIQUE,
    type VARCHAR(16) NOT NULL DEFAULT 'PUMP',
    data_type VARCHAR(16) NOT NULL DEFAULT 'weight',
    amount DECIMAL(10,2) NOT NULL DEFAULT 0,
    threshold_gram DECIMAL(10,2) NOT NULL DEFAULT 0,
    max_gram DECIMAL(10,2) NULL,
    gpio VARCHAR(8) NULL,
    in_stock BOOLEAN GENERATED ALWAYS AS (amount >= threshold_gram) STORED,
    CONSTRAINT uq_ingredient_type_gpio UNIQUE (type, gpio),
    CONSTRAINT ck_ingredient_amount CHECK (amount >= 0),
    CONSTRAINT ck_ingredient_threshold CHECK (threshold_gram >= 0),
    CONSTRAINT ck_ingredient_max_gram CHECK (max_gram IS NULL OR max_gram > 0),
    CONSTRAINT ck_ingredient_gpio
        CHECK (gpio IS NULL OR (length(gpio) BETWEEN 2 AND 8 AND substr(gpio,1,1) IN ('G','P')
            AND substr(gpio,2) NOT GLOB '*[^0-9]*')),
    CONSTRAINT ck_ingredient_type CHECK (type IN ('PUMP', 'MANUAL')),
    CONSTRAINT ck_ingredient_data_type
        CHECK (data_type IN ('boolean', 'percentage', 'weight'))
);

CREATE TABLE recipe (
    drink_id INT NOT NULL,
    ingredient_id INT NOT NULL,
    step_no INT NOT NULL,
    target_gram DECIMAL(10,2) NOT NULL,
    PRIMARY KEY (drink_id, step_no, ingredient_id),
    CONSTRAINT ck_recipe_step CHECK (step_no > 0),
    CONSTRAINT ck_recipe_gram CHECK (target_gram > 0),
    CONSTRAINT fk_recipe_drink FOREIGN KEY (drink_id)
        REFERENCES drink (drink_id) ON DELETE CASCADE,
    CONSTRAINT fk_recipe_ingredient FOREIGN KEY (ingredient_id)
        REFERENCES ingredient (ingredient_id) ON DELETE RESTRICT
);

CREATE TABLE recipe_action (
    drink_id INT NOT NULL,
    step_no INT NOT NULL,
    media_src VARCHAR(255) NOT NULL,
    title_vi VARCHAR(120) NOT NULL,
    title_en VARCHAR(120) NOT NULL DEFAULT '',
    detail_vi VARCHAR(400) NOT NULL DEFAULT '',
    detail_en VARCHAR(400) NOT NULL DEFAULT '',
    confirm_vi VARCHAR(40) NOT NULL DEFAULT '',
    confirm_en VARCHAR(40) NOT NULL DEFAULT '',
    cup_returns TINYINT(1) NOT NULL DEFAULT 1,
    PRIMARY KEY (drink_id, step_no),
    CONSTRAINT ck_recipe_action_step CHECK (step_no > 0),
    CONSTRAINT fk_recipe_action_drink FOREIGN KEY (drink_id)
        REFERENCES drink (drink_id) ON DELETE CASCADE
);

-- payload can cho in lai; hash la khoa claim, serial chi la so ve noi bo.
-- Gia/ten cho phep NULL de nhan lich su cu chua ghi duoc cac gia tri nay.
CREATE TABLE order_ticket (
    serial INTEGER PRIMARY KEY AUTOINCREMENT,
    drink_id INT NOT NULL,
    price DECIMAL(10,2) NULL,
    drink_name VARCHAR(100) NULL,
    payload VARCHAR(255) NOT NULL,
    payload_hash CHAR(64) NOT NULL,
    note VARCHAR(200) NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'unused',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    scanned_at DATETIME NULL,
    completed_at DATETIME NULL,
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%f','now')),
    CONSTRAINT uq_order_ticket_payload_hash UNIQUE (payload_hash),
    CONSTRAINT ck_order_ticket_price CHECK (price IS NULL OR price >= 0),
    CONSTRAINT ck_order_ticket_status
        CHECK (status IN ('unused', 'in_progress', 'used', 'expired', 'noqr_err'))
);

-- Moi loi la mot dong ben vung; tag [Ve #serial] van nam trong message.
CREATE TABLE error_log (
    error_id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%f','now')),
    severity VARCHAR(16) NOT NULL DEFAULT 'error',
    drink_id INT NULL,
    drink_name VARCHAR(100) NULL,
    step_label VARCHAR(16) NULL,
    step_type VARCHAR(16) NULL,
    message TEXT NOT NULL,
    CONSTRAINT ck_error_log_severity CHECK (severity IN ('info', 'warning', 'error'))
);


CREATE INDEX idx_order_ticket_status ON order_ticket (status, created_at);
CREATE INDEX idx_order_ticket_completed ON order_ticket (status, completed_at);
CREATE INDEX idx_order_ticket_updated ON order_ticket (updated_at, serial);
CREATE INDEX idx_error_log_time ON error_log (created_at);

-- Đồng bộ trạng thái món khi tồn hoặc công thức thay đổi.
CREATE TRIGGER trg_ingredient_after_update
AFTER UPDATE OF amount, threshold_gram ON ingredient
FOR EACH ROW BEGIN
    UPDATE drink
    SET in_stock = (
        SELECT CASE WHEN COUNT(*) > 0 AND MIN(ing.in_stock) = 1 THEN 1 ELSE 0 END
        FROM recipe AS rec
        JOIN ingredient AS ing ON ing.ingredient_id = rec.ingredient_id
        WHERE rec.drink_id = drink.drink_id
    )
    WHERE drink_id IN (SELECT drink_id FROM recipe WHERE ingredient_id=NEW.ingredient_id);
END;

CREATE TRIGGER trg_recipe_after_insert
AFTER INSERT ON recipe
FOR EACH ROW BEGIN
    UPDATE drink
    SET in_stock = (
        SELECT CASE WHEN COUNT(*) > 0 AND MIN(ing.in_stock) = 1 THEN 1 ELSE 0 END
        FROM recipe AS rec
        JOIN ingredient AS ing ON ing.ingredient_id = rec.ingredient_id
        WHERE rec.drink_id = drink.drink_id
    )
    WHERE drink_id=NEW.drink_id;
END;

CREATE TRIGGER trg_recipe_after_update
AFTER UPDATE ON recipe
FOR EACH ROW BEGIN
    UPDATE drink
    SET in_stock = (
        SELECT CASE WHEN COUNT(*) > 0 AND MIN(ing.in_stock) = 1 THEN 1 ELSE 0 END
        FROM recipe AS rec
        JOIN ingredient AS ing ON ing.ingredient_id = rec.ingredient_id
        WHERE rec.drink_id = drink.drink_id
    )
    WHERE drink_id IN (OLD.drink_id,NEW.drink_id);
END;

CREATE TRIGGER trg_recipe_after_delete
AFTER DELETE ON recipe
FOR EACH ROW BEGIN
    UPDATE drink
    SET in_stock = (
        SELECT CASE WHEN COUNT(*) > 0 AND MIN(ing.in_stock) = 1 THEN 1 ELSE 0 END
        FROM recipe AS rec
        JOIN ingredient AS ing ON ing.ingredient_id = rec.ingredient_id
        WHERE rec.drink_id = drink.drink_id
    )
    WHERE drink_id=OLD.drink_id;
END;

-- Không tự kích hoạt lại: lần UPDATE bên trong chỉ ghi updated_at.
CREATE TRIGGER trg_order_ticket_updated
AFTER UPDATE OF drink_id, price, drink_name, payload, payload_hash, note,
                status, created_at, scanned_at, completed_at ON order_ticket
FOR EACH ROW BEGIN
    UPDATE order_ticket
    SET updated_at = strftime('%Y-%m-%d %H:%M:%f','now')
    WHERE serial = NEW.serial;
END;
