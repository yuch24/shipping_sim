"""
AEU (亚洲—欧洲快航) 航线数据
数据来源: COSCO SHIPPING Lines AEU1/AEU2/AEU3 真实运营数据

三条航线:
  AEU1: 青岛→上海→宁波→厦门→盐田→新加坡→苏伊士→费利克斯托→泽布吕赫→格但斯克→威廉港→(回程)
  AEU2: 宁波→上海→盐田→新加坡→丹吉尔→勒阿弗尔→汉堡→鹿特丹→阿尔赫西拉斯→巴生港→(回程)
  AEU3: 天津→大连→青岛→上海→宁波→新加坡→鹿特丹→汉堡→安特卫普→(回程)
"""

# ── 港口坐标 ─────────────────────────────────────
# 来源: 真实港口经纬度（WGS84）
AEU_PORT_COORDS: dict[str, tuple[float, float]] = {
    # 中国
    "CNTAO": (36.0317, 120.2047),  # 青岛 (Qingdao)
    "CNSHA": (30.5821, 121.0734),  # 上海 洋山深水港 (Shanghai Yangshan)
    "CNNGB": (29.9336, 121.9669),  # 宁波 (Ningbo)
    "CNXMN": (24.4914, 118.0747),  # 厦门 (Xiamen)
    "CNYTN": (22.5727, 114.2751),  # 盐田 (Yantian/Shenzhen)
    "CNTXG": (38.9756, 117.7339),  # 天津 (Tianjin)
    "CNDLC": (38.9694, 121.6608),  # 大连 (Dalian)
    # 东南亚
    "SGSIN": (1.2672, 103.8342),  # 新加坡 (Singapore)
    "MYPKG": (2.9964, 101.3783),  # 巴生港 (Port Klang, Malaysia)
    # 好望角中转标记点
    "CPC01": (-34.5, 18.5),  # 好望角 (Cape of Good Hope) — 绕行中转
    # 北欧
    "GBFXT": (51.9506, 1.3264),  # 费利克斯托 (Felixstowe, UK)
    "BEZEE": (51.3414, 3.1808),  # 泽布吕赫 (Zeebrugge, Belgium)
    "PLGDY": (54.3875, 18.6853),  # 格但斯克 (Gdansk, Poland)
    "DEWVN": (53.5892, 8.1433),  # 威廉港 (Wilhelmshaven, Germany)
    "DEHAM": (53.5242, 9.9792),  # 汉堡 (Hamburg, Germany)
    "NLRTM": (51.9525, 4.0258),  # 鹿特丹 (Rotterdam, Netherlands)
    "BEANR": (51.2731, 4.3558),  # 安特卫普 (Antwerp, Belgium)
    "FRLEH": (49.4794, 0.1825),  # 勒阿弗尔 (Le Havre, France)
    "FRDKK": (51.0397, 2.3717),  # 敦刻尔克 (Dunkerque, France)
    "GBSOU": (50.8761, -1.3972),  # 南安普顿 (Southampton, UK)
    # 地中海/北非
    "MAPTM": (35.8439, -5.5122),  # 丹吉尔 (Tangier, Morocco)
}

# ── 港口代码 → 中文名称映射 ─────────────────────
PORT_CODES_TO_NAMES: dict[str, str] = {
    "CNTAO": "青岛",
    "CNSHA": "上海",
    "CNNGB": "宁波",
    "CNXMN": "厦门",
    "CNYTN": "盐田",
    "CNTXG": "天津",
    "CNDLC": "大连",
    "SGSIN": "新加坡",
    "MYPKG": "巴生港",
    "GBFXT": "费利克斯托",
    "BEZEE": "泽布吕赫",
    "PLGDY": "格但斯克",
    "DEWVN": "威廉港",
    "DEHAM": "汉堡",
    "NLRTM": "鹿特丹",
    "BEANR": "安特卫普",
    "FRLEH": "勒阿弗尔",
    "FRDKK": "敦刻尔克",
    "GBSOU": "南安普顿",
    "MAPTM": "丹吉尔",
}

