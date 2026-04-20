import io
import os
from urllib.parse import quote

from flask import Blueprint, jsonify, request, render_template, redirect, url_for, session, send_file
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
# CONTEXT PROCESSORS
# ==============================================================

@course_bp.app_context_processor
def inject_navbar_data():
    """Cung cấp dữ liệu cho navbar trên tất cả các trang"""
    return dict(
        nav_schools=Truong.query.order_by(Truong.ten_truong.asc()).all(),
        nav_faculties=KhoaVien.query.order_by(KhoaVien.ten_khoa.asc()).all(),
        nav_majors=NganhHoc.query.order_by(NganhHoc.ten_nganh.asc()).all()
    )


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


def _major_versions(major_id):
    return PhienBanCT.query.filter_by(nganh_id=major_id).order_by(PhienBanCT.nam_bat_dau.desc(), PhienBanCT.id.desc()).all()


def _pick_version(major_id, version_code=None):
    versions = _major_versions(major_id)
    if not versions:
        return None, []

    selected = None
    if version_code:
        selected = next((v for v in versions if v.ma_phien_ban == version_code), None)

    if not selected:
        selected = versions[0]

    return selected, versions


def _curriculum_items(version_id):
    return KhungChuongTrinh.query.filter_by(phien_ban_id=version_id).order_by(KhungChuongTrinh.hoc_ky_du_kien.asc()).all()

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


@course_bp.route('/api/major/<int:id>/versions', methods=['GET'])
def get_major_versions(id):
    major = NganhHoc.query.get_or_404(id)
    versions = _major_versions(major.id)
    return jsonify({
        "status": "success",
        "major_id": major.id,
        "data": [{"ma": v.ma_phien_ban, "nam": v.nam_bat_dau} for v in versions]
    })


@course_bp.route('/api/major/<int:id>/compare', methods=['GET'])
def compare_major_versions_api(id):
    default_major = NganhHoc.query.get_or_404(id)
    left_major_id = request.args.get('major_left_id', id, type=int)
    right_major_id = request.args.get('major_right_id', type=int)
    left_code = request.args.get('left', '')
    right_code = request.args.get('right', '')

    left_major = NganhHoc.query.get_or_404(left_major_id)
    right_major = NganhHoc.query.get(right_major_id) if right_major_id else None
    if not right_major:
        right_major = default_major if default_major.id != left_major.id else left_major

    left_version, _ = _pick_version(left_major.id, left_code)
    right_version, _ = _pick_version(right_major.id, right_code)

    if not left_version:
        return jsonify({"status": "error", "message": "Chương trình bên trái chưa có phiên bản"}), 404

    if not right_version:
        return jsonify({"status": "error", "message": "Chương trình bên phải chưa có phiên bản"}), 404

    left_items = _curriculum_items(left_version.id)
    right_items = _curriculum_items(right_version.id)

    left_map = {item.hoc_phan.ma_hoc_phan: item.hoc_phan for item in left_items}
    right_map = {item.hoc_phan.ma_hoc_phan: item.hoc_phan for item in right_items}

    common_codes = sorted(set(left_map.keys()) & set(right_map.keys()))
    left_only_codes = sorted(set(left_map.keys()) - set(right_map.keys()))
    right_only_codes = sorted(set(right_map.keys()) - set(left_map.keys()))

    return jsonify({
        "status": "success",
        "left_major": {"id": left_major.id, "ma": left_major.ma_nganh, "ten": left_major.ten_nganh},
        "right_major": {"id": right_major.id, "ma": right_major.ma_nganh, "ten": right_major.ten_nganh},
        "left_version": {"ma": left_version.ma_phien_ban, "nam": left_version.nam_bat_dau},
        "right_version": {"ma": right_version.ma_phien_ban, "nam": right_version.nam_bat_dau},
        "common": [{"ma": code, "ten": left_map[code].ten_hoc_phan, "tin_chi": left_map[code].so_tin_chi} for code in common_codes],
        "left_only": [{"ma": code, "ten": left_map[code].ten_hoc_phan, "tin_chi": left_map[code].so_tin_chi} for code in left_only_codes],
        "right_only": [{"ma": code, "ten": right_map[code].ten_hoc_phan, "tin_chi": right_map[code].so_tin_chi} for code in right_only_codes]
    })


