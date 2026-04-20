/**
 * NEU Course Management UI - Main JavaScript
 * Handles AJAX fetching, Rendering, and UI State
 */

const state = {
    currentTab: 'nganh', // Default tab
    currentView: 'list', // list or grid
    currentCohort: '',   // Empty means all
    searchQuery: '',
    page: 1,
    limit: 20,
    total: 0,
    totalPages: 1
};

// API Endpoints Mapping
const apiEndpoints = {
    'nganh': '/api/majors',
    'hocphan': '/api/courses',
    'khoa': '/api/faculties',
    'truong': '/api/schools'
};

document.addEventListener('DOMContentLoaded', () => {
    initUI();
    fetchVersions();
    fetchData();
});

function initUI() {
    // Tab switching
    const tabButtons = document.querySelectorAll('#mainTabs button');
    tabButtons.forEach(btn => {
        btn.addEventListener('shown.bs.tab', (e) => {
            state.currentTab = e.target.id.replace('-tab', '');
            state.page = 1; // Reset to page 1 on tab change
            fetchData();
        });
    });

    // Search input with debounce
    const searchInput = document.querySelector('.search-pill');
    let debounceTimer;
    searchInput.addEventListener('input', (e) => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            state.searchQuery = e.target.value;
            state.page = 1;
            fetchData();
        }, 500);
    });

    // View toggle
    const viewBtns = document.querySelectorAll('.view-btn');
    viewBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            viewBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            state.currentView = btn.title.toLowerCase().includes('list') ? 'list' : 'grid';
            renderCurrentData(); // Re-render existing data with new view
        });
    });

    // Cohort selection
    const cohortSelect = document.querySelector('.filter-controls select');
    cohortSelect.addEventListener('change', (e) => {
        state.currentCohort = e.target.value === 'all' ? '' : e.target.value;
        state.page = 1;
        fetchData();
    });

    // Limit selection
    const limitSelect = document.querySelector('.pagination-sm select');
    if (limitSelect) {
        limitSelect.addEventListener('change', (e) => {
            state.limit = parseInt(e.target.value);
            state.page = 1;
            fetchData();
        });
    }
}

async function fetchVersions() {
    try {
        const response = await fetch('/api/versions');
        const result = await response.json();
        if (result.status === 'success') {
            const select = document.querySelector('.filter-controls select');
            let html = '<option value="">Tất cả phiên bản</option>';
            result.data.forEach(v => {
                html += `<option value="${v.ma}">${v.ma}</option>`;
            });
            select.innerHTML = html;
        }
    } catch (error) {
        console.error('Error fetching versions:', error);
    }
}

let lastFetchedData = [];

async function fetchData() {
    const containerId = `${state.currentTab}-data-container`;
    const container = document.getElementById(containerId);
    
    // Show loading
    container.innerHTML = `
        <div class="text-center py-5 text-muted">
            <div class="spinner-border text-primary mb-3" role="status"></div>
            <p>Đang tải dữ liệu...</p>
        </div>
    `;

    const url = new URL(apiEndpoints[state.currentTab], window.location.origin);
    url.searchParams.append('page', state.page);
    url.searchParams.append('limit', state.limit);
    url.searchParams.append('q', state.searchQuery);
    url.searchParams.append('cohort', state.currentCohort);

    try {
        const response = await fetch(url);
        const result = await response.json();
        
        if (result.status === 'success') {
            lastFetchedData = result.data;
            state.total = result.total;
            state.totalPages = result.pages;
            renderCurrentData();
            renderPagination();
        }
    } catch (error) {
        container.innerHTML = `<div class="alert alert-danger">Lỗi khi tải dữ liệu. Vui lòng thử lại.</div>`;
        console.error('Fetch error:', error);
    }
}

function renderCurrentData() {
    const containerId = `${state.currentTab}-data-container`;
    const container = document.getElementById(containerId);
    
    if (lastFetchedData.length === 0) {
        container.innerHTML = `<div class="text-center py-5 text-muted">Không tìm thấy dữ liệu nào.</div>`;
        return;
    }

    if (state.currentView === 'list') {
        container.innerHTML = renderTable(lastFetchedData);
    } else {
        container.innerHTML = renderGrid(lastFetchedData);
    }
}

