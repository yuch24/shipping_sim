"""
Agent 配置系统

每个 Agent 的行为完全由其配置定义：system_prompt（人格描述）+ 可用工具 + 参数。
替代原先的 hardcoded if/else 逻辑和分离的 DecisionRuleService。
"""

import json
import os
import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel

logger = logging.getLogger(__name__)

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "..", "..", ".agent_configs.json")


class ToolBinding(BaseModel):
    """工具绑定 — 定义 agent 可用哪些工具及其参数覆盖"""
    tool_id: str
    enabled: bool = True
    params: Dict[str, float] = {}


class AgentConfig(BaseModel):
    """一个 AI Agent 的完整配置"""
    id: str
    name: str
    description: str
    category: str = "speed_optimization"
    enabled: bool = True
    decision_mode: str = "fast"  # "fast" | "llm"
    system_prompt: str = ""
    tools: List[ToolBinding] = []
    parameters: Dict[str, float] = {}


# ======== 默认 Agent 配置 ========

def _balanced_prompt() -> str:
    return (
        "你是一个多目标均衡的航运AI调度员。你的核心目标是：\n"
        "1. 优先保证准班率，延误越严重越要积极赶班\n"
        "2. 控制碳排放，CII比率超过1.35时必须降速\n"
        "3. 在延误和碳排放之间寻找最佳平衡点\n"
        "4. 避免频繁调整航速（最少间隔24小时）\n\n"
        "决策原则：\n"
        "- 严重延误(>48h)：即使CII偏高也需适度提速\n"
        "- 中度延误(24-48h)：CII正常可提速，CII偏高则保持经济航速\n"
        "- 无延误但CII超标：降速减排\n"
        "- 提前到达：可适当减速节省燃油"
    )


def _rule_based_prompt() -> str:
    return (
        "你是一个规则优先的航运AI调度员。你的决策严格遵循以下优先级：\n"
        "1. 碳排放合规是第一位 — CII比率超过1.35(D级)时必须立即降速\n"
        "2. CII在1.15-1.35之间时，除非延误超过12小时否则优先降速\n"
        "3. 只有在CII安全(<1.15)时，才可全速赶班\n"
        "4. 航速不超过经济航速+1节，不超过设计航速的90%"
    )


def _cii_prompt() -> str:
    return (
        "你是一个严格CII合规的航运AI调度员。你的唯一优先级是碳排放控制：\n"
        "1. 始终将CII评级维持在B级以上（CII比率<1.00）\n"
        "2. 当前CII评级低于目标时立即降速\n"
        "3. 降速幅度根据评级差距决定（每差一级降10%）\n"
        "4. 只有在CII完全合规的前提下才考虑准班率"
    )


def _default_balanced_tools() -> List[ToolBinding]:
    return [
        ToolBinding(tool_id="get_cii_status", enabled=True),
        ToolBinding(tool_id="get_delay_info", enabled=True),
        ToolBinding(tool_id="get_port_queue_info", enabled=True),
        ToolBinding(tool_id="check_cooldown", enabled=True),
        ToolBinding(tool_id="calculate_optimal_speed", enabled=True),
        ToolBinding(tool_id="evaluate_tradeoff", enabled=True),
        ToolBinding(tool_id="adjust_speed", enabled=True),
    ]


def _default_rule_based_tools() -> List[ToolBinding]:
    return [
        ToolBinding(tool_id="get_cii_status", enabled=True),
        ToolBinding(tool_id="get_delay_info", enabled=True),
        ToolBinding(tool_id="check_cooldown", enabled=True),
        ToolBinding(tool_id="calculate_optimal_speed", enabled=True),
        ToolBinding(tool_id="adjust_speed", enabled=True),
    ]


def _default_cii_tools() -> List[ToolBinding]:
    return [
        ToolBinding(tool_id="get_cii_status", enabled=True),
        ToolBinding(tool_id="get_delay_info", enabled=False),
        ToolBinding(tool_id="calculate_optimal_speed", enabled=True),
        ToolBinding(tool_id="adjust_speed", enabled=True),
    ]


