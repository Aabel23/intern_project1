-- ============================================================
-- FLEXMIX DEFAULT DATA
-- Chạy sau schema.sql (xem database/schema/apply.py). Chạy lặp lại được:
-- INSERT ... ON DUPLICATE KEY UPDATE, giữ nguyên tồn kho hiện tại.
-- ============================================================

-- ------------------------------------------------------------
-- 1. DEFAULT INGREDIENT DATA
-- Khi update, không ghi đè amount đang vận hành.
-- ------------------------------------------------------------

-- Free unique names before assigning the new physical pump layout.
DROP TEMPORARY TABLE IF EXISTS ingredient_inventory_snapshot;

CREATE TEMPORARY TABLE ingredient_inventory_snapshot AS
SELECT
    ingredient_name,
    amount
FROM ingredient;

UPDATE ingredient
SET ingredient_name = CONCAT('__ingredient_', ingredient_id)
WHERE ingredient_id BETWEEN 1 AND 10;

INSERT INTO ingredient (
    ingredient_id,
    ingredient_name,
    type,
    data_type,
    amount,
    gpio
)
VALUES
    -- gpio is a SLOT, not a bare number: 'G26' is BCM pin 26 driving a
    -- pump, 'P01' is position 1 on the manual panel. These were plain
    -- integers until the slot migration, and ON DUPLICATE KEY UPDATE
    -- below writes gpio on every re-run -- so a bare 26 here did not
    -- merely look stale, it overwrote 'G26' with a value
    -- ck_ingredient_gpio refuses, and every re-run of this file stopped
    -- right here. See gpio_slot() in database/core/helpers.py.
    (1,  'Water',            'PUMP',   'weight',      7825, 'G26'),
    (2,  'Tea',              'PUMP',   'weight',      4360, 'G15'),
    (3,  'Coffee',           'PUMP',   'weight',      1870, 'G21'),
    (4,  'Peach Syrup',      'PUMP',   'weight',      2415, 'G20'),
    (5,  'Strawberry Syrup', 'PUMP',   'weight',      2130, 'G16'),
    (6,  'Soda Water',       'PUMP',   'weight',      6140, 'G12'),
    -- MANUAL gpio is the panel position, not a Raspberry Pi pin.
    -- Panel 8 and panel 13 are not wired, so nothing is placed there.
    (7,  'Sugar',            'PUMP',   'percentage',  3580, 'G13'),
    (8,  'Milk',             'MANUAL', 'boolean',     2945, 'P01'),
    (9,  'Cream',            'MANUAL', 'boolean',     1260, 'P02'),
    (10, 'Chocolate',        'MANUAL', 'boolean',     1685, 'P03'),
    (11, 'Strawberry',       'MANUAL', 'boolean',     1000, 'P04'),
    (12, 'Ice',              'MANUAL', 'boolean',     5000, 'P05'),
    (13, 'Pearls',           'MANUAL', 'boolean',     1500, 'P06')
ON DUPLICATE KEY UPDATE
    ingredient_name = VALUES(ingredient_name),
    type = VALUES(type),
    data_type = VALUES(data_type),
    gpio = VALUES(gpio);

-- Preserve stock by ingredient name while ingredients move to new IDs.
UPDATE ingredient AS target
JOIN ingredient_inventory_snapshot AS snapshot
    ON snapshot.ingredient_name = target.ingredient_name
SET target.amount = snapshot.amount;

DROP TEMPORARY TABLE ingredient_inventory_snapshot;

-- ------------------------------------------------------------
-- 3b. DEFAULT GLASS DATA
-- Glass IDs are fixed because drink.glass_id references them, and because
-- `art` is the filename the bartender screen looks for -- changing an id
-- would silently repoint every drink that used it.
-- ------------------------------------------------------------

INSERT INTO glass (
    glass_id,
    glass_name,
    art,
    capacity_ml,
    sort_order
)
VALUES
    (3001, 'Ly cao',        'highball',  350, 10),
    (3002, 'Ly lùn',        'rocks',     300, 20),
    (3003, 'Ly hurricane',  'hurricane', 440, 30),
    (3004, 'Ly martini',    'martini',   210, 40),
    (3005, 'Ly coupe',      'coupe',     240, 50),
    (3006, 'Ca đồng',       'mug',       450, 60)
