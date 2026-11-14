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
  const ui = {universe:'active', themeSort:'score', themeDescending:true, selectedTheme:'', selectedTicker:'', selectedTickerTheme:'', candidateMode:'unique', candidateLens:'directional', memberSearch:'', memberRole:'', memberEligibility:'', memberSort:'priority'};
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
  const displayKey = 'themescope-vnext-display';
  let display = {density:'compact', text:100, motion:false, contrast:false};
  try {
    const stored = JSON.parse(localStorage.getItem(displayKey) || '{}');
    display = {density:stored.density === 'comfortable' ? 'comfortable' : 'compact', text:[100,125,150,175,200].includes(stored.text) ? stored.text : 100, motion:stored.motion === true, contrast:stored.contrast === true};
  } catch { /* Independent, optional browser preference. */ }
  function applyDisplay(persist = false) {
    const root = document.documentElement;
    root.dataset.density = display.density; root.dataset.motion = display.motion ? 'reduce' : 'system'; root.dataset.contrast = display.contrast ? 'high' : 'standard';
    root.style.fontSize = display.text + '%';
    $('text-size').textContent = display.text + '%';
    $('display-motion').checked = display.motion; $('display-contrast').checked = display.contrast;
    document.querySelectorAll('button[data-density]').forEach(b => b.setAttribute('aria-pressed',String(b.dataset.density === display.density)));
    document.querySelector('[data-text-step="-25"]').disabled = display.text === 100;
    document.querySelector('[data-text-step="25"]').disabled = display.text === 200;
    if ($('theme-map-panel').open) renderThemeMap();
    if(UX.reduced())document.getAnimations().forEach(a=>a.cancel());
    requestAnimationFrame(UX.indicators);
    if (persist) try { localStorage.setItem(displayKey,JSON.stringify(display)); } catch { announce('Display settings apply for this visit; browser storage is unavailable.'); }
  }
  function closeDisplay() { $('display-panel').hidden = true; $('display-toggle').setAttribute('aria-expanded','false'); }
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
  function themeBreadth(metric) {
    if(valid(metric?.value))return number(metric.value,0)+'%';
    if (!valid(metric?.valid) || !valid(metric?.configured)) return '—';
    const reason = Number(metric.configured) === 0 ? 'No active calculation basket' : Number(metric.valid) < 5 ? 'Insufficient members' : valid(metric.coverage) && Number(metric.coverage) < .8 ? 'Insufficient coverage' : 'Current close or EMA unavailable';
    const detail = `${reason} · ${metric.valid}/${metric.configured} valid${valid(metric.coverage) ? ' · ' + percent(metric.coverage,100) + ' coverage' : ''}`;
    return `<span title="${esc(detail)}">—<span class="sr-only"> breadth unavailable; ${esc(detail)}</span></span>`;
  }
  const research = () => snapshot?.research || {};
  const roleName = value => value === 'Core' ? 'Core business' : value === 'Enabler' ? 'Supporting business' : value;
  const roleLabel = value => `<span title="${value === 'Core' ? 'Business directly participates in this theme.' : value === 'Enabler' ? 'Provides products or services that enable this theme.' : ''}">${esc(roleName(value))}</span>`;
  const wHeading='Peer strength (pp) '+helpButton('w');
  function rankInfo(id) { return research().ranks?.themes?.[id] || {}; }
  function rankLabel(id) { const r=rankInfo(id); return valid(r.rank) ? '#' + r.rank : '—'; }
  function rankChange(id) {
    const r=rankInfo(id), reasons={no_compatible_previous_session:'Previous session unavailable',untracked_concept:'No active calculation basket',unavailable_score:'Strength unavailable',newly_active_theme:'Newly active theme',newly_available_score:'Newly available score',active_universe_changed:'Active theme universe changed',ranked_universe_changed:'Scored theme universe changed'};
    const text=valid(r.change) ? Number(r.change)>0 ? 'Up '+r.change : Number(r.change)<0 ? 'Down '+Math.abs(r.change) : 'Unchanged' : '—';
    const help=valid(r.change) ? `Compared with ${r.previous_session}; previous rank #${r.previous_rank}` : reasons[r.reason] || 'Previous session unavailable';
    return `<span title="${esc(help)}">${text}<span class="sr-only"> · ${esc(help)}</span></span>`;
  }

  function comparison(theme) { const value = theme.transition?.priority_change; return value == null ? 'Change unavailable' : value === '—' ? 'Continuing' : value; }
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
    const current=Boolean(v2().schema);
    const link=(url,label,file,id='')=>url?`<a ${id?`id="${id}"`:''} href="${esc(url)}" download="${esc(file)}" data-export="${esc(label)}">${esc(label)}<span aria-hidden="true">↓</span></a>`:`<span class="export-unavailable">${esc(label)} unavailable</span>`;
    let body=`<p class="menu-title">${current?'TradingView':'Previous research rules'} · ${esc(snapshot?.session||'No snapshot')}</p>`;
    body+=link(download(),current?'Full research list':'Previous rules list',current?'Research.txt':'PreviousResearch.txt','combined');
    const themes=Object.keys(snapshot?.exports?.individual||{});
    if(themes.length)body+=`<details class="theme-files"><summary class="button quiet">Theme files</summary>${themes.map(id=>link(download(id),name(id),'Theme.txt')).join('')}</details>`;
    body+=`<p class="menu-scope">${current?'Full session list in research order. Filters affect this view only.':'Stored under previous research rules. Refresh Data to build the current list.'}</p>`;
    if($('export-options').innerHTML!==body)$('export-options').innerHTML=body;
  }
  const columns = keys => `<colgroup>${keys.map(key=>`<col class="col-${key}">`).join('')}</colgroup>`;
  function table(headers, rows, caption, className = '') {
    const keys=headers.map(h=>h.column||'');
    return `<table class="${className}"><caption class="sr-only">${esc(caption)}</caption>${keys.every(Boolean)?columns(keys):''}<thead><tr>${headers.map(h=>`<th scope="col" class="${h.column?'col-'+h.column:''}${h.numeric?' numeric':''}">${h.label||h}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody></table>`;
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
      initialized:`Launch close: index initialized at 100 · First earned session ${layer.first_earned_session}. Historical comparisons are not yet available.`,
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
  const stateTone = value => ({Leading:'positive',Improving:'positive',Fading:'mixed',Lagging:'negative'})[value] || 'neutral';
  const themeState = id => `<span class="theme-state ${stateTone(researchState(id))}">${esc(researchState(id))}</span>`;
  const researchOrder = id => themeResearch(id).priority_rank ?? (v2().theme_order||[]).indexOf(id);
  function recentChange(id) {
    const recent=themeResearch(id).recent;
    if(!recent?.available)return '<span class="unavailable">History building</span>';
    return `<span class="${signTone(recent.score_change)}">${Number(recent.score_change)>0?'+':''}${number(recent.score_change,1)} pts</span>`;
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
    const states=['Improving','Fading'];
    $('leadership-changes').hidden=!snapshot;
    $('change-board').innerHTML=states.map(label=>{
      const rows=(snapshot?.themes||[]).filter(t=>researchState(t.theme_id)===label).sort((a,b)=>researchOrder(a.theme_id)-researchOrder(b.theme_id));
      return `<section class="change-column"><div class="section-heading"><h3 class="${stateTone(label)}">${label==='Improving'?'Gaining strength':'Losing strength'}</h3><span class="table-meta">${rows.length} themes</span></div>${rows.length?rows.slice(0,3).map(t=>`<div class="change-row">${themeLink(t.theme_id)}<span>${recentChange(t.theme_id)}</span></div>`).join(''):'<p class="table-note">'+(v2().schema?'No themes in this state.':'Five-session comparisons are not available in this snapshot.')+'</p>'}</section>`;
    }).join('');
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
    const rows=['SPY','QQQ','IWM'].map(ticker=>{
      const row=market.context?.[ticker]||{},breadth=row.breadth||{},extension=research().extension?.indices?.[ticker];
      return `<tr class="market-card ${ticker==='IWM'?'context':''}" aria-label="${ticker} market context"><td data-label="Index"><span class="market-ticker">${ticker}</span>${ticker==='IWM'?`<small>Small-cap context ${helpButton('iwm')}</small>`:''}</td><td data-label="State">${state(row.price_state)}</td><td class="numeric" data-label="Close"><span class="market-price">${money(row.close)}</span></td><td class="market-emas" data-label="EMA21">${marketEMA('EMA21',row.close,row.ema21,ticker)}</td><td class="market-emas" data-label="EMA50">${marketEMA('EMA50',row.close,row.ema50,ticker)}</td><td data-label="Breadth">${ticker==='IWM'?'<span aria-label="Breadth not applicable">—</span>':`<div class="market-breadth">${breadthBar('EMA21',breadth.above_ema21)}${breadthBar('EMA50',breadth.above_ema50)}</div><small class="breadth-state ${tone(breadth.state)}">${esc(breadth.state||'Unavailable')}</small>`}</td><td data-label="Extension">${ticker==='IWM'?'<span aria-label="Extension not applicable">—</span>':`${valid(extension?.distance)?number(extension.distance)+' ATR':'—'}<span class="index-extension">${esc(extension?.state||'History building')}</span>`}</td></tr>`;
    });
    $('market-cards').innerHTML=table(['Index','State',{label:'Close',numeric:true},'EMA21','EMA50','Breadth '+helpButton('market-breadth'),'Extension '+helpButton('extension')],rows,'Benchmark evidence. Breadth shows members above EMA21 and EMA50. IWM is context only.','benchmark-table');
    $('market-data-details').innerHTML=['SPY','QQQ'].map(ticker=>{const row=market.context?.[ticker]||{},b=row.breadth||{};return `<p>${ticker} breadth · ${esc(b.valid??0)}/${esc(b.configured??0)} valid<br>${esc(row.roster_source||'Roster unavailable')}<br>${esc((row.roster_warnings||[]).join(' ')||'No roster advisories.')}</p>`;}).join('');
  }
  function renderOverview() {
    if(initialLoading)return;
    document.querySelector('.overview-research').hidden=!snapshot;$('theme-map-panel').hidden=!snapshot;
    renderChanges();
    if(!snapshot){$('market-direction').innerHTML=empty('No completed snapshot','Refresh Data to load completed-session research.');$('market-cards').innerHTML='';return;}
    if(!v2().schema){
      document.querySelector('.overview-research').hidden=true;$('leadership-changes').hidden=true;
      $('market-direction').innerHTML=`<h2 class="direction-name">${esc(marketName(snapshot.market_direction))}</h2><p>Current research list unavailable · previous rules snapshot</p>`;
      renderBenchmarks();renderThemeMap();return;
    }
    const decision=snapshot?.market?.decision||{},direction=marketName(snapshot?.market_direction),changes=v2().changes||{};
    const changed=changes.changed?`Changed from ${marketName(changes.previous_market_direction)}`:changes.previous_market_direction?'Unchanged since previous session':'Previous market direction unavailable';
    const total=v2().list?.stock_count??uniqueRows(qualifiedRows()).length;
    $('market-direction').innerHTML=`<div class="market-conclusion direction-plane"><div class="bias-identity"><h2 class="direction-name ${tone(direction)}" aria-label="Market direction: ${esc(direction)}">${esc(direction)}</h2><span class="market-change">${esc(changed)}</span></div><div class="direction-step"><strong>${primaryThemes().length} themes</strong><span class="plane-label">Worth researching</span></div><div class="direction-step"><a href="#primary" class="research-total">${total} stocks</a><span class="plane-label">In today's research list</span></div><details class="decision-details"><summary>Market evidence</summary><p id="decision-path">${esc(decision.reason||'Market context unavailable.')}</p><p id="today-plan">${esc(snapshot?.today_plan||'')}</p><p>Breadth: ${esc(snapshot?.market?.breadth_consensus||'Unavailable')}</p><p>Benchmark extension: ${esc(research().extension?.state||'Unavailable')}</p></details></div>`;
    renderBenchmarks();renderThemeMap();
    $('theme-preview-order').textContent='Research priority';
    const themes=primaryThemes().slice(0,5);
    $('primary-themes').innerHTML=themes.length?themes.map(t=>`<div class="preview-row"><span class="position">${rankLabel(t.theme_id)}</span><div>${themeLink(t.theme_id)}<small>${themeState(t.theme_id)}</small></div><div class="preview-value">${number(t.score,1)}</div></div>`).join(''):empty('No researchable themes','All themes remain available for review.','<a href="#themes" class="text-link">Browse themes</a>');
    const stocks=uniqueRows(qualifiedRows()).slice(0,5);
    $('research-preview-count').textContent=total+' stocks · peer priority within each theme';
    $('candidate-preview').innerHTML=stocks.length?stocks.map(r=>`<div class="preview-row stock-row"><div>${tickerLink(r.ticker,r.theme_id,'directional')}<small>${esc(name(r.theme_id))}</small></div><div class="preview-value ${signTone(r.relative?.w)}">${points(r.relative?.w)}</div>${saveButton(r.ticker,'overview',r.theme_id,'directional')}</div>`).join(''):empty('No stocks to review','Daily eligibility and theme relevance determine the list.','<a href="#themes" class="text-link">Browse themes</a>');
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
    if (key === 'recent') return valid(themeResearch(theme.theme_id).recent?.score_change)?Number(themeResearch(theme.theme_id).recent.score_change):null;
    if (key === 'rankchange') return valid(rankInfo(theme.theme_id).change) ? Number(rankInfo(theme.theme_id).change) : null;
    if (key === 'change') return comparison(theme);
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
  function sortHeading(label, key, numeric = false, help = '') {
    const selected = ui.themeSort === key;
    const column=({name:'theme',score:'strength',rankchange:'rank-change'})[key]||key;
    return `<th scope="col" class="col-${column}${numeric?' numeric':''}"${selected ? ` aria-sort="${ui.themeDescending ? 'descending' : 'ascending'}"` : ''}><div class="th-content"><button class="sort-button" data-theme-sort="${key}" data-focus-key="sort:${key}">${label}<span aria-hidden="true">${selected ? ui.themeDescending ? '↓' : '↑' : '↕'}</span><span class="sr-only">, sort ${selected && !ui.themeDescending ? 'descending' : 'ascending'}</span></button>${help?helpButton(help):''}</div></th>`;
  }
  function renderThemes() {
    if(initialLoading)return;
    const active=(snapshot?.themes||[]).filter(t=>t.status==='active').length,tracked=ui.universe==='active';
    $('active-count').textContent=active;$('watch-count').textContent=(snapshot?.themes?.length||0)-active;
    document.querySelectorAll('[data-universe]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.universe===ui.universe)));
    for(const id of ['theme-priority','theme-trend'])$(id).closest('label').hidden=!tracked;
    const rows=themeRows();
    $('theme-results').textContent=`${rows.length} ${tracked?'themes':'concepts'} · ${v2().list?.side==='short'?'Short-side states':'Long-side states'} · ${primaryThemes().length} researchable`;
    if(!rows.length){$('theme-table').innerHTML=empty(snapshot?'No themes match':'Themes are waiting',snapshot?'Try another search or reset the filters.':'Refresh Data to load completed-session research.','<button class="button secondary" data-reset="themes">Reset filters</button>');return;}
    if(!tracked){$('theme-table').innerHTML=table(['Concept','Family','Coverage'],rows.map(t=>`<tr><td data-label="Concept">${themeLink(t.theme_id)}</td><td data-label="Family">${esc(t.family)}</td><td data-label="Coverage">Not currently tracked</td></tr>`),'Untracked concepts','concept-table');return;}
    const heading=`<thead><tr><th scope="col" class="col-rank numeric">Rank ${helpButton('rank')}</th>${sortHeading('Theme','name')}${sortHeading('Strength','score',true,'strength')}${sortHeading('5-session Δ','recent',true)}${sortHeading('Trend','trend')}${sortHeading('Participation','breadth',true,'breadth')}${sortHeading('State','priority',false,'priority')}</tr></thead>`;
    const body=rows.map(t=>`<tr data-theme-row="${esc(t.theme_id)}" class="${ui.selectedTheme===t.theme_id?'selected-row':''}"><td class="numeric col-rank canonical-rank" data-label="Rank">${rankLabel(t.theme_id)}</td><td class="col-theme theme-name" data-label="Theme">${themeLink(t.theme_id)}<small class="theme-family">${esc(t.family)}</small></td><td class="col-strength numeric" data-label="Strength">${number(t.score,1)}</td><td class="col-recent numeric" data-label="5-session change">${recentChange(t.theme_id)}<small class="rank-change">Rank ${rankChange(t.theme_id)}</small></td><td class="col-trend" data-label="Trend">${state(t.index?.trend)}</td><td class="col-breadth numeric" data-label="Participation">${participation(t.theme_id)}</td><td class="col-priority" data-label="State">${themeState(t.theme_id)}<small class="researchability">${themeResearch(t.theme_id).researchable?'Researchable':'Context only'}</small></td></tr>`).join('');
    const sortControl=`<label class="theme-mobile-sort inline-label">Sort themes<select id="theme-mobile-sort"><option value="score:desc">Strength strongest first</option><option value="score:asc">Strength weakest first</option><option value="name:asc">Theme A–Z</option><option value="recent:desc">Recent improvement first</option><option value="recent:asc">Recent deterioration first</option><option value="priority:asc">Research priority</option></select></label>`;
    $('theme-table').innerHTML=sortControl+`<table role="table" class="theme-research-table"><caption class="sr-only">Theme states reflect the current research side. Strength ranks compare all scored active themes. Five-session change uses compatible history.</caption>${columns(['rank','theme','strength','recent','trend','breadth','priority'])}${heading}<tbody role="rowgroup">${body}</tbody></table>`;
    const mobile=$('theme-mobile-sort');if([...mobile.options].some(o=>o.value===`${ui.themeSort}:${ui.themeDescending?'desc':'asc'}`))mobile.value=`${ui.themeSort}:${ui.themeDescending?'desc':'asc'}`;
  }
  function participation(id) {
    const breadth=themeResearch(id).breadth||{};
    const text=valid(breadth.percent)&&valid(breadth.above)?`${number(breadth.above,0)} / ${number(breadth.total,0)} · ${number(breadth.percent,0)}%`:'Unavailable';
    return `<span>${text}</span>${breadth.small_sample?'<small class="small-sample">Small sample · context only</small>':''}`;
  }

  function eligibility(row) { return !row.eligibility?.available ? 'Unavailable' : row.eligibility.eligible ? 'Liquidity eligible' : 'Liquidity ineligible'; }
  function candidateRow(row,location,withTheme=true) {
    const selected=ui.selectedTicker===row.ticker&&ui.selectedTickerTheme===row.theme_id;
    return `<tr data-ticker-row="${esc(row.ticker)}" data-relationship-theme="${esc(row.theme_id)}" class="${selected?'selected-row':''}"><td class="col-ticker" data-label="Ticker">${tickerLink(row.ticker,row.theme_id,ui.candidateLens)}</td>${withTheme?`<td class="col-theme" data-label="Theme">${themeLink(row.theme_id,ui.candidateLens)}</td>`:''}<td class="col-role" data-label="Role">${roleLabel(row.role)}</td><td data-label="Peer strength" class="col-w numeric ${signTone(row.relative?.w)}">${points(row.relative?.w)}</td>${earningsEnabled()?`<td data-label="Earnings" class="col-earnings table-note">${earnings(row.ticker)}</td>`:''}<td class="col-save" data-label="Save">${saveButton(row.ticker,location+':'+row.theme_id,row.theme_id,ui.candidateLens)}</td></tr>`;
  }
  const candidateHeaders=(withTheme=true)=>[{label:'Ticker',column:'ticker'},...(withTheme?[{label:'Theme',column:'theme'}]:[]),{label:'Role',column:'role'},{label:wHeading,column:'w',numeric:true},...(earningsEnabled()?[{label:'Earnings',column:'earnings'}]:[]),{label:'Save',column:'save'}];
  function matchesCandidate(row) {
    const query=$('candidate-search').value.trim().toLowerCase(),filter=$('candidate-theme').value;
    return (!query||`${row.ticker} ${name(row.theme_id)}`.toLowerCase().includes(query))&&(!filter||row.theme_id===filter)&&(!$('candidate-role').value||row.role===$('candidate-role').value)&&(!$('candidate-earnings').value||(earningsDates(row.ticker).length>0)===($('candidate-earnings').value==='available'));
  }
  function lensRows() { return qualifiedRows(); }
  function renderCandidateContext() {
    const side=v2().list?.side;
    $('primary-context').textContent=`${marketName(snapshot?.market_direction)} · ${side?side.charAt(0).toUpperCase()+side.slice(1)+'-side chart review':'No directional list'} · ${snapshot?.session||'No completed session'}`;
    renderExportMenu();requestAnimationFrame(UX.indicators);
  }
  function renderCandidates() {
    if(initialLoading)return;
    if(snapshot&&!v2().schema){
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
    rows.sort((a,b)=>(sort==='w-desc'||sort==='w-asc'?compareValues(valid(a.relative?.w)?Number(a.relative.w):null,valid(b.relative?.w)?Number(b.relative.w):null,sort==='w-desc'):sort==='theme'?name(a.theme_id).localeCompare(name(b.theme_id)):sort==='priority'?a.research_order-b.research_order:a.ticker.localeCompare(b.ticker))||a.ticker.localeCompare(b.ticker)||a.theme_id.localeCompare(b.theme_id));
    $('candidate-results').textContent=`${new Set(rows.map(r=>r.ticker)).size} stocks${ui.candidateMode==='relationships'?' · '+rows.length+' relationships':''}`;
    if(!rows.length){$('candidates').innerHTML=empty(all.length?'No stocks match':'No stocks to review this session',all.length?'Try another filter.':'No daily-eligible members belong to researchable themes.');return;}
    $('candidates').innerHTML=candidateTables(rows,'Daily Research List');
  }
  function candidateTables(rows,label) {
    const withTheme=ui.candidateMode==='unique';
    const render=(members,title)=>`<div class="table-wrap" role="region" tabindex="0" aria-label="${esc(title)}">${table(candidateHeaders(withTheme),members.map(r=>candidateRow(r,ui.candidateLens,withTheme)),title+'; peer-relative performance is relative to '+(withTheme?'the displayed theme.':name(members[0].theme_id)+'.'),withTheme?'candidate-table':'candidate-table grouped-table')}</div>`;
    if(ui.candidateMode==='unique')return render(rows,label);
    const groups=new Map();for(const row of rows){if(!groups.has(row.theme_id))groups.set(row.theme_id,[]);groups.get(row.theme_id).push(row);}
    return [...groups].map(([id,members])=>`<section class="qualification-group"><div class="group-heading"><h3>${themeLink(id,ui.candidateLens)}</h3><span class="table-meta">${members.length} relationships</span></div>${render(members,name(id))}</section>`).join('');
  }

  function memberRows(themeId) {
    let rows = (snapshot?.relationships || []).filter(r => r.theme_id === themeId && (!ui.memberSearch || r.ticker.toLowerCase().includes(ui.memberSearch.toLowerCase())) && (!ui.memberRole || r.role === ui.memberRole) && (!ui.memberEligibility || eligibility(r) === ui.memberEligibility));
    rows.sort((a,b) => ui.memberSort === 'ticker' ? a.ticker.localeCompare(b.ticker) : compareValues(valid(a.relative?.w) ? Number(a.relative.w) : null,valid(b.relative?.w) ? Number(b.relative.w) : null, ui.memberSort === 'w-desc'||ui.memberSort==='priority'&&v2().list?.side!=='short') || a.ticker.localeCompare(b.ticker));
    return rows;
  }
  function renderMembers(themeId) {
    const rows = memberRows(themeId), total = (snapshot?.relationships || []).filter(r => r.theme_id === themeId).length;
    $('member-count').textContent = `${rows.length} of ${total} reviewed relationships`;
    $('member-table').innerHTML = rows.length ? table(['Ticker','Role',{label:'Peer strength (pp)',numeric:true},'Daily eligibility','Research list',...(earningsEnabled() ? ['Earnings'] : []),'Saved'], rows.map(r => `<tr><td>${tickerLink(r.ticker,r.theme_id,'directional')}</td><td>${roleLabel(r.role)}</td><td class="numeric ${signTone(r.relative?.w)}">${points(r.relative?.w)}</td><td class="table-note">${esc(eligibility(r))}</td><td><span class="table-note">${r.role==='Related'?'Context only':r.qualifies ? 'Included in research list' : 'Outside research list'}</span></td>${earningsEnabled() ? `<td class="table-note">${earnings(r.ticker)}</td>` : ''}<td>${saveButton(r.ticker,'member:'+themeId,r.theme_id,'directional')}</td></tr>`), name(themeId) + ' members. Peer-relative performance is an ordering signal.') : empty(total ? 'No members match this view' : 'No reviewed members available', total ? 'Try another ticker, role or eligibility filter.' : 'No reviewed members are available.');
  }
  function renderDetail(themeId) {
    if(initialLoading){$('detail-content').innerHTML='<p class="loading-state">Loading theme research…</p>';return;}
    const theme=snapshot?.themes?.find(t=>t.theme_id===themeId);
    if(!theme){$('detail-content').innerHTML='<a href="#themes" class="back-link">← Back to Themes</a>'+empty('Theme unavailable','This theme is not in the current snapshot.');return;}
    if(theme.status!=='active'){$('detail-content').innerHTML=`<a href="#themes" class="back-link">← Back to Themes</a><h1 id="detail-title" tabindex="-1">${esc(theme.name||themeId)}</h1>${empty('Not currently tracked','This concept has no reviewed calculation basket.') }`;return;}
    const originName=origin.startsWith('#primary')?'research list':origin.startsWith('#saved')?'Saved':origin.startsWith('#overview')?'Overview':'Themes',context=themeResearch(themeId);
    $('detail-content').innerHTML=`<div class="crumbs"><a href="${esc(origin)}" class="back-link" data-return-theme="${esc(themeId)}">← Back to ${originName}</a>${themeDownload(themeId)}</div><div class="detail-heading"><h1 id="detail-title" tabindex="-1">${esc(theme.name||themeId)}</h1><p class="detail-family">${esc(theme.family)} · ${themeState(themeId)} · ${v2().list?.side==='short'?'Short-side':'Long-side'} context</p></div><div class="detail-primary">${metric('Structural strength '+helpButton('strength'),number(theme.score,1))}${metric('Strength rank '+helpButton('rank'),rankLabel(themeId))}${metric('Last five sessions',recentChange(themeId))}${metric('Theme trend',state(theme.index?.trend))}</div><p class="theme-reason">${esc(context.reason||'Comparison unavailable')} · ${context.researchable?'Daily-eligible members enter today’s research list.':'Members remain available for context.'}</p><div class="detail-summary">${metric('Median 1M return',percent(theme.returns?.[0]?.value,100,true))}${metric('Median 3M return',percent(theme.returns?.[1]?.value,100,true))}${metric('Theme participation '+helpButton('breadth'),participation(themeId))}</div><details class="theme-evidence"><summary>Recent change &amp; trend evidence</summary><dl class="relationship-metrics"><div><dt>Compared with</dt><dd>${esc(context.recent?.session||'History building')}</dd></div><div><dt>Five-session rank change</dt><dd>${valid(context.recent?.rank_change)?number(context.recent.rank_change,0):'Unavailable'}</dd></div><div><dt>Participation change</dt><dd>${valid(context.recent?.breadth_change)?number(context.recent.breadth_change,1)+' pp':'Unavailable'}</dd></div><div><dt>Index / EMA21 / EMA50</dt><dd>${number(theme.index?.level)} / ${number(theme.index?.ema21)} / ${number(theme.index?.ema50)}</dd></div></dl></details><div class="section-heading"><h2>Member stocks</h2><span id="member-count" class="table-meta"></span></div><form id="member-filters" class="filter-bar" role="search" aria-label="Filter theme members"><label class="search-field">Search members<input id="member-search" type="search" placeholder="Ticker…" value="${esc(ui.memberSearch)}"></label><label>Role<select id="member-role"><option value="">All roles</option><option value="Core">Core business</option><option value="Enabler">Supporting business</option><option value="Related">Related context</option></select></label><label>Eligibility<select id="member-eligibility"><option value="">All states</option><option>Liquidity eligible</option><option>Liquidity ineligible</option><option>Unavailable</option></select></label><label>Sort<select id="member-sort"><option value="priority">Peer priority</option><option value="ticker">Ticker A–Z</option><option value="w-desc">Peer strength high to low</option><option value="w-asc">Peer strength low to high</option></select></label></form><div id="member-table" class="table-wrap member-table" role="region" tabindex="0" aria-label="Theme member research"></div>`;
    $('member-role').value=ui.memberRole;$('member-eligibility').value=ui.memberEligibility;$('member-sort').value=ui.memberSort;renderMembers(themeId);
  }

  function savedContext(ticker,rows) {
    const remembered=savedContexts[ticker];
    if(remembered&&typeof remembered.theme==='string'&&/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(remembered.theme))return {theme:remembered.theme,lens:'directional'};
    return {theme:snapshot?.exports?.assignments?.[ticker]?.assigned_section||(rows.length===1?rows[0].theme_id:''),lens:'directional'};
  }
  function renderSaved() {
    $('saved-count').textContent=watched.length;
    if(!watched.length){$('saved').innerHTML=empty('No Saved tickers','Saved in this browser only');return;}
    $('saved').innerHTML='<p class="saved-scope">Saved in this browser only</p><div class="saved-list">'+watched.map(ticker=>{
      const rows=(snapshot?.relationships||[]).filter(r=>r.ticker===ticker),context=savedContext(ticker,rows),lead=rows.find(r=>r.theme_id===context.theme);
      const status=!snapshot?'Snapshot loading':!lead?'Relationship unavailable':lead.qualifies?'On today’s research list':'Outside today’s research list';
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
    document.title = (route.startsWith('#themes/') ? name(detailId()) : route === '#primary' ? 'Research list' : route.slice(1).replace(/^./,x=>x.toUpperCase())) + ' · ThemeScope';
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
    if (!$('research-inspector').open) { closeDisplay(); $('research-inspector').showModal(); document.documentElement.classList.add('inspecting'); }
    if(!unchanged){if(wasOpen){UX.move($('inspector-content'),'slide',inspector.depth<previousDepth?-1:1);UX.move($('inspector-title'),'slide',inspector.depth<previousDepth?-1:1);}const view=inspectorView();$('research-inspector').scrollTop=view.scroll||0;if(view.focus)restoreFocus(view.focus);else $('inspector-title').focus({preventScroll:true});}
  }
  function metric(label,value) { return `<div class="metric-block"><span class="metric-label">${label}</span><div class="metric-value">${value}</div></div>`; }
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
  function renderThemeInspector() {
    const t=snapshot?.themes?.find(row=>row.theme_id===inspector.id);
    if(!t){$('inspector-content').innerHTML=empty('Theme unavailable','This theme is not in the current snapshot.');return;}
    if(t.status!=='active'){$('inspector-content').innerHTML=`<p class="detail-family">${esc(t.family)} · Untracked Concept</p>${empty('No active calculation basket','This concept does not enter Strength, returns or candidate calculations.')}`;return;}
    const v=inspectorView();
    $('inspector-content').innerHTML=`<div class="inspector-subhead"><span>${esc(t.family)}</span>${themeState(t.theme_id)}</div><div class="inspector-metrics">${metric('Strength '+helpButton('strength'),number(t.score,1))}${metric('Strength Rank '+helpButton('rank'),rankLabel(t.theme_id))}${metric('Trend',state(t.index?.trend))}${metric('1M Return',percent(t.returns?.[0]?.value,100,true))}${metric('3M Return',percent(t.returns?.[1]?.value,100,true))}${metric('Last five sessions',recentChange(t.theme_id))}</div><div class="inspector-breadth">${participation(t.theme_id)}</div><p class="inspector-reason">${esc(themeResearch(t.theme_id).reason||'History building')}. ${helpButton('priority')}</p><div class="section-heading"><h3>Member preview</h3><span class="table-meta">Peer strength (pp) ${helpButton('w')}</span></div><form class="inspector-member-tools" aria-label="Filter member preview"><label>Search<input id="inspector-search" type="search" placeholder="Ticker" value="${esc(v.search)}" data-focus-key="inspector-search"></label><label>View<select id="inspector-view" data-focus-key="inspector-view"><option value="All">All members</option><option value="Primary">On research list</option><option value="Eligible">Liquidity eligible</option><option value="Core">Core business</option><option value="Enabler">Supporting business</option><option value="Related">Related context</option></select></label></form><p id="inspector-member-count" class="table-meta" role="status"></p><div id="inspector-members"></div><div class="inspector-footer"><a class="button secondary" href="${themeHref(t.theme_id)}">Open full theme</a><a class="text-link" href="#methodology?metric=strength">Metric definitions</a></div>`;
    $('inspector-view').value=v.filter;renderInspectorMembers();
  }
  function renderInspectorMembers() {
    if(inspector?.kind!=='theme'||!$('inspector-members'))return;
    const v=inspectorView(),all=(snapshot?.relationships||[]).filter(r=>r.theme_id===inspector.id);
    const rows=all.filter(r=>(!v.search||r.ticker.toLowerCase().includes(v.search.toLowerCase()))&&(v.filter==='All'||v.filter==='Primary'&&r.qualifies||v.filter==='Eligible'&&r.eligibility?.eligible||r.role===v.filter));
    rows.sort((a,b)=>compareValues(valid(a.relative?.w)?Number(a.relative.w):null,valid(b.relative?.w)?Number(b.relative.w):null,v2().list?.side!=='short')||a.ticker.localeCompare(b.ticker));const preview=rows.slice(0,6);
    $('inspector-member-count').textContent=`${preview.length} of ${rows.length} members`;
    $('inspector-members').innerHTML=preview.length?`<ul class="inspector-member-list">${preview.map(r=>`<li class="preview-row inspector-member-row" data-member-preview="${esc(r.ticker)}"><div>${tickerLink(r.ticker,r.theme_id,inspector.lens||'directional')}<small>${roleLabel(r.role)}</small></div><span class="numeric ${signTone(r.relative?.w)}">${points(r.relative?.w)}</span>${saveButton(r.ticker,'inspector-member',r.theme_id,inspector.lens||'directional')}</li>`).join('')}</ul>`:empty('No members match','Try another search or view.');
  }
  function tickerRelationship(row,primary=false) {
    const cell=(label,value)=>`<div><dt>${label}</dt><dd>${value}</dd></div>`;
    const lens='directional',meets=row.qualifies;
    return `<section class="${primary?'relationship-context':'ticker-relationship'}" ${primary?`data-current-theme="${esc(row.theme_id)}" data-current-w="${esc(row.relative?.w)}" data-current-role="${esc(row.role)}"`:''}><div class="relationship-heading"><h3>${themeLink(row.theme_id,lens)}</h3>${!primary?tickerLink(row.ticker,row.theme_id,lens):''}</div><dl class="relationship-metrics">${cell('Role',roleLabel(row.role))}${cell('Peer-relative strength '+helpButton('w'),`<span class="${primary?'w-value ':''}${signTone(row.relative?.w)}">${points(row.relative?.w)}</span>`)}${cell('Research list',meets?'Included today':'Not included today')}${cell('Liquidity',esc(eligibility(row)))}</dl>${primary&&earningsEnabled()?`<p class="table-note">Earnings · ${earnings(row.ticker)}</p>`:''}<details class="liquidity-details"><summary>Peer returns and liquidity</summary><dl class="relationship-metrics">${cell('1M return vs peers',points(row.relative?.er1))}${cell('3M return vs peers',points(row.relative?.er3))}${cell('Close',money(row.eligibility?.close))}${cell('Average volume · '+(v2().liquidity?.liquidity_sessions||20)+' sessions',number(row.eligibility?.average_volume,0))}${cell('Average dollar volume · '+(v2().liquidity?.liquidity_sessions||20)+' sessions',money(row.eligibility?.average_dollar_volume))}</dl></details></section>`;
  }
  function renderTickerInspector() {
    const ticker=inspector.id,rows=(snapshot?.relationships||[]).filter(r=>r.ticker===ticker).sort((a,b)=>name(a.theme_id).localeCompare(name(b.theme_id)));
    const assigned=snapshot?.exports?.assignments?.[ticker]?.assigned_section;
    const lead=inspector.context?rows.find(r=>r.theme_id===inspector.context):rows.find(r=>r.theme_id===assigned)||rows[0];
    const others=rows.filter(r=>r!==lead),lens=inspector.lens||'directional',company=research().companies?.[ticker];
    $('inspector-content').innerHTML=`${company?`<p class="ticker-company">${esc(company)}</p>`:''}<div class="inspector-subhead"><span>Stock research</span>${saveButton(ticker,'inspector-ticker',lead?.theme_id||inspector.context,lens)}</div>${lead?tickerRelationship(lead,true):empty('Relationship unavailable',inspector.context?name(inspector.context)+' is not a current relationship.':'No current theme relationships. Your bookmark is retained.')}<details class="other-relationships"><summary>Other relationships · ${others.length}</summary>${others.map(r=>tickerRelationship(r)).join('')||'<p class="table-note">No other current relationships.</p>'}</details>`;
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
    const title = isDetail ? name(detailId()) : part==='primary'?'Research list':part.charAt(0).toUpperCase() + part.slice(1);
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
    const scroll = window.scrollY, themeScroll = $('theme-table').scrollTop,previousMarket=snapshot?.market_direction;
    interactions.closeHelp();snapshot=data;snapshotSignature=signature;
    $('research-version-notice').hidden=Boolean(v2().schema);
    $('research-version-notice').textContent=publicSnapshot?'This frozen snapshot uses previous research rules. Open a current snapshot for the new research list.':'This stored snapshot uses previous research rules. Refresh Data to calculate the current research list.';
    ui.candidateLens='directional';
    for (const url of blobUrls.values()) URL.revokeObjectURL(url); blobUrls.clear();
    renderLayer(); renderOverview();
    const rules=v2().liquidity;
    if(rules){
      $('method-state-rule').textContent=`Structural boundary: ${rules.structural_boundary} points. A change of at least ${rules.material_score_change} points over ${rules.change_sessions} completed sessions is material. Short-side strength uses 100 minus structural strength, with the change direction reversed.`;
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
    if (button.id === 'display-toggle') { const open = $('display-panel').hidden; $('display-panel').hidden = !open; button.setAttribute('aria-expanded',String(open)); if (open) $('display-close').focus(); return; }
    if (button.id === 'display-close') { closeDisplay(); $('display-toggle').focus(); return; }
    if (button.dataset.density) { display.density = button.dataset.density; applyDisplay(true); return; }
    if (button.dataset.textStep) { display.text = Math.max(100,Math.min(200,display.text + Number(button.dataset.textStep))); applyDisplay(true); return; }
    if (button.dataset.save) { changeSaved(button.dataset.save,false,button.dataset.saveTheme||'',button.dataset.saveLens||''); return; }
    if (button.dataset.remove) { changeSaved(button.dataset.remove,true); return; }
    if (button.dataset.universe) { ui.universe=button.dataset.universe; if(ui.universe!=='active'){$('theme-priority').value='';$('theme-trend').value='';ui.themeSort='name';ui.themeDescending=false;} renderThemes();requestAnimationFrame(UX.indicators);return;}
    if (button.dataset.themeSort) {
      const key = button.dataset.themeSort, focused = focusKey();
      ui.themeDescending = ui.themeSort === key ? !ui.themeDescending : ['score','return1','return3','breadth'].includes(key); ui.themeSort = key; renderThemes(); restoreFocus(focused); return;
    }
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
    if (id === 'theme-mobile-sort') { const [key,direction] = event.target.value.split(':'); ui.themeSort = key; ui.themeDescending = direction === 'desc'; renderThemes(); $('theme-mobile-sort')?.focus(); }
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
  document.addEventListener('keydown',event => { if (event.key === 'Escape' && !$('display-panel').hidden) { closeDisplay(); $('display-toggle').focus(); } });
  document.addEventListener('click',event => { if (!$('display-panel').hidden && !event.target.closest('#display-panel, #display-toggle')) closeDisplay(); });
  document.addEventListener('change',event => { if (event.target.id === 'display-motion' || event.target.id === 'display-contrast') { display.motion = $('display-motion').checked; display.contrast = $('display-contrast').checked; applyDisplay(true); } });
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
  applyDisplay();
  history.scrollRestoration = 'manual';
  document.querySelectorAll('[data-nav]').forEach(link => { link.querySelector('.nav-icon').innerHTML = icon(link.dataset.nav); });
  document.querySelector('.brand-mark').innerHTML = icon('orbit');
  $('inspector-back').innerHTML=icon('back');
  document.querySelectorAll('a span[aria-hidden="true"]').forEach(span => { if (span.textContent === '↗') span.innerHTML = icon('up'); });
  renderSaved();showRoute(true);
  if (publicSnapshot) { render(window.THEMESCOPE_STATIC_SOURCE.snapshot); showStatus({state:'success',progress:'Market data fixed',target_session:snapshot.session,last_successful_refresh:snapshot.refreshed_at,completeness:snapshot.completeness,provider_health:snapshot.provider_health}); }
  else if (preview) { render(window.FIXTURE_SNAPSHOT); showStatus({state:'success',progress:'Synthetic inspection fixture',target_session:snapshot.session,last_successful_refresh:'Inspection fixture',completeness:snapshot.completeness,provider_health:'Fixture'}); }
  else { poll(); setInterval(poll,1500); }
})();
