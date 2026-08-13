import hashlib
from dao import reader_dao

def register(name, password, gender, birth, category, admin_id):
    """注册新读者"""
    if not name or not password:
        return False, "姓名和密码不能为空"
    
    pwd_hash = hashlib.md5(password.encode()).hexdigest()
    try:
        new_id = reader_dao.insert(name, pwd_hash, gender, birth, category, admin_id)
        return True, {"读者编号": new_id}
    except Exception as e:
        return False, f"注册失败：{str(e)}"

def login(reader_id, password):
    """读者登录"""
    if not reader_id or not password:
        return False, "读者编号和密码不能为空"
    
    reader = reader_dao.find_by_id(reader_id)
    if not reader:
        return False, "读者不存在"
    
    pwd_hash = hashlib.md5(password.encode()).hexdigest()
    if reader['密码'] != pwd_hash:
        return False, "密码错误"
    
    # 不返回密码字段
    return True, {
        "读者编号": reader['读者编号'],
        "姓名": reader['姓名'],
        "性别": reader['性别'],
        "类别号": reader['类别号']
    }