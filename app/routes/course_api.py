from flask import Blueprint, jsonify, request, render_template, redirect, url_for, session
from ..models import (
    db, Truong, KhoaVien, NganhHoc, PhienBanCT, HocPhan, KhungChuongTrinh,
    DeCuongChiTiet, ChuanDauRa, KeHoachGiangDay, DanhGiaHocPhan, HocLieu, User
)

course_bp = Blueprint('course', __name__)

# ==============================================================
# AUTHENTICATION ROUTES
# ==============================================================

@course_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        # Tìm user trong database
        user = User.query.filter_by(username=username, password=password).first()

        if user:
            # Lưu thông tin vào session
            session['user_id'] = user.id
            session['username'] = user.username
            session['ho_ten'] = user.ho_ten
            session['vai_tro'] = user.vai_tro
            
            # Redirect dựa trên vai trò
            if user.vai_tro == 'Admin':
                return redirect(url_for('course.admin'))
            else:
                return redirect(url_for('course.home'))
        else:
            return render_template('login.html', error='Tên đăng nhập hoặc mật khẩu không chính xác!')

    return render_template('login.html')


@course_bp.route('/logout', methods=['GET'])
def logout():
    session.clear()
    return redirect(url_for('course.home'))


# ==============================================================
# MAIN ROUTES
# ==============================================================

@course_bp.route('/', methods=['GET'])
def home():
    return render_template('index.html')

def get_pagination_params():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    search_query = request.args.get('q', '')
    cohort = request.args.get('cohort', '')
    return page, limit, search_query, cohort

# API: Schools
@course_bp.route('/api/schools', methods=['GET'])
def get_schools():
    page, limit, q, _ = get_pagination_params()
    query = Truong.query
    if q:
        query = query.filter(Truong.ten_truong.ilike(f'%{q}%') | Truong.ma_truong.ilike(f'%{q}%'))
    
    pagination = query.paginate(page=page, per_page=limit, error_out=False)
    data = [{
        "id": s.id, 
        "ma": s.ma_truong, 
        "ten": s.ten_truong,
        "count_khoa": len(s.khoas)
    } for s in pagination.items]
    
    return jsonify({
        "status": "success",
        "total": pagination.total,
        "pages": pagination.pages,
        "current_page": pagination.page,
        "data": data
    })

# API: Faculties
@course_bp.route('/api/faculties', methods=['GET'])
def get_faculties():
    page, limit, q, _ = get_pagination_params()
    query = KhoaVien.query
    if q:
        query = query.filter(KhoaVien.ten_khoa.ilike(f'%{q}%') | KhoaVien.ma_khoa.ilike(f'%{q}%'))
    
    pagination = query.paginate(page=page, per_page=limit, error_out=False)
    data = [{
        "id": f.id,
        "ma": f.ma_khoa,
        "ten": f.ten_khoa,
        "truong": f.truong.ten_truong if f.truong else "",
        "count_nganh": len(f.nganhs)
    } for f in pagination.items]
    
    return jsonify({
        "status": "success",
        "total": pagination.total,
        "pages": pagination.pages,
        "current_page": pagination.page,
        "data": data
    })

# API: Majors (Ngành/Chương trình)
@course_bp.route('/api/majors', methods=['GET'])
def get_majors():
    page, limit, q, cohort = get_pagination_params()
    query = NganhHoc.query
    
    if q:
        query = query.filter(NganhHoc.ten_nganh.ilike(f'%{q}%') | NganhHoc.ma_nganh.ilike(f'%{q}%'))
    
    if cohort:
        # Lọc theo phiên bản chương trình
        query = query.join(PhienBanCT).filter(PhienBanCT.ma_phien_ban.ilike(f'%{cohort}%'))
    
    pagination = query.paginate(page=page, per_page=limit, error_out=False)
    data = []
    for m in pagination.items:
        # Lấy phiên bản mới nhất hoặc phiên bản khớp với cohort
        pb = next((p for p in m.phien_ban_cts if cohort in p.ma_phien_ban), m.phien_ban_cts[0]) if m.phien_ban_cts else None
        data.append({
            "id": m.id,
            "ma": m.ma_nganh,
            "ten": m.ten_nganh,
            "khoa": m.khoa.ten_khoa if m.khoa else "",
            "phien_ban": pb.ma_phien_ban if pb else "N/A"
        })
    
    return jsonify({
        "status": "success",
        "total": pagination.total,
        "pages": pagination.pages,
        "current_page": pagination.page,
        "data": data
    })

