# 海运仿真迁移到 LinerDT - 完整实施方案

## 项目概述

**目标**：将海运仿真系统的核心算法和仿真引擎迁移到 LinerDT 平台

**方案**：保留 LinerDT 框架 + 替换仿真引擎 + 集成专业算法

**时间**：10天分阶段实施

---

## 关键决策

| 决策项 | 选择 | 理由 |
|---|---|---|
| **数据迁移** | 复制到 LinerDT backend/app/data/ | 稳妥、独立、便于管理 |
| **代码集成** | 海运仿真作为 Python 包安装 | 保持独立性、便于维护 |
| **引擎替换** | 完全替换 scheduler.py | 避免双引擎复杂性、彻底改造 |

---

## 核心架构对比

### LinerDT 优势（保留）
- ✅ AnyLogic Agent 框架（树形层次化）
- ✅ FastAPI + WebSocket（实时通信）
- ✅ Next.js 前端（专业可视化）
- ✅ Leaflet/Cesium 地图（2D/3D切换）
- ✅ ECharts 图表（专业仪表盘）
- ✅ AI 集成（Claude API）
- ✅ 实验管理（参数扫描/Monte Carlo）

### 海运仿真优势（集成）
- ✅ DEVS 仿真引擎（专业离散事件仿真）
- ✅ IMO 油耗计算（标准公式）
- ✅ 收益成本分析（完整财务模型）
- ✅ 港口拥堵模型（M/M/c队列）
- ✅ 强制装载逻辑（航线区分+容量限制）

---

## 详细实施步骤

### 任务1：创建 DEVS 适配器（核心工作）

**文件位置**：`backend/app/scheduler/devs_adapter.py`

**职责**：
1. 包装 DEVS SimulationEngine
2. 映射 Agent 树结构（Engine → Model → Ships/Ports）
3. 提供实时状态查询接口
4. 管理 WebSocket 数据推送

**核心代码**：