# ── 港口靠泊信息 ─────────────────────────────────
# (berth_count=30, crane_count, handling_rate_teu_per_hour) — 暂不考虑港口堵塞
PORT_INFRA: dict[str, tuple[int, int, int]] = {
    "CNTAO": (30, 12, 150),
    "CNSHA": (30, 20, 200),
    "CNNGB": (30, 15, 180),
    "CNXMN": (30, 10, 140),
    "CNYTN": (30, 12, 160),
    "CNTXG": (30, 12, 140),
    "CNDLC": (30, 10, 120),
    "SGSIN": (30, 22, 220),
    "MYPKG": (30, 12, 150),
    "GBFXT": (30, 10, 140),
    "BEZEE": (30, 8, 120),
    "PLGDY": (30, 8, 110),
    "DEWVN": (30, 8, 110),
    "DEHAM": (30, 15, 170),
    "NLRTM": (30, 20, 200),
    "BEANR": (30, 15, 170),
    "FRLEH": (30, 10, 140),
    "FRDKK": (30, 8, 110),
    "GBSOU": (30, 8, 110),
    "MAPTM": (30, 10, 130),
}

# ── 船舶数据 ─────────────────────────────────────
# 格式: (vessel_name, code, capacity_teu, service_id, design_speed, fuel_consumption, op_cost_day, charter_cost)
AEU_VESSELS: list[dict] = [
    # ── AEU1 (15 ships, OOCL operated, ~24000 TEU max) ──
    {
        "id": "s001",
        "service": "AEU1",
        "name": "OOCL PIRAEUS",
        "code": "MMX",
        "capacity": 21413,
        "design_speed": 22.0,
        "fuel_consumption": 290.0,
        "op_cost": 18000,
        "charter_cost": 35000,
    },
    {
        "id": "s002",
        "service": "AEU1",
        "name": "OOCL FELIXSTOWE",
        "code": "MHM",
        "capacity": 21413,
        "design_speed": 22.0,
        "fuel_consumption": 290.0,
        "op_cost": 18000,
        "charter_cost": 35000,
    },
    {
        "id": "s003",
        "service": "AEU1",
        "name": "OOCL GERMANY",
        "code": "SHO",
        "capacity": 21413,
        "design_speed": 22.0,
        "fuel_consumption": 290.0,
        "op_cost": 18000,
        "charter_cost": 35000,
    },
    {
        "id": "s004",
        "service": "AEU1",
        "name": "OOCL ABU DHABI",
        "code": "MSW",
        "capacity": 21413,
        "design_speed": 22.0,
        "fuel_consumption": 290.0,
        "op_cost": 18000,
        "charter_cost": 35000,
    },
    {
        "id": "s005",
        "service": "AEU1",
        "name": "OOCL SPAIN",
        "code": "MHJ",
        "capacity": 23964,
        "design_speed": 22.0,
        "fuel_consumption": 300.0,
        "op_cost": 20000,
        "charter_cost": 40000,
    },
    {
        "id": "s006",
        "service": "AEU1",
        "name": "OOCL UNITED KINGDOM",
        "code": "NQ2",
        "capacity": 21413,
        "design_speed": 22.0,
        "fuel_consumption": 290.0,
        "op_cost": 18000,
        "charter_cost": 35000,
    },
    {
        "id": "s007",
        "service": "AEU1",
        "name": "OOCL VALENCIA",
        "code": "TPJ",
        "capacity": 23964,
        "design_speed": 22.0,
        "fuel_consumption": 300.0,
        "op_cost": 20000,
        "charter_cost": 40000,
    },
    {
        "id": "s008",
        "service": "AEU1",
        "name": "OOCL FINLAND",
        "code": "MSX",
        "capacity": 21413,
        "design_speed": 22.0,
        "fuel_consumption": 290.0,
        "op_cost": 18000,
        "charter_cost": 35000,
    },
    {
        "id": "s009",
        "service": "AEU1",
        "name": "OOCL TURKIYE",
        "code": "MMY",
        "capacity": 21413,
        "design_speed": 22.0,
        "fuel_consumption": 290.0,
        "op_cost": 18000,
        "charter_cost": 35000,
    },
    {
        "id": "s010",
        "service": "AEU1",
        "name": "OOCL GDYNIA",
        "code": "MHO",
        "capacity": 21413,
        "design_speed": 22.0,
        "fuel_consumption": 290.0,
        "op_cost": 18000,
        "charter_cost": 35000,
    },
    {
        "id": "s011",
        "service": "AEU1",
        "name": "OOCL SWEDEN",
        "code": "MSY",
        "capacity": 21413,
        "design_speed": 22.0,
        "fuel_consumption": 290.0,
        "op_cost": 18000,
        "charter_cost": 35000,
    },
    {
        "id": "s012",
        "service": "AEU1",
        "name": "OOCL ZEEBRUGGE",
        "code": "MHN",
        "capacity": 21413,
        "design_speed": 22.0,
        "fuel_consumption": 290.0,
        "op_cost": 18000,
        "charter_cost": 35000,
    },
    {
        "id": "s013",
        "service": "AEU1",
        "name": "OOCL JAPAN",
        "code": "OJP",
        "capacity": 21413,
        "design_speed": 22.0,
        "fuel_consumption": 290.0,
        "op_cost": 18000,
        "charter_cost": 35000,
    },
    {
        "id": "s014",
        "service": "AEU1",
        "name": "OOCL WISDOM",
        "code": "DIO",
        "capacity": 21413,
        "design_speed": 22.0,
        "fuel_consumption": 290.0,
        "op_cost": 18000,
        "charter_cost": 35000,
    },
    # ── AEU2 (22 ships, CMA CGM / APL operated, ~14000-18000 TEU) ──
    {
        "id": "s015",
        "service": "AEU2",
        "name": "CMA CGM ZHENG HE",
        "code": "Q4X",
        "capacity": 16020,
        "design_speed": 22.0,
        "fuel_consumption": 250.0,
        "op_cost": 15000,
        "charter_cost": 28000,
    },
    {
        "id": "s016",
        "service": "AEU2",
        "name": "CMA CGM ALEXANDER VON HUMBOLDT",
        "code": "QUO",
        "capacity": 16020,
        "design_speed": 22.0,
        "fuel_consumption": 250.0,
        "op_cost": 15000,
        "charter_cost": 28000,
    },
    {
        "id": "s017",
        "service": "AEU2",
        "name": "APL CHANGI",
        "code": "NM7",
        "capacity": 14074,
        "design_speed": 21.0,
        "fuel_consumption": 220.0,
        "op_cost": 12000,
        "charter_cost": 22000,
    },
    {
        "id": "s018",
        "service": "AEU2",
        "name": "CMA CGM KERGUELEN",
        "code": "Q4H",
        "capacity": 17722,
        "design_speed": 22.0,
        "fuel_consumption": 265.0,
        "op_cost": 16000,
        "charter_cost": 30000,
    },
    {
        "id": "s019",
        "service": "AEU2",
        "name": "APL RAFFLES",
        "code": "N13",
        "capacity": 14074,
        "design_speed": 21.0,
        "fuel_consumption": 220.0,
        "op_cost": 12000,
        "charter_cost": 22000,
    },
    {
        "id": "s020",
        "service": "AEU2",
        "name": "CMA CGM GRACE BAY",
        "code": "MVZ",
        "capacity": 17722,
        "design_speed": 22.0,
        "fuel_consumption": 265.0,
        "op_cost": 16000,
        "charter_cost": 30000,
    },
    {
        "id": "s021",
        "service": "AEU2",
        "name": "CMA CGM BOUGAINVILLE",
        "code": "Q9Y",
        "capacity": 18000,
        "design_speed": 22.0,
        "fuel_consumption": 270.0,
        "op_cost": 17000,
        "charter_cost": 32000,
    },
    {
        "id": "s022",
        "service": "AEU2",
        "name": "APL MERLION",
        "code": "NG4",
        "capacity": 14074,
        "design_speed": 21.0,
        "fuel_consumption": 220.0,
        "op_cost": 12000,
        "charter_cost": 22000,
    },
    {
        "id": "s023",
        "service": "AEU2",
        "name": "APL TEMASEK",
        "code": "NN1",
        "capacity": 14074,
        "design_speed": 21.0,
        "fuel_consumption": 220.0,
        "op_cost": 12000,
        "charter_cost": 22000,
    },
    {
        "id": "s024",
        "service": "AEU2",
        "name": "APL VANDA",
        "code": "NG7",
        "capacity": 14074,
        "design_speed": 21.0,
        "fuel_consumption": 220.0,
        "op_cost": 12000,
        "charter_cost": 22000,
    },
    {
        "id": "s025",
        "service": "AEU2",
        "name": "CMA CGM VASCO DE GAMA",
        "code": "Q2X",
        "capacity": 16020,
        "design_speed": 22.0,
        "fuel_consumption": 250.0,
        "op_cost": 15000,
        "charter_cost": 28000,
    },
    {
        "id": "s026",
        "service": "AEU2",
        "name": "CMA CGM GEORG FORSTER",
        "code": "Q5N",
        "capacity": 16000,
        "design_speed": 22.0,
        "fuel_consumption": 250.0,
        "op_cost": 15000,
        "charter_cost": 28000,
    },
    {
        "id": "s027",
        "service": "AEU2",
        "name": "CMA CGM BENJAMIN FRANKLIN",
        "code": "R2M",
        "capacity": 18000,
        "design_speed": 22.0,
        "fuel_consumption": 270.0,
        "op_cost": 17000,
        "charter_cost": 32000,
    },
    {
        "id": "s028",
        "service": "AEU2",
        "name": "APL SINGAPURA",
        "code": "NM4",
        "capacity": 14074,
        "design_speed": 21.0,
        "fuel_consumption": 220.0,
        "op_cost": 12000,
        "charter_cost": 22000,
    },
    {
        "id": "s029",
        "service": "AEU2",
        "name": "APL FULLERTON",
        "code": "NM3",
        "capacity": 14074,
        "design_speed": 21.0,
        "fuel_consumption": 220.0,
        "op_cost": 12000,
        "charter_cost": 22000,
    },
    {
        "id": "s030",
        "service": "AEU2",
        "name": "CMA CGM LOUIS BLERIOT",
        "code": "NEB",
        "capacity": 16022,
        "design_speed": 22.0,
        "fuel_consumption": 250.0,
        "op_cost": 15000,
        "charter_cost": 28000,
    },
    {
        "id": "s031",
        "service": "AEU2",
        "name": "CMA CGM LEO",
        "code": "QZR",
        "capacity": 16020,
        "design_speed": 22.0,
        "fuel_consumption": 250.0,
        "op_cost": 15000,
        "charter_cost": 28000,
    },
    {
        "id": "s032",
        "service": "AEU2",
        "name": "CMA CGM SYMI",
        "code": "M80",
        "capacity": 15000,
        "design_speed": 22.0,
        "fuel_consumption": 240.0,
        "op_cost": 14000,
        "charter_cost": 26000,
    },
    {
        "id": "s033",
        "service": "AEU2",
        "name": "APL LION CITY",
        "code": "NM5",
        "capacity": 14074,
        "design_speed": 21.0,
        "fuel_consumption": 220.0,
        "op_cost": 12000,
        "charter_cost": 22000,
    },
    {
        "id": "s034",
        "service": "AEU2",
        "name": "CMA CGM JEAN MERMOZ",
        "code": "NAV",
        "capacity": 16022,
        "design_speed": 22.0,
        "fuel_consumption": 250.0,
        "op_cost": 15000,
        "charter_cost": 28000,
    },
    {
        "id": "s035",
        "service": "AEU2",
        "name": "CMA CGM LA SCALA",
        "code": "Q3K",
        "capacity": 16022,
        "design_speed": 22.0,
        "fuel_consumption": 250.0,
        "op_cost": 15000,
        "charter_cost": 28000,
    },
    {
        "id": "s036",
        "service": "AEU2",
        "name": "CMA CGM MONTMARTRE",
        "code": "NZL",
        "capacity": 16022,
        "design_speed": 22.0,
        "fuel_consumption": 250.0,
        "op_cost": 15000,
        "charter_cost": 28000,
    },
    {
        "id": "s037",
        "service": "AEU2",
        "name": "CMA CGM CHAMPS ELYSEES",
        "code": "NWD",
        "capacity": 16022,
        "design_speed": 22.0,
        "fuel_consumption": 250.0,
        "op_cost": 15000,
        "charter_cost": 28000,
    },
    # ── AEU3 (17 ships, COSCO / OOCL operated, ~19000-24000 TEU) ──
    {
        "id": "s038",
        "service": "AEU3",
        "name": "COSCO SHIPPING CAPRICORN",
        "code": "CNG",
        "capacity": 20119,
        "design_speed": 23.0,
        "fuel_consumption": 290.0,
        "op_cost": 17000,
        "charter_cost": 32000,
    },
    {
        "id": "s039",
        "service": "AEU3",
        "name": "COSCO SHIPPING VIRGO",
        "code": "CSD",
        "capacity": 19273,
        "design_speed": 23.0,
        "fuel_consumption": 285.0,
        "op_cost": 16500,
        "charter_cost": 30000,
    },
    {
        "id": "s040",
        "service": "AEU3",
        "name": "COSCO SHIPPING GALAXY",
        "code": "CSH",
        "capacity": 20119,
        "design_speed": 23.0,
        "fuel_consumption": 290.0,
        "op_cost": 17000,
        "charter_cost": 32000,
    },
    {
        "id": "s041",
        "service": "AEU3",
        "name": "COSCO SHIPPING LIBRA",
        "code": "CSB",
        "capacity": 19273,
        "design_speed": 23.0,
        "fuel_consumption": 285.0,
        "op_cost": 16500,
        "charter_cost": 30000,
    },
    {
        "id": "s042",
        "service": "AEU3",
        "name": "COSCO SHIPPING SOLAR",
        "code": "CSI",
        "capacity": 20119,
        "design_speed": 23.0,
        "fuel_consumption": 290.0,
        "op_cost": 17000,
        "charter_cost": 32000,
    },
    {
        "id": "s043",
        "service": "AEU3",
        "name": "COSCO SHIPPING UNIVERSE",
        "code": "CSF",
        "capacity": 20119,
        "design_speed": 23.0,
        "fuel_consumption": 290.0,
        "op_cost": 17000,
        "charter_cost": 32000,
    },
    {
        "id": "s044",
        "service": "AEU3",
        "name": "COSCO SHIPPING ARIES",
        "code": "CNE",
        "capacity": 19273,
        "design_speed": 23.0,
        "fuel_consumption": 285.0,
        "op_cost": 16500,
        "charter_cost": 30000,
    },
    {
        "id": "s045",
        "service": "AEU3",
        "name": "COSCO SHIPPING STAR",
        "code": "CSJ",
        "capacity": 20119,
        "design_speed": 23.0,
        "fuel_consumption": 290.0,
        "op_cost": 17000,
        "charter_cost": 32000,
    },
    {
        "id": "s046",
        "service": "AEU3",
        "name": "COSCO SHIPPING LEO",
        "code": "CNF",
        "capacity": 19273,
        "design_speed": 23.0,
        "fuel_consumption": 285.0,
        "op_cost": 16500,
        "charter_cost": 30000,
    },
    {
        "id": "s047",
        "service": "AEU3",
        "name": "COSCO SHIPPING GEMINI",
        "code": "CSA",
        "capacity": 20119,
        "design_speed": 23.0,
        "fuel_consumption": 290.0,
        "op_cost": 17000,
        "charter_cost": 32000,
    },
    {
        "id": "s048",
        "service": "AEU3",
        "name": "COSCO SHIPPING SAGITTARIUS",
        "code": "CSE",
        "capacity": 20119,
        "design_speed": 23.0,
        "fuel_consumption": 290.0,
        "op_cost": 17000,
        "charter_cost": 32000,
    },
    {
        "id": "s049",
        "service": "AEU3",
        "name": "OOCL PORTUGAL",
        "code": "MTA",
        "capacity": 21413,
        "design_speed": 22.0,
        "fuel_consumption": 290.0,
        "op_cost": 18000,
        "charter_cost": 35000,
    },
    {
        "id": "s050",
        "service": "AEU3",
        "name": "CSCL ATLANTIC OCEAN",
        "code": "QIP",
        "capacity": 19100,
        "design_speed": 23.0,
        "fuel_consumption": 285.0,
        "op_cost": 16000,
        "charter_cost": 29000,
    },
    {
        "id": "s051",
        "service": "AEU3",
        "name": "OOCL DENMARK",
        "code": "MSZ",
        "capacity": 21413,
        "design_speed": 22.0,
        "fuel_consumption": 290.0,
        "op_cost": 18000,
        "charter_cost": 35000,
    },
    {
        "id": "s052",
        "service": "AEU3",
        "name": "OOCL DENMARK",
        "code": "DEN",
        "capacity": 24188,
        "design_speed": 23.0,
        "fuel_consumption": 285.0,
        "op_cost": 21000,
        "charter_cost": 42000,
    },
    {
        "id": "s053",
        "service": "AEU3",
        "name": "OOCL VALENCIA",
        "code": "VLC",
        "capacity": 24188,
        "design_speed": 23.0,
        "fuel_consumption": 285.0,
        "op_cost": 21000,
        "charter_cost": 42000,
    },
    {
        "id": "s054",
        "service": "AEU3",
        "name": "OOCL PORTUGAL",
        "code": "PTG",
        "capacity": 24188,
        "design_speed": 23.0,
        "fuel_consumption": 285.0,
        "op_cost": 21000,
        "charter_cost": 42000,
    },
]

