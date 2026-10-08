/* 力扣刷题看板 · 前端逻辑 */
/* 难度色：柔和系（绿/琥珀/玫红，降饱和以适配冷色主题） */
const DIFF={easy:'#4ADE80',medium:'#FBBF24',hard:'#FB7185'};
const DIFF_GRAD={
  easy:'linear-gradient(135deg,#86EFAC,#4ADE80)',
  medium:'linear-gradient(135deg,#FDE68A,#FBBF24)',
  hard:'linear-gradient(135deg,#FDA4AF,#FB7185)'
};
const LBL={easy:'简单',medium:'中等',hard:'困难'};
const WD=['周日','周一','周二','周三','周四','周五','周六'];
const CHECK='<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="3.6" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>';
/* 换题：循环箭头 */
const ICO_SWAP='<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 9h11l-3-3"/><path d="M20 15H9l3 3"/></svg>';
/* 之前做过：书签/对勾标记（用旗子避免与勾选框对号混淆） */
const ICO_PRE='<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 21V4"/><path d="M6 4h11l-2.5 4L17 12H6"/></svg>';
/* 错题本：空心星（未标记）/ 实心星（已标记经典）/ 实心心形（错题） */
const ICO_STAR_O='<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3.2l2.7 5.5 6 .9-4.3 4.2 1 6-5.4-2.8L6.6 19.8l1-6L3.3 9.6l6-.9z"/></svg>';
const ICO_STAR='<svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"><path d="M12 3.2l2.7 5.5 6 .9-4.3 4.2 1 6-5.4-2.8L6.6 19.8l1-6L3.3 9.6l6-.9z"/></svg>';
const ICO_STAR_F='<svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="1.6"><path d="M12 20.7s-7.6-4.6-9.2-9.1c-1-2.8.5-5.7 3.2-6.4 2-.5 4 .3 5 1.7 1-1.4 3-2.2 5-1.7 2.7.7 4.2 3.6 3.2 6.4-1.6 4.5-9.2 9.1-9.2 9.1z"/></svg>';

/* 背景氛围：细雨（慢但看得见）+ 竹叶慢慢打转 */
(function(){
  function petals(){
    var box=document.getElementById('petals');
    if(!box)return;
    var small=window.innerWidth<760;
    var drops=small?45:90;     // 雨丝要密到「一眼看出在下雨」
    var leaves=small?8:16;
    for(var i=0;i<drops;i++){
      var p=document.createElement('i');
      p.style.height=(50+Math.random()*70)+'px';   // 长雨丝，慢落
      p.style.left=(Math.random()*100)+'%';
      p.style.animationDuration=(3.2+Math.random()*3.6)+'s';
      p.style.animationDelay=(-Math.random()*7)+'s';
      p.style.opacity=(0.3+Math.random()*0.25).toFixed(2);
      box.appendChild(p);
    }
    for(var k=0;k<leaves;k++){
      var b=document.createElement('b');
      if(Math.random()<.3)b.className='big';          // 三成大叶，层次更自然
      b.style.left=(4+Math.random()*90)+'%';
      b.style.animationDuration=(13+Math.random()*13)+'s';
      b.style.animationDelay=(-Math.random()*24)+'s';
      b.style.opacity=(0.3+Math.random()*0.28).toFixed(2);
      box.appendChild(b);
    }
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',petals);
  else petals();
})();

function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){
  return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
function toast(m){var t=document.getElementById('toast');t.textContent=m;
  t.classList.add('show');setTimeout(function(){t.classList.remove('show');},2500);}
function fmtDate(s){var p=String(s).split('-');return p[0]+'年'+parseInt(p[1],10)+'月'+parseInt(p[2],10)+'日';}
function wd(s){var p=String(s).split('-');return WD[new Date(p[0],p[1]-1,p[2]).getDay()];}
function md(s){var p=String(s).split('-');return parseInt(p[1],10)+'月'+parseInt(p[2],10)+'日';}

/* ---------- 自定义 tooltip（替代浏览器原生黑框） ----------
   用法：任意元素加 data-tip="内容（可含 <br>）"，鼠标悬停即显示。       */
function tipShow(html,ev){
  var t=document.getElementById('tip');
  if(!t)return;
  t.innerHTML=html;
  t.classList.add('show');
  tipMove(ev);
}
function tipMove(ev){
  var t=document.getElementById('tip');
  if(!t||!t.classList.contains('show'))return;
  var pad=14,w=t.offsetWidth,h=t.offsetHeight;
  var x=(ev.clientX||0)+pad,y=(ev.clientY||0)+pad;
  if(x+w>window.innerWidth-8)x=Math.max(8,(ev.clientX||0)-w-pad);
  if(y+h>window.innerHeight-8)y=Math.max(8,(ev.clientY||0)-h-pad);
  t.style.left=Math.max(8,x)+'px';
  t.style.top=Math.max(8,y)+'px';
}
function tipHide(){var t=document.getElementById('tip');if(t)t.classList.remove('show');}
function initTip(){
  document.addEventListener('mouseover',function(e){
    var el=e.target&&e.target.closest?e.target.closest('[data-tip]'):null;
    if(el)tipShow(el.getAttribute('data-tip'),e);
    else if(!(e.target&&e.target.closest&&e.target.closest('#tip')))tipHide();
  });
  document.addEventListener('mousemove',function(e){
    if(e.target&&e.target.closest&&e.target.closest('[data-tip]'))tipMove(e);
  });
  document.addEventListener('mouseout',function(e){
    var el=e.target&&e.target.closest?e.target.closest('[data-tip]'):null;
    if(el)tipHide();
  });
  window.addEventListener('scroll',function(){tipHide();closeListPop();},true);
  /* 点空白处收起题单小菜单 */
  document.addEventListener('click',function(e){
    var pop=document.getElementById('listPop');
    if(pop&&pop.classList.contains('show')){
      if(!(e.target.closest&&(e.target.closest('#listPop')||e.target.closest('.plist'))))closeListPop();
    }
  });
}

let TODAY='', STATE=null, SEARCH='', MODAL='', WELSTEP=0;

async function post(url,body){
  return (await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify(body||{})})).json();
}

/* ============ 错题本 / 经典题 ============ */
var MARK_FILTER='all';

function markOf(pid){
  var ms=(STATE&&STATE.marks)||[];
  for(var i=0;i<ms.length;i++){ if(ms[i].id===pid) return ms[i]; }
  return null;
}

function markLabel(pid){
  var m=markOf(pid);
  return m?m.kindLabel:'';
}

/* 题板行尾的标记按钮：已标记的显示彩色实心，未标记显示空心 */
function markBtn(pid){
  var m=markOf(pid);
  var cls='icobtn mkbtn'+(m?(m.kind==='wrong'?' on wrong':' on classic'):'');
  var tip=m?('已标记「'+m.kindLabel+'」· 点击取消'):'标记为经典 / 错题';
  return '<button class="'+cls+'" data-mark="'+pid+'" data-tip="'+esc(tip)+'">'+
    (m?(m.kind==='wrong'?ICO_STAR_F:ICO_STAR):ICO_STAR_O)+'</button>';
}

async function toggleMark(pid,kind){
  var r=await post('/api/mark',{id:pid,kind:kind});
  if(r&&r.state){
    STATE=r.state;
    load();
    renderPanelBody();
    toast(kind?('已标记为「'+({classic:'经典',wrong:'错题'})[kind]+'」'):'已取消标记');
  }
}

function renderMarks(s){
  var ms=s.marks||[], st=s.markStats||{};
  if(!ms.length){
    return '<div class="emptyhint" style="padding:26px 4px">'+
      '<div style="font-size:15px;font-weight:800;margin-bottom:8px">错题本还是空的</div>'+
      '<div style="font-size:12.5px;line-height:1.9;color:var(--ink-2)">'+
      '在题板上点每道题行尾的 <b>☆</b> 按钮，就能标记成<br>'+
      '<b>经典</b>（值得回看的好题）或 <b>错题</b>（做错、想再练的）。<br>'+
      '标记过的题会汇总到这里，并统计难度与考点分布。</div></div>';
  }
  var h='';
  h+='<div class="mkstats">'+
     '<div class="mkstat"><div class="v">'+st.total+'</div><div class="k">标记总数</div></div>'+
     '<div class="mkstat w"><div class="v">'+st.wrong+'</div><div class="k">错题</div></div>'+
     '<div class="mkstat c"><div class="v">'+st.classic+'</div><div class="k">经典</div></div>'+
     '<div class="mkstat"><div class="v">'+st.solved+'</div><div class="k">已做出来</div></div>'+
     '</div>';

  var bd=st.byDiff||{};
  h+='<div class="mkbar">'+
     '<span class="lb">难度</span>'+
     '<span class="seg"><i style="background:#5EEAD4"></i>简单 '+bd.easy+'</span>'+
     '<span class="seg"><i style="background:#FBBF6E"></i>中等 '+bd.medium+'</span>'+
     '<span class="seg"><i style="background:#FB8A8A"></i>困难 '+bd.hard+'</span>';
  if((st.topCat||[]).length){
    h+='<span class="lb" style="margin-left:14px">高频考点</span>'+
       st.topCat.slice(0,4).map(function(c){
         return '<span class="seg plain">'+esc(c.name)+' '+c.n+'</span>';}).join('');
  }
  h+='</div>';

  h+='<div class="mktabs">'+
     ['all','wrong','classic'].map(function(k){
       var n=k==='all'?st.total:(k==='wrong'?st.wrong:st.classic);
       return '<button class="mkt'+(MARK_FILTER===k?' on':'')+'" onclick="mkFilter(\''+k+'\')">'+
         ({all:'全部',wrong:'错题',classic:'经典'})[k]+' '+n+'</button>';}).join('')+
     '</div>';

  var list=ms.filter(function(m){
    return MARK_FILTER==='all'||m.kind===MARK_FILTER;});
  if(!list.length){
    h+='<div class="fhelp" style="padding:18px 0">这个分类下还没有题。</div>';
    return h;
  }
  h+='<div class="mklist">'+list.map(function(m){
    var dcls=m.difficulty==='hard'?'d hard':(m.difficulty==='medium'?'d med':'d easy');
    return '<div class="mkitem" data-id="'+m.id+'">'+
      '<span class="mkkind '+(m.kind==='wrong'?'w':'c')+'">'+
        (m.kind==='wrong'?'错题':'经典')+'</span>'+
      '<div class="mkmain">'+
        '<div class="mktitle"><b>#'+m.id+'</b> '+esc(m.name)+
          '<span class="'+dcls+'">'+({easy:'简单',medium:'中等',hard:'困难'})[m.difficulty]+'</span>'+
          (m.category?'<span class="mkcat">'+esc(m.category)+'</span>':'')+
          (m.done?'<span class="mkok">已做出来</span>':'')+
        '</div>'+
        '<input class="mknote" placeholder="加一句备注：卡在哪、下次注意什么" value="'+esc(m.note||'')+'" '+
          'onchange="saveMarkNote('+m.id+',this.value)">'+
      '</div>'+
      '<button class="mkdel" data-tip="取消标记" onclick="toggleMark('+m.id+',\'\')">×</button>'+
    '</div>';}).join('')+'</div>';
  return h;
}

function mkFilter(k){
  MARK_FILTER=k;
  renderPanelBody();
}

/* 题板上点☆：弹一个小选择（经典 / 错题 / 取消） */
var MKPICK=null;
function askMark(pid){
  var m=markOf(pid);
  var cur=m?m.kind:'';
  var tip=document.getElementById('mkpickTip');
  if(tip)tip.textContent='题目 #'+pid;
  var box=document.getElementById('mkpick');
  if(box){
    box.dataset.id=pid;
    box.querySelectorAll('[data-kind]').forEach(function(b){
      b.classList.toggle('on',b.dataset.kind===cur);});
    box.querySelector('[data-kind=""]').style.display=cur?'':'none';
  }
  var m2=document.getElementById('mkpickMask');
  if(m2)m2.classList.add('show');
}
function closeMarkPick(){
  var m=document.getElementById('mkpickMask');
  if(m)m.classList.remove('show');
}