```python
"""
DEVS 引擎适配器

将 DEVS SimulationEngine 适配到 LinerDT Agent 框架
"""

import sys
import os

# 添加海运仿真路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '海运仿真', '海运仿真'))

from src.devs.sim.engine import SimulationEngine
from src.devs import ShippingNetwork, load_route_schedule, load_od_demand, filter_ods_by_route
from app.core.tree import Agent, Engine as TreeEngine
from app.scheduler.visualization_sync import get_visualization_sync


class DEVSAdapter:
    """
    DEVS 引擎适配器
    
    负责：
    1. 包装 DEVS SimulationEngine
    2. 构建 Agent 树（映射 DEVS 模型）
    3. 提供实时状态查询
    4. 推送数据到 WebSocket
    """
    
    def __init__(self):
        self.devs_engine = None
        self.agent_tree = None
        self.config = None
        self.is_running = False
        
    def initialize(self, config: dict):
        """
        初始化仿真
        
        :param config: {
            'speed': 19,  # 船速（节）
            'capacity': 21000,  # 船舶容量（TEU）
            'berth_count': 3,  # 泊位数
            'weeks': 30,  # 仿真周数
            'max_time': 250,  # 最大时间（天）
        }
        """
        self.config = config
        
        # 1. 加载航线数据
        base_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '海运仿真', '海运仿真')
        data_dir = os.path.join(base_dir, '海运数据')
        
        schedules = load_route_schedule(os.path.join(data_dir, '航线船期_20260507_ych.csv'))
        
        # 2. 加载 OD 数据
        od_file = os.path.join(data_dir, 'od对需求_with_route.csv')
        if not os.path.exists(od_file):
            od_file = os.path.join(data_dir, 'od对需求_20260507_ych.csv')
        all_ods = load_od_demand(od_file)
        
        # 3. 筛选 OD 对
        route_od_map = {}
        for s in schedules:
            matched = filter_ods_by_route(all_ods, s)
            route_od_map[s.route_id] = matched
        
        # 4. 计算船舶数量
        vessels_per_route = max(int(s.total_days / 7) + 2 for s in schedules)
        
        # 5. 构建 DEVS 网络
        network = ShippingNetwork(
            name="ShippingNetwork",
            routes=schedules,
            route_od_map=route_od_map,
            weeks_to_sim=config['weeks'],
            vessels_per_route=vessels_per_route,
        )
        
        # 6. 创建 DEVS 引擎
        self.devs_engine = SimulationEngine(network, max_time=config['max_time'])
        self.devs_engine.initialize()
        
        # 7. 构建 Agent 树
        self._build_agent_tree()
        
        self.is_running = True
        
    def _build_agent_tree(self):
        """从 DEVS 模型构建 Agent 树"""
        # Engine 根节点
        engine_agent = TreeEngine(name="engine")
        engine_agent.current_time = 0.0
        
        # Model 子节点
        model_agent = Agent(name="model", owner=engine_agent)
        
        # 获取 DEVS 模型中的船舶和港口
        # 注意：DEVS 模型在耦合模型内部，需要遍历获取
        
        # Ship Agents（从 events 推断）
        vessel_names = set()
        for event in self.devs_engine.all_events:
            if event.event_type in ['ARRIVAL', 'DEPARTURE']:
                vessel_names.add(event.vessel_name)
        
        for vessel_name in vessel_names:
            ship_agent = Agent(
                name=vessel_name,
                owner=model_agent,
            )
            # 设置参数
            ship_agent.set_parameter('speed', self.config['speed'])
            ship_agent.set_parameter('capacity', self.config['capacity'])
        
        # Port Agents（从 events 推断）
        port_codes = set()
        for event in self.devs_engine.all_events:
            port_codes.add(event.port_code)
        
        for port_code in port_codes:
            port_agent = Agent(
                name=port_code,
                owner=model_agent,
            )
            port_agent.set_parameter('berth_count', self.config['berth_count'])
        
        self.agent_tree = engine_agent
        
    def step(self) -> bool:
        """执行一步仿真"""
        if not self.devs_engine or not self.is_running:
            return False
            
        result = self.devs_engine.step()
        
        if result:
            # 更新 Agent 树时间
            self.agent_tree.current_time = self.devs_engine.current_time
            
            # 推送数据到 WebSocket
            self._push_to_websocket()
        
        return result
        
    def _push_to_websocket(self):
        """推送数据到 WebSocket"""
        viz_sync = get_visualization_sync()
        state = self.get_state()
        viz_sync.push_state(state)
        
    def get_state(self) -> dict:
        """获取当前状态"""
        if not self.devs_engine:
            return {}
        
        # 收集船舶状态
        vessels = {}
        for event in self.devs_engine.all_events[-100:]:  # 最近100个事件
            if event.vessel_name not in vessels:
                vessels[event.vessel_name] = {
                    'name': event.vessel_name,
                    'route': event.route_id,
                    'current_port': event.port_code,
                    'last_event': event.event_type,
                    'time': event.sim_time,
                }
        
        # 收集港口状态
        ports = {}
        for stat in self.devs_engine.all_stats[-50:]:  # 最近50个统计
            if stat.port_code not in ports:
                ports[stat.port_code] = {
                    'code': stat.port_code,
                    'vessel_count': stat.vessel_count,
                    'cargo_loaded': stat.cargo_loaded,
                    'cargo_discharged': stat.cargo_discharged,
                }
        
        # 收集货物状态
        cargo_count = len(self.devs_engine.all_cargo)
        
        return {
            'time': self.devs_engine.current_time,
            'step_count': self.devs_engine.step_count,
            'max_time': self.devs_engine.max_time,
            'vessels': vessels,
            'ports': ports,
            'cargo_count': cargo_count,
            'events_count': len(self.devs_engine.all_events),
            'stats_count': len(self.devs_engine.all_stats),
        }
        
    def run_all(self):
        """运行完整仿真"""
        while self.step():
            pass
        
        self.is_running = False
        
    def stop(self):
        """停止仿真"""
        self.is_running = False
        
    def get_events(self):
        """获取所有事件"""
        return self.devs_engine.all_events if self.devs_engine else []
        
    def get_stats(self):
        """获取所有统计"""
        return self.devs_engine.all_stats if self.devs_engine else []
        
    def get_cargo(self):
        """获取所有货物"""
        return self.devs_engine.all_cargo if self.devs_engine else []
```

---

### 任务2：集成油耗计算服务

**文件位置**：`backend/app/services/fuel_service.py`

**职责**：
1. IMO 标准油耗计算
2. 燃油成本计算
3. 碳排放计算（对接 LinerDT carbon 模块）

