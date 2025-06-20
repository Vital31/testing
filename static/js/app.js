// Конфигурация API
const API_BASE_URL = 'http://localhost:8000';

// Глобальные переменные
let deviceActivityChart = null;
let deviceTypesChart = null;

// Инициализация приложения
document.addEventListener('DOMContentLoaded', function() {
    console.log('IoT System Dashboard initialized');
    
    // Загружаем данные при загрузке страницы
    refreshDashboard();
    loadDevices();
    loadAnalytics();
    loadMonitoringData();
    loadBackups();
    loadLogs();
    
    // Обновляем данные каждые 30 секунд
    setInterval(refreshDashboard, 30000);
    setInterval(loadAnalytics, 30000);
});

// Функции для работы с API
async function apiRequest(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API request failed:', error);
        showError(`Ошибка API: ${error.message}`);
        throw error;
    }
}

async function apiTextRequest(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.text();
    } catch (error) {
        console.error('API text request failed:', error);
        showError(`Ошибка API (text): ${error.message}`);
        throw error;
    }
}

// Показать ошибку
function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
    
    // Добавляем в начало основного контента
    const mainContent = document.querySelector('.main-content');
    mainContent.insertBefore(errorDiv, mainContent.firstChild);
    
    // Удаляем через 5 секунд
    setTimeout(() => {
        errorDiv.remove();
    }, 5000);
}

// Показать/скрыть индикатор загрузки
function showLoading(containerId) {
    const container = document.getElementById(containerId);
    const loading = container.querySelector('.loading');
    if (loading) {
        loading.style.display = 'block';
    }
}

function hideLoading(containerId) {
    const container = document.getElementById(containerId);
    const loading = container.querySelector('.loading');
    if (loading) {
        loading.style.display = 'none';
    }
}

// Дашборд
async function refreshDashboard() {
    try {
        showLoading('services-status');
        
        // Загружаем статус сервисов
        const healthData = await apiRequest('/health');
        updateServicesStatus(healthData);
        
        // Загружаем устройства
        const devicesData = await apiRequest('/devices');
        updateDashboardMetrics(devicesData);
        
        // Обновляем графики
        updateCharts(devicesData);
        
        hideLoading('services-status');
    } catch (error) {
        console.error('Failed to refresh dashboard:', error);
        hideLoading('services-status');
    }
}

function updateServicesStatus(healthData) {
    const container = document.getElementById('services-status');
    
    let html = '<div class="row">';
    
    for (const [serviceName, serviceData] of Object.entries(healthData.services)) {
        const statusClass = serviceData.status === 'healthy' ? 'status-healthy' : 'status-error';
        const statusText = serviceData.status === 'healthy' ? 'Работает' : 'Ошибка';
        
        html += `
            <div class="col-md-6 mb-2">
                <div class="d-flex align-items-center">
                    <span class="status-indicator ${statusClass}"></span>
                    <strong>${serviceName}</strong>
                    <span class="ms-auto badge bg-${serviceData.status === 'healthy' ? 'success' : 'danger'}">${statusText}</span>
                </div>
                ${serviceData.response_time ? `<small class="text-muted">Время ответа: ${(serviceData.response_time * 1000).toFixed(2)}ms</small>` : ''}
            </div>
        `;
    }
    
    html += '</div>';
    container.innerHTML = html;
}

function updateDashboardMetrics(devicesData) {
    const totalDevices = devicesData.count || 0;
    const activeDevices = devicesData.devices ? devicesData.devices.filter(d => d.status === 'active').length : 0;
    
    document.getElementById('total-devices').textContent = totalDevices;
    document.getElementById('active-devices').textContent = activeDevices;
    document.getElementById('data-points').textContent = 'N/A'; // Будет обновлено позже
    document.getElementById('system-health').textContent = totalDevices > 0 ? 'OK' : 'N/A';
}

function updateCharts(devicesData) {
    updateDeviceActivityChart(devicesData);
    updateDeviceTypesChart(devicesData);
}

