// API配置
const API_BASE_URL = 'http://localhost:5001';

// 全局变量
let map = null;
let loadChart = null;
let currentAnalysis = null;
let networkData = null;
let candidateLayer = null; // 显示候选方案的图层
// 网格叠加
let gridLayer = null;
let gridShown = false;
// 区域图层功能已移除（按网格叠加展示），保留变量占位避免报错
let zonesLayer = null;
let zonesShown = false;
// 请求取消控制器
let currentAbortController = null;

// 仅用于可视化的“坐标压缩”：将节点围绕中心点按比例收缩，提升地图观感密度（不影响后端计算）
const VISUAL_DENSIFY_ENABLED = true;  // 可置为 false 关闭
const VISUAL_DENSIFY_SCALE = 0.35;    // 0~1，越小越密集，建议 0.25~0.5
let visualCenter = null;              // {lat, lon}

function visualCoord(lat, lon) {
    if (!VISUAL_DENSIFY_ENABLED || !visualCenter) return [lat, lon];
    const lat2 = visualCenter.lat + (lat - visualCenter.lat) * VISUAL_DENSIFY_SCALE;
    const lon2 = visualCenter.lon + (lon - visualCenter.lon) * VISUAL_DENSIFY_SCALE;
    return [lat2, lon2];
}

// 前端计算：找到离给定经纬度最近的已知站点（用于新线预览端点对齐）
function nearestStation(lat, lon) {
    if (!networkData) return null;
    const subs = (networkData.substations || networkData.buses || []).filter(s => s.location);
    if (!subs.length) return null;
    let best = null; let bestD = 1e18;
    subs.forEach(s => {
        const d = Math.pow(Number(s.location.lat) - Number(lat), 2) + Math.pow(Number(s.location.lon) - Number(lon), 2);
        if (d < bestD) { bestD = d; best = s; }
    });
    return best;
}

function kNearestStations(lat, lon, k = 2) {
    if (!networkData) return [];
    const subs = (networkData.substations || networkData.buses || []).filter(s => s.location);
    const arr = subs.map(s => ({ s, d: Math.pow(Number(s.location.lat) - Number(lat), 2) + Math.pow(Number(s.location.lon) - Number(lon), 2) }));
    arr.sort((a, b) => a.d - b.d);
    return arr.slice(0, k).map(x => x.s);
}

function findStationById(id) {
    const subs = (networkData && (networkData.substations || networkData.buses)) || [];
    return subs.find(s => s.id === id) || null;
}

function normalizeBusId(id) {
    if (id == null) return null;
    if (typeof id === 'number') return `bus_${id}`;
    if (typeof id === 'string') return id.startsWith('bus_') ? id : id;
    return String(id);
}

function lineExistsBetween(busIdA, busIdB) {
    const lines = (networkData && networkData.lines) || [];
    const a = normalizeBusId(busIdA), b = normalizeBusId(busIdB);
    if (!a || !b) return false;
    for (const ln of lines) {
        const fa = normalizeBusId(typeof ln.from_bus === 'number' ? `bus_${ln.from_bus}` : ln.from_bus);
        const tb = normalizeBusId(typeof ln.to_bus === 'number' ? `bus_${ln.to_bus}` : ln.to_bus);
        if ((fa === a && tb === b) || (fa === b && tb === a)) return true;
    }
    return false;
}

function offsetVisualSegment(p1, p2, meters = 120) {
    // 简单近似：1度纬度约111km，1度经度约111km*cos(lat)
    const [lat1, lon1] = p1; const [lat2, lon2] = p2;
    const dlat = lat2 - lat1; const dlon = lon2 - lon1;
    const latScale = 111000.0; const lonScale = Math.cos((lat1 + lat2) * Math.PI / 360.0) * 111000.0;
    const vx = dlon * lonScale; const vy = dlat * latScale; // 向量（米）
    const L = Math.sqrt(vx*vx + vy*vy) || 1.0;
    // 垂直单位向量（米）
    const px = -vy / L; const py = vx / L;
    const offX = (px * meters) / lonScale; // 转回度
    const offY = (py * meters) / latScale;
    return [[lat1 + offY, lon1 + offX], [lat2 + offY, lon2 + offX]];
}
// 缓存数据供语言切换使用
let currentLoadSummary = null;
let currentTopology = null;
let currentPowerFlowResults = null;
let currentNMinus1Results = null;
let currentConstraints = null;

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    console.log('Grid Planning System - Initializing...');

    initMap();
    initChart();
    bindEvents();
    checkAPIConnection();

    // 初始化语言
    if (window.updatePageLanguage) {
        updatePageLanguage();
    }

    // 首次进入页面时自动加载一次数据，避免用户未点击"加载数据"导致图表为空
    setTimeout(() => {
        loadData().catch(() => {});
    }, 100);
});

// 初始化地图
function initMap() {
    // 使用广州坐标（IEEE 14-bus数据位于广州地区）
    map = L.map('map').setView([23.12, 113.26], 11);

    // 使用高德地图（更适合中国地区）
    L.tileLayer('https://webrd01.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}', {
        attribution: '© 高德地图',
        maxZoom: 18
    }).addTo(map);

    console.log('Map initialized with Guangzhou coordinates');
}

// 初始化图表
function initChart() {
    const ctx = document.getElementById('loadChart').getContext('2d');

    loadChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: '预测负载 (MW)',
                data: [],
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                borderWidth: 2,
                pointBackgroundColor: '#60a5fa',
                pointBorderColor: '#3b82f6',
                pointRadius: 3,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        color: '#e2e8f0',
                        font: {
                            size: 12
                        }
                    }
                }
            },
            scales: {
                x: {
                    ticks: {
                        color: '#94a3b8'
                    },
                    grid: {
                        color: '#334155'
                    }
                },
                y: {
                    beginAtZero: false,
                    ticks: {
                        color: '#94a3b8'
                    },
                    grid: {
                        color: '#334155'
                    },
                    title: {
                        display: true,
                        text: '负载 (MW)',
                        color: '#cbd5e1'
                    }
                }
            }
        }
    });

    console.log('Chart initialized');
}

