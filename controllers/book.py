from flask import Blueprint, request
from services import book_service
from utils.response import success, error

book_bp = Blueprint('book', __name__, url_prefix='/api')

@book_bp.route('/books', methods=['GET'])
def search_books():
    """组合搜索：书名、作者、ISBN、出版社、类别各自独立，AND 组合 + 分页"""
    book_name = request.args.get('书名', '')
    author = request.args.get('作者', '')
    isbn = request.args.get('ISBN', '')
    publisher = request.args.get('出版社', '')
    category = request.args.get('类别号', '')
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))

    ok, result = book_service.search_books(book_name, author, isbn, publisher, category, page, limit)
    if ok:
        return success(result)
    return error(result, 400)

@book_bp.route('/categories', methods=['GET'])
def get_categories():
    """获取所有图书类别"""
    from db import get_conn
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM bookcategory ORDER BY 类别号")
            cats = cur.fetchall()
        return success(cats)
    finally:
        conn.close()

@book_bp.route('/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    """查询单本图书详情"""
    from dao import book_dao
    book = book_dao.find_by_id(book_id)
    if book:
        return success(book)
    return error("图书不存在", 404)