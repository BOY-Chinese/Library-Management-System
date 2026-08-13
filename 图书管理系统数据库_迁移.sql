-- ============================================
-- 迁移脚本：添加借阅限制 + 出版社搜索支持
-- 适用于已有 librarydb 数据库，运行前请备份
-- ============================================

USE `librarydb`;

-- 1. readertype 增加 可借数量 / 可借天数
ALTER TABLE `readertype`
    ADD COLUMN `可借数量` INT NOT NULL DEFAULT 5 COMMENT '该类别读者最多可同时借阅的本数',
    ADD COLUMN `可借天数` INT NOT NULL DEFAULT 30 COMMENT '该类别读者每本书可借阅的天数';

-- 2. 设置各读者类别的借阅限制
UPDATE `readertype` SET `可借数量` = 10, `可借天数` = 60  WHERE `类别号` = 'R01';  -- 本科生
UPDATE `readertype` SET `可借数量` = 15, `可借天数` = 90  WHERE `类别号` = 'R02';  -- 研究生
UPDATE `readertype` SET `可借数量` = 20, `可借天数` = 120 WHERE `类别号` = 'R03';  -- 教师

-- 3. borrowrecord 增加 应还日期
ALTER TABLE `borrowrecord`
    ADD COLUMN `应还日期` DATE DEFAULT NULL COMMENT '预计归还日期，由读者类别的可借天数自动计算';

-- 4. 为历史借阅记录补全应还日期（借阅日期 + 60 天作为估算）
UPDATE borrowrecord br
JOIN reader r ON br.读者编号 = r.读者编号
JOIN readertype rt ON r.类别号 = rt.类别号
SET br.应还日期 = DATE_ADD(br.借阅日期, INTERVAL rt.可借天数 DAY)
WHERE br.借阅编号 > 0              -- 主键绕过安全模式
  AND br.应还日期 IS NULL;


-- 5. 重建借书存储过程（加入限制检查 + 应还日期）
DROP PROCEDURE IF EXISTS `sp_borrow_book`;

DELIMITER //
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

    -- 获取读者类别的借阅参数
    SELECT rt.可借数量, rt.可借天数 INTO v_max_count, v_max_days
    FROM reader r
    JOIN readertype rt ON r.类别号 = rt.类别号
    WHERE r.读者编号 = p_reader_id;

    -- 检查当前在借数量
    SELECT COUNT(*) INTO v_current_count
    FROM borrowrecord
    WHERE 读者编号 = p_reader_id AND 是否归还 = '否';

    IF v_current_count >= v_max_count THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = '借阅数量已达上限，请先归还部分图书';
    END IF;

    -- 检查库存
    IF (SELECT 库存 FROM book WHERE 图书编号 = p_book_id) <= 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '库存不足';
    END IF;

    -- 计算应还日期
    SET v_due_date = DATE_ADD(CURDATE(), INTERVAL v_max_days DAY);

    -- 减库存
    UPDATE book SET 库存 = 库存 - 1 WHERE 图书编号 = p_book_id;

    -- 插入借阅记录
    INSERT INTO borrowrecord (图书编号, 读者编号, 借阅日期, 应还日期, 是否归还)
    VALUES (p_book_id, p_reader_id, CURDATE(), v_due_date, '否');

    COMMIT;
END //
DELIMITER ;

SELECT '迁移完成：readertype 已增加可借数量/可借天数，borrowrecord 已增加应还日期，sp_borrow_book 已更新。' AS result;