async function saveMarkNote(pid,val){
  var m=markOf(pid); if(!m)return;
  var r=await post('/api/mark',{id:pid,kind:m.kind,note:val});
  if(r&&r.state)STATE=r.state;
  toast('备注已保存');
}

/* 面板内容重绘（错题本在弹窗内切分类/改备注时用） */
function renderPanelBody(){
  if(MODAL!=='marks'||!STATE)return;
  var body=document.getElementById('mBody');
  if(body)body.innerHTML=renderMarks(STATE);
}

/* ---------- 成就殿堂 ---------- */
/* 分类配色：每个分类一套鲜亮渐变（图标方块 + 卡片底色 + 进度条）*/
var ACH_CATS={
  milestone:{name:'里程碑',c1:'#8B7CF6',c2:'#6D5DE8',tint:'#F5F3FF',bd:'#DDD8FF'},
  streak:{name:'坚持',c1:'#5EB8F5',c2:'#3B96E0',tint:'#EFF8FF',bd:'#CFE8FF'},
  burst:{name:'爆发',c1:'#FBBF24',c2:'#F59E0B',tint:'#FFFBEB',bd:'#FDE68A'},
  collect:{name:'收藏',c1:'#FB7185',c2:'#F43F5E',tint:'#FFF1F3',bd:'#FECDD3'},
  plan:{name:'计划',c1:'#5EEAD4',c2:'#2DD4BF',tint:'#F0FDFA',bd:'#A7F3D0'}
};
/* 成就定义（原型版：定义写死在前端，进度从实时 state 算，做到哪个解锁哪个）*/
var ACH=[
  /* 里程碑：累计完成题数 */
  {id:'a1',cat:'milestone',icon:'🌱',name:'初露锋芒',desc:'完成第 1 道题，刷题之旅起步',target:1,unit:'题',
   val:function(s){return s.doneCount||0;}},
  {id:'a2',cat:'milestone',icon:'🌿',name:'小有所成',desc:'累计完成 10 道题',target:10,unit:'题',
   val:function(s){return s.doneCount||0;}},
  {id:'a3',cat:'milestone',icon:'🌳',name:'渐入佳境',desc:'累计完成 25 道题',target:25,unit:'题',
   val:function(s){return s.doneCount||0;}},
  {id:'a4',cat:'milestone',icon:'⛰️',name:'半壁江山',desc:'累计完成 50 道题',target:50,unit:'题',
   val:function(s){return s.doneCount||0;}},
  {id:'a5',cat:'milestone',icon:'🏆',name:'计划通关',desc:'完成本题单计划的全部题目',target:0,unit:'题',
   dyn:function(s){return s.target||100;},
   val:function(s){return s.doneCount||0;}},
  /* 坚持：连续刷题天数 */
  {id:'s3',cat:'streak',icon:'📅',name:'三日连胜',desc:'连续 3 天有做题记录',target:3,unit:'天',
   val:function(s){return (s.stats&&s.stats.streak)||0;}},
  {id:'s7',cat:'streak',icon:'🔥',name:'一周不懈',desc:'连续 7 天有做题记录',target:7,unit:'天',
   val:function(s){return (s.stats&&s.stats.streak)||0;}},
  {id:'s15',cat:'streak',icon:'🌙',name:'半月之约',desc:'连续 15 天有做题记录',target:15,unit:'天',
   val:function(s){return (s.stats&&s.stats.streak)||0;}},
  {id:'s30',cat:'streak',icon:'👑',name:'三十功名',desc:'连续 30 天有做题记录',target:30,unit:'天',
   val:function(s){return (s.stats&&s.stats.streak)||0;}},
  /* 爆发：单日做题量 */
  {id:'b5',cat:'burst',icon:'⚡',name:'小爆发',desc:'单一天完成 5 道题',target:5,unit:'题',
   val:function(s){return maxDaily(s);}},
  {id:'b8',cat:'burst',icon:'💥',name:'大爆发',desc:'单一天完成 8 道题',target:8,unit:'题',
   val:function(s){return maxDaily(s);}},
  {id:'b12',cat:'burst',icon:'🐲',name:'肝帝附体',desc:'单一天完成 12 道题',target:12,unit:'题',
   val:function(s){return maxDaily(s);}},
  /* 爆发·跨计划：所有计划里单日完成最多的一天（记录型成就，progress 位直接摆纪录） */
  {id:'btop',cat:'burst',icon:'🏔️',name:'单日之巅',desc:'所有计划里，单日完成题数最多的一天',target:1,unit:'题',rec:true,
   val:function(s){return (s.recAll&&s.recAll.count)||0;}},
  /* 收藏：错题本标记 */
  {id:'c1',cat:'collect',icon:'⭐',name:'首记经典',desc:'把第 1 道题标记为「经典」',target:1,unit:'道',
   val:function(s){return (s.markStats&&s.markStats.classic)||0;}},
  {id:'w10',cat:'collect',icon:'📕',name:'错题收藏家',desc:'累计标记 10 道错题',target:10,unit:'道',
   val:function(s){return (s.markStats&&s.markStats.wrong)||0;}},
  {id:'c10',cat:'collect',icon:'💎',name:'好题猎人',desc:'累计标记 10 道经典题',target:10,unit:'道',
   val:function(s){return (s.markStats&&s.markStats.classic)||0;}},
  /* 计划：提前 / 补做 / 新一轮 */
  {id:'e3',cat:'plan',icon:'🚀',name:'提前日达人',desc:'累计 3 天做题量超出当日计划（提前刷后面的题）',target:3,unit:'天',
   val:function(s){return earlyDays(s);}},
  {id:'x1',cat:'plan',icon:'🧹',name:'清完补做',desc:'完整清空 1 个补做日',target:1,unit:'个',
   val:function(s){
     return (s.board||[]).filter(function(b){return b.extra&&b.done;}).length;}},
  {id:'r2',cat:'plan',icon:'🔁',name:'第二轮',desc:'完成一轮计划后，开启新一轮刷题',target:2,unit:'轮',
   val:function(s){return s.round||1;}}
];
var ACH_VIEW={cat:'all',open:null};   // open=成就 id 时显示详情

/* 单日最大做题量（只算真正做的新题，和日历一致）*/
function maxDaily(s){
  var d=s.daily||{}, mx=0;
  for(var k in d){if(d[k]>mx)mx=d[k];}
  return mx;
}
/* 本计划单日完成最多的一天（真正做的新题，和日历/热力图同源）。
   并列取更早的一天——纪录属于第一次达成它的那天。 */
function bestDay(s){
  var d=s.daily||{},best=null;
  for(var k in d){
    var n=d[k]||0;
    if(!n)continue;
    if(!best||n>best.count||(n===best.count&&k<best.date)){
      best={date:k,count:n};
    }
  }
  return best;
}
/* 提前日天数：当天做题量 > 当日计划配额 */
function earlyDays(s){
  var d=s.daily||{}, per=s.perDay||4, n=0;
  for(var k in d){if(d[k]>per)n++;}
  return n;
}
/* 计算所有成就的当前进度 */
function achCalc(s){
  return ACH.map(function(a){
    var target=a.dyn?a.dyn(s):a.target;
    var cur=a.val(s)||0;
    var o={def:a,cur:cur,target:target,ok:cur>=target};
    if(a.rec)o.rec=s.recAll||{date:'',count:0,list:''};
    return o;
  });
}
/* 奖杯徽标：已解锁 / 总数 */
function renderTrophy(s){
  var list=achCalc(s), n=0;
  list.forEach(function(x){if(x.ok)n++;});
  var b=document.getElementById('trophyBadge');
  if(b)b.textContent=n+'/'+list.length;
  var t=document.getElementById('trophyBtn');
  if(t)t.classList.toggle('allin',n===list.length&&n>0);
}
/* 点击奖杯：弹跳 + 撒纸屑 + 开弹窗 */
function openTrophy(){
  var btn=document.getElementById('trophyBtn');
  if(btn){
    /* 类名用 tbpop：项目里 .pop 是题单下拉菜单（min-width:158px），
       撞名会把奖杯按钮撑成长椭圆 */
    btn.classList.remove('tbpop');void btn.offsetWidth;btn.classList.add('tbpop');
    trophySparks(btn);
  }
  ACH_VIEW.open=null;
  ACH_VIEW.cat='all';   // 重开重置分类，别留着上次的筛选
  renderAchList();
  document.getElementById('achMask').classList.add('show');
}
function closeTrophy(){
  document.getElementById('achMask').classList.remove('show');
  ACH_VIEW.open=null;
}
/* 纸屑：从奖杯中心向外撒一把，0.9s 后清掉 */
function trophySparks(btn){
  var box=document.createElement('div');box.className='tsparks';
  var r=btn.getBoundingClientRect();
  var cols=['#F59E0B','#8B7CF6','#5EB8F5','#FB7185','#5EEAD4'];
  for(var i=0;i<14;i++){
    var p=document.createElement('i');
    var a=Math.random()*Math.PI*2, dist=46+Math.random()*56;
    p.style.left=(r.left+r.width/2-3)+'px';
    p.style.top=(r.top+r.height/2-3)+'px';
    p.style.background=cols[i%cols.length];
    p.style.setProperty('--dx',(Math.cos(a)*dist).toFixed(1)+'px');
    p.style.setProperty('--dy',(Math.sin(a)*dist-22).toFixed(1)+'px');
    p.style.animationDelay=(Math.random()*.08)+'s';
    box.appendChild(p);
  }
  document.body.appendChild(box);
  setTimeout(function(){if(box.parentNode)box.parentNode.removeChild(box);},950);
}
/* 成就列表视图 */
function renderAchList(){
  ACH_VIEW.open=null;
  var box=document.getElementById('achBox');
  if(!STATE){box.innerHTML='';return;}
  var list=achCalc(STATE);
  var nUnlock=0;list.forEach(function(x){if(x.ok)nUnlock++;});
  var st=STATE.stats||{};

  /* 顶栏 */
  var h='<div class="ach-head">'+
    '<div class="hicon"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M7 4h10v5a5 5 0 0 1-10 0V4z"/><path d="M7 5.5H4.5V8a3 3 0 0 0 3 3M17 5.5h2.5V8a3 3 0 0 1-3 3"/><path d="M12 14v3.5M8.5 21h7l-.8-3.5h-5.4L8.5 21z"/></svg></div>'+
    '<div class="htx"><div class="hname">成就殿堂</div>'+
    '<div class="hsub">已解锁 <b>'+nUnlock+'</b> / '+list.length+' 个成就</div></div>'+
    '<button class="ach-close" onclick="closeTrophy()">✕</button></div>';

  /* 顶部大数字统计 */
  h+='<div class="ach-top">'+
    '<div class="cell2 gold"><div class="v">'+nUnlock+' <small>/ '+list.length+'</small></div><div class="k">已解锁成就</div></div>'+
    '<div class="cell2"><div class="v">'+(STATE.doneCount||0)+' <small>/ '+(STATE.target||0)+'</small></div><div class="k">累计完成题数</div></div>'+
    '<div class="cell2 mint"><div class="v">'+(st.streak||0)+' <small>天</small></div><div class="k">连续刷题</div></div>'+
    '</div>';

  /* 分类筛选 */
  h+='<div class="ach-chips">';
  h+='<button class="chip'+(ACH_VIEW.cat==='all'?' on':'')+'" onclick="achChip(\'all\')">全部<span class="n">'+nUnlock+'/'+list.length+'</span></button>';
  for(var ck in ACH_CATS){
    var c=ACH_CATS[ck];
    var tt=list.filter(function(x){return x.def.cat===ck;}).length;
    var uu=list.filter(function(x){return x.def.cat===ck&&x.ok;}).length;
    h+='<button class="chip'+(ACH_VIEW.cat===ck?' on':'')+'" onclick="achChip(\''+ck+'\')">'+c.name+'<span class="n">'+uu+'/'+tt+'</span></button>';
  }
  h+='</div>';

  /* 卡片网格 */
  var show=list.filter(function(x){return ACH_VIEW.cat==='all'||x.def.cat===ACH_VIEW.cat;});
  if(!show.length){
    h+='<div class="ad-empty">这个分类下还没有成就</div>';
  }else{
    h+='<div class="ach-grid">';
    show.forEach(function(x){h+=achCardHTML(x);});
    h+='</div>';
  }
  box.innerHTML=h;
}
function achChip(cat){ACH_VIEW.cat=cat;renderAchList();}
/* 单张成就卡片 */
function achCardHTML(x){
  var a=x.def,c=ACH_CATS[a.cat]||ACH_CATS.milestone;
  var pct=x.target?Math.min(100,Math.round(x.cur/x.target*100)):100;
  var num=x.target
    ?'<b>'+Math.min(x.cur,x.target)+'</b> / '+x.target+' '+a.unit
    :'<b>'+x.cur+'</b> '+a.unit;
  /* 记录型成就（单日之巅）：不搞百分比，进度位直接摆纪录——哪天 · 几题 */
  if(a.rec){
    pct=x.ok?100:0;
    num=(x.rec&&x.rec.count)
      ?'<b>'+md(x.rec.date)+'</b> · '+x.rec.count+' '+a.unit
      :'暂无记录';
  }
  return '<button class="ach-card'+(x.ok?'':' locked')+'" '+
    'style="--c1:'+c.c1+';--c2:'+c.c2+';--tint:'+c.tint+';--bd:'+c.bd+'" '+
    'onclick="openAchDetail(\''+a.id+'\')">'+
    (x.ok?'<span class="aok">✓</span>':'')+
    '<div class="arow"><div class="aicon">'+a.icon+'</div>'+
    '<div class="atx"><div class="anm">'+esc(a.name)+'</div>'+
    '<div class="ads">'+esc(a.desc)+'</div></div></div>'+
    '<div class="apbar"><i style="width:'+pct+'%"></i></div>'+
    '<div class="apnum"><span>'+(x.ok?'已解锁':'进行中')+'</span><span>'+num+'</span></div>'+
    '</button>';
}
/* 成就详情视图（点卡片进来）*/
function openAchDetail(id){
  if(!STATE)return;
  var list=achCalc(STATE), x=null;
  list.forEach(function(y){if(y.def.id===id)x=y;});
  if(!x)return;
  var a=x.def,c=ACH_CATS[a.cat]||ACH_CATS.milestone;
  var pct=x.target?Math.min(100,Math.round(x.cur/x.target*100)):100;
  var left=Math.max(0,x.target-x.cur);
  /* 记录型成就（单日之巅）：详情里单独一块摆完整纪录——日期 / 题数 / 来自哪个计划的哪轮 */
  var recBlock='';
  if(a.rec){
    var ra=(STATE.recAll)||{date:'',count:0,list:''};
    recBlock=ra.count
      ?'<div class="ad-rec"><div class="ad-rec-k">目前的纪录</div>'+
       '<div class="ad-rec-v">'+md(ra.date)+' · <b>'+ra.count+'</b> 题</div>'+
       (ra.list?'<div class="ad-rec-f">来自「'+esc(ra.list)+'」</div>':'')+'</div>'
      :'<div class="ad-rec"><div class="ad-rec-v">所有计划还没有任何一天的完成记录</div></div>';
  }
  var h='<div class="ach-detail'+(x.ok?'':' locked')+'" '+
    'style="--c1:'+c.c1+';--c2:'+c.c2+';--tint:'+c.tint+';--bd:'+c.bd+'">'+
    '<button class="ach-back" onclick="renderAchList()">‹ 返回</button>'+
    '<div class="ad-icon">'+a.icon+'</div>'+
    '<div class="ad-name">'+esc(a.name)+'</div>'+
    '<div class="ad-cat">'+c.name+'</div>'+
    '<div class="ad-desc">'+esc(a.desc)+'</div>'+
    recBlock+
    '<div class="ad-prog"><div class="apbar"><i style="width:'+pct+'%"></i></div>'+
    '<div class="ad-pnum"><b>'+(x.target?Math.min(x.cur,x.target)+' / '+x.target+' '+a.unit:'')+'</b>'+
    '<span>'+(x.target?Math.round(pct)+'%':'')+'</span></div></div>'+
    '<div class="ad-state '+(x.ok?'ok':'no')+'">'+
    (x.ok?'✓ 已解锁':('未解锁 · 还差 '+left+' '+a.unit))+'</div>'+
    '<div class="ad-btns">'+
    (a.id==='e3'||a.id==='x1'
      ?'<button class="ad-btn" onclick="calFlash();closeTrophy()">去日历看看</button>'
      :'')+
    '<button class="ad-btn primary" onclick="renderAchList()">'+(x.ok?'太棒了':'知道了')+'</button></div>'+
    '</div>';
  document.getElementById('achBox').innerHTML=h;
  ACH_VIEW.open=id;
}
/* 日历高亮一下（从成就详情跳过来时用）*/
function calFlash(){
  var c=document.getElementById('cal');
  if(!c)return;
  c.classList.remove('flash');void c.offsetWidth;c.classList.add('flash');
  setTimeout(function(){c.classList.remove('flash');},1300);
  c.scrollIntoView({behavior:'smooth',block:'center'});
}

