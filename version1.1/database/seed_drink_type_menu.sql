-- ============================================================
-- A STARTING drink_type AND garnish FOR THE MENU AS IT STANDS
--
-- Not part of the schema and not run by database.sql. These are the
-- classic builds for the cocktails already on the menu -- a Mojito over
-- crushed ice with mint, a Negroni over a cube with orange -- so the prep
-- card has something to show on day one instead of a single LY chip.
--
-- Every value here is a starting point, not a rule: change any of it in
-- the admin recipe editor. To clear the lot and start over:
--
--   UPDATE drink SET drink_type_id = NULL, garnish = NULL;
--
-- Matched by name, so a drink that has been renamed is simply skipped
-- rather than being given somebody else's garnish.
-- ============================================================

UPDATE drink SET drink_type_id = 5001, garnish = 'Lát đào, ống hút to'        WHERE drink_name = 'Peach Tea';
UPDATE drink SET drink_type_id = 5001, garnish = 'Ống hút to, nắp dập'        WHERE drink_name = 'Milk Tea';
UPDATE drink SET drink_type_id = 5001, garnish = 'Ống hút nhỏ'                WHERE drink_name = 'Milk Coffee';
UPDATE drink SET drink_type_id = 5001, garnish = 'Lát dâu, lá bạc hà'         WHERE drink_name = 'Strawberry Soda';
UPDATE drink SET drink_type_id = 5001, garnish = 'Bột cacao rắc mặt'          WHERE drink_name = 'Chocolate Milk';
UPDATE drink SET drink_type_id = 5001, garnish = 'Ống hút to'                 WHERE drink_name IN ('SO1', 'kham drink');

UPDATE drink SET drink_type_id = 5003, garnish = 'Lát cam, cherry, ống hút to' WHERE drink_name = 'Rainbow Paradise';
UPDATE drink SET drink_type_id = 5005, garnish = 'Vỏ chanh vàng'              WHERE drink_name = 'White Lady';
UPDATE drink SET drink_type_id = 5005, garnish = 'Ô liu hoặc vỏ chanh vàng'   WHERE drink_name = 'Martini';
UPDATE drink SET drink_type_id = 5005, garnish = 'Cherry ngâm'                WHERE drink_name = 'Manhattan';
UPDATE drink SET drink_type_id = 5001, garnish = 'Cần tây, lát chanh'         WHERE drink_name = 'Bloody Mary';
UPDATE drink SET drink_type_id = 5003, garnish = 'Chùm bạc hà, lát chanh'     WHERE drink_name = 'Mojito';
UPDATE drink SET drink_type_id = 5001, garnish = 'Vỏ cam, cherry'             WHERE drink_name = 'Whiskey Sour';
UPDATE drink SET drink_type_id = 5005, garnish = 'Viền muối, lát chanh'       WHERE drink_name = 'Margarita';
UPDATE drink SET drink_type_id = 5003, garnish = 'Chùm bạc hà, lát chanh'     WHERE drink_name = 'Moscow Mule';
UPDATE drink SET drink_type_id = 5001, garnish = 'Lát cam'                    WHERE drink_name = 'Aperol Spritz';
UPDATE drink SET drink_type_id = 5001, garnish = 'Vỏ cam'                     WHERE drink_name IN ('Old Fashion', 'Boulevardier');
UPDATE drink SET drink_type_id = 5005, garnish = NULL                         WHERE drink_name IN ('Angel Shot', 'Gin Shot');
UPDATE drink SET drink_type_id = 5001, garnish = 'Lát cam'                    WHERE drink_name = 'Negroni';
UPDATE drink SET drink_type_id = 5003, garnish = 'Chùm bạc hà'                WHERE drink_name = 'Mint Julep';
UPDATE drink SET drink_type_id = 5005, garnish = '3 hạt cà phê'               WHERE drink_name = 'Espresso Martini';
UPDATE drink SET drink_type_id = 5005, garnish = 'Lát chanh'                  WHERE drink_name = 'Daiquiri';
UPDATE drink SET drink_type_id = 5004, garnish = 'Lát dứa, cherry, ống hút to' WHERE drink_name = 'Piña Colada';
UPDATE drink SET drink_type_id = 5005, garnish = 'Vỏ chanh vàng'              WHERE drink_name IN ('French 75', 'Sazerac');
UPDATE drink SET drink_type_id = 5001, garnish = 'Lát chanh, cherry'          WHERE drink_name = 'Tom Collins';
UPDATE drink SET drink_type_id = 5005, garnish = 'Cherry ngâm'                WHERE drink_name = 'Aviation';
UPDATE drink SET drink_type_id = 5006, garnish = 'Kem tươi, bột cacao'        WHERE drink_name = 'Mocha';
UPDATE drink SET drink_type_id = 5006, garnish = NULL                         WHERE drink_name = 'Espresso';
UPDATE drink SET drink_type_id = 5004, garnish = 'Lát dâu, viền muối'         WHERE drink_name = 'Frozen Strawberry Margarita';
UPDATE drink SET drink_type_id = 5006, garnish = 'Kem tươi'                   WHERE drink_name = 'Irish Coffee';
UPDATE drink SET drink_type_id = 5003, garnish = 'Lá bạc hà, lát dứa'         WHERE drink_name = 'Mai Tai';
UPDATE drink SET drink_type_id = 5005, garnish = 'Viền đường, vỏ cam'         WHERE drink_name = 'Sidecar';
UPDATE drink SET drink_type_id = 5001, garnish = 'Lát chanh'                  WHERE drink_name = "Dark 'n' Stormy";
UPDATE drink SET drink_type_id = 5005, garnish = 'Nửa quả chanh dây'          WHERE drink_name = 'Passion Fruit Martini';
UPDATE drink SET drink_type_id = 5004, garnish = 'Kem tươi, ống hút to'       WHERE drink_name = 'Milk Shake';

SELECT COUNT(*) AS still_without_a_type
FROM drink WHERE deleted_at IS NULL AND drink_type_id IS NULL;
