from flask import Blueprint, jsonify, request, render_template
from app.models import db, Truong, KhoaVien, NganhHoc, PhienBanCT, HocPhan, KhungChuongTrinh, DeCuongChiTiet
from flask import Blueprint, jsonify, request, render_template, redirect, url_for, session
from ..models import (
    db, Truong, KhoaVien, NganhHoc, PhienBanCT, HocPhan, KhungChuongTrinh,
    DeCuongChiTiet, ChuanDauRa, KeHoachGiangDay, DanhGiaHocPhan, HocLieu, User
)
import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load biến môi trường từ file .env
load_dotenv()

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


@course_bp.route('/api/chat', methods=['POST'])
def chat_api():
    data = request.get_json()
    user_message = data.get('message', '').strip()

    if not user_message:
        return jsonify({"reply": "Bạn hãy nhập câu hỏi nhé!"})

    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return jsonify({"reply": "Lỗi hệ thống: Chưa cấu hình API."})

        genai.configure(api_key=api_key)
        # Vẫn dùng bản Flash Lite cho nhẹ và an toàn với tài khoản Free
        model = genai.GenerativeModel('gemini-flash-lite-latest')

        # 1. Lấy dữ liệu tổng quan chung (Bảng Truong, KhoaVien, NganhHoc)
        so_truong = Truong.query.count()
        so_khoa = KhoaVien.query.count()
        so_nganh = NganhHoc.query.count()

        # =================================================================
        # 2. SMART ROUTER: RÚT TRÍCH DỮ LIỆU TỪ 11 BẢNG DỰA THEO CÂU HỎI
        # =================================================================
        thong_tin_db = ""
        user_msg_lower = user_message.lower()

        # TRƯỜNG HỢP A: User hỏi về NGÀNH HỌC (Liên kết bảng NganhHoc, PhienBanCT, KhungChuongTrinh)
        for nganh in NganhHoc.query.all():
            if nganh.ten_nganh.lower() in user_msg_lower:
                thong_tin_db += f"\n[THÔNG TIN NGÀNH HỌC]\n- Tên ngành: {nganh.ten_nganh} (Mã: {nganh.ma_nganh}, Thuộc {nganh.khoa.ten_khoa})\n"
                # Tìm Khung chương trình của ngành này
                phien_ban = PhienBanCT.query.filter_by(nganh_id=nganh.id).first()
                if phien_ban:
                    so_mon_hoc = KhungChuongTrinh.query.filter_by(phien_ban_id=phien_ban.id).count()
                    thong_tin_db += f"- Phiên bản đào tạo: {phien_ban.ma_phien_ban} ({phien_ban.nam_bat_dau})\n"
                    thong_tin_db += f"- Tổng số môn phải học: {so_mon_hoc} môn.\n"
                break  # Tìm thấy 1 ngành khớp là dừng

        # TRƯỜNG HỢP B: User hỏi về MÔN HỌC (Liên kết bảng HocPhan, DeCuong, DanhGia, HocLieu, ChuanDauRa)
        for mon in HocPhan.query.all():
            if mon.ten_hoc_phan.lower() in user_msg_lower or mon.ma_hoc_phan.lower() in user_msg_lower:
                thong_tin_db += f"\n[THÔNG TIN MÔN HỌC]\n- Môn: {mon.ten_hoc_phan} (Mã: {mon.ma_hoc_phan})\n"
                thong_tin_db += f"- Số tín chỉ: {mon.so_tin_chi}\n"

                # Tìm Đề cương chi tiết
                de_cuong = DeCuongChiTiet.query.filter_by(hoc_phan_id=mon.id).first()
                if de_cuong:
                    # Rút bảng Đánh giá
                    danh_gia = DanhGiaHocPhan.query.filter_by(de_cuong_id=de_cuong.id).all()
                    if danh_gia:
                        thong_tin_db += "- Điểm đánh giá: " + ", ".join(
                            [f"{dg.thanh_phan} ({int(dg.trong_so * 100)}%)" for dg in danh_gia]) + "\n"

                    # Rút bảng Học liệu
                    hoc_lieu = HocLieu.query.filter_by(de_cuong_id=de_cuong.id).all()
                    if hoc_lieu:
                        thong_tin_db += "- Giáo trình/Tài liệu: " + ", ".join(
                            [hl.ten_tai_lieu for hl in hoc_lieu]) + "\n"

                    # Rút bảng Chuẩn đầu ra (CLO)
                    clo = ChuanDauRa.query.filter_by(de_cuong_id=de_cuong.id).all()
                    if clo:
                        thong_tin_db += "- Mục tiêu môn học: " + " và ".join([c.mo_ta for c in clo]) + "\n"
                break  # Tìm thấy 1 môn khớp là dừng
        dinh_huong = {
            "web": ["lập trình", "web", "phần mềm", "cơ sở dữ liệu", "hệ thống thông tin"],
            "cloud": ["mạng", "bảo mật", "hệ điều hành", "đám mây", "an toàn", "nhúng"],
            "data": ["dữ liệu", "thống kê", "ai", "trí tuệ nhân tạo", "machine", "toán"],
            "marketing": ["marketing", "thương hiệu", "hành vi", "khách hàng", "pr", "thị trường"]
        }

        is_career_question = False
        for nghe, tu_khoa_list in dinh_huong.items():
            if nghe in user_msg_lower or "lộ trình" in user_msg_lower or "định hướng" in user_msg_lower:
                is_career_question = True
                thong_tin_db += f"\n[CÁC MÔN HỌC TRONG TRƯỜNG PHÙ HỢP VỚI NGHỀ NÀY]\n"

                # Quét tất cả môn học, môn nào có tên chứa từ khóa thì gom lại
                mon_goi_y = []
                for mon in HocPhan.query.all():
                    if any(tk in mon.ten_hoc_phan.lower() for tk in tu_khoa_list):
                        mon_goi_y.append(f"- {mon.ten_hoc_phan} ({mon.so_tin_chi} TC)")

                # Lấy tối đa 10 môn để AI không bị ngợp
                thong_tin_db += "\n".join(mon_goi_y[:10]) + "\n"
                break

        for truong in Truong.query.all():
            if truong.ten_truong.lower() in user_msg_lower and truong.ma_truong != "NEU_BASE":
                so_khoa_truong_nay = len(truong.khoas)
                thong_tin_db += f"\n[THÔNG TIN CHI TIẾT TRƯỜNG: {truong.ten_truong}]\n"
                thong_tin_db += f"- Số lượng Khoa/Viện trực thuộc: {so_khoa_truong_nay}\n"

                # Liệt kê luôn tên các khoa cho AI biết đường mà kể
                ten_cac_khoa = [k.ten_khoa for k in truong.khoas]
                thong_tin_db += f"- Danh sách gồm: {', '.join(ten_cac_khoa)}\n"
                break

        # =================================================================
        # 3. TIÊM TOÀN BỘ VÀO PROMPT CHO AI XỬ LÝ
        # =================================================================
        prompt = f"""
        Bạn là "NEU Assistant", trợ lý ảo tư vấn học tập của hệ thống NEU Course.

        [DỮ LIỆU TỔNG QUAN]
        - Trường có {so_truong} khối/trường, {so_khoa} khoa/viện, {so_nganh} ngành đào tạo.

        [DỮ LIỆU CHI TIẾT TRÍCH XUẤT TỪ DATABASE CHÍNH XÁC 100%]
        Hãy dùng Dữ liệu dưới đây để trả lời. Nếu trống, nghĩa là hệ thống chưa có thông tin chi tiết.
        {thong_tin_db}

        [QUY TẮC CỐT LÕI]
        1. Xưng "mình", gọi "bạn". Trả lời thân thiện, năng động.
        2. NẾU USER HỎI VỀ ĐỊNH HƯỚNG/LỘ TRÌNH (như Web, Cloud, Data...):
           - Hãy sử dụng CÁC MÔN HỌC TRONG TRƯỜNG ở mục Dữ liệu chi tiết để vẽ ra lộ trình.
           - Sắp xếp logic theo: Cơ bản -> Chuyên sâu -> Kỹ năng bổ trợ.
           - KHÔNG tự bịa ra môn học mà trường không dạy. Trình bày dạng danh sách (bullet points) cho dễ nhìn.
        3. Nếu user hỏi thông tin tra cứu thông thường, trả lời cực kỳ ngắn gọn (2-3 câu).
        Câu hỏi của sinh viên: {user_message}
        """

        response = model.generate_content(prompt)
        reply = response.text.replace('**', '<b>').replace('*', '<br>-')

    except Exception as e:
        print(f"Lỗi AI: {e}")
        reply = "Hệ thống AI đang bảo trì. Bạn đợi chút rồi hỏi lại nhé!"

    return jsonify({"reply": reply})