/* ---------- 左侧：统计 ---------- */
function renderStats(s){
  var doneN=s.doneCount, tgt=s.target;
  document.getElementById('sDone').textContent=doneN;
  document.getElementById('sLeft').textContent=Math.max(0,tgt-doneN);
  var mk=document.getElementById('navMk');
  if(mk){
    var st=s.markStats||{};
    mk.textContent=st.total?(st.wrong+' 错 / '+st.classic+' 经典'):'0';
  }
  var sp=document.getElementById('sPre');
  if(sp)sp.textContent=s.preCount||0;
  var cand=s.candLeft||0;
  var cEl=document.getElementById('sCand');
  if(cEl){
    cEl.textContent=cand;
    cEl.style.color=cand>0?'':'#E11D48';
  }
  document.getElementById('doneN').textContent=doneN;
  document.getElementById('tgt').textContent=tgt;
  document.getElementById('pageTitle').textContent=s.activeName||'刷题看板';
  var pct=tgt?Math.round(doneN/tgt*100):0;
  document.getElementById('bar').style.width=pct+'%';
  document.getElementById('pct').textContent=pct+'%';
  var arc=document.getElementById('ringArc');
  if(arc){var C=2*Math.PI*30;arc.setAttribute('stroke-dashoffset',String(C*(1-pct/100)));}
  document.getElementById('daysInfo').textContent='已展开 '+s.board.length+' / '+s.totalDays+' 天';

  renderListSwitcher(s);
  renderPlanBar(s);
  renderCalendar(s);
  renderTaskList(s);
  renderStats2(s);
  renderWeekly(s);
  renderReminders(s);
  renderTrophy(s);
}

/* ---------- 计划栏 ---------- */
function renderPlanBar(s){
  var p=s.plan||{};
  document.getElementById('pbTotal').textContent=p.total||0;
  document.getElementById('pbPer').textContent=p.perDay||4;
  document.getElementById('pbDays').textContent=p.days||0;
  var paused=!!s.paused;
  var btn=document.getElementById('pauseBtn');
  if(btn){
    btn.textContent=paused?'▶ 继续计划':'⏸ 暂停计划';
    btn.className=paused?'pausing':'';
    btn.setAttribute('data-tip',paused
      ? '继续计划<br>已完成的记录都还在，结束日期按剩余题数顺延'
      : '暂停计划<br>暂停期间日历不标红，已完成的记录保留');
  }
  var tag=document.getElementById('pauseTag');
  if(tag)tag.style.display=paused?'':'none';
}
async function togglePause(){
  if(!STATE)return;
  var was=!!STATE.paused;
  var j=await post('/api/pauseplan',{pause:!was});
  if(!j.ok){toast('操作失败');return;}
  STATE=j.state;
  renderStats(j.state);renderBoard(j.state);
  toast(was?'计划已继续 · 之前的记录都在':'计划已暂停 · 记录都留着');
}

/* ---------- 题单切换 ---------- */
function renderListSwitcher(s){
  var box=document.getElementById('plists');
  var arr=s.lists||[];
  /* 侧栏只摆当前题单一行，其余题单和「新建」都收进它的下拉菜单 */
  box.innerHTML='';
  arr.forEach(function(x){
    if(!x.active)return;
    var d=document.createElement('div');
    d.className='plist on';
    d.setAttribute('data-tip','<div class="tt">'+esc(x.name)+'</div><div class="tr">'+
      '点开菜单：题目清单 / 切换题单 / 新建</div>');
    d.innerHTML='<span class="pn">'+esc(x.name)+'</span>'+
      '<span class="pc">'+x.done+'/'+x.total+'</span>'+
      '<span class="pchev">▾</span>';
    d.onclick=function(e){openListPop(x,e);};
    box.appendChild(d);
  });
}

/* 点击「当前题单」弹出小菜单。
   侧栏只留当前题单一行，其余题单 + 新建都收在这里（题目清单原本也单列过）。 */
var ICO_LIST='<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 6h13"/><path d="M8 12h13"/><path d="M8 18h13"/><path d="M3 6h.01"/><path d="M3 12h.01"/><path d="M3 18h.01"/></svg>';
var ICO_DEL='<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="M19 6l-1 14H6L5 6"/></svg>';
var ICO_PLUS='<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14"/><path d="M5 12h14"/></svg>';

function openListPop(x,ev){
  var pop=document.getElementById('listPop');
  if(!pop)return;
  var s=STATE||{};
  var others=(s.lists||[]).filter(function(o){return !o.active;});

  var h='<button onclick="closeListPop();openPanel(\'list\')">'+ICO_LIST+
    '<span class="popnm">题目清单</span>'+
    '<span class="poppc">'+x.done+'/'+x.total+'</span></button>';

  if(others.length){
    h+='<div class="pd"></div><div class="popsec">切换题单</div>';
    others.forEach(function(o){
      h+='<button data-key="'+esc(o.key)+'" onclick="popSwitch(this)">'+
        '<span class="popnm">'+esc(o.name)+'</span>'+
        '<span class="poppc">'+o.done+'/'+o.total+'</span></button>';
    });
  }

  h+='<div class="pd"></div>'+
    '<button onclick="closeListPop();openNewList()">'+ICO_PLUS+
    '<span class="popnm">新建题单</span></button>'+
    '<button class="dg" data-key="'+esc(x.key)+'" data-nm="'+esc(x.name)+'" onclick="popDel(this)">'+
    ICO_DEL+'<span class="popnm">删除当前题单</span></button>';

  pop.innerHTML=h;
  pop.classList.add('show');
  var r=ev.currentTarget.getBoundingClientRect();
  var w=pop.offsetWidth||160;
  pop.style.left=Math.max(8,Math.min(r.left,window.innerWidth-w-8))+'px';
  pop.style.top=(r.bottom+6)+'px';
}
function closeListPop(){var p=document.getElementById('listPop');if(p)p.classList.remove('show');}
function popDel(el){
  closeListPop();
  delList(el.getAttribute('data-key'),el.getAttribute('data-nm'));
}
function popSwitch(el){
  closeListPop();
  switchList(el.getAttribute('data-key'));
}
async function switchList(key){
  var j=await post('/api/switch',{key:key});
  if(!j.ok){toast('切换失败');return;}
  STATE=j.state;SEARCH='';
  document.getElementById('search').value='';
  document.getElementById('searchClr').classList.remove('on');
  renderStats(j.state);renderBoard(j.state);
  toast('已切换到「'+(j.state.activeName||key)+'」');
}
async function delList(key,name){
  if(!confirm('删除题单「'+name+'」？该题单的进度记录会一起删掉。'))return;
  var j=await post('/api/dellist',{key:key});
  if(!j.ok){toast(j.msg||'删除失败');return;}
  STATE=j.state;renderStats(j.state);renderBoard(j.state);
  toast('已删除');
}