**核心代码**：

```python
"""
IMO 油耗计算服务

来源：海运仿真 src/devs/utils/fuel_calculator.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '海运仿真', '海运仿真'))

from src.devs.utils.fuel_calculator import FuelCalculator
from src.devs.types import VesselCharacteristics
from src.devs.config import get_vessel_capacity, DEFAULT_FUEL_PRICE


class FuelService:
    """
    油耗计算服务
    
    功能：
    1. IMO 标准油耗计算
    2. 燃油成本计算
    3. 碳排放计算
    """
    
    def __init__(self):
        self.calculators = {}  # 每艘船一个计算器
        
    def create_calculator(self, vessel_name: str, route_id: str, capacity: int = None):
        """
        为船舶创建油耗计算器
        
        :param vessel_name: 船名
        :param route_id: 航线ID
        :param capacity: 船舶容量（可选，默认从config获取）
        """
        if capacity is None:
            capacity = get_vessel_capacity(route_id)
        
        chars = VesselCharacteristics(
            vessel_name=vessel_name,
            route_id=route_id,
            design_speed=20.0,
            main_engine_power=50000.0,
            sfoc=175.0,
            capacity_teus=capacity,
            fuel_price=DEFAULT_FUEL_PRICE,
        )
        
        self.calculators[vessel_name] = FuelCalculator(chars)
        
    def calculate_fuel(
        self,
        vessel_name: str,
        speed: float,
        distance_nm: float,
        load_factor: float,
        time_days: float = None
    ) -> float:
        """
        计算油耗
        
        :param vessel_name: 船名
        :param speed: 船速（节）
        :param distance_nm: 距离（海里）
        :param load_factor: 载重因子（0-1）
        :param time_days: 时间（天，可选）
        :return: 油耗（吨）
        """
        calculator = self.calculators.get(vessel_name)
        if not calculator:
            return 0.0
        
        return calculator.calculate_fuel_consumption(
            speed, distance_nm, load_factor, time_days
        )
        
    def calculate_cost(self, vessel_name: str, fuel_consumed: float) -> float:
        """
        计算燃油成本
        
        :param vessel_name: 船名
        :param fuel_consumed: 油耗（吨）
        :return: 成本（$）
        """
        calculator = self.calculators.get(vessel_name)
        if not calculator:
            return 0.0
        
        return calculator.calculate_fuel_cost(fuel_consumed)
        
    def get_speed_options(self, vessel_name: str) -> dict:
        """
        获取速度选项
        
        :return: {'economic': 15, 'normal': 19, 'fast': 22}
        """
        calculator = self.calculators.get(vessel_name)
        if not calculator:
            return {}
        
        return calculator.get_speed_options()
        
    def calculate_carbon_emissions(self, fuel_consumed: float) -> float:
        """
        计算碳排放
        
        :param fuel_consumed: 油耗（吨）
        :return: 碳排放（吨CO2）
        """
        # IMO 标准：1吨燃油 ≈ 3.1吨CO2
        return fuel_consumed * 3.1


# 全局单例
_fuel_service = None

def get_fuel_service() -> FuelService:
    """获取油耗服务单例"""
    global _fuel_service
    if _fuel_service is None:
        _fuel_service = FuelService()
    return _fuel_service
```

---

### 任务3：集成收益计算服务

**文件位置**：`backend/app/services/revenue_service.py`

**核心代码**：