# ── 航线端口轮转 ─────────────────────────────────
AEU_PORT_ROTATIONS: dict[str, list[str]] = {
    # 好望角绕行路线（不经过苏伊士运河）
    # 末尾不再重复起点港口，模运算 (i+1)%len 自然从末尾回到起点
    "AEU1": [
        "CNTAO",
        "CNSHA",
        "CNNGB",
        "CNXMN",
        "CNYTN",
        "SGSIN",
        "GBFXT",
        "BEZEE",
        "PLGDY",
        "DEWVN",
        "SGSIN",
        "CNYTN",
    ],
    "AEU2": [
        "CNNGB",
        "CNSHA",
        "CNYTN",
        "SGSIN",
        "MAPTM",
        "FRDKK",
        "GBSOU",
        "FRLEH",
        "MYPKG",
    ],
    "AEU3": [
        "CNTXG",
        "CNDLC",
        "CNTAO",
        "CNSHA",
        "CNNGB",
        "SGSIN",
        "NLRTM",
        "DEHAM",
        "BEANR",
        "CNSHA",
    ],
}

AEU_SERVICES: dict[str, dict] = {
    "AEU1": {
        "name": "亚欧快航一线",
        "operator": "OOCL / COSCO",
        "description": "青岛→上海→宁波→厦门→盐田→新加坡→(好望角)→费利克斯托→泽布吕赫→格但斯克→威廉港(回程)",
        "vessel_count": 14,
        "cycle_days": 84,
    },
    "AEU2": {
        "name": "亚欧快航二线",
        "operator": "CMA CGM / APL",
        "description": "宁波→上海→盐田→新加坡→(好望角)→丹吉尔→敦刻尔克→南安普顿→勒阿弗尔→巴生港(回程)",
        "vessel_count": 23,
        "cycle_days": 91,
    },
    "AEU3": {
        "name": "亚欧快航三线",
        "operator": "COSCO SHIPPING",
        "description": "天津→大连→青岛→上海→宁波→新加坡→(好望角)→鹿特丹→汉堡→安特卫普(回程)",
        "vessel_count": 17,
        "cycle_days": 84,
    },
}

