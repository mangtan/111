// 国际化配置
const translations = {
    'zh': {
        // 页面标题
        'header.title': '智能电网规划系统',

        // 左侧面板
        'left.system_control': '系统控制',
        'left.btn_analyze': '运行完整分析',
        'left.btn_load_data': '加载数据',
        'left.btn_powerflow': '潮流计算',
        'left.btn_nminus1': 'N-1校验',
        'left.btn_toggle_grid': '切换基线连线',
        'left.load_summary': '负载摘要',
        'left.load_summary_hint': '点击"加载数据"获取负载信息...',
        'left.candidate_ranking': '候选方案排名',
        'left.candidate_ranking_hint': '等待分析结果...',

        // 中间面板
        'center.tab_map': '电网拓扑地图',
        'center.tab_chart': '负载预测曲线',

        // 右侧面板
        'right.powerflow_validation': '潮流与校验',
        'right.powerflow': '潮流计算',
        'right.nminus1': 'N-1校验',
        'right.powerflow_hint': '点击"潮流计算"按钮获取结果',
        'right.nminus1_hint': '点击"N-1校验"按钮获取结果',
        'right.constraint_check': '约束检查',
        'right.constraint_hint': '等待分析...',
        'right.topology_analysis': '拓扑分析',
        'right.topology_hint': '等待数据...',
        'right.llm_chat': 'LLM交互',
        'right.chat_placeholder': '输入问题咨询AI助手...',
        'right.btn_send': '发送',

        // 状态和消息
        'status.ready': '系统就绪',
        'status.loading': '加载数据中...',
        'status.analyzing': '运行完整分析...',
        'status.powerflow': '运行潮流计算...',
        'status.nminus1': '运行N-1校验...',
        'status.complete': '操作完成',
        'status.cancelled': '操作已取消',
        'status.data_loaded': '数据加载完成',
        'status.analysis_complete': '分析完成',
        'status.powerflow_complete': '潮流计算完成',
        'status.nminus1_complete': 'N-1校验完成',
        'status.grid_shown': '已显示基线连线',
        'status.grid_hidden': '已隐藏基线连线',
        'status.no_grid_data': '无可显示的基线连线',

        // API状态
        'api.connected': 'API: 已连接',
        'api.disconnected': 'API: 连接失败',

        // 负载摘要
        'load.current_features': '当前特征',
        'load.avg_load': '平均负载',
        'load.max_load': '最大负载',
        'load.growth_rate': '增长率',
        'load.peak_hour': '峰值时段',
        'load.overload_areas': '过载区域',
        'load.loading_rate': '负载率',
        'load.priority': '优先级',
        'load.priority.high': '高',
        'load.priority.medium': '中',
        'load.priority.low': '低',

        // 候选方案
        'candidate.new_substation': '新建变电站',
        'candidate.substation_expansion': '变电站扩容',
        'candidate.new_line': '新建线路',
        'candidate.area': '区域',
        'candidate.total_score': '综合评分',
        'candidate.load_score': '负载得分',
        'candidate.distance_score': '距离得分',
        'candidate.topology_score': '拓扑得分',
        'candidate.constraint_score': '约束得分',
        'candidate.estimated_cost': '估算成本',
        'candidate.passed': '通过',
        'candidate.failed': '未通过',
        'candidate.powerflow_validation': '潮流验证',
        'candidate.preview': '在地图上预览',
        'candidate.rank': '排名',
        'candidate.reinforcement': '并联加固',
        'candidate.interconnection': '新建联络',

        // 地图预览
        'preview.new_line': '新建线路',
        'preview.new_substation': '新建变电站',
        'preview.substation_expansion': '变电站扩容',
        'preview.voltage': '电压',
        'preview.capacity': '容量',
        'preview.additional_capacity': '新增容量',
        'preview.connect_to': '连接至',
        'preview.from': '起点',

        // 拓扑信息
        'topology.total_substations': '变电站数量',
        'topology.total_lines': '线路数量',
        'topology.avg_degree': '平均连接度',
        'topology.critical_nodes': '关键节点',
        'topology.weak_nodes': '薄弱节点',
        'topology.degree': '度数',

        // Loading
        'loading.message': '数据处理中，请稍候...',
        'loading.cancel': '取消',

        // Power Flow Results
        'powerflow.bus_results': '母线结果',
        'powerflow.transformer_load': '变压器负载',
        'powerflow.line_load': '线路负载',
        'powerflow.violations': '违规项',
        'powerflow.no_violations': '无违规项',
        'powerflow.not_converged': '潮流计算未收敛',
        'powerflow.voltage': '电压',
        'powerflow.power': '功率',
        'powerflow.loading_rate': '负载率',
        'powerflow.passed': '通过',
        'powerflow.warning': '警告',
        'powerflow.transformer': '变压器',
        'powerflow.line': '线路',

        // N-1 Check Results
        'nminus1.results': 'N-1校验结果',
        'nminus1.total': '总计',
        'nminus1.lines': '条线路',
        'nminus1.status': '状态',
        'nminus1.passed': 'N-1校验',
        'nminus1.failed': 'N-1校验',
        'nminus1.critical_contingencies': '关键故障',
        'nminus1.contingency': '故障',
        'nminus1.violations_count': '违规数',

        // Constraints
        'constraints.title': '约束条件',
        'constraints.parsing': '约束解析中...',
        'constraints.none': '暂无约束信息',

        // LLM Document Analysis
        'llm.doc_analysis': 'LLM 文档分析',
        'llm.doc_description': '上传官方标准/手册（PDF/TXT），解析为结构化约束并一键应用。',
        'llm.select_file': '选择文件',
        'llm.no_file_selected': '未选择文件',
        'llm.btn_upload': '上传并解析',
        'llm.btn_apply': '应用至系统',
        'llm.btn_reset': '重置覆盖',
        'llm.no_document': '尚未解析文档。',

        // Alert Messages
        'alert.load_data_failed': '加载数据失败',
        'alert.analysis_complete': '完整分析已完成！',
        'alert.analysis_failed': '分析失败',
        'alert.powerflow_failed': '潮流计算失败',
        'alert.nminus1_failed': 'N-1校验失败',
        'alert.select_file_first': '请先选择要上传的文件（PDF/TXT）。',
        'alert.parse_complete': '解析完成。可点击"应用至系统"。',
        'alert.upload_parse_failed': '上传/解析失败',
        'alert.complete_parse_first': '请先完成文档解析',
        'alert.constraints_applied': '约束已应用。建议重新运行分析/潮流以查看阈值变化效果。',
        'alert.apply_failed': '应用失败',
        'alert.reset_failed': '重置失败'
    },
    'en': {
        // Header
        'header.title': 'Intelligent Grid Planning System',

        // Left Panel
        'left.system_control': 'System Control',
        'left.btn_analyze': 'Run Complete Analysis',
        'left.btn_load_data': 'Load Data',
        'left.btn_powerflow': 'Power Flow',
        'left.btn_nminus1': 'N-1 Check',
        'left.btn_toggle_grid': 'Toggle Baseline Lines',
        'left.load_summary': 'Load Summary',
        'left.load_summary_hint': 'Click "Load Data" to get load information...',
        'left.candidate_ranking': 'Candidate Ranking',
        'left.candidate_ranking_hint': 'Waiting for analysis results...',

        // Center Panel
        'center.tab_map': 'Grid Topology Map',
        'center.tab_chart': 'Load Forecast Curve',

        // Right Panel
        'right.powerflow_validation': 'Power Flow & Validation',
        'right.powerflow': 'Power Flow',
        'right.nminus1': 'N-1 Check',
        'right.powerflow_hint': 'Click "Power Flow" button to get results',
        'right.nminus1_hint': 'Click "N-1 Check" button to get results',
        'right.constraint_check': 'Constraint Check',
        'right.constraint_hint': 'Waiting for analysis...',
        'right.topology_analysis': 'Topology Analysis',
        'right.topology_hint': 'Waiting for data...',
        'right.llm_chat': 'LLM Chat',
        'right.chat_placeholder': 'Ask AI assistant a question...',
        'right.btn_send': 'Send',

        // Status Messages
        'status.ready': 'System Ready',
        'status.loading': 'Loading data...',
        'status.analyzing': 'Running complete analysis...',
        'status.powerflow': 'Running power flow...',
        'status.nminus1': 'Running N-1 check...',
        'status.complete': 'Operation complete',
        'status.cancelled': 'Operation cancelled',
        'status.data_loaded': 'Data loaded',
        'status.analysis_complete': 'Analysis complete',
        'status.powerflow_complete': 'Power flow complete',
        'status.nminus1_complete': 'N-1 check complete',
        'status.grid_shown': 'Baseline lines shown',
        'status.grid_hidden': 'Baseline lines hidden',
        'status.no_grid_data': 'No displayable baseline connections',

        // API Status
        'api.connected': 'API: Connected',
        'api.disconnected': 'API: Connection Failed',

        // Load Summary
        'load.current_features': 'Current Features',
        'load.avg_load': 'Average Load',
        'load.max_load': 'Max Load',
        'load.growth_rate': 'Growth Rate',
        'load.peak_hour': 'Peak Hour',
        'load.overload_areas': 'Overload Areas',
        'load.loading_rate': 'Loading Rate',
        'load.priority': 'Priority',
        'load.priority.high': 'High',
        'load.priority.medium': 'Medium',
        'load.priority.low': 'Low',

        // Candidates
        'candidate.new_substation': 'New Substation',
        'candidate.substation_expansion': 'Substation Expansion',
        'candidate.new_line': 'New Line',
        'candidate.area': 'Area',
        'candidate.total_score': 'Total Score',
        'candidate.load_score': 'Load Score',
        'candidate.distance_score': 'Distance Score',
        'candidate.topology_score': 'Topology Score',
        'candidate.constraint_score': 'Constraint Score',
        'candidate.estimated_cost': 'Estimated Cost',
        'candidate.passed': 'Passed',
        'candidate.failed': 'Failed',
        'candidate.powerflow_validation': 'Power Flow Validation',
        'candidate.preview': 'Preview on Map',
        'candidate.rank': 'Rank',
        'candidate.reinforcement': 'Reinforcement',
        'candidate.interconnection': 'New Interconnection',

        // Preview
        'preview.new_line': 'New Line',
        'preview.new_substation': 'New Substation',
        'preview.substation_expansion': 'Substation Expansion',
        'preview.voltage': 'Voltage',
        'preview.capacity': 'Capacity',
        'preview.additional_capacity': 'Additional Capacity',
        'preview.connect_to': 'Connect to',
        'preview.from': 'From',

        // Topology
        'topology.total_substations': 'Total Substations',
        'topology.total_lines': 'Total Lines',
        'topology.avg_degree': 'Average Degree',
        'topology.critical_nodes': 'Critical Nodes',
        'topology.weak_nodes': 'Weak Nodes',
        'topology.degree': 'Degree',

        // Loading
        'loading.message': 'Processing data, please wait...',
        'loading.cancel': 'Cancel',

        // Power Flow Results
        'powerflow.bus_results': 'Bus Results',
        'powerflow.transformer_load': 'Transformer Load',
        'powerflow.line_load': 'Line Load',
        'powerflow.violations': 'Violations',
        'powerflow.no_violations': 'No Violations',
        'powerflow.not_converged': 'Power flow not converged',
        'powerflow.voltage': 'Voltage',
        'powerflow.power': 'Power',
        'powerflow.loading_rate': 'Loading Rate',
        'powerflow.passed': 'Passed',
        'powerflow.warning': 'Warning',
        'powerflow.transformer': 'Transformer',
        'powerflow.line': 'Line',

        // N-1 Check Results
        'nminus1.results': 'N-1 Check Results',
        'nminus1.total': 'Total',
        'nminus1.lines': 'Lines',
        'nminus1.status': 'Status',
        'nminus1.passed': 'N-1 Check',
        'nminus1.failed': 'N-1 Check',
        'nminus1.critical_contingencies': 'Critical Contingencies',
        'nminus1.contingency': 'Contingency',
        'nminus1.violations_count': 'Violations',

        // Constraints
        'constraints.title': 'Constraint Conditions',
        'constraints.parsing': 'Parsing constraints...',
        'constraints.none': 'No constraint information',

        // LLM Document Analysis
        'llm.doc_analysis': 'LLM Document Analysis',
        'llm.doc_description': 'Upload official standards/manuals (PDF/TXT), parse to structured constraints and apply with one click.',
        'llm.select_file': 'Select File',
        'llm.no_file_selected': 'No file selected',
        'llm.btn_upload': 'Upload & Parse',
        'llm.btn_apply': 'Apply to System',
        'llm.btn_reset': 'Reset Override',
        'llm.no_document': 'No document parsed yet.',

        // Alert Messages
        'alert.load_data_failed': 'Failed to load data',
        'alert.analysis_complete': 'Complete analysis finished!',
        'alert.analysis_failed': 'Analysis failed',
        'alert.powerflow_failed': 'Power flow calculation failed',
        'alert.nminus1_failed': 'N-1 check failed',
        'alert.select_file_first': 'Please select a file to upload (PDF/TXT).',
        'alert.parse_complete': 'Parsing complete. Click "Apply to System" to proceed.',
        'alert.upload_parse_failed': 'Upload/parse failed',
        'alert.complete_parse_first': 'Please complete document parsing first',
        'alert.constraints_applied': 'Constraints applied. Re-run analysis/power flow to see threshold changes.',
        'alert.apply_failed': 'Apply failed',
        'alert.reset_failed': 'Reset failed'
    }
};