```python
"""
收益计算服务

来源：海运仿真 src/devs/utils/revenue_calculator.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '海运仿真', '海运仿真'))

from src.devs.utils.revenue_calculator import RevenueCalculator
from src.devs.types import VesselCharacteristics, CargoBatch
from src.devs.config import (
    DEFAULT_DAILY_CHARTER_RATE,
    DEFAULT_PORT_LOADING_COST,
    DEFAULT_PORT_DISCHARGING_COST,
    DEFAULT_PORT_CALL_COST,
)


class RevenueService:
    """
    收益计算服务
    
    功能：
    1. 运输收入计算
    2. 成本分解（燃油、港口、时间）
    3. 利润分析
    4. 财务报告生成
    """
    
    def __init__(self):
        self.calculators = {}
        
    def create_calculator(self, vessel_name: str, route_id: str, capacity: int):
        """创建收益计算器"""
        chars = VesselCharacteristics(
            vessel_name=vessel_name,
            route_id=route_id,
            capacity_teus=capacity,
            daily_charter_rate=DEFAULT_DAILY_CHARTER_RATE,
        )
        
        self.calculators[vessel_name] = RevenueCalculator(chars)
        
    def calculate_revenue(self, cargo_list: list) -> float:
        """
        计算运输收入
        
        :param cargo_list: 货物列表
        :return: 总收入（$）
        """
        total = 0.0
        for cargo in cargo_list:
            if hasattr(cargo, 'ffe') and hasattr(cargo, 'revenue_per_unit'):
                total += cargo.ffe * cargo.revenue_per_unit
        return total
        
    def calculate_full_report(
        self,
        vessel_name: str,
        cargo_list: list,
        fuel_consumed: float,
        time_days: float,
        port_call_count: int = 10
    ) -> dict:
        """
        生成完整财务报告
        
        :return: {
            'total_revenue': 总收入,
            'fuel_cost': 燃油成本,
            'port_cost': 港口费用,
            'time_cost': 时间成本,
            'total_cost': 总成本,
            'net_profit': 净利润,
            'profit_margin': 利润率,
        }
        """
        calculator = self.calculators.get(vessel_name)
        if not calculator:
            return {}
        
        return calculator.calculate_full_report(
            cargo_list, fuel_consumed, time_days, port_call_count
        )
        
    def get_profit_margin(self, report: dict) -> float:
        """获取利润率"""
        if not report or report.get('total_revenue', 0) == 0:
            return 0.0
        
        return (report['net_profit'] / report['total_revenue']) * 100


# 全局单例
_revenue_service = None

def get_revenue_service() -> RevenueService:
    """获取收益服务单例"""
    global _revenue_service
    if _revenue_service is None:
        _revenue_service = RevenueService()
    return _revenue_service
```

---

### 任务4：集成港口拥堵服务

**文件位置**：`backend/app/services/congestion_service.py`

**核心代码**：

```python
"""
港口拥堵模型服务

来源：海运仿真 src/devs/utils/congestion_model.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '海运仿真', '海运仿真'))

from src.devs.utils.congestion_model import SimplifiedCongestionModel, PortCongestionManager
from src.devs.types import VesselEvent


class CongestionService:
    """
    港口拥堵服务
    
    功能：
    1. M/M/c 队列模型
    2. 等待时间预测
    3. 泊位利用率计算
    """
    
    def __init__(self):
        self.manager = PortCongestionManager()
        
    def init_port_model(
        self,
        port_code: str,
        berth_count: int = 3,
        handling_rate: float = 1000.0,
        service_rate: float = 1.0
    ):
        """
        初始化港口拥堵模型
        
        :param port_code: 港口代码
        :param berth_count: 泊位数
        :param handling_rate: 处理能力（TEU/天）
        :param service_rate: 服务率（船/天）
        """
        model = SimplifiedCongestionModel(
            port_code=port_code,
            berth_count=berth_count,
            handling_rate=handling_rate,
            service_rate=service_rate,
        )
        
        self.manager.port_models[port_code] = model
        
    def update_from_event(self, port_code: str, vessel_event: VesselEvent) -> float:
        """
        根据船舶事件更新拥堵状态
        
        :param port_code: 港口代码
        :param vessel_event: 船舶事件
        :return: 等待时间（小时）
        """
        return self.manager.update_from_event(vessel_event)
        
    def get_congestion_state(self, port_code: str) -> dict:
        """
        获取港口拥堵状态
        
        :return: {
            'queue_length': 队列长度,
            'avg_wait_time': 平均等待时间,
            'utilization_rate': 泊位利用率,
        }
        """
        model = self.manager.get_port_model(port_code)
        if not model:
            return {}
        
        return model.get_congestion_state(0.0)


# 全局单例
_congestion_service = None

def get_congestion_service() -> CongestionService:
    """获取拥堵服务单例"""
    global _congestion_service
    if _congestion_service is None:
        _congestion_service = CongestionService()
    return _congestion_service
```

---

### 任务5：修改 API 接口

**文件位置**：`backend/app/api/sim.py`（扩展）

**关键修改**：