function updateDeviceActivityChart(devicesData) {
    const ctx = document.getElementById('deviceActivityChart').getContext('2d');
    
    if (deviceActivityChart) {
        deviceActivityChart.destroy();
    }
    
    // Генерируем тестовые данные для активности
    const labels = [];
    const data = [];
    const now = new Date();
    
    for (let i = 6; i >= 0; i--) {
        const date = new Date(now);
        date.setDate(date.getDate() - i);
        labels.push(date.toLocaleDateString('ru-RU'));
        data.push(Math.floor(Math.random() * 100) + 50); // Случайные данные
    }
    
    deviceActivityChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Активность устройств',
                data: data,
                borderColor: '#667eea',
                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

function updateDeviceTypesChart(devicesData) {
    const ctx = document.getElementById('deviceTypesChart').getContext('2d');
    
    if (deviceTypesChart) {
        deviceTypesChart.destroy();
    }
    
    // Группируем устройства по типам
    const typeCounts = {};
    if (devicesData.devices) {
        devicesData.devices.forEach(device => {
            typeCounts[device.device_type] = (typeCounts[device.device_type] || 0) + 1;
        });
    }
    
    const labels = Object.keys(typeCounts);
    const data = Object.values(typeCounts);
    const colors = ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe'];
    
    deviceTypesChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors.slice(0, labels.length),
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

// Устройства
async function loadDevices() {
    try {
        showLoading('devices-list');
        
        const devicesData = await apiRequest('/devices');
        displayDevices(devicesData.devices || []);
        
        hideLoading('devices-list');
    } catch (error) {
        console.error('Failed to load devices:', error);
        hideLoading('devices-list');
    }
}

function displayDevices(devices) {
    const container = document.getElementById('devices-list');
    
    if (devices.length === 0) {
        container.innerHTML = '<p class="text-muted">Устройства не найдены</p>';
        return;
    }
    
    let html = '<div class="row">';
    
    devices.forEach(device => {
        const statusClass = device.status === 'active' ? 'status-healthy' : 'status-error';
        const statusText = device.status === 'active' ? 'Активно' : 'Неактивно';
        
        html += `
            <div class="col-md-6 col-lg-4 mb-3">
                <div class="card device-card">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <h6 class="card-title mb-0">${device.name}</h6>
                            <span class="status-indicator ${statusClass}"></span>
                        </div>
                        <p class="card-text text-muted small">${device.device_type}</p>
                        ${device.location ? `<p class="card-text text-muted small"><i class="fas fa-map-marker-alt"></i> ${device.location}</p>` : ''}
                        ${device.sensor_type ? `<p class="card-text text-muted small"><i class="fas fa-sensor"></i> ${device.sensor_type}</p>` : ''}
                        <div class="d-flex justify-content-between align-items-center">
                            <small class="text-muted">ID: ${device.id.substring(0, 8)}...</small>
                            <div class="btn-group btn-group-sm">
                                <button type="button" class="btn btn-outline-primary" onclick="viewDevice('${device.id}')">
                                    <i class="fas fa-eye"></i>
                                </button>
                                <button type="button" class="btn btn-outline-warning" onclick="editDevice('${device.id}')">
                                    <i class="fas fa-edit"></i>
                                </button>
                                <button type="button" class="btn btn-outline-danger" onclick="deleteDevice('${device.id}')">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
}

async function submitDevice() {
    try {
        const formData = {
            name: document.getElementById('deviceName').value,
            device_type: document.getElementById('deviceType').value,
            location: document.getElementById('deviceLocation').value,
            sensor_type: document.getElementById('sensorType').value,
            sampling_rate: parseInt(document.getElementById('samplingRate').value) || null
        };
        
        await apiRequest('/devices', {
            method: 'POST',
            body: JSON.stringify(formData)
        });
        
        // Закрываем модальное окно
        const modal = bootstrap.Modal.getInstance(document.getElementById('addDeviceModal'));
        modal.hide();
        
        // Обновляем список устройств
        loadDevices();
        refreshDashboard();
        
        // Очищаем форму
        document.getElementById('addDeviceForm').reset();
        
    } catch (error) {
        console.error('Failed to add device:', error);
    }
}

async function deleteDevice(deviceId) {
    if (!confirm('Вы уверены, что хотите удалить это устройство?')) {
        return;
    }
    
    try {
        await apiRequest(`/devices/${deviceId}`, {
            method: 'DELETE'
        });
        
        loadDevices();
        refreshDashboard();
    } catch (error) {
        console.error('Failed to delete device:', error);
    }
}

// Аналитика
async function loadAnalytics() {
    try {
        showLoading('realtime-analytics');
        showLoading('anomalies-list');
        
        // Загружаем аналитику в реальном времени
        const realtimeData = await apiRequest('/analytics/realtime');
        displayRealtimeAnalytics(realtimeData);
        
        // Загружаем аномалии
        const anomaliesData = await apiRequest('/anomalies');
        displayAnomalies(anomaliesData.anomalies || []);
        
        hideLoading('realtime-analytics');
        hideLoading('anomalies-list');
    } catch (error) {
        console.error('Failed to load analytics:', error);
        hideLoading('realtime-analytics');
        hideLoading('anomalies-list');
    }
}

function displayRealtimeAnalytics(data) {
    const container = document.getElementById('realtime-analytics');
    
    let html = `
        <div class="mb-3">
            <strong>Время обновления:</strong> ${new Date(data.timestamp).toLocaleString('ru-RU')}
        </div>
    `;
    
    if (Object.keys(data.devices).length === 0) {
        html += '<p class="text-muted">Нет данных для отображения</p>';
    } else {
        for (const [deviceId, deviceData] of Object.entries(data.devices)) {
            html += `<h6>Устройство ${deviceId.substring(0, 8)}...</h6>`;
            
            for (const [dataType, stats] of Object.entries(deviceData)) {
                html += `
                    <div class="mb-2">
                        <small class="text-muted">${dataType}:</small>
                        <div class="row">
                            <div class="col-6">
                                <small>Последнее: ${stats.latest}</small>
                            </div>
                            <div class="col-6">
                                <small>Среднее: ${stats.avg.toFixed(2)}</small>
                            </div>
                        </div>
                    </div>
                `;
            }
        }
    }
    
    container.innerHTML = html;
}

function displayAnomalies(anomalies) {
    const container = document.getElementById('anomalies-list');
    
    if (anomalies.length === 0) {
        container.innerHTML = '<p class="text-success">Аномалии не обнаружены</p>';
        return;
    }
    
    let html = '';
    anomalies.slice(0, 5).forEach(anomaly => {
        html += `
            <div class="alert alert-warning alert-sm">
                <strong>Устройство:</strong> ${anomaly.device_id.substring(0, 8)}...<br>
                <strong>Тип данных:</strong> ${anomaly.data_type}<br>
                <strong>Значение:</strong> ${anomaly.value}<br>
                <strong>Z-score:</strong> ${anomaly.z_score.toFixed(2)}<br>
                <small class="text-muted">${new Date(anomaly.timestamp).toLocaleString('ru-RU')}</small>
            </div>
        `;
    });
    
    if (anomalies.length > 5) {
        html += `<p class="text-muted">И еще ${anomalies.length - 5} аномалий...</p>`;
    }
    
    container.innerHTML = html;
}

// Мониторинг
async function loadMonitoringData() {
    try {
        showLoading('monitoring-data');
        
        // Загружаем метрики Prometheus
        const metricsData = await apiTextRequest('/metrics');
        displayPrometheusMetrics(metricsData);
        
        hideLoading('monitoring-data');
    } catch (error) {
        console.error('Failed to load monitoring data:', error);
        hideLoading('monitoring-data');
    }
}

function displayPrometheusMetrics(metricsData) {
    const container = document.getElementById('prometheus-metrics');
    
    // Парсим метрики Prometheus
    const lines = metricsData.split('\n');
    const metrics = {};
    
    lines.forEach(line => {
        if (line && !line.startsWith('#')) {
            const parts = line.split(' ');
            if (parts.length >= 2) {
                const metricName = parts[0];
                const value = parseFloat(parts[1]);
                if (!isNaN(value)) {
                    metrics[metricName] = value;
                }
            }
        }
    });
    
    let html = '<div class="table-responsive"><table class="table table-sm">';
    html += '<thead><tr><th>Метрика</th><th>Значение</th></tr></thead><tbody>';
    
    for (const [metric, value] of Object.entries(metrics)) {
        html += `<tr><td>${metric}</td><td>${value}</td></tr>`;
    }
    
    html += '</tbody></table></div>';
    container.innerHTML = html;
}

// Резервное копирование
async function loadBackups() {
    try {
        showLoading('backups-list');
        
        // Здесь будет загрузка списка бэкапов
        // Пока отображаем заглушку
        const container = document.getElementById('backups-list');
        container.innerHTML = '<p class="text-muted">Функция резервного копирования будет доступна после настройки</p>';
        
        hideLoading('backups-list');
    } catch (error) {
        console.error('Failed to load backups:', error);
        hideLoading('backups-list');
    }
}

async function createBackup() {
    try {
        // Здесь будет создание бэкапа
        alert('Функция создания бэкапа будет доступна после настройки');
    } catch (error) {
        console.error('Failed to create backup:', error);
    }
}

async function restoreBackup() {
    try {
        const fileInput = document.getElementById('backup-file');
        if (!fileInput.files[0]) {
            alert('Выберите файл бэкапа');
            return;
        }
        
        // Здесь будет восстановление из бэкапа
        alert('Функция восстановления будет доступна после настройки');
    } catch (error) {
        console.error('Failed to restore backup:', error);
    }
}

// Логи
async function loadLogs() {
    try {
        showLoading('logs-content');
        
        // Здесь будет загрузка логов
        // Пока отображаем заглушку
        const container = document.getElementById('logs-content');
        container.innerHTML = '<p class="text-muted">Логи будут доступны после настройки системы логирования</p>';
        
        hideLoading('logs-content');
    } catch (error) {
        console.error('Failed to load logs:', error);
        hideLoading('logs-content');
    }
}

// Настройки
async function clearCache() {
    try {
        await apiRequest('/cache/clear');
        alert('Кэш успешно очищен');
    } catch (error) {
        console.error('Failed to clear cache:', error);
        alert('Ошибка при очистке кэша');
    }
}

// Обновление данных
function refreshAnalytics() {
    loadAnalytics();
}

function refreshLogs() {
    loadLogs();
}

// Функции для работы с устройствами (заглушки)
function viewDevice(deviceId) {
    alert(`Просмотр устройства ${deviceId} - функция в разработке`);
}

function editDevice(deviceId) {
    alert(`Редактирование устройства ${deviceId} - функция в разработке`);
} 