AEU_SERVICES: dict[str, dict] = {
    "AEU1": {
        "name": "亚欧快航一线",
        "operator": "OOCL / COSCO",
        "description": "青岛→上海→宁波→厦门→盐田→新加坡→苏伊士→费利克斯托→泽布吕赫→格但斯克→威廉港(回程)",
        "vessel_count": 14,
        "cycle_days": 77,
    },
    "AEU2": {
        "name": "亚欧快航二线",
        "operator": "CMA CGM / APL",
        "description": "宁波→上海→盐田→新加坡→丹吉尔→勒阿弗尔→汉堡→鹿特丹→阿尔赫西拉斯→巴生港(回程)",
        "vessel_count": 23,
        "cycle_days": 84,
    },
    "AEU3": {
        "name": "亚欧快航三线",
        "operator": "COSCO SHIPPING",
        "description": "天津→大连→青岛→上海→宁波→新加坡→鹿特丹→汉堡→安特卫普(回程)",
        "vessel_count": 17,
        "cycle_days": 77,
    },
}

# ── 货运需求 ─────────────────────────────────────
AEU_DEMANDS: list[dict] = [
    {"origin": "CNDLC", "dest": "DEHAM", "teu": 465},
    {"origin": "CNNGB", "dest": "GBFXT", "teu": 1357},
    {"origin": "CNNGB", "dest": "DEHAM", "teu": 1163},
    {"origin": "CNNGB", "dest": "FRLEH", "teu": 1473},
    {"origin": "CNNGB", "dest": "NLRTM", "teu": 1404},
    {"origin": "CNSHA", "dest": "BEANR", "teu": 1240},
    {"origin": "CNSHA", "dest": "FRDKK", "teu": 853},
    {"origin": "CNSHA", "dest": "GBFXT", "teu": 1550},
    {"origin": "CNSHA", "dest": "PLGDY", "teu": 775},
    {"origin": "CNSHA", "dest": "DEHAM", "teu": 1629},
    {"origin": "CNSHA", "dest": "FRLEH", "teu": 1744},
    {"origin": "CNSHA", "dest": "NLRTM", "teu": 1938},
    {"origin": "CNSHA", "dest": "GBSOU", "teu": 698},
    {"origin": "CNSHA", "dest": "MAPTM", "teu": 775},
    {"origin": "CNSHA", "dest": "DEWVN", "teu": 698},
    {"origin": "CNSHA", "dest": "BEZEE", "teu": 969},
    {"origin": "CNTAO", "dest": "GBFXT", "teu": 581},
    {"origin": "CNTXG", "dest": "NLRTM", "teu": 581},
    {"origin": "CNYTN", "dest": "GBFXT", "teu": 1085},
    {"origin": "CNYTN", "dest": "FRLEH", "teu": 1008},
]