// 绑定事件
function bindEvents() {
    document.getElementById('btnAnalyze').addEventListener('click', runCompleteAnalysis);
    document.getElementById('btnLoadData').addEventListener('click', loadData);
    document.getElementById('btnPowerFlow').addEventListener('click', runPowerFlow);
    document.getElementById('btnNMinus1').addEventListener('click', runNMinus1);
    // LLM文档分析 按钮绑定（存在时再绑定，避免报错）
    const btnUpload = document.getElementById('btnUploadParse');
    if (btnUpload) btnUpload.addEventListener('click', uploadAndParseDoc);
    const btnApplyCons = document.getElementById('btnApplyConstraints');
    if (btnApplyCons) btnApplyCons.addEventListener('click', applyParsedConstraints);
    const btnResetCons = document.getElementById('btnResetConstraints');
    if (btnResetCons) btnResetCons.addEventListener('click', resetConstraintsOverrides);

    // 自定义文件选择按钮
    const btnSelectFile = document.getElementById('btnSelectFile');
    const llmFile = document.getElementById('llmFile');
    if (btnSelectFile && llmFile) {
        btnSelectFile.addEventListener('click', function() {
            llmFile.click();
        });

        llmFile.addEventListener('change', function() {
            const fileNameSpan = document.getElementById('selectedFileName');
            if (this.files && this.files.length > 0) {
                fileNameSpan.textContent = this.files[0].name;
            } else {
                fileNameSpan.textContent = window.t ? window.t('llm.no_file_selected') : '未选择文件';
            }
        });

        // 初始化显示
        const fileNameSpan = document.getElementById('selectedFileName');
        fileNameSpan.textContent = window.t ? window.t('llm.no_file_selected') : '未选择文件';
    }

    // 语言切换按钮
    document.getElementById('btnLanguage').addEventListener('click', function() {
        if (window.toggleLanguage) toggleLanguage();
    });

    // LLM聊天输入已移除

    // 取消加载按钮
    document.getElementById('btnCancelLoading').addEventListener('click', cancelLoading);
    // 网格开关
    const btnGrid = document.getElementById('btnToggleGrid');
    if (btnGrid) btnGrid.addEventListener('click', toggleGrid);

    // 中心面板标签页切换
    initCenterTabs();

    // 潮流与校验标签页切换
    initPFTabs();

    console.log('Events bound');
}

// 初始化中心面板标签页
function initCenterTabs() {
    const tabs = document.querySelectorAll('.center-tab');
    const panels = document.querySelectorAll('.tab-panel');

    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const targetTab = this.getAttribute('data-tab');

            // 切换标签按钮状态
            tabs.forEach(t => t.classList.remove('active'));
            this.classList.add('active');

            // 切换面板显示
            panels.forEach(panel => {
                if (panel.getAttribute('data-panel') === targetTab) {
                    panel.classList.add('active');
                } else {
                    panel.classList.remove('active');
                }
            });

            // 切换到地图时刷新地图尺寸
            if (targetTab === 'map' && map) {
                setTimeout(() => {
                    map.invalidateSize();
                }, 100);
            }

            // 切换到图表时刷新图表
            if (targetTab === 'chart' && loadChart) {
                setTimeout(() => {
                    loadChart.resize();
                }, 100);
            }
        });
    });
}

// 初始化潮流与校验标签页
function initPFTabs() {
    const tabs = document.querySelectorAll('#pfTabHeader .tab-btn');
    const panes = document.querySelectorAll('#pfTabContent .tab-pane');

    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const targetTab = this.getAttribute('data-tab');

            // 切换标签按钮状态
            tabs.forEach(t => t.classList.remove('active'));
            this.classList.add('active');

            // 切换面板显示
            panes.forEach(pane => {
                if (pane.id === `pf-${targetTab}`) {
                    pane.classList.add('active');
                } else {
                    pane.classList.remove('active');
                }
            });
        });
    });
}

// 检查API连接
async function checkAPIConnection() {
    try {
        const response = await fetch(`${API_BASE_URL}/`);
        const data = await response.json();

        const statusEl = document.getElementById('apiStatus');
        statusEl.textContent = window.t ? t('api.connected') : 'API: 已连接';
        statusEl.classList.add('connected');
        console.log('API Connected:', data);
    } catch (error) {
        const statusEl = document.getElementById('apiStatus');
        statusEl.textContent = window.t ? t('api.disconnected') : 'API: 连接失败';
        console.error('API Connection failed:', error);
    }
}

// 显示Loading
function showLoading(show = true) {
    if (show) {
        // 创建新的 AbortController
        currentAbortController = new AbortController();
    }
    document.getElementById('loadingOverlay').style.display = show ? 'flex' : 'none';
}

// 取消加载
function cancelLoading() {
    if (currentAbortController) {
        currentAbortController.abort();
        currentAbortController = null;
    }
    showLoading(false);
    updateStatus('status.cancelled');
}

// 更新状态
function updateStatus(textOrKey) {
    const statusEl = document.getElementById('statusText');
    // 如果是翻译键，尝试翻译；否则直接使用文本
    if (window.t && textOrKey.startsWith('status.')) {
        statusEl.textContent = t(textOrKey);
    } else {
        statusEl.textContent = textOrKey;
    }
}

// 加载数据
async function loadData() {
    showLoading(true);
    updateStatus('status.loading');

    try {
        const signal = currentAbortController ? currentAbortController.signal : undefined;

        // 获取负载摘要
        const loadResponse = await fetch(`${API_BASE_URL}/api/load/summary`, { signal });
        const loadData = await loadResponse.json();

        if (loadData.success) {
            currentLoadSummary = loadData.summary;
            window.currentLoadSummary = currentLoadSummary;
            displayLoadSummary(loadData.summary);
        }

        // 获取网络数据
        const networkResponse = await fetch(`${API_BASE_URL}/api/gis/network`, { signal });
        const networkData = await networkResponse.json();

        if (networkData.success) {
            currentTopology = networkData.network.topology;
            window.currentTopology = currentTopology;
            displayNetwork(networkData.network);
            displayTopology(networkData.network.topology);
        }

        // 获取负载预测
        const predictionResponse = await fetch(`${API_BASE_URL}/api/load/predict`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ horizon_days: 30 }),
            signal
        });
        const predictionData = await predictionResponse.json();
        console.log('Prediction API response:', predictionData && predictionData.success, predictionData && predictionData.prediction ? predictionData.prediction.length : 'N/A');

        if (predictionData.success) {
            displayLoadPrediction(predictionData.prediction);
        }

        updateStatus('status.data_loaded');
    } catch (error) {
        if (error.name === 'AbortError') {
            console.log('Request was cancelled');
            return;
        }
        console.error('Error loading data:', error);
        updateStatus('数据加载失败');
        const errorMsg = window.translateErrorMessage ? window.translateErrorMessage(error.message) : error.message;
        alert((window.t ? window.t('alert.load_data_failed') : '加载数据失败') + ': ' + errorMsg);
    } finally {
        showLoading(false);
    }
}

