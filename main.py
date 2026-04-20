from app import create_app, db
from app.models import HocPhan, User, seed_data

app = create_app()

with app.app_context():
    # Tạo tất cả các bảng dựa trên models.py vào file .db trong thư mục instance
    db.create_all()

    # Tạo 2 tài khoản mẫu nếu chưa tồn tại
    if not User.query.first():
        user_account = User(username='user', password='123456', ho_ten='Người dùng', vai_tro='User')
        admin_account = User(username='admin', password='123456', ho_ten='Quản trị viên', vai_tro='Admin')
        db.session.add_all([user_account, admin_account])
        db.session.commit()
        print("✅ Đã tạo 2 tài khoản: user (123456) và admin (123456)")

    # Kiểm tra xem đã có dữ liệu chưa
    if not HocPhan.query.first():
        seed_data(db)

if __name__ == '__main__':
    app.run(debug=True)