function renderTable(data) {
    let headers = '';
    let rows = '';

    if (state.currentTab === 'nganh') {
        headers = '<th>Mã ngành</th><th>Tên ngành</th><th>Khoa/Viện</th><th>Phiên bản</th>';
        rows = data.map(item => `
            <tr>
                <td><span class="fw-bold text-primary">${item.ma}</span></td>
                <td><a href="/major/${item.id}" class="text-decoration-none text-dark fw-medium">${item.ten}</a></td>
                <td>${item.khoa}</td>
                <td><span class="badge bg-light text-dark border">${item.phien_ban}</span></td>
            </tr>
        `).join('');
    } else if (state.currentTab === 'hocphan') {
        headers = '<th>Mã HP</th><th>Tên học phần</th><th>Số TC</th><th>Khoa quản lý</th>';
        rows = data.map(item => `
            <tr>
                <td><span class="fw-bold text-primary">${item.ma}</span></td>
                <td><a href="/course/${item.id}" class="text-decoration-none text-dark fw-medium">${item.ten}</a></td>
                <td>${item.tin_chi}</td>
                <td>${item.khoa}</td>
            </tr>
        `).join('');
    } else if (state.currentTab === 'khoa') {
        headers = '<th>Mã khoa</th><th>Tên khoa/viện</th><th>Trực thuộc</th><th>Số ngành</th>';
        rows = data.map(item => `
            <tr>
                <td><span class="fw-bold text-primary">${item.ma}</span></td>
                <td><a href="/faculty/${item.id}" class="text-decoration-none text-dark fw-medium">${item.ten}</a></td>
                <td>${item.truong}</td>
                <td>${item.count_nganh}</td>
            </tr>
        `).join('');
    } else if (state.currentTab === 'truong') {
        headers = '<th>Mã trường</th><th>Tên trường</th><th>Số khoa</th>';
        rows = data.map(item => `
            <tr>
                <td><span class="fw-bold text-primary">${item.ma}</span></td>
                <td><a href="/school/${item.id}" class="text-decoration-none text-dark fw-medium">${item.ten}</a></td>
                <td>${item.count_khoa}</td>
            </tr>
        `).join('');
    }

    return `
        <div class="table-responsive">
            <table class="table table-hover align-middle">
                <thead>
                    <tr>${headers}</tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
        </div>
    `;
}

function renderGrid(data) {
    const cards = data.map(item => {
        let subtext = '';
        let badge = '';
        
        if (state.currentTab === 'nganh') {
            subtext = item.khoa;
            badge = item.phien_ban;
        } else if (state.currentTab === 'hocphan') {
            subtext = item.khoa;
            badge = `${item.tin_chi} tín chỉ`;
        } else if (state.currentTab === 'khoa') {
            subtext = item.truong;
            badge = `${item.count_nganh} ngành`;
        } else if (state.currentTab === 'truong') {
            subtext = 'Đại học Kinh tế Quốc dân';
            badge = `${item.count_khoa} khoa`;
        }

        return `
            <div class="col-md-4 col-lg-3 mb-4">
                <div class="card h-100 border-0 shadow-sm hover-card">
                    <div class="card-body">
                        <div class="d-flex justify-content-between mb-2">
                            <span class="text-primary small fw-bold">${item.ma}</span>
                            <span class="badge bg-light text-dark border small font-weight-normal">${badge}</span>
                        </div>
                        <h6 class="card-title mb-1">
                            <a href="/${state.currentTab}/${item.id}" class="text-decoration-none text-dark stretched-link">${item.ten}</a>
                        </h6>
                        <p class="card-text text-muted small">${subtext}</p>
                    </div>
                </div>
            </div>
        `;
    }).join('');

    return `<div class="row">${cards}</div>`;
}

function renderPagination() {
    const paginationContainer = document.querySelector('.pagination');
    if (!paginationContainer) return;

    let html = '';
    
    // Prev button
    html += `
        <li class="page-item ${state.page === 1 ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="changePage(${state.page - 1}); return false;"><</a>
        </li>
    `;

    // Page numbers
    const startPage = Math.max(1, state.page - 2);
    const endPage = Math.min(state.totalPages, startPage + 4);

    for (let i = startPage; i <= endPage; i++) {
        html += `
            <li class="page-item ${i === state.page ? 'active' : ''}">
                <a class="page-link" href="#" onclick="changePage(${i}); return false;">${i}</a>
            </li>
        `;
    }

    // Next button
    html += `
        <li class="page-item ${state.page === state.totalPages || state.totalPages === 0 ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="changePage(${state.page + 1}); return false;">></a>
        </li>
    `;

    paginationContainer.innerHTML = html;
}

window.changePage = (newPage) => {
    if (newPage < 1 || newPage > state.totalPages) return;
    state.page = newPage;
    fetchData();
    window.scrollTo({ top: 400, behavior: 'smooth' });
};