// 显示负载摘要
function displayLoadSummary(summary) {
    const container = document.getElementById('loadSummary');
    const lang = window.t;

    const html = `
        <h3>${lang ? t('load.current_features') : '当前特征'}</h3>
        <p><strong>${lang ? t('load.avg_load') : '平均负载'}:</strong> ${summary.current_features.avg_load.toFixed(2)} MW</p>
        <p><strong>${lang ? t('load.max_load') : '最大负载'}:</strong> ${summary.current_features.max_load.toFixed(2)} MW</p>
        <p><strong>${lang ? t('load.growth_rate') : '增长率'}:</strong> ${(summary.current_features.growth_rate * 100).toFixed(2)}%</p>
        <p><strong>${lang ? t('load.peak_hour') : '峰值时段'}:</strong> ${summary.current_features.peak_hour}:00</p>

        <h3>${lang ? t('load.overload_areas') : '过载区域'}</h3>
        ${summary.overload_areas.map(area => {
            // 翻译优先级
            let priorityText = area.priority;
            if (lang) {
                const priorityKey = `load.priority.${area.priority.toLowerCase()}`;
                priorityText = t(priorityKey) || area.priority;
            }

            // 翻译变电站名称
            const stationName = window.translateStationName ? window.translateStationName(area.name) : area.name;

            return `
                <div style="margin: 5px 0; padding: 8px; background: #422006; border-left: 3px solid #f59e0b; color: #fcd34d;">
                    <strong style="color: #fbbf24;">${stationName}</strong><br>
                    <span style="color: #fde68a;">${lang ? t('load.loading_rate') : '负载率'}: ${(area.loading_rate * 100).toFixed(1)}%</span><br>
                    <span style="color: #fde68a;">${lang ? t('load.priority') : '优先级'}: ${priorityText}</span>
                </div>
            `;
        }).join('')}
    `;

    container.innerHTML = html;
}

// 显示网络拓扑
function displayNetwork(network) {
    networkData = network;

    // 清除现有标记（不移除瓦片/网格/候选图层）
    map.eachLayer(layer => {
        if ((layer instanceof L.Marker || layer instanceof L.Polyline) && layer !== candidateLayer) {
            map.removeLayer(layer);
        }
    });

    // 兼容IEEE数据（使用buses）和原始数据（使用substations）
    const stations = network.buses || network.substations || [];
    const lines = network.lines || [];

    // 计算可视化中心点（平均值）
    const validForCenter = stations.filter(s => s.location);
    if (validForCenter.length > 0) {
        const latSum = validForCenter.reduce((acc, s) => acc + Number(s.location.lat), 0);
        const lonSum = validForCenter.reduce((acc, s) => acc + Number(s.location.lon), 0);
        visualCenter = { lat: latSum / validForCenter.length, lon: lonSum / validForCenter.length };
    }

    // 创建自定义图标
    const createCustomIcon = (voltageKv) => {
        let color = '#3b82f6';  // 蓝色 - 中压
        let iconSize = [12, 12];

        if (voltageKv > 200) {
            color = '#dc2626';  // 红色 - 超高压
            iconSize = [20, 20];
        } else if (voltageKv > 100) {
            color = '#f59e0b';  // 橙色 - 高压
            iconSize = [16, 16];
        }

        return L.divIcon({
            className: 'custom-station-icon',
            html: `<div style="
                width: ${iconSize[0]}px;
                height: ${iconSize[1]}px;
                background: ${color};
                border: 2px solid #fff;
                border-radius: 50%;
                box-shadow: 0 2px 4px rgba(0,0,0,0.3);
            "></div>`,
            iconSize: iconSize,
            iconAnchor: [iconSize[0]/2, iconSize[1]/2]
        });
    };

    // 线路绘制已禁用 - 仅通过网格叠加显示
    // lines.forEach(line => {
    //     const fromBusId = typeof line.from_bus === 'number' ? `bus_${line.from_bus}` : line.from_bus;
    //     const toBusId = typeof line.to_bus === 'number' ? `bus_${line.to_bus}` : line.to_bus;
    //
    //     const fromSub = stations.find(s => s.id === fromBusId);
    //     const toSub = stations.find(s => s.id === toBusId);
    //
    //     if (fromSub && toSub && fromSub.location && toSub.location) {
    //         const loadingPercent = line.loading_percent || 0;
    //
    //         // 根据负载率设置颜色
    //         let color = '#10b981';  // 绿色 < 50%
    //         if (loadingPercent > 0.8) color = '#ef4444';  // 红色 > 80%
    //         else if (loadingPercent > 0.5) color = '#f59e0b';  // 黄色 50-80%
    //
    //         const polyline = L.polyline([
    //             [fromSub.location.lat, fromSub.location.lon],
    //             [toSub.location.lat, toSub.location.lon]
    //         ], {
    //             color: color,
    //             weight: 3,
    //             opacity: 0.7
    //         }).addTo(map);
    //
    //         // 添加弹出信息
    //         polyline.bindPopup(`
    //             <div style="color: #1e293b;">
    //                 <strong style="color: #1e40af;">${line.name || line.id}</strong><br>
    //                 长度: ${line.length_km} km<br>
    //                 负载率: ${(loadingPercent * 100).toFixed(1)}%<br>
    //                 ${line.capacity_mva ? `容量: ${line.capacity_mva} MVA` : ''}
    //             </div>
    //         `);
    //     }
    // });

    // 绘制变电站标记
    stations.forEach(station => {
        if (!station.location) return;

        const voltageKv = station.voltage_kv || station.voltage_level || 0;
        const icon = createCustomIcon(voltageKv);

        const [vlat, vlon] = visualCoord(station.location.lat, station.location.lon);
        const marker = L.marker([vlat, vlon], { icon: icon }).addTo(map);

        // 添加弹出信息
        const stationName = window.translateStationName ? window.translateStationName(station.name_zh || station.name) : (station.name_zh || station.name);
        const lang = window.t;
        const isEnglish = window.getCurrentLanguage && window.getCurrentLanguage() === 'en';
        const voltageLabel = isEnglish ? 'Voltage' : '电压';
        const capacityLabel = isEnglish ? 'Capacity' : '容量';
        const typeLabel = isEnglish ? 'Type' : '类型';

        marker.bindPopup(`
            <div style="color: #1e293b; min-width: 150px;">
                <strong style="color: #1e40af; font-size: 14px;">${stationName}</strong><br>
                <span style="color: #64748b;">ID: ${station.id}</span><br>
                <span style="color: #64748b;">${voltageLabel}: ${voltageKv} kV</span><br>
                <span style="color: #64748b;">${capacityLabel}: ${station.capacity_mva || 'N/A'} MVA</span><br>
                <span style="color: #64748b;">${typeLabel}: ${station.type_zh || station.type || 'N/A'}</span>
            </div>
        `);
    });

    // 调整地图视图以包含所有标记
    if (stations.length > 0) {
        const validStations = stations.filter(s => s.location);
        if (validStations.length > 0) {
            const bounds = L.latLngBounds(validStations.map(s => {
                const p = s.location; const v = visualCoord(p.lat, p.lon); return [v[0], v[1]];
            }));
            map.fitBounds(bounds, { padding: [50, 50] });
        }
    }

    console.log(`Network displayed: ${stations.length} stations, ${lines.length} lines`);

    // 自动显示网格叠加
    if (!gridShown && map && networkData) {
        setTimeout(() => {
            toggleGrid();
        }, 300);
    }
}