// 当前语言
let currentLanguage = localStorage.getItem('language') || 'zh';

// 翻译函数
function t(key) {
    return translations[currentLanguage][key] || key;
}

// 更新页面所有文本
function updatePageLanguage() {
    // 更新所有带data-i18n属性的元素
    document.querySelectorAll('[data-i18n]').forEach(element => {
        const key = element.getAttribute('data-i18n');
        element.textContent = t(key);
    });

    // 更新placeholder
    document.querySelectorAll('[data-i18n-placeholder]').forEach(element => {
        const key = element.getAttribute('data-i18n-placeholder');
        element.placeholder = t(key);
    });

    // 更新页面标题
    document.title = t('header.title');

    // 更新语言按钮文本
    document.getElementById('langText').textContent = currentLanguage === 'zh' ? '中文' : 'English';

    // 更新图表标签（如果已初始化）
    if (window.loadChart) {
        loadChart.data.datasets[0].label = currentLanguage === 'zh' ? '预测负载 (MW)' : 'Predicted Load (MW)';
        loadChart.options.scales.y.title.text = currentLanguage === 'zh' ? '负载 (MW)' : 'Load (MW)';
        loadChart.update();
    }

    // 重新渲染已加载的动态内容
    if (window.currentAnalysis) {
        // 如果有分析数据，重新显示
        if (window.currentAnalysis.load_summary) {
            window.displayLoadSummary(window.currentAnalysis.load_summary);
        }
        if (window.currentAnalysis.network_topology) {
            window.displayTopology(window.currentAnalysis.network_topology);
        }
        if (window.currentAnalysis.validated_candidates) {
            window.displayCandidates(window.currentAnalysis.validated_candidates);
        }
    } else {
        // 如果没有分析数据，但有单独加载的数据，也要更新
        if (window.currentLoadSummary) {
            window.displayLoadSummary(window.currentLoadSummary);
        }
        if (window.currentTopology) {
            window.displayTopology(window.currentTopology);
        }
    }

    // 重新渲染潮流计算结果
    if (window.currentPowerFlowResults && window.renderPowerFlowHTML) {
        const html = window.renderPowerFlowHTML(window.currentPowerFlowResults);
        const pfPanel = document.getElementById('pf-powerflow');
        if (pfPanel && !pfPanel.textContent.includes('点击') && !pfPanel.textContent.includes('Click')) {
            pfPanel.innerHTML = html;
        }
    }

    // 重新渲染 N-1 校验结果
    if (window.currentNMinus1Results && window.renderNMinus1HTML) {
        const html = window.renderNMinus1HTML(window.currentNMinus1Results);
        const n1Panel = document.getElementById('pf-nminus1');
        if (n1Panel && !n1Panel.textContent.includes('点击') && !n1Panel.textContent.includes('Click')) {
            n1Panel.innerHTML = html;
        }
    }

    // 重新渲染约束检查
    if (window.currentConstraints && window.displayConstraints) {
        window.displayConstraints(window.currentConstraints);
    }

    // 更新文件选择显示
    const fileNameSpan = document.getElementById('selectedFileName');
    const llmFileInput = document.getElementById('llmFile');
    if (fileNameSpan && llmFileInput) {
        if (!llmFileInput.files || llmFileInput.files.length === 0) {
            fileNameSpan.textContent = window.t('llm.no_file_selected');
        }
        // 如果已选择文件，保持文件名不变
    }

    // 更新API状态文本
    const apiStatus = document.getElementById('apiStatus');
    if (apiStatus && apiStatus.classList.contains('connected')) {
        apiStatus.textContent = t('api.connected');
    } else if (apiStatus) {
        apiStatus.textContent = t('api.disconnected');
    }

    // 更新状态文本（如果不是默认的"系统就绪"）
    const statusText = document.getElementById('statusText');
    if (statusText) {
        const currentStatus = statusText.textContent;
        // 尝试匹配并更新常见的状态消息
        if (currentStatus.includes('就绪') || currentStatus.includes('Ready')) {
            statusText.textContent = t('status.ready');
        } else if (currentStatus.includes('完成') || currentStatus.includes('complete')) {
            statusText.textContent = t('status.complete');
        } else if (currentStatus.includes('取消') || currentStatus.includes('cancelled')) {
            statusText.textContent = t('status.cancelled');
        }
    }
}

