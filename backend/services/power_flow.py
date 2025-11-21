"""
潮流计算和N-1校验模块
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional
import pandapower as pp
import pandapower.networks as pn
from config import Config
try:
    from .settings_service import settings  # package import
except Exception:  # pragma: no cover
    from services.settings_service import settings  # module import from backend cwd


class PowerFlowAnalysis:
    """潮流计算和N-1校验"""

    def __init__(self):
        self.network = None
        self.create_sample_network()

    def create_sample_network(self):
        """使用pandapower内置IEEE 14-bus作为验证基线。"""
        net = pn.case14()
        # 先跑一次确保可收敛
        try:
            pp.runpp(net)
        except Exception:
            pass
        self.network = net

    def _run_power_flow_on(self, net: pp.pandapowerNet) -> Dict[str, Any]:
        """
        在给定网络上运行潮流计算

        Returns:
            潮流计算结果
        """
        try:
            pp.runpp(net)

            results = {
                'converged': net.converged,
                'buses': self._extract_bus_results_from(net),
                'lines': self._extract_line_results_from(net),
                'transformers': self._extract_transformer_results_from(net),
                'violations': self._check_violations_on(net)
            }

            return results

        except Exception as e:
            return {
                'converged': False,
                'error': str(e)
            }

    def run_power_flow(self) -> Dict[str, Any]:
        return self._run_power_flow_on(self.network)

    def _extract_bus_results_from(self, net: pp.pandapowerNet) -> List[Dict[str, Any]]:
        """提取母线结果"""
        buses = []
        for idx, row in net.res_bus.iterrows():
            bus_data = {
                'id': int(idx),
                'name': net.bus.at[idx, 'name'],
                'voltage_pu': float(row['vm_pu']),
                'voltage_kv': float(row['vm_pu'] * net.bus.at[idx, 'vn_kv']),
                'angle_deg': float(row['va_degree']),
                'p_mw': float(row['p_mw']),
                'q_mvar': float(row['q_mvar'])
            }
            buses.append(bus_data)
        return buses

    def _extract_line_results_from(self, net: pp.pandapowerNet) -> List[Dict[str, Any]]:
        """提取线路结果"""
        lines = []
        for idx, row in net.res_line.iterrows():
            line_data = {
                'id': int(idx),
                'name': net.line.at[idx, 'name'],
                'loading_percent': float(row['loading_percent']),
                'p_from_mw': float(row['p_from_mw']),
                'p_to_mw': float(row['p_to_mw']),
                'pl_mw': float(row['pl_mw']),  # 线损
                'i_ka': float(row['i_ka'])
            }
            lines.append(line_data)
        return lines

    def _extract_transformer_results_from(self, net: pp.pandapowerNet) -> List[Dict[str, Any]]:
        """提取变压器结果"""
        transformers = []
        for idx, row in net.res_trafo.iterrows():
            trafo_data = {
                'id': int(idx),
                'name': net.trafo.at[idx, 'name'],
                'loading_percent': float(row['loading_percent']),
                'p_hv_mw': float(row['p_hv_mw']),
                'p_lv_mw': float(row['p_lv_mw']),
                'pl_mw': float(row['pl_mw'])
            }
            transformers.append(trafo_data)
        return transformers

    def _check_violations_on(self, net: pp.pandapowerNet) -> List[Dict[str, Any]]:
        """检查约束违反"""
        violations = []

        # 检查电压越限
        # 跳过发电机母线/外部电网母线的电压设定点
        gen_buses = set(net.gen['bus'].tolist()) if len(net.gen) else set()
        ext_buses = set(net.ext_grid['bus'].tolist()) if len(net.ext_grid) else set()

        for idx, row in net.res_bus.iterrows():
            if int(idx) in gen_buses or int(idx) in ext_buses:
                continue
            voltage_pu = row['vm_pu']
            max_dev = float(settings.get('MAX_VOLTAGE_DEVIATION', Config.MAX_VOLTAGE_DEVIATION))
            # 支持按电压等级分层阈值（可选）
            try:
                level_map = settings.get('VOLTAGE_DEVIATION_BY_LEVEL', None)
                if level_map:
                    vn = float(net.bus.at[idx, 'vn_kv'])
                    # level_map: list of {min_kv,max_kv,limit}
                    for item in level_map:
                        lo = float(item.get('min_kv') or 0.0)
                        hi = float(item.get('max_kv') or 1e9)
                        if vn >= lo and vn <= hi:
                            max_dev = float(item.get('limit') or max_dev)
                            break
            except Exception:
                pass
            if abs(voltage_pu - 1.0) > max_dev:
                violations.append({
                    'type': 'voltage',
                    'element': 'bus',
                    'id': int(idx),
                    'name': net.bus.at[idx, 'name'],
                    'value': float(voltage_pu),
                    'limit': 1.0,
                    'deviation': float(abs(voltage_pu - 1.0))
                })

        # 检查线路过载
        for idx, row in net.res_line.iterrows():
            loading = row['loading_percent'] / 100.0
            max_line = float(settings.get('MAX_LINE_LOADING', Config.MAX_LINE_LOADING))
            if loading > max_line:
                violations.append({
                    'type': 'overload',
                    'element': 'line',
                    'id': int(idx),
                    'name': net.line.at[idx, 'name'],
                    'value': float(loading),
                    'limit': max_line,
                    'excess': float(loading - max_line)
                })

        # 检查变压器过载
        if hasattr(net, 'res_trafo') and len(net.res_trafo):
            for idx, row in net.res_trafo.iterrows():
                loading = float(row.get('loading_percent', 0.0)) / 100.0
                max_trafo = float(settings.get('MAX_TRAFO_LOADING', getattr(Config, 'MAX_TRAFO_LOADING', 0.9)))
                if loading > max_trafo:
                    violations.append({
                        'type': 'overload',
                        'element': 'transformer',
                        'id': int(idx),
                        'name': net.trafo.at[idx, 'name'],
                        'value': float(loading),
                        'limit': max_trafo,
                        'excess': float(loading - max_trafo)
                    })

        return violations

    def _run_n_minus_1_on(self, net: pp.pandapowerNet) -> Dict[str, Any]:
        """
        运行N-1安全校验

        Returns:
            N-1校验结果
        """
        if not bool(settings.get('N_MINUS_1_CHECK', Config.N_MINUS_1_CHECK)):
            return {'enabled': False}

        results = {
            'enabled': True,
            'total_lines': len(net.line),
            'line_contingencies': [],
            'critical_contingencies': []
        }

        # 保存原始状态
        original_line_status = net.line['in_service'].copy()

        # 遍历每条线路，模拟其退出运行
        for line_idx in net.line.index:
            # 断开线路
            net.line.at[line_idx, 'in_service'] = False

            try:
                # 运行潮流
                pp.runpp(net)

                contingency = {
                    'line_id': int(line_idx),
                    'line_name': net.line.at[line_idx, 'name'],
                    'converged': net.converged,
                    'violations': []
                }

                if net.converged:
                    # 检查违规
                    violations = self._check_violations_on(net)
                    contingency['violations'] = violations

                    if len(violations) > 0:
                        contingency['critical'] = True
                        results['critical_contingencies'].append(contingency)
                else:
                    contingency['critical'] = True
                    contingency['error'] = 'Power flow did not converge'
                    results['critical_contingencies'].append(contingency)

                results['line_contingencies'].append(contingency)

            except Exception as e:
                results['line_contingencies'].append({
                    'line_id': int(line_idx),
                    'line_name': net.line.at[line_idx, 'name'],
                    'error': str(e),
                    'critical': True
                })

            finally:
                # 恢复线路状态
                net.line.at[line_idx, 'in_service'] = True

        # 恢复所有线路状态
        net.line['in_service'] = original_line_status

        results['n_minus_1_passed'] = len(results['critical_contingencies']) == 0

        return results

    def run_n_minus_1_check(self) -> Dict[str, Any]:
        return self._run_n_minus_1_on(self.network)

    def _nearest_bus_id(self, gis_data: Dict[str, Any], lat: float, lon: float) -> int | None:
        best_id = None
        best_d = 1e18
        for s in (gis_data.get('substations') or []):
            loc = s.get('location')
            if not loc:
                continue
            d = (float(loc['lat']) - lat) ** 2 + (float(loc['lon']) - lon) ** 2
            if d < best_d:
                best_d = d
                # ids like 'bus_3'
                sid = s.get('id')
                if isinstance(sid, str) and sid.startswith('bus_'):
                    try:
                        best_id = int(sid.split('_')[1])
                    except Exception:
                        best_id = None
        return best_id

    def _nearest_distinct_bus(self, gis_data: Dict[str, Any], lat: float, lon: float, exclude_bus: Optional[int]) -> Optional[int]:
        """Pick nearest bus to (lat,lon) that is not exclude_bus."""
        best_id = None
        best_d = 1e18
        for s in (gis_data.get('substations') or []):
            loc = s.get('location')
            if not loc:
                continue
            sid = s.get('id')
            bid = None
            if isinstance(sid, str) and sid.startswith('bus_'):
                try:
                    bid = int(sid.split('_')[1])
                except Exception:
                    bid = None
            if bid is None or (exclude_bus is not None and bid == exclude_bus):
                continue
            d = (float(loc['lat']) - lat) ** 2 + (float(loc['lon']) - lon) ** 2
            if d < best_d:
                best_d = d
                best_id = bid
        return best_id

    def _inject_new_line(self, net: pp.pandapowerNet, candidate: Dict[str, Any], gis_data: Dict[str, Any]) -> Dict[str, Any]:
        length_km = float(candidate.get('length_km') or candidate.get('distance_to_existing') or 5.0)
        vn = float(candidate.get('voltage_level') or 110)
        # choose from/to buses
        from_bus = None
        sid = candidate.get('from_substation_id') or candidate.get('substation_id')
        if isinstance(sid, str) and sid.startswith('bus_'):
            try:
                from_bus = int(sid.split('_')[1])
            except Exception:
                from_bus = None
        if from_bus is None and candidate.get('from_location'):
            loc = candidate['from_location']
            from_bus = self._nearest_bus_id(gis_data, float(loc['lat']), float(loc['lon']))

        to_bus = None
        if candidate.get('to_substation_id'):
            try:
                to_bus = int(str(candidate['to_substation_id']).split('_')[1])
            except Exception:
                to_bus = None
        if to_bus is None and candidate.get('to_location'):
            loc = candidate['to_location']
            to_bus = self._nearest_bus_id(gis_data, float(loc['lat']), float(loc['lon']))

        if from_bus is None or to_bus is None or from_bus == to_bus:
            # 回退：选择与目标位置最近的、且不同于from_bus的母线
            fallback_loc = candidate.get('to_location') or candidate.get('location') or candidate.get('from_location')
            if fallback_loc:
                to_bus_alt = self._nearest_distinct_bus(gis_data, float(fallback_loc['lat']), float(fallback_loc['lon']), exclude_bus=from_bus)
                if to_bus_alt is not None and to_bus_alt != from_bus:
                    to_bus = to_bus_alt
            if from_bus is None or to_bus is None or from_bus == to_bus:
                raise ValueError('cannot determine from/to bus for new_line')

        # per-km parameters (rough)
        if vn >= 100:
            r_ohm_per_km = 0.06
            x_ohm_per_km = 0.32
            c_nf_per_km = 10.0
            max_i_ka = 0.6
        else:
            r_ohm_per_km = 0.15
            x_ohm_per_km = 0.35
            c_nf_per_km = 8.0
            max_i_ka = 0.4

        idx = pp.create_line_from_parameters(
            net,
            from_bus=from_bus,
            to_bus=to_bus,
            length_km=length_km,
            r_ohm_per_km=r_ohm_per_km,
            x_ohm_per_km=x_ohm_per_km,
            c_nf_per_km=c_nf_per_km,
            max_i_ka=max_i_ka,
            name=f"cand_line_{from_bus}_{to_bus}",
            df=1.0,
            type='ol',
            parallel=1,
        )
        return {'type': 'new_line', 'from_bus': from_bus, 'to_bus': to_bus, 'length_km': length_km, 'voltage_kv': vn, 'line_idx': int(idx)}

    def _inject_substation_expansion(self, net: pp.pandapowerNet, candidate: Dict[str, Any]) -> Dict[str, Any]:
        sid = candidate.get('substation_id') or candidate.get('from_substation_id')
        if not isinstance(sid, str) or not sid.startswith('bus_'):
            raise ValueError('invalid substation id')
        bus_id = int(sid.split('_')[1])
        # find a trafo related to this bus
        base_idx = None
        for idx, t in net.trafo.iterrows():
            if int(t.hv_bus) == bus_id or int(t.lv_bus) == bus_id:
                base_idx = idx
                break
        if base_idx is None:
            raise ValueError('no trafo to expand at bus')
        t = net.trafo.loc[base_idx]
        hv_bus = int(t.hv_bus)
        lv_bus = int(t.lv_bus)
        add_sn = float(candidate.get('additional_capacity') or candidate.get('capacity_mva') or 25.0)
        idx_new = pp.create_transformer_from_parameters(
            net,
            hv_bus=hv_bus,
            lv_bus=lv_bus,
            sn_mva=add_sn,
            vn_hv_kv=float(net.bus.at[hv_bus, 'vn_kv']),
            vn_lv_kv=float(net.bus.at[lv_bus, 'vn_kv']),
            vk_percent=float(t.vk_percent if not np.isnan(t.vk_percent) else 10.0),
            vkr_percent=float(t.vkr_percent if not np.isnan(t.vkr_percent) else 0.5),
            pfe_kw=float(t.pfe_kw if not np.isnan(t.pfe_kw) else 0.0),
            i0_percent=float(t.i0_percent if not np.isnan(t.i0_percent) else 0.0),
            shift_degree=float(t.shift_degree if not np.isnan(t.shift_degree) else 0.0),
            tap_side=str(t.tap_side) if not (isinstance(t.tap_side, float) and np.isnan(t.tap_side)) else 'hv',
            tap_neutral=int(t.tap_neutral) if not (isinstance(t.tap_neutral, float) and np.isnan(t.tap_neutral)) else 0,
            tap_min=int(t.tap_min) if not (isinstance(t.tap_min, float) and np.isnan(t.tap_min)) else 0,
            tap_max=int(t.tap_max) if not (isinstance(t.tap_max, float) and np.isnan(t.tap_max)) else 0,
            tap_step_percent=float(t.tap_step_percent if not np.isnan(t.tap_step_percent) else 2.5),
            tap_step_degree=float(t.tap_step_degree if not np.isnan(t.tap_step_degree) else 0.0),
        )
        return {'type': 'substation_expansion', 'bus': bus_id, 'trafo_idx': int(idx_new), 'add_sn_mva': add_sn}

    def _inject_new_substation(self, net: pp.pandapowerNet, candidate: Dict[str, Any], gis_data: Dict[str, Any]) -> Dict[str, Any]:
        # Minimal: add a new bus and connect to nearest existing bus via a line
        vn = float(candidate.get('voltage_level') or 110)
        length_km = float(candidate.get('distance_to_existing') or candidate.get('length_km') or 5.0)
        loc = candidate.get('location') or {}
        nearest_id = None
        if candidate.get('nearest_existing'):
            sid = candidate['nearest_existing']
            if isinstance(sid, str) and sid.startswith('bus_'):
                try:
                    nearest_id = int(sid.split('_')[1])
                except Exception:
                    nearest_id = None
        if nearest_id is None and loc:
            nearest_id = self._nearest_bus_id(gis_data, float(loc.get('lat', 0.0)), float(loc.get('lon', 0.0)))
        if nearest_id is None:
            raise ValueError('cannot find nearest bus for new_substation')

        new_bus = pp.create_bus(net, vn_kv=vn, name=f"NewSub_{vn}kV")
        # parameters
        if vn >= 100:
            r_ohm_per_km = 0.06; x_ohm_per_km = 0.32; c_nf_per_km = 10.0; max_i_ka = 0.6
        else:
            r_ohm_per_km = 0.15; x_ohm_per_km = 0.35; c_nf_per_km = 8.0; max_i_ka = 0.4
        pp.create_line_from_parameters(net, from_bus=new_bus, to_bus=nearest_id, length_km=length_km,
                                       r_ohm_per_km=r_ohm_per_km, x_ohm_per_km=x_ohm_per_km,
                                       c_nf_per_km=c_nf_per_km, max_i_ka=max_i_ka,
                                       name=f"cand_newsub_{new_bus}_{nearest_id}")
        # 演示：将邻近母线部分负荷迁移至新站，以模拟负荷疏解效果
        try:
            alpha = float(getattr(Config, 'DEMO_REASSIGN_LOAD_ALPHA', 0.0) or 0.0)
            if alpha > 0 and len(net.load):
                import numpy as np
                # 选择连接的最近母线的负荷
                sel = net.load['bus'] == int(nearest_id)
                if sel.any():
                    total_p = float(net.load.loc[sel, 'p_mw'].sum())
                    total_q = float(net.load.loc[sel, 'q_mvar'].sum()) if 'q_mvar' in net.load.columns else 0.0
                    move_p = total_p * alpha
                    move_q = total_q * alpha
                    # 原母线负荷按比例缩小
                    net.load.loc[sel, 'p_mw'] *= (1.0 - alpha)
                    if 'q_mvar' in net.load.columns:
                        net.load.loc[sel, 'q_mvar'] *= (1.0 - alpha)
                    # 新母线创建等功率因数负荷
                    if move_p > 1e-6:
                        q_new = move_q if total_p <= 1e-9 else move_p * (total_q / total_p)
                        pp.create_load(net, bus=int(new_bus), p_mw=move_p, q_mvar=q_new, name='migrated_load_demo')
        except Exception:
            pass

        return {'type': 'new_substation', 'new_bus': int(new_bus), 'connect_to': int(nearest_id), 'length_km': length_km}

    def evaluate_candidate_with_power_flow(
        self,
        candidate: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        使用潮流计算评估候选方案

        Args:
            candidate: 候选方案

        Returns:
            评估结果
        """
        # 真实校核：克隆基线网络，将候选方案注入，再运行潮流与N-1
        net = self.network.deepcopy()
        injection = None
        try:
            # 延迟导入以获得GIS坐标
            from services.gis_service import gis_service  # type: ignore
            gis_data = gis_service.get_network_summary()
        except Exception:
            gis_data = {'substations': []}

        try:
            if candidate.get('type') == 'new_line':
                injection = self._inject_new_line(net, candidate, gis_data)
            elif candidate.get('type') == 'substation_expansion':
                injection = self._inject_substation_expansion(net, candidate)
            elif candidate.get('type') == 'new_substation':
                injection = self._inject_new_substation(net, candidate, gis_data)
        except Exception as e:
            injection = {'error': str(e)}

        power_flow_results = self._run_power_flow_on(net)

        evaluation = {
            'candidate': candidate,
            'power_flow': power_flow_results,
            'passed': power_flow_results.get('converged', False) and
                     len(power_flow_results.get('violations', [])) == 0
        }

        # 如果基础潮流通过，进行N-1校验
        if evaluation['passed'] and Config.N_MINUS_1_CHECK:
            n_minus_1_results = self._run_n_minus_1_on(net)
            evaluation['n_minus_1'] = n_minus_1_results
            evaluation['passed'] = evaluation['passed'] and \
                                  n_minus_1_results.get('n_minus_1_passed', False)
        if injection is not None:
            evaluation['injection'] = injection

        return evaluation


# 全局实例
power_flow = PowerFlowAnalysis()