```python
# 在 sim.py 开头添加
from app.scheduler.devs_adapter import DEVSAdapter
from app.services.fuel_service import get_fuel_service
from app.services.revenue_service import get_revenue_service
from app.services.congestion_service import get_congestion_service

# 全局 DEVS 适配器
devs_adapter = None

# 替换原有的 start_simulation 函数
@router.post("/start")
async def start_simulation(config: SimulationConfig):
    """启动仿真（使用 DEVS 引擎）"""
    global devs_adapter
    
    # 创建 DEVS 适配器
    devs_adapter = DEVSAdapter()
    
    # 初始化配置
    devs_config = {
        'speed': config.speed,
        'capacity': config.capacity,
        'berth_count': config.berth_count,
        'weeks': config.weeks,
        'max_time': config.max_time,
    }
    
    devs_adapter.initialize(devs_config)
    
    # 异步运行仿真
    asyncio.create_task(run_simulation_loop())
    
    return {"status": "started", "engine": "DEVS"}

# 添加新接口：获取油耗数据
@router.get("/fuel/{vessel_name}")
async def get_fuel_data(vessel_name: str):
    """获取船舶油耗数据"""
    fuel_service = get_fuel_service()
    
    # 从仿真状态获取数据
    state = devs_adapter.get_state()
    vessel = state['vessels'].get(vessel_name)
    
    if not vessel:
        return {"error": "vessel not found"}
    
    # 计算油耗（示例）
    fuel_consumed = 100.0  # 从实际数据计算
    fuel_cost = fuel_service.calculate_cost(vessel_name, fuel_consumed)
    
    return {
        "vessel": vessel_name,
        "fuel_consumed": fuel_consumed,
        "fuel_cost": fuel_cost,
    }

# 添加新接口：获取收益数据
@router.get("/revenue/{vessel_name}")
async def get_revenue_data(vessel_name: str):
    """获取船舶收益数据"""
    revenue_service = get_revenue_service()
    
    state = devs_adapter.get_state()
    
    # 计算收益（示例）
    cargo_list = devs_adapter.get_cargo()
    revenue = revenue_service.calculate_revenue(cargo_list)
    
    return {
        "vessel": vessel_name,
        "total_revenue": revenue,
    }
```

---

### 任务6：前端仪表盘扩展

**文件位置**：`frontend/components/dashboard/FuelChart.tsx`（新建）

**核心代码**：

```tsx
import ReactECharts from 'echarts-for-react';
import { useWebSocket } from '@/hooks/useWebSocket';

export function FuelChart() {
  const { state } = useWebSocket();
  
  // 从 WebSocket 数据提取油耗数据
  const fuelData = state?.fuel || { times: [], consumed: [] };
  
  const option = {
    title: {
      text: '油耗统计',
      left: 'center',
      textStyle: { fontSize: 16 },
    },
    tooltip: {
      trigger: 'axis',
      formatter: '{b}<br/>油耗: {c} 吨',
    },
    xAxis: {
      type: 'category',
      data: fuelData.times,
      name: '时间（天）',
      nameLocation: 'middle',
      nameGap: 30,
    },
    yAxis: {
      type: 'value',
      name: '油耗（吨）',
      nameLocation: 'middle',
      nameGap: 40,
    },
    series: [{
      name: '油耗',
      type: 'line',
      data: fuelData.consumed,
      smooth: true,
      itemStyle: { color: '#5470c6' },
      areaStyle: { opacity: 0.3 },
    }],
    grid: {
      left: '10%',
      right: '10%',
      bottom: '15%',
      top: '20%',
    },
  };
  
  return (
    <div className="bg-white rounded-lg shadow p-4">
      <ReactECharts option={option} style={{ height: '300px' }} />
    </div>
  );
}
```

---

### 任务7：参数配置面板扩展

**文件位置**：`frontend/components/SimulationConfig.tsx`（扩展）

**添加参数**：