// 显示拓扑信息
function displayTopology(topology) {
    const container = document.getElementById('topologyInfo');
    const lang = window.t;

    const html = `
        <p><strong>${lang ? t('topology.total_substations') : '变电站数量'}:</strong> ${topology.total_substations}</p>
        <p><strong>${lang ? t('topology.total_lines') : '线路数量'}:</strong> ${topology.total_lines}</p>
        <p><strong>${lang ? t('topology.avg_degree') : '平均连接度'}:</strong> ${topology.avg_degree.toFixed(2)}</p>

        <h3>${lang ? t('topology.critical_nodes') : '关键节点'}</h3>
        ${topology.critical_nodes.map(node => `
            <p>• ${node.id} (${lang ? t('topology.degree') : '度数'}: ${node.degree})</p>
        `).join('')}

        ${topology.weak_nodes.length > 0 ? `
            <h3>${lang ? t('topology.weak_nodes') : '薄弱节点'}</h3>
            ${topology.weak_nodes.map(node => `<p>• ${node}</p>`).join('')}
        ` : ''}
    `;

    container.innerHTML = html;
}

// 显示负载预测
function displayLoadPrediction(prediction) {
    if (!Array.isArray(prediction) || prediction.length === 0) {
        console.warn('displayLoadPrediction: empty prediction array');
        return;
    }

    // 显示7天的详细数据（每3小时1个点，共56个点），以展示日周期波动
    const sampledData = prediction.filter((_, index) => index % 3 === 0).slice(0, 56);

    const labels = sampledData.map((d, i) => {
        try {
            if (!d.timestamp) return `${i}`;
            const date = new Date(d.timestamp);
            if (isNaN(date.getTime())) return `${i}`; // 解析失败时退回索引
            const month = date.getMonth() + 1;
            const day = date.getDate();
            const hour = date.getHours();
            return hour === 0 ? `${month}/${day}` : `${hour}h`;
        } catch (e) {
            return `${i}`;
        }
    });

    const data = sampledData.map(d => Number(d.predicted_load_mw));

    loadChart.data.labels = labels;
    loadChart.data.datasets[0].data = data;
    loadChart.update();
}

// 运行完整分析
async function runCompleteAnalysis() {
    showLoading(true);
    updateStatus('status.analyzing');

    try {
        const signal = currentAbortController ? currentAbortController.signal : undefined;

        const response = await fetch(`${API_BASE_URL}/api/planning/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            signal
        });

        const data = await response.json();

        if (data.success) {
            currentAnalysis = data.analysis;
            window.currentAnalysis = currentAnalysis; // 同步到全局作用域

            // 显示各项结果
            displayLoadSummary(currentAnalysis.load_summary);
            displayTopology(currentAnalysis.network_topology);
            displayCandidates(currentAnalysis.validated_candidates);
            // displayLLMSuggestions(currentAnalysis.llm_suggestions); // 已移除该功能
            displayConstraints(currentAnalysis.constraints);

            // 同步刷新负载预测曲线
            try {
                const predictionResponse = await fetch(`${API_BASE_URL}/api/load/predict`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ horizon_days: 30 }),
                    signal
                });
                const predictionData = await predictionResponse.json();
                console.log('Prediction API response (analyze):', predictionData && predictionData.success, predictionData && predictionData.prediction ? predictionData.prediction.length : 'N/A');
                if (predictionData.success) {
                    displayLoadPrediction(predictionData.prediction);
                }
            } catch (e) {
                if (e.name !== 'AbortError') {
                    console.warn('Failed to refresh prediction after analyze:', e);
                }
            }

            updateStatus('status.analysis_complete');
            alert(window.t ? window.t('alert.analysis_complete') : '完整分析已完成！');
        } else {
            throw new Error(data.error);
        }
    } catch (error) {
        if (error.name === 'AbortError') {
            console.log('Analysis was cancelled');
            return;
        }
        console.error('Analysis error:', error);
        updateStatus('分析失败');
        const errorMsg = window.translateErrorMessage ? window.translateErrorMessage(error.message) : error.message;
        alert((window.t ? window.t('alert.analysis_failed') : '分析失败') + ': ' + errorMsg);
    } finally {
        showLoading(false);
    }
}

// 显示候选方案
function displayCandidates(candidates) {
    const container = document.getElementById('candidateRanking');
    const lang = window.t;

    if (!candidates || candidates.length === 0) {
        container.innerHTML = `<p>${lang ? t('left.candidate_ranking_hint') : '暂无候选方案'}</p>`;
        return;
    }

    const html = candidates.map((c, idx) => {
        const candidate = c.candidate;
        const scores = c.scores;
        const rankClass = `rank-${c.rank}`;

        let typeLabel = lang
            ? (candidate.type === 'new_substation' ? t('candidate.new_substation') :
               candidate.type === 'substation_expansion' ? t('candidate.substation_expansion') : t('candidate.new_line'))
            : (candidate.type === 'new_substation' ? '新建变电站' :
               candidate.type === 'substation_expansion' ? '变电站扩容' : '新建线路');
        if (candidate.type === 'new_line' && candidate.subtype) {
            if (candidate.subtype === 'reinforcement') typeLabel += lang ? ` (${t('candidate.reinforcement')})` : '（并联加固）';
            else if (candidate.subtype === 'interconnection') typeLabel += lang ? ` (${t('candidate.interconnection')})` : '（新建联络）';
        }

        const areaLabel = lang ? t('candidate.area') : '区域';
        const totalScoreLabel = lang ? t('candidate.total_score') : '综合评分';
        const loadScoreLabel = lang ? t('candidate.load_score') : '负载得分';
        const distanceScoreLabel = lang ? t('candidate.distance_score') : '距离得分';
        const topoScoreLabel = lang ? t('candidate.topology_score') : '拓扑得分';
        const constraintScoreLabel = lang ? t('candidate.constraint_score') : '约束得分';
        const costLabel = lang ? t('candidate.estimated_cost') : '估算成本';
        const passedLabel = lang ? t('candidate.passed') : '通过';
        const failedLabel = lang ? t('candidate.failed') : '未通过';
        const validationLabel = lang ? t('candidate.powerflow_validation') : '潮流验证';
        const previewLabel = lang ? t('candidate.preview') : '在地图上预览';
        const rankLabel = lang ? t('candidate.rank') : '排名';

        // 翻译区域名称
        const areaName = window.translateStationName ? window.translateStationName(candidate.area_name) : candidate.area_name;

        return `
            <div class="candidate-item ${rankClass}" data-cand-index="${idx}">
                <h3>${rankLabel} #${c.rank} - ${typeLabel}</h3>
                <p><strong>${areaLabel}:</strong> ${areaName}</p>
                <p><strong>${totalScoreLabel}:</strong> <span class="score-badge">${scores.total.toFixed(2)}</span></p>
                <p><strong>${loadScoreLabel}:</strong> ${scores.load_growth.toFixed(2)} | <strong>${distanceScoreLabel}:</strong> ${scores.distance.toFixed(2)}</p>
                <p><strong>${topoScoreLabel}:</strong> ${scores.topology.toFixed(2)} | <strong>${constraintScoreLabel}:</strong> ${scores.constraint.toFixed(2)}</p>
                <p><strong>${costLabel}:</strong> ${candidate.estimated_cost_m}M${lang && window.getCurrentLanguage && window.getCurrentLanguage() === 'en' ? ' CNY' : '元'}</p>
                ${c.power_flow_validation ? `
                    <p class="${c.power_flow_validation.passed ? 'text-success' : 'text-danger'}">
                        ${c.power_flow_validation.passed ? `[${passedLabel}] ${validationLabel}` : `[${failedLabel}] ${validationLabel}`}
                    </p>
                ` : ''}
                <p style="margin-top:6px;"><button class="btn btn-small preview-btn">${previewLabel}</button></p>
            </div>
        `;
    }).join('');

    container.innerHTML = html;

    // 绑定预览事件（点击整块或按钮都可）
    container.querySelectorAll('.candidate-item').forEach(el => {
        el.addEventListener('click', (e) => {
            const idx = parseInt(el.getAttribute('data-cand-index'), 10);
            const candWrap = candidates[idx];
            if (candWrap && candWrap.candidate) {
                // 地图预览
                previewCandidateOnMap(candWrap.candidate);
                // 同步更新右侧“潮流计算/N-1校验”面板，展示该候选方案的校核结果
                try {
                    const pfv = candWrap.power_flow_validation || {};
                    const t = (candWrap.candidate.type === 'new_substation' ? '新建变电站' : (candWrap.candidate.type === 'substation_expansion' ? '变电站扩容' : '新建线路'));
                    const header = `<p class=\"text-info\">当前方案：${t} · 区域：${candWrap.candidate.area_name || ''}</p>`;
                    if (pfv.power_flow) {
                        document.getElementById('pf-powerflow').innerHTML = header + renderPowerFlowHTML(pfv.power_flow);
                        // 切到潮流计算标签
                        activatePFTabByName('powerflow');
                    }
                    if (pfv.n_minus_1) {
                        document.getElementById('pf-nminus1').innerHTML = header + renderNMinus1HTML(pfv.n_minus_1);
                    }
                } catch (err) {
                    console.warn('Failed to render candidate PF/N-1 panels:', err);
                }
            }
        });
        const btn = el.querySelector('.preview-btn');
        if (btn) btn.addEventListener('click', (ev) => {
            ev.stopPropagation();
            const idx = parseInt(el.getAttribute('data-cand-index'), 10);
            const candWrap = candidates[idx];
            if (candWrap) {
                previewCandidateOnMap(candWrap.candidate);
                try {
                    const pfv = candWrap.power_flow_validation || {};
                    const t = (candWrap.candidate.type === 'new_substation' ? '新建变电站' : (candWrap.candidate.type === 'substation_expansion' ? '变电站扩容' : '新建线路'));
                    const header = `<p class=\"text-info\">当前方案：${t} · 区域：${candWrap.candidate.area_name || ''}</p>`;
                    if (pfv.power_flow) {
                        document.getElementById('pf-powerflow').innerHTML = header + renderPowerFlowHTML(pfv.power_flow);
                        activatePFTabByName('powerflow');
                    }
                    if (pfv.n_minus_1) {
                        document.getElementById('pf-nminus1').innerHTML = header + renderNMinus1HTML(pfv.n_minus_1);
                    }
                } catch (err) {
                    console.warn('Failed to render candidate PF/N-1 panels:', err);
                }
            }
        });
    });
}

