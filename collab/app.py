"""DrugMind 药物研发协作平台 — 按席位付费"""
from flask import Flask, render_template_string, render_template, jsonify, request
import json, os, time
from datetime import datetime

app = Flask(__name__, template_folder="templates")
DB_FILE = os.path.join(os.path.dirname(__file__), "teams.json")

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE) as f: return json.load(f)
    return {"teams": {}, "revenue": 0}

def save_db(db):
    with open(DB_FILE, "w") as f: json.dump(db, f, ensure_ascii=False, indent=2)

@app.before_request
def ensure_db():
    if not hasattr(app, '_db'): app._db = load_db()
def get_db(): return app._db
def commit(): save_db(app._db)

PLANS = {
    "starter": {"name": "起步版", "price": 300, "seats": 5, "features": ["靶点知识图谱", "文献自动聚合", "基础协作空间"]},
    "team": {"name": "团队版", "price": 500, "seats": -1, "features": ["全部起步版功能", "数字孪生模拟", "管线进度追踪", "AI决策建议", "外部数据对接"], "popular": True},
    "enterprise": {"name": "企业版", "price": 800, "seats": -1, "features": ["全部团队版功能", "私有化部署", "SSO集成", "专属客户成功经理", "定制化开发"]},
}

PIPELINE_STAGES = [
    {"stage": "靶点发现", "icon": "🎯", "tools": ["知识图谱查询", "文献自动挖掘", "OMIM/OpenTargets对接"], "collab": "靶点评审会"},
    {"stage": "先导发现", "icon": "💊", "tools": ["虚拟筛选", "分子生成", "ADMET预测"], "collab": "分子评审"},
    {"stage": "临床前", "icon": "🔬", "tools": ["毒理预测", "药代动力学", "动物模型推荐"], "collab": "IND准备"},
    {"stage": "临床试验", "icon": "🏥", "tools": ["试验设计AI", "患者招募", "数据分析"], "collab": "临床运营"},
    {"stage": "上市后", "icon": "📊", "tools": ["RWD分析", "不良反应监测", "竞品追踪"], "collab": "上市后管理"},
]

DIFFERENTIATION = """
<div class="section">
  <h2>⚔️ DrugMind vs MediPharma：差异化定位</h2>
  <table>
    <tr><th></th><th>MediPharma</th><th>DrugMind</th></tr>
    <tr><td>核心价值</td><td>卖候选化合物</td><td>卖研发协作效率</td></tr>
    <tr><td>付费模式</td><td>API按次付费</td><td>按席位订阅</td></tr>
    <tr><td>客户</td><td>单个研究者</td><td>研发团队/部门</td></tr>
    <tr><td>使用场景</td><td>"帮我发现一个靶点"</td><td>"帮我们团队管理整个管线"</td></tr>
    <tr><td>协同关系</td><td colspan="2">MediPharma的API可以嵌入DrugMind使用</td></tr>
  </table>
</div>
"""

