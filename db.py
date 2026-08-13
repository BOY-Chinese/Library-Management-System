# db.py
import pymysql
from config import Config


def get_conn():
    return pymysql.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DB,
        cursorclass=pymysql.cursors.DictCursor  # 让查询结果返回字典，方便处理
    )


def auto_migrate():
    """启动时自动检测并补齐缺失的数据库列 / 更新存储过程，无需手动执行 SQL"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            # ---- 1. readertype：可借数量 / 可借天数 ----
            cols = _existing_columns(cur, 'readertype')
            if '可借数量' not in cols:
                cur.execute("ALTER TABLE readertype ADD COLUMN `可借数量` INT NOT NULL DEFAULT 5")
                print('[迁移] readertype + 可借数量')
            if '可借天数' not in cols:
                cur.execute("ALTER TABLE readertype ADD COLUMN `可借天数` INT NOT NULL DEFAULT 30")
                print('[迁移] readertype + 可借天数')
            # 确保默认值合理
            cur.execute("""
                UPDATE readertype SET 可借数量=10, 可借天数=60  WHERE 类别号='R01' AND 可借数量=5;
                UPDATE readertype SET 可借数量=15, 可借天数=90  WHERE 类别号='R02' AND 可借数量=5;
                UPDATE readertype SET 可借数量=20, 可借天数=120 WHERE 类别号='R03' AND 可借数量=5;
            """)

            # ---- 2. borrowrecord：应还日期 ----
            cols = _existing_columns(cur, 'borrowrecord')
            if '应还日期' not in cols:
                cur.execute("ALTER TABLE borrowrecord ADD COLUMN `应还日期` DATE DEFAULT NULL")
                print('[迁移] borrowrecord + 应还日期')
                # 给历史数据补一个估算值
                cur.execute("UPDATE borrowrecord SET 应还日期 = DATE_ADD(借阅日期, INTERVAL 60 DAY) WHERE 应还日期 IS NULL")

            # ---- 3. 重建 sp_borrow_book ----
            cur.execute("DROP PROCEDURE IF EXISTS sp_borrow_book")
            cur.execute("""
                CREATE PROCEDURE sp_borrow_book(IN p_reader_id INT, IN p_book_id INT)
                BEGIN
                    DECLARE v_max_count INT;
                    DECLARE v_max_days INT;
                    DECLARE v_current_count INT;
                    DECLARE v_due_date DATE;
                    DECLARE EXIT HANDLER FOR SQLEXCEPTION
                    BEGIN
                        ROLLBACK;
                        RESIGNAL;
                    END;
                    START TRANSACTION;
                    SELECT rt.可借数量, rt.可借天数 INTO v_max_count, v_max_days
                    FROM reader r JOIN readertype rt ON r.类别号 = rt.类别号
                    WHERE r.读者编号 = p_reader_id;
                    SELECT COUNT(*) INTO v_current_count
                    FROM borrowrecord WHERE 读者编号 = p_reader_id AND 是否归还 = '否';
                    IF v_current_count >= v_max_count THEN
                        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '借阅数量已达上限，请先归还部分图书';
                    END IF;
                    IF (SELECT 库存 FROM book WHERE 图书编号 = p_book_id) <= 0 THEN
                        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '库存不足';
                    END IF;
                    SET v_due_date = DATE_ADD(CURDATE(), INTERVAL v_max_days DAY);
                    UPDATE book SET 库存 = 库存 - 1 WHERE 图书编号 = p_book_id;
                    INSERT INTO borrowrecord (图书编号, 读者编号, 借阅日期, 应还日期, 是否归还)
                    VALUES (p_book_id, p_reader_id, CURDATE(), v_due_date, '否');
                    COMMIT;
                END
            """)
            print('[迁移] sp_borrow_book 已更新')

        conn.commit()
        print('[迁移] 数据库结构检查完成')
    except Exception as e:
        print(f'[迁移] 警告 - 自动迁移失败：{e}')
    finally:
        conn.close()


def _existing_columns(cur, table_name):
    """返回表中已有的列名集合"""
    cur.execute(f"SHOW COLUMNS FROM `{table_name}`")
    return {row['Field'] for row in cur.fetchall()}