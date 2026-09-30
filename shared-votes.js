// Loaded after the generated gallery script. The database is authoritative.
(() => {
  const API = (window.FIGLIB_VOTE_API || '').replace(/\/$/, '');
  const TOKEN_KEY = 'figlib_shared_identity_v1';
  const SIGNAL_KEY = 'figlib_shared_update_v1';
  const records = new Map(D.map(r => [r.id, r]));
  const baseScores = new Map(D.map(r => [r.id, r.ai_score ?? r.score]));
  let legacy = {};
  try { legacy = JSON.parse(localStorage.getItem('figlib_votes_v1') || '{}'); } catch {}
  if (!legacy || typeof legacy !== 'object' || Array.isArray(legacy)) legacy = {};
  legacy = Object.fromEntries(Object.entries(legacy).filter(([id,v])=>records.has(id)&&[1,-1].includes(v)));
  let token, busy = false, ready = false, refreshing = false, sequence = 0, skipUntil = 0, lastSnapshot = '';
  const status = document.createElement('span');
  status.id = 'vote-status'; status.role = 'status'; status.style.cssText = 'font-size:12px;color:var(--mute)';
  const retry = document.createElement('button'); retry.textContent = '重试连接'; retry.hidden = true;
  const migrate = document.createElement('button');
  migrate.textContent = `同步本机旧投票 (${Object.keys(legacy).length})`;
  migrate.hidden = !Object.keys(legacy).length;
  document.querySelector('header').append(status, retry, migrate);
  const help = document.createElement('span');
  help.textContent = '匿名投票按浏览器识别 · 改票/撤票即时保存 · 他人票数约10秒同步';
  help.style.cssText = 'font-size:11px;color:var(--mute)'; document.querySelector('header').append(help);
  V = {};
  voteBar = r => {
    const v = V[r.id] || 0;
    return `<div class="vote" data-id="${esc(r.id)}"><button class="up${v===1?' on':''}" ${!ready||busy?'disabled':''} aria-pressed="${v===1}">👍 好图</button><button class="down${v===-1?' on':''}" ${!ready||busy?'disabled':''} aria-pressed="${v===-1}">👎</button><span class="hv">大家 +${r.up||0} / −${r.down||0}</span></div>`;
  };
  function message(text, failed=false) { status.textContent=text; status.style.color=failed?'#c9544f':'var(--mute)'; }
  function lock() {
    document.querySelectorAll('.vote button').forEach(b=>b.disabled=!ready||busy);
    migrate.disabled=!ready||busy;
  }
  function apply(totals, mine) {
    const snapshot=JSON.stringify([totals,mine]);
    if (snapshot===lastSnapshot) { lock(); return; }
    V=Object.fromEntries(Object.entries(mine).filter(([id,v])=>records.has(id)&&[1,-1].includes(v)));
    for (const r of D) {
      r.up=totals[r.id]?.up||0; r.down=totals[r.id]?.down||0;
      const net=r.up-r.down;
      r.board=net>=2?'red':net<=-2?'black':'';
      r.score=Math.max(1,Math.min(5,baseScores.get(r.id)+(net>=2?1:net<=-2?-1:0)));
    }
    lastSnapshot=snapshot; render(); lock();
  }
  async function api(path, votes) {
    const res=await fetch(API+path,{method:votes?'PUT':'GET',cache:'no-store',signal:AbortSignal.timeout(20000),headers:{...(path==='/summary'?{}:{Authorization:'Bearer '+token}),...(votes?{'Content-Type':'application/json'}:{})},...(votes?{body:JSON.stringify({votes})}:{})});
    if (!res.ok) throw new Error(res.status===429?'操作频繁，请一分钟后重试':'投票服务连接失败，请重试');
    return res.json();
  }
  async function refresh(includeMine=false) {
    if (busy||refreshing||(Date.now()<skipUntil)) return;
    refreshing=true; const seq=sequence;
    try {
      const [data,mine]=await Promise.all([api('/summary'),includeMine?api('/mine'):Promise.resolve({votes:V})]);
      if (seq!==sequence||busy) return;
      ready=true; retry.hidden=true; apply(data.totals,mine.votes);
      message('共享投票已连接 · '+new Date().toLocaleTimeString());
    } catch (e) {
      retry.hidden=false; message(ready?'同步暂时失败，显示上次票数；点击重试':'共享投票未连接，暂不能投票',true);
    } finally { refreshing=false; lock(); }
  }
  async function submit(votes) {
    if (!ready||busy) return false;
    busy=true; sequence++; lock(); message('正在保存投票…');
    try {
      const data=await api('/votes',votes);
      skipUntil=Date.now()+6000;
      apply(data.totals,data.votes);
      try {localStorage.setItem(SIGNAL_KEY,crypto.randomUUID());} catch {}
      message('投票已保存 · 大家共享');
      return true;
    } catch(e) {
      retry.hidden=false; message('未确认保存成功，请重试；重复提交不会重复计票',true);
      return false;
    } finally { busy=false; lock(); }
  }
  // Capture voting clicks so the original local-only handler never records a second vote.
  document.querySelector('#grid').addEventListener('click',async e=>{
    const b=e.target.closest('.vote button'); if(!b)return;
    e.preventDefault();e.stopImmediatePropagation();
    if(!ready||busy)return;
    const id=b.parentNode.dataset.id, value=b.classList.contains('up')?1:-1;
    await submit({[id]:V[id]===value?0:value});
  },true);
  migrate.onclick=async()=>{
    if(!confirm('将这个浏览器中以前的点赞/点踩同步到共享图库？相同图片将以旧投票覆盖你当前的选择。'))return;
    const entries=Object.entries(legacy);
    for(let i=0;i<entries.length;i+=40) if(!await submit(Object.fromEntries(entries.slice(i,i+40))))return;
    migrate.hidden=true;
    // Keep the original local data as a backup; only hide the migration offer for this identity.
    try {localStorage.setItem('figlib_migrated_'+token,'1');}catch{}
  };
  retry.onclick=()=>refresh(true);
  try {
    token=localStorage.getItem(TOKEN_KEY);
    if(!/^[a-f0-9]{64}$/.test(token||'')) {
      token=[...crypto.getRandomValues(new Uint8Array(32))].map(b=>b.toString(16).padStart(2,'0')).join('');
      localStorage.setItem(TOKEN_KEY,token);
    }
    if(localStorage.getItem('figlib_migrated_'+token))migrate.hidden=true;
  } catch {
    message('浏览器禁止本地存储，无法保存匿名身份；请允许存储后刷新',true); render();lock();return;
  }
  render();lock();
  if(!API){message('共享投票服务尚未配置',true);return;}
  message('正在连接共享投票…');refresh(true);
  setInterval(()=>{if(!document.hidden)refresh();},10000);
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh(true);});
  window.addEventListener('storage',e=>{if(e.key===SIGNAL_KEY)refresh(true);});
})();