# ── 辅助函数 ─────────────────────────────────────


def get_service_ships(service_id: str) -> list[dict]:
    """获取指定航线的所有船舶。"""
    return [v for v in AEU_VESSELS if v["service"] == service_id]


def get_service_ports(service_id: str) -> list[str]:
    """获取指定航线的所有港口代码（去重保留顺序）。"""
    seen = set()
    result = []
    for port in AEU_PORT_ROTATIONS.get(service_id, []):
        if port not in seen:
            seen.add(port)
            result.append(port)
    return result


def get_port_display_name(port_code: str) -> str:
    """获取港口中文显示名。"""
    return PORT_CODES_TO_NAMES.get(port_code, port_code)


def get_port_coords(port_code: str) -> tuple[float, float]:
    """获取港口坐标。"""
    return AEU_PORT_COORDS.get(port_code, (0.0, 0.0))


def get_port_infra(port_code: str) -> tuple[int, int, int]:
    """获取港口基础设施信息 (berth_count, crane_count, handling_rate)。"""
    return PORT_INFRA.get(port_code, (3, 6, 100))


ALL_PORTS: list[str] = list(
    dict.fromkeys(port for rotation in AEU_PORT_ROTATIONS.values() for port in rotation)
)
"""所有航线涉及的全部港口代码（去重）。"""