ON DUPLICATE KEY UPDATE
    glass_name = VALUES(glass_name),
    art = VALUES(art),
    capacity_ml = VALUES(capacity_ml),
    sort_order = VALUES(sort_order);

-- ------------------------------------------------------------
-- 3c. DEFAULT DRINK TYPE DATA
-- Fixed ids for the same reason as glass: drink.drink_type_id references
-- them, and `art` is the filename the bartender screen looks for.
--
-- Six rows because six is what a shop actually serves. Anything past this
-- is a new row here, not a code change: nothing in the GUI names an ice
-- kind, it draws whatever `art` it is given and falls back to a generic
-- ice cube for one it has no drawing for.
-- ------------------------------------------------------------

INSERT INTO drink_type (
    drink_type_id,
    type_name,
    art,
    method,
    detail,
    sort_order
)
VALUES
    (5001, 'Đá viên', 'cube',
     'Dựng thẳng trong ly',
     'Topping xuống đáy, đá đầy 3/4 ly, rồi máy rót lên trên.',
     10),

    (5002, 'Đá nugget', 'nugget',
     'Dựng thẳng trong ly',
     'Đá nugget đầy ly — mềm, tan nhanh, nên rót ngay khi vừa lấy đá.',
     20),

    (5003, 'Đá bào', 'crushed',
     'Rót lên đá bào',
     'Đá bào vun cao trên miệng ly, rót chậm để đá không sụp.',
     30),

    (5004, 'Xay đá', 'blend',
     'Xay với đá',
     'Máy rót vào cối, thêm đá rồi xay đến khi mịn, đổ ra ly phục vụ.',
     40),

    (5005, 'Không đá', 'none',
     'Rót thẳng, không đá',
     'Không cho đá. Ly nên được làm lạnh trước nếu có.',
     50),

    (5006, 'Đồ uống nóng', 'hot',
     'Phục vụ nóng',
     'Tráng ly bằng nước nóng trước khi rót để giữ nhiệt.',
     60)
ON DUPLICATE KEY UPDATE
    type_name = VALUES(type_name),
    art = VALUES(art),
    method = VALUES(method),
    -- detail is deliberately absent from this list. It is the one column
    -- here with an editor behind it -- the recipe editor writes it
    -- -- and re-running the seed must not throw away what somebody
    -- typed there. The rest are structural and have no editor yet.
    sort_order = VALUES(sort_order);

-- ------------------------------------------------------------
-- 2. DEFAULT DRINK DATA
-- ------------------------------------------------------------

-- glass_id, drink_type_id and garnish are seeded here so a FRESH install
-- shows the prep card fully filled in. They are deliberately absent from
-- the ON DUPLICATE KEY UPDATE list below: on an existing database these
-- are somebody's choices, and re-running the seed must never reset
-- them the way it refreshes a name or an image.
INSERT INTO drink (
    drink_id,
    drink_name,
    image,
    in_stock,
    glass_id,
    drink_type_id,
    garnish
)
VALUES
    (1001, 'Peach Tea',       'recipe/image/Peach Tea.webp',       TRUE,
     3001, 5001, 'Ống hút to, lát đào'),
    (1002, 'Milk Tea',        'recipe/image/Milk Tea.webp',        TRUE,
     3001, 5001, 'Ống hút to, nắp dập'),
    (1003, 'Milk Coffee',     'recipe/image/Milk Coffee.webp',     TRUE,
     3002, 5001, 'Ống hút nhỏ'),
    (1004, 'Strawberry Soda', 'recipe/image/Strawberry Soda.webp', TRUE,
     3003, 5003, 'Lát chanh, lá bạc hà'),
    (1005, 'Chocolate Milk',  'recipe/image/Chocolate Milk.webp',  TRUE,
     3001, 5004, 'Kem tươi, bột cacao')
ON DUPLICATE KEY UPDATE
    drink_name = VALUES(drink_name),
    image = VALUES(image);

-- ------------------------------------------------------------
-- 3. DEFAULT CATEGORY DATA
-- Category IDs are fixed because drink_category_mapping references them.
-- ------------------------------------------------------------

INSERT INTO category (
    category_id,
    category_name,
    description
)
VALUES
    (4001, 'Summer',     'Đồ uống giải nhiệt mùa hè'),
    (4002, 'Soda',       'Các loại đồ uống có ga'),
    (4003, 'Tea',        'Các loại trà thanh mát'),
    (4004, 'Coffee',     'Cà phê các loại'),
    (4005, 'Bestseller', 'Danh sách đồ uống bán chạy nhất')