// 在地图上预览候选方案
function previewCandidateOnMap(candidate) {
    if (!map) return;
    if (candidateLayer) { map.removeLayer(candidateLayer); candidateLayer = null; }
    candidateLayer = L.layerGroup().addTo(map);

    const type = candidate.type;
    if (type === 'new_line') {
        const a = candidate.from_location || {};
        const b = candidate.to_location || {};
        if (a.lat != null && a.lon != null && b.lat != null && b.lon != null) {
            // 确定起点站
            let fromStation = candidate.from_substation_id ? findStationById(candidate.from_substation_id) : nearestStation(a.lat, a.lon);
            let fromLat = a.lat, fromLon = a.lon, fromName = '';
            if (fromStation && fromStation.location) {
                fromLat = fromStation.location.lat;
                fromLon = fromStation.location.lon;
                const rawName = fromStation.name || fromStation.id;
                fromName = window.translateStationName ? window.translateStationName(rawName) : rawName;
            }

            // 确定终点站：优先指定ID，否则选择“离目标最近但不同于起点”的站
            let toStation = candidate.to_substation_id ? findStationById(candidate.to_substation_id) : null;
            if (!toStation) {
                const nearList = kNearestStations(b.lat, b.lon, 3);
                toStation = nearList.find(s => !fromStation || s.id !== fromStation.id) || nearList[0] || null;
            }
            if (!toStation || !toStation.location) return; // 无法确定端点，不画线

            let av = visualCoord(fromLat, fromLon);
            let bv = visualCoord(toStation.location.lat, toStation.location.lon);
            // 如果基线已有同一对站点的线路，则将预览线做一个小偏移，避免完全重合
            const fromId = fromStation ? fromStation.id : null;
            const toId = toStation.id;
            if (lineExistsBetween(fromId, toId)) {
                const seg = offsetVisualSegment(av, bv, 140); // 偏移约140米
                av = seg[0]; bv = seg[1];
            }
            const line = L.polyline([av, bv], { color: '#22d3ee', weight: 5, opacity: 0.9, dashArray: '6,6' }).addTo(candidateLayer);
            const lang = window.t;
            const toStationName = toStation ? (window.translateStationName ? window.translateStationName(toStation.name || toStation.id) : (toStation.name || toStation.id)) : '';
            const tip = `<strong>${lang ? t('preview.new_line') : '新建线路'}</strong><br>${lang ? t('preview.voltage') : '电压'}: ${candidate.voltage_level || 110} kV` +
                (toStationName ? `<br>${lang ? t('preview.connect_to') : '连接至'}: ${toStationName}` : '') +
                (fromName ? `<br>${lang ? t('preview.from') : '起点'}: ${fromName}` : '');
            line.bindPopup(tip);
            map.fitBounds(line.getBounds(), { padding: [40, 40] });
        }
    } else if (type === 'new_substation') {
        const loc = candidate.location || {};
        if (loc.lat != null && loc.lon != null) {
            const v = visualCoord(loc.lat, loc.lon);
            const marker = L.circleMarker(v, { radius: 8, color: '#ef4444', weight: 3, fillColor: '#fca5a5', fillOpacity: 0.7 }).addTo(candidateLayer);
            const lang = window.t;
            marker.bindPopup(`<strong>${lang ? t('preview.new_substation') : '新建变电站'}</strong><br>${lang ? t('preview.capacity') : '容量'}: ${(candidate.capacity_mva || 0).toFixed(0)} MVA<br>${lang ? t('preview.voltage') : '电压'}: ${candidate.voltage_level || 110} kV`);
            map.setView(v, 13);
        }
    } else if (type === 'substation_expansion') {
        // 高亮扩容的既有站点
        const sid = candidate.substation_id;
        let found = null;
        const subs = (networkData && (networkData.substations || networkData.buses)) || [];
        found = subs.find(s => s.id === sid);
        if (found && found.location) {
            const loc = found.location; const v = visualCoord(loc.lat, loc.lon);
            const circle = L.circle(v, { radius: 400, color: '#f59e0b', weight: 2, fillColor: '#fde68a', fillOpacity: 0.3 }).addTo(candidateLayer);
            const lang = window.t;
            const stationName = window.translateStationName ? window.translateStationName(found.name || sid) : (found.name || sid);
            circle.bindPopup(`<strong>${lang ? t('preview.substation_expansion') : '变电站扩容'}</strong><br>${stationName}<br>${lang ? t('preview.additional_capacity') : '新增容量'}: ${(candidate.additional_capacity || 0).toFixed(0)} MVA`);
            map.setView(v, 13);
        }
    }
}

