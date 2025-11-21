"""
主应用程序 - Flask REST API
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import traceback
from config import Config

# 导入服务
from services.llm_service import llm_service
from services.retrieval_service import retrieval_service
from services.load_prediction import load_prediction
from services.gis_service import gis_service
from services.scorer import scorer
from services.power_flow import power_flow
from werkzeug.utils import secure_filename
import os
from services.doc_ingest import extract_text, rag_select
from services.settings_service import settings


app = Flask(__name__)
CORS(app)  # 允许跨域请求


@app.route('/')
def index():
    """首页"""
    return jsonify({
        'name': 'Grid Planning System',
        'version': '1.0.0',
        'description': 'LLM + GIS + Load Forecasting integrated grid planning system'
    })


# --------------------- 上传/解析/应用 约束（基础版） ---------------------
@app.route('/api/uploads', methods=['POST'])
def upload_document():
    """接收文件上传，保存到 data/documents/uploads，并返回 doc_id、基本信息。"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': '缺少文件字段 file'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': '文件名为空'}), 400
        fname = secure_filename(file.filename)
        uploads_dir = os.path.join(Config.DATA_DIR, 'documents', 'uploads')
        os.makedirs(uploads_dir, exist_ok=True)
        save_path = os.path.join(uploads_dir, fname)
        file.save(save_path)

        # 基础文本化（PDF/TXT）
        text, pages = extract_text(save_path)
        # 将文本保存为同名txt，便于检索与后续处理
        try:
            txt_out = os.path.join(uploads_dir, fname + '.txt')
            with open(txt_out, 'w', encoding='utf-8') as f:
                f.write(text)
        except Exception:
            pass
        # 为避免响应过大，返回前 10000 字预览
        preview = text[:10000]
        doc_id = fname

        return jsonify({
            'success': True,
            'doc_id': doc_id,
            'filename': fname,
            'path': save_path,
            'pages': pages,
            'text_preview': preview,
            'text_length': len(text)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/constraints/parse_file', methods=['POST'])
def parse_constraints_from_file():
    """对已上传文件进行文本化并调用 LLM 解析为结构化约束（基础版）。"""
    try:
        data = request.json or {}
        doc_id = data.get('doc_id')
        if not doc_id:
            return jsonify({'success': False, 'error': '缺少 doc_id'}), 400
        uploads_dir = os.path.join(Config.DATA_DIR, 'documents', 'uploads')
        file_path = os.path.join(uploads_dir, doc_id)
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'error': f'未找到文件: {doc_id}'}), 404

        text, _ = extract_text(file_path)
        # 简易RAG：从文档中筛选与约束相关的片段再解析，提升长文稳定性
        queries = [
            '电压 偏差 允许 范围 kV %',
            '线路 负载 率 限值 % 运行 N-1',
            '变压器 负载 限值 % 主变',
            'N-1 安全 准则 校验',
            '安全 距离 线路 建筑 变电站 km',
            '电压 等级 kV 范围'
        ]
        selected = rag_select(text, queries, per_query=3, max_chars=7000)
        constraints = llm_service.parse_constraints(selected)
        return jsonify({'success': True, 'constraints': constraints, 'rag': True, 'selected_len': len(selected)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/constraints/apply', methods=['POST'])
def apply_constraints_api():
    """应用 LLM 解析出来的约束到运行态阈值（仅覆盖已识别到的键）。"""
    try:
        data = request.json or {}
        constraints = data.get('constraints') or {}
        # 结构校验与容错：
        # - 如果是 list，尝试：
        #   1) list 只有一个 dict -> 取该 dict
        #   2) list 有多个 dict -> 合并已知字段（voltage_constraints/line_loading/trafo_loading/n_minus_1/voltage_levels/distance_constraints）
        # - 如果是 dict，直接使用
        def _merge_known_fields(items):
            merged = {}
            keys = ['voltage_constraints', 'line_loading', 'trafo_loading', 'n_minus_1', 'n-1', 'voltage_levels', 'distance_constraints']
            for it in items:
                if not isinstance(it, dict):
                    continue
                for k in keys:
                    if k in it and it[k] is not None and k not in merged:
                        merged[k] = it[k]
            return merged

        if isinstance(constraints, list):
            constraints = [c for c in constraints if c is not None]
            if len(constraints) == 1 and isinstance(constraints[0], dict):
                constraints = constraints[0]
            else:
                merged = _merge_known_fields(constraints)
                if not merged:
                    return jsonify({'success': False, 'error': '解析结果为列表且无法识别可应用字段'}), 400
                constraints = merged

        if not isinstance(constraints, dict):
            return jsonify({'success': False, 'error': '解析结果不是结构化JSON（dict）', 'got_type': str(type(constraints))}), 400
        if constraints.get('parsed') is False and constraints.get('raw_text'):
            return jsonify({'success': False, 'error': 'LLM未输出有效JSON，请调整文档或重试'}), 400
        applied = settings.apply_constraints(constraints)
        return jsonify({'success': True, 'applied': applied, 'overrides': settings.all()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/constraints/reset', methods=['POST'])
def reset_constraints_api():
    try:
        overrides = settings.reset()
        return jsonify({'success': True, 'overrides': overrides})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/documents', methods=['GET'])
def get_documents():
    """获取所有文档"""
    try:
        documents = retrieval_service.get_all_documents()
        return jsonify({
            'success': True,
            'documents': documents
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/documents/search', methods=['POST'])
def search_documents():
    """搜索文档"""
    try:
        data = request.json
        query = data.get('query', '')
        top_k = data.get('top_k', 3)

        results = retrieval_service.search(query, top_k)

        return jsonify({
            'success': True,
            'query': query,
            'results': results
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/constraints/parse', methods=['POST'])
def parse_constraints():
    """解析约束条件"""
    try:
        data = request.json
        document_text = data.get('document_text', '')

        constraints = llm_service.parse_constraints(document_text)

        return jsonify({
            'success': True,
            'constraints': constraints
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/load/summary', methods=['GET'])
def get_load_summary():
    """获取负载摘要"""
    try:
        summary = load_prediction.get_load_summary()

        return jsonify({
            'success': True,
            'summary': summary
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/load/predict', methods=['POST'])
def predict_load():
    """预测负载"""
    try:
        data = request.json
        horizon_days = data.get('horizon_days', 365)

        prediction = load_prediction.predict_future_load(horizon_days)

        # pandas 的 Timestamp 无法直接 JSON 序列化，转换为 ISO 字符串
        # 仅对该接口做最小侵入式处理，保持前端字段名不变
        pred_serializable = prediction.copy()
        if 'timestamp' in pred_serializable.columns:
            # 使用 ISO-8601 字符串，前端可被各浏览器的 Date 正确解析
            try:
                pred_serializable['timestamp'] = pred_serializable['timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S')
            except Exception:
                # 回退方案，至少保证可序列化
                pred_serializable['timestamp'] = pred_serializable['timestamp'].astype(str)

        return jsonify({
            'success': True,
            'prediction': pred_serializable.to_dict(orient='records')
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/gis/network', methods=['GET'])
def get_network():
    """获取电网拓扑"""
    try:
        network = gis_service.get_network_summary()

        return jsonify({
            'success': True,
            'network': network
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/gis/zones', methods=['GET'])
def get_zones():
    """获取区域划分（GeoJSON）"""
    try:
        zones = gis_service.get_zones_geojson()
        return jsonify({'success': True, 'zones': zones})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/gis/zones/generate', methods=['POST'])
def generate_zones():
    """按rows/cols生成规则区域网格并保存"""
    try:
        data = request.json or {}
        rows = int(data.get('rows', 6))
        cols = int(data.get('cols', 10))
        zones = gis_service.generate_zones_grid(rows, cols)
        return jsonify({'success': True, 'zones': zones, 'rows': rows, 'cols': cols})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/gis/zones/clear', methods=['POST'])
def clear_zones():
    try:
        ok = gis_service.clear_zones()
        return jsonify({'success': True, 'cleared': ok})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/planning/analyze', methods=['POST'])
def analyze_planning():
    """完整的规划分析流程"""
    try:
        # 1. 获取负载摘要
        load_summary = load_prediction.get_load_summary()
        load_features = load_summary['current_features']
        overload_areas = load_summary['overload_areas']

        # 2. 获取GIS数据和拓扑
        network = gis_service.get_network_summary()
        topology = network['topology']

        # 3. 搜索相关约束文档
        constraint_docs = retrieval_service.search("电网规划标准约束", top_k=3)

        # 4. 使用LLM解析约束
        all_constraints = {}
        for doc in constraint_docs:
            constraints = llm_service.parse_constraints(doc['content'])
            all_constraints[doc['filename']] = constraints

        # 5. 生成候选方案
        candidates = gis_service.get_expansion_candidates(overload_areas)

        # 6. 使用评分器排名候选方案
        if getattr(Config, 'DEMO_DIVERSIFY_TOPK', False):
            # 演示模式：先全量排序，再做类型多样化选取
            ranked_candidates_full = scorer.rank_candidates(
                candidates,
                load_features,
                network,
                topology,
                all_constraints,
                top_k=len(candidates)  # 全量排序，便于后续挑选不同类型
            )

            # 类型多样化：确保Top-K内尽量覆盖 new_line / new_substation / substation_expansion
            K = Config.TOP_K_CANDIDATES
            picked: list[dict] = []

            def pick_best_of_type(t: str):
                for item in ranked_candidates_full:
                    cand = item.get('candidate') or {}
                    if cand.get('type') == t and item not in picked:
                        picked.append(item)
                        return

            # 优先各取一个类型（若存在）
            for t in ['new_substation', 'substation_expansion', 'new_line']:
                pick_best_of_type(t)

            # 用剩余得分高的补足到K个
            for item in ranked_candidates_full:
                if len(picked) >= K:
                    break
                if item not in picked:
                    picked.append(item)

            # 最终Top-K（保留原始得分顺序）
            ranked_candidates = picked[:K]
        else:
            # 标准模式：直接排名并取Top-K
            ranked_candidates = scorer.rank_candidates(
                candidates,
                load_features,
                network,
                topology,
                all_constraints
            )

        # 7. 对排名靠前的方案进行潮流计算和N-1校验
        top_candidates = ranked_candidates[:Config.TOP_K_CANDIDATES]
        validated_candidates = []

        for candidate_data in top_candidates:
            candidate = candidate_data['candidate']
            # 简化：直接使用潮流分析（实际应将候选方案添加到网络中）
            power_flow_eval = power_flow.evaluate_candidate_with_power_flow(candidate)

            validated_candidates.append({
                **candidate_data,
                'power_flow_validation': power_flow_eval
            })

        # 8. 规划建议调用移除（前端不展示，避免多余的LLM请求）
        # llm_suggestions = llm_service.generate_planning_suggestions(
        #     network,
        #     load_summary,
        #     all_constraints
        # )

        return jsonify({
            'success': True,
            'analysis': {
                'load_summary': load_summary,
                'network_topology': topology,
                'constraints': all_constraints,
                'total_candidates': len(candidates),
                'ranked_candidates': ranked_candidates,
                'validated_candidates': validated_candidates
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/planning/candidates/evaluate', methods=['POST'])
def evaluate_candidates():
    """评估候选方案"""
    try:
        data = request.json
        candidates = data.get('candidates', [])

        # 获取必要数据
        load_summary = load_prediction.get_load_summary()
        network = gis_service.get_network_summary()

        # 简单约束
        constraints = {
            'voltage_constraints': {'max_deviation': Config.MAX_VOLTAGE_DEVIATION},
            'capacity_constraints': {},
            'distance_constraints': {},
            'topology_rules': {},
            'safety_requirements': {}
        }

        # 评分
        ranked = scorer.rank_candidates(
            candidates,
            load_summary['current_features'],
            network,
            network['topology'],
            constraints
        )

        return jsonify({
            'success': True,
            'ranked_candidates': ranked
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/powerflow/run', methods=['POST'])
def run_powerflow():
    """运行潮流计算"""
    try:
        results = power_flow.run_power_flow()

        return jsonify({
            'success': True,
            'results': results
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/powerflow/n-minus-1', methods=['POST'])
def run_n_minus_1():
    """运行N-1校验"""
    try:
        results = power_flow.run_n_minus_1_check()

        return jsonify({
            'success': True,
            'results': results
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/llm/chat', methods=['POST'])
def llm_chat():
    """LLM聊天接口"""
    try:
        data = request.json
        messages = data.get('messages', [])

        response = llm_service.chat_completion(messages)
        text = llm_service.extract_text(response)

        return jsonify({
            'success': True,
            'response': text
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    print("=" * 60)
    print("Grid Planning System - Starting")
    print("=" * 60)
    print(f"Server: http://{Config.FLASK_HOST}:{Config.FLASK_PORT}")
    print("=" * 60)

    # 初始化数据
    print("Initializing services...")
    try:
        retrieval_service.build_index()
        print("✓ Document retrieval service initialized")
    except Exception as e:
        print(f"✗ Document retrieval service error: {e}")

    try:
        load_prediction.load_historical_data()
        print("✓ Load prediction service initialized")
    except Exception as e:
        print(f"✗ Load prediction service error: {e}")

    try:
        gis_service.load_network_data()
        print("✓ GIS service initialized")
    except Exception as e:
        print(f"✗ GIS service error: {e}")

    print("=" * 60)

    app.run(
        host=Config.FLASK_HOST,
        port=Config.FLASK_PORT,
        debug=Config.FLASK_DEBUG
    )
