from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Khởi tạo db ở ngay đây để các file khác có thể import được
db = SQLAlchemy()


def create_app():
    app = Flask(__name__)

    # Cấu hình SQLite (Nằm ngay thư mục gốc)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///neu_course.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Cấu hình Session
    app.config['SECRET_KEY'] = 'neu_course_secret_key_2026'  # Thay đổi sang một khóa an toàn hơn trong production
    app.config['SESSION_TYPE'] = 'filesystem'

    # Gắn db vào app
    db.init_app(app)

    # Đăng ký Blueprint để nhận diện các đường dẫn API và giao diện
    with app.app_context():
        from .routes.course_api import course_bp
        app.register_blueprint(course_bp)

    return app