# API: Courses (Học phần)
@course_bp.route('/api/courses', methods=['GET'])
def get_courses():
    page, limit, q, cohort = get_pagination_params()
    query = HocPhan.query
    
    if q:
        query = query.filter(HocPhan.ten_hoc_phan.ilike(f'%{q}%') | HocPhan.ma_hoc_phan.ilike(f'%{q}%'))
    
    if cohort:
        # Học phần thuộc khung chương trình của phiên bản đó
        query = query.join(KhungChuongTrinh).join(PhienBanCT).filter(PhienBanCT.ma_phien_ban.ilike(f'%{cohort}%'))
    
    pagination = query.distinct().paginate(page=page, per_page=limit, error_out=False)
    data = [{
        "id": c.id,
        "ma": c.ma_hoc_phan,
        "ten": c.ten_hoc_phan,
        "tin_chi": c.so_tin_chi,
        "khoa": c.khoa_quan_ly.ten_khoa if c.khoa_quan_ly else ""
    } for c in pagination.items]
    
    return jsonify({
        "status": "success",
        "total": pagination.total,
        "pages": pagination.pages,
        "current_page": pagination.page,
        "data": data
    })

# API: Versions
@course_bp.route('/api/versions', methods=['GET'])
def get_versions():
    versions = PhienBanCT.query.with_entities(PhienBanCT.ma_phien_ban, PhienBanCT.nam_bat_dau).distinct().order_by(PhienBanCT.nam_bat_dau.desc()).all()
    data = [{"ma": v.ma_phien_ban, "nam": v.nam_bat_dau} for v in versions]
    return jsonify({"status": "success", "data": data})


# ==============================================================
# 3. ROUTES CHI TIẾT (DRILL-DOWN)
# ==============================================================

@course_bp.route('/school/<int:id>')
def school_detail(id):
    school = Truong.query.get_or_404(id)
    return render_template('detail.html', type='school', item=school)

@course_bp.route('/faculty/<int:id>')
def faculty_detail(id):
    faculty = KhoaVien.query.get_or_404(id)
    return render_template('detail.html', type='faculty', item=faculty)

@course_bp.route('/major/<int:id>')
def major_detail(id):
    major = NganhHoc.query.get_or_404(id)
    # Lấy phiên bản mặc định (phiên bản đầu tiên)
    version = major.phien_ban_cts[0] if major.phien_ban_cts else None
    return render_template('detail.html', type='major', item=major, version=version)

@course_bp.route('/course/<int:id>')
def course_detail(id):
    course = HocPhan.query.get_or_404(id)
    # Lấy đề cương mới nhất
    syllabus = DeCuongChiTiet.query.filter_by(hoc_phan_id=id).order_by(DeCuongChiTiet.nam_ap_dung.desc()).first()
    return render_template('syllabus.html', course=course, syllabus=syllabus)


# ==============================================================
# ADMIN ROUTES
# ==============================================================

def check_admin():
    """Kiểm tra xem user có phải admin không"""
    if not session.get('user_id') or session.get('vai_tro') != 'Admin':
        return False
    return True


@course_bp.route('/admin', methods=['GET'])
def admin():
    if not check_admin():
        return redirect(url_for('course.login'))
    return render_template('admin_dashboard.html')


@course_bp.route('/admin/schools', methods=['GET'])
def admin_schools():
    if not check_admin():
        return redirect(url_for('course.login'))
    return render_template('admin_schools.html')


@course_bp.route('/admin/schools/create', methods=['GET', 'POST'])
def admin_school_create():
    if not check_admin():
        return redirect(url_for('course.login'))
    
    if request.method == 'POST':
        ma = request.form.get('ma_truong')
        ten = request.form.get('ten_truong')
        
        if not ma or not ten:
            return render_template('admin_school_form.html', error='Vui lòng nhập đầy đủ thông tin')
        
        school = Truong(ma_truong=ma, ten_truong=ten)
        db.session.add(school)
        db.session.commit()
        return redirect(url_for('course.admin_schools'))
    
    return render_template('admin_school_form.html')


@course_bp.route('/admin/schools/<int:id>/edit', methods=['GET', 'POST'])
def admin_school_edit(id):
    if not check_admin():
        return redirect(url_for('course.login'))
    
    school = Truong.query.get_or_404(id)
    
    if request.method == 'POST':
        school.ma_truong = request.form.get('ma_truong', school.ma_truong)
        school.ten_truong = request.form.get('ten_truong', school.ten_truong)
        db.session.commit()
        return redirect(url_for('course.admin_schools'))
    
    return render_template('admin_school_form.html', school=school)


@course_bp.route('/admin/schools/<int:id>', methods=['GET'])
def admin_school_detail(id):
    if not check_admin():
        return redirect(url_for('course.login'))
    
    school = Truong.query.get_or_404(id)
    return render_template('admin_school_detail.html', school=school)


