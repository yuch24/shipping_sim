"""ML Pipeline — 机器学习预测管道

使用 scikit-learn 对仿真数据进行预测建模。
"""

import math
from typing import Any

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_absolute_error, r2_score, accuracy_score, confusion_matrix
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


def _make_synthetic_data(task_id: str, n_samples: int = 500):
    """生成仿真数据用于 ML 演示"""
    np.random.seed(42)

    if task_id == "eta":
        # ETA 预测: 特征 = 距离, 航速, 历史延误, 港口拥堵度
        dist = np.random.uniform(200, 1200, n_samples)
        speed = np.random.uniform(12, 22, n_samples)
        hist_delay = np.random.exponential(2, n_samples)
        congestion = np.random.uniform(0, 5, n_samples)
        target = dist / speed * 60 + hist_delay + congestion * 1.5 + np.random.normal(0, 2, n_samples)
        features = np.column_stack([dist, speed, hist_delay, congestion])
        return features, target, ["距离(nm)", "航速(kn)", "历史延误(h)", "港口拥堵度"]

    elif task_id == "congestion":
        # 港口拥堵预测: 特征 = 排队船舶数, 到港率, 泊位数, 装卸效率
        queue = np.random.poisson(3, n_samples)
        arrival_rate = np.random.uniform(0.5, 3, n_samples)
        berths = np.random.choice([3, 4, 5], n_samples)
        eff = np.random.uniform(0.6, 1.0, n_samples)
        target = queue * 2.5 + arrival_rate * 4 - berths * 1.5 + eff * 3 + np.random.normal(0, 1, n_samples)
        target = np.maximum(0, target)
        features = np.column_stack([queue, arrival_rate, berths, eff])
        return features, target, ["排队船舶数", "到港率(艘/h)", "泊位数", "装卸效率"]

    elif task_id == "fuel":
        # 燃油预测: 特征 = 航速, 载重率, 距离, 海况等级
        speed = np.random.uniform(12, 22, n_samples)
        load = np.random.uniform(0.5, 1.0, n_samples)
        dist = np.random.uniform(200, 1200, n_samples)
        sea = np.random.uniform(0, 5, n_samples)
        target = (0.01 * speed ** 3 + 0.5 * load + 0.02 * dist + sea * 0.8) * np.random.uniform(0.9, 1.1, n_samples)
        features = np.column_stack([speed, load, dist, sea])
        return features, target, ["航速(kn)", "载重率", "距离(nm)", "海况等级"]

    elif task_id == "cii":
        # CII 评级预测: 特征 = 年排放, 航行距离, 船舶容量, 航速
        emission = np.random.uniform(50, 200, n_samples)
        distance = np.random.uniform(10000, 50000, n_samples)
        capacity = np.random.choice([8000, 10000, 14000, 20000], n_samples)
        speed = np.random.uniform(12, 22, n_samples)
        cii = emission / (capacity * distance / 10000)
        # 映射到 A-E 评级
        thresholds = [0.85, 1.0, 1.15, 1.35]
        target = np.digitize(cii * 10, thresholds)  # 0=A, 1=B, 2=C, 3=D, 4=E
        target = np.clip(target, 0, 4)
        features = np.column_stack([emission, distance, capacity, speed])
        return features, target, ["年排放(t)", "航行距离(nm)", "船舶容量(TEU)", "平均航速(kn)"]

    return np.random.rand(n_samples, 4), np.random.rand(n_samples), ["f1", "f2", "f3", "f4"]


def get_task_info() -> list[dict]:
    """返回可用的 ML 任务列表"""
    return [
        {
            "id": "eta",
            "name": "ETA 预测",
            "description": "基于航行历史预测船舶到港时间",
            "type": "regression",
            "features": ["距离(nm)", "航速(kn)", "历史延误(h)", "港口拥堵度"],
            "sample_count": 500,
        },
        {
            "id": "congestion",
            "name": "港口拥堵预测",
            "description": "预测港口队列长度与等待时间",
            "type": "regression",
            "features": ["排队船舶数", "到港率(艘/h)", "泊位数", "装卸效率"],
            "sample_count": 500,
        },
        {
            "id": "fuel",
            "name": "燃油消耗预测",
            "description": "基于航速/载重/海况预测油耗",
            "type": "regression",
            "features": ["航速(kn)", "载重率", "距离(nm)", "海况等级"],
            "sample_count": 500,
        },
        {
            "id": "cii",
            "name": "CII 评级预测",
            "description": "预测船舶年度 CII 评级",
            "type": "classification",
            "features": ["年排放(t)", "航行距离(nm)", "船舶容量(TEU)", "平均航速(kn)"],
            "sample_count": 500,
        },
    ]


