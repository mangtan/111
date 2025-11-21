"""
Runtime ML scorer integration.
- Loads a joblib model saved by ml/train_baseline.py
- Computes features from candidate + current network/topology/powerflow baseline
"""
from __future__ import annotations

import os
import math
from typing import Dict, Any, List

try:
    import joblib
except Exception:  # pragma: no cover
    try:
        from sklearn.externals import joblib  # type: ignore
    except Exception:  # pragma: no cover
        joblib = None  # type: ignore

try:
    from ..config import Config  # when imported as package
except Exception:  # pragma: no cover
    from config import Config    # when imported as module from backend cwd


class MLScorer:
    def __init__(self, model_path: str | None = None):
        self.model_path = model_path or Config.ML_MODEL_PATH
        self._model = None
        self._features: List[str] | None = None
        self._base_metrics: Dict[str, float] | None = None
        self._load()

    def available(self) -> bool:
        return self._model is not None and self._features is not None

    def _load(self):
        if not Config.ENABLE_ML_SCORING:
            return
        if joblib is None:
            return
        if not os.path.exists(self.model_path):
            return
        try:
            data = joblib.load(self.model_path)
            self._model = data.get('model')
            self._features = data.get('features')
        except Exception:
            self._model = None
            self._features = None

    def _get_base_metrics(self) -> Dict[str, float]:
        if self._base_metrics is not None:
            return self._base_metrics
        # Lazy import to avoid circulars
        try:
            from ..services.power_flow import power_flow  # package import
        except Exception:
            from services.power_flow import power_flow      # module import from backend cwd
        res = power_flow.run_power_flow()
        violations = 0
        if res.get('violations'):
            violations = len(res['violations'])
        max_loading = 0.0
        total_losses = 0.0
        for line in res.get('lines', []) or []:
            max_loading = max(max_loading, float(line.get('loading_percent', 0.0)))
            total_losses += float(line.get('pl_mw', 0.0))
        self._base_metrics = {
            'base_violations': float(violations),
            'base_max_loading_percent': float(max_loading),
            'base_total_losses_mw': float(total_losses),
        }
        return self._base_metrics

    @staticmethod
    def _degree_of(node_id: str, topology: Dict[str, Any]) -> int:
        if not topology:
            return 0
        degs = topology.get('node_degrees') or {}
        return int(degs.get(node_id, 0))

    @staticmethod
    def _nearest_bus_id_by_location(gis_data: Dict[str, Any], lat: float, lon: float) -> str | None:
        subs = gis_data.get('substations') or []
        best_id, best_d = None, 1e18
        for s in subs:
            loc = s.get('location')
            if not loc:
                continue
            d = (float(loc['lat']) - lat) ** 2 + (float(loc['lon']) - lon) ** 2
            if d < best_d:
                best_d = d
                best_id = s.get('id')
        return best_id

    def score(self, candidate: Dict[str, Any], gis_data: Dict[str, Any], topology: Dict[str, Any]) -> float | None:
        if not self.available():
            return None
        feats = self._features or []
        base = self._get_base_metrics()

        # Build feature dict with safe defaults
        f: Dict[str, float] = {
            'vn_kv': float(candidate.get('voltage_level') or 110),
            'length_km': float(candidate.get('length_km') or candidate.get('distance_to_existing') or 5.0),
            'max_i_ka': 0.5 if float(candidate.get('voltage_level') or 110) >= 100 else 0.35,
            'deg_from': 0.0,
            'deg_to': 0.0,
            **base,
        }

        # Estimate degrees using topology node ids
        from_id = candidate.get('from_substation_id') or candidate.get('substation_id')
        to_id = None
        if candidate.get('to_substation_id'):
            to_id = candidate.get('to_substation_id')
        elif candidate.get('to_location'):
            loc = candidate['to_location']
            to_id = self._nearest_bus_id_by_location(gis_data, float(loc['lat']), float(loc['lon']))

        if isinstance(from_id, str):
            f['deg_from'] = float(self._degree_of(from_id, topology))
        if isinstance(to_id, str):
            f['deg_to'] = float(self._degree_of(to_id, topology))

        # Arrange vector
        x = [float(f.get(name, 0.0)) for name in feats]
        try:
            pred = float(self._model.predict([x])[0])  # type: ignore[attr-defined]
        except Exception:
            return None

        # Map raw prediction to 0-100 via tanh squashing
        ml_score = max(0.0, min(100.0, (math.tanh(pred) + 1.0) * 50.0))
        return ml_score
