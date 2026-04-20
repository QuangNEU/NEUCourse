from . import db
from datetime import datetime


# 1. QUẢN LÝ HÀNH CHÍNH
class Truong(db.Model):
    __tablename__ = 'truong'
    id = db.Column(db.Integer, primary_key=True)
    ma_truong = db.Column(db.String(20), unique=True, nullable=False)
    ten_truong = db.Column(db.String(255), nullable=False)
    khoas = db.relationship('KhoaVien', backref='truong', lazy=True)


class KhoaVien(db.Model):
    __tablename__ = 'khoa_vien'
    id = db.Column(db.Integer, primary_key=True)
    truong_id = db.Column(db.Integer, db.ForeignKey('truong.id'), nullable=False)
    ma_khoa = db.Column(db.String(20), unique=True, nullable=False)
    ten_khoa = db.Column(db.String(255), nullable=False)
    nganhs = db.relationship('NganhHoc', backref='khoa', lazy=True)
    hoc_phans = db.relationship('HocPhan', backref='khoa_quan_ly', lazy=True)


class NganhHoc(db.Model):
    __tablename__ = 'nganh_hoc'
    id = db.Column(db.Integer, primary_key=True)
    khoa_id = db.Column(db.Integer, db.ForeignKey('khoa_vien.id'), nullable=False)
    ma_nganh = db.Column(db.String(20), unique=True, nullable=False)
    ten_nganh = db.Column(db.String(255), nullable=False)
    phien_ban_cts = db.relationship('PhienBanCT', backref='nganh', lazy=True)


# 2. KHUNG CHƯƠNG TRÌNH ĐÀO TẠO
class PhienBanCT(db.Model):
    __tablename__ = 'phien_ban_ct'
    id = db.Column(db.Integer, primary_key=True)
    nganh_id = db.Column(db.Integer, db.ForeignKey('nganh_hoc.id'), nullable=False)
    ma_phien_ban = db.Column(db.String(50), nullable=False)  # VD: K66_KHMT
    nam_bat_dau = db.Column(db.Integer)
    khung_chuong_trinhs = db.relationship('KhungChuongTrinh', backref='phien_ban', lazy=True)


class KhungChuongTrinh(db.Model):
    __tablename__ = 'khung_chuong_trinh'
    phien_ban_id = db.Column(db.Integer, db.ForeignKey('phien_ban_ct.id'), primary_key=True)
    hoc_phan_id = db.Column(db.Integer, db.ForeignKey('hoc_phan.id'), primary_key=True)
    hoc_ky_du_kien = db.Column(db.Integer)
    loai_mon = db.Column(db.String(50))  # Bắt buộc / Tự chọn

    hoc_phan = db.relationship('HocPhan', backref='khung_chuong_trinhs', lazy=True)


# 3. HỌC PHẦN VÀ ĐỀ CƯƠNG CHI TIẾT
class HocPhan(db.Model):
    __tablename__ = 'hoc_phan'
    id = db.Column(db.Integer, primary_key=True)
    khoa_quan_ly_id = db.Column(db.Integer, db.ForeignKey('khoa_vien.id'), nullable=False)
    ma_hoc_phan = db.Column(db.String(20), unique=True, nullable=False)
    ten_hoc_phan = db.Column(db.String(255), nullable=False)
    so_tin_chi = db.Column(db.Integer, nullable=False)
    de_cuongs = db.relationship('DeCuongChiTiet', backref='hoc_phan', lazy=True)


class DeCuongChiTiet(db.Model):
    __tablename__ = 'de_cuong_chi_tiet'
    id = db.Column(db.Integer, primary_key=True)
    hoc_phan_id = db.Column(db.Integer, db.ForeignKey('hoc_phan.id'), nullable=False)
    nam_ap_dung = db.Column(db.String(50), nullable=False)
    trang_thai = db.Column(db.String(20), default='Published')

    clos = db.relationship('ChuanDauRa', backref='de_cuong', lazy=True)
    lich_trinh = db.relationship('KeHoachGiangDay', backref='de_cuong', lazy=True)
    danh_gia = db.relationship('DanhGiaHocPhan', backref='de_cuong', lazy=True)
    hoc_lieu = db.relationship('HocLieu', backref='de_cuong', lazy=True)


# 4. CHI TIẾT NỘI DUNG ĐỀ CƯƠNG
class ChuanDauRa(db.Model):
    __tablename__ = 'chuan_dau_ra'
    id = db.Column(db.Integer, primary_key=True)
    de_cuong_id = db.Column(db.Integer, db.ForeignKey('de_cuong_chi_tiet.id'), nullable=False)
    ma_clo = db.Column(db.String(10))
    mo_ta = db.Column(db.Text)