@course_bp.route('/api/major/<int:id>/share-info', methods=['GET'])
def major_share_info(id):
    major = NganhHoc.query.get_or_404(id)
    version_code = request.args.get('version', '')
    version, _ = _pick_version(major.id, version_code)

    if not version:
        return jsonify({"status": "error", "message": "Ngành chưa có phiên bản chương trình"}), 404

    share_url = url_for('course.major_detail', id=major.id, version=version.ma_phien_ban, _external=True)
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=260x260&data={quote(share_url)}"

    return jsonify({
        "status": "success",
        "share_url": share_url,
        "qr_url": qr_url,
        "version": {"ma": version.ma_phien_ban, "nam": version.nam_bat_dau}
    })


@course_bp.route('/api/favorites/majors', methods=['GET'])
def get_favorite_majors():
    favorites = session.get('favorite_majors', [])
    return jsonify({"status": "success", "data": favorites})


@course_bp.route('/api/favorites/majors', methods=['POST'])
def add_favorite_major():
    payload = request.get_json(silent=True) or {}
    major_id = payload.get('major_id')
    version_code = payload.get('version')

    if not major_id or not version_code:
        return jsonify({"status": "error", "message": "Thiếu major_id hoặc version"}), 400

    major = NganhHoc.query.get_or_404(major_id)
    version = PhienBanCT.query.filter_by(nganh_id=major.id, ma_phien_ban=version_code).first()
    if not version:
        return jsonify({"status": "error", "message": "Phiên bản không hợp lệ"}), 400

    favorites = session.get('favorite_majors', [])
    already_exists = next((x for x in favorites if x.get('major_id') == major.id and x.get('version') == version_code), None)

    if not already_exists:
        favorites.append({
            "major_id": major.id,
            "major_name": major.ten_nganh,
            "major_code": major.ma_nganh,
            "version": version_code
        })
        session['favorite_majors'] = favorites
        session.modified = True
        added = True
    else:
        added = False

    return jsonify({"status": "success", "message": "Đã thêm vào yêu thích", "added": added, "data": favorites})


@course_bp.route('/api/favorites/majors/<int:major_id>', methods=['DELETE'])
def remove_favorite_major(major_id):
    version_code = request.args.get('version', '')
    favorites = session.get('favorite_majors', [])
    next_favorites = [x for x in favorites if not (x.get('major_id') == major_id and x.get('version') == version_code)]
    session['favorite_majors'] = next_favorites
    session.modified = True

    return jsonify({"status": "success", "message": "Đã xóa khỏi yêu thích", "data": next_favorites})


@course_bp.route('/favorites', methods=['GET'])
def favorite_list_page():
    raw_favorites = session.get('favorite_majors', [])
    favorites = []

    for item in raw_favorites:
        major_id = item.get('major_id')
        version_code = item.get('version')
        major = NganhHoc.query.get(major_id)
        if not major:
            continue

        version = PhienBanCT.query.filter_by(nganh_id=major.id, ma_phien_ban=version_code).first()
        if not version:
            continue

        favorites.append({
            "major_id": major.id,
            "major_name": major.ten_nganh,
            "major_code": major.ma_nganh,
            "version": version.ma_phien_ban,
            "year": version.nam_bat_dau
        })

    return render_template('favorites.html', favorites=favorites)


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
    version_code = request.args.get('version', '')
    version, versions = _pick_version(id, version_code)

    if not version:
        return "Chưa có khung chương trình cho ngành này", 404

    curriculum_list = _curriculum_items(version.id)
    favorites = session.get('favorite_majors', [])
    is_favorite = any(x.get('major_id') == major.id and x.get('version') == version.ma_phien_ban for x in favorites)

    total_credits = sum(item.hoc_phan.so_tin_chi for item in curriculum_list)

    return render_template(
        'major_detail.html',
        major=major,
        version=version,
        versions=versions,
        curriculum_list=curriculum_list,
        total_credits=total_credits,
        is_favorite=is_favorite
    )