def train_model(task_id: str) -> dict:
    """训练 ML 模型

    Args:
        task_id: 任务 ID

    Returns:
        训练结果（指标 + 特征重要性）
    """
    if not HAS_NUMPY:
        return {"status": "error", "error": "需要 numpy"}

    features, target, feature_names = _make_synthetic_data(task_id)

    if task_id == "cii":
        # 分类任务
        if HAS_SKLEARN:
            X_train, X_test, y_train, y_test = train_test_split(
                features, target, test_size=0.2, random_state=42
            )
            model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)
            acc = accuracy_score(y_test, y_pred)

            return {
                "status": "success",
                "task_id": task_id,
                "task_name": get_task_info()[{"eta": 0, "congestion": 1, "fuel": 2, "cii": 3}[task_id]]["name"],
                "model_type": "RandomForestClassifier",
                "metrics": {
                    "accuracy": round(acc, 4),
                    "samples": len(features),
                },
                "feature_importance": [
                    {"name": feature_names[i], "importance": round(float(model.feature_importances_[i]), 4)}
                    for i in range(len(feature_names))
                ],
            }
        else:
            # 无 sklearn 回退
            return _fallback_metrics(task_id, feature_names, features, target, "classification")

    else:
        # 回归任务
        if HAS_SKLEARN:
            X_train, X_test, y_train, y_test = train_test_split(
                features, target, test_size=0.2, random_state=42
            )
            model = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42)
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)
            mae = mean_absolute_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)

            return {
                "status": "success",
                "task_id": task_id,
                "task_name": get_task_info()[{"eta": 0, "congestion": 1, "fuel": 2, "cii": 3}[task_id]]["name"],
                "model_type": "RandomForestRegressor",
                "metrics": {
                    "mae": round(mae, 2),
                    "r2_score": round(r2, 4),
                    "samples": len(features),
                },
                "feature_importance": [
                    {"name": feature_names[i], "importance": round(float(model.feature_importances_[i]), 4)}
                    for i in range(len(feature_names))
                ],
            }
        else:
            return _fallback_metrics(task_id, feature_names, features, target, "regression")


def _fallback_metrics(task_id, feature_names, features, target, task_type):
    """无 sklearn 时的回退统计"""
    import numpy as np

    mean_target = float(np.mean(target))
    std_target = float(np.std(target))

    return {
        "status": "success",
        "task_id": task_id,
        "model_type": "statistical (sklearn not available)",
        "metrics": {
            "mean": round(mean_target, 2),
            "std": round(std_target, 2),
            "samples": len(features),
            "note": "基础统计（安装 scikit-learn 获取模型训练）",
        },
        "feature_importance": [
            {"name": feature_names[i], "importance": round(abs(float(np.corrcoef(features[:, i], target)[0, 1])), 4) if len(np.unique(features[:, i])) > 1 else 0}
            for i in range(len(feature_names))
        ],
    }


def predict(task_id: str, input_data: list) -> dict:
    """对新数据做预测"""
    if not HAS_SKLEARN:
        return {"status": "error", "error": "需要 scikit-learn"}

    features, target, feature_names = _make_synthetic_data(task_id)

    if task_id == "cii":
        model = RandomForestClassifier(n_estimators=100, random_state=42)
    else:
        model = RandomForestRegressor(n_estimators=100, random_state=42)

    model.fit(features, target)
    pred = model.predict([input_data])

    return {
        "status": "success",
        "prediction": [round(float(p), 2) for p in pred],
    }