/* ---------- 学习统计 ---------- */
function renderStats2(s){
  var st=s.stats||{};
  document.getElementById('stStreak').textContent=(st.streak||0)+' 天';
  document.getElementById('stAvg').textContent=(st.avg7||0)+' 题';
  var eta=st.eta;
  var etaK=document.getElementById('stEtaK');
  if(eta){
    var dd=Math.round((new Date(eta)-new Date(s.today))/86400000);
    document.getElementById('stEta').textContent=eta.slice(5);
    if(etaK)etaK.textContent='预计完成 · 约 '+dd+' 天后';
  }else{
    var fin=(st.left===0);
    document.getElementById('stEta').textContent=fin?'🎉':'—';
    if(etaK)etaK.textContent=fin?'已完成':'预计完成';
  }

  var diff=st.diff||{easy:0,medium:0,hard:0};
  var tot=(diff.easy+diff.medium+diff.hard)||1;
  var order=[['easy','简单','#10B981'],['medium','中等','#F59E0B'],['hard','困难','#EF4444']];
  var bar=document.getElementById('diffBar');
  bar.innerHTML='';
  order.forEach(function(o){
    var n=diff[o[0]]||0;
    if(!n)return;
    var i=document.createElement('i');
    i.style.width=(n/tot*100)+'%';
    i.style.background=o[2];
    i.setAttribute('data-tip','<div class="tt">'+o[1]+'</div><div class="tr">'+n+' 题</div>');
    bar.appendChild(i);
  });
  document.getElementById('diffLegend').innerHTML=order.map(function(o){
    var n=diff[o[0]]||0;
    return '<span><em style="background:'+o[2]+'"></em>'+o[1]+' '+n+
           ' <span style="color:#C3C9D2">'+Math.round(n/tot*100)+'%</span></span>';
  }).join('');

  var sp=document.getElementById('spark');
  sp.innerHTML='';
  var d7=st.days7||[];
  var mx=Math.max.apply(null,[1].concat(d7.map(function(x){return x.count;})));
  d7.forEach(function(x){
    var el=document.createElement('div');
    el.className='sb'+(x.count>=4?' hi':'');
    var h=x.count?Math.max(6,Math.round(x.count/mx*38)):3;
    el.innerHTML='<b>'+(x.count||'')+'</b><i style="height:'+h+'px"></i>'+
      '<span>'+String(x.date).slice(8)+'</span>';
    el.setAttribute('data-tip','<div class="tt">'+md(x.date)+'</div><div class="tr">'+x.count+' 题</div>');
    sp.appendChild(el);
  });

  /* 单日之最：本计划到目前为止完成最多的一天（日期 + 题数）。
     只算真正做的新题（与 daily/日历同源），并列取更早的一天。 */
  var be=document.getElementById('stBest');
  if(be){
    var bd=bestDay(s);
    if(bd){
      be.innerHTML=md(bd.date)+' · '+bd.count+' 题';
    }else{
      be.textContent='—';
    }
  }
}

/* 日历当前显示的月份（全局） */
var CAL_YM=null;

function calShift(delta){
  if(!CAL_YM){
    var t=new Date();CAL_YM={y:t.getFullYear(),m:t.getMonth()};
  }
  var d=new Date(CAL_YM.y,CAL_YM.m+delta,1);
  CAL_YM={y:d.getFullYear(),m:d.getMonth()};
  if(STATE)renderCalendar(STATE);
}
function calToday(){
  var t=new Date();CAL_YM={y:t.getFullYear(),m:t.getMonth()};
  if(STATE)renderCalendar(STATE);
}

/* 把 Date 转成本地 YYYY-MM-DD（避免 toISOString 的时区偏移） */
function ymd(y,m,d){
  return y+'-'+String(m+1).padStart(2,'0')+'-'+String(d).padStart(2,'0');
}

function renderCalendar(s){
  var el=document.getElementById('cal');
  el.innerHTML='';
  var today=new Date();
  var todayStr=s.today||ymd(today.getFullYear(),today.getMonth(),today.getDate());
  if(!CAL_YM){CAL_YM={y:today.getFullYear(),m:today.getMonth()};}
  var y=CAL_YM.y, m=CAL_YM.m;

  var daily=s.daily||{};
  var detail=s.dailyDetail||{};
  var plan=s.plan||{};
  /* 题号 -> 题名，供日历悬停时显示「当天做了哪些题」 */
  var nameById={};
  (s.tasks||[]).forEach(function(t){nameById[t.id]=t.name;});

  /* 欠账超出上限顺延出来的「补做日」，日历上换颜色 */
  var extraDates=s.extraDates||[];

  /* 暂停区间：落在区间内的日子算「暂停中」，不判为空缺（不标红） */
  var pauses=s.pauses||[];
  function inPause(ds){
    for(var i=0;i<pauses.length;i++){
      var a=(pauses[i]||{}).from||'', b=(pauses[i]||{}).to||'';
      if(!a)continue;
      if(ds>=a&&(b===''||ds<=b))return true;
    }
    return false;
  }
  var pStart=plan.startDate||'';
  var pEnd=plan.endDate||'';

  var first=new Date(y,m,1).getDay();
  var dim=new Date(y,m+1,0).getDate();
  var monthTotal=0, missed=0, inPlan=0;

  document.getElementById('calMonth').textContent=y+' 年 '+(m+1)+' 月';
  // 计划区间提示
  var rg=document.getElementById('calRange');
  if(pStart&&pEnd){
    rg.innerHTML='计划区间：<b>'+fmtDate(pStart)+'</b> → <b>'+fmtDate(pEnd)+'</b>（共 '+plan.days+' 天）';
  }else{
    rg.innerHTML='还没有设定计划区间';
  }

  WD.forEach(function(w){var d=document.createElement('div');d.className='wd';d.textContent=w[1];el.appendChild(d);});
  for(var i=0;i<first;i++){var p=document.createElement('div');p.className='cell pad';el.appendChild(p);}

  for(var d=1;d<=dim;d++){
    var ds=ymd(y,m,d);
    var n=daily[ds]||0;
    var c=document.createElement('div');
    c.setAttribute('data-date',ds);
    var cls='cell';

    /* 是否落在计划区间内（没有区间时：今天及以前算区间内） */
    var hasRange=!!(pStart&&pEnd);
    var inRange=hasRange?(ds>=pStart&&ds<=pEnd):(ds<=todayStr);
    var beforeStart=hasRange&&ds<pStart;
    var afterEnd=hasRange&&ds>pEnd;

    if(inRange)inPlan++;

    var head='<div class="tt">'+fmtDate(ds)+'</div>';

    var pausedDay=inPause(ds);

    if(n>0){
      /* 做过题：日期居中 + 做题量右上角标。原来直接把日期替换成题数，
         「4」分不清是 4 号还是做了 4 题。颜色深浅继续编码做题量。 */
      var lvl=n>=8?4:n>=5?3:n>=3?2:1;
      cls+=' l'+lvl;
      /* 提前日：当天做题量超出计划配额 —— 提前把后面的题做掉了，薄荷青 + 左上箭头 */
      var early=n>(s.perDay||4);
      if(early)cls+=' early';
      c.innerHTML='<span class="dn">'+d+'</span><span class="cnt">'+n+'</span>';
      var rows=(detail[ds]||[]).map(function(id){
        return '<div class="tr">#'+id+' '+esc(nameById[id]||'')+'</div>';
      }).join('');
      c.setAttribute('data-tip',head+'<div class="tr" style="color:var(--iris-d);font-weight:800">'+
        n+' 题</div>'+rows+
        (early?'<div class="tr" style="color:#0F766E;font-weight:800">↑ 提前 · 超出当日计划，做了 '+n+' 题</div>':''));
      monthTotal+=n;
    }else if(pausedDay){
      /* 暂停期间：斜纹灰，不算空缺 */
      cls+=' pause'; c.textContent=d;
      c.setAttribute('data-tip',head+'<div class="tr">计划暂停中</div>');
    }else if(extraDates.indexOf(ds)>=0){
      /* 补做日：欠账顺延加出来的一天，琥珀色 */
      cls+=' extra'; c.textContent=d;
      c.setAttribute('data-tip',head+'<div class="tr">补做日 · 欠账顺延</div>');
    }else if(inRange){
      /* 区间内、没做题 -> 红（空缺） */
      if(ds>todayStr){
        cls+=' future'; c.textContent=d;
        c.setAttribute('data-tip',head+'<div class="tr">还没到</div>');
      }else{
        cls+=' miss'; c.textContent=d;
        if(ds===todayStr){c.setAttribute('data-tip',head+'<div class="tr">今天还没做</div>');}
        else{c.setAttribute('data-tip',head+'<div class="tr">当天 0 题（未完成）</div>');missed++;}
      }
    }else{
      /* 区间外：中性灰，不判为空缺 */
      cls+=' out'; c.textContent=d;
      var why=beforeStart?'计划开始前':(afterEnd?'计划已结束':'不在计划区间内');
      c.setAttribute('data-tip',head+'<div class="tr">'+why+'</div>');
    }

    if(ds===pStart)cls+=' beg';
    if(ds===pEnd)cls+=' end';
    if(ds===todayStr)cls+=' today';
    c.className=cls;
    el.appendChild(c);
  }

  var sub=(m+1)+'月 '+monthTotal+' 题';
  if(missed>0){sub+=' · '+missed+' 天空缺';}
  document.getElementById('calSub').textContent=sub;
}

/* ---------- 题目清单（小方框） ---------- */
function renderTaskList(s){
  var el=document.getElementById('tlist');
  var arr=s.tasks||[];
  var doneN=arr.filter(function(t){return t.done;}).length;
  var kw=(SEARCH||'').trim().toLowerCase();
  var view=arr;
  if(kw){
    view=arr.filter(function(t){
      return String(t.id).indexOf(kw)>=0||
             String(t.name).toLowerCase().indexOf(kw)>=0||
             String(t.category||'').toLowerCase().indexOf(kw)>=0;
    });
  }
  var subEl=document.getElementById('listSub');
  if(subEl)subEl.textContent=kw?(view.length+' 条结果'):(doneN+' / '+arr.length);
  el.innerHTML='';
  if(!view.length){
    el.innerHTML='<div class="nores">没有匹配的题目</div>';
    return;
  }
  view.forEach(function(t){
    var d=document.createElement('div');
    d.className='titem'+(t.done?' on':'');
    var color=DIFF[t.difficulty]||'#9CA3AF';
    d.innerHTML='<span class="dot" style="background:'+color+'"></span>'+
      '<span class="tid">#'+esc(t.id)+'</span>'+
      '<span class="tnm">'+esc(t.name)+'</span>'+
      (t.done?'<span style="color:#10B981;font-weight:700;font-size:11px">✓</span>':'');
    el.appendChild(d);
  });
}
function onSearch(v){
  SEARCH=v||'';
  document.getElementById('searchClr').classList.toggle('on',!!SEARCH);
  if(STATE)renderTaskList(STATE);
}
function clearSearch(){
  document.getElementById('search').value='';
  onSearch('');
}

/* ---------- 分类清单弹窗 ---------- */
function openCategories(){
  if(!STATE)return;
  dockReturn();
  MODAL='cats';
  var s=STATE;
  document.getElementById('mTitle').innerHTML='题目清单<span class="msub">'+
    esc(s.activeName||'')+' · '+s.doneCount+'/'+s.target+'</span>';
  document.getElementById('modal').classList.add('wide');
  var body=document.getElementById('mBody');
  var cats=s.categories||[];
  if(!cats.length){
    body.innerHTML='<div style="text-align:center;color:#9CA3AF;padding:34px">这个题单还没有题目</div>';
  }else{
    body.innerHTML=cats.map(function(c){
      var full=c.done>=c.total&&c.total>0;
      var rows=c.problems.map(function(p){
        var col=DIFF[p.difficulty]||'#9CA3AF';
        return '<div class="crow'+(p.done?' on':'')+'">'+
          '<span class="rdot" style="background:'+col+'"></span>'+
          '<span class="rid">#'+esc(p.id)+'</span>'+
          '<span class="rnm">'+esc(p.name)+'</span>'+
          (p.hint?'<span class="rhint">'+esc(p.hint)+'</span>':'')+
          (p.done?'<span class="rck">✓</span>':'')+
        '</div>';
      }).join('');
      return '<div class="cgrp"><div class="cgtop"><span class="cn">'+esc(c.name)+'</span>'+
        '<span class="cc'+(full?' full':'')+'">'+c.done+' / '+c.total+
        (full?' ✓':'')+'</span></div>'+rows+'</div>';
    }).join('');
  }
  document.getElementById('mask').classList.add('show');
}

