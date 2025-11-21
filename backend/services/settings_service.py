"""
运行态配置覆盖服务：用于在不修改硬编码 Config 的前提下，按需应用 LLM 解析出来的阈值/规则。
"""
from __future__ import annotations

from typing import Any, Dict, Optional
import re

from config import Config


class SettingsService:
    def __init__(self) -> None:
        # 存放运行时覆盖项，例如 { 'MAX_VOLTAGE_DEVIATION': 0.05 }
        self.overrides: Dict[str, Any] = {}
        # 最近一次应用的原始约束（保留可追溯）
        self.last_constraints: Optional[Dict[str, Any]] = None

    def get(self, key: str, default: Any) -> Any:
        return self.overrides.get(key, default)

    def all(self) -> Dict[str, Any]:
        return dict(self.overrides)

    def reset(self) -> Dict[str, Any]:
        self.overrides.clear()
        self.last_constraints = None
        return self.all()

    @staticmethod
    def _as_ratio(x: Any) -> Optional[float]:
        # 接受 0.07 或 7/"7%"
        try:
            if isinstance(x, (int, float)):
                return float(x) if float(x) <= 1 else float(x) / 100.0
            if isinstance(x, str):
                m = re.search(r"([0-9]+\.?[0-9]*)", x)
                if m:
                    v = float(m.group(1))
                    return v if v <= 1 else v / 100.0
        except Exception:
            return None
        return None

    @staticmethod
    def _as_float(x: Any) -> Optional[float]:
        try:
            return float(x)
        except Exception:
            return None

    def apply_constraints(self, constraints: Dict[str, Any]) -> Dict[str, Any]:
        """
        从LLM解析的约束中提取关键阈值，应用到运行态 overrides。
        约定字段（尽力匹配，容错）：
          - voltage_constraints.max_deviation / max_deviation_percent
          - line_loading.max_percent / normal_max_percent
          - trafo_loading.max_percent
          - n_minus_1.enabled
          - voltage_levels: [10,35,110,...]
          - distance_constraints.min_new_substation_km / max_new_substation_km
        """
        self.last_constraints = constraints
        applied: Dict[str, Any] = {}

        if not isinstance(constraints, dict):
            raise ValueError('constraints 需为 dict')

        vc = (constraints or {}).get('voltage_constraints') or {}
        # 允许是 dict 或 list
        r = None
        if isinstance(vc, dict):
            max_dev = vc.get('max_deviation') or vc.get('max_deviation_percent') or vc.get('deviation') or vc.get('limit')
            r = self._as_ratio(max_dev)
        elif isinstance(vc, list):
            # 从条目中解析如 "±7%"、"+7%,-10%"、"…10%" 等，取一个合理阈值（此处取最小值更严格）
            vals = []
            for it in vc:
                if not isinstance(it, dict):
                    continue
                cand = it.get('max_deviation') or it.get('max_deviation_percent') or it.get('deviation') or it.get('deviation_limit') or it.get('limit') or it.get('rule')
                rr = self._as_ratio(cand)
                if rr is None and isinstance(cand, str):
                    # 解析形如 "+7%,-10%" 取绝对值的最大值
                    nums = re.findall(r"[-+]?\d+\.?\d*\s*%", cand)
                    if nums:
                        try:
                            mx = 0.0
                            for n in nums:
                                v = float(re.findall(r"[-+]?\d+\.?\d*", n)[0])
                                v = v if v <= 1 else v/100.0
                                if v < 0:
                                    v = -v
                                mx = max(mx, v)
                            rr = mx
                        except Exception:
                            rr = None
                if rr is not None:
                    vals.append(rr)
            if vals:
                # 取更严格的最小值，例如 {±7%, ±10%} -> 0.07
                r = min(vals)
        # 额外：按电压等级条款解析（35kV及以上/20kV及以下/220V等），生成 LEVEL 映射
        level_map = []
        if isinstance(vc, list):
            for it in vc:
                if not isinstance(it, dict):
                    continue
                lvl = it.get('voltage_level') or it.get('level') or ''
                lim = it.get('deviation_limit') or it.get('limit')
                limv = self._as_ratio(lim)
                if limv is None:
                    # 再尝试从字符串中提取百分比
                    if isinstance(lim, str):
                        m = re.findall(r"[-+]?\d+\.?\d*\s*%", lim)
                        if m:
                            try:
                                mx = 0.0
                                for n in m:
                                    v = float(re.findall(r"[-+]?\d+\.?\d*", n)[0])
                                    v = v if v <= 1 else v/100.0
                                    if v < 0: v = -v
                                    mx = max(mx, v)
                                limv = mx
                            except Exception:
                                limv = None
                if limv is None:
                    continue
                # 解析电压等级范围
                lo = 0.0; hi = 1e9
                if isinstance(lvl, str):
                    kvs = re.findall(r"(\d+\.?\d*)\s*k?V", lvl, re.I)
                    vals = [float(x) for x in kvs] if kvs else []
                    if '及以上' in lvl and vals:
                        lo = vals[0]
                    elif '及以下' in lvl and vals:
                        hi = vals[0]
                    elif len(vals) == 1:
                        lo = hi = vals[0]
                level_map.append({'min_kv': lo, 'max_kv': hi, 'limit': limv})

        if r is not None:
            self.overrides['MAX_VOLTAGE_DEVIATION'] = r
            applied['MAX_VOLTAGE_DEVIATION'] = r
        if level_map:
            self.overrides['VOLTAGE_DEVIATION_BY_LEVEL'] = level_map
            applied['VOLTAGE_DEVIATION_BY_LEVEL'] = level_map

        # 线路负载率
        lc = (constraints or {}).get('line_loading') or {}
        # 允许 list/dict，尝试解析百分比
        rr = None
        if isinstance(lc, dict):
            ll = lc.get('normal_max_percent') or lc.get('max_percent') or lc.get('line_max_percent') or lc.get('limit')
            rr = self._as_ratio(ll)
        elif isinstance(lc, list):
            vals = []
            for it in lc:
                if not isinstance(it, dict):
                    continue
                cand = it.get('max_percent') or it.get('limit') or it.get('rule')
                r1 = self._as_ratio(cand)
                if r1 is not None:
                    vals.append(r1)
            if vals:
                rr = min(vals)
        if rr is not None:
            self.overrides['MAX_LINE_LOADING'] = rr
            applied['MAX_LINE_LOADING'] = rr

        # 变压器负载率
        tc = (constraints or {}).get('trafo_loading') or {}
        tl = self._as_ratio(tc.get('max_percent'))
        if tl is not None:
            self.overrides['MAX_TRAFO_LOADING'] = tl
            applied['MAX_TRAFO_LOADING'] = tl

        # N-1
        n1 = (constraints or {}).get('n_minus_1') or (constraints or {}).get('n-1') or {}
        if isinstance(n1.get('enabled'), bool):
            self.overrides['N_MINUS_1_CHECK'] = bool(n1['enabled'])
            applied['N_MINUS_1_CHECK'] = bool(n1['enabled'])

        # 电压等级集合
        vls = constraints.get('voltage_levels') if isinstance(constraints, dict) else None
        if isinstance(vls, list) and all(isinstance(v, (int, float)) for v in vls):
            vals = [int(v) for v in vls]
            self.overrides['VOLTAGE_LEVELS'] = vals
            applied['VOLTAGE_LEVELS'] = vals

        # 新站距离约束
        dc = (constraints or {}).get('distance_constraints') or {}
        mn = mx = None
        if isinstance(dc, dict):
            mn = self._as_float(dc.get('min_new_substation_km') or dc.get('min_distance_km'))
            mx = self._as_float(dc.get('max_new_substation_km') or dc.get('max_distance_km'))
        elif isinstance(dc, list):
            # 尝试在条文文字里解析“Xkm/公里”
            for it in dc:
                if not isinstance(it, dict):
                    continue
                for k in ['min_new_substation_km', 'min_distance_km', 'max_new_substation_km', 'max_distance_km', 'rule']:
                    txt = it.get(k)
                    if isinstance(txt, (int, float)):
                        val = float(txt)
                    elif isinstance(txt, str):
                        m = re.search(r"(\d+\.?\d*)\s*(km|公里)", txt, re.I)
                        val = float(m.group(1)) if m else None
                    else:
                        val = None
                    if val is None:
                        continue
                    if 'min' in k and mn is None:
                        mn = val
                    if 'max' in k and mx is None:
                        mx = val
        if mn is not None:
            self.overrides['MIN_NEW_STATION_DISTANCE_KM'] = mn
            applied['MIN_NEW_STATION_DISTANCE_KM'] = mn
        if mx is not None:
            self.overrides['MAX_NEW_STATION_DISTANCE_KM'] = mx
            applied['MAX_NEW_STATION_DISTANCE_KM'] = mx

        return applied


# 全局实例
settings = SettingsService()
