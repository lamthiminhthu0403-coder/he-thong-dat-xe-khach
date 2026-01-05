/**
 * Bus Booking System - Frontend Application
 * 
 * Hệ thống đặt vé xe khách - Môn Lập trình mạng
 * Giao thức: TCP cho các thao tác chính, UDP cho realtime updates
 */

// ============================
// STATE MANAGEMENT
// ============================
const state = {
    selectedRoute: null,
    selectedDate: null,
    selectedTrip: null,
    selectedSeats: [],
    tripInfo: null,
    routeInfo: null
};

// ============================
// SOCKET.IO CONNECTION
// ============================
let socket = null;

function initSocketIO() {
    socket = io();

    socket.on('connect', () => {
        console.log('[Socket.IO] Đã kết nối');
        updateConnectionStatus(true);
    });

    socket.on('disconnect', () => {
        console.log('[Socket.IO] Mất kết nối');
        updateConnectionStatus(false);
    });

    // Nhận cập nhật trạng thái ghế realtime từ UDP broadcast
    socket.on('seat_update', (data) => {
        console.log('[UDP] Nhận cập nhật ghế:', data.timestamp);
        if (state.selectedTrip && data.seats_data[state.selectedTrip]) {
            updateSeatsDisplay(data.seats_data[state.selectedTrip]);
        }
    });
}

function updateConnectionStatus(connected) {
    const statusEl = document.getElementById('connectionStatus');
    if (connected) {
        statusEl.innerHTML = '<span class="status-dot"></span><span>Kết nối</span>';
        statusEl.style.background = '#f0fdf4';
        statusEl.style.color = '#166534';
    } else {
        statusEl.innerHTML = '<span class="status-dot" style="background:#ef4444"></span><span>Mất kết nối</span>';
        statusEl.style.background = '#fef2f2';
        statusEl.style.color = '#dc2626';
    }
}

// ============================
// API CALLS (qua TCP)
// ============================

async function fetchCities() {
    try {
        const response = await fetch('/api/cities');
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Lỗi lấy danh sách thành phố:', error);
        return null;
    }
}

async function searchRoutes(fromCity, toCity) {
    try {
        const response = await fetch('/api/routes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ from_city: fromCity, to_city: toCity })
        });
        return await response.json();
    } catch (error) {
        console.error('Lỗi tìm tuyến:', error);
        return null;
    }
}

async function fetchDates(routeId) {
    try {
        const response = await fetch(`/api/dates/${routeId}`);
        return await response.json();
    } catch (error) {
        console.error('Lỗi lấy ngày:', error);
        return null;
    }
}

async function searchTrips(routeId, date) {
    try {
        const response = await fetch('/api/trips', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ route_id: routeId, date: date })
        });
        return await response.json();
    } catch (error) {
        console.error('Lỗi tìm chuyến:', error);
        return null;
    }
}

async function fetchSeats(tripId) {
    try {
        const response = await fetch(`/api/seats/${tripId}`);
        return await response.json();
    } catch (error) {
        console.error('Lỗi lấy ghế:', error);
        return null;
    }
}

async function selectSeat(tripId, seatId) {
    try {
        const response = await fetch('/api/select-seat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ trip_id: tripId, seat_id: seatId })
        });
        return await response.json();
    } catch (error) {
        console.error('Lỗi chọn ghế:', error);
        return null;
    }
}

async function unselectSeat(tripId, seatId) {
    try {
        const response = await fetch('/api/unselect-seat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ trip_id: tripId, seat_id: seatId })
        });
        return await response.json();
    } catch (error) {
        console.error('Lỗi bỏ chọn ghế:', error);
        return null;
    }
}

async function bookSeats(tripId, seatIds, customerInfo) {
    try {
        const response = await fetch('/api/book', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                trip_id: tripId,
                seat_ids: seatIds,
                customer_info: customerInfo
            })
        });
        return await response.json();
    } catch (error) {
        console.error('Lỗi đặt vé:', error);
        return null;
    }
}

async function fetchTripInfo(tripId) {
    try {
        const response = await fetch(`/api/trip-info/${tripId}`);
        return await response.json();
    } catch (error) {
        console.error('Lỗi lấy thông tin chuyến:', error);
        return null;
    }
}

async function uploadFile(file, bookingId) {
    try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('booking_id', bookingId);

        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        return await response.json();
    } catch (error) {
        console.error('Lỗi upload file:', error);
        return null;
    }
}