/* ---------- 新建题单（从力扣 URL 导入） ---------- */
function openNewList(){
  dockReturn();
  MODAL='new';
  document.getElementById('mTitle').innerHTML='新建题单';
  document.getElementById('modal').classList.remove('wide');
  renderNewListModal();
  document.getElementById('mask').classList.add('show');
  setTimeout(function(){var e=document.getElementById('nlUrl');if(e)e.focus();},60);
}
function renderNewListModal(){
  document.getElementById('mBody').innerHTML =
    '<div class="frow"><label>力扣题单 URL</label>'+
      '<input type="text" id="nlUrl" placeholder="https://leetcode.cn/problem-list/xxxxxx/"></div>'+
    '<div class="frow"><label>题单名称（可选）</label>'+
      '<input type="text" id="nlUrlName" placeholder="留空则自动命名"></div>'+
    '<div class="frow"><div class="f2">'+
      '<div><label>每天几题</label><input type="number" id="nlUrlPer" value="4" min="1" max="50"></div>'+
    '</div></div>'+
    '<div class="frow"><label>分组方式</label>'+
      '<select id="nlGroup">'+
        '<option value="tag">按考点标签分组</option>'+
        '<option value="none">不分组（全部放一起）</option>'+
      '</select></div>'+
    '<div class="fhelp" style="margin-top:-6px">'+
      '分享题单和官方标签题单（如 <code>problem-list/hash-table/</code>）都可以；'+
      '需联网，由服务借系统自带的 Edge / Chrome 无头拉取</div>'+
    '<div id="nlPreview"></div>'+
    '<div class="fbtns">'+
      '<button class="cancel" onclick="closeModal()">取消</button>'+
      '<button class="ok" onclick="importUrl()">导入题单</button>'+
    '</div>';
}
async function importUrl(){
  var url=(document.getElementById('nlUrl').value||'').trim();
  var name=(document.getElementById('nlUrlName').value||'').trim();
  var per=parseInt(document.getElementById('nlUrlPer').value,10)||4;
  var group=(document.getElementById('nlGroup').value||'tag');
  if(!url){toast('请粘贴力扣题单 URL');return;}
  var prev=document.getElementById('nlPreview');
  prev.innerHTML='<div class="fhelp">正在从力扣拉取题单，请稍候...</div>';
  var j=await post('/api/importurl',{url:url,name:name,perDay:per,group:group});
  if(!j.ok){
    prev.innerHTML='<div class="fhelp" style="color:#dc2626">导入失败：'+(j.msg||'未知错误')+'</div>';
    return;
  }
  prev.innerHTML='<div class="fhelp" style="color:#059669">✓ 共 '+j.count+' 道题，'+j.groups+' 个分类</div>';
  var j2=await post('/api/importurlsave',{url:url,name:name,perDay:per,group:group});
  if(!j2.ok){
    prev.innerHTML='<div class="fhelp" style="color:#dc2626">保存失败：'+(j2.msg||'未知错误')+'</div>';
    return;
  }
  STATE=j2.state;
  closeModal();
  renderStats(j2.state);renderBoard(j2.state);
  toast('题单「'+j2.info.name+'」已导入，共 '+j2.info.count+' 题');
}

/* ---------- 右侧：只显示当天 ---------- */
function dayHTML(day, di, s, isCur){
  var fin=day.done&&!day.tasks.length;
  var debt=day.deficit||0;
  var comp=(day.completed!=null)?day.completed:null;

  var badge='';
  if(fin){
    badge += debt>0
      ? '<span class="daybadge b-carry">欠 '+debt+' 题已顺延</span>'
      : '<span class="daybadge b-fin">已完成</span>';
  }else if(day.date===s.today){
    badge='<span class="daybadge b-today">今天</span>';
  }
  var dtitle=day.extra?'补做日':('第 '+(day.dayIndex+1)+' 天');
  if(day.extra){
    badge+='<span class="daybadge" style="background:#FEF3C7;color:#B45309">计划外补做</span>';
  }
  /* 加一题：过去的天做完就禁用；今天就算全做完了也留着入口——
     想多做题只能「+ 加一题」，不翻第二天的卡 */
  var addOff=(fin&&day.date!==s.today)?'disabled':'';
  var addTip=(fin&&day.date===s.today)
    ?' data-tip="今天已全部完成<br>加一道 · 挑战自我"':'';
  var head='<div class="dayhead"><span class="daytitle">'+dtitle+'</span>'+
    '<span class="daydate">'+fmtDate(day.date)+' '+wd(day.date)+'</span>'+badge+
    '<span class="spacer"></span>'+
    '<button class="addone" data-di="'+di+'" '+addOff+addTip+'>+ 加一题</button>'+
    '<button class="addone reset" data-di="'+di+'" data-tip="恢复成当天的原始题目<br>顺延进来的题会保留">重置</button></div>';

  var inner='';
  day.tasks.forEach(function(t,ti){
    var color=DIFF[t.difficulty]||'#A79FBA';
    var grad=DIFF_GRAD[t.difficulty]||'linear-gradient(135deg,#D5CDE0,#A79FBA)';
    var label=LBL[t.difficulty]||'';
    var hint=t.hint?('考点：'+esc(t.hint)):(t.category?('分类：'+esc(t.category)):'');
    inner+='<div class="task'+(t.checked?' done':'')+(t.carry?' carry':'')+'" data-di="'+di+'" data-ti="'+ti+'">'+
      '<div class="check">'+CHECK+'</div>'+
      '<div class="num" style="background:'+grad+'">'+esc(t.id)+'</div>'+
      '<div class="info"><div class="name">'+esc(t.name)+'</div>'+
      (hint?'<div class="hint">'+hint+'</div>':'')+'</div>'+
      (t.carry?'<span class="tag">补做</span>':'')+
      '<span class="pill" style="background:'+grad+'">'+label+'</span>'+
      '<button class="icobtn swap" data-di="'+di+'" data-ti="'+ti+'" data-tip="换一道题（不影响统计）">'+ICO_SWAP+'</button>'+
      '<button class="icobtn mark" data-di="'+di+'" data-ti="'+ti+'" data-tip="之前做过<br>计入已完成，不计入每日量">'+ICO_PRE+'</button>'+
      markBtn(t.id)+'</div>';
  });

  if(fin){
    var txt;
    if(debt>0){
      var n=(comp==null)?'':('完成 '+comp+' 题，');
      txt='<div style="padding:14px;text-align:center;color:#BE123C;font-weight:600;line-height:1.7">'+
          n+debt+' 题已顺延'+(day.extra?'（本补做日未做完）'
            :('到第 '+(day.dayIndex+2)+' 天补做'))+'</div>';
    }else{
      txt='<div style="padding:14px;text-align:center;color:#10B981;font-weight:600">这天已全部完成</div>';
    }
    inner=txt;
  }

  // 说明不再铺成文字，挂在「确定完成」按钮里的问号上（hover 才看）
  var per=(s.plan&&s.plan.perDay)||4;
  // 注意：data-tip 是 HTML 属性，里面只能用单引号，双引号会把属性提前闭合
  var qtip="<div class='tt'>没做完也能直接点「确定完成」</div>"+
    "<div class='tr'>· 没勾选的题会自动顺延到第二天</div>"+
    "<div class='tr'>· 顺延超过 "+per*2+" 道的部分，挪到计划末尾的补做日</div>"+
    "<div class='tr'>· 补做日在日历上是<b style='color:#B45309'>琥珀色</b>那天</div>";
  var btn='<button class="submit" data-di="'+di+'" '+(fin?'disabled':'')+'>'+
    (fin?'已完成':'确定完成')+
    (fin?'':'<span class="swq" data-tip="'+qtip+'">?</span>')+'</button>';
  var tip='';
  // 当前天只留「撤销」。展开下一天交给服务端跨天自动做：
  //手动展开会让「明天的题板」在今天就能提交，记录算到哪天变得很别扭；
  // 想今天多做几道，用题板上的「+ 加一题」就够了。
  var acts='';
  if(isCur){
    acts='<div class="dayacts">'+
      '<button class="tbtn" id="undoBtn" onclick="undo()" data-tip="撤销上一步操作">↶ 撤销</button>'+
      '</div>';
  }
  return head+inner+btn+tip+acts;
}

function bindDay(box){
  box.querySelectorAll('.task').forEach(function(el){
    el.onclick=function(e){if(e.target.closest('.swap'))return;
      toggle(+el.dataset.di,+el.dataset.ti);};
  });
  box.querySelectorAll('.swap').forEach(function(el){
    el.onclick=function(e){e.stopPropagation();swap(+el.dataset.di,+el.dataset.ti);};
  });
  box.querySelectorAll('.mark').forEach(function(el){
    el.onclick=function(e){e.stopPropagation();markPre(+el.dataset.di,+el.dataset.ti);};
  });
  box.querySelectorAll('.mkbtn').forEach(function(el){
    el.onclick=function(e){e.stopPropagation();askMark(+el.dataset.mark);};
  });
  box.querySelectorAll('.addone:not(.reset)').forEach(function(el){
    el.onclick=function(e){e.stopPropagation();addOne(+el.dataset.di);};
  });
  box.querySelectorAll('.addone.reset').forEach(function(el){
    el.onclick=function(e){e.stopPropagation();resetDay(+el.dataset.di);};
  });
  box.querySelectorAll('.submit').forEach(function(el){
    el.onclick=function(){submit(+el.dataset.di);};
  });
}

var LAST_DAY='';   // 上次渲染的「当前天」标识：同一天重复渲染时不播入场动画
function renderBoard(s){
  var box=document.getElementById('board');
  box.innerHTML='';
  var cur=s.board.length-1;
  if(cur<0){
    box.innerHTML='<div class="day" style="text-align:center;color:#9CA3AF;padding:40px">'+
      '这个题单还没有题目</div>';
    return;
  }
  /* 「当前天」严格按日期锁定今天：做完今天也停留当天，绝不顺手把明天的卡翻出来；
     跨到第二天只靠零点自动刷新（watchNewDay）或下次启动服务（auto_settle）。
     数据里找不到今天（停机多日没补结算 / 计划排满）才退化成
     「最后一个还没做完的普通天」，保证老状态也有合理落点。 */
  var todayI=-1;
  for(var i=0;i<s.board.length;i++){
    if(s.board[i].date===s.today){todayI=i;break;}
  }
  if(todayI>=0){
    cur=todayI;
  }else{
    // 补做日排在数组末尾，兜底时仍以普通天优先
    var lastN=-1;
    for(var j=0;j<s.board.length;j++) if(!s.board[j].extra) lastN=j;
    if(lastN>=0&&!s.board[lastN].done) cur=lastN;
  }

  var dcur=s.board[cur];
  var dkey=(s.activeList||'')+'#'+dcur.dayIndex+'#'+dcur.date+(dcur.extra?'#x':'');
  var el=document.createElement('div');
  el.className='day'+(dcur.done&&!dcur.tasks.length?' finished':'')+
    (dkey===LAST_DAY?' noanim':'');
  LAST_DAY=dkey;
  el.innerHTML=dayHTML(dcur,cur,s,true);
  box.appendChild(el);
  bindDay(box);

  document.getElementById('daysInfo').textContent=s.board[cur].extra
    ? ('补做日 / 共 '+s.totalDays+' 天')
    : ('第 '+(s.board[cur].dayIndex+1)+' / '+s.totalDays+' 天');

  var ub=document.getElementById('undoBtn');   // 在题板底部操作条里
  if(ub){
    ub.disabled=!s.canUndo;
    ub.setAttribute('data-tip',s.canUndo?'撤销上一步操作':'没有可撤销的操作');
  }
}