@course_bp.route('/admin/schools/<int:school_id>/faculties/create', methods=['GET', 'POST'])
def admin_faculty_create_in_school(school_id):
    if not check_admin():
        return redirect(url_for('course.login'))
    
    school = Truong.query.get_or_404(school_id)
    
    if request.method == 'POST':
        ma = request.form.get('ma_khoa')
        ten = request.form.get('ten_khoa')
        
        if not ma or not ten:
            return render_template('admin_faculty_form_in_school.html', school=school, error='Vui lòng nhập đầy đủ')
        
        faculty = KhoaVien(truong_id=school_id, ma_khoa=ma, ten_khoa=ten)
        db.session.add(faculty)
        db.session.commit()
        return redirect(url_for('course.admin_school_detail', id=school_id))
    
    return render_template('admin_faculty_form_in_school.html', school=school)


@course_bp.route('/admin/faculties/<int:faculty_id>/edit', methods=['GET', 'POST'])
def admin_faculty_edit(faculty_id):
    if not check_admin():
        return redirect(url_for('course.login'))
    
    faculty = KhoaVien.query.get_or_404(faculty_id)
    
    if request.method == 'POST':
        faculty.ma_khoa = request.form.get('ma_khoa', faculty.ma_khoa)
        faculty.ten_khoa = request.form.get('ten_khoa', faculty.ten_khoa)
        db.session.commit()
        return redirect(url_for('course.admin_school_detail', id=faculty.truong_id))
    
    return render_template('admin_faculty_form_in_school.html', school=faculty.truong, faculty=faculty)


@course_bp.route('/api/admin/stats', methods=['GET'])
def admin_stats():
    if not check_admin():
        return jsonify({"error": "Unauthorized"}), 401
    
    return jsonify({
        "schools": Truong.query.count(),
        "faculties": KhoaVien.query.count(),
        "majors": NganhHoc.query.count(),
        "courses": HocPhan.query.count()
    })


@course_bp.route('/api/admin/schools/<int:id>', methods=['DELETE'])
def admin_delete_school(id):
    if not check_admin():
        return jsonify({"error": "Unauthorized"}), 401
    
    school = Truong.query.get_or_404(id)
    db.session.delete(school)
    db.session.commit()
    return jsonify({"status": "success"})


@course_bp.route('/api/admin/faculties', methods=['GET'])
def admin_list_faculties():
    if not check_admin():
        return jsonify({"error": "Unauthorized"}), 401
    
    page = request.args.get('page', 1, type=int)
    faculties = KhoaVien.query.paginate(page=page, per_page=20, error_out=False)
    
    return jsonify({
        "status": "success",
        "total": faculties.total,
        "pages": faculties.pages,
        "current_page": faculties.page,
        "data": [{
            "id": f.id,
            "ma": f.ma_khoa,
            "ten": f.ten_khoa,
            "truong": f.truong.ten_truong if f.truong else "",
            "count_nganh": len(f.nganhs)
        } for f in faculties.items]
    })


@course_bp.route('/admin/faculties', methods=['GET'])
def admin_faculties():
    if not check_admin():
        return redirect(url_for('course.login'))
    return render_template('admin_faculties.html')


@course_bp.route('/admin/majors', methods=['GET'])
def admin_majors():
    if not check_admin():
        return redirect(url_for('course.login'))
    return render_template('admin_majors.html')


@course_bp.route('/admin/courses', methods=['GET'])
def admin_courses():
    if not check_admin():
        return redirect(url_for('course.login'))
    return render_template('admin_courses.html')


@course_bp.route('/admin/users', methods=['GET'])
def admin_users():
    if not check_admin():
        return redirect(url_for('course.login'))
    
    users = User.query.all()
    return render_template('admin_users.html', users=users)


@course_bp.route('/admin/school/create', methods=['GET'])
def admin_school_create_page():
    if not check_admin():
        return redirect(url_for('course.login'))
    return render_template('admin_school_form.html')


@course_bp.route('/admin/faculty/create', methods=['GET'])
def admin_faculty_create():
    if not check_admin():
        return redirect(url_for('course.login'))
    return render_template('admin_faculty_form.html')


@course_bp.route('/admin/major/create', methods=['GET'])
def admin_major_create():
    if not check_admin():
        return redirect(url_for('course.login'))
    return render_template('admin_major_form.html')


@course_bp.route('/admin/course/create', methods=['GET'])
def admin_course_create():
    if not check_admin():
        return redirect(url_for('course.login'))
    return render_template('admin_course_form.html')


@course_bp.route('/admin/user/create', methods=['GET'])
def admin_user_create():
    if not check_admin():
        return redirect(url_for('course.login'))
    return render_template('admin_user_form.html')


@course_bp.route('/api/admin/faculties/<int:id>', methods=['DELETE'])
def admin_delete_faculty(id):
    if not check_admin():
        return jsonify({"error": "Unauthorized"}), 401
    
    faculty = KhoaVien.query.get_or_404(id)
    db.session.delete(faculty)
    db.session.commit()
    return jsonify({"status": "success"})