// ============================
// UI FUNCTIONS
// ============================

function goBack(stepNumber) {
    showStep(stepNumber);
}

function showStep(stepNumber) {
    // Ẩn tất cả các step
    document.querySelectorAll('.step').forEach(step => {
        step.style.display = 'none';
    });

    // Hiện step được chọn
    const stepEl = document.getElementById(`step${stepNumber}`);
    if (stepEl) {
        stepEl.style.display = 'block';
    }
}

function populateCityDropdowns(cities) {
    const fromSelect = document.getElementById('fromCity');
    const toSelect = document.getElementById('toCity');

    // Xóa options cũ
    fromSelect.innerHTML = '<option value="">Chọn điểm đi...</option>';
    toSelect.innerHTML = '<option value="">Chọn điểm đến...</option>';

    // Thêm thành phố điểm đi
    cities.from_cities.forEach(city => {
        const option = document.createElement('option');
        option.value = city;
        option.textContent = city;
        fromSelect.appendChild(option);
    });

    // Thêm thành phố điểm đến
    cities.to_cities.forEach(city => {
        const option = document.createElement('option');
        option.value = city;
        option.textContent = city;
        toSelect.appendChild(option);
    });
}

function displayRoutes(routes) {
    const container = document.getElementById('routesList');

    if (!routes || routes.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: #6b7280; padding: 20px;">Không tìm thấy tuyến phù hợp</p>';
        return;
    }

    container.innerHTML = routes.map(route => `
        <div class="route-card" data-route-id="${route.id}" onclick="selectRoute('${route.id}', '${route.from_city}', '${route.to_city}', ${route.base_price})">
            <div class="route-info">
                <div class="route-path">
                    <strong>${route.from_city}</strong> → <strong>${route.to_city}</strong>
                    <span style="display: block; font-size: 14px; color: #6b7280; margin-top: 5px;">
                        📍 ${route.distance_km} km
                    </span>
                </div>
                <div class="route-price">${formatPrice(route.base_price)}</div>
            </div>
        </div>
    `).join('');
}

async function selectRoute(routeId, fromCity, toCity, price) {
    // Highlight selected route
    document.querySelectorAll('.route-card').forEach(card => {
        card.classList.remove('selected');
    });
    document.querySelector(`[data-route-id="${routeId}"]`).classList.add('selected');

    // Lưu state
    state.selectedRoute = routeId;
    state.routeInfo = { from_city: fromCity, to_city: toCity, base_price: price };

    // Lấy danh sách ngày có chuyến
    const data = await fetchDates(routeId);
    if (data && data.dates) {
        displayDates(data.dates);
        showStep(2);
    }
}