/* ---------- 二级菜单面板（把侧栏细节收进弹窗） ----------
   做法：这些区块的 DOM 常驻在 #dock（隐藏），打开弹窗时把节点搬进弹窗，
   关闭时再搬回 #dock。渲染逻辑完全复用，不用为弹窗重写一份。 */
var DOCKED=[];   // 记录本次搬走了哪些节点

function dockReturn(){
  var dock=document.getElementById('dock');
  if(!dock)return;
  DOCKED.forEach(function(el){
    if(el&&el.parentNode!==dock)dock.appendChild(el);
  });
  DOCKED=[];
}

function openPanel(kind){
  if(!STATE)return;
  dockReturn();
  var s=STATE;
  var body=document.getElementById('mBody');
  var modal=document.getElementById('modal');
  var title=document.getElementById('mTitle');
  body.innerHTML='';
  modal.classList.remove('wide');
  MODAL=kind;

  function take(id){
    var el=document.getElementById(id);
    if(el){DOCKED.push(el);body.appendChild(el);}
    return el;
  }

  if(kind==='list'){
    title.innerHTML='题目清单<span class="msub">'+esc(s.activeName||'')+' · '+
      s.doneCount+'/'+s.target+'</span>';
    take('dockList');
    renderTaskList(s);
  }else if(kind==='stats'||kind==='weekly'){
    /* 学习统计 + 本周进度合并成一个面板（侧栏只留一个入口） */
    title.innerHTML='学习统计<span class="msub">'+esc(s.activeName||'')+'</span>';
    take('dockStats');
    renderStats2(s);
    var h=document.createElement('div');
    h.className='psec';
    h.style.marginTop='20px';
    h.textContent='本周进度';
    body.appendChild(h);
    take('dockWeekly');
    renderWeekly(s);
  }else if(kind==='marks'){
    title.innerHTML='错题本<span class="msub">'+esc(s.activeName||'')+'</span>';
    modal.classList.add('wide');
    body.innerHTML=renderMarks(s);
  }else if(kind==='remind'){
    title.innerHTML='每日提醒<span class="msub">到点弹 Windows 通知</span>';
    take('dockRemind');
    renderReminders(s);
  }else if(kind==='data'){
    title.innerHTML='数据管理<span class="msub">'+esc(s.activeName||'')+'</span>';
    body.innerHTML=
      '<div class="psec">导出当前题单进度</div>'+
      '<div class="pbig" style="grid-template-columns:1fr 1fr">'+
        '<div class="cell2" style="cursor:pointer" onclick="exportData(\'json\')">'+
          '<div class="v">JSON</div><div class="k">完整结构，可再导入</div></div>'+
        '<div class="cell2" style="cursor:pointer" onclick="exportData(\'csv\')">'+
          '<div class="v">CSV</div><div class="k">表格，可看 Excel</div></div>'+
      '</div>'+
      '<div class="fhelp">导出的是<b>当前题单</b>的进度数据（含题目、完成记录、计划设置）。</div>';
  }else if(kind==='reset'){
    title.innerHTML='重新开始<span class="msub">当前第 '+(s.round||1)+' 轮 · '+esc(s.activeName||'')+'</span>';
    body.innerHTML=
      '<div class="psec">开始新一轮</div>'+
      '<div class="pbig" style="grid-template-columns:1fr">'+
        '<div class="cell2" style="cursor:pointer" onclick="restartRound()">'+
          '<div class="v">↻ 重新开始一轮</div>'+
          '<div class="k">本轮记录归档保留，从今天重排第一天</div></div>'+
      '</div>'+
      '<div class="fhelp">当前是第 <b>'+(s.round||1)+'</b> 轮 · '+
        (((s.rounds||[]).length)
          ? ('已完成 <b>'+s.rounds.length+'</b> 轮，'+
             '<a href="javascript:void(0)" onclick="openRounds()" '+
             'style="color:var(--iris-d);font-weight:800">查看往期记录</a>')
          : '还没有往期记录')+
      '</div>'+
      '<div class="psec" style="margin-top:20px">重置计划</div>'+
      '<div class="pbig" style="grid-template-columns:1fr 1fr">'+
        '<div class="cell2" style="cursor:pointer" onclick="resetPlan(\'progress\')">'+
          '<div class="v">重置进度</div><div class="k">清空完成记录，保留计划设置</div></div>'+
        '<div class="cell2" style="cursor:pointer" onclick="resetPlan(\'all\')">'+
          '<div class="v">恢复默认</div><div class="k">连计划设置一起重置</div></div>'+
      '</div>'+
      '<div class="fhelp">只影响<b>当前题单</b>，其它题单不受影响；重置后可用工具栏<b>撤销</b>找回。</div>';
  }
  document.getElementById('mask').classList.add('show');
}

function closeModal(){
  document.getElementById('mask').classList.remove('show');
  document.getElementById('modal').classList.remove('wide');
  dockReturn();
  MODAL='';
}
document.addEventListener('keydown',function(e){
  if(e.key==='Escape'){
    if(document.getElementById('wel').classList.contains('show'))return;  // 欢迎页不给 Esc 关
    closeModal();
  }
});

/* ---------- 动作 ---------- */
/* 界面版本检测：改了 ui.html / app.js 之后，页面自己提示并刷新，
   免得开着旧页面以为改动没生效。 */
function checkBuild(s){
  /* 后端能力自检：ui.html / app.js 每次请求都重读磁盘（改了刷新就有），
     但 server.py 是**进程启动时加载**的——改了后端不重启，接口就不存在，
     表现是「按钮出现了、点了没反应」。这里主动识别并提示重启。 */
  if(s && s.marks===undefined){
    var box=document.getElementById('backendWarn');
    if(box)box.style.display='flex';
    return;                       // 后端还是旧的，后面的版本号对比没意义
  }
  var b=s&&s.build;
  if(!b)return;
  var old=null;
  try{old=localStorage.getItem('lc_build');}catch(e){}
  if(old===b)return;
  try{localStorage.setItem('lc_build',b);}catch(e){}
  if(old&&old!==b){
    var t=document.getElementById('toast');
    if(t){
      t.textContent='界面已更新，正在刷新…';
      t.classList.add('show');
    }
    setTimeout(function(){location.reload();},1100);
  }
}

async function load(){
  var s;
  try{
    s=await (await fetch('/api/state')).json();
  }catch(e){
    toast('连不上看板服务，5 秒后自动重试…');
    setTimeout(load,5000);
    return;
  }
  STATE=s; TODAY=s.today;
  checkBuild(s);
  renderStats(s);
  renderBoard(s);
  // 首次访问：弹欢迎页引导设置计划
  if(!s.setupDone && !document.getElementById('wel').classList.contains('show')){
    openWelcome(0);
  }
}
async function toggle(di,ti){
  /* 勾选只影响这一行的样式：原地翻转，不重建题板（重建会让整张卡闪一下） */
  var row=document.querySelector('.task[data-di="'+di+'"][data-ti="'+ti+'"]');
  var optimistic=row?!row.classList.contains('done'):false;
  if(row)row.classList.toggle('done',optimistic);
  var j;
  try{
    j=await post('/api/toggle',{day:di,index:ti});
    if(!j.ok)throw new Error('toggle failed');
  }catch(e){
    if(row)row.classList.toggle('done',!optimistic);   // 失败回滚
    toast('操作失败，请重试');
    return;
  }
  STATE=j.state;
  var t=(STATE.board[di]||{}).tasks?STATE.board[di].tasks[ti]:null;
  if(row)row.classList.toggle('done',!!(t&&t.checked));
  var ub=document.getElementById('undoBtn');
  if(ub){
    ub.disabled=!STATE.canUndo;
    ub.setAttribute('data-tip',STATE.canUndo?'撤销上一步操作':'没有可撤销的操作');
  }
}
async function swap(di,ti){
  var j=await post('/api/swap',{day:di,index:ti});
  if(!j.ok){
    toast(j.err==='no_candidate'
      ? '没有可换的题了 —— 这个题单的题已全部排进计划，题池也没有备用题'
      : '换题失败');
    return;
  }
  toast('已换一道题');load();
}
async function markPre(di,ti){
  var j=await post('/api/markpre',{day:di,index:ti});
  if(!j.ok){
    toast(j.err==='already'?'这题已经标记过了':'标记失败');
    return;
  }
  var st=j.state||{};
  toast('已标记「之前做过」· 计划缩短为 '+st.totalDays+' 天');
  load();
}
async function addOne(di){
  var j=await post('/api/add',{day:di,n:1});
  if(!j.ok){
    toast(j.err==='no_candidate'
      ? '没有可加的题了 —— 题池已空，可导入新题单补充'
      : '加题失败');
    return;
  }
  toast('已加 1 题');load();
}
async function submit(di){
  var j=await post('/api/submit',{day:di});
  if(j.added===0&&j.carried===0){toast('还没勾选任何题');return;}
  load();
  showSettle(j);
}

/* ============ 结算页 ============
   提交后弹出来的那一屏：这次做完了什么、难度分布、以及记录记到哪一天。
   当天全部完成时，统计最上方多一条庆祝横幅，主按钮变「挑战自我」
   （加一道题继续做）；没完成时主按钮换成鼓励词，点击照样回当天题板。 */
function showSettle(j){
  var picked=j.picked||[], n=picked.length;
  var diff={'easy':0,'medium':0,'hard':0};
  picked.forEach(function(t){ var k=t.difficulty||'easy'; if(diff[k]!==undefined)diff[k]++; });
  var DN={easy:'简单',medium:'中等',hard:'困难'};

  // 记录日期：默认记到今天；如果是提前做明天的题，明确说明
  var sameDay=(!j.planDate||j.planDate===j.recDate);
  var head=n===0?'今天没做新题':(n===1?'完成 1 道题':'完成 '+n+' 道题');
  var sub;
  if(n===0){
    sub='勾的题都已经在记录里了，去看看别的吧';
  }else if(sameDay){
    sub='记录到 '+md(j.recDate)+'，已计入完成与日历';
  }else{
    sub='本该是 '+md(j.planDate)+' 的题，做于 '+md(j.recDate)+'，<b>计入今天</b>的完成量与日历';
  }

  /* 庆祝判定：这一交把当天板面上的题全收了（没顺延、也没剩题）。
     「挑战自我」加题后再交一次也走这里——carried=0 一样庆祝。 */
  var allDone=!j.carried && !j.remain;

  /* 当天的总完成量 / 第几天：交完后板面已清空，从新 state 里按计划日期找回那天 */
  var dayB=null;
  if(j.state&&j.state.board){
    for(var bi=0;bi<j.state.board.length;bi++){
      var bb=j.state.board[bi];
      if(!bb.extra&&bb.date===(j.planDate||'')){dayB=bb;break;}
    }
  }
  var dTotal=dayB?(dayB.completed||0):n;
  var dNo=dayB?(dayB.dayIndex+1):0;
  var st=STATE&&STATE.stats?STATE.stats:{};

  var h='<div class="settle">';
  if(allDone){
    h+='<div class="scele">'+
      '<div class="sc-em">🎉</div>'+
      '<div class="sc-t">今天已全部完成！</div>'+
      '<div class="sc-s">第 '+dNo+' 天 · 完成 <b>'+dTotal+'</b> 题'+
        (st.streak>1?' · 连续刷题 <b>'+st.streak+'</b> 天':'')+'</div>'+
      '</div>';
  }
  h+='<div class="shead"><div class="stitle">'+head+'</div>'+
    '<div class="ssub">'+sub+'</div></div>';

  if(n>0){
    h+='<div class="sdiff">'+
      ['easy','medium','hard'].map(function(k){
        if(!diff[k])return '';
        return '<span class="sd"><i style="background:'+
          ({easy:'#5EEAD4',medium:'#FBBF6E',hard:'#FB8A8A'})[k]+'"></i>'+
          DN[k]+' '+diff[k]+'</span>';}).join('')+
      '</div>';
    h+='<div class="slist">'+picked.map(function(t){
      return '<div class="srow"><span class="snum">#'+t.id+'</span>'+
        '<span class="snm">'+esc(t.name)+'</span>'+
        (t.category?'<span class="scat">'+esc(t.category)+'</span>':'')+
        '<span class="sdg '+(t.difficulty||'easy')+'">'+DN[t.difficulty||'easy']+'</span></div>';
    }).join('')+'</div>';
  }

  // 顺延/ 补做情况
  var tail=[];
  if(j.carried>0)tail.push(j.carried+' 题没勾，已顺延到'+(j.extra>0?'补做日':'第二天'));
  if(j.extra>0)tail.push(j.extra+' 题超出上限，挪到计划末尾的补做日');
  if(tail.length){
    h+='<div class="scar">'+tail.map(esc).join(' · ')+'</div>';
  }

  // 累计进度
  var st=STATE&&STATE.stats?STATE.stats:{};
  h+='<div class="sstat">'+
     '<div><b>'+(j.state?j.state.doneCount:'-')+'</b> 题已完成</div>'+
     '<div><b>'+(j.state?Math.max(0,j.state.target-(j.state?j.state.doneCount:0)):'-')+'</b> 题待做</div>'+
     '</div>';

  /* 底部按钮：
     全部完成 → 「⚔ 挑战自我」：关弹窗给当天加一道题，想多做题只能这么加
     没完成   → 鼓励词（还差 N 题 · 一鼓作气），点击关弹窗回当天题板 */
  var primary;
  if(allDone){
    primary='<button class="sbtn primary" onclick="settleChallenge()">⚔ 挑战自我</button>';
  }else if(j.carried>0){
    primary='<button class="sbtn primary" onclick="settleBack()">还差 '+j.carried+
      ' 题 · 一鼓作气 💪</button>';
  }else{
    primary='<button class="sbtn primary" onclick="settleBack()">继续把今天的题做完 →</button>';
  }
  h+='<div class="sbtns">'+
     '<button class="sbtn ghost" onclick="closeSettle()">留在这儿</button>'+
     primary+
     '</div></div>';

  var m=document.getElementById('settleMask');
  var box=document.getElementById('settleBox');
  if(box)box.innerHTML=h;
  if(m)m.classList.add('show');
  if(allDone){
    /* 撒一把纸屑（复用奖杯那套粒子），等弹窗入场动画起来再撒 */
    setTimeout(function(){
      var el=document.querySelector('#settleBox .scele');
      if(el)trophySparks(el);
    },150);
  }
}

