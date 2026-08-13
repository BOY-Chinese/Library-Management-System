from db import get_conn

#查找读者
def find_by_id(reader_id):
    conn=get_conn()
    try:
        with conn.cursor() as cur:
            sql="SELECT * FROM reader WHERE 读者编号 = %s"
            params=(reader_id,)
            cur.execute(sql,params)
        return cur.fetchone()#查找一个独用
    finally:
        conn.close()

#插入新读者，返回自增ID
def insert(name, pwd_hash, gender, birth, category, admin_id):
    conn=get_conn()
    try:
        with conn.cursor() as cur:
            sql="""
            INSERT INTO 
            reader(姓名, 密码, 性别, 出生日期, 类别号, 管理员编号) 
            VALUES(%s,%s,%s,%s,%s,%s)
            """
            params=(name,pwd_hash,gender,birth,category,admin_id)
            cur.execute(sql,params)
            conn.commit()
        return cur.lastrowid
    finally:
        conn.close()