// 切换语言
function toggleLanguage() {
    currentLanguage = currentLanguage === 'zh' ? 'en' : 'zh';
    localStorage.setItem('language', currentLanguage);
    updatePageLanguage();
}

// 导出函数供全局使用
window.t = t;
window.toggleLanguage = toggleLanguage;
window.updatePageLanguage = updatePageLanguage;
window.currentLanguage = () => currentLanguage;

// 变电站名称翻译函数
function translateStationName(chineseName) {
    // 获取当前语言
    const lang = currentLanguage;
    if (lang !== 'en') return chineseName;

    // 地名翻译映射
    const locationMap = {
        '天河': 'Tianhe',
        '黄埔': 'Huangpu',
        '越秀': 'Yuexiu',
        '海珠': 'Haizhu',
        '白云': 'Baiyun',
        '番禺': 'Panyu',
        '花都': 'Huadu',
        '增城': 'Zengcheng',
        '从化': 'Conghua',
        '南沙': 'Nansha',
        '荔湾': 'Liwan',
        '城东': 'East District',
        '城西': 'West District',
        '城南': 'South District',
        '城北': 'North District',
        '开发区': 'Development Zone'
    };

    // 术语翻译
    const termMap = {
        '主变': 'Main Substation',
        '变': 'Substation',
        '变电站': 'Substation',
        '区': 'District'
    };

    let translated = chineseName;

    // 翻译地名
    for (const [cn, en] of Object.entries(locationMap)) {
        if (translated.includes(cn)) {
            translated = translated.replace(cn, en);
        }
    }

    // 翻译术语
    for (const [cn, en] of Object.entries(termMap)) {
        translated = translated.replace(cn, en);
    }

    return translated;
}

