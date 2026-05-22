"""
离线稳态仿真 — FCFS vs Gurobi 对比 (无 matplotlib 版本)
========================================================
输出 CSV 表格供 Excel / Python 画图使用。
"""

import json, os, sys, csv
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")

ROUTE_SCHEDULES = {
    "AEU1": [
        {"port": "CNTAO", "eta": 0, "etd": 24},
        {"port": "CNSHA", "eta": 72, "etd": 96},
        {"port": "CNNGB", "eta": 120, "etd": 144},
        {"port": "CNXMN", "eta": 192, "etd": 216},
        {"port": "CNYTN", "eta": 240, "etd": 264},
        {"port": "SGSIN", "eta": 336, "etd": 360},
        {"port": "GBFXT", "eta": 1080, "etd": 1104},
        {"port": "BEZEE", "eta": 1152, "etd": 1176},
        {"port": "PLGDY", "eta": 1248, "etd": 1272},
        {"port": "DEWVN", "eta": 1392, "etd": 1416},
        {"port": "SGSIN", "eta": 2280, "etd": 2304},
        {"port": "CNYTN", "eta": 2400, "etd": 2424},
        {"port": "CNTAO", "eta": 2520, "etd": None},
    ],
    "AEU2": [
        {"port": "CNNGB", "eta": 0, "etd": 24},
        {"port": "CNSHA", "eta": 72, "etd": 96},
        {"port": "CNYTN", "eta": 144, "etd": 168},
        {"port": "SGSIN", "eta": 264, "etd": 288},
        {"port": "MAPTM", "eta": 864, "etd": 888},
        {"port": "FRDKK", "eta": 984, "etd": 1008},
        {"port": "GBSOU", "eta": 1056, "etd": 1080},
        {"port": "FRLEH", "eta": 1320, "etd": 1344},
        {"port": "MYPKG", "eta": 2280, "etd": 2304},
        {"port": "CNNGB", "eta": 2520, "etd": None},
    ],
    "AEU3": [
        {"port": "CNTXG", "eta": 0, "etd": 24},
        {"port": "CNDLC", "eta": 72, "etd": 96},
        {"port": "CNTAO", "eta": 120, "etd": 144},
        {"port": "CNSHA", "eta": 192, "etd": 216},
        {"port": "CNNGB", "eta": 240, "etd": 264},
        {"port": "SGSIN", "eta": 384, "etd": 408},
        {"port": "NLRTM", "eta": 1104, "etd": 1128},
        {"port": "DEHAM", "eta": 1200, "etd": 1224},
        {"port": "BEANR", "eta": 1296, "etd": 1320},
        {"port": "CNSHA", "eta": 2280, "etd": 2304},
        {"port": "CNTXG", "eta": 2352, "etd": None},
    ],
}

ROUTE_CAPS = {"AEU1": 21413, "AEU2": 16000, "AEU3": 19100}
ROUTE_CYCLE_WEEKS = {"AEU1": 15, "AEU2": 15, "AEU3": 14}
ROUTE_HOURS = {"AEU1": 2520, "AEU2": 2520, "AEU3": 2352}

ORDERS_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "..",
    "frontend",
    "public",
    "week1_orders.json",
)
OUT_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "frontend", "public"
)

orders = json.load(open(ORDERS_PATH, encoding="utf-8"))
TOTAL_HOURS = 15120


# ─── FCFS Simulation ──────────────────────────────────────────────
def init_buffer(os_, route_id, cw):
    buf = {}
    for o in os_:
        if o["routeID"] != route_id or o["week"] != cw:
            continue
        k = o["originPort"]
        if k not in buf:
            buf[k] = []
        buf[k].append(
            {
                "orderID": o["orderID"],
                "originPort": o["originPort"],
                "destPort": o["destPort"],
                "revenuePerTEU": o["revenuePerTEU"],
                "volumeTEU": o["volumeTEU"],
                "deadline": o["deadline"],
                "remainingTEU": o["volumeTEU"],
            }
        )
    return buf