```tsx
// 在 SimulationConfig.tsx 中添加海运仿真参数

{/* 船速选择 */}
<div className="mb-4">
  <label className="block text-sm font-medium mb-2">船速（节）</label>
  <select 
    className="w-full p-2 border rounded focus:ring-2 focus:ring-blue-500"
    value={config.speed}
    onChange={(e) => setConfig({...config, speed: parseInt(e.target.value)})}
  >
    <option value="15">经济速度 (15节) - 燃油节省</option>
    <option value="19">默认速度 (19节) - 平衡</option>
    <option value="22">快速速度 (22节) - 时间优先</option>
  </select>
  <p className="text-xs text-gray-500 mt-1">
    经济速度可节省15%燃油成本，快速速度可缩短20%运输时间
  </p>
</div>

{/* 船舶容量 */}
<div className="mb-4">
  <label className="block text-sm font-medium mb-2">船舶容量（TEU）</label>
  <input 
    type="range" 
    min="10000" 
    max="25000" 
    step="1000"
    value={config.capacity}
    onChange={(e) => setConfig({...config, capacity: parseInt(e.target.value)})}
    className="w-full"
  />
  <div className="flex justify-between text-xs text-gray-500">
    <span>10,000</span>
    <span className="font-medium">{config.capacity}</span>
    <span>25,000</span>
  </div>
</div>

{/* 仿真周数 */}
<div className="mb-4">
  <label className="block text-sm font-medium mb-2">仿真周数</label>
  <select 
    className="w-full p-2 border rounded"
    value={config.weeks}
    onChange={(e) => setConfig({...config, weeks: parseInt(e.target.value)})}
  >
    <option value="5">5周（快速验证）</option>
    <option value="30">30周（标准仿真）</option>
    <option value="52">52周（完整年度）</option>
  </select>
</div>
```

---

### 任务8：AI 工具扩展

**文件位置**：`backend/app/ai/safe_tools.py`（扩展）

**添加工具**：

```python
# 在 safe_tools.py 中添加海运仿真查询工具

from app.services.fuel_service import get_fuel_service
from app.services.revenue_service import get_revenue_service
from app.scheduler.devs_adapter import devs_adapter

def get_fuel_status(vessel_name: str = None) -> dict:
    """
    查询船舶油耗状态
    
    :param vessel_name: 船名（可选，不提供则返回所有船舶）
    :return: 油耗数据
    """
    fuel_service = get_fuel_service()
    
    if not devs_adapter:
        return {"error": "simulation not running"}
    
    state = devs_adapter.get_state()
    
    if vessel_name:
        vessel = state['vessels'].get(vessel_name)
        if not vessel:
            return {"error": f"vessel {vessel_name} not found"}
        
        # 计算油耗（示例）
        fuel_consumed = 100.0
        fuel_cost = fuel_service.calculate_cost(vessel_name, fuel_consumed)
        
        return {
            "vessel": vessel_name,
            "fuel_consumed": fuel_consumed,
            "fuel_cost": fuel_cost,
            "fuel_rate": fuel_consumed / state['time'] if state['time'] > 0 else 0,
        }
    else:
        # 返回所有船舶油耗汇总
        total_fuel = 0.0
        total_cost = 0.0
        
        for vessel_name in state['vessels']:
            fuel_consumed = 100.0
            total_fuel += fuel_consumed
            total_cost += fuel_service.calculate_cost(vessel_name, fuel_consumed)
        
        return {
            "total_fuel_consumed": total_fuel,
            "total_fuel_cost": total_cost,
            "vessel_count": len(state['vessels']),
        }

def get_revenue_status(vessel_name: str = None) -> dict:
    """
    查询船舶收益状态
    
    :param vessel_name: 船名（可选）
    :return: 收益数据
    """
    revenue_service = get_revenue_service()
    
    if not devs_adapter:
        return {"error": "simulation not running"}
    
    cargo_list = devs_adapter.get_cargo()
    total_revenue = revenue_service.calculate_revenue(cargo_list)
    
    return {
        "total_revenue": total_revenue,
        "cargo_count": len(cargo_list),
        "average_revenue_per_cargo": total_revenue / len(cargo_list) if cargo_list else 0,
    }

def suggest_speed_optimization(current_speed: float) -> dict:
    """
    AI 建议：航速优化
    
    :param current_speed: 当前船速（节）
    :return: 优化建议
    """
    fuel_service = get_fuel_service()
    
    # 计算不同速度下的油耗
    speeds = [15, 17, 19, 21, 22]
    fuel_estimates = []
    
    for speed in speeds:
        # 示例计算（实际应从仿真数据获取）
        fuel = fuel_service.calculate_fuel("sample_vessel", speed, 5000, 0.7)
        fuel_estimates.append({
            'speed': speed,
            'fuel': fuel,
            'cost': fuel_service.calculate_cost("sample_vessel", fuel),
        })
    
    # 找到最优速度（油耗最低）
    optimal = min(fuel_estimates, key=lambda x: x['fuel'])
    
    return {
        "current_speed": current_speed,
        "optimal_speed": optimal['speed'],
        "fuel_savings": (optimal['fuel'] - fuel_estimates[0]['fuel']) / fuel_estimates[0]['fuel'] * 100,
        "recommendation": f"建议将船速从 {current_speed}节 降低到 {optimal['speed']}节，可节省 {optimal['fuel']:.1f}吨燃油",
    }

# 注册到 AI 工具列表
TOOLS.extend([
    get_fuel_status,
    get_revenue_status,
    suggest_speed_optimization,
])
```