// 显示LLM建议
function displayLLMSuggestions(suggestions) {
    const container = document.getElementById('llmSuggestions');

    if (!suggestions || suggestions.length === 0) {
        container.innerHTML = '<p>暂无建议</p>';
        return;
    }

    const html = suggestions.map((sug, index) => {
        if (sug.parsed === false) {
            return `<p>${sug.raw_text}</p>`;
        }

        return `
            <div style="margin-bottom: 10px; padding: 8px; background: white;">
                <h4>${index + 1}. ${sug.type || '方案'}</h4>
                <p><strong>位置:</strong> ${sug.location || 'N/A'}</p>
                <p><strong>优先级:</strong> ${sug.priority || 'N/A'}</p>
                <p>${sug.reasoning || ''}</p>
            </div>
        `;
    }).join('');

    container.innerHTML = html;
}

// 显示约束
function displayConstraints(constraints) {
    const container = document.getElementById('constraintCheck');
    const lang = window.t;

    // 缓存约束数据
    currentConstraints = constraints;
    window.currentConstraints = currentConstraints;

    if (!constraints || Object.keys(constraints).length === 0) {
        container.innerHTML = `<p>${lang ? t('constraints.none') : '暂无约束信息'}</p>`;
        return;
    }

    let html = `<h3>${lang ? t('constraints.title') : '约束条件'}</h3>`;
    let count = 0;

    for (const [docName, constraint] of Object.entries(constraints)) {
        if (constraint && constraint.parsed === false) {
            // 跳过未能解析成JSON的条目
            continue;
        }
        const translatedDocName = window.translateDocumentName ? window.translateDocumentName(docName) : docName;
        html += `<div style="margin: 5px 0;"><strong>${translatedDocName}</strong></div>`;
        count++;
    }

    if (count === 0) {
        container.innerHTML = `<p>${lang ? t('constraints.parsing') : '约束解析中或未解析到有效条款'}</p>`;
    } else {
        container.innerHTML = html;
    }
}

// 运行潮流计算
async function runPowerFlow() {
    showLoading(true);
    updateStatus('status.powerflow');

    try {
        const signal = currentAbortController ? currentAbortController.signal : undefined;

        const response = await fetch(`${API_BASE_URL}/api/powerflow/run`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            signal
        });

        const data = await response.json();

        if (data.success) {
            currentPowerFlowResults = data.results;
            window.currentPowerFlowResults = currentPowerFlowResults;
            const html = renderPowerFlowHTML(data.results);
            // 更新固定标签内容并切换到该标签
            document.getElementById('pf-powerflow').innerHTML = html;
            activatePFTabByName('powerflow');
            updateStatus('status.powerflow_complete');
        } else {
            throw new Error(data.error);
        }
    } catch (error) {
        if (error.name === 'AbortError') {
            console.log('Power flow was cancelled');
            return;
        }
        console.error('Power flow error:', error);
        updateStatus('潮流计算失败');
        const errorMsg = window.translateErrorMessage ? window.translateErrorMessage(error.message) : error.message;
        alert((window.t ? window.t('alert.powerflow_failed') : '潮流计算失败') + ': ' + errorMsg);
    } finally {
        showLoading(false);
    }
}

// 切换到指定的潮流校验标签
function activatePFTabByName(tabName) {
    const tabs = document.querySelectorAll('#pfTabHeader .tab-btn');
    const panes = document.querySelectorAll('#pfTabContent .tab-pane');

    tabs.forEach(tab => {
        if (tab.getAttribute('data-tab') === tabName) {
            tab.classList.add('active');
        } else {
            tab.classList.remove('active');
        }
    });

    panes.forEach(pane => {
        if (pane.id === `pf-${tabName}`) {
            pane.classList.add('active');
        } else {
            pane.classList.remove('active');
        }
    });
}

function renderPowerFlowHTML(results) {
    const lang = window.t;

    if (!results || !results.converged) {
        return `<p style="color: red;">${lang ? t('powerflow.not_converged') : '潮流计算未收敛'}</p>`;
    }

    let html = `<h3>${lang ? t('powerflow.bus_results') : '母线结果'}</h3>`;
    (results.buses || []).slice(0, 5).forEach(bus => {
        html += `<p><strong>${bus.name}</strong> ${lang ? t('powerflow.voltage') : '电压'}: ${bus.voltage_pu.toFixed(3)} p.u. | ${lang ? t('powerflow.power') : '功率'}: ${bus.p_mw.toFixed(2)} MW</p>`;
    });

    // 展示变压器负载，便于观察"扩容"效果
    if (Array.isArray(results.transformers) && results.transformers.length > 0) {
        html += `<h3>${lang ? t('powerflow.transformer_load') : '变压器负载'}</h3>`;
        results.transformers.forEach(tr => {
            const color = tr.loading_percent > 90 ? 'red' : tr.loading_percent > 70 ? 'orange' : 'green';
            html += `<p><strong>${tr.name || (lang ? t('powerflow.transformer') : '变压器')}</strong> <span style="color:${color}">${lang ? t('powerflow.loading_rate') : '负载率'}: ${tr.loading_percent.toFixed(1)}%</span></p>`;
        });
    }

    html += `<h3>${lang ? t('powerflow.line_load') : '线路负载'}</h3>`;
    (results.lines || []).forEach(line => {
        const color = line.loading_percent > 90 ? 'red' : line.loading_percent > 70 ? 'orange' : 'green';
        html += `<p><strong>${line.name || (lang ? t('powerflow.line') : '线路')}</strong> <span style="color:${color}">${lang ? t('powerflow.loading_rate') : '负载率'}: ${line.loading_percent.toFixed(1)}%</span></p>`;
    });

    if (results.violations && results.violations.length > 0) {
        html += `<h3 class="text-danger">${lang ? t('powerflow.violations') : '违规项'}</h3>`;
        results.violations.forEach(v => {
            html += `<p class="text-warning">[${lang ? t('powerflow.warning') : '警告'}] ${v.element} ${v.name}: ${v.type}</p>`;
        });
    } else {
        html += `<p class="text-success">[${lang ? t('powerflow.passed') : '通过'}] ${lang ? t('powerflow.no_violations') : '无违规项'}</p>`;
    }

    return html;
}