def simulate_fcfs(os_, total_h):
    results = {}
    for rid, schedule in ROUTE_SCHEDULES.items():
        cap = ROUTE_CAPS[rid]
        ch = ROUTE_HOURS[rid]
        ns = ROUTE_CYCLE_WEEKS[rid]

        loads = {i: 0.0 for i in range(ns)}
        revs = {i: 0.0 for i in range(ns)}
        picked = {i: {} for i in range(ns)}
        deliveries = {i: 0 for i in range(ns)}
        delays = {i: 0 for i in range(ns)}

        buffers = {}
        events = []
        for si in range(ns):
            off = si * 168
            for cyc in range(max(1, (total_h - off) // ch + 1)):
                for p in schedule:
                    t = off + cyc * ch + p["eta"]
                    if t > total_h:
                        continue
                    events.append(
                        {"time": t, "ship": si, "port": p["port"], "offset": off}
                    )
        events.sort(key=lambda e: e["time"])

        for ev in events:
            t, si, port, off = ev["time"], ev["ship"], ev["port"], ev["offset"]
            cw = (int(t // 168) % ROUTE_CYCLE_WEEKS[rid]) + 1
            if cw not in buffers:
                buffers[cw] = init_buffer(os_, rid, cw)

            buf = buffers[cw]
            items = buf.get(port, [])
            cur = loads[si]

            for bi in items:
                if bi["remainingTEU"] <= 0:
                    continue
                rem = cap - cur
                if rem <= 0:
                    break
                take = min(bi["remainingTEU"], rem)
                bi["remainingTEU"] -= take
                cur += take
                oid = bi["orderID"]
                if oid not in picked[si]:
                    picked[si][oid] = {
                        "vol": 0,
                        "revPerTEU": bi["revenuePerTEU"],
                        "pick": t,
                        "dl": bi["deadline"],
                        "dest": bi["destPort"],
                    }
                picked[si][oid]["vol"] += take
            loads[si] = cur

            done = [
                oid
                for oid, info in picked[si].items()
                if info["dest"] == port and info["vol"] > 0
            ]
            for oid in done:
                info = picked[si][oid]
                rev = info["vol"] * info["revPerTEU"]
                revs[si] += rev
                cur -= info["vol"]
                deliveries[si] += 1
                if t > info["pick"] + info["dl"]:
                    delays[si] += 1
                info["vol"] = 0
            loads[si] = cur

        total_rev = sum(revs.values())
        total_del = sum(deliveries.values())
        total_delay = sum(delays.values())

        weekly_revs = []
        for w in range(1, ROUTE_CYCLE_WEEKS[rid] + 1):
            wr = 0
            for si in range(w, ns + 1):
                frac = min(1.0, max(0.0, (TOTAL_HOURS - si * 168) / (ROUTE_HOURS[rid])))
                wr += revs.get(si - 1, 0) * frac
            weekly_revs.append((w, wr))

        results[rid] = {
            "revenue": total_rev,
            "deliveries": total_del,
            "delays": total_delay,
            "delay_rate": total_delay / total_del * 100 if total_del else 0,
            "weekly_revenues": weekly_revs,
            "per_ship_rev": [revs[i] for i in range(ns)],
        }

    return results


print(f"=== FCFS Simulation ({TOTAL_HOURS}h) ===")
fcfs = simulate_fcfs(orders, TOTAL_HOURS)
fcfs_total = 0
for rid in ["AEU1", "AEU2", "AEU3"]:
    r = fcfs[rid]
    fcfs_total += r["revenue"]
    avg_per_wk = r["revenue"] / ROUTE_CYCLE_WEEKS[rid]
    print(
        f"  {rid}: \${r['revenue']:>15,.0f}  avg/wk \${avg_per_wk:>12,.0f}  "
        f"delays={r['delays']}/{r['deliveries']} ({r['delay_rate']:.1f}%)"
    )
print(f"  TOTAL: \${fcfs_total:>15,.0f}")

# ─── Theoretical max ──────────────────────────────────────────────
theo_max = sum(o["volumeTEU"] * o["revenuePerTEU"] for o in orders)
print(f"\n  Theory max: \${theo_max:>13,.0f} (if unlimited capacity)")
print(
    f"  FCFS loss:  \${theo_max - fcfs_total:>13,.0f} ({(theo_max - fcfs_total) / theo_max * 100:.1f}%)"
)

# ─── Save per-route weekly CSV ─────────────────────────────────────
csv_path = os.path.join(OUT_DIR, "fcfs_weekly_revenue.csv")
with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["Week", "AEU1_Revenue", "AEU2_Revenue", "AEU3_Revenue", "Total"])
    max_w = max(ROUTE_CYCLE_WEEKS.values())
    for wk in range(1, max_w + 1):
        a1 = next((wr for ww, wr in fcfs["AEU1"]["weekly_revenues"] if ww == wk), 0)
        a2 = next((wr for ww, wr in fcfs["AEU2"]["weekly_revenues"] if ww == wk), 0)
        a3 = next((wr for ww, wr in fcfs["AEU3"]["weekly_revenues"] if ww == wk), 0)
        w.writerow(
            [wk, round(a1, 0), round(a2, 0), round(a3, 0), round(a1 + a2 + a3, 0)]
        )
print(f"\nWeekly revenue CSV: {csv_path}")

# ─── Save summary JSON ────────────────────────────────────────────
summary = {
    "fcfs_total": fcfs_total,
    "theory_max": theo_max,
    "fcfs_loss": theo_max - fcfs_total,
    "fcfs_loss_pct": round((theo_max - fcfs_total) / theo_max * 100, 1),
    "routes": {
        rid: {"revenue": fcfs[rid]["revenue"], "delay_rate": fcfs[rid]["delay_rate"]}
        for rid in ["AEU1", "AEU2", "AEU3"]
    },
    "note": "Gurobi rolling mode requires live backend with gurobipy. Install gurobipy + matplotlib to run full comparison.",
}
json_path = os.path.join(OUT_DIR, "steady_state_fcfs.json")
json.dump(summary, open(json_path, "w", encoding="utf-8"), indent=2)
print(f"Summary JSON: {json_path}")
print("Done.")
