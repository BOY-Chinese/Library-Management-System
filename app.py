import sys
import os
import webbrowser
import tkinter as tk
from tkinter import messagebox

from flask import Flask, send_file
from flask_cors import CORS
from controllers.reader import reader_bp
from controllers.book import book_bp
from controllers.borrow import borrow_bp
from controllers.admin import admin_bp
from config import Config, load_config, save_config, get_config_path


def resource_path(relative_path):
    """获取资源文件的绝对路径，兼容 PyInstaller 打包后的 _MEIPASS"""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def test_db_connection(host, user, password, database):
    """测试数据库连接，返回 (成功, 消息)"""
    import pymysql
    try:
        conn = pymysql.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            connect_timeout=5
        )
        conn.close()
        return True, "连接成功！"
    except pymysql.err.OperationalError as e:
        code = e.args[0] if e.args else 0
        if code == 1045:
            return False, "用户名或密码错误"
        elif code == 1049:
            return False, f"数据库「{database}」不存在，请先创建"
        elif code == 2003:
            return False, f"无法连接到 {host}，请检查 MySQL 服务是否启动"
        else:
            return False, f"连接失败：{e}"
    except Exception as e:
        return False, f"连接失败：{e}"


def show_setup_dialog():
    """显示数据库配置对话框，返回 (host, user, password, database) 或 None（用户取消）"""
    root = tk.Tk()
    root.title("图书馆管理系统 - 数据库配置")
    root.resizable(False, False)

    # 居中窗口
    w, h = 420, 280
    ws = root.winfo_screenwidth()
    hs = root.winfo_screenheight()
    x = (ws - w) // 2
    y = (hs - h) // 2
    root.geometry(f"{w}x{h}+{x}+{y}")

    # 标题
    title = tk.Label(root, text="请填写 MySQL 数据库连接信息",
                     font=("Microsoft YaHei", 12, "bold"), pady=10)
    title.grid(row=0, column=0, columnspan=2)

    # 表单字段
    fields = [
        ("主机地址：", "host", Config.MYSQL_HOST),
        ("用户名：",   "user", Config.MYSQL_USER),
        ("密码：",     "password", Config.MYSQL_PASSWORD),
        ("数据库名：",  "database", Config.MYSQL_DB),
    ]

    entries = {}
    for i, (label, key, default) in enumerate(fields):
        tk.Label(root, text=label, font=("Microsoft YaHei", 10),
                 anchor="e", width=10).grid(row=i + 1, column=0, padx=(10, 5), pady=6)
        show = "" if key == "password" else None
        entry = tk.Entry(root, font=("Microsoft YaHei", 10), width=32, show=show)
        entry.insert(0, default)
        entry.grid(row=i + 1, column=1, padx=(5, 10), pady=6)
        entries[key] = entry

    result = {"data": None}

    def on_confirm():
        host = entries["host"].get().strip()
        user = entries["user"].get().strip()
        password = entries["password"].get().strip()
        database = entries["database"].get().strip()

        if not all([host, user, database]):
            messagebox.showwarning("提示", "主机地址、用户名和数据库名不能为空")
            return

        ok, msg = test_db_connection(host, user, password, database)
        if ok:
            messagebox.showinfo("成功", f"✅ {msg}\n\n点击确定启动系统")
            result["data"] = (host, user, password, database)
            root.destroy()
        else:
            messagebox.showerror("连接失败", f"❌ {msg}\n请检查后重试")

    def on_cancel():
        root.destroy()

    # 按钮
    btn_frame = tk.Frame(root)
    btn_frame.grid(row=len(fields) + 1, column=0, columnspan=2, pady=15)

    tk.Button(btn_frame, text="测试连接并启动", font=("Microsoft YaHei", 10),
              bg="#4CAF50", fg="white", width=16, height=1,
              command=on_confirm).pack(side=tk.LEFT, padx=5)
    tk.Button(btn_frame, text="取消", font=("Microsoft YaHei", 10),
              width=10, command=on_cancel).pack(side=tk.LEFT, padx=5)

    root.protocol("WM_DELETE_WINDOW", on_cancel)
    root.mainloop()
    return result["data"]


app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

app.register_blueprint(reader_bp)
app.register_blueprint(book_bp)
app.register_blueprint(borrow_bp)
app.register_blueprint(admin_bp)


@app.route('/ping', methods=['GET'])
def ping():
    return {"msg": "pong"}


@app.route('/')
def home():
    return send_file(resource_path('test_frontend.html'))


if __name__ == '__main__':
    # 1. 尝试加载已保存的配置
    has_config = load_config()

    # 2. 验证已保存的配置是否仍然有效
    if has_config:
        ok, msg = test_db_connection(
            Config.MYSQL_HOST, Config.MYSQL_USER,
            Config.MYSQL_PASSWORD, Config.MYSQL_DB
        )
        if not ok:
            print(f"[!] 已保存的配置连接失败：{msg}")
            print("[!] 将重新打开配置界面...")
            has_config = False

    # 3. 如果没有有效配置，显示配置对话框
    if not has_config:
        print("[*] 正在打开数据库配置界面...")
        credentials = show_setup_dialog()
        if credentials is None:
            print("[!] 用户取消了配置，程序退出")
            sys.exit(0)
        host, user, password, database = credentials
        save_config(host, user, password, database)
        print(f"[✓] 配置已保存至：{get_config_path()}")

    # 4. 自动迁移数据库结构（补齐缺失列、更新存储过程）
    from db import auto_migrate
    auto_migrate()

    # 5. 启动 Flask
    print("=" * 50)
    print("  图书馆管理系统 正在启动...")
    print(f"  数据库：{Config.MYSQL_HOST}/{Config.MYSQL_DB}")
    print("  请打开浏览器访问: http://localhost:5000")
    print("  按 Ctrl+C 可停止服务")
    print("=" * 50)
    webbrowser.open("http://localhost:5000")
    app.run(debug=False, host='0.0.0.0', port=5000)