// 运行N-1校验
async function runNMinus1() {
    showLoading(true);
    updateStatus('status.nminus1');

    try {
        const signal = currentAbortController ? currentAbortController.signal : undefined;

        const response = await fetch(`${API_BASE_URL}/api/powerflow/n-minus-1`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            signal
        });

        const data = await response.json();

        if (data.success) {
            currentNMinus1Results = data.results;
            window.currentNMinus1Results = currentNMinus1Results;
            const html = renderNMinus1HTML(data.results);
            // 更新固定标签内容并切换到该标签
            document.getElementById('pf-nminus1').innerHTML = html;
            activatePFTabByName('nminus1');
            updateStatus('status.nminus1_complete');
        } else {
            throw new Error(data.error);
        }
    } catch (error) {
        if (error.name === 'AbortError') {
            console.log('N-1 check was cancelled');
            return;
        }
        console.error('N-1 check error:', error);
        updateStatus('N-1校验失败');
        const errorMsg = window.translateErrorMessage ? window.translateErrorMessage(error.message) : error.message;
        alert((window.t ? window.t('alert.nminus1_failed') : 'N-1校验失败') + ': ' + errorMsg);
    } finally {
        showLoading(false);
    }
}

function renderNMinus1HTML(results) {
    const lang = window.t;

    let html = `<h3>${lang ? t('nminus1.results') : 'N-1校验结果'}</h3>`;
    html += `<p><strong>${lang ? t('nminus1.total') : '总计'}:</strong> ${results.total_lines} ${lang ? t('nminus1.lines') : '条线路'}</p>`;
    html += `<p><strong>${lang ? t('nminus1.status') : '状态'}:</strong> ${results.n_minus_1_passed ? `<span class="text-success">[${lang ? t('powerflow.passed') : '通过'}] ${lang ? t('nminus1.passed') : 'N-1校验'}</span>` : `<span class="text-danger">[${lang ? t('candidate.failed') : '未通过'}] ${lang ? t('nminus1.failed') : 'N-1校验'}</span>`}</p>`;

    if (results.critical_contingencies && results.critical_contingencies.length > 0) {
        html += `<h4>${lang ? t('nminus1.critical_contingencies') : '关键故障'}:</h4>`;
        results.critical_contingencies.slice(0, 8).forEach(c => {
            html += `<p class="text-warning">[${lang ? t('nminus1.contingency') : '故障'}] ${c.line_name} | ${lang ? t('nminus1.violations_count') : '违规数'}: ${c.violations ? c.violations.length : 'N/A'}</p>`;
        });
    }

    return html;
}

// --------- 网格叠加 ---------
function toggleGrid() {
    if (!map || !networkData) return;
    if (gridShown) {
        if (gridLayer) { map.removeLayer(gridLayer); gridLayer = null; }
        gridShown = false;
        updateStatus('status.grid_hidden');
        return;
    }

    const subs = networkData.substations || networkData.buses || [];
    const lines = networkData.lines || [];
    if (!subs.length || !lines.length) {
        updateStatus('status.no_grid_data');
        return;
    }
    const byId = {}; subs.forEach(s => { if (s && s.id) byId[s.id] = s; });

    gridLayer = L.layerGroup();
    lines.forEach(ln => {
        const fbId = typeof ln.from_bus === 'number' ? `bus_${ln.from_bus}` : ln.from_bus;
        const tbId = typeof ln.to_bus === 'number' ? `bus_${ln.to_bus}` : ln.to_bus;
        const fs = byId[fbId]; const ts = byId[tbId];
        if (!fs || !ts || !fs.location || !ts.location) return;
        const av = visualCoord(fs.location.lat, fs.location.lon);
        const bv = visualCoord(ts.location.lat, ts.location.lon);
        const loading = ln.loading_percent || 0;
        let color = '#10b981';
        if (loading > 90) color = '#ef4444'; else if (loading > 70) color = '#f59e0b';
        const poly = L.polyline([av, bv], { color, weight: 3, opacity: 0.85 }).addTo(gridLayer);
        const name = ln.name || `${fbId} - ${tbId}`;
        const lang = window.t;
        poly.bindPopup(`<div style="color:#1e293b;"><strong>${name}</strong><br>${lang ? t('load.loading_rate') : '负载率'}: ${Number(loading).toFixed(1)}%</div>`);
    });

    gridLayer.addTo(map);
    gridShown = true;
    updateStatus('status.grid_shown');
}

// 区域图层/生成已移除（回退到仅网格叠加模式）

// Delaunay 三角剖分算法 (Bowyer-Watson)
function delaunayTriangulation(points) {
    if (points.length < 3) return [];

    // 创建超级三角形包含所有点
    let minLat = Infinity, maxLat = -Infinity;
    let minLon = Infinity, maxLon = -Infinity;

    points.forEach(p => {
        minLat = Math.min(minLat, p.lat);
        maxLat = Math.max(maxLat, p.lat);
        minLon = Math.min(minLon, p.lon);
        maxLon = Math.max(maxLon, p.lon);
    });

    const dx = (maxLon - minLon) * 2;
    const dy = (maxLat - minLat) * 2;
    const midLat = (minLat + maxLat) / 2;
    const midLon = (minLon + maxLon) / 2;

    // 超级三角形的三个顶点
    const p1 = { lat: midLat - dy * 2, lon: midLon - dx, load: 0, isSuper: true };
    const p2 = { lat: midLat - dy * 2, lon: midLon + dx, load: 0, isSuper: true };
    const p3 = { lat: midLat + dy * 2, lon: midLon, load: 0, isSuper: true };

    let triangles = [[p1, p2, p3]];

    // 逐点插入
    points.forEach(point => {
        let badTriangles = [];
        let polygon = [];

        // 找出所有外接圆包含该点的三角形
        triangles.forEach(tri => {
            if (isPointInCircumcircle(point, tri)) {
                badTriangles.push(tri);
            }
        });

        // 找出多边形边界
        badTriangles.forEach(tri => {
            for (let i = 0; i < 3; i++) {
                const edge = [tri[i], tri[(i + 1) % 3]];
                let shared = false;

                badTriangles.forEach(other => {
                    if (other === tri) return;
                    for (let j = 0; j < 3; j++) {
                        const otherEdge = [other[j], other[(j + 1) % 3]];
                        if (edgesEqual(edge, otherEdge)) {
                            shared = true;
                            break;
                        }
                    }
                });

                if (!shared) {
                    polygon.push(edge);
                }
            }
        });

        // 移除坏三角形
        triangles = triangles.filter(tri => !badTriangles.includes(tri));

        // 用新点和多边形边界创建新三角形
        polygon.forEach(edge => {
            triangles.push([edge[0], edge[1], point]);
        });
    });

    // 移除包含超级三角形顶点的三角形
    triangles = triangles.filter(tri => {
        return !tri.some(p => p.isSuper);
    });

    return triangles;
}