def _default_configs() -> List[AgentConfig]:
    return [
        AgentConfig(
            id="balanced_agent",
            name="多目标均衡代理",
            description="综合考量延误、碳排放、燃油成本和港口效率，多目标均衡优化",
            category="speed_optimization",
            enabled=True,
            decision_mode="fast",
            system_prompt=_balanced_prompt(),
            tools=_default_balanced_tools(),
            parameters={
                "delay_weight": 0.40,
                "cii_weight": 0.20,
                "fuel_weight": 0.20,
                "port_weight": 0.20,
                "delay_critical": 48.0,
                "delay_warning": 24.0,
                "speed_boost_critical": 1.5,
                "speed_boost_warning": 1.0,
                "max_speed_pct": 0.92,
                "cii_critical": 1.35,
                "cii_warning": 1.15,
                "tolerance_hours": 12.0,
                "cooldown_hours": 24.0,
                "cii_reduce_speed_pct": 0.95,
                "eco_speed_over_economic": 1.0,
            },
        ),
        AgentConfig(
            id="rule_based_agent",
            name="规则优先代理",
            description="碳排放合规优先，延误容忍度低，严格按规则执行",
            category="cii_protection",
            enabled=True,
            decision_mode="fast",
            system_prompt=_rule_based_prompt(),
            tools=_default_rule_based_tools(),
            parameters={
                "cii_critical": 1.35,
                "cii_warning": 1.15,
                "delay_tolerance_hours": 12.0,
                "max_speed_over_economic": 1.0,
                "cooldown_hours": 24.0,
                "speed_change_min": 0.5,
            },
        ),
        AgentConfig(
            id="cii_agent",
            name="CII 合规代理",
            description="严格遵循IMO CII评级标准，优先保证碳排放合规",
            category="cii_protection",
            enabled=True,
            decision_mode="fast",
            system_prompt=_cii_prompt(),
            tools=_default_cii_tools(),
            parameters={
                "cii_target_rating": 2.0,  # 0=A, 1=B, 2=C, 3=D, 4=E
                "cii_reduce_per_rating": 0.10,
                "cii_max_reduction": 0.25,
                "design_speed_pct": 0.9,
            },
        ),
    ]


def _migrate_from_rules() -> List[AgentConfig]:
    """从旧的 .ai_rules.json 迁移参数到 agent configs。"""
    rules_path = os.path.join(os.path.dirname(__file__), "..", "..", ".ai_rules.json")
    configs = _default_configs()
    if not os.path.exists(rules_path):
        return configs

    try:
        with open(rules_path, "r", encoding="utf-8") as f:
            rules_data = json.load(f)
    except Exception:
        return configs

    rules_map = {}
    for item in rules_data:
        if "id" in item and "params" in item:
            rules_map[item["id"]] = {
                p["key"]: p["value"] for p in item["params"].values()
            }

    # 将规则值映射到 balanced_agent 的参数
    param_map = {
        "delay_critical": ("speed_priority", "delay_critical"),
        "delay_warning": ("speed_priority", "delay_warning"),
        "speed_boost_critical": ("speed_priority", "speed_boost_critical"),
        "speed_boost_warning": ("speed_priority", "speed_boost_warning"),
        "max_speed_pct": ("speed_priority", "max_speed_pct"),
        "cii_critical": ("cii_thresholds", "cii_critical"),
        "cii_warning": ("cii_thresholds", "cii_warning"),
        "cii_reduce_speed_pct": ("cii_thresholds", "cii_reduce_speed_pct"),
        "eco_speed_over_economic": ("cii_thresholds", "eco_speed_over_economic"),
        "cooldown_hours": ("speed_cooldown", "cooldown_hours"),
        "tolerance_hours": ("delay_tolerance", "tolerance_hours"),
        "delay_weight": ("delay_tolerance", "delay_weight"),
        "cii_weight": ("delay_tolerance", "cii_weight"),
        "fuel_weight": ("delay_tolerance", "fuel_weight"),
        "port_weight": ("delay_tolerance", "port_weight"),
        "delay_tolerance_hours": ("delay_tolerance", "tolerance_hours"),
    }

    for config in configs:
        if config.id == "balanced_agent":
            for param_key, (rule_id, rule_param) in param_map.items():
                if rule_id in rules_map and rule_param in rules_map[rule_id]:
                    config.parameters[param_key] = rules_map[rule_id][rule_param]

    logger.info(f"已从 .ai_rules.json 迁移参数到 agent configs")
    return configs


