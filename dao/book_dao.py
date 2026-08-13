from db import get_conn

# 组合搜索：书名、作者、ISBN、出版社、类别各自独立，全部 AND 组合
def search(book_name, author, isbn, publisher, category, offset, limit):
    conn=get_conn()
    try:
        with conn.cursor() as cur:
            sql="SELECT * FROM book WHERE 1=1"
            params=[]

            if book_name:
                sql+=" AND 图书名 LIKE %s"
                params.append(f"%{book_name}%")

            if author:
                sql+=" AND 作者 LIKE %s"
                params.append(f"%{author}%")

            if isbn:
                sql+=" AND ISBN LIKE %s"
                params.append(f"%{isbn}%")

            if publisher:
                sql+=" AND 出版社 LIKE %s"
                params.append(f"%{publisher}%")

            if category:
                sql+=" AND 类别号 = %s"
                params.append(category)

            sql+=" LIMIT %s OFFSET %s"
            params.extend([limit,offset])

            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        conn.close()

#查找书本id
def find_by_id(book_id):
    conn=get_conn()
    try:
        with conn.cursor() as cur:
            sql="SELECT * FROM book WHERE 图书编号=%s"
            cur.execute(sql,(book_id,))
        return cur.fetchone()
    finally:
        conn.close()

#统计符合搜索条件的库存总量
def sum_stock(book_name, author, isbn, publisher, category):
    conn=get_conn()
    try:
        with conn.cursor() as cur:
            sql="SELECT COALESCE(SUM(库存),0) AS total_stock FROM book WHERE 1=1"
            params=[]

            if book_name:
                sql+=" AND 图书名 LIKE %s"
                params.append(f"%{book_name}%")

            if author:
                sql+=" AND 作者 LIKE %s"
                params.append(f"%{author}%")

            if isbn:
                sql+=" AND ISBN LIKE %s"
                params.append(f"%{isbn}%")

            if publisher:
                sql+=" AND 出版社 LIKE %s"
                params.append(f"%{publisher}%")

            if category:
                sql+=" AND 类别号=%s"
                params.append(category)

            cur.execute(sql,params)
            result=cur.fetchone()
        return result['total_stock'] if result else 0
    finally:
        conn.close()

#统计符合搜索条件的总数
def count_search(book_name, author, isbn, publisher, category):
    conn=get_conn()
    try:
        with conn.cursor() as cur:
            sql="SELECT COUNT(*) AS total FROM book WHERE 1=1"
            params=[]

            if book_name:
                sql+=" AND 图书名 LIKE %s"
                params.append(f"%{book_name}%")

            if author:
                sql+=" AND 作者 LIKE %s"
                params.append(f"%{author}%")

            if isbn:
                sql+=" AND ISBN LIKE %s"
                params.append(f"%{isbn}%")

            if publisher:
                sql+=" AND 出版社 LIKE %s"
                params.append(f"%{publisher}%")

            if category:
                sql+=" AND 类别号=%s"
                params.append(category)

            cur.execute(sql,params)
            result=cur.fetchone()
        return result['total'] if result else 0
    finally:
        conn.close()

#确保类别号在 bookcategory 表中存在（不存在则自动创建）
def ensure_category(category_code):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 类别号 FROM bookcategory WHERE 类别号 = %s", (category_code,))
            if not cur.fetchone():
                cur.execute(
                    "INSERT INTO bookcategory (类别号, 类别名) VALUES (%s, %s)",
                    (category_code, category_code)
                )
                conn.commit()
    finally:
        conn.close()

#新增图书
def insert(data):
    conn=get_conn()
    try:
        with conn.cursor() as cur:
            # 先确保类别号存在
            category = data.get('类别号', '')
            if category:
                cur.execute("SELECT 类别号 FROM bookcategory WHERE 类别号 = %s", (category,))
                if not cur.fetchone():
                    cur.execute(
                        "INSERT INTO bookcategory (类别号, 类别名) VALUES (%s, %s)",
                        (category, category)
                    )

            sql="""
            INSERT INTO
            book(图书名, 作者, 出版社, 单价, 库存, ISBN, 类别号, 管理员编号)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s)
            """
            cur.execute(sql, (
                data.get('图书名'),
                data.get('作者', ''),
                data.get('出版社', ''),
                data.get('单价', 0),
                data.get('库存', 0),
                data.get('ISBN', ''),
                category,
                data.get('管理员编号')
            ))
            conn.commit()
        return cur.lastrowid
    finally:
        conn.close()
    
#动态更新图书字段
def update(book_id, data):
    # 允许更新的字段白名单（防止恶意传参）
    allowed_fields = ['图书名', '作者', '出版社', '单价', '库存', 'ISBN', '类别号']

    # 如果更新了类别号，先确保新类别存在
    if '类别号' in data and data['类别号']:
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 类别号 FROM bookcategory WHERE 类别号 = %s", (data['类别号'],))
                if not cur.fetchone():
                    cur.execute(
                        "INSERT INTO bookcategory (类别号, 类别名) VALUES (%s, %s)",
                        (data['类别号'], data['类别号'])
                    )
                    conn.commit()
        finally:
            conn.close()

    # 1. 动态拼接 SET 子句
    set_parts = []      # 存放 ["图书名=%s", "作者=%s", ...]
    values = []         # 存放对应的值

    for field in allowed_fields:
        if field in data:
            set_parts.append(f"{field}=%s")
            values.append(data[field])
    
    # 如果没有任何字段要更新，直接返回 False
    if not set_parts:
        return False
    
    # 2. 组装完整 SQL
    sql = f"UPDATE book SET {', '.join(set_parts)} WHERE 图书编号 = %s"
    values.append(book_id)   # 把 WHERE 条件值加到最后
    
    # 3. 执行
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, values)
            conn.commit()
        return cur.rowcount > 0   # rowcount 是受影响行数
    finally:
        conn.close()
    
#删掉图书
def delete(book_id):
    conn=get_conn()
    try:
        with conn.cursor() as cur:
            sql = "DELETE FROM book WHERE 图书编号 = %s"
            cur.execute(sql, (book_id,))
            conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()