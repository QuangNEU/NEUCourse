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
    # Lấy thông tin ngành
    major = NganhHoc.query.get_or_404(id)

    # Lấy phiên bản chương trình đào tạo
    version = PhienBanCT.query.filter_by(nganh_id=id).first()

    if not version:
        return "Chưa có khung chương trình cho ngành này", 404

    # Lấy danh sách khung chương trình
    curriculum_list = KhungChuongTrinh.query.filter_by(phien_ban_id=version.id) \
        .order_by(KhungChuongTrinh.hoc_ky_du_kien.asc()) \
        .all()

    # Tính tổng số tín chỉ
    total_credits = sum(item.hoc_phan.so_tin_chi for item in curriculum_list)

    # Đổi tên file giao diện thành major_detail.html cho đồng bộ
    return render_template(
        'major_detail.html',
        major=major,
        version=version,
        curriculum_list=curriculum_list,
        total_credits=total_credits
    )
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
        faculty_id = request.form.get('faculty_id')
        
        if not faculty_id:
            # Get all available faculties not in this school
            all_faculties = KhoaVien.query.filter(KhoaVien.truong_id != school_id).all()
            return render_template('admin_faculty_form_in_school.html', school=school, faculties=all_faculties, error='Vui lòng chọn Khoa/Viện')
        
        faculty = KhoaVien.query.get_or_404(faculty_id)
        faculty.truong_id = school_id
        db.session.commit()
        return redirect(url_for('course.admin_school_detail', id=school_id))
    
    # Get all available faculties not in this school
    all_faculties = KhoaVien.query.filter(KhoaVien.truong_id != school_id).all()
    return render_template('admin_faculty_form_in_school.html', school=school, faculties=all_faculties)


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
    
    # Get all available faculties not in this school for edit mode
    all_faculties = KhoaVien.query.filter(KhoaVien.truong_id != faculty.truong_id).all()
    return render_template('admin_faculty_form_in_school.html', school=faculty.truong, faculty=faculty, faculties=all_faculties)


@course_bp.route('/admin/majors/<int:major_id>', methods=['GET', 'POST'])
def admin_major_detail(major_id):
    if not check_admin():
        return redirect(url_for('course.login'))

    major = NganhHoc.query.get_or_404(major_id)
    
    # Handle POST request (form submission)
    if request.method == 'POST':
        major.ma_nganh = request.form.get('ma_nganh', major.ma_nganh).strip()
        major.ten_nganh = request.form.get('ten_nganh', major.ten_nganh).strip()
        khoa_id = request.form.get('khoa_id')
        
        if not major.ma_nganh or not major.ten_nganh or not khoa_id:
            return render_template('admin_major_detail.html', major=major, 
                                 error='Vui lòng nhập đầy đủ thông tin')
        
        try:
            major.khoa_id = int(khoa_id)
            db.session.commit()
        except Exception:
            db.session.rollback()
            return render_template('admin_major_detail.html', major=major, 
                                 error='Lỗi khi cập nhật ngành')

    # Get version - either from query param or first available
    version_id = request.args.get('version_id', type=int)
    
    if version_id:
        version = PhienBanCT.query.filter_by(id=version_id, nganh_id=major_id).first()
    else:
        version = PhienBanCT.query.filter_by(nganh_id=major_id).first()

    curriculum_list = []
    total_credits = 0
    
    if version:
        curriculum_list = KhungChuongTrinh.query.filter_by(phien_ban_id=version.id) \
            .order_by(KhungChuongTrinh.hoc_ky_du_kien.asc()) \
            .all()
        total_credits = sum(item.hoc_phan.so_tin_chi for item in curriculum_list)

    return render_template('admin_major_detail.html', major=major, version=version, 
                         curriculum_list=curriculum_list, total_credits=total_credits)


