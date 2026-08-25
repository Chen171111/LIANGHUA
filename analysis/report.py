"""生成回测报告：JSON 数据 + 自包含 HTML Dashboard（ECharts，CDN 引入）。"""
import json
from pathlib import Path

from ..backtest.performance import compute_metrics

_ECHARTS = "https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"

# 备注：模板不使用 str.format，而用令牌替换，从而允许 JS 中出现裸花括号
_PAGE = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__ · AI 量化研投平台</title>
<script src="__ECHARTS__"></script>
<style>
body{font-family:Segoe UI,PingFang SC,Microsoft YaHei,sans-serif;margin:0;background:#f5f7fb;color:#333}
header{padding:16px 24px;background:#2b3a67;color:#fff}
header h1{margin:0;font-size:20px} header p{margin:4px 0 0;font-size:13px;opacity:.85}
.wrap{max-width:1200px;margin:0 auto;padding:16px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}
.card{background:#fff;border-radius:10px;padding:14px 16px;box-shadow:0 1px 4px rgba(0,0,0,.08)}
.card .k{font-size:12px;color:#888} .card .v{font-size:22px;font-weight:600;color:#2b3a67}
.card .v.dn{color:#d1381f} .card .v.up{color:#1ea672}
.chart{background:#fff;border-radius:10px;margin-top:16px;padding:12px;box-shadow:0 1px 4px rgba(0,0,0,.08)}
.chart h3{margin:4px 8px;font-size:14px;color:#444}
.chart .box{height:320px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:800px){.grid2{grid-template-columns:1fr}}
#metrics_box{margin-bottom:24px}
table{width:100%;border-collapse:collapse;background:#fff}
th,td{padding:8px 10px;border-bottom:1px solid #eee;font-size:13px;text-align:right}
th{background:#2b3a67;color:#fff}
</style>
</head>
<body>
<header>
  <h1>__TITLE__</h1>
  <p>__SUBTITLE__</p>
</header>
<div class="wrap">
  <div class="cards" id="cards"></div>
  <div class="grid2">
    <div class="chart"><h3>净值曲线（策略 vs 基准）</h3><div class="box" id="c_eq"></div></div>
    <div class="chart"><h3>回撤曲线</h3><div class="box" id="c_dd"></div></div>
  </div>
  <div class="grid2">
    <div class="chart"><h3>年度收益</h3><div class="box" id="c_year"></div></div>
    <div class="chart"><h3>持仓构成（近20个调仓日）</h3><div class="box" id="c_hold"></div></div>
  </div>
  <div class="chart" id="metrics_box"><h3>绩效指标</h3><div id="metrics_table"></div></div>
</div>
<script>
const DATA = __DATAJSON__;
function render(){
  const d=DATA, ec=echarts, pos=arr=>arr.map((v,i)=>[d.dates[i],v]);
  const cm=d.metrics||{}, cards=document.getElementById('cards');
  let html='';
  const order=[['累计收益','%'],['年化收益','%'],['夏普比率',''],['最大回撤','%'],['年化波动率','%'],['Calmar','']];
  order.forEach(function(kv){
    const k=kv[0],fmt=kv[1]; let v=cm[k]; if(v===undefined) return;
    const s=(v*((fmt==='%')?100:1)).toFixed(3)+(fmt==='%'?'%':'');
    const cls=v<0?'dn':'up';
    html+='<div class="card"><div class="k">'+k+'</div><div class="v '+cls+'">'+s+'</div></div>';
  });
  cards.innerHTML=html;
  ec.init(document.getElementById('c_eq')).setOption({
    tooltip:{trigger:'axis'},legend:{data:['策略','基准']},grid:{left:50,right:16,top:30,bottom:30},
    xAxis:{type:'category',data:d.dates},yAxis:{type:'value',scale:true},
    series:[
      {name:'策略',type:'line',showSymbol:false,data:pos(d.equity),lineStyle:{color:'#2b3a67',width:2}},
      {name:'基准',type:'line',showSymbol:false,data:d.benchmark?pos(d.benchmark):[],lineStyle:{color:'#1ea672',width:1.5,type:'dashed'}}
    ]});
  const eq=d.equity; let peak=eq[0]; const dd=eq.map(function(v){peak=Math.max(peak,v);return (v/peak-1)*100;});
  ec.init(document.getElementById('c_dd')).setOption({
    grid:{left:50,right:16,top:30,bottom:30},
    xAxis:{type:'category',data:d.dates},yAxis:{type:'value',value:0},
    series:[{type:'line',showSymbol:false,data:pos(dd),areaStyle:{color:'rgba(209,56,31,.25)'},lineStyle:{color:'#d1381f',width:1.5}}]});
  const years={};
  for(let i=0;i<d.dates.length;i++){
    const yy=d.dates[i].slice(0,4); years[yy]=(years[yy]||1)*(1+(d.rate[i]||0));
  }
  const yr=Object.entries(years).map(function(e){return [e[0],(e[1]-1)*100];});
  ec.init(document.getElementById('c_year')).setOption({
    grid:{left:50,right:16,top:30,bottom:30},
    xAxis:{type:'category',data:yr.map(function(x){return x[0];})},yAxis:{type:'value',value:0},
    series:[{type:'bar',data:yr.map(function(x){return Math.round(x[1]*100)/100;}),
      itemStyle:{color:function(p){return p.value>=0?'#d1381f':'#1ea672';}}}]});
  const hd=d.holdings.slice(-20).reverse();
  const codes=[];
  hd.forEach(function(h){h.codes.forEach(function(c){if(codes.indexOf(c)<0) codes.push(c);});});
  const top=codes.slice(0,8);
  const hdata=hd.map(function(h){return top.map(function(c){return h.codes.indexOf(c)>=0?1:0;});});
  ec.init(document.getElementById('c_hold')).setOption({
    grid:{left:80,right:16,top:20,bottom:60},tooltip:{},
    xAxis:{type:'category',data:hd.map(function(h){return h.date;}),axisLabel:{interval:1,rotate:45}},
    yAxis:{type:'category',data:top},visualMap:{min:0,max:1,show:false},
    series:[{type:'heatmap',data:hd.map(function(h,i){return top.map(function(c,j){return [i,j,hdata[i][j]];});}).flat()}]});
  let th='<tr><th>指标</th>';
  Object.keys(cm).forEach(function(k){th+='<th>'+k+'</th>';}); th+='</tr>';
  let tr='<tr><td>策略</td>';
  Object.values(cm).forEach(function(v){tr+='<td>'+(typeof v==='number'?Math.round(v*10000)/10000:v)+'</td>';}); tr+='</tr>';
  document.getElementById('metrics_table').innerHTML='<table>'+th+tr+'</table>';
}
render();
</script>
</body>
</html>"""


def render_dashboard(result, metrics, title="回测报告", subtitle="") -> str:
    """将回测结果渲染为 HTML 字符串。"""
    result_dict = result.to_dict()
    metric_row = {}
    if metrics is not None and "策略" in metrics.columns:
        metric_row = metrics["策略"].to_dict()
    elif metrics is not None and len(metrics.columns):
        metric_row = metrics.iloc[:, 0].to_dict()
    result_dict["metrics"] = metric_row
    data_json = json.dumps(result_dict, ensure_ascii=False)
    return (_PAGE
            .replace("__TITLE__", title)
            .replace("__SUBTITLE__", subtitle)
            .replace("__ECHARTS__", _ECHARTS)
            .replace("__DATAJSON__", data_json))


def run_report(result, benchmark_nav=None, title="回测报告", subtitle="") -> dict:
    """构建策略与基准净值表 + 绩效指标。"""
    eq = result.equity[["equity"]].copy()
    eq.columns = ["策略"]
    if benchmark_nav is not None:
        eq["基准"] = benchmark_nav.values
    metrics = compute_metrics(eq)
    return {"metrics": metrics, "equity": eq}


def save_report(result, metrics, path: Path, title="回测报告", subtitle="") -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    html = render_dashboard(result, metrics, title=title, subtitle=subtitle)
    path.write_text(html, encoding="utf-8")
    return path