---

### 任务9：参数扫描实验

**文件位置**：`backend/app/api/experiment.py`（扩展）

**添加实验**：

```python
# 在 experiment.py 中添加海运仿真参数扫描

@router.post("/sweep/fuel")
async def fuel_parameter_sweep(config: FuelSweepConfig):
    """
    油耗参数扫描
    
    参数：
    - speed_range: [15, 17, 19, 21, 22]（节）
    - capacity_range: [15000, 18000, 21000]（TEU）
    - weeks: 30（仿真周数）
    """
    results = []
    
    for speed in config.speed_range:
        for capacity in config.capacity_range:
            # 运行仿真
            devs_adapter = DEVSAdapter()
            devs_adapter.initialize({
                'speed': speed,
                'capacity': capacity,
                'weeks': config.weeks,
                'max_time': config.weeks * 7,
            })
            
            devs_adapter.run_all()
            
            # 收集结果
            state = devs_adapter.get_state()
            
            # 计算总油耗
            fuel_service = get_fuel_service()
            total_fuel = 0.0
            
            for vessel_name in state['vessels']:
                fuel_service.create_calculator(vessel_name, 'AEU1', capacity)
                fuel = fuel_service.calculate_fuel(vessel_name, speed, 5000, 0.7)
                total_fuel += fuel
            
            results.append({
                'speed': speed,
                'capacity': capacity,
                'fuel_consumed': total_fuel,
                'fuel_cost': fuel_service.calculate_cost('sample', total_fuel),
            })
    
    return {
        "experiment": "fuel_parameter_sweep",
        "results": results,
        "best_config": min(results, key=lambda x: x['fuel_consumed']),
    }
```

---

### 任务10：测试验证

**验证清单**：

#### 后端验证
- ✅ DEVS 引擎可启动仿真
- ✅ Agent 树正确构建（Engine → Model → Ships/Ports）
- ✅ WebSocket 可推送实时数据
- ✅ 油耗计算正确（验证 IMO 公式）
- ✅ 收益计算正确（验证成本分解）
- ✅ API 接口可查询数据

#### 前端验证
- ✅ 地图显示船舶位置（实时更新）
- ✅ 油耗图表正确显示
- ✅ 收益图表正确显示
- ✅ 参数可调整（船速、容量）
- ✅ 仿真控制按钮工作（暂停/继续）

#### AI 验证
- ✅ AI 可查询油耗数据
- ✅ AI 可查询收益数据
- ✅ AI 可给出航速建议

---

## 文件清单

### 后端新增文件（10个）

```
backend/app/scheduler/
├── devs_adapter.py            ✅ 新建（核心，200行）
└── devs_wrapper.py            ✅ 新建（辅助，100行）

backend/app/services/
├── fuel_service.py            ✅ 新建（150行）
├── revenue_service.py         ✅ 新建（200行）
├── congestion_service.py      ✅ 新建（150行）
└── load_service.py            ✅ 新建（100行）

backend/app/api/
├── fuel.py                    ✅ 新建（80行）
├── revenue.py                 ✅ 新建（80行）
└── sim.py                     ✅ 扩展（+100行）

backend/app/data/
├── od_demand.csv              ✅ 复制
├── port_coordinates.csv       ✅ 复制
└── route_schedule.csv         ✅ 复制
```

### 前端新增文件（5个）

```
frontend/components/dashboard/
├── FuelChart.tsx              ✅ 新建（100行）
├── RevenueChart.tsx           ✅ 新建（100行）
├── LoadChart.tsx              ✅ 新建（100行）
├── CongestionChart.tsx        ✅ 新建（100行）
└── SeaSimDashboard.tsx        ✅ 新建（整合组件，150行）
```