@course_bp.route('/admin/faculties/<int:faculty_id>/majors/create', methods=['GET', 'POST'])
def admin_faculty_major_create(faculty_id):
    if not check_admin():
        return redirect(url_for('course.login'))

    faculty = KhoaVien.query.get_or_404(faculty_id)

    if request.method == 'POST':
        major_id = request.form.get('major_id', '').strip()

        if not major_id:
            # Get all available majors not in this faculty
            all_majors = NganhHoc.query.filter(NganhHoc.khoa_id != faculty_id).all()
            return render_template(
                'admin_major_form_in_faculty.html',
                school=faculty.truong,
                faculty=faculty,
                majors=all_majors,
                error='Vui lòng chọn ngành học'
            )

        try:
            major = NganhHoc.query.get_or_404(major_id)
            major.khoa_id = faculty_id
            db.session.commit()
            return redirect(url_for('course.admin_faculty_detail', faculty_id=faculty_id))
        except Exception:
            db.session.rollback()
            all_majors = NganhHoc.query.filter(NganhHoc.khoa_id != faculty_id).all()
            return render_template(
                'admin_major_form_in_faculty.html',
                school=faculty.truong,
                faculty=faculty,
                majors=all_majors,
                error='Lỗi khi thêm ngành'
            )

    # Get all available majors not in this faculty
    all_majors = NganhHoc.query.filter(NganhHoc.khoa_id != faculty_id).all()
    return render_template('admin_major_form_in_faculty.html', school=faculty.truong, faculty=faculty, majors=all_majors)


@course_bp.route('/admin/major/create', methods=['GET', 'POST'])
def admin_major_create():
    if not check_admin():
        return redirect(url_for('course.login'))

    if request.method == 'POST':
        ma = request.form.get('ma_nganh', '').strip()
        ten = request.form.get('ten_nganh', '').strip()
        khoa_id = request.form.get('khoa_id')

        if not ma or not ten or not khoa_id:
            return render_template('admin_major_form.html', error='Vui lòng nhập đầy đủ thông tin')

        try:
            major = NganhHoc(khoa_id=int(khoa_id), ma_nganh=ma, ten_nganh=ten)
            db.session.add(major)
            db.session.commit()
            return redirect(url_for('course.admin_faculty_detail', faculty_id=int(khoa_id)))
        except Exception:
            db.session.rollback()
            return render_template('admin_major_form.html', error='Lỗi khi tạo ngành hoặc mã ngành đã tồn tại')

    return render_template('admin_major_form.html')


@course_bp.route('/admin/majors/<int:major_id>/edit', methods=['GET', 'POST'])
def admin_major_edit(major_id):
    if not check_admin():
        return redirect(url_for('course.login'))

    # Redirect to detail page (which now has the form integrated)
    version_id = request.args.get('version_id')
    if version_id:
        return redirect(url_for('course.admin_major_detail', major_id=major_id, version_id=version_id))
    return redirect(url_for('course.admin_major_detail', major_id=major_id))


@course_bp.route('/api/admin/majors/<int:id>', methods=['DELETE'])
def admin_delete_major(id):
    if not check_admin():
        return jsonify({"error": "Unauthorized"}), 401

    major = NganhHoc.query.get_or_404(id)

    try:
        # Xóa các phiên bản CT và khung chương trình liên quan trước
        for version in list(major.phien_ban_cts):
            KhungChuongTrinh.query.filter_by(phien_ban_id=version.id).delete(synchronize_session=False)
            db.session.delete(version)

        faculty_id = major.khoa_id
        db.session.delete(major)
        db.session.commit()
        return jsonify({"status": "success", "faculty_id": faculty_id})
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Không thể xóa ngành"}), 400


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


@course_bp.route('/admin/faculty/create', methods=['GET', 'POST'])
def admin_faculty_create_form():
    if not check_admin():
        return redirect(url_for('course.login'))
    
    if request.method == 'POST':
        ma = request.form.get('ma_khoa')
        ten = request.form.get('ten_khoa')
        truong_id = request.form.get('truong_id')
        
        if not ma or not ten or not truong_id:
            return render_template('admin_faculty_create_form.html', error='Vui lòng nhập đầy đủ thông tin')
        
        try:
            faculty = KhoaVien(truong_id=int(truong_id), ma_khoa=ma, ten_khoa=ten)
            db.session.add(faculty)
            db.session.commit()
            return redirect(url_for('course.admin_faculties'))
        except:
            return render_template('admin_faculty_create_form.html', error='Lỗi khi tạo Khoa/Viện')
    
    schools = Truong.query.all()
    return render_template('admin_faculty_create_form.html', schools=schools)


@course_bp.route('/admin/major/create-page', methods=['GET'])
def admin_major_create_page():
  if not check_admin():
    return redirect(url_for('course.login'))
  return redirect(url_for('course.admin_major_create'))


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


