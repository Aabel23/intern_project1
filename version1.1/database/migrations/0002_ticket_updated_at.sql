-- ============================================================
-- 0002 — order_ticket.updated_at, và index để quét theo nó
-- ============================================================
--
-- VÌ SAO CẦN CỘT NÀY
--     Agent của Hub đẩy vé lên theo lối "cái gì đã đổi kể từ lần trước"
--     (pha P4 của docs/Lo_Trinh_Code_Hub.md). Nó cần một mốc trả lời đúng
--     câu "dòng này vừa bị sửa lúc nào".
--
--     Bảng đang có created_at, scanned_at và completed_at. Không cột nào
--     làm được việc đó: một vé bị sửa trạng thái bằng tay trên trang Vé QR
--     không chạm vào cột nào trong ba cột ấy, nên agent sẽ không bao giờ
--     thấy thay đổi đó.
--
-- ON UPDATE CURRENT_TIMESTAMP
--     Để MySQL tự lo, nhờ đó mọi đường ghi đều được tính — kể cả những
--     đường chưa tồn tại hôm nay. Một cột phải nhớ cập nhật bằng tay là
--     một cột sẽ bị quên ở đúng chỗ ít ai đọc nhất.
--
-- BA BƯỚC, VÀ VÌ SAO KHÔNG GỘP THÀNH MỘT
--     Cách hiển nhiên là thêm cột kèm sẵn DEFAULT CURRENT_TIMESTAMP rồi vá
--     dữ liệu cũ sau. Cách đó HỎNG, và hỏng im lặng: ALTER TABLE đặt
--     updated_at = NOW() cho mọi dòng đang có, nên không còn cách nào phân
--     biệt "dòng cũ chưa vá" với "dòng vừa thật sự được sửa". Câu UPDATE
--     vá dữ liệu hoặc không khớp dòng nào, hoặc khớp cả những dòng không
--     được phép đụng.
--
--     Nên: thêm cột cho phép NULL trước. NULL là dấu duy nhất không thể
--     nhầm — nó nghĩa là "dòng này có từ trước khi có cột này, chưa ai vá".
--     Vá xong mới siết thành NOT NULL kèm mặc định.
--
-- VÌ SAO PHẢI VÁ DỮ LIỆU CŨ
--     Không vá thì mọi vé cũ mang cùng một mốc: lúc chạy migration này.
--     Agent quét lần đầu sẽ thấy cả nghìn vé "vừa sửa xong" trong cùng một
--     giây, và thứ tự thời gian thật của chúng mất vĩnh viễn.
--
--     completed_at nếu vé đã xong, không thì scanned_at, không nữa thì
--     created_at — lần cuối dòng đó thật sự đổi, theo đúng những gì bảng
--     còn nhớ được.
--
-- VÌ SAO DÙNG PREPARE/EXECUTE
--     MySQL 8 KHÔNG có `ADD COLUMN IF NOT EXISTS` (đó là cú pháp MariaDB),
--     cũng không có `CREATE INDEX IF NOT EXISTS`. Mà DDL trong MySQL không
--     nằm trong transaction: file này có bốn thao tác, hỏng ở thao tác thứ
--     ba thì hai thao tác đầu ĐÃ nằm trong database và không lùi được. Bộ
--     chạy chỉ ghi vào sổ sau khi cả file xong, nên lần sau nó chạy lại từ
--     đầu file.
--
--     Khuôn dưới đây biến mỗi thao tác thành thứ chạy lần hai vẫn vô hại —
--     đúng ràng buộc mà database/migrate.py đặt ra.
-- ============================================================

-- ---- 1. Thêm cột, CHO PHÉP NULL, nếu chưa có ----
--
-- Không đặt DEFAULT ở bước này: có default thì dòng cũ nhận NOW() và dấu
-- "chưa vá" biến mất ngay lập tức.
SET @ddl := (
    SELECT IF(COUNT(*) = 0,
        'ALTER TABLE order_ticket ADD COLUMN updated_at DATETIME NULL',
        'DO 0')
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'order_ticket'
      AND COLUMN_NAME = 'updated_at'
);
PREPARE add_column FROM @ddl;
EXECUTE add_column;
DEALLOCATE PREPARE add_column;

-- ---- 2. Vá mốc cho những vé đã có ----
--
-- `WHERE updated_at IS NULL` là toàn bộ chốt chặn của bước này. Vá xong
-- thì không còn NULL nào, nên chạy lại là không đụng dòng nào — kể cả một
-- vé vừa được sửa tay sau lần chạy hỏng trước đó.
UPDATE order_ticket
   SET updated_at = COALESCE(completed_at, scanned_at, created_at)
 WHERE updated_at IS NULL;

-- ---- 3. Siết thành NOT NULL, kèm mặc định và tự cập nhật ----
--
-- Chỉ chạy khi cột còn đang cho phép NULL, nên lần hai là không làm gì.
SET @ddl := (
    SELECT IF(IS_NULLABLE = 'YES',
        'ALTER TABLE order_ticket
             MODIFY COLUMN updated_at DATETIME NOT NULL
                 DEFAULT CURRENT_TIMESTAMP
                 ON UPDATE CURRENT_TIMESTAMP',
        'DO 0')
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'order_ticket'
      AND COLUMN_NAME = 'updated_at'
);
PREPARE tighten FROM @ddl;
EXECUTE tighten;
DEALLOCATE PREPARE tighten;

-- ---- 4. Index để agent quét theo mốc ----
--
-- (updated_at, serial) chứ không chỉ updated_at: agent đọc theo lô, sắp
-- theo updated_at rồi phân trang. Nhiều vé xong trong cùng một giây là
-- chuyện thường, và không có khoá phụ phá hoà thì thứ tự giữa các lô là
-- tuỳ engine — một dòng hiện hai lần, một dòng khác biến mất. Cùng lý do
-- mà admin_gui/serve.py sắp theo "completed_at DESC, serial DESC".
SET @ddl := (
    SELECT IF(COUNT(*) = 0,
        'CREATE INDEX idx_order_ticket_updated
             ON order_ticket (updated_at, serial)',
        'DO 0')
    FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'order_ticket'
      AND INDEX_NAME = 'idx_order_ticket_updated'
);
PREPARE add_index FROM @ddl;
EXECUTE add_index;
DEALLOCATE PREPARE add_index;