// 获取当前语言的函数
function getCurrentLanguage() {
    return currentLanguage;
}

// 文档名称翻译函数
function translateDocumentName(chineseName) {
    const lang = currentLanguage;
    if (lang !== 'en') return chineseName;

    // 文档类型翻译映射
    const docTermMap = {
        '地方': 'Local',
        '电网': 'Power Grid',
        '规划': 'Planning',
        '政策': 'Policy',
        '扩展': 'Expansion',
        '手册': 'Manual',
        '标准': 'Standard',
        '规范': 'Specification',
        '技术': 'Technical',
        '安全': 'Safety',
        '运行': 'Operation',
        '管理': 'Management',
        '设计': 'Design',
        '施工': 'Construction',
        '验收': 'Acceptance',
        '维护': 'Maintenance'
    };

    let translated = chineseName;

    // 翻译文档名称中的关键词
    for (const [cn, en] of Object.entries(docTermMap)) {
        translated = translated.replace(new RegExp(cn, 'g'), en);
    }

    // 保留文件扩展名
    return translated;
}

window.translateStationName = translateStationName;
window.getCurrentLanguage = getCurrentLanguage;
window.translateDocumentName = translateDocumentName;

// 后端错误消息映射
const errorMessageMap = {
    'zh': {
        'LLM未输出有效JSON，请调整文档或重试': 'LLM未输出有效JSON，请调整文档或重试',
        '缺少文件字段 file': '缺少文件字段 file',
        '文件名为空': '文件名为空',
        '缺少 doc_id': '缺少 doc_id',
        '未找到文件': '未找到文件',
        '解析结果为列表且无法识别可应用字段': '解析结果为列表且无法识别可应用字段',
        '解析结果不是结构化JSON': '解析结果不是结构化JSON',
        '上传失败': '上传失败',
        '解析失败': '解析失败',
        '应用失败': '应用失败',
        '重置失败': '重置失败'
    },
    'en': {
        'LLM未输出有效JSON，请调整文档或重试': 'LLM did not output valid JSON, please adjust the document or retry',
        '缺少文件字段 file': 'Missing file field',
        '文件名为空': 'File name is empty',
        '缺少 doc_id': 'Missing doc_id',
        '未找到文件': 'File not found',
        '解析结果为列表且无法识别可应用字段': 'Parse result is a list and no applicable fields can be identified',
        '解析结果不是结构化JSON': 'Parse result is not structured JSON',
        '上传失败': 'Upload failed',
        '解析失败': 'Parse failed',
        '应用失败': 'Apply failed',
        '重置失败': 'Reset failed'
    }
};

// 翻译错误消息函数
function translateErrorMessage(errorMessage) {
    if (currentLanguage === 'zh') {
        return errorMessage;
    }

    // 尝试完整匹配
    if (errorMessageMap.en[errorMessage]) {
        return errorMessageMap.en[errorMessage];
    }

    // 尝试部分匹配（处理包含变量的错误消息，如 "未找到文件: xxx.pdf"）
    for (const [zhKey, enValue] of Object.entries(errorMessageMap.en)) {
        if (errorMessage.includes(zhKey)) {
            return errorMessage.replace(zhKey, enValue);
        }
    }

    return errorMessage;
}

window.translateErrorMessage = translateErrorMessage;