ON DUPLICATE KEY UPDATE
    category_name = VALUES(category_name),
    description = VALUES(description);

-- Floors for the id ranges.
--
-- Seeding explicit ids already pushes AUTO_INCREMENT past them, so on a
-- normal install these are redundant. They are here for the install where
-- they are not: a table created but never seeded starts its counter at 1,
-- and the first drink added by hand would land on id 1 -- outside its
-- range, and colliding with the seed the moment anyone ran it.
--
-- Harmless to re-run: MySQL ignores an AUTO_INCREMENT lower than the
-- highest id present, so this can never pull a live counter backwards.
ALTER TABLE drink    AUTO_INCREMENT = 1001;
ALTER TABLE glass    AUTO_INCREMENT = 3001;
ALTER TABLE category AUTO_INCREMENT = 4001;
ALTER TABLE drink_type AUTO_INCREMENT = 5001;

INSERT INTO drink_category_mapping (
    drink_id,
    category_id
)
VALUES
    (1001, 4003),
    (1001, 4001),
    (1002, 4003),
    (1002, 4005),
    (1003, 4004),
    (1004, 4002),
    (1004, 4001),
    (1005, 4005)
ON DUPLICATE KEY UPDATE
    category_id = VALUES(category_id);

-- ------------------------------------------------------------
-- 4. RECIPE
-- recipe is the direct drink -> ingredient mapping.
-- Các dòng trùng khóa sẽ được cập nhật target_gram.
-- ------------------------------------------------------------

INSERT IGNORE INTO recipe (
    drink_id,
    step_no,
    ingredient_id,
    target_gram
)
VALUES
    -- Peach Tea
    (1, 1, 1, 120),
    (1, 1, 2, 80),
    (1, 2, 4, 30),

    -- Milk Tea
    (2, 1, 2, 100),
    (2, 1, 1, 50),

    -- Milk Coffee
    (3, 1, 3, 60),
    (3, 1, 1, 30),

    -- Strawberry Soda
    (4, 1, 5, 30),
    (4, 1, 6, 150),

    -- Chocolate Milk
    (5, 1, 1, 50);

-- ------------------------------------------------------------
-- 5. CALCULATE THRESHOLD
-- threshold = lượng lớn nhất của nguyên liệu trong một recipe * 110%
-- Nếu cùng nguyên liệu xuất hiện nhiều bước trong một recipe, tổng các bước
-- được tính trước khi lấy giá trị lớn nhất.
-- ------------------------------------------------------------

UPDATE ingredient AS target
LEFT JOIN (
    SELECT
        ingredient_id,
        ROUND(MAX(recipe_total_gram) * 1.10, 2) AS threshold_gram
    FROM (
        SELECT
            drink_id,
            ingredient_id,
            SUM(target_gram) AS recipe_total_gram
        FROM recipe
        GROUP BY
            drink_id,
            ingredient_id
    ) AS recipe_usage
    GROUP BY ingredient_id
) AS calculated
    ON calculated.ingredient_id = target.ingredient_id
SET target.threshold_gram = COALESCE(
    calculated.threshold_gram,
    0
);

-- ------------------------------------------------------------
-- 6. CALCULATE DRINK STOCK
-- Món chỉ còn hàng khi có recipe và mọi nguyên liệu đều in_stock.
-- ------------------------------------------------------------

UPDATE drink AS target
LEFT JOIN (
    SELECT
        recipe.drink_id,
        COUNT(recipe.ingredient_id) AS ingredient_count,
        MIN(
            CASE
                WHEN ingredient.in_stock = TRUE THEN 1
                ELSE 0
            END
        ) AS every_ingredient_instock
    FROM recipe AS recipe
    LEFT JOIN ingredient AS ingredient
        ON ingredient.ingredient_id = recipe.ingredient_id
    GROUP BY recipe.drink_id
) AS stock
    ON stock.drink_id = target.drink_id
SET target.in_stock = IF(
    COALESCE(stock.ingredient_count, 0) > 0
    AND COALESCE(stock.every_ingredient_instock, 0) = 1,
    TRUE,
    FALSE
);