class KeHoachGiangDay(db.Model):
    __tablename__ = 'ke_hoach_giang_day'
    id = db.Column(db.Integer, primary_key=True)
    de_cuong_id = db.Column(db.Integer, db.ForeignKey('de_cuong_chi_tiet.id'), nullable=False)
    tuan_thu = db.Column(db.Integer)
    chu_de_bai_hoc = db.Column(db.String(255))
    noi_dung_chi_tiet = db.Column(db.Text)


class DanhGiaHocPhan(db.Model):
    __tablename__ = 'danh_gia_hoc_phan'
    id = db.Column(db.Integer, primary_key=True)
    de_cuong_id = db.Column(db.Integer, db.ForeignKey('de_cuong_chi_tiet.id'), nullable=False)
    thanh_phan = db.Column(db.String(100))  # Giữa kỳ, Cuối kỳ
    trong_so = db.Column(db.Float)
    hinh_thuc = db.Column(db.String(255))


class HocLieu(db.Model):
    __tablename__ = 'hoc_lieu'
    id = db.Column(db.Integer, primary_key=True)
    de_cuong_id = db.Column(db.Integer, db.ForeignKey('de_cuong_chi_tiet.id'), nullable=False)
    loai = db.Column(db.String(50))
    ten_tai_lieu = db.Column(db.String(255))
    tac_gia = db.Column(db.String(255))