function displayDates(dates) {
    const container = document.getElementById('datesList');

    if (!dates || dates.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: #6b7280; padding: 20px;">Không có chuyến nào trong thời gian tới</p>';
        return;
    }

    container.innerHTML = dates.map(dateStr => {
        const date = new Date(dateStr);
        const dayNames = ['CN', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7'];
        const monthNames = ['Th1', 'Th2', 'Th3', 'Th4', 'Th5', 'Th6', 'Th7', 'Th8', 'Th9', 'Th10', 'Th11', 'Th12'];

        return `
            <div class="date-card" data-date="${dateStr}" onclick="selectDate('${dateStr}')">
                <div class="date-day">${date.getDate()}</div>
                <div class="date-info">
                    ${dayNames[date.getDay()]}, ${monthNames[date.getMonth()]}
                </div>
            </div>
        `;
    }).join('');
}

async function selectDate(dateStr) {
    console.log('[App] selectDate called with:', dateStr);
    try {
        // Highlight selected date
        document.querySelectorAll('.date-card').forEach(card => {
            card.classList.remove('selected');
        });

        // Safely try to select the element
        const selectedEl = document.querySelector(`.date-card[data-date="${dateStr}"]`);
        if (selectedEl) {
            selectedEl.classList.add('selected');
        } else {
            console.warn('[App] Could not find date-card element for highlighting');
        }

        // Lưu state
        state.selectedDate = dateStr;
        console.log('[App] State updated. Route:', state.selectedRoute, 'Date:', state.selectedDate);

        if (!state.selectedRoute) {
            console.error('[App] No route selected!');
            alert('Vui lòng chọn tuyến trước');
            return;
        }

        // Tìm chuyến xe
        console.log('[App] Calling searchTrips...');
        const data = await searchTrips(state.selectedRoute, dateStr);
        console.log('[App] searchTrips response:', data);

        if (data && data.trips) {
            console.log('[App] Found', data.trips.length, 'trips');
            displayTrips(data.trips);
            showStep(3);
            console.log('[App] Moved to step 3');
        } else {
            console.error('[App] Invalid data received:', data);
        }
    } catch (error) {
        console.error('[App] Error in selectDate:', error);
        alert('Có lỗi xảy ra: ' + error.message);
    }
}
// Expose to window to ensure HTML onclick can hit it
window.selectDate = selectDate;

function displayTrips(trips) {
    const container = document.getElementById('tripsList');

    if (!trips || trips.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: #6b7280; padding: 20px;">Không có chuyến nào trong ngày này</p>';
        return;
    }

    container.innerHTML = trips.map(trip => `
        <div class="trip-card" data-trip-id="${trip.id}" onclick="selectTrip('${trip.id}')">
            <div class="trip-header">
                <div>
                    <div class="trip-time">🕐 ${trip.departure_time}</div>
                    <div class="trip-type">${trip.bus_type}</div>
                </div>
                <div class="trip-seats">
                    <div class="seats-available">${trip.available_seats || 40} ghế trống</div>
                </div>
            </div>
            <div class="trip-bus">🚌 ${trip.bus_code}</div>
        </div>
    `).join('');
}

async function selectTrip(tripId) {
    // Highlight selected trip
    document.querySelectorAll('.trip-card').forEach(card => {
        card.classList.remove('selected');
    });
    document.querySelector(`[data-trip-id="${tripId}"]`).classList.add('selected');

    // Lưu state
    state.selectedTrip = tripId;
    state.selectedSeats = [];

    // Lấy thông tin chuyến
    const tripInfo = await fetchTripInfo(tripId);
    if (tripInfo) {
        state.tripInfo = tripInfo.trip;
    }

    // Lấy ghế
    const data = await fetchSeats(tripId);
    if (data && data.seats) {
        displaySeats(data.seats);
        showStep(4);
    }
}

function displaySeats(seats) {
    const floor1 = document.getElementById('floor1');
    const floor2 = document.getElementById('floor2');

    // Tầng 1: T1-A01 đến T1-A20
    let floor1HTML = '';
    for (let i = 1; i <= 20; i++) {
        const seatId = `T1-A${i.toString().padStart(2, '0')}`;
        const seat = seats[seatId] || { status: 'available' };
        const isMySelection = state.selectedSeats.includes(seatId);

        let seatClass = 'seat ' + seat.status;
        if (isMySelection) {
            seatClass = 'seat my-selection';
        }

        floor1HTML += `
            <div class="${seatClass}" 
                 data-seat-id="${seatId}"
                 onclick="handleSeatClick('${seatId}', '${seat.status}')">
                ${seatId.split('-')[1]}
            </div>
        `;
    }
    floor1.innerHTML = floor1HTML;

    // Tầng 2: T2-B01 đến T2-B20
    let floor2HTML = '';
    for (let i = 1; i <= 20; i++) {
        const seatId = `T2-B${i.toString().padStart(2, '0')}`;
        const seat = seats[seatId] || { status: 'available' };
        const isMySelection = state.selectedSeats.includes(seatId);

        let seatClass = 'seat ' + seat.status;
        if (isMySelection) {
            seatClass = 'seat my-selection';
        }

        floor2HTML += `
            <div class="${seatClass}" 
                 data-seat-id="${seatId}"
                 onclick="handleSeatClick('${seatId}', '${seat.status}')">
                ${seatId.split('-')[1]}
            </div>
        `;
    }
    floor2.innerHTML = floor2HTML;

    updateSelectedSeatsDisplay();
}

function updateSeatsDisplay(seats) {
    // Cập nhật hiển thị ghế từ UDP broadcast
    Object.keys(seats).forEach(seatId => {
        const seatEl = document.querySelector(`[data-seat-id="${seatId}"]`);
        if (seatEl) {
            const seat = seats[seatId];
            const isMySelection = state.selectedSeats.includes(seatId);

            // Xóa tất cả class cũ
            seatEl.classList.remove('available', 'selecting', 'booked', 'my-selection');

            if (isMySelection) {
                seatEl.classList.add('my-selection');
            } else {
                seatEl.classList.add(seat.status);
            }
        }
    });
}

async function handleSeatClick(seatId, currentStatus) {
    const isMySelection = state.selectedSeats.includes(seatId);

    if (isMySelection) {
        // Bỏ chọn ghế
        const result = await unselectSeat(state.selectedTrip, seatId);
        if (result && result.success) {
            state.selectedSeats = state.selectedSeats.filter(id => id !== seatId);

            // Cập nhật UI
            const seatEl = document.querySelector(`[data-seat-id="${seatId}"]`);
            seatEl.classList.remove('my-selection');
            seatEl.classList.add('available');

            updateSelectedSeatsDisplay();
        } else {
            showNotification(result?.message || 'Không thể bỏ chọn ghế', 'error');
        }
    } else if (currentStatus === 'available') {
        // Chọn ghế mới
        const result = await selectSeat(state.selectedTrip, seatId);
        if (result && result.success) {
            state.selectedSeats.push(seatId);

            // Cập nhật UI
            const seatEl = document.querySelector(`[data-seat-id="${seatId}"]`);
            seatEl.classList.remove('available');
            seatEl.classList.add('my-selection');

            updateSelectedSeatsDisplay();
        } else {
            showNotification(result?.message || 'Không thể chọn ghế', 'error');
        }
    } else {
        showNotification('Ghế này không còn trống', 'warning');
    }
}

function updateSelectedSeatsDisplay() {
    const displayEl = document.getElementById('selectedSeatsDisplay');
    const continueBtn = document.getElementById('continueToBooking');

    if (state.selectedSeats.length === 0) {
        displayEl.textContent = 'Chưa chọn ghế nào';
        continueBtn.style.display = 'none';
    } else {
        displayEl.textContent = state.selectedSeats.join(', ');
        continueBtn.style.display = 'block';
    }
}

function continueToBooking() {
    if (state.selectedSeats.length === 0) {
        showNotification('Vui lòng chọn ít nhất 1 ghế', 'warning');
        return;
    }

    // Hiển thị thông tin đặt vé
    const summaryEl = document.getElementById('bookingSummary');
    const price = state.routeInfo?.base_price || 0;
    const totalPrice = price * state.selectedSeats.length;

    summaryEl.innerHTML = `
        <h3>📋 Thông tin đặt vé</h3>
        <p><strong>Tuyến:</strong> ${state.routeInfo?.from_city} → ${state.routeInfo?.to_city}</p>
        <p><strong>Ngày:</strong> ${formatDate(state.selectedDate)}</p>
        <p><strong>Giờ khởi hành:</strong> ${state.tripInfo?.departure_time || 'N/A'}</p>
        <p><strong>Xe:</strong> ${state.tripInfo?.bus_code || 'N/A'} (${state.tripInfo?.bus_type || 'Giường nằm'})</p>
        <p><strong>Ghế:</strong> ${state.selectedSeats.join(', ')}</p>
        <p><strong>Số lượng:</strong> ${state.selectedSeats.length} ghế</p>
        <p style="font-size: 20px; color: #667eea; margin-top: 15px;">
            <strong>Tổng tiền: ${formatPrice(totalPrice)}</strong>
        </p>
    `;

    showStep(5);
}

async function handleBookingSubmit(event) {
    event.preventDefault();

    const customerInfo = {
        name: document.getElementById('customerName').value.trim(),
        phone: document.getElementById('customerPhone').value.trim(),
        cccd: document.getElementById('customerCCCD').value.trim()
    };

    // Validate
    if (!customerInfo.name || !customerInfo.phone || !customerInfo.cccd) {
        showNotification('Vui lòng điền đầy đủ thông tin', 'warning');
        return;
    }

    // Gửi request đặt vé
    const result = await bookSeats(state.selectedTrip, state.selectedSeats, customerInfo);

    if (result && result.success) {
        // Upload files nếu có
        const fileInput = document.getElementById('uploadFiles');
        if (fileInput && fileInput.files.length > 0) {
            for (const file of fileInput.files) {
                await uploadFile(file, result.booking_id);
            }
        }

        // Hiển thị kết quả
        displayBookingSuccess(result, customerInfo);
    } else {
        showNotification(result?.message || 'Đặt vé thất bại', 'error');
    }
}

function displayBookingSuccess(result, customerInfo) {
    const resultEl = document.getElementById('bookingResult');
    const price = state.routeInfo?.base_price || 0;
    const totalPrice = price * state.selectedSeats.length;

    resultEl.innerHTML = `
        <p><strong>Mã vé:</strong> <span style="color: #667eea; font-size: 24px;">${result.booking_id}</span></p>
        <p><strong>Khách hàng:</strong> ${customerInfo.name}</p>
        <p><strong>Số điện thoại:</strong> ${customerInfo.phone}</p>
        <p><strong>CCCD:</strong> ${customerInfo.cccd}</p>
        <hr style="margin: 15px 0; border-color: #e5e7eb;">
        <p><strong>Tuyến:</strong> ${state.routeInfo?.from_city} → ${state.routeInfo?.to_city}</p>
        <p><strong>Ngày:</strong> ${formatDate(state.selectedDate)}</p>
        <p><strong>Giờ:</strong> ${state.tripInfo?.departure_time || 'N/A'}</p>
        <p><strong>Xe:</strong> ${state.tripInfo?.bus_code || 'N/A'}</p>
        <p><strong>Ghế:</strong> ${state.selectedSeats.join(', ')}</p>
        <p style="font-size: 18px; color: #22c55e; margin-top: 10px;">
            <strong>Tổng tiền: ${formatPrice(totalPrice)}</strong>
        </p>
    `;

    showStep('Success');
}

// ============================
// UTILITY FUNCTIONS
// ============================

function formatPrice(price) {
    return new Intl.NumberFormat('vi-VN', {
        style: 'currency',
        currency: 'VND'
    }).format(price);
}

function formatDate(dateStr) {
    const date = new Date(dateStr);
    const dayNames = ['Chủ nhật', 'Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7'];
    return `${dayNames[date.getDay()]}, ${date.getDate()}/${date.getMonth() + 1}/${date.getFullYear()}`;
}

function showNotification(message, type = 'info') {
    // Tạo notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 25px;
        border-radius: 10px;
        color: white;
        font-weight: 500;
        z-index: 9999;
        animation: slideIn 0.3s ease-out;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    `;

    // Set màu theo type
    switch (type) {
        case 'success':
            notification.style.background = 'linear-gradient(135deg, #22c55e, #16a34a)';
            break;
        case 'error':
            notification.style.background = 'linear-gradient(135deg, #ef4444, #dc2626)';
            break;
        case 'warning':
            notification.style.background = 'linear-gradient(135deg, #f59e0b, #d97706)';
            break;
        default:
            notification.style.background = 'linear-gradient(135deg, #3b82f6, #2563eb)';
    }

    document.body.appendChild(notification);

    // Tự động ẩn sau 3 giây
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-in';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// ============================
// EVENT LISTENERS
// ============================

async function handleCityChange() {
    const fromCity = document.getElementById('fromCity').value;
    const toCity = document.getElementById('toCity').value;

    if (fromCity && toCity) {
        const data = await searchRoutes(fromCity, toCity);
        if (data && data.routes) {
            displayRoutes(data.routes);
        }
    } else if (fromCity || toCity) {
        // Tìm với 1 tiêu chí
        const data = await searchRoutes(fromCity, toCity);
        if (data && data.routes) {
            displayRoutes(data.routes);
        }
    }
}

// ============================
// INITIALIZATION
// ============================

// Expose all critical UI functions to window for onclick compatibility
window.selectRoute = selectRoute;
window.selectDate = selectDate;
window.selectTrip = selectTrip;
window.handleSeatClick = handleSeatClick;
window.goBack = goBack;
window.continueToBooking = continueToBooking;

document.addEventListener('DOMContentLoaded', async () => {
    console.log('🚌 Bus Booking System - Khởi động (App v4)');

    // Khởi tạo Socket.IO
    initSocketIO();

    // Lấy danh sách thành phố
    const cities = await fetchCities();
    if (cities) {
        populateCityDropdowns(cities);
    }

    // Event listeners cho dropdown
    const fromCityEl = document.getElementById('fromCity');
    const toCityEl = document.getElementById('toCity');

    if (fromCityEl) fromCityEl.addEventListener('change', handleCityChange);
    if (toCityEl) toCityEl.addEventListener('change', handleCityChange);

    // Event listener cho nút tiếp tục đặt vé
    const contBtn = document.getElementById('continueToBooking');
    if (contBtn) contBtn.addEventListener('click', continueToBooking);

    // Event listener cho form đặt vé
    const custForm = document.getElementById('customerForm');
    if (custForm) custForm.addEventListener('submit', handleBookingSubmit);

    console.log('✅ Hệ thống sẵn sàng');
});

// Thêm CSS cho notification animation
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);
