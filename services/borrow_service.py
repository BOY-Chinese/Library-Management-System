from db import get_conn

# 借书（预校验 + 调用存储过程，共用同一 cursor 避免 pymysql 冲突）
def borrow(reader_id, book_id):
    if not reader_id or not book_id:
        return False, "读者编号和图书编号不能为空"

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            # 1. 预校验：查询读者类别的借阅上限
            cur.execute("""
                SELECT rt.可借数量, rt.可借天数,
                       (SELECT COUNT(*) FROM borrowrecord
                        WHERE 读者编号 = %s AND 是否归还 = '否') AS 当前在借
                FROM reader r
                JOIN readertype rt ON r.类别号 = rt.类别号
                WHERE r.读者编号 = %s
            """, (reader_id, reader_id))
            limit_info = cur.fetchone()

            if limit_info and limit_info['当前在借'] >= limit_info['可借数量']:
                return False, (
                    f"借阅数量已达上限（最多 {limit_info['可借数量']} 本），"
                    f"当前在借 {limit_info['当前在借']} 本，请先归还部分图书"
                )

            # 2. 调用存储过程完成借书
            cur.callproc('sp_borrow_book', (reader_id, book_id))
            cur.execute("SELECT LAST_INSERT_ID() AS 借阅编号")
            record = cur.fetchone()
            conn.commit()

        return True, {
            "借阅编号": record["借阅编号"] if record else None,
            "读者编号": reader_id,
            "图书编号": book_id,
        }
    except Exception as e:
        conn.rollback()
        return False, f"借阅失败：{str(e)}"
    finally:
        conn.close()


# 还书
def return_book(borrow_id):
    if not borrow_id:
        return False, "借阅编号不能为空"

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.callproc('sp_return_book', (borrow_id,))
            conn.commit()
        return True, "还书成功"
    except Exception as e:
        conn.rollback()
        return False, f"还书失败：{str(e)}"
    finally:
        conn.close()


# 查询个人借阅历史（含应还日期）
def get_reader_history(reader_id):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            sql = """
                SELECT
                    br.借阅编号,
                    r.读者编号,
                    r.姓名,
                    b.图书编号,
                    b.图书名,
                    br.借阅日期,
                    br.应还日期,
                    br.是否归还
                FROM borrowrecord AS br
                JOIN reader AS r ON br.读者编号 = r.读者编号
                JOIN book AS b ON br.图书编号 = b.图书编号
                WHERE r.读者编号 = %s
                ORDER BY br.借阅日期 DESC, br.借阅编号 DESC
            """
            cur.execute(sql, (reader_id,))
            result = cur.fetchall()
        return True, result
    except Exception as e:
        return False, f"查询失败：{str(e)}"
    finally:
        conn.close()


# 查询当前在借记录（含应还日期）
def get_current_borrows():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            sql = """
                SELECT
                    br.借阅编号,
                    b.图书编号,
                    b.图书名,
                    r.读者编号,
                    r.姓名,
                    br.借阅日期,
                    br.应还日期
                FROM borrowrecord AS br
                JOIN book AS b ON br.图书编号 = b.图书编号
                JOIN reader AS r ON br.读者编号 = r.读者编号
                WHERE br.是否归还 = '否'
                ORDER BY br.借阅日期 DESC, br.借阅编号 DESC
            """
            cur.execute(sql)
            result = cur.fetchall()
        return True, result
    except Exception as e:
        return False, f"查询失败：{str(e)}"
    finally:
        conn.close()
