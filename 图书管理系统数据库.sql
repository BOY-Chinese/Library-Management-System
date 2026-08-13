CREATE DATABASE `librarydb`
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE `librarydb`;

CREATE TABLE `readertype` (
    `类别号`   VARCHAR(20) PRIMARY KEY,
    `类别名`   VARCHAR(50) NOT NULL,
    `可借数量`  INT NOT NULL DEFAULT 5 COMMENT '该类别读者最多可同时借阅的本数',
    `可借天数`  INT NOT NULL DEFAULT 30 COMMENT '该类别读者每本书可借阅的天数'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `bookcategory` (
    `类别号`   VARCHAR(20) PRIMARY KEY,
    `类别名`   VARCHAR(50) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `admin` (
    `管理员编号`  INT AUTO_INCREMENT PRIMARY KEY,
    `管理员名`   VARCHAR(50) NOT NULL,
    `密码`      VARCHAR(255) NOT NULL,
    `管理权限`   VARCHAR(50) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `reader` (
    `读者编号`   INT AUTO_INCREMENT PRIMARY KEY,
    `密码`      VARCHAR(255) NOT NULL,
    `姓名`      VARCHAR(50) NOT NULL,
    `性别`      VARCHAR(4),
    `出生日期`   DATE,
    `类别号`    VARCHAR(20) NOT NULL,
    `管理员编号`  INT NOT NULL,
    FOREIGN KEY (`类别号`) REFERENCES `readertype`(`类别号`),
    FOREIGN KEY (`管理员编号`) REFERENCES `admin`(`管理员编号`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `book` (
    `图书编号`   INT AUTO_INCREMENT PRIMARY KEY,
    `图书名`    VARCHAR(200) NOT NULL,
    `作者`      VARCHAR(200),
    `出版社`    VARCHAR(100),
    `单价`      DECIMAL(10,2),
    `库存`      INT,
    `ISBN`      VARCHAR(20),
    `类别号`    VARCHAR(20) NOT NULL,
    `管理员编号`  INT NOT NULL,
    FOREIGN KEY (`类别号`) REFERENCES `bookcategory`(`类别号`),
    FOREIGN KEY (`管理员编号`) REFERENCES `admin`(`管理员编号`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `borrowrecord` (
    `借阅编号`   INT AUTO_INCREMENT PRIMARY KEY,
    `图书编号`   INT NOT NULL,
    `读者编号`   INT NOT NULL,
    `借阅日期`   DATE NOT NULL DEFAULT (CURRENT_DATE),
    `应还日期`   DATE DEFAULT NULL COMMENT '预计归还日期，由读者类别的可借天数自动计算',
    `是否归还`   VARCHAR(10) NOT NULL DEFAULT '否',
    FOREIGN KEY (`图书编号`) REFERENCES `book`(`图书编号`),
    FOREIGN KEY (`读者编号`) REFERENCES `reader`(`读者编号`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 读者类别（可借数量 / 可借天数）
INSERT INTO `readertype` (`类别号`, `类别名`, `可借数量`, `可借天数`) VALUES
('R01', '本科生', 10, 60),
('R02', '研究生', 15, 90),
('R03', '教师',   20, 120);

-- 图书类别
INSERT INTO `bookcategory` (`类别号`, `类别名`) VALUES
('TP', '计算机'), ('I', '文学'), ('H', '语言');

-- 管理员
INSERT INTO `admin` (`管理员名`, `密码`, `管理权限`) VALUES
('admin', '123456', '系统管理员'),
('lib01', '123456', '普通管理员');

-- 读者
INSERT INTO `reader` (`姓名`, `密码`, `性别`, `出生日期`, `类别号`, `管理员编号`) VALUES
('张三', '123456', '男', '2000-01-01', 'R01', 1),
('李四', '123456', '女', '1999-05-10', 'R02', 1);

-- 图书
INSERT INTO `book` (`图书名`, `作者`, `出版社`, `单价`, `库存`, `ISBN`, `类别号`, `管理员编号`) VALUES
('数据库系统概论', '王珊', '高教', 45.00, 10, '9787111', 'TP', 1),
('红楼梦', '曹雪芹', '人民文学', 38.00, 5, '9787020', 'I', 1);

-- 借阅记录
INSERT INTO `borrowrecord` (`图书编号`, `读者编号`, `借阅日期`, `应还日期`, `是否归还`) VALUES
(1, 1, '2025-06-01', '2025-08-01', '否');

-- 存储过程：借书（含借阅数量限制 + 自动计算应还日期）
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

    -- 1. 获取该读者类别的可借数量和可借天数
    SELECT rt.可借数量, rt.可借天数 INTO v_max_count, v_max_days
    FROM reader r
    JOIN readertype rt ON r.类别号 = rt.类别号
    WHERE r.读者编号 = p_reader_id;

    -- 2. 查询当前在借数量
    SELECT COUNT(*) INTO v_current_count
    FROM borrowrecord
    WHERE 读者编号 = p_reader_id AND 是否归还 = '否';

    IF v_current_count >= v_max_count THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = '借阅数量已达上限，请先归还部分图书';
    END IF;

    -- 3. 检查库存
    IF (SELECT 库存 FROM book WHERE 图书编号 = p_book_id) <= 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '库存不足';
    END IF;

    -- 4. 计算应还日期
    SET v_due_date = DATE_ADD(CURDATE(), INTERVAL v_max_days DAY);

    -- 5. 减库存
    UPDATE book SET 库存 = 库存 - 1 WHERE 图书编号 = p_book_id;

    -- 6. 插入借阅记录
    INSERT INTO borrowrecord (图书编号, 读者编号, 借阅日期, 应还日期, 是否归还)
    VALUES (p_book_id, p_reader_id, CURDATE(), v_due_date, '否');

    COMMIT;
END //
DELIMITER ;

-- 存储过程：还书
DELIMITER //
CREATE PROCEDURE sp_return_book(IN p_borrow_id INT)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;
    START TRANSACTION;
    -- 检查借阅记录是否存在且未归还
    IF NOT EXISTS (SELECT 1 FROM borrowrecord WHERE 借阅编号 = p_borrow_id AND 是否归还 = '否') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '借阅记录无效或已归还';
    END IF;
    -- 更新状态
    UPDATE borrowrecord SET 是否归还 = '是' WHERE 借阅编号 = p_borrow_id;
    -- 增加库存（需要知道图书编号，可子查询或变量）
    UPDATE book SET 库存 = 库存 + 1 
    WHERE 图书编号 = (SELECT 图书编号 FROM borrowrecord WHERE 借阅编号 = p_borrow_id);
    COMMIT;
END //
DELIMITER ;

-- 视图：当前在借
CREATE VIEW v_current_borrows AS
SELECT b.图书编号, b.图书名, r.读者编号, r.姓名, br.借阅日期
FROM borrowrecord br
JOIN book b ON br.图书编号 = b.图书编号
JOIN reader r ON br.读者编号 = r.读者编号
WHERE br.是否归还 = '否';

-- 视图：读者借阅历史
CREATE VIEW v_reader_history AS
SELECT r.读者编号, r.姓名, b.图书名, br.借阅日期, br.是否归还
FROM borrowrecord br
JOIN reader r ON br.读者编号 = r.读者编号
JOIN book b ON br.图书编号 = b.图书编号;