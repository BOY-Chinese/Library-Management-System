from dao import book_dao

#添加书本
def add_book(data):
    if not data.get('图书名'):
        return False,"图书名不能为空"
    if not data.get('类别号'):
        return False,"图书类别不能为空"
    if not data.get('管理员编号'):  
        return False, "管理员编号不能为空"
    
    try:
        book_id=book_dao.insert(data)
        return True,book_id
    except Exception as e:
        return False, f"添加图书失败：{str(e)}"
    
#更新书本
def update_book(book_id,data):
    book=book_dao.find_by_id(book_id)
    if not book:
        return False,"图书不存在"
    if not data:
        return False,"没有需要更新的字段"
    
    try:
        success=book_dao.update(book_id,data)
        if success:
            return True,"更新成功"
        else:
            return False,"更新失败"
    except Exception as e:
        return False,f"更新失败：{str(e)}"

#删除书本
def delete_book(book_id):
    book=book_dao.find_by_id(book_id)
    if not book:
        return False,"图书不存在"
    
    try:
        success=book_dao.delete(book_id)
        if success:
            return True,"删除成功"
        else:
            return False,"删除失败"
    except Exception as e:
        return False, f"删除失败：{str(e)}"
    
# 组合搜索：书名、作者、ISBN、出版社、类别各自独立，AND 组合
def search_books(book_name, author, isbn, publisher, category, page, limit):
    if not page or page<1:
        page=1
    if not limit or limit<1:
        limit=10

    offset=(page-1)*limit
    try:
        books=book_dao.search(book_name, author, isbn, publisher, category, offset, limit)
        total=book_dao.count_search(book_name, author, isbn, publisher, category)
        total_stock=book_dao.sum_stock(book_name, author, isbn, publisher, category)

        return True, {
            "list": books,
            "total": total,
            "total_stock": total_stock,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit if total > 0 else 0
        }
    except Exception as e:
        return False, f"查询失败：{str(e)}"