class AgentConfigService:
    """Agent 配置服务 — 单例，管理配置的加载/保存。"""

    def __init__(self):
        self._configs: Dict[str, AgentConfig] = {}
        self._load()

    def _load(self) -> None:
        """从 JSON 文件加载配置，文件不存在则迁移/使用默认值。"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for item in data:
                    config = AgentConfig(**item)
                    self._configs[config.id] = config
                logger.info(f"已加载 {len(self._configs)} 个 agent 配置")
                return
            except Exception as e:
                logger.warning(f"加载 agent 配置失败，使用默认值: {e}")

        # 尝试从旧规则迁移
        configs = _migrate_from_rules()
        for config in configs:
            self._configs[config.id] = config
        self._save()
        logger.info(f"已创建 {len(self._configs)} 个默认 agent 配置")

    def _save(self) -> None:
        try:
            data = [c.model_dump() for c in self._configs.values()]
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存 agent 配置失败: {e}")

    def get_all(self) -> List[AgentConfig]:
        return list(self._configs.values())

    def get(self, config_id: str) -> Optional[AgentConfig]:
        return self._configs.get(config_id)

    def get_by_category(self, category: str) -> List[AgentConfig]:
        return [c for c in self._configs.values() if c.category == category]

    def get_enabled_tool_ids(self, config_id: str) -> List[str]:
        """获取指定 agent 已启用的工具 ID 列表。"""
        config = self._configs.get(config_id)
        if not config or not config.enabled:
            return []
        return [t.tool_id for t in config.tools if t.enabled]

    def get_tool_params(self, config_id: str, tool_id: str) -> Dict[str, float]:
        """获取指定 agent 的某个工具的覆盖参数。"""
        config = self._configs.get(config_id)
        if not config:
            return {}
        for t in config.tools:
            if t.tool_id == tool_id:
                return t.params
        return {}

    def update(self, config_id: str, updates: Dict[str, Any]) -> Optional[AgentConfig]:
        """更新 agent 配置。"""
        config = self._configs.get(config_id)
        if not config:
            return None

        if "enabled" in updates:
            config.enabled = bool(updates["enabled"])
        if "decision_mode" in updates:
            config.decision_mode = str(updates["decision_mode"])
        if "system_prompt" in updates:
            config.system_prompt = str(updates["system_prompt"])
        if "parameters" in updates:
            config.parameters.update(updates["parameters"])
        if "tools" in updates:
            for tool_update in updates["tools"]:
                for existing in config.tools:
                    if existing.tool_id == tool_update.get("tool_id"):
                        if "enabled" in tool_update:
                            existing.enabled = bool(tool_update["enabled"])
                        if "params" in tool_update:
                            existing.params.update(tool_update["params"])
                        break

        self._save()
        return config

    def reset_to_defaults(self) -> List[AgentConfig]:
        self._configs = {}
        for config in _default_configs():
            self._configs[config.id] = config
        self._save()
        return self.get_all()


_service: Optional[AgentConfigService] = None


def get_agent_config_service() -> AgentConfigService:
    global _service
    if _service is None:
        _service = AgentConfigService()
    return _service