function closeSettle(){
  var m=document.getElementById('settleMask');
  if(m)m.classList.remove('show');
}

/* 「一鼓作气 / 继续做完」：关掉结算页，视口带回当天题板 */
function settleBack(){
  closeSettle();
  var b=document.getElementById('board');
  if(b&&b.scrollIntoView)b.scrollIntoView({behavior:'smooth',block:'center'});
  var mk=document.querySelector('.submit:not([disabled])');
  if(mk)setTimeout(function(){mk.focus();},260);
}

/* 「挑战自我」：今天已全做完，想继续做只能「+ 加一题」——
   关掉结算页、给当天加一道、视口带回题板（不翻第二天的卡） */
function settleChallenge(){
  closeSettle();
  var s=STATE,di=-1;
  if(s&&s.board){
    for(var i=0;i<s.board.length;i++){
      if(!s.board[i].extra&&s.board[i].date===s.today){di=i;break;}
    }
  }
  if(di>=0)addOne(di);
  var b=document.getElementById('board');
  if(b&&b.scrollIntoView)b.scrollIntoView({behavior:'smooth',block:'center'});
}

async function expand(){
  var j=await post('/api/expand');
  if(!j.ok){toast('已经展开到最后一天了');return;}
  toast('已展开下一天 · 可以提前做');load();
}
async function resetDay(di){
  if(!confirm('把这一天恢复成当天的原始题目？\n\n勾选、换题、加题都会还原；顺延（补做）进来的题会保留。\n\n确定继续吗？'))return;
  var j=await post('/api/resetday',{day:di});
  if(!j.ok){toast('重置失败');return;}
  toast('已重置');load();
}
async function undo(){
  var j=await post('/api/undo');
  if(!j.ok){toast('没有可撤销的操作');return;}
  toast('已撤销上一步');load();
}
document.addEventListener('keydown',function(e){
  if((e.ctrlKey||e.metaKey)&&e.key==='z'){e.preventDefault();undo();}
});

/* ---------- 周视图 ---------- */
function renderWeekly(s){
  var w=s.weekly||{};
  var days=w.thisWeek||[];
  var mx=Math.max.apply(null,[1].concat(days.map(function(x){return x.count;})));
  document.getElementById('wkTotal').textContent=w.thisWeekTotal||0;
  var dl=document.getElementById('wkDelta');
  if(w.delta==null||w.lastWeekTotal===0){
    dl.textContent='上周 '+w.lastWeekTotal+' 题'; dl.style.color='#9CA3AF';
  }else if(w.delta>0){
    dl.textContent='↑ 比上周多 '+w.delta+'%'; dl.style.color='#059669';
  }else if(w.delta<0){
    dl.textContent='↓ 比上周少 '+Math.abs(w.delta)+'%'; dl.style.color='#DC2626';
  }else{
    dl.textContent='与上周持平'; dl.style.color='#6B7280';
  }
  var box=document.getElementById('wk');
  box.innerHTML='';
  days.forEach(function(x){
    var d=document.createElement('div');
    var cls='wcell';
    if(!x.count)cls+=' zero';
    if(x.future)cls+=' future';
    if(x.today)cls+=' today';
    if(x.count&&x.count===mx&&mx>0)cls+=' best';
    d.className=cls;
    d.innerHTML='<div class="n">'+(x.future?'·':x.count)+'</div><div class="l">'+x.label+'</div>';
    d.setAttribute('data-tip','<div class="tt">'+md(x.date)+' 周'+x.label+'</div><div class="tr">'+x.count+' 题</div>');
    box.appendChild(d);
  });
  document.getElementById('wkNote').textContent=
    '统计区间 '+String(w.weekStart||'').slice(5)+' ~ '+String(w.weekEnd||'').slice(5)+'（仅统计真正做的新题）';
  // 侧栏入口摘要
  var nav=document.getElementById('navWk');
  if(nav)nav.textContent='本周 '+(w.thisWeekTotal||0)+' 题'+
    (w.delta==null?'':'（'+(w.delta>0?'↑':'↓')+Math.abs(w.delta)+'%）');
}

/* ---------- 提醒设置 ---------- */
function renderReminders(s){
  var r=s.reminders||{enabled:false,slots:[]};
  document.getElementById('remEnabled').checked=!!r.enabled;
  var navR=document.getElementById('navRem');
  if(navR){
    var ns=(r.slots||[]).length;
    navR.textContent=r.enabled?('每日 '+ns+' 次'):'未开启';
  }
  var box=document.getElementById('slotBox');
  box.innerHTML='';
  (r.slots||[]).forEach(function(sl,i){
    var row=document.createElement('div');
    row.className='slotline';
    row.innerHTML='<input type="time" value="'+esc(sl.time)+'" data-i="'+i+'">'+
      '<span>'+esc(sl.label||'提醒')+'</span>'+
      '<button class="rm" data-i="'+i+'" data-tip="删除">✕</button>';
    box.appendChild(row);
  });
  if(!(r.slots||[]).length){
    box.innerHTML='<div class="remnote" style="margin:8px 0 2px">还没设提醒时间，点下面「加一个时间」</div>';
  }
  box.querySelectorAll('input[type=time]').forEach(function(inp){
    inp.onchange=function(){saveSlots();};
  });
  box.querySelectorAll('.rm').forEach(function(b){
    b.onclick=function(){removeSlot(+b.dataset.i);};
  });
}
function collectSlots(){
  var out=[];
  document.querySelectorAll('#slotBox .slotline').forEach(function(row){
    var t=row.querySelector('input[type=time]').value;
    var lbl=row.querySelector('span').textContent;
    if(t)out.push({time:t,label:lbl});
  });
  return out;
}
async function saveSlots(slots){
  var arr=slots||collectSlots();
  var j=await post('/api/remind',{slots:arr,enabled:document.getElementById('remEnabled').checked});
  if(j.ok){STATE=j.state;renderReminders(j.state);toast('提醒时间已保存');}
}
async function toggleRemind(on){
  await saveSlots();
  toast(on?'已开启每日提醒':'已关闭每日提醒');
}
function addSlot(){
  var slots=collectSlots();
  if(slots.length>=6){toast('最多 6 个提醒时间');return;}
  var used={};slots.forEach(function(x){used[x.time]=1;});
  var cand=['09:00','12:00','15:00','18:30','21:00','22:30'].filter(function(t){return !used[t];});
  slots.push({time:cand[0]||'12:00',label:'提醒'});
  slots.sort(function(a,b){return a.time<b.time?-1:1;});
  saveSlots(slots);
}
function removeSlot(i){
  var slots=collectSlots();
  slots.splice(i,1);
  saveSlots(slots);
}
async function testRemind(){
  var j=await post('/api/testremind');
  if(j.ok){toast('测试通知已弹出，看右下角');}
  else{toast('通知发送失败：'+(j.msg||'未知原因'));}
}

/* ---------- 导出 ---------- */
async function resetPlan(mode){
  var msg = mode==='all'
    ? '「恢复默认」会清空本题单的全部进度，并把总题数、每天题数一起重置，回到最初的初始化向导。\n\n确定继续吗？'
    : '「重置进度」会清空本题单的所有完成记录（含「之前做过」标记），从今天重新开始。\n\n总题数和每天题数保持不变。\n\n确定继续吗？';
  if(!confirm(msg))return;
  var j=await post('/api/resetplan',{mode:mode});
  if(j&&j.ok){
    closeModal();
    await load();
    toast(mode==='all'?'已恢复默认设置':'进度已重置，可用撤销找回');
  }else{
    toast('重置失败：'+((j&&j.msg)||'未知错误'));
  }
}

/* 重新开启一轮：本轮记录归档保留，不是清空 */
async function restartRound(){
  if(!STATE)return;
  var s=STATE;
  var msg='「重新开始一轮」会把本轮（第 '+(s.round||1)+' 轮）已完成的 '+
    (s.doneCount||0)+' 题记录**归档保存**，然后从今天重新排第一天。\n\n'+
    '归档的记录不会丢，可在「往期记录」里回看每轮做了哪些题。\n\n确定继续吗？';
  if(!confirm(msg))return;
  var j=await post('/api/restartplan',{});
  if(j&&j.ok){
    closeModal();
    await load();
    toast('已开启第 '+(j.state.round||1)+' 轮 · 上一轮记录已归档');
  }else{
    toast('操作失败：'+((j&&j.msg)||'未知错误'));
  }
}

/* 查看往期轮次做了哪些题 */
function openRounds(){
  var s=STATE;
  if(!s)return;
  var rs=s.rounds||[];
  if(!rs.length){toast('还没有往期记录');return;}
  var nameMap={};
  (s.tasks||[]).forEach(function(t){nameMap[t.id]=t.name;});

  var h='';
  rs.slice().reverse().forEach(function(r){
    h+='<div class="psec">第 '+r.no+' 轮 · '+r.count+' 题</div>'+
       '<div class="fhelp" style="margin:-4px 0 8px">'+r.from+' → '+r.to+'</div>'+
       '<div style="max-height:210px;overflow:auto;border:1px solid var(--line);'+
       'border-radius:11px;padding:8px 11px;margin-bottom:16px">';
    (r.done||[]).forEach(function(d){
      h+='<div style="font-size:12px;padding:2.5px 0;color:var(--ink-2)">'+
         '#'+d.id+' '+esc(nameMap[d.id]||'')+
         '<span style="opacity:.5;margin-left:6px">'+(d.date||'')+'</span>'+
         (d.pre?'<span style="color:var(--iris-d);font-weight:800;margin-left:6px">之前做过</span>':'')+
         '</div>';
    });
    h+='</div>';
  });

  dockReturn();
  MODAL='rounds';
  document.getElementById('mTitle').innerHTML=
    '往期轮次<span class="msub">'+esc(s.activeName||'')+'</span>';
  document.getElementById('mBody').innerHTML=h;
  document.getElementById('mask').classList.add('show');
}