@course_bp.route('/api/admin/versions/major/<int:major_id>', methods=['GET'])
def admin_get_versions(major_id):
    if not check_admin():
        return jsonify({"error": "Unauthorized"}), 401
    
    versions = PhienBanCT.query.filter_by(nganh_id=major_id).all()
    data = [{
        "id": v.id,
        "ma_phien_ban": v.ma_phien_ban,
        "nam_bat_dau": v.nam_bat_dau
    } for v in versions]
    
    return jsonify({"status": "success", "data": data})


@course_bp.route('/api/admin/versions', methods=['POST'])
def admin_create_version():
    if not check_admin():
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        data = request.get_json()
        nganh_id = data.get('nganh_id')
        ma_phien_ban = data.get('ma_phien_ban', '').strip()
        nam_bat_dau = data.get('nam_bat_dau')
        
        if not ma_phien_ban or not nam_bat_dau:
            return jsonify({"error": "Thiếu mã phiên bản hoặc năm"}), 400
        
        # Check if version already exists
        existing = PhienBanCT.query.filter_by(
            nganh_id=int(nganh_id),
            ma_phien_ban=ma_phien_ban
        ).first()
        
        if existing:
            return jsonify({"error": "Phiên bản này đã tồn tại"}), 400
        
        version = PhienBanCT(
            nganh_id=int(nganh_id),
            ma_phien_ban=ma_phien_ban,
            nam_bat_dau=int(nam_bat_dau)
        )
        db.session.add(version)
        db.session.commit()
        return jsonify({"status": "success", "data": {
            "id": version.id,
            "ma_phien_ban": version.ma_phien_ban,
            "nam_bat_dau": version.nam_bat_dau
        }})
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Lỗi: {str(e)}"}), 400


@course_bp.route('/api/admin/courses/available', methods=['GET'])
def admin_get_available_courses():
    if not check_admin():
        return jsonify({"error": "Unauthorized"}), 401
    
    major_id = request.args.get('major_id', type=int)
    version_id = request.args.get('version_id', type=int)
    
    # Lấy danh sách học phần chưa được thêm vào phiên bản này
    existing = db.session.query(KhungChuongTrinh.hoc_phan_id).filter_by(phien_ban_id=version_id).all()
    existing_ids = [e[0] for e in existing]
    
    # Lấy tất cả học phần trừ những cái đã có
    if existing_ids:
        courses = HocPhan.query.filter(HocPhan.id.notin_(existing_ids)).all()
    else:
        courses = HocPhan.query.all()
    
    data = [{
        "id": c.id,
        "ma": c.ma_hoc_phan,
        "ten": c.ten_hoc_phan,
        "tin_chi": c.so_tin_chi,
        "khoa": c.khoa_quan_ly.ten_khoa if c.khoa_quan_ly else ""
    } for c in courses]
    
    return jsonify({"status": "success", "data": data})


@course_bp.route('/api/admin/curriculum', methods=['POST'])
def admin_add_curriculum():
    if not check_admin():
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        data = request.get_json()
        phien_ban_id = data.get('phien_ban_id')
        hoc_phan_id = data.get('hoc_phan_id')
        hoc_ky = data.get('hoc_ky', 1)
        loai_mon = data.get('loai_mon', 'Bắt buộc')
        
        if not phien_ban_id or not hoc_phan_id:
            return jsonify({"error": "Thiếu phiên bản hoặc học phần"}), 400
        
        # Check if already exists
        existing = KhungChuongTrinh.query.filter_by(
            phien_ban_id=int(phien_ban_id),
            hoc_phan_id=int(hoc_phan_id)
        ).first()
        
        if existing:
            return jsonify({"error": "Học phần này đã có trong phiên bản này"}), 400
        
        curriculum = KhungChuongTrinh(
            phien_ban_id=int(phien_ban_id),
            hoc_phan_id=int(hoc_phan_id),
            hoc_ky_du_kien=int(hoc_ky),
            loai_mon=loai_mon
        )
        db.session.add(curriculum)
        db.session.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Lỗi: {str(e)}"}), 400


@course_bp.route('/api/admin/curriculum/<int:phien_ban_id>/<int:hoc_phan_id>', methods=['DELETE'])
def admin_delete_curriculum(phien_ban_id, hoc_phan_id):
    if not check_admin():
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        curriculum = KhungChuongTrinh.query.filter_by(
            phien_ban_id=phien_ban_id,
            hoc_phan_id=hoc_phan_id
        ).first()
        
        if not curriculum:
            return jsonify({"error": "Không tìm thấy"}), 404
            
        db.session.delete(curriculum)
        db.session.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
