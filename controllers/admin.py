from flask import Blueprint, request
from dao import book_dao, reader_dao
from services import book_service
from utils.response import success, error
from db import get_conn

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

@admin_bp.route('/login', methods=['POST'])
def admin_login():
    """管理员登录"""
    data = request.get_json()
    name = data.get('管理员名')
    pwd = data.get('密码')
    
    if not name or not pwd:
        return error("账号密码不能为空")
    
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM admin WHERE 管理员名=%s AND 密码=%s", (name, pwd))
            admin = cur.fetchone()
    finally:
        conn.close()
    
    if admin:
        return success({
            "管理员编号": admin['管理员编号'],
            "管理员名": admin['管理员名']
        }, "登录成功")
    return error("账号或密码错误", 401)

@admin_bp.route('/books', methods=['POST'])
def add_book():
    """添加图书"""
    data = request.get_json()
    ok, result = book_service.add_book(data)
    if ok:
        return success({"图书编号": result}, "添加成功")
    return error(result, 400)

@admin_bp.route('/books/<int:book_id>', methods=['PUT'])
def update_book(book_id):
    """修改图书"""
    data = request.get_json()
    ok, msg = book_service.update_book(book_id, data)
    if ok:
        return success(None, msg)
    return error(msg, 400)

@admin_bp.route('/books/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    """删除图书"""
    ok, msg = book_service.delete_book(book_id)
    if ok:
        return success(None, msg)
    return error(msg, 400)

@admin_bp.route('/readers', methods=['GET'])
def list_readers():
    """查询所有读者"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 读者编号, 姓名, 性别, 类别号 FROM reader")
            readers = cur.fetchall()
    finally:
        conn.close()
    return success(readers)

@admin_bp.route('/reader-types', methods=['GET'])
def get_reader_types():
    """获取所有读者类别及其借阅限制"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 类别号, 类别名, 可借数量, 可借天数 FROM readertype ORDER BY 类别号")
            types = cur.fetchall()
    finally:
        conn.close()
    return success(types)

@admin_bp.route('/reader-types/<category_id>', methods=['PUT'])
def update_reader_type(category_id):
    """修改读者类别的借阅限制"""
    data = request.get_json()
    max_count = data.get('可借数量')
    max_days = data.get('可借天数')

    if max_count is None and max_days is None:
        return error("至少需要提供一个要修改的字段（可借数量 或 可借天数）", 400)

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            # 检查类别是否存在
            cur.execute("SELECT 类别号 FROM readertype WHERE 类别号 = %s", (category_id,))
            if not cur.fetchone():
                return error(f"读者类别「{category_id}」不存在", 404)

            # 动态组装 SET 子句
            set_parts = []
            values = []
            if max_count is not None:
                if not isinstance(max_count, int) or max_count < 1:
                    return error("可借数量必须为正整数", 400)
                set_parts.append("可借数量 = %s")
                values.append(max_count)
            if max_days is not None:
                if not isinstance(max_days, int) or max_days < 1:
                    return error("可借天数必须为正整数", 400)
                set_parts.append("可借天数 = %s")
                values.append(max_days)

            values.append(category_id)
            sql = f"UPDATE readertype SET {', '.join(set_parts)} WHERE 类别号 = %s"
            cur.execute(sql, values)
            conn.commit()

            # 返回更新后的记录
            cur.execute(
                "SELECT 类别号, 类别名, 可借数量, 可借天数 FROM readertype WHERE 类别号 = %s",
                (category_id,)
            )
            updated = cur.fetchone()
    finally:
        conn.close()

    return success(updated, f"读者类别「{category_id}」的借阅限制已更新")