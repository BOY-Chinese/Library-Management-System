# config.py
import os
import sys
import json


def get_config_path():
    """获取配置文件路径（与 exe 同目录，开发时与 config.py 同目录）"""
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, 'db_config.json')


class Config:
    MYSQL_HOST = 'localhost'
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = ''
    MYSQL_DB = 'librarydb'
    SECRET_KEY = 'any-simple-key'


def load_config():
    """从 JSON 文件加载数据库配置，返回 True 表示成功加载"""
    path = get_config_path()
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        Config.MYSQL_HOST = data.get('host', Config.MYSQL_HOST)
        Config.MYSQL_USER = data.get('user', Config.MYSQL_USER)
        Config.MYSQL_PASSWORD = data.get('password', Config.MYSQL_PASSWORD)
        Config.MYSQL_DB = data.get('database', Config.MYSQL_DB)
        return True
    return False


def save_config(host, user, password, database):
    """保存数据库配置到 JSON 文件，同时更新 Config 类属性"""
    path = get_config_path()
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({
            'host': host,
            'user': user,
            'password': password,
            'database': database
        }, f, ensure_ascii=False, indent=2)
    Config.MYSQL_HOST = host
    Config.MYSQL_USER = user
    Config.MYSQL_PASSWORD = password
    Config.MYSQL_DB = database