@course_bp.route('/major/<int:id>/compare', methods=['GET'])
def major_compare_page(id):
    base_major = NganhHoc.query.get_or_404(id)
    left_major_id = request.args.get('major_left_id', id, type=int)
    right_major_id = request.args.get('major_right_id', type=int)
    left_code = request.args.get('left', '')
    right_code = request.args.get('right', '')

    left_major = NganhHoc.query.get_or_404(left_major_id)
    right_major = NganhHoc.query.get(right_major_id) if right_major_id else None
    if not right_major:
        right_major = next((m for m in NganhHoc.query.order_by(NganhHoc.id.asc()).all() if m.id != left_major.id), left_major)

    left_versions = _major_versions(left_major.id)
    right_versions = _major_versions(right_major.id)

    if not left_versions:
        return "Chương trình bên trái chưa có phiên bản để so sánh", 404
    if not right_versions:
        return "Chương trình bên phải chưa có phiên bản để so sánh", 404

    left_version = next((v for v in left_versions if v.ma_phien_ban == left_code), left_versions[0])
    right_version = next((v for v in right_versions if v.ma_phien_ban == right_code), right_versions[0])

    left_items = _curriculum_items(left_version.id)
    right_items = _curriculum_items(right_version.id)

    left_map = {item.hoc_phan.ma_hoc_phan: item.hoc_phan for item in left_items}
    right_map = {item.hoc_phan.ma_hoc_phan: item.hoc_phan for item in right_items}

    common_codes = sorted(set(left_map.keys()) & set(right_map.keys()))
    left_only_codes = sorted(set(left_map.keys()) - set(right_map.keys()))
    right_only_codes = sorted(set(right_map.keys()) - set(left_map.keys()))

    return render_template(
        'major_compare.html',
        major=base_major,
        left_major=left_major,
        right_major=right_major,
        compare_majors=NganhHoc.query.order_by(NganhHoc.ten_nganh.asc()).all(),
        left_versions=left_versions,
        right_versions=right_versions,
        left_version=left_version,
        right_version=right_version,
        common_courses=[left_map[code] for code in common_codes],
        left_only_courses=[left_map[code] for code in left_only_codes],
        right_only_courses=[right_map[code] for code in right_only_codes]
    )


@course_bp.route('/major/<int:id>/pdf', methods=['GET'])
def major_pdf(id):
    major = NganhHoc.query.get_or_404(id)
    version_code = request.args.get('version', '')
    version, _ = _pick_version(major.id, version_code)

    if not version:
        return "Ngành chưa có phiên bản chương trình", 404

    curriculum_list = _curriculum_items(version.id)

    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except Exception:
        return jsonify({
            "status": "error",
            "message": "Thiếu thư viện reportlab. Cài bằng lệnh: pip install reportlab"
        }), 500

    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm
    )

    try:
        font_candidates = [
            'DejaVuSans.ttf',
            'C:/Windows/Fonts/arial.ttf',
            'C:/Windows/Fonts/tahoma.ttf'
        ]
        font_path = next((path for path in font_candidates if os.path.exists(path)), None)
        if font_path:
            pdfmetrics.registerFont(TTFont('AppFont', font_path))
            font_name = 'AppFont'
        else:
            font_name = 'Helvetica'
    except Exception:
        font_name = 'Helvetica'

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontName=font_name, fontSize=14, leading=18)
    text_style = ParagraphStyle('TextStyle', parent=styles['Normal'], fontName=font_name, fontSize=10, leading=13)
    table_text_style = ParagraphStyle('TableTextStyle', parent=styles['Normal'], fontName=font_name, fontSize=9, leading=11)

    table_data = [[
        'STT',
        'Ma HP',
        'Ten hoc phan',
        'Tin chi',
        'Ky',
        'Loai',
        'Khoa/Vien'
    ]]

    total_credits = 0
    for idx, item in enumerate(curriculum_list, start=1):
        total_credits += item.hoc_phan.so_tin_chi
        table_data.append([
            str(idx),
            item.hoc_phan.ma_hoc_phan,
            Paragraph(item.hoc_phan.ten_hoc_phan, table_text_style),
            str(item.hoc_phan.so_tin_chi),
            str(item.hoc_ky_du_kien or ''),
            item.loai_mon or '',
            Paragraph(item.hoc_phan.khoa_quan_ly.ten_khoa if item.hoc_phan.khoa_quan_ly else '', table_text_style)
        ])

    table = Table(
        table_data,
        colWidths=[10 * mm, 20 * mm, 56 * mm, 12 * mm, 10 * mm, 28 * mm, 36 * mm],
        repeatRows=1
    )

    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#085CA7')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTSIZE', (0, 1), (-1, -1), 8.5),
        ('ALIGN', (0, 0), (1, -1), 'CENTER'),
        ('ALIGN', (3, 1), (4, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.HexColor('#F9FCFF')])
    ]))

    story = [
        Paragraph(f'Chuong trinh dao tao: {major.ten_nganh}', title_style),
        Spacer(1, 6),
        Paragraph(f'Ma nganh: {major.ma_nganh}', text_style),
        Paragraph(f'Phien ban: {version.ma_phien_ban} - Nam bat dau: {version.nam_bat_dau}', text_style),
        Paragraph(f'Tong so tin chi: {total_credits}', text_style),
        Spacer(1, 10),
        table
    ]

    doc.build(story)
    pdf_buffer.seek(0)

    filename = f"CTDT_{major.ma_nganh}_{version.ma_phien_ban}.pdf"
    return send_file(pdf_buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')


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