// 检查点是否在三角形外接圆内
function isPointInCircumcircle(point, triangle) {
    const [a, b, c] = triangle;

    const ax = a.lon - point.lon;
    const ay = a.lat - point.lat;
    const bx = b.lon - point.lon;
    const by = b.lat - point.lat;
    const cx = c.lon - point.lon;
    const cy = c.lat - point.lat;

    const det = (ax * ax + ay * ay) * (bx * cy - cx * by)
              - (bx * bx + by * by) * (ax * cy - cx * ay)
              + (cx * cx + cy * cy) * (ax * by - bx * ay);

    // 检查三角形方向
    const orientation = (a.lon - c.lon) * (b.lat - c.lat) - (a.lat - c.lat) * (b.lon - c.lon);

    return orientation > 0 ? det > 0 : det < 0;
}

// 检查两条边是否相等
function edgesEqual(e1, e2) {
    return (e1[0] === e2[0] && e1[1] === e2[1]) ||
           (e1[0] === e2[1] && e1[1] === e2[0]);
}

// 发送聊天消息
async function sendChatMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();

    if (!message) return;

    // 添加用户消息
    addChatMessage(message, 'user');
    input.value = '';

    try {
        const response = await fetch(`${API_BASE_URL}/api/llm/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                messages: [
                    { role: 'system', content: '你是一个电网规划专家助手。' },
                    { role: 'user', content: message }
                ]
            })
        });

        const data = await response.json();

        if (data.success) {
            addChatMessage(data.response, 'assistant');
        } else {
            addChatMessage('抱歉,处理消息时出错。', 'assistant');
        }
    } catch (error) {
        console.error('Chat error:', error);
        addChatMessage('抱歉,无法连接到服务器。', 'assistant');
    }
}

// ---------------- LLM 文档分析（基础版） ----------------
let lastUploadedDocId = null;
let lastParsedConstraints = null;

async function uploadAndParseDoc() {
    try {
        const fileInput = document.getElementById('llmFile');
        if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
            alert(window.t ? window.t('alert.select_file_first') : '请先选择要上传的文件（PDF/TXT）。');
            return;
        }
        const file = fileInput.files[0];
        showLoading(true);
        updateStatus('上传并解析文档...');
        // 上传
        const form = new FormData();
        form.append('file', file);
        const upRes = await fetch(`${API_BASE_URL}/api/uploads`, { method: 'POST', body: form });
        const upData = await upRes.json();
        if (!upData.success) throw new Error(upData.error || '上传失败');
        lastUploadedDocId = upData.doc_id;
        // 解析
        const parRes = await fetch(`${API_BASE_URL}/api/constraints/parse_file`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ doc_id: lastUploadedDocId })
        });
        const parData = await parRes.json();
        if (!parData.success) throw new Error(parData.error || '解析失败');
        lastParsedConstraints = parData.constraints;
        // 展示
        const box = document.getElementById('llmParseResult');
        box.innerHTML = `<pre style="white-space:pre-wrap;">${escapeHtml(JSON.stringify(lastParsedConstraints, null, 2)).slice(0, 10000)}</pre>`;
        updateStatus('解析完成');
        alert(window.t ? window.t('alert.parse_complete') : '解析完成。可点击"应用至系统"。');
    } catch (e) {
        console.error('uploadAndParseDoc error:', e);
        const errorMsg = window.translateErrorMessage ? window.translateErrorMessage(e.message) : e.message;
        alert((window.t ? window.t('alert.upload_parse_failed') : '上传/解析失败') + '：' + errorMsg);
        updateStatus('上传/解析失败');
    } finally {
        showLoading(false);
    }
}

async function applyParsedConstraints() {
    try {
        if (!lastParsedConstraints) {
            alert(window.t ? window.t('alert.complete_parse_first') : '请先完成文档解析');
            return;
        }
        showLoading(true);
        updateStatus('应用约束到系统...');
        // 兼容：LLM返回 [ {..} ] 的情况
        let payload = lastParsedConstraints;
        if (Array.isArray(payload) && payload.length === 1 && typeof payload[0] === 'object') {
            payload = payload[0];
        }
        const res = await fetch(`${API_BASE_URL}/api/constraints/apply`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ constraints: payload })
        });
        const data = await res.json();
        if (!data.success) throw new Error(data.error || '应用失败');
        const box = document.getElementById('llmParseResult');
        const applied = JSON.stringify(data.applied || {}, null, 2);
        box.innerHTML += `<hr><div>已应用覆盖项：</div><pre style="white-space:pre-wrap;">${escapeHtml(applied)}</pre>`;
        updateStatus('约束已应用');
        alert(window.t ? window.t('alert.constraints_applied') : '约束已应用。建议重新运行分析/潮流以查看阈值变化效果。');
    } catch (e) {
        console.error('applyParsedConstraints error:', e);
        const errorMsg = window.translateErrorMessage ? window.translateErrorMessage(e.message) : e.message;
        alert((window.t ? window.t('alert.apply_failed') : '应用失败') + '：' + errorMsg);
        updateStatus('应用失败');
    } finally {
        showLoading(false);
    }
}

async function resetConstraintsOverrides() {
    try {
        showLoading(true);
        updateStatus('重置覆盖项...');
        const res = await fetch(`${API_BASE_URL}/api/constraints/reset`, { method: 'POST' });
        const data = await res.json();
        if (!data.success) throw new Error(data.error || '重置失败');
        const box = document.getElementById('llmParseResult');
        box.innerHTML += `<hr><div>已重置覆盖项。</div>`;
        updateStatus('已重置覆盖项');
    } catch (e) {
        console.error('resetConstraintsOverrides error:', e);
        const errorMsg = window.translateErrorMessage ? window.translateErrorMessage(e.message) : e.message;
        alert((window.t ? window.t('alert.reset_failed') : '重置失败') + '：' + errorMsg);
        updateStatus('重置失败');
    } finally {
        showLoading(false);
    }
}

function escapeHtml(s) {
    return String(s).replace(/[&<>]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[ch]));
}

// 添加聊天消息
function addChatMessage(text, role) {
    const container = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${role}`;
    messageDiv.textContent = text;
    container.appendChild(messageDiv);
    container.scrollTop = container.scrollHeight;
}

// 导出函数和变量到全局作用域，供i18n使用
window.displayLoadSummary = displayLoadSummary;
window.displayTopology = displayTopology;
window.displayCandidates = displayCandidates;
window.displayConstraints = displayConstraints;
window.renderPowerFlowHTML = renderPowerFlowHTML;
window.renderNMinus1HTML = renderNMinus1HTML;