function exportData(fmt){
  var a=document.createElement('a');
  a.href='/api/export?fmt='+fmt;
  a.download='leetcode-progress.'+fmt;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  toast('已开始下载 '+fmt.toUpperCase());
}

/* ---------- 欢迎页 / 计划设置 ---------- */
function safePlan(){
  var pl=(STATE&&STATE.plan)||{};
  var all=pl.allTotal||100;
  return {
    total:(pl.limit||all),
    per:pl.perDay||4,
    days:pl.days||Math.ceil(all/(pl.perDay||4))
  };
}
function planNums(){
  var t=parseInt((document.getElementById('welTotal')||{}).value,10);
  var d=parseInt((document.getElementById('welPer')||{}).value,10);
  return {total:isNaN(t)?100:t, per:isNaN(d)?4:d};
}
function calcDays(){
  var n=planNums();
  var per=Math.max(1,n.per);
  var all=(STATE&&STATE.plan&&STATE.plan.allTotal)||n.total;
  var total=Math.min(Math.max(1,n.total), all);
  return {total:total, per:per, days:Math.ceil(total/per), all:all};
}
function endDateStr(days){
  var d=new Date(); d.setDate(d.getDate()+Math.max(0,days-1));
  return (d.getMonth()+1)+'月'+d.getDate()+'日';
}

function welRender(){
  var el=document.getElementById('welBody');
  var all=(STATE&&STATE.plan&&STATE.plan.allTotal)||100;
  var nm=(STATE&&STATE.activeName)||'LeetCode 100';
  var p=safePlan();

  if(WELSTEP===0){
    el.innerHTML=
      '<div class="welhi">欢迎使用 · 刷题看板</div>'+
      '<div class="weltitle">先定个计划，<br>再开始刷题</div>'+
      '<div class="weldesc">'+
        '当前题单 <b>'+esc(nm)+'</b> 共 <b>'+all+' 题</b>。'+
        '设定总题数和每天做几道，看板会自动把题目排到每一天，'+
        '没做完的还会顺延到第二天补回来。'+
      '</div>'+
      '<div class="welsec"><span class="n">1</span>设定你的刷题计划</div>'+
      '<div class="setgrid">'+
        '<div class="setcell"><label>总共刷多少题</label>'+
          '<input type="number" id="welTotal" value="'+p.total+'" min="1" max="'+all+'" '+
            'oninput="updCalc()"><span class="unit">题（题库共 '+all+'）</span></div>'+
        '<div class="setcell"><label>每天做几道</label>'+
          '<input type="number" id="welPer" value="'+p.per+'" min="1" max="50" '+
            'oninput="updCalc()"><span class="unit">题 / 天</span></div>'+
        '<div class="setcell"><label>预计用时</label>'+
          '<input type="text" id="welDays" value="'+p.days+'" readonly>'+
          '<span class="unit">天</span></div>'+
      '</div>'+
      '<div class="welcal" id="welCal"></div>'+
      '<div class="welacts">'+
        '<button class="later" onclick="welSkip()">稍后再设</button>'+
        '<button class="go" onclick="welNext()">下一步 →</button>'+
      '</div>'+
      '<div class="welnav"><i class="on"></i><i></i></div>';
    updCalc();
  }else{
    el.innerHTML=
      '<div class="welhi">用起来很简单</div>'+
      '<div class="weltitle">四个动作，覆盖全部流程</div>'+
      '<div class="guides">'+
        '<div class="guide"><div class="ic">✓</div><div>'+
          '<div class="gt">勾选做完的题</div>'+
          '<div class="gd">点题目卡片就能勾上。没做完也可以直接点「确定完成」，'+
          '剩下的题会自动顺延到第二天补做。</div></div></div>'+
        '<div class="guide"><div class="ic">⇄</div><div>'+
          '<div class="gt">做过的题可以「换一题」</div>'+
          '<div class="gd">某题以前刷过，点「换一题」从题库换一道没做过的，'+
          '计入总题数但不占当天做题量。</div></div></div>'+
        '<div class="guide"><div class="ic">⤢</div><div>'+
          '<div class="gt">左侧看进度、切题单</div>'+
          '<div class="gd">日历热力图看每天做了多少，点「展开全部」按分类看整份题单，'+
          '还能自己新建题单（比如剑指 Offer）。</div></div></div>'+
        '<div class="guide"><div class="ic">↶</div><div>'+
          '<div class="gt">点错了就撤销</div>'+
          '<div class="gd">工具栏「↶ 撤销」或 Ctrl+Z 都能回退，最多 30 步。</div></div></div>'+
      '</div>'+
      '<div class="welacts">'+
        '<button class="later" onclick="welBack()">← 返回</button>'+
        '<button class="go" onclick="welFinish()">进入看板</button>'+
      '</div>'+
      '<div class="welnav"><i></i><i class="on"></i></div>';
  }
}

function updCalc(){
  var c=calcDays();
  var el=document.getElementById('welDays');
  if(el)el.value=c.days;
  var cal=document.getElementById('welCal');
  if(!cal)return;
  var per=c.per;
  var lvl=per<=3?'轻松':per<=5?'适中':per<=8?'偏紧':'很硬核';
  var bg=per<=5?'#F0FDF4':per<=8?'#FEF3C7':'#FEF2F2';
  var bd=per<=5?'#A7F3D0':per<=8?'#FDE68A':'#FECACA';
  var col=per<=5?'#065F46':per<=8?'#92400E':'#991B1B';
  cal.style.background=bg; cal.style.borderColor=bd; cal.style.color=col;
  cal.innerHTML='按这个节奏，<b>'+c.total+'</b> 题要做 <b>'+c.days+'</b> 天，'+
    '平均每天 <b>'+per+'</b> 题（强度：'+lvl+'）。<br>'+
    '<span style="font-size:12.5px;opacity:.85">'+
    '从今天算起，预计 <b>'+endDateStr(c.days)+'</b> 完成。</span>';
}

function openWelcome(step){
  WELSTEP=(step==null)?0:step;
  welRender();
  document.getElementById('wel').classList.add('show');
}
function closeWelcome(){document.getElementById('wel').classList.remove('show');}
function welNext(){WELSTEP=1;welRender();}
function welBack(){WELSTEP=0;welRender();}
async function welSkip(){
  await post('/api/welcomeskip');
  closeWelcome();
  toast('已跳过，随时可点「⚙ 修改计划」再设');
  load();
}
/* 回到开场的欢迎引导（计划设置 + 功能说明），入口在计划栏「↺ 新手引导」 */
async function replayWelcome(){
  await post('/api/welcomereset');
  await load();          // load() 检测到 setupDone=false 会自动弹欢迎页
}
async function welFinish(){
  var c=calcDays();
  var lim=(c.total>=c.all)?0:c.total;
  var j=await post('/api/setplan',{limit:lim,perDay:c.per,reset:true,markSetup:true});
  if(!j.ok){toast(j.msg||'设置失败');return;}
  STATE=j.state;
  closeWelcome();
  renderStats(j.state);renderBoard(j.state);
  toast('计划已设定：'+c.total+' 题 / 每天 '+c.per+' 题 / 共 '+c.days+' 天');
}

/* ---------- 修改计划 ---------- */
function openPlanSetup(){
  if(!STATE)return;
  dockReturn();
  MODAL='plan';
  var all=(STATE.plan&&STATE.plan.allTotal)||100;
  var p=safePlan();
  document.getElementById('mTitle').innerHTML='修改计划<span class="msub">'+
    esc(STATE.activeName||'')+'</span>';
  document.getElementById('modal').classList.remove('wide');
  document.getElementById('mBody').innerHTML=
    '<div class="setgrid" style="margin-bottom:14px">'+
      '<div class="setcell"><label>总共刷多少题</label>'+
        '<input type="number" id="psTotal" value="'+p.total+'" min="1" max="'+all+'" '+
          'oninput="updPlanCalc()"><span class="unit">题（题库共 '+all+'）</span></div>'+
      '<div class="setcell"><label>每天做几道</label>'+
        '<input type="number" id="psPer" value="'+p.per+'" min="1" max="50" '+
          'oninput="updPlanCalc()"><span class="unit">题 / 天</span></div>'+
      '<div class="setcell"><label>预计用时</label>'+
        '<input type="text" id="psDays" value="'+p.days+'" readonly>'+
        '<span class="unit">天</span></div>'+
    '</div>'+
    '<div class="welcal" id="psCal" style="margin-bottom:16px"></div>'+
    '<div class="fhelp" style="margin-bottom:14px">'+
      '修改后会<b>重新排期</b>：已展开的天会重置成新计划的第一天，'+
      '但<b>已完成记录会保留</b>（日历热力图和统计不受影响）。'+
    '</div>'+
    '<div class="fbtns">'+
      '<button class="cancel" onclick="closeModal()">取消</button>'+
      '<button class="ok" onclick="savePlan()">保存计划</button>'+
    '</div>';
  document.getElementById('mask').classList.add('show');
  updPlanCalc();
}
function planSetupNums(){
  var t=parseInt(document.getElementById('psTotal').value,10);
  var d=parseInt(document.getElementById('psPer').value,10);
  return {total:isNaN(t)?100:t, per:isNaN(d)?4:d};
}
function updPlanCalc(){
  var n=planSetupNums();
  var all=(STATE.plan&&STATE.plan.allTotal)||100;
  var total=Math.min(Math.max(1,n.total),all);
  var per=Math.max(1,n.per);
  var days=Math.ceil(total/per);
  document.getElementById('psDays').value=days;
  var cal=document.getElementById('psCal');
  var lvl=per<=3?'轻松':per<=5?'适中':per<=8?'偏紧':'很硬核';
  var bg=per<=5?'#F0FDF4':per<=8?'#FEF3C7':'#FEF2F2';
  var bd=per<=5?'#A7F3D0':per<=8?'#FDE68A':'#FECACA';
  var col=per<=5?'#065F46':per<=8?'#92400E':'#991B1B';
  cal.style.background=bg; cal.style.borderColor=bd; cal.style.color=col;
  cal.innerHTML='按这个节奏，<b>'+total+'</b> 题要做 <b>'+days+'</b> 天，'+
    '平均每天 <b>'+per+'</b> 题（强度：'+lvl+'）。<br>'+
    '<span style="font-size:12.5px;opacity:.85">预计 <b>'+endDateStr(days)+'</b> 完成。</span>';
}
async function savePlan(){
  var n=planSetupNums();
  var all=(STATE.plan&&STATE.plan.allTotal)||100;
  var total=Math.min(Math.max(1,n.total),all);
  var per=Math.max(1,n.per);
  var lim=(total>=all)?0:total;
  var j=await post('/api/setplan',{limit:lim,perDay:per,reset:true});
  if(!j.ok){toast(j.msg||'设置失败');return;}
  STATE=j.state;
  closeModal();
  renderStats(j.state);renderBoard(j.state);
  toast('计划已更新：'+total+' 题 / 每天 '+per+' 题 / 共 '+Math.ceil(total/per)+' 天');
}

/* ---------- 跨天自动刷新 ----------
   页面开着过零点时，每分钟问一次服务器「今天几号」。
   日期变了 -> 服务端已经自动结算昨天的账 -> 刷新页面就是新的一天。
   （不这样做的话，页面会一直停在昨天的题板上，直到手动 F5） */
function watchNewDay(){
  setInterval(function(){
    fetch('/api/state').then(function(r){return r.json();}).then(function(s){
      if(s&&s.today&&TODAY&&s.today!==TODAY){
        var t=document.getElementById('toast');
        if(t){
          t.textContent='新的一天已开始，正在刷新…';
          t.classList.add('show');
        }
        setTimeout(function(){location.reload();},1200);
      }
    }).catch(function(){});
  },60000);
}

initTip();
load();
watchNewDay();
