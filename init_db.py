#!/usr/bin/env python
from app import create_app, db
from app.models import User, HocPhan, seed_data

app = create_app()
with app.app_context():
    db.create_all()
    print('✅ Database created')
    
    if not User.query.first():
        user = User(username='user', password='123456', ho_ten='Người dùng', vai_tro='User')
        admin = User(username='admin', password='123456', ho_ten='Quản trị viên', vai_tro='Admin')
        db.session.add_all([user, admin])
        db.session.commit()
        print('✅ Created user and admin accounts')
    
    if not HocPhan.query.first():
        seed_data(db)
    else:
        print('✅ Database already initialized with sample data')

