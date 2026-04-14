from app import create_app, db
from app.models import HocPhan,     seed_data

app = create_app()

with app.app_context():
    # Tạo tất cả các bảng dựa trên models.py vào file .db trong thư mục instance
    db.create_all()

    # Kiểm tra xem đã có dữ liệu chưa
    if not HocPhan.query.first():
        seed_data(db)

if __name__ == '__main__':
    app.run(debug=True)