def seed_data(db):
    print("⏳ Bắt đầu tạo dữ liệu mẫu với cấu trúc 3 Trường của NEU...")

    # ---------------------------------------------------------
    # 1. TẠO 3 TRƯỜNG TRỰC THUỘC (CẤP CAO NHẤT)
    # ---------------------------------------------------------
    truong_cong_nghe = Truong(ma_truong="SOT", ten_truong="Trường Công nghệ")
    truong_kinh_doanh = Truong(ma_truong="SOB", ten_truong="Trường Kinh doanh")
    truong_kinh_te = Truong(ma_truong="SOE", ten_truong="Trường Kinh tế và Quản lý công")

    db.session.add_all([truong_cong_nghe, truong_kinh_doanh, truong_kinh_te])
    db.session.flush()  # Lưu tạm để lấy ID

    # ---------------------------------------------------------
    # 2. TẠO KHOA/VIÊN TRỰC THUỘC CÁC TRƯỜNG
    # ---------------------------------------------------------
    # Thuộc Trường Công nghệ
    vien_cntt = KhoaVien(truong=truong_cong_nghe, ma_khoa="CNTT", ten_khoa="Viện Công nghệ thông tin và Kinh tế số")
    khoa_toan = KhoaVien(truong=truong_cong_nghe, ma_khoa="TKT", ten_khoa="Khoa Toán kinh tế")

    # Thuộc Trường Kinh doanh
    khoa_qtkd = KhoaVien(truong=truong_kinh_doanh, ma_khoa="QTKD", ten_khoa="Khoa Quản trị kinh doanh")
    vien_ketoan = KhoaVien(truong=truong_kinh_doanh, ma_khoa="KTKT", ten_khoa="Viện Kế toán - Kiểm toán")

    # Thuộc Trường Kinh tế
    khoa_kth = KhoaVien(truong=truong_kinh_te, ma_khoa="KTH", ten_khoa="Khoa Kinh tế học")

    db.session.add_all([vien_cntt, khoa_toan, khoa_qtkd, vien_ketoan, khoa_kth])
    db.session.flush()

    # ---------------------------------------------------------
    # 3. TẠO NGÀNH & PHIÊN BẢN CHƯƠNG TRÌNH ĐÀO TẠO
    # ---------------------------------------------------------
    # Ngành Khoa học máy tính (Của Viện CNTT - Trường Công nghệ)
    nganh_khmt = NganhHoc(khoa=vien_cntt, ma_nganh="7480101", ten_nganh="Khoa học máy tính")
    phien_ban_khmt_k66 = PhienBanCT(nganh=nganh_khmt, ma_phien_ban="K66_KHMT", nam_bat_dau=2024)

    # Ngành Quản trị kinh doanh (Của Khoa QTKD - Trường Kinh doanh)
    nganh_qtkd = NganhHoc(khoa=khoa_qtkd, ma_nganh="7340101", ten_nganh="Quản trị kinh doanh")
    phien_ban_qtkd_k66 = PhienBanCT(nganh=nganh_qtkd, ma_phien_ban="K66_QTKD", nam_bat_dau=2024)

    db.session.add_all([nganh_khmt, phien_ban_khmt_k66, nganh_qtkd, phien_ban_qtkd_k66])
    db.session.flush()

    # ---------------------------------------------------------
    # 4. TẠO HỌC PHẦN (MÔN HỌC) CHO CÁC VIỆN KHÁC NHAU
    # ---------------------------------------------------------
    # Môn của Viện CNTT
    hp_csdl = HocPhan(khoa_quan_ly=vien_cntt, ma_hoc_phan="IT104", ten_hoc_phan="Hệ quản trị Cơ sở dữ liệu",
                      so_tin_chi=3)
    hp_ltweb = HocPhan(khoa_quan_ly=vien_cntt, ma_hoc_phan="IT105", ten_hoc_phan="Lập trình Web", so_tin_chi=3)

    # Môn của Khoa QTKD
    hp_mkt = HocPhan(khoa_quan_ly=khoa_qtkd, ma_hoc_phan="MK101", ten_hoc_phan="Marketing căn bản", so_tin_chi=3)

    db.session.add_all([hp_csdl, hp_ltweb, hp_mkt])
    db.session.flush()

    # ---------------------------------------------------------
    # 5. GẮN MÔN HỌC VÀO KHUNG CHƯƠNG TRÌNH K66
    # ---------------------------------------------------------
    # Dân KHMT học CSDL và Lập trình Web
    db.session.add(KhungChuongTrinh(phien_ban_id=phien_ban_khmt_k66.id, hoc_phan_id=hp_csdl.id, hoc_ky_du_kien=3,
                                    loai_mon="Bắt buộc"))
    db.session.add(KhungChuongTrinh(phien_ban_id=phien_ban_khmt_k66.id, hoc_phan_id=hp_ltweb.id, hoc_ky_du_kien=4,
                                    loai_mon="Bắt buộc"))

    # Dân KHMT cũng phải học Marketing căn bản (Tự chọn)
    db.session.add(KhungChuongTrinh(phien_ban_id=phien_ban_khmt_k66.id, hoc_phan_id=hp_mkt.id, hoc_ky_du_kien=5,
                                    loai_mon="Tự chọn"))

    # ---------------------------------------------------------
    # 6. TẠO ĐỀ CƯƠNG CHI TIẾT CHO MÔN CSDL (IT104)
    # ---------------------------------------------------------
    dc_csdl = DeCuongChiTiet(hoc_phan=hp_csdl, nam_ap_dung="2024-2025", trang_thai="Published")
    db.session.add(dc_csdl)
    db.session.flush()

    # Chuẩn đầu ra (CLOs)
    db.session.add_all([
        ChuanDauRa(de_cuong=dc_csdl, ma_clo="CLO1",
                   mo_ta="Hiểu các khái niệm cơ bản về hệ cơ sở dữ liệu quan hệ, mô hình thực thể kết nối (ERD)."),
        ChuanDauRa(de_cuong=dc_csdl, ma_clo="CLO2", mo_ta="Thành thạo ngôn ngữ truy vấn cấu trúc (SQL).")
    ])

    # Ma trận đánh giá
    db.session.add_all([
        DanhGiaHocPhan(de_cuong=dc_csdl, thanh_phan="Chuyên cần", trong_so=0.1, hinh_thuc="Điểm danh"),
        DanhGiaHocPhan(de_cuong=dc_csdl, thanh_phan="Giữa kỳ", trong_so=0.3, hinh_thuc="Thi trắc nghiệm (60 phút)"),
        DanhGiaHocPhan(de_cuong=dc_csdl, thanh_phan="Cuối kỳ", trong_so=0.6,
                       hinh_thuc="Thi tự luận + Thực hành SQL (90 phút)")
    ])

    # Học liệu
    db.session.add_all([
        HocLieu(de_cuong=dc_csdl, loai="Giáo trình", ten_tai_lieu="Database System Concepts (7th)",
                tac_gia="Silberschatz"),
        HocLieu(de_cuong=dc_csdl, loai="Tham khảo", ten_tai_lieu="Bài giảng CSDL - Trường Công nghệ",
                tac_gia="Viện CNTT - NEU")
    ])

    # Kế hoạch giảng dạy (Rút gọn 3 tuần làm mẫu)
    db.session.add_all([
        KeHoachGiangDay(de_cuong=dc_csdl, tuan_thu=1, chu_de_bai_hoc="Tổng quan về Hệ CSDL",
                        noi_dung_chi_tiet="Hệ thống file truyền thống vs DBMS."),
        KeHoachGiangDay(de_cuong=dc_csdl, tuan_thu=2, chu_de_bai_hoc="Mô hình Thực thể - Kết nối (ERD)",
                        noi_dung_chi_tiet="Thực thể, thuộc tính, mối quan hệ. Vẽ ERD bằng Draw.io."),
        KeHoachGiangDay(de_cuong=dc_csdl, tuan_thu=3, chu_de_bai_hoc="Ngôn ngữ truy vấn SQL",
                        noi_dung_chi_tiet="Lệnh SELECT, INSERT, UPDATE, DELETE cơ bản.")
    ])

    # Lưu toàn bộ vào DB
    db.session.commit()
    print("✅ Đã tạo thành công dữ liệu mẫu bám sát mô hình 3 Trường của NEU!")