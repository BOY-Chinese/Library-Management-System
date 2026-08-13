from flask import Blueprint, request
from services import borrow_service
from utils.response import success, error

borrow_bp = Blueprint('borrow', __name__, url_prefix='/api')

@borrow_bp.route('/borrow', methods=['POST'])
def borrow():
    """借书"""
    data = request.get_json()
    reader_id = data.get('读者编号')
    book_id = data.get('图书编号')
    
    ok, result = borrow_service.borrow(reader_id, book_id)
    if ok:
        return success(result, "借阅成功")
    return error(result, 400)

@borrow_bp.route('/return', methods=['PUT'])
def return_book():
    """还书"""
    data = request.get_json()
    borrow_id = data.get('借阅编号')
    
    ok, msg = borrow_service.return_book(borrow_id)
    if ok:
        return success(None, msg)
    return error(msg, 400)

@borrow_bp.route('/reader/<int:reader_id>/history', methods=['GET'])
def reader_history(reader_id):
    """个人借阅历史"""
    ok, result = borrow_service.get_reader_history(reader_id)
    if ok:
        return success(result)
    return error(result, 400)

@borrow_bp.route('/borrows/current', methods=['GET'])
def current_borrows():
    """当前在借列表（管理员用）"""
    ok, result = borrow_service.get_current_borrows()
    if ok:
        return success(result)
    return error(result, 400)