from flask import Blueprint, request
from services import reader_service
from utils.response import success, error

reader_bp = Blueprint('reader', __name__, url_prefix='/api')

@reader_bp.route('/reader/register', methods=['POST'])
def register():
    """读者注册"""
    data = request.get_json()
    name = data.get('姓名')
    password = data.get('密码')
    gender = data.get('性别', '')
    birth = data.get('出生日期')
    category = data.get('类别号', 'R01')
    admin_id = data.get('管理员编号', 1)
    
    ok, result = reader_service.register(name, password, gender, birth, category, admin_id)
    if ok:
        return success(result, "注册成功")
    return error(result, 400)

@reader_bp.route('/reader/login', methods=['POST'])
def login():
    """读者登录"""
    data = request.get_json()
    reader_id = data.get('读者编号')
    password = data.get('密码')
    
    ok, result = reader_service.login(reader_id, password)
    if ok:
        return success(result, "登录成功")
    return error(result, 401)