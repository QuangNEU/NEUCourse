from flask import Blueprint, jsonify, request, render_template
from app.models import db, Truong, KhoaVien, NganhHoc, PhienBanCT, HocPhan

# Khởi tạo Blueprint (Nhóm các đường dẫn lại với nhau)
course_bp = Blueprint('course', __name__)


# ==============================================================
# 1. ROUTE GIAO DIỆN: Trả về trang chủ HTML
# ==============================================================
@course_bp.route('/', methods=['GET'])
def home():
    # Gọi file index.html trong thư mục templates
    return render_template('index.html')


# ==============================================================
# 2. CÁC API TRẢ VỀ DỮ LIỆU JSON (Dành cho 4 Tab ở Frontend)
# ==============================================================

# API: Lấy danh sách TRƯỜNG (Tab 4)
@course_bp.route('/api/schools', methods=['GET'])
def get_schools():
    schools = Truong.query.all()
    data = [
        {"id": s.id, "ma_truong": s.ma_truong, "ten_truong": s.ten_truong}
        for s in schools
    ]
    return jsonify({"status": "success", "data": data})


# API: Lấy danh sách KHOA / VIỆN (Tab 3)
@course_bp.route('/api/faculties', methods=['GET'])
def get_faculties():
    faculties = KhoaVien.query.all()
    data = [{
        "id": f.id,
        "ma_khoa": f.ma_khoa,
        "ten_khoa": f.ten_khoa,
        # Lấy thêm tên trường chủ quản nhờ Relationship đã setup trong models
        "thuoc_truong": f.truong.ten_truong if f.truong else "Khác"
    } for f in faculties]
    return jsonify({"status": "success", "data": data})


# API: Lấy danh sách NGÀNH HỌC (Tab 1 - Mặc định)
@course_bp.route('/api/majors', methods=['GET'])
def get_majors():
    majors = NganhHoc.query.all()
    data = [{
        "id": m.id,
        "ma_nganh": m.ma_nganh,
        "ten_nganh": m.ten_nganh,
        "khoa_vien": m.khoa.ten_khoa if m.khoa else ""
    } for m in majors]
    return jsonify({"status": "success", "data": data})


# API: Lấy danh sách HỌC PHẦN (Tab 2) - CÓ HỖ TRỢ TÌM KIẾM
@course_bp.route('/api/courses', methods=['GET'])
def get_courses():
    # Lấy từ khóa tìm kiếm từ URL (VD: /api/courses?q=IT)
    search_query = request.args.get('q', '')

    query = HocPhan.query

    # Nếu người dùng có gõ tìm kiếm
    if search_query:
        # Tìm gần đúng (LIKE) trong cột Mã môn hoặc Tên môn
        query = query.filter(
            (HocPhan.ma_hoc_phan.ilike(f'%{search_query}%')) |
            (HocPhan.ten_hoc_phan.ilike(f'%{search_query}%'))
        )

    courses = query.all()
    data = [{
        "id": c.id,
        "ma_hoc_phan": c.ma_hoc_phan,
        "ten_hoc_phan": c.ten_hoc_phan,
        "so_tin_chi": c.so_tin_chi,
        "khoa_quan_ly": c.khoa_quan_ly.ten_khoa if c.khoa_quan_ly else ""
    } for c in courses]

    return jsonify({"status": "success", "total": len(data), "data": data})


# API: Lấy danh sách PHIÊN BẢN (Dành cho ô Dropdown góc phải)
@course_bp.route('/api/versions', methods=['GET'])
def get_versions():
    # Lấy các mã phiên bản không trùng lặp (distinct)
    versions = PhienBanCT.query.with_entities(PhienBanCT.ma_phien_ban, PhienBanCT.nam_bat_dau).distinct().all()
    data = [{"ma_phien_ban": v.ma_phien_ban, "nam_bat_dau": v.nam_bat_dau} for v in versions]
    return jsonify({"status": "success", "data": data})