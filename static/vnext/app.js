'use strict';
/* Presentation only. Financial values, qualification and exports come from one snapshot. */
(() => {
  const UX=window.ThemeScopeUI;
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? 'Unavailable').replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));
  const valid = value => value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));
  const number = (value, digits = 2) => valid(value) ? Number(value).toLocaleString('en-US', {minimumFractionDigits:digits, maximumFractionDigits:digits}) : '—';
  const percent = (value, scale = 1, signed = false) => valid(value) ? `${signed && Number(value) > 0 ? '+' : ''}${number(Number(value) * scale)}%` : '—';
  const points = value => valid(value) ? `${Number(value) > 0 ? '+' : ''}${number(Number(value) * 100)} pp` : '—';
  const money = value => valid(value) ? `$${number(value)}` : '—';
  const marketName = value => String(value||'Unclassified').replace(/\b[a-z]/g,c=>c.toUpperCase());
  const iconPaths = {back:'M19 12H5m6-6-6 6 6 6',up:'M6 18 18 6M6 6h12v12',down:'M6 6l12 12M6 18h12V6',flat:'M4 12h16m-4-4 4 4-4 4M8 8l-4 4 4 4',overview:'M4 4h16v16H4zM4 10h16M12 10v10',themes:'m12 3 9 9-9 9-9-9 9-9zM8 12l4-4 4 4-4 4-4-4z',primary:'M10 17a7 7 0 1 0 0-14 7 7 0 0 0 0 14zm5-2 6 6',saved:'m12 3 2.8 5.8 6.4.9-4.6 4.5 1.1 6.4-5.7-3-5.7 3 1.1-6.4L2.8 9.7l6.4-.9L12 3z',methodology:'M5 5h14M5 10h14M5 15h9M5 20h9',orbit:'M20 12a8 8 0 1 1-8-8M12 4v8h8'};
  const icon = key => `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${iconPaths[key] || iconPaths.flat}"/></svg>`;
  const tone = value => /bullish|positive|long/i.test(value || '') ? 'positive' : /bearish|negative|short/i.test(value || '') ? 'negative' : /mixed/i.test(value || '') ? 'mixed' : 'neutral';
  const signTone = value => !valid(value) || Number(value) === 0 ? 'neutral' : Number(value) > 0 ? 'positive' : 'negative';
  const symbol = value => icon(tone(value) === 'positive' ? 'up' : tone(value) === 'negative' ? 'down' : 'flat');
  const state = value => `<span class="state ${tone(value)}"><span aria-hidden="true">${symbol(value)}</span>${esc(value || 'Unavailable')}</span>`;
  const publicSnapshot = window.THEMESCOPE_STATIC_SOURCE?.mode === 'public_snapshot';
  const preview = publicSnapshot || Boolean(window.FIXTURE_SNAPSHOT);
  const savedKey = 'themescope-vnext-watchlist';
  let snapshot = null, snapshotSignature = '', currentStatus = {}, route = '', origin = '#themes', feedbackTimer, requestError = '';
  let initialLoading=true;
  const savedContextKey='themescope-vnext-saved-context';
  let savedContexts={};
  try{const data=JSON.parse(localStorage.getItem(savedContextKey)||'{}');if(data&&typeof data==='object'&&!Array.isArray(data))savedContexts=data;}catch{}
  let watched = [];
  try { const values = JSON.parse(localStorage.getItem(savedKey) || '[]'); if (Array.isArray(values)) watched = [...new Set(values.filter(s => typeof s === 'string' && s.trim()))]; } catch { /* A blocked or malformed browser store must not stop research. */ }
  const ui = {universe:'active', themeSort:'priority', themeDescending:false, selectedTheme:'', selectedTicker:'', selectedTickerTheme:'', candidateMode:'unique', candidateLens:'directional', memberSearch:'', memberRole:'', memberEligibility:'', memberSort:'priority'};
  const positions = new Map(), blobUrls = new Map();
  let inspector = null, inspectorTrigger = '', inspectorOrigin = '', inspectorScroll = 0;
  const inspectorViews = new Map();
  let closingInspector=false;
  let mapSelected='',mapFocusId='',mapResizeTimer;
  let mapWidth = 800;
  const mapHeight = 280, mapPadding = {left:66,right:24,top:24,bottom:50};
  const name = id => snapshot?.themes?.find(t => t.theme_id === id)?.name || id || 'Unavailable';
  const themeHref = id => '#themes/' + encodeURIComponent(id);
  const helpButton = key => `<button type="button" class="metric-help" data-help="${key}" data-focus-key="help:${key}" aria-label="About ${esc(UX.help[key]?.[0]||key)}" aria-expanded="false" aria-controls="metric-tooltip">?</button>`;
  const tickerLink = (ticker,themeId='',lens='') => `<a class="ticker ticker-link" href="#primary?ticker=${encodeURIComponent(ticker)}${themeId?'&context='+encodeURIComponent(themeId):''}${lens?'&lens='+encodeURIComponent(lens):''}" data-inspect-ticker="${esc(ticker)}" data-context-theme="${esc(themeId)}" data-context-lens="${esc(lens)}" data-focus-key="ticker:${esc(ticker)}${themeId?':'+esc(themeId):''}">${esc(ticker)}</a>`;
  const themeLink = (id,lens='directional') => `<a class="theme-link" href="${themeHref(id)}" data-inspect-theme="${esc(id)}" data-context-lens="${esc(lens)}" data-focus-key="theme:${esc(id)}">${esc(name(id))}</a>`;
  const saveButton = (ticker,location,themeId='',lens='') => `<button class="save-button" data-save="${esc(ticker)}" data-save-theme="${esc(themeId)}" data-save-lens="${esc(lens)}" data-focus-key="${esc(location+':'+ticker)}" aria-pressed="${watched.includes(ticker)}" aria-label="${watched.includes(ticker)?'Saved '+esc(ticker)+'; remove from Saved':'Save '+esc(ticker)}">${icon('saved')}<span class="sr-only">${watched.includes(ticker)?'Saved':'Save'}</span></button>`;
  const empty = (title, message, action = '') => `<div class="empty-state"><h3>${esc(title)}</h3><p>${esc(message)}</p>${action}</div>`;
  function focusKey() { return document.activeElement?.dataset?.focusKey; }
  function restoreFocus(key) { if (key) [...(inspector ? $('research-inspector') : document).querySelectorAll(`[data-focus-key="${CSS.escape(key)}"]`)].find(node => !node.closest('[hidden]'))?.focus({preventScroll:true}); }
  function announce(text) {
    clearTimeout(feedbackTimer); $('feedback').textContent = text; $('feedback').classList.add('visible');UX.move($('feedback'),'confirm');
    feedbackTimer = setTimeout(() => $('feedback').classList.remove('visible'), 3200);
  }
  function earningsDates(ticker) { return snapshot?.earnings?.[ticker]?.dates || []; }
  // All-unavailable cannot distinguish disabled, failed, or an empty calendar in this contract.
  function earningsEnabled() { return Object.values(snapshot?.earnings || {}).some(e=>(e?.dates?.length || 0)>0 || e?.status === 'Available'); }
  function earnings(ticker) { const dates = earningsDates(ticker); return dates.length ? dates.map(esc).join('<br>') : `<span class="muted">${snapshot?.earnings?.[ticker]?.status === 'Available' ? 'No reported date' : 'Unavailable'}</span>`; }
  const research = () => snapshot?.research || {};
  const roleName = value => value === 'Core' ? 'Core business' : value === 'Enabler' ? 'Supporting business' : value;
  const roleLabel = value => `<span title="${value === 'Core' ? 'Business directly participates in this theme.' : value === 'Enabler' ? 'Provides products or services that enable this theme.' : ''}">${esc(roleName(value))}</span>`;
  function rankInfo(id) { return themeResearch(id); }
  function rankLabel(id) { const r=rankInfo(id); return valid(r.strength_rank) ? '#' + r.strength_rank : '—'; }
  function rankChange(id) {
    const recent=themeResearch(id).recent,change=recent?.directional_rank_change;
    const value=currentSide()?change:recent?.raw_rank_change;
    const text=valid(value)?Number(value)>0?'Up '+value:Number(value)<0?'Down '+Math.abs(value):'Unchanged':'—';
    const description=recent?.available?`Compared with ${recent.comparison_session}`:UX.comparisonMessage(recent?.reason);
    return `<span title="${esc(description)}">${text}<span class="sr-only"> · ${esc(description)}</span></span>`;
  }

  function prelaunch() { return snapshot?.theme_layer?.state === 'pre_launch_research'; }
  function download(themeId) {
    const text = themeId ? snapshot?.exports?.individual?.[themeId] : snapshot?.exports?.combined;
    if (text === undefined || text === null) return null;
    if (!preview) return themeId ? `/api/exports/${encodeURIComponent(themeId)}.txt` : '/api/exports/combined.txt';
    const key = themeId || '__combined';
    if (!blobUrls.has(key)) blobUrls.set(key, URL.createObjectURL(new Blob([text], {type:'text/plain'})));
    return blobUrls.get(key);
  }
  function themeDownload(themeId) {
    const url = download(themeId);
    return url ? `<a class="button secondary small" href="${esc(url)}" download="Theme.txt">Theme TXT <span aria-hidden="true">↓</span></a>` : '<span class="muted table-note">No research list export for this theme</span>';
  }
  function renderExportMenu() {
    const current=currentResearch();
    const link=(url,label,file,id='')=>url?`<a ${id?`id="${id}"`:''} href="${esc(url)}" download="${esc(file)}" data-export="${esc(label)}">${esc(label)}<span aria-hidden="true">↓</span></a>`:`<span class="export-unavailable">${esc(label)} unavailable</span>`;
    let body=`<p class="menu-title">${current?'TradingView':'Previous research rules'} · ${esc(snapshot?.session||'No snapshot')}</p>`;
    body+=link(download(),current?'Full research list':'Previous rules list',current?'Research.txt':'PreviousResearch.txt','combined');
    const themes=Object.keys(snapshot?.exports?.individual||{});
    if(themes.length)body+=`<details class="theme-files"><summary class="button quiet">Theme files</summary>${themes.map(id=>link(download(id),name(id),'Theme.txt')).join('')}</details>`;
    body+=`<p class="menu-scope">${current?'Full session list in research order. Filters affect this view only.':'Stored under previous research rules. Refresh Data to build the current list.'}</p>`;
    if($('export-options').innerHTML!==body)$('export-options').innerHTML=body;
  }
  function renderLayer() {
    $('fixture-banner').hidden = publicSnapshot || !snapshot?.synthetic_fixture;
    $('public-banner').hidden = !publicSnapshot;
    if (publicSnapshot) $('public-banner').textContent = `Public snapshot · Completed US session ${snapshot.session} · Market data fixed`;
    $('refresh').hidden = publicSnapshot;
    if (publicSnapshot) document.querySelector('.diagnostics summary').textContent = 'Snapshot details';
    const layer = snapshot?.theme_layer || {}, session = snapshot?.session;
    const messages = {
      pre_launch_research:`Pre-launch research · Completed session ${session} · Approved launch membership universe. Official index history begins at the ${layer.launch_rebalance_session} close; first earned session ${layer.first_earned_session}.`,
      pre_launch:'Pre-launch · Official theme indices have not yet initialized.',
      initialized:`Launch close: index initialized at 100 · First earned session ${layer.first_earned_session}. Official index history has just begun.`,
      live:'Official theme history · Completed-session research',
      activation_blocked:'Theme activation blocked · Market context remains available. See Configuration & activation status in Methodology.'
    };
    const routine = ['initialized','live'].includes(layer.state);
    $('lifecycle-detail').hidden = !messages[layer.state];
    $('lifecycle-detail').textContent = messages[layer.state] || '';
    $('theme-layer').hidden = routine || !messages[layer.state];
    $('theme-layer').textContent = messages[layer.state] || '';
    $('blockers').innerHTML = (snapshot?.production_blockers || []).map(b => `<li>${esc(b)}</li>`).join('') || '<li>No activation blockers recorded.</li>';
  }
  const v2 = () => snapshot?.research_v2 || {};
  const themeResearch = id => v2().themes?.[id] || {};
  const researchState = id => UX.themeState(snapshot,id);
  const stateTone = value => ({Leading:'leader',Improving:'improving',Fading:'fading',Lagging:'lagging'})[value] || 'neutral';
  const themeState = id => `<span class="theme-state ${stateTone(researchState(id))}">${esc(researchState(id))}</span>`;
  const researchOrder = id => currentResearch()?(themeResearch(id).research_order_index ?? (v2().theme_order||[]).indexOf(id)):(snapshot?.themes||[]).map(t=>t.theme_id).sort().indexOf(id);
  const currentSide = () => UX.currentSide(snapshot);
  const currentResearch = () => UX.currentContract(snapshot);
  const sideLabel = () => currentSide()==='long'?'Long-side research':currentSide()==='short'?'Short-side research':'Non-directional context';
  const recentLabel = () => currentSide()?'Five-session research change':'Five-session raw strength change';
  const recentValue = id => { const recent=themeResearch(id).recent; return currentSide()?recent?.directional_score_change:recent?.raw_score_change; };
  function recentChange(id) {
    const recent=themeResearch(id).recent,value=recentValue(id);
    if(!recent?.available)return `<span class="unavailable" title="${esc(UX.comparisonMessage(recent?.reason))}"><span class="comparison-short" aria-hidden="true">Unavailable</span><span class="comparison-reason">${esc(UX.comparisonMessage(recent?.reason))}</span></span>`;
    return `<span class="${signTone(value)}">${Number(value)>0?'+':''}${number(value,1)} pts</span>`;
  }
  function primaryThemes() {
    return (snapshot?.themes || []).filter(t => themeResearch(t.theme_id).researchable).sort((a,b)=>researchOrder(a.theme_id)-researchOrder(b.theme_id)||a.theme_id.localeCompare(b.theme_id));
  }
  function qualifiedRows() { return UX.researchRows(snapshot); }
  function uniqueRows(rows) {
    const tickers=new Map();for(const row of rows)if(!tickers.has(row.ticker))tickers.set(row.ticker,row);
    return [...tickers.values()];
  }
  function renderChanges() {
    $('leadership-changes').hidden=!snapshot;
    $('movement-side').textContent=sideLabel();
    if(!currentSide()){
      $('change-board').innerHTML='<p class="table-note">No directional theme states \u00b7 Raw score changes remain in the theme ledger.</p>';return;
    }
    const active=(snapshot?.themes||[]).filter(t=>t.status==='active');
    const comparable=active.filter(t=>themeResearch(t.theme_id).recent?.available);
    const missing=active.filter(t=>!themeResearch(t.theme_id).recent?.available);
    const unavailable=missing.length?`<p class="comparison-availability table-note">Five-session comparison unavailable \u00b7 ${[...new Set(missing.map(t=>UX.comparisonMessage(themeResearch(t.theme_id).recent?.reason)))].map(esc).join(' \u00b7 ')}</p>`:'';
    $('change-board').innerHTML=unavailable+'<div class="movement-columns">'+[1,-1].map(direction=>{
      const rows=comparable.filter(t=>Number(recentValue(t.theme_id))*direction>0).sort((a,b)=>direction*(Number(recentValue(b.theme_id))-Number(recentValue(a.theme_id)))||researchOrder(a.theme_id)-researchOrder(b.theme_id));
      return `<section class="movement-column"><h3>${direction===1?'Gaining strength':'Losing strength'}<span>${rows.length}</span></h3>${rows.length?'<ol>'+rows.slice(0,3).map(t=>`<li><div>${themeLink(t.theme_id)}<small>${themeState(t.theme_id)} \u00b7 ${esc(t.index?.trend||'Unavailable')} price</small></div><span class="movement-value">${recentChange(t.theme_id)}</span></li>`).join('')+'</ol>':`<p class="table-note">${comparable.length?'No themes '+(direction===1?'gaining':'losing')+' strength':'Comparison unavailable'}</p>`}</section>`;
    }).join('')+'</div>';
  }

  // Display transforms only: all breadth, returns, scores and trend come from the snapshot.
  function breadthBar(label,value,coverage = '') {
    const available = valid(value), bounded = available ? Math.max(0,Math.min(100,Number(value))) : 0;
    return `<div class="breadth-bar"><span class="breadth-label">${esc(label)}</span><svg viewBox="0 0 100 6" preserveAspectRatio="none" aria-hidden="true" focusable="false"><rect class="breadth-track" width="100" height="6" rx="2"/>${available ? `<rect class="breadth-fill" width="${bounded}" height="6" rx="2"/>` : ''}</svg><strong>${valid(value)?number(value,0)+'%':'—'}</strong>${coverage ? `<small>${esc(coverage)}</small>` : ''}</div>`;
  }
  function mapThemes() { return (snapshot?.themes || []).filter(t=>t.status === 'active' && valid(t.returns?.[0]?.value) && valid(t.returns?.[1]?.value)); }
  function mapDescription(t) { return `${t.name || t.theme_id} · Theme Strength Score ${number(t.score)} · 1M ${percent(t.returns?.[0]?.value,100,true)} · 3M ${percent(t.returns?.[1]?.value,100,true)} · ${t.index?.trend || 'Unavailable'} · ${researchState(t.theme_id)}`; }
  function renderThemeMap() {
    if(initialLoading)return;
    const rows=mapThemes().sort((a,b)=>name(a.theme_id).localeCompare(name(b.theme_id)));
    if(!rows.length){$('theme-map').innerHTML=empty('Theme Returns Map unavailable','Both completed-session returns are needed.');return;}
    if(!rows.some(t=>t.theme_id===mapSelected))mapSelected=rows[0].theme_id;
    if(!rows.some(t=>t.theme_id===mapFocusId))mapFocusId=mapSelected;
    const scale=parseFloat(getComputedStyle(document.documentElement).fontSize)/16,panelWidth=$('theme-map').clientWidth;
    mapWidth=Math.max(240,panelWidth?(window.innerWidth<=800?panelWidth:panelWidth*.78-24):800);
    mapPadding.left=66*scale;mapPadding.right=24*scale;mapPadding.top=24;mapPadding.bottom=50*scale;
    const domain=index=>{const values=rows.map(t=>Number(t.returns[index].value)),low=Math.min(0,...values),high=Math.max(0,...values),padding=Math.max((high-low)*.07,.005);return UX.axis(low-padding,high+padding,mapWidth<500?3:5);};
    const xd=domain(0),yd=domain(1),width=mapWidth-mapPadding.left-mapPadding.right,height=mapHeight-mapPadding.top-mapPadding.bottom;
    const x=v=>mapPadding.left+(v-xd.low)/(xd.high-xd.low)*width,y=v=>mapPadding.top+(yd.high-v)/(yd.high-yd.low)*height;
    const tick=v=>`${number(v*100,Number.isInteger(v*100)?0:Number.isInteger(v*1000)?1:2)}%`;
    const xt=xd.ticks.map((v,i)=>`<g class="map-tick"><line x1="${x(v)}" y1="${mapHeight-mapPadding.bottom}" x2="${x(v)}" y2="${mapHeight-mapPadding.bottom+4}"/><text x="${x(v)}" y="${mapHeight-mapPadding.bottom+21*scale}" text-anchor="${i===0?'start':i===xd.ticks.length-1?'end':'middle'}">${tick(v)}</text></g>`).join('');
    const yt=yd.ticks.map(v=>`<g class="map-tick"><line x1="${mapPadding.left-4}" y1="${y(v)}" x2="${mapPadding.left}" y2="${y(v)}"/><text x="${mapPadding.left-9}" y="${y(v)+4}" text-anchor="end">${tick(v)}</text></g>`).join('');
    const point=t=>{const cx=x(Number(t.returns[0].value)),cy=y(Number(t.returns[1].value)),cls=tone(t.index?.trend);const shape=cls==='negative'?`<path d="M${cx-5} ${cy-4}h10l-5 9z"/>`:cls==='mixed'?`<path d="M${cx} ${cy-6}l6 6-6 6-6-6z"/>`:`<circle cx="${cx}" cy="${cy}" r="4.5"/>`;return `<g role="button" tabindex="${t.theme_id===mapFocusId?0:-1}" data-map-theme="${esc(t.theme_id)}" data-focus-key="map:${esc(t.theme_id)}" class="map-point ${cls} ${t.theme_id===mapSelected?'map-selected':''}" aria-pressed="${t.theme_id===mapSelected}" aria-label="${esc(mapDescription(t))}"><title>${esc(mapDescription(t))}</title><circle class="point-hit" cx="${cx}" cy="${cy}" r="12"/><circle class="point-ring" cx="${cx}" cy="${cy}" r="9"/>${shape}</g>`;};
    $('theme-map').innerHTML=`<div class="map-toolbar"><p>${rows.length} themes · median returns</p><label class="inline-label">Focus theme<select id="map-selection" data-focus-key="map-selection">${rows.map(t=>`<option value="${esc(t.theme_id)}">${esc(t.name||t.theme_id)}</option>`).join('')}</select></label></div><div class="map-layout"><div class="map-chart"><div class="map-axis-label">3M return ↑</div><svg id="theme-map-svg" viewBox="0 0 ${mapWidth} ${mapHeight}" role="group" aria-label="Theme Returns Map. Arrow keys inspect themes; Enter selects. Open research from the readout." data-xmin="${xd.low}" data-xmax="${xd.high}" data-ymin="${yd.low}" data-ymax="${yd.high}"><rect class="map-field" x="${mapPadding.left}" y="${mapPadding.top}" width="${width}" height="${height}"/><line class="map-zero" x1="${x(0)}" y1="${mapPadding.top}" x2="${x(0)}" y2="${mapHeight-mapPadding.bottom}"/><line class="map-zero" x1="${mapPadding.left}" y1="${y(0)}" x2="${mapWidth-mapPadding.right}" y2="${y(0)}"/>${xt}${yt}${rows.map(point).join('')}</svg><div class="map-axis-label map-x-label">1M return →</div></div><div id="map-readout" class="map-readout" aria-live="polite"></div></div><div class="map-footer"><span class="map-legend"><span class="positive">● Bullish</span><span class="negative">▼ Bearish</span><span class="mixed">◆ Mixed</span><span>○ Unavailable</span></span><a class="text-link" href="#themes">Compare themes</a></div>`;
    $('map-selection').value=mapSelected;showMapReadout(mapSelected);
  }
  function showMapReadout(id,select=false) {
    const t=mapThemes().find(t=>t.theme_id===id);if(!t||!$('map-readout'))return;
    if(select){mapSelected=id;mapFocusId=id;$('map-selection').value=id;document.querySelectorAll('[data-map-theme]').forEach(n=>{const selected=n.dataset.mapTheme===id;n.classList.toggle('map-selected',selected);n.setAttribute('aria-pressed',String(selected));n.tabIndex=selected?0:-1;});}
    $('map-readout').innerHTML=`<h3>${esc(name(id))}</h3><dl><div><dt>Strength</dt><dd>${number(t.score,1)}</dd></div><div><dt>1M</dt><dd class="${signTone(t.returns[0].value)}">${percent(t.returns[0].value,100,true)}</dd></div><div><dt>3M</dt><dd class="${signTone(t.returns[1].value)}">${percent(t.returns[1].value,100,true)}</dd></div></dl>${state(t.index?.trend)}<p>${themeState(t.theme_id)}</p><a class="button secondary" href="${themeHref(id)}" data-inspect-theme="${esc(id)}" data-focus-key="map-open:${esc(id)}">Open theme</a>`;
    if(select){UX.move($('map-readout'),'lock');UX.pulse(document.querySelector('[data-map-theme="'+CSS.escape(id)+'"] .point-ring'));}
  }

  function marketEMA(label,close,value,ticker) {
    const available=valid(close)&&valid(value),relation=!available?'Unavailable':Number(close)>Number(value)?'Above':Number(close)<Number(value)?'Below':'At';
    const cls=relation==='Above'?'positive':relation==='Below'?'negative':'neutral';
    const message=research().ema_transitions?.[ticker]?.[label.toLowerCase()]?.message;
    return `<div class="ema-context ${cls}"><span>${relation}</span><b>${money(value)}</b>${message?`<small class="ema-transition">${esc(message)}</small>`:''}</div>`;
  }
  function renderBenchmarks() {
    const market=snapshot?.market||{};
    $('market-cards').innerHTML='<div class="benchmark-pair">'+['SPY','QQQ'].map(ticker=>{
      const row=market.context?.[ticker]||{},breadth=row.breadth||{},extension=research().extension?.indices?.[ticker];
      return `<article class="benchmark" aria-label="${ticker} market evidence"><div class="benchmark-heading"><h3>${ticker}</h3><span class="market-price">${money(row.close)}</span>${state(row.price_state)}</div><div class="benchmark-observations"><div><span class="metric-label">EMA21</span>${marketEMA('EMA21',row.close,row.ema21,ticker)}</div><div><span class="metric-label">EMA50</span>${marketEMA('EMA50',row.close,row.ema50,ticker)}</div><div class="benchmark-breadth"><span class="metric-label">Breadth ${helpButton('market-breadth')}</span>${breadthBar('21',breadth.above_ema21)}${breadthBar('50',breadth.above_ema50)}<small>${esc(breadth.state||'Unavailable')}</small></div></div><details class="benchmark-extra"><summary>Extension <span>${esc(extension?.state||'Unavailable')}</span></summary><p>${valid(extension?.distance)?number(extension.distance)+' ATR':'Unavailable'} ${helpButton('extension')}</p></details></article>`;
    }).join('')+'</div>';
    const iwm=market.context?.IWM||{};
    $('market-cards').innerHTML+=`<div class="iwm-context"><strong>IWM</strong><span>${money(iwm.close)}</span>${state(iwm.price_state)}<span class="context-label">Small-cap context ${helpButton('iwm')}</span><details><summary>EMA evidence</summary><div>${marketEMA('EMA21',iwm.close,iwm.ema21,'IWM')}${marketEMA('EMA50',iwm.close,iwm.ema50,'IWM')}</div></details></div>`;
    $('market-data-details').innerHTML=['SPY','QQQ'].map(ticker=>{const row=market.context?.[ticker]||{},b=row.breadth||{};return `<p>${ticker} breadth \u00b7 ${esc(b.valid??0)}/${esc(b.configured??0)} valid<br>${esc(row.roster_source||'Roster unavailable')}<br>${esc((row.roster_warnings||[]).join(' ')||'No roster advisories.')}</p>`;}).join('');
  }
  function renderOverview() {
    if(initialLoading)return;
    $('theme-map-panel').hidden=!snapshot;renderChanges();
    if(!snapshot){$('market-direction').innerHTML=empty('No completed snapshot','Open Snapshot to refresh completed-session data.');$('market-cards').innerHTML='';$('market-continuation').innerHTML='';return;}
    const direction=marketName(snapshot.market_direction),changes=v2().changes||{},decision=snapshot.market?.decision||{};
    const changed=changes.changed?`From ${marketName(changes.previous_market_direction)}`:changes.previous_market_direction?'Unchanged since previous session':'No previous comparison';
    $('market-direction').innerHTML=`<div class="bias-line"><div class="bias-title"><span class="eyebrow">Market Bias</span><h2 class="direction-name ${tone(direction)}" aria-label="Market Bias: ${esc(direction)}">${esc(direction)}</h2><span class="market-change">${esc(changed)}${v2().conviction==='selective'?' \u00b7 Reduced conviction':''}</span></div><div class="bias-action">${!currentResearch()?'<p>Current research list unavailable \u00b7 previous rules snapshot</p>':currentSide()?`<span>${sideLabel()}</span><a href="#themes">${primaryThemes().length} researchable themes <span aria-hidden="true">\u2192</span></a>`:'<p>No directional research list</p><a href="#themes">Explore theme context \u2192</a>'}</div></div><details class="decision-details"><summary>Decision evidence</summary><p id="decision-path">${esc(decision.reason||'Market context unavailable.')}</p><p id="today-plan">${esc(snapshot.today_plan||'')}</p><p>Breadth: ${esc(snapshot.market?.breadth_consensus||'Unavailable')}</p></details>`;
    renderBenchmarks();renderThemeMap();
    const leaders=primaryThemes().slice(0,3);
    $('market-continuation').innerHTML=`<section class="research-next"><div class="section-heading"><h2>Next in research</h2><a href="#themes" class="text-link">Theme changes \u2192</a></div>${leaders.length?`<ol class="next-themes">${leaders.map(t=>`<li><div>${themeLink(t.theme_id)}<small>${themeState(t.theme_id)}</small></div><span>${recentChange(t.theme_id)}</span></li>`).join('')}</ol><a href="#primary" class="queue-entry"><span>Primary research</span><strong>${v2().list?.stock_count??uniqueRows(qualifiedRows()).length} stocks <span aria-hidden="true">\u2192</span></strong></a>`:'<a href="#themes" class="queue-entry">All themes <span aria-hidden="true">\u2192</span></a>'}</section>`;
  }

  function setOptions(id, options) {
    const select = $(id), first = select.options[0].outerHTML, previous = select.value;
    const html = first + options.map(([value, text]) => `<option value="${esc(value)}">${esc(text)}</option>`).join('');
    if (select.innerHTML !== html) { select.innerHTML = html; select.value = options.some(([value]) => value === previous) ? previous : ''; }
  }
  function themeValue(theme, key) {
    if (key === 'name') return theme.name || theme.theme_id;
    if (key === 'score') return valid(theme.score) ? Number(theme.score) : null;
    if (key === 'return1' || key === 'return3') { const v = theme.returns?.[key === 'return1' ? 0 : 1]?.value; return valid(v) ? Number(v) : null; }
    if (key === 'breadth') { const v = theme.breadth?.[0]?.value; return valid(v) ? Number(v) : null; }
    if (key === 'trend') return ({Bullish:0,Mixed:1,Bearish:2,Unavailable:3})[theme.index?.trend || 'Unavailable'];
    if (key === 'priority') return researchOrder(theme.theme_id);
    if (key === 'recent') return valid(recentValue(theme.theme_id))?Number(recentValue(theme.theme_id)):null;
    if (key === 'rankchange') { const change=currentSide()?themeResearch(theme.theme_id).recent?.directional_rank_change:themeResearch(theme.theme_id).recent?.raw_rank_change; return valid(change)?Number(change):null; }
    return theme[key] || '';
  }
  function compareValues(a, b, descending = false) {
    if (a == null) return b == null ? 0 : 1;
    if (b == null) return -1;
    const order = typeof a === 'number' ? a - b : String(a).localeCompare(String(b));
    return descending ? -order : order;
  }
  function themeRows() {
    const query = $('theme-search').value.trim().toLowerCase();
    return (snapshot?.themes || []).filter(t => (ui.universe === 'active' ? t.status === 'active' : t.status !== 'active') && (!query || `${t.name} ${t.theme_id} ${t.family}`.toLowerCase().includes(query)) && (!$('theme-family').value || t.family === $('theme-family').value) && (!$('theme-priority').value || researchState(t.theme_id) === $('theme-priority').value) && (!$('theme-trend').value || (t.index?.trend || 'Unavailable') === $('theme-trend').value)).sort((a, b) => compareValues(themeValue(a, ui.themeSort), themeValue(b, ui.themeSort), ui.themeDescending) || a.theme_id.localeCompare(b.theme_id));
  }
  function renderThemes() {
    if(initialLoading)return;
    const tracked=ui.universe==='active';
    $('active-count').textContent=(snapshot?.themes||[]).filter(t=>t.status==='active').length;
    $('watch-count').textContent=(snapshot?.themes||[]).filter(t=>t.status!=='active').length;
    document.querySelectorAll('[data-universe]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.universe===ui.universe)));
    $('theme-priority').closest('label').hidden=!tracked||!currentSide();$('theme-trend').closest('label').hidden=!tracked;
    const count=['theme-family','theme-priority','theme-trend'].filter(id=>$(id).value).length;
    document.querySelector('.theme-filter-menu>summary').textContent='Filters'+(count?' ('+count+')':'');
    const rows=themeRows();
    $('theme-results').textContent=tracked?`${rows.length} themes \u00b7 ${sideLabel()} \u00b7 ${primaryThemes().length} researchable`:`${rows.length} untracked concepts`;
    $('theme-sort').value=`${ui.themeSort}:${ui.themeDescending?'desc':'asc'}`;
    if(!rows.length){$('theme-table').innerHTML=empty(snapshot?'No themes match':'Themes are waiting',snapshot?'Try another search or reset the filters.':'Open Snapshot to refresh completed-session data.','<button class="button secondary" data-reset="themes">Reset filters</button>');return;}
    if(!tracked){$('theme-table').innerHTML='<ul class="concept-list">'+rows.map(t=>`<li>${themeLink(t.theme_id)}<span>${esc(t.family)}</span></li>`).join('')+'</ul>';return;}
    const side=currentSide()?currentSide()==='short'?'Short':'Long':'Current';
    $('theme-table').innerHTML=`<div class="theme-ledger-head" aria-hidden="true"><span>Rank / Theme</span><span>Relative state \u00b7 ${side}</span><span>Theme Score</span><span>5-session \u0394</span><span>Price direction</span><span>1M / 3M return</span></div><ol class="theme-ledger">${rows.map(t=>`<li data-theme-row="${esc(t.theme_id)}" class="theme-line ${ui.selectedTheme===t.theme_id?'selected-row':''}"><div class="theme-identity"><span class="canonical-rank">${rankLabel(t.theme_id)}</span><div>${themeLink(t.theme_id)}<small>${esc(t.family)}</small></div></div><div class="relative-cell"><span class="mobile-label">Relative state \u00b7 ${side}</span>${themeState(t.theme_id)}<small>${themeResearch(t.theme_id).researchable?'Researchable':'Context'}</small></div><div class="score-cell"><span class="mobile-label">Theme Score</span><span class="score-value">${number(t.score,1)}</span><span class="score-rule" aria-hidden="true"><i style="width:${valid(t.score)?Math.max(0,Math.min(100,Number(t.score))):0}%"></i></span></div><div class="change-cell"><span class="mobile-label">5-session \u0394</span>${recentChange(t.theme_id)}<small>${currentSide()?'Side rank':'Rank'} ${rankChange(t.theme_id)}</small></div><div class="price-cell"><span class="mobile-label">Price direction</span>${state(t.index?.trend)}</div><div class="return-cell"><span class="mobile-label">1M / 3M return</span><span class="${signTone(t.returns?.[0]?.value)}">${percent(t.returns?.[0]?.value,100,true)}</span><span class="${signTone(t.returns?.[1]?.value)}">${percent(t.returns?.[1]?.value,100,true)}</span></div></li>`).join('')}</ol>`;
  }

  function participation(id) {
    const breadth=themeResearch(id).breadth||{};
    const text=valid(breadth.percent)&&valid(breadth.above)?`${number(breadth.above,0)} / ${number(breadth.total,0)} · ${number(breadth.percent,0)}%`:'Unavailable';
    return `<span>${text}</span>${breadth.small_sample?'<small class="small-sample" title="Participation is context only">Small sample<span class="sr-only">; context only</span></small>':''}`;
  }

  function researchStatus(row,included='Included in research list',excluded='Outside research list') { return !currentResearch()?'Previous rules snapshot':row.role==='Related'?'Context only':!currentSide()?'No directional research list':row.qualifies?included:excluded; }
  function eligibility(row) { return !currentResearch()?'Previous rules':!row.eligibility?.available ? 'Unavailable' : row.eligibility.eligible ? 'Liquidity eligible' : 'Liquidity ineligible'; }
  function candidateRow(row,location,withTheme=true,index=0) {
    const selected=ui.selectedTicker===row.ticker&&ui.selectedTickerTheme===row.theme_id;
    return `<li data-ticker-row="${esc(row.ticker)}" data-relationship-theme="${esc(row.theme_id)}" class="queue-row ${selected?'selected-row':''}"><span class="queue-position" aria-hidden="true">${String(index+1).padStart(2,'0')}</span><div class="queue-stock">${tickerLink(row.ticker,row.theme_id,ui.candidateLens)}<small class="row-company">${esc(research().companies?.[row.ticker]||'')}</small></div>${withTheme?`<div class="queue-theme">${themeLink(row.theme_id,ui.candidateLens)}<small class="col-role">${roleLabel(row.role)}</small></div>`:`<span class="col-role sr-only">${roleLabel(row.role)}</span>`}<div class="queue-peer"><span class="mobile-label">Peer strength</span><span class="numeric ${signTone(row.relative?.w)}">${points(row.relative?.w)}</span></div>${earningsEnabled()?`<div class="queue-earnings table-note"><span class="mobile-label">Earnings</span>${earnings(row.ticker)}</div>`:''}${saveButton(row.ticker,location+':'+row.theme_id,row.theme_id,ui.candidateLens)}</li>`;
  }

  function matchesCandidate(row) {
    const query=$('candidate-search').value.trim().toLowerCase(),filter=$('candidate-theme').value;
    return (!query||`${row.ticker} ${research().companies?.[row.ticker]||''} ${name(row.theme_id)}`.toLowerCase().includes(query))&&(!filter||row.theme_id===filter)&&(!$('candidate-role').value||row.role===$('candidate-role').value)&&(!$('candidate-earnings').value||(earningsDates(row.ticker).length>0)===($('candidate-earnings').value==='available'));
  }
  function lensRows() { return qualifiedRows(); }
  function renderCandidateContext() {
    const side=currentSide();
    const context=!currentResearch()?'Research update required':side?side.charAt(0).toUpperCase()+side.slice(1)+'-side chart review':'No directional list';
    $('primary-context').textContent=`${marketName(snapshot?.market_direction)} · ${v2().conviction==='selective'?'Reduced conviction · ':''}${context} · ${snapshot?.session||'No completed session'}`;
    renderExportMenu();requestAnimationFrame(UX.indicators);
  }
  function renderCandidates() {
    if(initialLoading)return;
    if(snapshot&&!currentResearch()){
      renderCandidateContext();$('candidate-results').textContent='Current research list unavailable';
      $('candidates').innerHTML=empty('Research update required','This stored snapshot uses previous rules. Refresh Data to calculate the current list. Themes and Saved remain available.');return;
    }
    const enabled=earningsEnabled(),earningsFilter=$('candidate-earnings');
    if(!enabled)earningsFilter.value='';earningsFilter.closest('label').hidden=!enabled;
    setOptions('candidate-theme',(snapshot?.themes||[]).filter(t=>lensRows().some(r=>r.theme_id===t.theme_id)).sort((a,b)=>name(a.theme_id).localeCompare(name(b.theme_id))).map(t=>[t.theme_id,t.name||t.theme_id]));
    renderCandidateContext();document.querySelectorAll('[data-candidate-mode]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.candidateMode===ui.candidateMode)));
        const all=qualifiedRows(),representatives=uniqueRows(all);
    const rows=(ui.candidateMode==='unique'?UX.displayRows(all,representatives,$('candidate-theme').value):all).filter(matchesCandidate);
    const sort=$('candidate-sort').value;
    rows.sort((a,b)=>(sort==='w-desc'||sort==='w-asc'?compareValues(valid(a.relative?.w)?Number(a.relative.w):null,valid(b.relative?.w)?Number(b.relative.w):null,sort==='w-desc'):sort==='theme'?name(a.theme_id).localeCompare(name(b.theme_id)):sort==='priority'?a.list_order-b.list_order:a.ticker.localeCompare(b.ticker))||a.ticker.localeCompare(b.ticker)||a.theme_id.localeCompare(b.theme_id));
    $('candidate-results').textContent=`${new Set(rows.map(r=>r.ticker)).size} ${new Set(rows.map(r=>r.ticker)).size===1?'stock':'stocks'}${ui.candidateMode==='relationships'?' · '+rows.length+' relationships':''}`;
    if(!rows.length){$('candidates').innerHTML=currentSide()?empty(all.length?'No stocks match':'No stocks to review this session',all.length?'Try another filter.':'No daily-eligible members belong to researchable themes.'):empty('No directional research list',marketName(snapshot?.market_direction)+' has no Long or Short research side. Themes, stock context and Saved remain available.');return;}
    $('candidates').innerHTML=candidateTables(rows,'Daily Research List');
  }
  function candidateTables(rows,label) {
    const grouped=ui.candidateMode==='relationships'||$('candidate-sort').value==='priority';
    if(!grouped)return `<div class="research-queue ${earningsEnabled()?'has-earnings':''}"><div class="queue-head" aria-hidden="true"><span>#</span><span>Stock</span><span>Theme</span><span>Peer strength (pp)</span>${earningsEnabled()?'<span>Earnings</span>':''}<span>Save</span></div><ol aria-label="${esc(label)}">${rows.map((r,i)=>candidateRow(r,ui.candidateLens,true,i)).join('')}</ol></div>`;
    const groups=new Map();for(const row of rows){if(!groups.has(row.theme_id))groups.set(row.theme_id,[]);groups.get(row.theme_id).push(row);}
    let position=0;
    return [...groups].map(([id,members])=>`<section class="queue-chapter" aria-label="${esc(name(id))}"><header class="chapter-heading"><span class="eyebrow">${String([...groups.keys()].indexOf(id)+1).padStart(2,'0')}</span><h2>${themeLink(id,ui.candidateLens)}</h2><div>${themeState(id)}</div><a class="text-link" href="${themeHref(id)}">${members.length} stocks <span aria-hidden="true">&#8599;</span></a></header><div class="chapter-stocks"><span class="chapter-peer-label">Peer strength (pp) ${helpButton('w')}</span><ol class="chapter-queue" aria-label="${esc(name(id))} stocks">${members.map(r=>candidateRow(r,ui.candidateLens,false,position++)).join('')}</ol></div></section>`).join('');
  }

  function memberRows(themeId) {
    let rows = (snapshot?.relationships || []).filter(r => r.theme_id === themeId && (!ui.memberSearch || r.ticker.toLowerCase().includes(ui.memberSearch.toLowerCase())) && (!ui.memberRole || r.role === ui.memberRole) && (!ui.memberEligibility || eligibility(r) === ui.memberEligibility));
    rows.sort((a,b) => ui.memberSort === 'ticker'||ui.memberSort==='priority'&&!currentSide() ? a.ticker.localeCompare(b.ticker) : compareValues(valid(a.relative?.w) ? Number(a.relative.w) : null,valid(b.relative?.w) ? Number(b.relative.w) : null, ui.memberSort === 'w-desc'||ui.memberSort==='priority'&&currentSide()==='long') || a.ticker.localeCompare(b.ticker));
    return rows;
  }
  function renderMembers(themeId) {
    const rows=memberRows(themeId),total=(snapshot?.relationships||[]).filter(r=>r.theme_id===themeId).length;
    $('member-count').textContent=`${rows.length} of ${total} reviewed relationships`;
    $('member-table').innerHTML=rows.length?`<ol class="member-ledger" aria-label="${esc(name(themeId))} members">${rows.map(r=>`<li><div class="member-identity">${tickerLink(r.ticker,r.theme_id,'directional')}<small>${roleLabel(r.role)}</small></div><div class="member-comparison"><span class="metric-label">Peer strength</span><span class="numeric ${signTone(r.relative?.w)}">${points(r.relative?.w)}</span></div><div class="member-status"><span>${esc(eligibility(r))}</span><small>${researchStatus(r)}</small>${earningsEnabled()?`<small>Earnings ${earnings(r.ticker)}</small>`:''}</div>${saveButton(r.ticker,'member:'+themeId,r.theme_id,'directional')}</li>`).join('')}</ol>`:empty(total?'No members match':'No reviewed members',total?'Try another filter.':'No reviewed members are available.');
  }
  function renderDetail(themeId) {
    if(initialLoading){$('detail-content').innerHTML='<p class="loading-state">Loading theme research…</p>';return;}
    const theme=snapshot?.themes?.find(t=>t.theme_id===themeId);
    if(!theme){$('detail-content').innerHTML='<a href="#themes" class="back-link">← Back to Themes</a>'+empty('Theme unavailable','This theme is not in the current snapshot.');return;}
    if(theme.status!=='active'){$('detail-content').innerHTML=`<a href="#themes" class="back-link">← Back to Themes</a><h1 id="detail-title" tabindex="-1">${esc(theme.name||themeId)}</h1>${empty('Not currently tracked','This concept has no reviewed calculation basket.') }`;return;}
    const originName=origin.startsWith('#primary')?'Primary':origin.startsWith('#saved')?'Saved':origin.startsWith('#overview')?'Market':'Themes';
    $('detail-content').innerHTML=`<div class="crumbs"><a href="${esc(origin)}" class="back-link" data-return-theme="${esc(themeId)}">&#8592; ${originName}</a>${themeDownload(themeId)}</div><header class="full-theme-heading"><h1 id="detail-title" tabindex="-1">${esc(theme.name||themeId)}</h1><span>${esc(theme.family)}</span></header><div class="full-theme-evidence">${themeEvidence(theme)}</div><div class="section-heading"><h2>Member stocks</h2><span id="member-count" class="table-meta"></span></div><form id="member-filters" class="filter-bar" role="search" aria-label="Filter theme members"><label class="search-field">Search members<input id="member-search" type="search" placeholder="Ticker…" value="${esc(ui.memberSearch)}"></label><label>Role<select id="member-role"><option value="">All roles</option><option value="Core">Core business</option><option value="Enabler">Supporting business</option><option value="Related">Related context</option></select></label><label>Eligibility<select id="member-eligibility"><option value="">All states</option><option>Liquidity eligible</option><option>Liquidity ineligible</option><option>Unavailable</option></select></label><label>Sort<select id="member-sort"><option value="priority">${currentSide()?'Peer priority':'Context order (A–Z)'}</option><option value="ticker">Ticker A–Z</option><option value="w-desc">Peer strength high to low</option><option value="w-asc">Peer strength low to high</option></select></label></form><div id="member-table" class="table-wrap member-table" role="region" tabindex="0" aria-label="Theme member research"></div>`;
    $('member-role').value=ui.memberRole;$('member-eligibility').value=ui.memberEligibility;$('member-sort').value=ui.memberSort;renderMembers(themeId);
  }

  function savedContext(ticker,rows) {
    const remembered=savedContexts[ticker];
    if(remembered&&typeof remembered.theme==='string'&&/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(remembered.theme))return {theme:remembered.theme,lens:'directional'};
    return {theme:snapshot?.exports?.assignments?.[ticker]?.assigned_section||(rows.length===1?rows[0].theme_id:''),lens:'directional'};
  }
  function renderSaved() {
    $('saved-count').textContent=watched.length;
    if(!watched.length){$('saved').innerHTML=empty('No saved stocks','Use the star beside a stock to save it here. Saved stays in this browser.');return;}
    $('saved').innerHTML='<p class="saved-scope">Saved in this browser only</p><div class="saved-list">'+watched.map(ticker=>{
      const rows=(snapshot?.relationships||[]).filter(r=>r.ticker===ticker),context=savedContext(ticker,rows),lead=rows.find(r=>r.theme_id===context.theme);
      const status=!snapshot?'Snapshot loading':!lead?'Relationship unavailable':researchStatus(lead,'On today’s research list','Outside today’s research list');
      return `<article class="saved-row ${earningsEnabled()?'has-earnings':''}">${tickerLink(ticker,context.theme,context.lens)}<div class="saved-context">${context.theme?themeLink(context.theme,context.lens):'No theme selected'}<small>${status}</small></div><span class="numeric ${signTone(lead?.relative?.w)}">Peer strength ${points(lead?.relative?.w)}${lead?`<small class="saved-w-theme">vs ${esc(name(lead.theme_id))} peers</small>`:''}</span>${earningsEnabled()?`<span class="table-note">${earnings(ticker)}</span>`:''}<button class="button quiet small" data-remove="${esc(ticker)}" data-focus-key="saved-remove:${esc(ticker)}" aria-label="Remove ${esc(ticker)} from Saved">Remove</button></article>`;
    }).join('')+'</div>';
  }

  function syncSaveButtons() {
    document.querySelectorAll('[data-save]').forEach(button => {
      const saved = watched.includes(button.dataset.save);
      button.setAttribute('aria-pressed',String(saved)); button.setAttribute('aria-label',saved ? `Saved ${button.dataset.save}; remove from Saved` : `Save ${button.dataset.save}`);
      button.innerHTML = `${icon('saved')}<span class="sr-only">${saved ? 'Saved' : 'Save'}</span>`;
    });
    $('saved-count').textContent = watched.length;
  }
  function changeSaved(ticker, remove = false, themeId = '', lens = '') {
    watched = remove || watched.includes(ticker) ? watched.filter(s => s !== ticker) : [...watched,ticker];
    if(!watched.includes(ticker))delete savedContexts[ticker];else if(themeId)savedContexts[ticker]={theme:themeId,lens:lens||'directional'};
    let persisted = true;
    try { localStorage.setItem(savedKey,JSON.stringify(watched));localStorage.setItem(savedContextKey,JSON.stringify(savedContexts)); } catch { persisted = false; }
    syncSaveButtons();
    if (inspector && route === '#saved') renderSaved();
    if (route === '#saved' && !inspector) {
      const index = [...document.querySelectorAll('[data-remove]')].findIndex(b => b.dataset.remove === ticker);
      renderSaved(); const buttons = document.querySelectorAll('[data-remove]');
      (buttons[Math.min(Math.max(index,0),buttons.length - 1)] || $('saved-title')).focus({preventScroll:true});
    }
    announce(`${ticker} ${watched.includes(ticker) ? 'saved' : 'removed from Saved'}${persisted ? '' : ' for this visit; browser storage is unavailable'}.`);
  }
  function inspectorFromLocation() {
    const params = new URLSearchParams((location.hash || '').split('?')[1] || '');
    const kind = params.has('theme') ? 'theme' : params.has('ticker') ? 'ticker' : null;
    const id = kind && params.get(kind);
    return id?{kind,id,context:kind==='ticker'?params.get('context')||'':'',lens:params.get('lens')||''}:null;
  }
  function inspectorView() {
    const key=inspector?.kind+':'+inspector?.id+':'+(inspector?.context||'');
    if (!inspectorViews.has(key)) inspectorViews.set(key,{filter:'All',search:'',sort:'ticker'});
    return inspectorViews.get(key);
  }
  function openInspector(kind,id,trigger,context='',lens='') {
    if(inspector?.kind===kind&&inspector?.id===id&&(inspector.context||'')===context)return;
    if(!inspector){inspectorTrigger=trigger;inspectorOrigin=route;inspectorScroll=window.scrollY;}
    else {const view=inspectorView();view.scroll=$('research-inspector').scrollTop;view.focus=trigger;}
    const depth=(inspector?Number(history.state?.researchDepth)||0:0)+1;
    const params=new URLSearchParams({[kind]:id});if(context)params.set('context',context);if(lens)params.set('lens',lens);
    const url=(route||'#overview')+'?'+params.toString();
    history.pushState({researchInspector:true,researchDepth:depth},'',url);
    syncInspector();
  }
  function closeInspector() {
    const depth=Number(history.state?.researchDepth)||0;
    if(depth){closingInspector=true;history.go(-depth);}
    else {history.replaceState(null,'',route||'#overview');syncInspector();}
  }
  function dismissInspector(restore = true) {
    if (!inspector) return;
    inspector = null;
    $('research-inspector').close();
    document.documentElement.classList.remove('inspecting');
    if (restore) {
      window.scrollTo(0,inspectorScroll);
      restoreFocus(inspectorTrigger);
      if (document.activeElement === document.body) document.querySelector('.view:not([hidden]) h1')?.focus({preventScroll:true});
    }
    document.title = (route.startsWith('#themes/') ? name(detailId()) : route === '#primary' ? 'Primary research' : route === '#overview' ? 'Market' : route.slice(1).replace(/^./,x=>x.toUpperCase())) + ' · ThemeScope';
  }
  function syncInspector() {
    let next=inspectorFromLocation();
    if(closingInspector){closingInspector=false;if(next){history.replaceState(null,'',route||'#overview');next=null;}}
    if (!next) { dismissInspector(); return; }
    const unchanged=inspector?.kind===next.kind&&inspector?.id===next.id&&(inspector?.context||'')===(next.context||'');
    if (!inspector) { inspectorScroll = window.scrollY; if (inspectorOrigin !== route) inspectorTrigger = ''; }
    const previousDepth=inspector?.depth||0,wasOpen=$('research-inspector').open;
    inspector = {...next,depth:Number(history.state?.researchDepth)||0};
    if(inspector.kind==='ticker'){ui.selectedTicker=inspector.id;ui.selectedTickerTheme=inspector.context;document.querySelectorAll('[data-ticker-row]').forEach(row=>row.classList.toggle('selected-row',row.dataset.tickerRow===inspector.id&&row.dataset.relationshipTheme===inspector.context));}
    if (inspector.kind === 'theme') { ui.selectedTheme = inspector.id; document.querySelectorAll('[data-theme-row]').forEach(row=>row.classList.toggle('selected-row',row.dataset.themeRow === inspector.id)); }
    renderInspector(unchanged);
    if (!$('research-inspector').open) { $('research-inspector').showModal(); document.documentElement.classList.add('inspecting'); }
    if(!unchanged){if(wasOpen){UX.move($('inspector-content'),'slide',inspector.depth<previousDepth?-1:1);UX.move($('inspector-title'),'slide',inspector.depth<previousDepth?-1:1);}const view=inspectorView();$('research-inspector').scrollTop=view.scroll||0;if(view.focus)restoreFocus(view.focus);else $('inspector-title').focus({preventScroll:true});}
  }
  function renderInspector(preserve = false) {
    if(!inspector)return;
    const dialog = $('research-inspector'), focused = dialog.contains(document.activeElement) ? focusKey() : null;
    const textSelection = document.activeElement?.id === 'inspector-search' ? document.activeElement.selectionStart : null;
    const scroll = dialog.scrollTop;
    $('inspector-back').hidden=(inspector.depth||0)<2;
    $('inspector-kind').textContent = inspector.kind === 'theme' ? 'Theme research' : 'Ticker research';
    $('inspector-title').textContent = inspector.kind === 'theme' ? name(inspector.id) : inspector.id;
    $('inspector-status').textContent = ['failed','interrupted'].includes(currentStatus.state) ? 'Refresh failed · previous successful snapshot retained' : 'Completed session ' + (snapshot?.session || '—');
    document.title = $('inspector-title').textContent + ' · Research · ThemeScope';
    if(initialLoading){$('inspector-content').innerHTML='<p class="loading-state">Loading research…</p>';return;}
    if (inspector.kind === 'theme') renderThemeInspector(); else renderTickerInspector();
    if (preserve) { dialog.scrollTop = scroll; restoreFocus(focused); if (textSelection != null) $('inspector-search')?.setSelectionRange(textSelection,textSelection); }
  }
  function themeEvidence(t) {
    const id=t.theme_id,r=themeResearch(id);
    return `<section class="relative-evidence" aria-label="Relative state"><div class="evidence-label">Relative state <span>${sideLabel()}</span></div><div class="relative-summary"><div>${themeState(id)}<small>${r.researchable?'Researchable':'Context only'}</small></div><div><span class="metric-label">Theme Score ${helpButton('strength')}</span><strong>${number(t.score,1)}</strong><small>Rank ${rankLabel(id)}</small></div><div><span class="metric-label">Five-session change</span><strong>${recentChange(id)}</strong><small>${rankChange(id)}</small></div></div></section><section class="price-evidence" aria-label="Price direction"><div class="evidence-label">Price direction ${state(t.index?.trend)}</div><div class="price-returns"><div><span class="metric-label">Median 1M return</span><strong class="${signTone(t.returns?.[0]?.value)}">${percent(t.returns?.[0]?.value,100,true)}</strong></div><div><span class="metric-label">Median 3M return</span><strong class="${signTone(t.returns?.[1]?.value)}">${percent(t.returns?.[1]?.value,100,true)}</strong></div></div></section><details class="theme-provenance"><summary>Evidence &amp; provenance</summary><p>${esc(r.reason||'Comparison unavailable')}</p><dl class="evidence-list"><div><dt>Participation ${helpButton('breadth')}</dt><dd>${participation(id)}</dd></div><div><dt>Current-basket comparison</dt><dd>${esc(r.recent?.comparison_session||UX.comparisonMessage(r.recent?.reason))}</dd></div><div><dt>Basket session</dt><dd>${esc(v2().comparison?.basis_session||snapshot?.session||'Unavailable')}</dd></div><div><dt>Participation change</dt><dd>${valid(r.recent?.breadth_change)?number(r.recent.breadth_change,1)+' pp':'Unavailable'}</dd></div><div><dt>Raw score change</dt><dd>${valid(r.recent?.raw_score_change)?number(r.recent.raw_score_change,1)+' pts':UX.comparisonMessage(r.recent?.reason)}</dd></div><div><dt>Index / EMA21 / EMA50</dt><dd>${number(t.index?.level)} / ${number(t.index?.ema21)} / ${number(t.index?.ema50)}</dd></div></dl></details>`;
  }
  function renderThemeInspector() {
    const t=snapshot?.themes?.find(row=>row.theme_id===inspector.id);
    if(!t){$('inspector-content').innerHTML=empty('Theme unavailable','This theme is not in the current snapshot.');return;}
    if(t.status!=='active'){$('inspector-content').innerHTML=`<p class="detail-family">${esc(t.family)}</p>${empty('Not currently tracked','No reviewed calculation basket.')}`;return;}
    const v=inspectorView();
    $('inspector-content').innerHTML=`<p class="inspector-family">${esc(t.family)}</p>${themeEvidence(t)}<div class="section-heading"><h3>Members</h3><span class="table-meta">Peer strength (pp) ${helpButton('w')}</span></div><form class="inspector-member-tools" aria-label="Filter member preview"><label>Search<input id="inspector-search" type="search" placeholder="Ticker" value="${esc(v.search)}" data-focus-key="inspector-search"></label><label>View<select id="inspector-view" data-focus-key="inspector-view"><option value="All">All members</option><option value="Primary">On research list</option><option value="Eligible">Liquidity eligible</option><option value="Core">Core business</option><option value="Enabler">Supporting business</option><option value="Related">Related context</option></select></label></form><p id="inspector-member-count" class="table-meta" role="status"></p><div id="inspector-members"></div><div class="inspector-footer"><a class="button secondary" href="${themeHref(t.theme_id)}">Open full theme</a>${themeDownload(t.theme_id)}</div>`;
    $('inspector-view').value=v.filter;renderInspectorMembers();
  }
  function renderInspectorMembers() {
    if(inspector?.kind!=='theme'||!$('inspector-members'))return;
    const v=inspectorView(),all=(snapshot?.relationships||[]).filter(r=>r.theme_id===inspector.id);
    const rows=all.filter(r=>(!v.search||r.ticker.toLowerCase().includes(v.search.toLowerCase()))&&(v.filter==='All'||v.filter==='Primary'&&r.qualifies||v.filter==='Eligible'&&r.eligibility?.eligible||r.role===v.filter));
    rows.sort((a,b)=>currentSide()?compareValues(valid(a.relative?.w)?Number(a.relative.w):null,valid(b.relative?.w)?Number(b.relative.w):null,currentSide()==='long')||a.ticker.localeCompare(b.ticker):a.ticker.localeCompare(b.ticker));const preview=rows.slice(0,6);
    $('inspector-member-count').textContent=`${preview.length} of ${rows.length} members`;
    $('inspector-members').innerHTML=preview.length?`<ul class="inspector-member-list">${preview.map(r=>`<li class="preview-row inspector-member-row" data-member-preview="${esc(r.ticker)}"><div>${tickerLink(r.ticker,r.theme_id,inspector.lens||'directional')}<small>${roleLabel(r.role)}</small></div><span class="numeric ${signTone(r.relative?.w)}">${points(r.relative?.w)}</span>${saveButton(r.ticker,'inspector-member',r.theme_id,inspector.lens||'directional')}</li>`).join('')}</ul>`:empty('No members match','Try another search or view.');
  }
  function tickerRelationship(row,primary=false) {
    return `<section class="stock-relationship ${primary?'relationship-context':'ticker-relationship'}" ${primary?`data-current-theme="${esc(row.theme_id)}" data-current-w="${esc(row.relative?.w)}" data-current-role="${esc(row.role)}"`:''}><div class="relationship-heading"><h3>${themeLink(row.theme_id,'directional')}</h3>${!primary?tickerLink(row.ticker,row.theme_id,'directional'):''}</div><div class="stock-comparison"><div><span class="metric-label">Peer strength ${helpButton('w')}</span><strong class="${primary?'w-value ':''}${signTone(row.relative?.w)}">${points(row.relative?.w)}</strong></div><div class="stock-membership"><span>${roleLabel(row.role)}</span><small>${researchStatus(row,'Included today','Not included today')}</small></div></div><dl class="evidence-list"><div><dt>1M excess return</dt><dd class="${signTone(row.relative?.er1)}">${points(row.relative?.er1)}</dd></div><div><dt>3M excess return</dt><dd class="${signTone(row.relative?.er3)}">${points(row.relative?.er3)}</dd></div><div><dt>Daily eligibility</dt><dd>${esc(eligibility(row))}</dd></div>${earningsEnabled()?`<div><dt>Earnings</dt><dd>${earnings(row.ticker)}</dd></div>`:''}</dl><details class="liquidity-details"><summary>Liquidity evidence</summary><dl class="evidence-list"><div><dt>Close</dt><dd>${money(row.eligibility?.close)}</dd></div><div><dt>${currentResearch()?v2().policy.liquidity_sessions+'-session average volume':'Average volume'}</dt><dd>${number(row.eligibility?.average_volume,0)}</dd></div><div><dt>${currentResearch()?v2().policy.liquidity_sessions+'-session average dollar volume':'Average dollar volume'}</dt><dd>${money(row.eligibility?.average_dollar_volume)}</dd></div></dl></details></section>`;
  }
  function renderTickerInspector() {
    const ticker=inspector.id,rows=(snapshot?.relationships||[]).filter(r=>r.ticker===ticker).sort((a,b)=>name(a.theme_id).localeCompare(name(b.theme_id)));
    const assigned=snapshot?.exports?.assignments?.[ticker]?.assigned_section;
    const lead=inspector.context?rows.find(r=>r.theme_id===inspector.context):rows.find(r=>r.theme_id===assigned)||rows[0];
    const others=rows.filter(r=>r!==lead),lens=inspector.lens||'directional',company=research().companies?.[ticker];
    $('inspector-content').innerHTML=`<div class="inspector-subhead"><span class="ticker-company">${esc(company||ticker)}</span>${saveButton(ticker,'inspector-ticker',lead?.theme_id||inspector.context,lens)}</div>${lead?tickerRelationship(lead,true):empty('Relationship unavailable',inspector.context?name(inspector.context)+' is not a current relationship.':'No current theme relationships. Your bookmark is retained.')}<details class="other-relationships"${others.length?'':' hidden'}><summary>Other relationships · ${others.length}</summary>${others.map(r=>tickerRelationship(r)).join('')||'<p class="table-note">No other current relationships.</p>'}</details>`;
  }

  function parseRoute() {
    const raw = (location.hash || '#overview').split('?')[0];
    if (['#market','#daily-plan'].includes(raw)) return '#overview';
    if (raw === '#candidates') return '#primary';
    if (raw === '#watchlist') return '#saved';
    return /^#(overview|themes(?:\/[^/]+)?|primary|saved|methodology)$/.test(raw) ? raw : '#overview';
  }
  function detailId() { try { return decodeURIComponent(route.split('/')[1] || ''); } catch { return ''; } }
  function methodologyAnchor() {
    if(route!=='#methodology')return false;
    const key=new URLSearchParams((location.hash||'').split('?')[1]||'').get('metric');
    const target=key&&document.getElementById('method-'+key);
    if(!target||!target.classList.contains('method-item'))return false;
    document.querySelectorAll('.method-item.research-anchor').forEach(node=>node.classList.remove('research-anchor'));target.classList.add('research-anchor');
    target.open=true;target.querySelector('summary').focus({preventScroll:true});target.scrollIntoView({block:'start'});return true;
  }
  function showRoute(initial = false) {
    interactions.closeHelp();
    document.querySelectorAll('.diagnostics[open],.theme-filter-menu[open],.secondary-filters[open],.export-menu[open]').forEach(e=>e.open=false);
    const next = parseRoute();
    const previousRoute = route;
    if(next===route){syncInspector();methodologyAnchor();return;}
    dismissInspector(false);
    if (route) positions.set(route,{scroll:window.scrollY, table:$('theme-table').scrollTop});
    route = next;
    const part = route.slice(1).split('/')[0], isDetail = route.startsWith('#themes/');
    const viewId = isDetail ? 'theme-detail' : ({overview:'overview-page',themes:'themes-page',primary:'candidate-page',saved:'saved-page',methodology:'methodology-page'})[part];
    document.querySelectorAll('.view').forEach(view => { view.hidden = view.id !== viewId;  });
    const view = $(viewId);
    if(!initial)UX.move(view,isDetail||previousRoute.startsWith('#themes/')?'slide':'shift');
    requestAnimationFrame(UX.indicators);
    document.querySelectorAll('[data-nav]').forEach(link => { if (link.dataset.nav === part) link.setAttribute('aria-current','page'); else link.removeAttribute('aria-current'); });
    if (isDetail) renderDetail(detailId());
    if (part === 'themes' && !isDetail) {
      document.querySelectorAll('[data-theme-row]').forEach(row => row.classList.toggle('selected-row',row.dataset.themeRow === ui.selectedTheme));
    }
    if (part === 'saved') renderSaved();
    const title = isDetail ? name(detailId()) : part==='primary'?'Primary research':part==='overview'?'Market':part.charAt(0).toUpperCase() + part.slice(1);
    document.title = title + ' · ThemeScope';
    requestAnimationFrame(() => {
      if (inspectorFromLocation()) { syncInspector(); return; }
      if(methodologyAnchor())return;
      if (!initial) view?.querySelector('h1')?.focus({preventScroll:true});
      const pos = positions.get(route); window.scrollTo(0,pos?.scroll || 0);
      if (!isDetail && part === 'themes') $('theme-table').scrollTop = pos?.table || 0;
      if (previousRoute.startsWith('#themes/') && route === origin) view?.querySelector(`a[href="${CSS.escape(previousRoute)}"]`)?.focus({preventScroll:true});
    });
  }
  function render(data) {
    if(!data||typeof data!=='object'){
      if(initialLoading){initialLoading=false;$('workspace').setAttribute('aria-busy','false');renderOverview();renderThemes();renderCandidates();renderSaved();}
      return;
    }
    initialLoading=false;$('workspace').setAttribute('aria-busy','false');
    const signature=JSON.stringify(data);
    if (signature === snapshotSignature) return; // Polling must not replace a focused or expanded research control.
    const focused = focusKey(), memberFocused = document.activeElement?.id?.startsWith('member-') ? {id:document.activeElement.id,start:document.activeElement.selectionStart} : null;
    const scroll = window.scrollY, themeScroll = $('theme-table').scrollTop,previousMarket=snapshot?.market_direction,previousSide=currentSide();
    interactions.closeHelp();snapshot=data;snapshotSignature=signature;
    if(!previousMarket||previousSide!==currentSide()){ui.themeSort='priority';ui.themeDescending=false;$('theme-priority').value='';}
    $('research-version-notice').hidden=currentResearch();
    $('research-version-notice').textContent=publicSnapshot?'This frozen snapshot uses previous research rules. Open a current snapshot for the new research list.':'This stored snapshot uses previous research rules. Refresh Data to calculate the current research list.';
    ui.candidateLens='directional';
    for (const url of blobUrls.values()) URL.revokeObjectURL(url); blobUrls.clear();
    renderLayer(); renderOverview();
    const rules=v2().policy;
    if(rules){
      $('method-state-rule').textContent=`Structural boundary: ${rules.structural_boundary} points. A change of at least ${rules.material_score_change} points over ${rules.change_sessions} completed sessions is material. Short-side research favors raw structural weakness, with changes reversed. Exactly 50 is a directional tie for both sides. Selective states keep the same members but place structurally established Fading themes ahead of below-boundary Improving themes.`;
      $('method-liquidity-rule').textContent=`Require a completed-session close above $${number(rules.price_floor_exclusive,0)} and average dollar volume of at least ${money(rules.average_dollar_volume_floor)} over ${rules.liquidity_sessions} completed regular sessions.`;
    }
    if(previousMarket&&previousMarket!==snapshot.market_direction&&route==='#overview')UX.move($('market-direction'),'sweep');
    setOptions('theme-family',[...new Set((snapshot.themes || []).map(t => t.family).filter(Boolean))].sort().map(f => [f,f]));
    renderThemes(); renderCandidates(); renderSaved();
    if (inspector) renderInspector(true);
    if (route.startsWith('#themes/')) { renderDetail(detailId()); document.title = name(detailId()) + ' · ThemeScope'; }
    $('target').textContent = 'Completed US session ' + (snapshot.session || '—');
    $('theme-table').scrollTop = themeScroll; window.scrollTo(0,scroll); restoreFocus(focused);
    if (memberFocused) { const input = $(memberFocused.id); input?.focus({preventScroll:true}); if (input?.type === 'search' && memberFocused.start != null) input.setSelectionRange(memberFocused.start,memberFocused.start); }
  }
  function showStatus(status) {
    const previous = currentStatus; currentStatus = status;
    const progress = status.progress || status.state || 'Ready';
    if ($('progress').textContent !== progress) $('progress').textContent = progress;
    $('target-detail').textContent = 'Target session ' + (status.target_session || '—');
    $('last-success').textContent = 'Last successful refresh ' + (status.last_successful_refresh || '—');
    const coverage = status.completeness;
    $('completeness').textContent = coverage?.complete ? coverage.terminal_target > 0 ? `Data complete · ${coverage.valid_target}/${coverage.required} inputs · ${coverage.trading_target} trading · ${coverage.terminal_target} terminal` : `Data complete · ${coverage.valid_target}/${coverage.required} symbols` : 'Completeness —';
    $('provider').textContent = 'Provider · ' + (typeof status.provider_health === 'string' ? status.provider_health : status.provider_health?.status || 'Not checked');
    $('read-status').textContent = status.snapshot_read?.startsWith('busy') ? 'Storage is busy. Showing the last committed snapshot.' : '';
    $('refresh').disabled = status.state === 'running';
    $('refresh-label').textContent = publicSnapshot ? 'Market data fixed' : preview ? 'Replay fixture' : status.state === 'running' ? 'Refreshing…' : 'Refresh Data';
    const failed = ['failed','interrupted'].includes(status.state);
    if (inspector) $('inspector-status').textContent = failed ? 'Refresh failed · previous successful snapshot retained' : status.state === 'running' ? progress : 'Completed session ' + (snapshot?.session || '—');
    $('error').hidden = !failed && !requestError;
    $('error').textContent = failed ? `${status.state === 'interrupted' ? 'Refresh interrupted' : 'Refresh failed'}${status.error ? ' (' + status.error + ')' : ''}. Previous successful results and exports remain available. Refresh Data to retry.` : requestError;
    if (previous.state === 'running' && status.state === 'success') {
      announce('Refresh complete.');
      $('refresh').classList.remove('refresh-complete');
      void $('refresh').offsetWidth;
      $('refresh').classList.add('refresh-complete');
    }
  }
  let polling = false;
  async function poll() {
    if (preview || polling) return;
    polling = true;
    try {
      const response = await fetch('/api/status'); if (!response.ok) throw Error('status');
      showStatus(await response.json());
      const data = await fetch('/api/dashboard-data'); if (!data.ok) throw Error('snapshot');
      render(await data.json());
    } catch {
      const message=snapshot?`Connection lost · showing completed session ${snapshot.session}`:'Connection lost · no snapshot loaded';
      if ($('progress').textContent !== message) $('progress').textContent = message;
      if(!snapshot){render(null);$('error').hidden=false;$('error').textContent='Unable to load research. Open Snapshot to retry.';}
    } finally { polling = false; }
  }
  document.addEventListener('submit',event => { if (event.target.matches('form')) event.preventDefault(); });
  document.addEventListener('click',event => {
    const button=event.target.closest('button'),link=event.target.closest('a'),point=event.target.closest('[data-map-theme]');
    if(point){showMapReadout(point.dataset.mapTheme,true);return;}
    if(link?.dataset.export){announce('Preparing '+link.dataset.export+' export.');const menu=link.closest('.export-menu');if(menu)menu.open=false;}
    if ((link?.dataset.inspectTheme || link?.dataset.inspectTicker) && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey) {
      event.preventDefault(); openInspector(link.dataset.inspectTheme ? 'theme' : 'ticker',link.dataset.inspectTheme || link.dataset.inspectTicker,link.dataset.focusKey,link.dataset.contextTheme||'',link.dataset.contextLens||'directional'); return;
    }
    if (link?.getAttribute('href') === '#workspace') { event.preventDefault(); $('workspace').focus(); $('workspace').scrollIntoView(); return; }
    if (link?.getAttribute('aria-disabled') === 'true') { event.preventDefault(); return; }
    if (link?.getAttribute('href')?.startsWith('#themes/')) {
      if (!route.startsWith('#themes/')) origin = route || '#themes';
      try { ui.selectedTheme = decodeURIComponent(link.getAttribute('href').split('/')[1]); } catch { ui.selectedTheme = ''; }
    }
    if (link?.getAttribute('href')?.startsWith('#') && link.getAttribute('href') !== '#workspace' && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey) {
      event.preventDefault();
      if (location.hash !== link.getAttribute('href')) { history.pushState(null,'',link.getAttribute('href')); showRoute(); }
      return;
    }
    if (!button) return;
    if (button.id === 'inspector-back') { history.back();return; }
    if (button.id === 'inspector-close') { closeInspector(); return; }
    if (button.dataset.inspectorFilter) { inspectorView().filter = button.dataset.inspectorFilter; renderInspector(true); restoreFocus('inspect-filter:' + button.dataset.inspectorFilter); return; }
    if (button.dataset.save) { changeSaved(button.dataset.save,false,button.dataset.saveTheme||'',button.dataset.saveLens||''); return; }
    if (button.dataset.remove) { changeSaved(button.dataset.remove,true); return; }
    if (button.dataset.universe) { ui.universe=button.dataset.universe; if(ui.universe!=='active'){$('theme-priority').value='';$('theme-trend').value='';ui.themeSort='name';ui.themeDescending=false;} renderThemes();requestAnimationFrame(UX.indicators);return;}
    if (button.dataset.candidateMode) { const changed=ui.candidateMode!==button.dataset.candidateMode;ui.candidateMode=button.dataset.candidateMode;renderCandidates();UX.indicators();if(changed)UX.move($('candidates'),'sweep');return; }
    if (button.dataset.reset === 'themes') { $('theme-filters').reset(); renderThemes(); }
    if (button.dataset.reset === 'candidates') { $('candidate-filters').reset(); renderCandidates(); }
  });
  function filterChange(event) {
    const id = event.target.id;
    if(id==='map-selection'){showMapReadout(event.target.value,true); return; }
    if (id === 'inspector-search') { inspectorView().search = event.target.value; renderInspectorMembers(); return; }
    if(id==='inspector-view'){inspectorView().filter=event.target.value;renderInspectorMembers();return;}
    if (id === 'inspector-sort') { inspectorView().sort = event.target.value; renderInspectorMembers(); return; }
    if (['theme-search','theme-family','theme-priority','theme-trend'].includes(id)) renderThemes();
    if (id === 'theme-sort') { const [key,direction] = event.target.value.split(':'); ui.themeSort = key; ui.themeDescending = direction === 'desc'; renderThemes(); $('theme-sort')?.focus(); }
    if (id.startsWith('candidate-') && id !== 'candidate-filters') renderCandidates();
    if (id.startsWith('member-') && ['member-search','member-role','member-eligibility','member-sort'].includes(id)) {
      ui.memberSearch = $('member-search').value; ui.memberRole = $('member-role').value; ui.memberEligibility = $('member-eligibility').value; ui.memberSort = $('member-sort').value; renderMembers(detailId());
    }
  }
  document.addEventListener('pointerover',event=>{ const point=event.target.closest('[data-map-theme]'); if (point) showMapReadout(point.dataset.mapTheme); });
  document.addEventListener('focusin',event=>{ const point=event.target.closest('[data-map-theme]'); if (point) { showMapReadout(point.dataset.mapTheme); } });
  document.addEventListener('keydown',event=>{
    const dialog=$('research-inspector');
    if(event.key==='Tab'&&dialog.open){
      const controls=[...dialog.querySelectorAll('a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),summary,[tabindex="0"]')].filter(node=>node.getClientRects().length&&!node.closest('[hidden]'));
      const first=controls[0],last=controls.at(-1),active=document.activeElement;
      if(event.shiftKey&&(active===first||!controls.includes(active))){event.preventDefault();last?.focus();}
      else if(!event.shiftKey&&active===last){event.preventDefault();first?.focus();}
      return;
    }
    const point=event.target.closest('[data-map-theme]');
    if(point&&['Enter',' '].includes(event.key)){event.preventDefault();showMapReadout(point.dataset.mapTheme,true);return;}
    if(!point||!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Home','End'].includes(event.key))return;
    const points=[...document.querySelectorAll('[data-map-theme]')], index=points.indexOf(point);
    const next=event.key === 'Home' ? 0 : event.key === 'End' ? points.length-1 : (index+(['ArrowRight','ArrowDown'].includes(event.key) ? 1 : -1)+points.length)%points.length;
    event.preventDefault();points.forEach((n,i)=>n.tabIndex=i===next?0:-1);mapFocusId=points[next].dataset.mapTheme;points[next]?.focus({preventScroll:true});
  });
  document.addEventListener('input',event => { if (event.target.matches('input')) filterChange(event); });
  document.addEventListener('change',event => { if (event.target.matches('select')) filterChange(event); });
  window.addEventListener('hashchange',() => showRoute());
  window.addEventListener('popstate',()=>showRoute());
  $('refresh').addEventListener('click',async () => {
    if (publicSnapshot) return;
    if (preview) { render(window.FIXTURE_SNAPSHOT); showStatus({state:'success',progress:'Synthetic fixture replayed',target_session:snapshot.session,last_successful_refresh:'Inspection fixture',completeness:snapshot.completeness,provider_health:'Fixture'}); return; }
    requestError = '';
    $('refresh').disabled = true;
    try {
      const response = await fetch('/api/refresh',{method:'POST'});
      if (!response.ok && response.status !== 409) requestError = 'Unable to start refresh. Previous results remain available. Refresh Data to retry.';
    } catch { requestError = 'Unable to reach the local server. Previous results remain available. Refresh Data to retry.'; }
    await poll();
  });
  $('theme-map-panel').addEventListener('toggle',()=>{ if ($('theme-map-panel').open) renderThemeMap(); });
  window.addEventListener('resize',()=>{ clearTimeout(mapResizeTimer); mapResizeTimer=setTimeout(()=>{ if ($('theme-map-panel').open) { const key=focusKey(); renderThemeMap(); restoreFocus(key); } },100); });
  $('research-inspector').addEventListener('cancel',event=>{ event.preventDefault(); closeInspector(); });
  const interactions=UX.install();
  new ResizeObserver(([entry]) => document.documentElement.style.setProperty('--masthead-height',entry.borderBoxSize[0].blockSize+'px')).observe(document.querySelector('.masthead'));
  history.scrollRestoration = 'manual';
  $('inspector-back').innerHTML=icon('back');
  document.querySelectorAll('a span[aria-hidden="true"]').forEach(span => { if (span.textContent === '↗') span.innerHTML = icon('up'); });
  renderSaved();showRoute(true);
  if (publicSnapshot) { render(window.THEMESCOPE_STATIC_SOURCE.snapshot); showStatus({state:'success',progress:'Market data fixed',target_session:snapshot.session,last_successful_refresh:snapshot.refreshed_at,completeness:snapshot.completeness,provider_health:snapshot.provider_health}); }
  else if (preview) { render(window.FIXTURE_SNAPSHOT); showStatus({state:'success',progress:'Synthetic inspection fixture',target_session:snapshot.session,last_successful_refresh:'Inspection fixture',completeness:snapshot.completeness,provider_health:'Fixture'}); }
  else { poll(); setInterval(poll,1500); }
})();