---

## 时间表

| 天 | 任务 | 文件 | 预期成果 |
|---|---|---|---|
| **Day 1** | DEVS 引擎适配器 | devs_adapter.py | DEVS 引擎可运行 |
| **Day 2** | 油耗计算服务 | fuel_service.py | IMO 油耗计算可用 |
| **Day 3** | 收益计算服务 | revenue_service.py | 收益分析可用 |
| **Day 4** | 港口拥堵服务 | congestion_service.py | M/M/c 模型可用 |
| **Day 5** | API 接口扩展 | api/fuel.py, revenue.py | 数据接口可用 |
| **Day 6** | 前端仪表盘 | FuelChart.tsx等4个 | 图表可视化 |
| **Day 7** | 参数配置面板 | SimulationConfig.tsx | 参数可调整 |
| **Day 8** | AI 工具扩展 | safe_tools.py | AI 可查询数据 |
| **Day 9** | 参数扫描实验 | experiment.py | 实验管理可用 |
| **Day 10** | 测试和调试 | 全部文件 | 系统验证通过 |

---

## 注意事项

### 1. 数据路径问题

**问题**：海运仿真数据在 `海运数据/` 目录，LinerDT 数据在 `backend/app/data/`

**解决方案**：复制数据文件到 LinerDT

**操作**：
```bash
cp 海运数据/od对需求_with_route.csv LinerDT/backend/app/data/od_demand.csv
cp 海运数据/港口坐标.csv LinerDT/backend/app/data/port_coordinates.csv
cp 海运数据/航线船期_20260507_ych.csv LinerDT/backend/app/data/route_schedule.csv
```

---

### 2. 导入路径问题

**问题**：海运仿真使用 `from src.devs import ...`，LinerDT 使用 `from app import ...`

**解决方案**：在每个服务文件开头添加路径

**代码**：
```python
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '海运仿真', '海运仿真'))
```

---

### 3. Agent 框架适配

**问题**：DEVS 模型不是 Agent，无法直接嵌入 Agent 树

**解决方案**：创建 AgentWrapper 包装 DEVS 模型

**实现**：
```python
class ShipAgentWrapper(Agent):
    """包装 DEVS VesselSailing"""
    
    def __init__(self, vessel_model, owner):
        super().__init__(owner=owner)
        self.devs_model = vessel_model
        
    def get_parameters(self):
        return {
            'speed': self.devs_model.current_speed,
            'load': self.devs_model.current_load,
        }
```

---

## 风险和应对

| 风险 | 影响 | 应对措施 |
|---|---|---|
| **导入路径冲突** | 高 | 使用绝对路径，添加 sys.path.insert |
| **数据格式不兼容** | 中 | 创建数据转换函数 |
| **Agent 框架不匹配** | 高 | 创建适配层（AgentWrapper） |
| **WebSocket 数据格式变化** | 中 | 扩展 visualization_sync.py |
| **前端组件不兼容** | 低 | 使用 ECharts 标准格式 |

---

## 成功标准

### 功能标准
- ✅ 仿真可运行（DEVS 引擎工作）
- ✅ 数据可查询（API 接口工作）
- ✅ 可视化正常（前端图表显示）
- ✅ AI 可查询（AI 工具工作）
- ✅ 实验可运行（参数扫描工作）

### 性能标准
- ✅ 仿真速度：≥100步/秒
- ✅ WebSocket 推送延迟：<100ms
- ✅ 前端渲染流畅：无卡顿

### 代码标准
- ✅ 代码规范：符合 PEP8
- ✅ 文档完整：每个函数有注释
- ✅ 测试覆盖：核心功能有测试

---

## 后续优化方向

1. **性能优化**：
   - 使用多线程加速仿真
   - 优化 WebSocket 推送频率
   - 缓存计算结果

2. **功能扩展**：
   - 添加延误统计
   - 添加碳排放分析
   - 添加多方案对比

3. **用户体验**：
   - 添加仿真回放功能
   - 添加报告生成功能
   - 添加参数持久化

---

**版本**: v1.0
**创建时间**: 2026-05-11
**作者**: 海运仿真项目组