@app.route("/")
def index():
    return render_template_string("""<!DOCTYPE html>
<html lang="zh-CN"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>DrugMind — 药物研发协作平台</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}body{font-family:-apple-system,sans-serif;background:#f5f7fa;color:#333;max-width:800px;margin:0 auto;padding:20px}
.hdr{background:linear-gradient(135deg,#00695c,#004d40);color:#fff;padding:24px;border-radius:14px;text-align:center;margin-bottom:20px}
.hdr h1{font-size:22px}.hdr p{font-size:13px;opacity:.8;margin-top:6px}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:20px}
@media(max-width:600px){.grid{grid-template-columns:1fr}}
.card{background:#fff;border-radius:12px;padding:20px;box-shadow:0 2px 8px rgba(0,0,0,.05);text-align:center}
.card.popular{border:2px solid #00695c;position:relative}
.card.popular::before{content:'推荐';position:absolute;top:-10px;right:16px;background:#00695c;color:#fff;font-size:11px;padding:2px 10px;border-radius:8px}
.card h3{font-size:16px;margin-bottom:6px}
.card .price{font-size:28px;font-weight:800;color:#00695c}.card .unit{font-size:12px;color:#888}
.card .features{text-align:left;font-size:13px;line-height:2;margin:12px 0}
.card .btn{display:block;width:100%;padding:10px;background:#00695c;color:#fff;border:none;border-radius:8px;cursor:pointer}
.section{background:#fff;border-radius:12px;padding:20px;box-shadow:0 2px 8px rgba(0,0,0,.05);margin-bottom:20px}
.section h2{font-size:15px;margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid #eee}
table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:8px;font-size:13px;border-bottom:1px solid #f0f0f0}
th{background:#fafafa}
.pipeline{display:flex;overflow-x:auto;gap:10px;padding:10px 0}
.stage{min-width:140px;background:#e0f2f1;border-radius:10px;padding:12px;text-align:center;font-size:12px}
.stage .icon{font-size:24px;margin-bottom:4px}.stage .name{font-weight:700;margin-bottom:4px}
input,select{width:100%;padding:8px;border:1px solid #ddd;border-radius:8px;margin:4px 0 8px}
.btn-main{padding:10px 20px;background:#00695c;color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:14px}
.tag{display:inline-block;padding:3px 10px;border-radius:10px;font-size:11px;background:#e0f2f1;color:#00695c}
</style></head><body>
<div class="hdr">
  <h1>🔬 DrugMind</h1>
  <p>药物研发数字孪生协作平台 · 按席位订阅 · 团队效率倍增器</p>
  <nav style="margin-top:10px;display:flex;gap:8px;justify-content:center"><a href="/" style="color:rgba(255,255,255,.85);text-decoration:none;font-size:12px;padding:4px 10px;border-radius:6px;background:rgba(255,255,255,.15)">📊 定价</a><a href="/workspace" style="color:rgba(255,255,255,.85);text-decoration:none;font-size:12px;padding:4px 10px;border-radius:6px;background:rgba(255,255,255,.15)">🔬 工作区体验</a></nav>
</div>

<div class="section">
  <h2>🔄 全管线协作覆盖</h2>
  <div class="pipeline">
  {% for s in stages %}
  <div class="stage"><div class="icon">{{ s.icon }}</div><div class="name">{{ s.stage }}</div><div>{{ s.collab }}</div></div>
  {% endfor %}
  </div>
</div>

<div class="grid">
{% for k,v in plans.items() %}
<div class="card {{ 'popular' if v.get('popular') else '' }}">
  <h3>{{ v.name }}</h3>
  <div><span class="price">¥{{ v.price }}</span><span class="unit">/人/月</span></div>
  <div class="features">
    {% for f in v.features %}✓ {{ f }}<br>{% endfor %}
    {% if v.seats > 0 %}最多{{ v.seats }}人{% else %}不限人数{% endif %}
  </div>
  <button class="btn" onclick="apply('{{ k }}')">选择方案</button>
</div>
{% endfor %}
</div>

{{ diff }}

<div class="section">
  <h2>💰 ROI计算器（20人研发团队）</h2>
  <div style="font-size:13px;line-height:2">
    团队年费：20人 × ¥500/人/月 × 12 = <strong>¥120,000</strong><br>
    文献调研时间节省：每人每月8小时 × ¥200/时 × 20人 × 12月 = <strong>¥384,000</strong><br>
    决策失误减少：每个错误决策成本¥50万 × 减少20% = <strong>¥100,000</strong><br>
    管线加速：提前1个月上市 × 日收入¥10万 = <strong>¥3,000,000</strong><br>
  </div>
  <div style="text-align:center;margin-top:10px;background:#e0f2f1;padding:12px;border-radius:8px">
    <div style="font-size:12px;color:#888">年净收益（保守估计）</div>
    <div style="font-size:28px;font-weight:800;color:#00695c">¥3,364,000</div>
    <div style="font-size:12px;color:#888">ROI 28倍</div>
  </div>
</div>

<div class="section">
  <h2>📋 申请试用</h2>
  <label>公司/团队名称</label>
  <input id="teamName" placeholder="输入团队名称">
  <label>团队规模</label>
  <select id="teamSize"><option value="5">5人以下</option><option value="15">5-20人</option><option value="50">20-50人</option><option value="100">50人以上</option></select>
  <button class="btn-main" onclick="applyTeam()">申请14天免费试用</button>
  <div id="result" style="display:none;margin-top:12px;padding:12px;background:#e0f2f1;border-radius:8px;font-size:13px"></div>
</div>

<script>
function apply(plan){alert('已选择'+plan+'方案')}
async function applyTeam(){
  const name=document.getElementById('teamName').value;
  const size=document.getElementById('teamSize').value;
  if(!name){alert('请输入团队名称');return;}
  const res=await fetch('/api/apply',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,size:parseInt(size)})});
  const data=await res.json();
  document.getElementById('result').style.display='block';
  document.getElementById('result').innerHTML=`✅ 试用申请已提交！<br>团队：${data.name}<br>方案：${data.plan}<br>席位：${data.seats}人<br>14天免费，之后¥${data.monthly_fee}/月`;
}
</script>
</body></html>""", plans=PLANS, stages=PIPELINE_STAGES, diff=DIFFERENTIATION)

@app.route("/api/apply", methods=["POST"])
def api_apply():
    data = request.json
    name = data.get("name", "")
    size = data.get("size", 10)
    plan_key = "starter" if size <= 5 else ("team" if size <= 50 else "enterprise")
    plan = PLANS[plan_key]
    monthly = size * plan["price"]
    db = get_db()
    team_id = f"DM{int(time.time())}"
    db["teams"][team_id] = {"name": name, "plan": plan_key, "seats": size, "monthly_fee": monthly, "created": datetime.now().isoformat()}
    commit()
    return jsonify({"id": team_id, "name": name, "plan": plan["name"], "seats": size, "monthly_fee": monthly, "annual_fee": monthly * 12})

@app.route("/api/plans")
def api_plans(): return jsonify(PLANS)

@app.route("/api/stats")
def api_stats():
    db = get_db()
    return jsonify({"teams": len(db["teams"]), "total_revenue": db.get("revenue", 0)})

@app.route("/workspace")
def workspace():
    return render_template("workspace.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5006, debug=True)
