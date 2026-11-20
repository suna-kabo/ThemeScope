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
  const iconPaths = {back:'M19 12H5m6-6-6 6 6 6',up:'M6 18 18 6M6 6h12v12',down:'M6 6l12 12M6 18h12V6',flat:'M4 12h16m-4-4 4 4-4 4M8 8l-4 4 4 4',saved:'m12 3 2.8 5.8 6.4.9-4.6 4.5 1.1 6.4-5.7-3-5.7 3 1.1-6.4L2.8 9.7l6.4-.9L12 3z'};
  const icon = key => `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${iconPaths[key] || iconPaths.flat}"/></svg>`;
  const tone = value => /bullish|positive|long/i.test(value || '') ? 'positive' : /bearish|negative|short/i.test(value || '') ? 'negative' : /mixed/i.test(value || '') ? 'mixed' : 'neutral';
  const signTone = value => !valid(value) || Number(value) === 0 ? 'neutral' : Number(value) > 0 ? 'positive' : 'negative';
  const symbol = value => icon(tone(value) === 'positive' ? 'up' : tone(value) === 'negative' ? 'down' : 'flat');
  const state = value => `<span class="state ${tone(value)}"><span aria-hidden="true">${symbol(value)}</span>${esc(value || 'Unavailable')}</span>`;
  const savedKey = 'themescope-vnext-watchlist';
  const savedContextKey = 'themescope-vnext-saved-context';
  let snapshot = null, loadedVersion, currentStatus = {}, route = '', origin = '#themes', themeOriginFocus, feedbackTimer, requestError = '';
  let initialLoading = true;
  let savedContexts = {}, watched = [];
  const ui = {universe:'active', themeSort:'score', themeDescending:true, selectedTheme:'', selectedTicker:'', selectedTickerTheme:'', candidateMode:'unique'};
  const positions = new Map(), memberViews = new Map();
  function memberView(id) {
    if (!memberViews.has(id)) memberViews.set(id,{memberSearch:'',memberRole:'',memberEligibility:'',memberSort:'priority'});
    return memberViews.get(id);
  }
  let inspector = null, inspectorTrigger = '', inspectorOrigin = '', inspectorScroll = 0;
  const inspectorViews = new Map();
  let closingInspector=false;
  let mapSelected='',mapFocusId='',mapResizeTimer;
  let mapWidth = 800;
  const mapHeight = 280, mapPadding = {left:66,right:24,top:24,bottom:50};
  const name = id => snapshot?.themes?.find(t => t.theme_id === id)?.name || id || 'Unavailable';
  const themeHref = id => '#themes/' + encodeURIComponent(id);
  const helpButton = key => `<button type="button" class="metric-help" data-help="${key}" data-focus-key="help:${key}" aria-label="About ${esc(UX.help[key]?.[0]||key)}" aria-expanded="false" aria-controls="metric-tooltip">?</button>`;
  const tickerLink = (ticker,themeId='') => `<a class="ticker ticker-link" href="#primary?ticker=${encodeURIComponent(ticker)}${themeId?'&context='+encodeURIComponent(themeId):''}" data-inspect-ticker="${esc(ticker)}" data-context-theme="${esc(themeId)}" data-focus-key="ticker:${esc(ticker)}${themeId?':'+esc(themeId):''}">${esc(ticker)}</a>`;
  const themeLink = (id, focusPrefix='theme') => `<a class="theme-link" href="${themeHref(id)}" data-focus-key="${focusPrefix}:${esc(id)}">${esc(name(id))}</a>`;
  const quickView = id => `<button type="button" class="button quiet small" data-inspect-theme="${esc(id)}" data-focus-key="quick:${esc(id)}" aria-label="Quick View for ${esc(name(id))}">Quick View</button>`;
  const saveButton = (ticker,location,themeId='') => `<button class="save-button" data-save="${esc(ticker)}" data-save-theme="${esc(themeId)}" data-focus-key="${esc(location+':'+ticker)}" aria-pressed="${watched.includes(ticker)}" aria-label="${watched.includes(ticker)?'Saved '+esc(ticker)+'; remove from Saved':'Save '+esc(ticker)}">${icon('saved')}<span class="sr-only">${watched.includes(ticker)?'Saved':'Save'}</span></button>`;
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
  function download(themeId) {
    const text = themeId ? snapshot?.exports?.individual?.[themeId] : snapshot?.exports?.combined;
    if (!currentResearch() || text == null || text === '') return null;
    return themeId ? `/api/exports/${encodeURIComponent(themeId)}.txt` : '/api/exports/combined.txt';
  }
  function themeDownload(themeId) {
    const url = download(themeId);
    return url ? `<a class="button secondary small" href="${esc(url)}" download data-export="TradingView watchlist" aria-label="TradingView TXT for ${esc(name(themeId))}">TradingView TXT <span aria-hidden="true">↓</span></a>` : '';
  }
  function renderExportMenu() {
    const url=download();
    const body=`<p class="menu-title">TradingView · ${esc(snapshot?.session||'No snapshot')}</p>`+
      (url?`<a id="combined" href="${esc(url)}" download data-export="Primary research">Full research list <span aria-hidden="true">↓</span></a><p class="menu-scope">Full session list in research order. Filters affect this view only.</p>`:
        '<p class="export-unavailable">No current research list to export.</p>');
    if($('export-options').innerHTML!==body)$('export-options').innerHTML=body;
  }
  function renderLayer() {
    $('fixture-banner').hidden = !snapshot?.synthetic_fixture;
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
  const v2 = () => UX.currentContract(snapshot) ? snapshot.research_v2 : {};
  const themeResearch = id => v2().themes?.[id] || {};
  const researchState = id => UX.themeState(snapshot,id);
  const stateTone = value => ({Leading:'leader',Improving:'improving',Fading:'fading',Lagging:'lagging'})[value] || 'neutral';
  const primaryThemeState = id => `<span class="theme-state ${stateTone(researchState(id))}">${esc(researchState(id))}</span>`;
  const rawState = id => themeResearch(id).raw_state || 'Unavailable';
  const rawStateLabel = id => {
    const label=rawState(id), tone=({Strong:'positive', Improving:'positive', Fading:'mixed', Weak:'muted'})[label]||'muted';
    return `<span class="raw-theme-state ${tone}">${esc(label)}</span>`;
  };
  const researchOrder = id => themeResearch(id).research_order_index ?? null;
  const currentSide = () => UX.currentSide(snapshot);
  const currentResearch = () => UX.currentContract(snapshot);
  const sideLabel = () => currentSide()==='long'?'Long-side research':currentSide()==='short'?'Short-side research':'Non-directional context';
  const recentValue = id => themeResearch(id).recent?.score_change;
  function recentChange(id) {
    const recent=themeResearch(id).recent,value=recentValue(id);
    if(!recent?.available)return `<span class="unavailable" title="${esc(UX.comparisonMessage(recent?.reason))}"><span class="comparison-short" aria-hidden="true">Unavailable</span><span class="comparison-reason">${esc(UX.comparisonMessage(recent?.reason))}</span></span>`;
    return `<span class="numeric ${signTone(value)}">${Number(value)>0?'+':''}${number(value,1)} pts</span>`;
  }
  function primaryThemes() {
    return (snapshot?.themes || []).filter(t => themeResearch(t.theme_id).researchable).sort((a,b)=>researchOrder(a.theme_id)-researchOrder(b.theme_id)||a.theme_id.localeCompare(b.theme_id));
  }
  function qualifiedRows() { return UX.researchRows(snapshot); }
  function uniqueRows(rows) {
    const tickers=new Map();for(const row of rows)if(!tickers.has(row.ticker))tickers.set(row.ticker,row);
    return [...tickers.values()];
  }
  // Display transforms only: all breadth, returns, scores and trend come from the snapshot.
  function breadthBar(label,value,coverage = '') {
    const available = valid(value), bounded = available ? Math.max(0,Math.min(100,Number(value))) : 0;
    return `<div class="breadth-bar"><span class="breadth-label">${esc(label)}</span><svg viewBox="0 0 100 6" preserveAspectRatio="none" aria-hidden="true" focusable="false"><rect class="breadth-track" width="100" height="6" rx="2"/>${available ? `<rect class="breadth-fill" width="${bounded}" height="6" rx="2"/>` : ''}</svg><strong>${valid(value)?number(value,0)+'%':'—'}</strong>${coverage ? `<small>${esc(coverage)}</small>` : ''}</div>`;
  }
  function mapThemes() { return (snapshot?.themes || []).filter(t=>t.status === 'active' && valid(t.returns?.[0]?.value) && valid(t.returns?.[1]?.value)); }
  function mapDescription(t) { return `${t.name || t.theme_id} · Theme Score ${number(t.score)} · 1M ${percent(t.returns?.[0]?.value,100,true)} · 3M ${percent(t.returns?.[1]?.value,100,true)} · ${researchState(t.theme_id)}`; }
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
    const point=t=>{const cx=x(Number(t.returns[0].value)),cy=y(Number(t.returns[1].value)),cls='neutral';const shape=`<circle cx="${cx}" cy="${cy}" r="4.5"/>`;return `<g role="button" tabindex="${t.theme_id===mapFocusId?0:-1}" data-map-theme="${esc(t.theme_id)}" data-focus-key="map:${esc(t.theme_id)}" class="map-point ${cls} ${t.theme_id===mapSelected?'map-selected':''}" aria-pressed="${t.theme_id===mapSelected}" aria-label="${esc(mapDescription(t))}"><title>${esc(mapDescription(t))}</title><circle class="point-hit" cx="${cx}" cy="${cy}" r="12"/><circle class="point-ring" cx="${cx}" cy="${cy}" r="9"/>${shape}</g>`;};
    $('theme-map').innerHTML=`<div class="map-toolbar"><p>${rows.length} themes · median returns</p><label class="inline-label">Focus theme<select id="map-selection" data-focus-key="map-selection">${rows.map(t=>`<option value="${esc(t.theme_id)}">${esc(t.name||t.theme_id)}</option>`).join('')}</select></label></div><div class="map-layout"><div class="map-chart"><div class="map-axis-label">3M return ↑</div><svg id="theme-map-svg" viewBox="0 0 ${mapWidth} ${mapHeight}" role="group" aria-label="Theme Returns Map. Arrow keys inspect themes; Enter selects. Open research from the readout." data-xmin="${xd.low}" data-xmax="${xd.high}" data-ymin="${yd.low}" data-ymax="${yd.high}"><rect class="map-field" x="${mapPadding.left}" y="${mapPadding.top}" width="${width}" height="${height}"/><line class="map-zero" x1="${x(0)}" y1="${mapPadding.top}" x2="${x(0)}" y2="${mapHeight-mapPadding.bottom}"/><line class="map-zero" x1="${mapPadding.left}" y1="${y(0)}" x2="${mapWidth-mapPadding.right}" y2="${y(0)}"/>${xt}${yt}${rows.map(point).join('')}</svg><div class="map-axis-label map-x-label">1M return →</div></div><div id="map-readout" class="map-readout" aria-live="polite"></div></div><div class="map-footer"><a class="text-link" href="#themes">Compare themes</a></div>`;
    $('map-selection').value=mapSelected;showMapReadout(mapSelected);
  }
  function showMapReadout(id,select=false) {
    const t=mapThemes().find(t=>t.theme_id===id);if(!t||!$('map-readout'))return;
    if(select){mapSelected=id;mapFocusId=id;$('map-selection').value=id;document.querySelectorAll('[data-map-theme]').forEach(n=>{const selected=n.dataset.mapTheme===id;n.classList.toggle('map-selected',selected);n.setAttribute('aria-pressed',String(selected));n.tabIndex=selected?0:-1;});}
    $('map-readout').innerHTML=`<h3>${esc(name(id))}</h3><dl><div><dt>Theme Score</dt><dd>${number(t.score,1)}</dd></div><div><dt>1M</dt><dd class="${signTone(t.returns[0].value)}">${percent(t.returns[0].value,100,true)}</dd></div><div><dt>3M</dt><dd class="${signTone(t.returns[1].value)}">${percent(t.returns[1].value,100,true)}</dd></div></dl><p>${primaryThemeState(t.theme_id)}</p><a class="button secondary" href="${themeHref(id)}" data-focus-key="map-open:${esc(id)}">Open theme</a>`;
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
    $('theme-map-panel').hidden=!snapshot;
    if(!snapshot){$('market-direction').innerHTML=empty('No completed snapshot','Open Snapshot and refresh and select Refresh Data.');$('market-cards').innerHTML='';$('market-continuation').innerHTML='';return;}
    const direction=marketName(snapshot.market_direction),changes=v2().changes||{},decision=snapshot.market?.decision||{};
    const changed=changes.changed?`From ${marketName(changes.previous_market_direction)}`:changes.previous_market_direction?'Unchanged since previous session':'No previous comparison';
    $('market-direction').innerHTML=`<div class="bias-line"><div class="bias-title"><span class="eyebrow">Market Bias</span><h2 class="direction-name ${tone(direction)}" aria-label="Market Bias: ${esc(direction)}">${esc(direction)}</h2><span class="market-change"><span class="${changes.previous_market_direction?'':'comparison-unavailable'}">${esc(changed)}</span>${v2().conviction==='selective'?' \u00b7 Reduced conviction':''}</span></div><div class="bias-action">${!currentResearch()?'<p>Current research list unavailable \u00b7 previous rules snapshot</p>':currentSide()?`<span>${sideLabel()}</span><a href="#themes">${primaryThemes().length} researchable themes <span aria-hidden="true">\u2192</span></a>`:'<p>No directional research list</p><a href="#themes">Explore theme context \u2192</a>'}</div></div><details class="decision-details"><summary>Decision evidence</summary><p id="decision-path">${esc(decision.reason||'Market context unavailable.')}</p><p id="today-plan">${esc(snapshot.today_plan||'')}</p><p>Breadth: ${esc(snapshot.market?.breadth_consensus||'Unavailable')}</p></details>`;
    renderBenchmarks();renderThemeMap();
    const leaders=primaryThemes().slice(0,3);
    $('market-continuation').innerHTML=`<section class="research-next"><div class="section-heading"><h2>Next in research</h2><a href="#themes" class="text-link">All themes \u2192</a></div>${leaders.length?`<ol class="next-themes">${leaders.map(t=>`<li><div>${themeLink(t.theme_id)}<small>${primaryThemeState(t.theme_id)}</small></div><span>${recentChange(t.theme_id)}</span></li>`).join('')}</ol><a href="#primary" class="queue-entry"><span>Primary research</span><strong>${v2().list?.stock_count??uniqueRows(qualifiedRows()).length} stocks <span aria-hidden="true">\u2192</span></strong></a>`:'<a href="#themes" class="queue-entry">All themes <span aria-hidden="true">\u2192</span></a>'}</section>`;
  }

  function setOptions(id, options) {
    const select = $(id), first = select.options[0].outerHTML, previous = select.value;
    const html = first + options.map(([value, text]) => `<option value="${esc(value)}">${esc(text)}</option>`).join('');
    if (select.innerHTML !== html) { select.innerHTML = html; select.value = options.some(([value]) => value === previous) ? previous : ''; }
  }
  function themeValue(theme, key) {
    if (key === 'name') return theme.name || theme.theme_id;
    if (key === 'score') return valid(theme.score) ? Number(theme.score) : null;
    if (key === 'recent') return valid(recentValue(theme.theme_id))?Number(recentValue(theme.theme_id)):null;
    return null;
  }
  function compareValues(a, b, descending = false) {
    if (a == null) return b == null ? 0 : 1;
    if (b == null) return -1;
    const order = typeof a === 'number' ? a - b : String(a).localeCompare(String(b));
    return descending ? -order : order;
  }
  function themeRows() {
    const query = $('theme-search').value.trim().toLowerCase();
    return (snapshot?.themes || []).filter(t => (ui.universe === 'active' ? t.status === 'active' : t.status !== 'active') && (!query || `${t.name} ${t.theme_id} ${t.family}`.toLowerCase().includes(query)) && (!$('theme-family').value || t.family === $('theme-family').value) && (!$('theme-state-filter').value || rawState(t.theme_id) === $('theme-state-filter').value)).sort((a, b) => compareValues(themeValue(a, ui.themeSort), themeValue(b, ui.themeSort), ui.themeDescending) || a.theme_id.localeCompare(b.theme_id));
  }
  function renderThemeMovement() {
    const themes=(snapshot.themes||[]).filter(t=>t.status==='active');
    const comparable=themes.filter(t=>valid(recentValue(t.theme_id)));
    const unavailable=themes.length-comparable.length;
    $('movement-availability').textContent=unavailable?` · ${unavailable} unavailable`:'';
    $('movement-body').innerHTML=`<div class="movement-groups">${[1,-1].map(direction=>{
      const entries=comparable.filter(t=>direction*Number(recentValue(t.theme_id))>0)
        .sort((a,b)=>compareValues(Number(recentValue(a.theme_id)),Number(recentValue(b.theme_id)),direction>0)||a.theme_id.localeCompare(b.theme_id))
        .slice(0,3);
      return `<section><h3>${direction>0?'Largest gains':'Largest declines'}</h3>${entries.length?
        `<ol>${entries.map(t=>`<li>${themeLink(t.theme_id,'movement')}${recentChange(t.theme_id)}</li>`).join('')}</ol>`:
        `<p class="table-note">${direction>0?'No gains':'No declines'}</p>`}</section>`;
    }).join('')}</div>${unavailable?'<p class="table-note">Themes with unavailable comparisons stay in the table below.</p>':''}`;
  }
  function renderThemes() {
    if(initialLoading)return;
    const tracked=ui.universe==='active';
    $('theme-movement').hidden=!tracked||!snapshot;
    $('active-count').textContent=(snapshot?.themes||[]).filter(t=>t.status==='active').length;
    $('watch-count').textContent=(snapshot?.themes||[]).filter(t=>t.status!=='active').length;
    document.querySelectorAll('[data-universe]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.universe===ui.universe)));
    $('theme-state-filter').closest('label').hidden=!tracked;
    const count=['theme-family','theme-state-filter'].filter(id=>$(id).value).length;
    document.querySelector('.theme-filter-menu>summary').textContent='Filters'+(count?' ('+count+')':'');
    const rows=themeRows();
    $('theme-results').textContent=tracked ? `${rows.length} ${rows.length===1?'theme':'themes'}` : `${rows.length} untracked concepts`;
    $('theme-sort').value=`${ui.themeSort}:${ui.themeDescending?'desc':'asc'}`;
    if(!rows.length){$('theme-table').innerHTML=empty(snapshot?'No themes match':'Themes are waiting',snapshot?'Try another search or reset the filters.':'Open Snapshot and refresh and select Refresh Data.','<button class="button secondary" data-reset="themes">Reset filters</button>');return;}
    if(!tracked){$('theme-table').innerHTML='<ul class="concept-list">'+rows.map(t=>`<li>${themeLink(t.theme_id)}<span>${esc(t.family)}</span></li>`).join('')+'</ul>';return;}
    $('theme-table').innerHTML=`<div class="theme-ledger-head" aria-hidden="true"><span>Theme</span><span>Theme Score</span><span>State</span><span>5-session Change</span><span>1M / 3M</span></div><ol class="theme-ledger" aria-label="Tracked themes">${rows.map(t=>{
      const id=t.theme_id;
      return `<li data-theme-row="${esc(id)}" class="theme-line ${ui.selectedTheme===id?'selected-row':''}"><div class="theme-identity"><div>${themeLink(id)}<small>${esc(t.family)}</small><div class="theme-actions">${quickView(id)}${themeDownload(id)}</div></div></div><div class="score-cell"><span class="mobile-label">Theme Score</span><strong class="numeric">${number(t.score,1)}</strong></div><div class="state-cell"><span class="mobile-label">State</span>${rawStateLabel(id)}</div><div class="change-cell"><span class="mobile-label">5-session Change</span>${recentChange(id)}</div><div class="return-cell"><span class="mobile-label">1M / 3M</span><span class="${signTone(t.returns?.[0]?.value)}">${percent(t.returns?.[0]?.value,100,true)}</span><span aria-hidden="true"> / </span><span class="${signTone(t.returns?.[1]?.value)}">${percent(t.returns?.[1]?.value,100,true)}</span></div></li>`;
    }).join('')}</ol>`;
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
    return `<li data-ticker-row="${esc(row.ticker)}" data-relationship-theme="${esc(row.theme_id)}" class="queue-row ${selected?'selected-row':''}"><span class="queue-position" aria-hidden="true">${String(index+1).padStart(2,'0')}</span><div class="queue-stock">${tickerLink(row.ticker,row.theme_id)}<small class="row-company">${esc(research().companies?.[row.ticker]||'')}</small></div>${withTheme?`<div class="queue-theme">${themeLink(row.theme_id)}<small class="col-role">${roleLabel(row.role)}</small></div>`:`<span class="col-role sr-only">${roleLabel(row.role)}</span>`}<div class="queue-peer"><span class="mobile-label">Peer strength</span><span class="numeric ${signTone(row.relative?.w)}">${points(row.relative?.w)}</span></div>${earningsEnabled()?`<div class="queue-earnings table-note"><span class="mobile-label">Earnings</span>${earnings(row.ticker)}</div>`:''}${saveButton(row.ticker,location+':'+row.theme_id,row.theme_id)}</li>`;
  }

  function matchesCandidate(row) {
    const query=$('candidate-search').value.trim().toLowerCase(),filter=$('candidate-theme').value;
    return (!query||`${row.ticker} ${research().companies?.[row.ticker]||''} ${name(row.theme_id)}`.toLowerCase().includes(query))&&(!filter||row.theme_id===filter)&&(!$('candidate-role').value||row.role===$('candidate-role').value)&&(!$('candidate-earnings').value||(earningsDates(row.ticker).length>0)===($('candidate-earnings').value==='available'));
  }
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
      $('candidates').innerHTML=empty('Research update required','This stored snapshot uses previous rules. Open Snapshot and refresh and select Refresh Data to calculate the current list. Themes and Saved remain available.');return;
    }
    const enabled=earningsEnabled(),earningsFilter=$('candidate-earnings');
    if(!enabled)earningsFilter.value='';earningsFilter.closest('label').hidden=!enabled;
    setOptions('candidate-theme',(snapshot?.themes||[]).filter(t=>qualifiedRows().some(r=>r.theme_id===t.theme_id)).sort((a,b)=>name(a.theme_id).localeCompare(name(b.theme_id))).map(t=>[t.theme_id,t.name||t.theme_id]));
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
    if(!grouped)return `<div class="research-queue ${earningsEnabled()?'has-earnings':''}"><div class="queue-head" aria-hidden="true"><span>#</span><span>Stock</span><span>Theme</span><span>Peer strength (pp)</span>${earningsEnabled()?'<span>Earnings</span>':''}<span>Save</span></div><ol aria-label="${esc(label)}">${rows.map((r,i)=>candidateRow(r,"primary",true,i)).join('')}</ol></div>`;
    const groups=new Map();for(const row of rows){if(!groups.has(row.theme_id))groups.set(row.theme_id,[]);groups.get(row.theme_id).push(row);}
    let position=0;
    return [...groups].map(([id,members])=>`<section class="queue-chapter" aria-label="${esc(name(id))}"><header class="chapter-heading"><span class="eyebrow">${String([...groups.keys()].indexOf(id)+1).padStart(2,'0')}</span><h2>${themeLink(id)}</h2><div>${primaryThemeState(id)}</div><div class="theme-actions">${quickView(id)}${themeDownload(id)}</div></header><div class="chapter-stocks"><span class="chapter-peer-label">Peer strength (pp) ${helpButton('w')}</span><ol class="chapter-queue" aria-label="${esc(name(id))} stocks">${members.map(r=>candidateRow(r,"primary",false,position++)).join('')}</ol></div></section>`).join('');
  }

  function memberRows(themeId) {
    const view = memberView(themeId);
    const rows = (snapshot?.relationships || []).filter(r => r.theme_id === themeId && (!view.memberSearch || r.ticker.toLowerCase().includes(view.memberSearch.toLowerCase())) && (!view.memberRole || r.role === view.memberRole) && (!view.memberEligibility || eligibility(r) === view.memberEligibility));
    rows.sort((a,b) => view.memberSort === 'ticker'||view.memberSort==='priority'&&!currentSide() ? a.ticker.localeCompare(b.ticker) : compareValues(valid(a.relative?.w) ? Number(a.relative.w) : null,valid(b.relative?.w) ? Number(b.relative.w) : null, view.memberSort === 'w-desc'||view.memberSort==='priority'&&currentSide()==='long') || a.ticker.localeCompare(b.ticker));
    return rows;
  }
  function renderMembers(themeId) {
    const rows=memberRows(themeId),total=(snapshot?.relationships||[]).filter(r=>r.theme_id===themeId).length;
    $('member-count').textContent=`${rows.length} of ${total} reviewed relationships`;
    $('member-table').innerHTML=rows.length?`<ol class="member-ledger" aria-label="${esc(name(themeId))} members">${rows.map(r=>`<li><div class="member-identity">${tickerLink(r.ticker,r.theme_id)}<small>${roleLabel(r.role)}</small></div><div class="member-comparison"><span class="metric-label">Peer strength</span><span class="numeric ${signTone(r.relative?.w)}">${points(r.relative?.w)}</span></div><div class="member-status"><span>${esc(eligibility(r))}</span><small>${researchStatus(r)}</small>${earningsEnabled()?`<small>Earnings ${earnings(r.ticker)}</small>`:''}</div>${saveButton(r.ticker,'member:'+themeId,r.theme_id)}</li>`).join('')}</ol>`:empty(total?'No members match':'No reviewed members',total?'Try another filter.':'No reviewed members are available.');
  }
  function renderDetail(themeId) {
    if(initialLoading){$('detail-content').innerHTML='<p class="loading-state">Loading theme research…</p>';return;}
    const theme=snapshot?.themes?.find(t=>t.theme_id===themeId);
    if(!theme){$('detail-content').innerHTML='<a href="#themes" class="back-link">← Back to Themes</a>'+empty('Theme unavailable','This theme is not in the current snapshot.');return;}
    if(theme.status!=='active'){$('detail-content').innerHTML=`<a href="#themes" class="back-link">← Back to Themes</a><h1 id="detail-title" tabindex="-1">${esc(theme.name||themeId)}</h1>${empty('Not currently tracked','This concept has no reviewed calculation basket.') }`;return;}
    const view = memberView(themeId);
    const originName=origin.startsWith('#primary')?'Primary':origin.startsWith('#saved')?'Saved':origin.startsWith('#overview')?'Market':'Themes';
    $('detail-content').innerHTML=`<div class="crumbs"><a href="${esc(origin)}" class="back-link" data-return-theme="${esc(themeId)}">&#8592; ${originName}</a>${themeDownload(themeId)}</div><header class="full-theme-heading"><h1 id="detail-title" tabindex="-1">${esc(theme.name||themeId)}</h1><span>${esc(theme.family)}</span></header><div class="full-theme-evidence">${themeEvidence(theme)}</div><div class="section-heading"><h2>Member stocks</h2><span id="member-count" class="table-meta"></span></div><form id="member-filters" class="filter-bar" role="search" aria-label="Filter theme members"><label class="search-field">Search members<input id="member-search" type="search" placeholder="Ticker…" value="${esc(view.memberSearch)}"></label><label>Role<select id="member-role"><option value="">All roles</option><option value="Core">Core business</option><option value="Enabler">Supporting business</option><option value="Related">Related context</option></select></label><label>Eligibility<select id="member-eligibility"><option value="">All states</option><option>Liquidity eligible</option><option>Liquidity ineligible</option><option>Unavailable</option></select></label><label>Sort<select id="member-sort"><option value="priority">${currentSide()?'Peer priority':'Context order (A–Z)'}</option><option value="ticker">Ticker A–Z</option><option value="w-desc">Peer strength high to low</option><option value="w-asc">Peer strength low to high</option></select></label></form><div id="member-table" class="table-wrap member-table" role="region" tabindex="0" aria-label="Theme member research"></div>`;
    $('member-role').value=view.memberRole;$('member-eligibility').value=view.memberEligibility;$('member-sort').value=view.memberSort;renderMembers(themeId);
  }

  function savedContext(ticker,rows) {
    return savedContexts[ticker] || snapshot?.exports?.assignments?.[ticker]?.assigned_section || (rows.length===1?rows[0].theme_id:'');
  }
  function renderSaved() {
    $('saved-count').textContent=watched.length;
    if(!watched.length){$('saved').innerHTML=empty('No saved stocks','Use the star beside a stock to save it here.');return;}
    $('saved').innerHTML='<p class="saved-scope">Saved on this computer</p><div class="saved-list">'+watched.map(ticker=>{
      const rows=(snapshot?.relationships||[]).filter(r=>r.ticker===ticker),context=savedContext(ticker,rows),lead=rows.find(r=>r.theme_id===context);
      const status=!snapshot?'Snapshot loading':!lead?'Relationship unavailable':researchStatus(lead,'On today’s research list','Outside today’s research list');
      return `<article class="saved-row ${earningsEnabled()?'has-earnings':''}">${tickerLink(ticker,context)}<div class="saved-context">${context?themeLink(context):'No theme selected'}<small>${status}</small></div><span class="numeric ${signTone(lead?.relative?.w)}">Peer strength ${points(lead?.relative?.w)}${lead?`<small class="saved-w-theme">vs ${esc(name(lead.theme_id))} peers</small>`:''}</span>${earningsEnabled()?`<span class="table-note">${earnings(ticker)}</span>`:''}<button class="button quiet small" data-remove="${esc(ticker)}" data-focus-key="saved-remove:${esc(ticker)}" aria-label="Remove ${esc(ticker)} from Saved">Remove</button></article>`;
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
  let savedReady = false, saving = false;
  function applySaved(entries) {
    savedContexts=entries;
    watched=Object.keys(entries);
    syncSaveButtons();
  }
  async function writeSaved(entries,merge=false) {
    const response=await fetch('/api/saved',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({entries,merge})});
    if(!response.ok)throw Error('Saved research unavailable');
    return response.json();
  }
  async function loadSaved(mode) {
    const response=await fetch('/api/saved');
    if(!response.ok)throw Error('Saved research unavailable');
    let entries=await response.json();
    let legacy={};
    if(mode==='live'){
      try {
        const tickers=JSON.parse(localStorage.getItem(savedKey)||'[]'),contexts=JSON.parse(localStorage.getItem(savedContextKey)||'{}');
        legacy=Object.fromEntries(tickers.filter(t=>typeof t==='string'&&/^[A-Z][A-Z0-9.-]{0,15}$/.test(t)).map(t=>{
          const theme=contexts?.[t]?.theme;
          return [t,typeof theme==='string'&&theme.length<=100&&/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(theme)?theme:''];
        }));
      } catch { /* Unavailable browser storage leaves the application list usable. */ }
    }
    if(Object.keys(legacy).length){
      entries=await writeSaved(legacy,true);
      try { localStorage.removeItem(savedKey); localStorage.removeItem(savedContextKey); } catch {}
    }
    applySaved(entries);
    savedReady=true;
    if(route==='#saved')renderSaved();
  }
  async function changeSaved(ticker, remove=false, themeId='') {
    if(saving)return;
    if(!savedReady){announce('Saved research is connecting. Try again in a moment.');return;}
    saving=true;
    try {
      applySaved(await writeSaved({[ticker]:remove||watched.includes(ticker)?null:themeId}));
      if(route==='#saved'){
        const index=[...document.querySelectorAll('[data-remove]')].findIndex(b=>b.dataset.remove===ticker);
        renderSaved();
        if(!inspector){
          const buttons=document.querySelectorAll('[data-remove]');
          (buttons[Math.min(Math.max(index,0),buttons.length-1)]||$('saved-title')).focus({preventScroll:true});
        }
      }
      announce(`${ticker} ${watched.includes(ticker)?'saved':'removed from Saved'}.`);
    } catch { announce('Saved research is unavailable. Try again.'); }
    finally { saving=false; }
  }
  function inspectorFromLocation() {
    const params = new URLSearchParams((location.hash || '').split('?')[1] || '');
    const kind = params.has('theme') ? 'theme' : params.has('ticker') ? 'ticker' : null;
    const id = kind && params.get(kind);
    return id?{kind,id,context:kind==='ticker'?params.get('context')||'':''}:null;
  }
  function inspectorView() {
    const key=inspector?.kind+':'+inspector?.id+':'+(inspector?.context||'');
    if (!inspectorViews.has(key)) inspectorViews.set(key,{filter:'All',search:'',sort:'ticker'});
    return inspectorViews.get(key);
  }
  function openInspector(kind,id,trigger,context='') {
    if(inspector?.kind===kind&&inspector?.id===id&&(inspector.context||'')===context)return;
    if(!inspector){inspectorTrigger=trigger;inspectorOrigin=route;inspectorScroll=window.scrollY;}
    else {const view=inspectorView();view.scroll=$('research-inspector').scrollTop;view.focus=trigger;}
    const depth=(inspector?Number(history.state?.researchDepth)||0:0)+1;
    const params=new URLSearchParams({[kind]:id});if(context)params.set('context',context);
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
    $('inspector-kind').textContent = inspector.kind === 'theme' ? 'Quick View' : 'Ticker research';
    $('inspector-title').textContent = inspector.kind === 'theme' ? name(inspector.id) : inspector.id;
    $('inspector-status').textContent = ['failed','interrupted'].includes(currentStatus.state) ? 'Refresh failed · previous successful snapshot retained' : 'Completed session ' + (snapshot?.session || '—');
    document.title = $('inspector-title').textContent + ' · Research · ThemeScope';
    if(initialLoading){$('inspector-content').innerHTML='<p class="loading-state">Loading research…</p>';return;}
    if (inspector.kind === 'theme') renderThemeInspector(); else renderTickerInspector();
    if (preserve) { dialog.scrollTop = scroll; restoreFocus(focused); if (textSelection != null) $('inspector-search')?.setSelectionRange(textSelection,textSelection); }
  }
  function themeEvidence(t) {
    const id=t.theme_id,r=themeResearch(id);
    const returns=`${percent(t.returns?.[0]?.value,100,true)} / ${percent(t.returns?.[1]?.value,100,true)}`;
    return `<dl class="raw-theme-summary"><div><dt>Theme Score ${helpButton('strength')}</dt><dd><strong class="numeric">${number(t.score,1)}</strong></dd></div><div><dt>State ${helpButton('raw-state')}</dt><dd>${rawStateLabel(id)}</dd></div><div><dt>5-session Change ${helpButton('score-change')}</dt><dd>${recentChange(id)}</dd></div><div><dt>1M / 3M</dt><dd class="numeric">${returns}</dd></div></dl>
      <details class="theme-provenance price-evidence"><summary>Price context</summary><dl class="evidence-list"><div><dt>Trend</dt><dd>${state(t.index?.trend)}</dd></div><div><dt>Index / EMA21 / EMA50</dt><dd>${number(t.index?.level)} / ${number(t.index?.ema21)} / ${number(t.index?.ema50)}</dd></div></dl></details>
      <details class="theme-provenance"><summary>Participation and comparison</summary><dl class="evidence-list"><div><dt>Participation ${helpButton('breadth')}</dt><dd>${participation(id)}</dd></div><div><dt>5-session comparison</dt><dd>${esc(r.recent?.available?r.recent.comparison_session:UX.comparisonMessage(r.recent?.reason))}</dd></div><div><dt>Basket session</dt><dd>${esc(v2().comparison?.basis_session||snapshot?.session||'Unavailable')}</dd></div><div><dt>Participation change</dt><dd>${valid(r.recent?.breadth_change)?number(r.recent.breadth_change,1)+' pp':'Unavailable'}</dd></div></dl></details>`;
  }
  function renderThemeInspector() {
    const t=snapshot?.themes?.find(row=>row.theme_id===inspector.id);
    if(!t){$('inspector-content').innerHTML=empty('Theme unavailable','This theme is not in the current snapshot.');return;}
    if(t.status!=='active'){$('inspector-content').innerHTML=`<p class="detail-family">${esc(t.family)}</p>${empty('Not currently tracked','No reviewed calculation basket.')}`;return;}
    const v=inspectorView();
    $('inspector-content').innerHTML=`<div class="theme-actions"><a class="button secondary" href="${themeHref(t.theme_id)}">Open full theme</a>${themeDownload(t.theme_id)}</div><p class="inspector-family">${esc(t.family)}</p>${themeEvidence(t)}<div class="section-heading"><h3>Members</h3><span class="table-meta">Peer strength (pp) ${helpButton('w')}</span></div><form class="inspector-member-tools" aria-label="Filter member preview"><label>Search<input id="inspector-search" type="search" placeholder="Ticker" value="${esc(v.search)}" data-focus-key="inspector-search"></label><label>View<select id="inspector-view" data-focus-key="inspector-view"><option value="All">All members</option><option value="Primary">On research list</option><option value="Eligible">Liquidity eligible</option><option value="Core">Core business</option><option value="Enabler">Supporting business</option><option value="Related">Related context</option></select></label></form><p id="inspector-member-count" class="table-meta" role="status"></p><div id="inspector-members"></div>`;
    $('inspector-view').value=v.filter;renderInspectorMembers();
  }
  function renderInspectorMembers() {
    if(inspector?.kind!=='theme'||!$('inspector-members'))return;
    const v=inspectorView(),all=(snapshot?.relationships||[]).filter(r=>r.theme_id===inspector.id);
    const rows=all.filter(r=>(!v.search||r.ticker.toLowerCase().includes(v.search.toLowerCase()))&&(v.filter==='All'||v.filter==='Primary'&&r.qualifies||v.filter==='Eligible'&&r.eligibility?.eligible||r.role===v.filter));
    rows.sort((a,b)=>currentSide()?compareValues(valid(a.relative?.w)?Number(a.relative.w):null,valid(b.relative?.w)?Number(b.relative.w):null,currentSide()==='long')||a.ticker.localeCompare(b.ticker):a.ticker.localeCompare(b.ticker));const preview=rows.slice(0,6);
    $('inspector-member-count').textContent=`${preview.length} of ${rows.length} members`;
    $('inspector-members').innerHTML=preview.length?`<ul class="inspector-member-list">${preview.map(r=>`<li class="preview-row inspector-member-row" data-member-preview="${esc(r.ticker)}"><div>${tickerLink(r.ticker,r.theme_id)}<small>${roleLabel(r.role)}</small></div><span class="numeric ${signTone(r.relative?.w)}">${points(r.relative?.w)}</span>${saveButton(r.ticker,'inspector-member',r.theme_id)}</li>`).join('')}</ul>`:empty('No members match','Try another search or view.');
  }
  function tickerRelationship(row,primary=false) {
    return `<section class="stock-relationship ${primary?'relationship-context':'ticker-relationship'}" ${primary?`data-current-theme="${esc(row.theme_id)}" data-current-w="${esc(row.relative?.w)}" data-current-role="${esc(row.role)}"`:''}><div class="relationship-heading"><h3>${themeLink(row.theme_id)}</h3>${!primary?tickerLink(row.ticker,row.theme_id):''}</div><div class="stock-comparison"><div><span class="metric-label">Peer strength ${helpButton('w')}</span><strong class="${primary?'w-value ':''}${signTone(row.relative?.w)}">${points(row.relative?.w)}</strong></div><div class="stock-membership"><span>${roleLabel(row.role)}</span><small>${researchStatus(row,'Included today','Not included today')}</small></div></div><dl class="evidence-list"><div><dt>1M excess return</dt><dd class="${signTone(row.relative?.er1)}">${points(row.relative?.er1)}</dd></div><div><dt>3M excess return</dt><dd class="${signTone(row.relative?.er3)}">${points(row.relative?.er3)}</dd></div><div><dt>Daily eligibility</dt><dd>${esc(eligibility(row))}</dd></div>${earningsEnabled()?`<div><dt>Earnings</dt><dd>${earnings(row.ticker)}</dd></div>`:''}</dl><details class="liquidity-details"><summary>Liquidity evidence</summary><dl class="evidence-list"><div><dt>Close</dt><dd>${money(row.eligibility?.close)}</dd></div><div><dt>${currentResearch()?v2().policy.liquidity_sessions+'-session average volume':'Average volume'}</dt><dd>${number(row.eligibility?.average_volume,0)}</dd></div><div><dt>${currentResearch()?v2().policy.liquidity_sessions+'-session average dollar volume':'Average dollar volume'}</dt><dd>${money(row.eligibility?.average_dollar_volume)}</dd></div></dl></details></section>`;
  }
  function renderTickerInspector() {
    const ticker=inspector.id,rows=(snapshot?.relationships||[]).filter(r=>r.ticker===ticker).sort((a,b)=>name(a.theme_id).localeCompare(name(b.theme_id)));
    const assigned=snapshot?.exports?.assignments?.[ticker]?.assigned_section;
    const lead=inspector.context?rows.find(r=>r.theme_id===inspector.context):rows.find(r=>r.theme_id===assigned)||rows[0];
    const others=rows.filter(r=>r!==lead),company=research().companies?.[ticker];
    $('inspector-content').innerHTML=`<div class="inspector-subhead"><span class="ticker-company">${esc(company||ticker)}</span>${saveButton(ticker,'inspector-ticker',lead?.theme_id||inspector.context)}</div>${lead?tickerRelationship(lead,true):empty('Relationship unavailable',inspector.context?name(inspector.context)+' is not a current relationship.':'No current theme relationships. Your bookmark is retained.')}<details class="other-relationships"${others.length?'':' hidden'}><summary>Other relationships · ${others.length}</summary>${others.map(r=>tickerRelationship(r)).join('')||'<p class="table-note">No other current relationships.</p>'}</details>`;
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
      if (previousRoute.startsWith('#themes/') && route === origin) {
        restoreFocus(themeOriginFocus);
        if (document.activeElement===view?.querySelector('h1')) {
          view.querySelector(`a[href="${CSS.escape(previousRoute)}"]`)?.focus({preventScroll:true});
        }
      }
    });
  }
  function render(data) {
    if(!data||typeof data!=='object'){
      if(initialLoading){initialLoading=false;$('workspace').setAttribute('aria-busy','false');renderOverview();renderThemes();renderCandidates();renderSaved();if(route.startsWith('#themes/'))renderDetail(detailId());}
      return;
    }
    initialLoading=false;$('workspace').setAttribute('aria-busy','false');
    const focused = focusKey(), memberFocused = document.activeElement?.id?.startsWith('member-') ? {id:document.activeElement.id,start:document.activeElement.selectionStart} : null;
    const scroll = window.scrollY, themeScroll = $('theme-table').scrollTop,previousMarket=snapshot?.market_direction;
    interactions.closeHelp();snapshot=data;
    $('research-version-notice').hidden=currentResearch();
    $('research-version-notice').textContent='This snapshot uses previous research rules. Select Refresh Data to calculate current Themes and Primary research.';
    renderLayer(); renderOverview();
    const rules=v2().policy;
    if(rules){
      const boundary=rules.structural_boundary, threshold=rules.material_score_change;
      $('method-state-rule').textContent=`At ${boundary} or above, the state is Fading when the score falls by at least ${threshold} points and Strong otherwise. Below ${boundary}, the state is Improving when the score rises by at least ${threshold} points and Weak otherwise. Without a comparison, the score alone determines Strong or Weak. A missing score gives Unavailable.`;
      $('method-liquidity-rule').textContent=`Require a completed-session close above $${number(rules.price_floor_exclusive,0)} and average dollar volume of at least ${money(rules.average_dollar_volume_floor)} over ${rules.liquidity_sessions} completed regular sessions.`;
    }
    if(previousMarket&&previousMarket!==snapshot.market_direction&&route==='#overview')UX.move($('market-direction'),'sweep');
    setOptions('theme-family',[...new Set((snapshot.themes || []).map(t => t.family).filter(Boolean))].sort().map(f => [f,f]));
    renderThemeMovement(); renderThemes(); renderCandidates(); renderSaved();
    if (inspector) renderInspector(true);
    if (route.startsWith('#themes/')) { renderDetail(detailId()); document.title = name(detailId()) + ' · ThemeScope'; }
    $('target').textContent = snapshot.session || '—';
    $('theme-table').scrollTop = themeScroll; window.scrollTo(0,scroll); restoreFocus(focused);
    if (memberFocused) { const input = $(memberFocused.id); input?.focus({preventScroll:true}); if (input?.type === 'search' && memberFocused.start != null) input.setSelectionRange(memberFocused.start,memberFocused.start); }
  }
  function showStatus(status) {
    const previous = currentStatus; currentStatus = status;
    const freshness={current:'Current',update_available:'Update available',previous_rules:'Refresh required for current rules',
      configuration_changed:'Refresh required after configuration change',configuration_invalid:'Configuration unavailable'}[status.freshness];
    const failed = ['failed','interrupted'].includes(status.state);
    const progress=status.state==='running'?'Refreshing':failed?
      (snapshot?'Refresh failed, previous snapshot retained':'Refresh failed'):freshness||'Ready';
    if ($('progress').textContent !== progress) $('progress').textContent = progress;
    $('target-detail').textContent = 'Latest safely completed session ' + (status.latest_completed_session || '—');
    $('last-success').textContent = 'Last successful refresh ' + (status.last_successful_refresh || '—');
    const coverage = status.completeness;
    $('completeness').textContent = coverage?.complete ? coverage.terminal_target > 0 ? `Data complete · ${coverage.valid_target}/${coverage.required} inputs · ${coverage.trading_target} trading · ${coverage.terminal_target} terminal` : `Data complete · ${coverage.valid_target}/${coverage.required} symbols` : 'Completeness —';
    $('provider').textContent = 'Provider · ' + (typeof status.provider_health === 'string' ? status.provider_health : status.provider_health?.status || 'Not checked');
    $('read-status').textContent = status.snapshot_read?.startsWith('busy') ? 'Storage is busy. Showing the last committed snapshot.' : '';
    $('refresh').disabled = status.state === 'running';
    $('refresh-label').textContent = status.state === 'running' ? 'Refreshing…' : 'Refresh Data';
    if (inspector) $('inspector-status').textContent = failed ? 'Refresh failed · previous successful snapshot retained' : status.state === 'running' ? progress : 'Completed session ' + (snapshot?.session || '—');
    const errorText={credentials_missing:'Set Alpaca credentials with configure-credentials.cmd.',
      authentication_denied:'Alpaca denied access. Check your SIP subscription and saved credentials.',
      rate_limited:'The provider rate limit was reached.',provider_unavailable:'The market-data provider was unavailable.',
      required_data_incomplete:'Required completed-session data is incomplete.',configuration_invalid:'Reviewed configuration could not be loaded.',
      storage_problem:'Local research storage is unavailable.',calculation_validation_failed:'Research calculation or validation failed.',
      interrupted_refresh:'The previous refresh was interrupted.'}[status.error];
    const message=failed?[errorText||'Refresh failed.',snapshot?'Previous successful snapshot retained.':'','Select Refresh Data to retry.'].filter(Boolean).join(' '):requestError;
    $('error').hidden = !message;
    if($('error').textContent!==message)$('error').textContent=message;
    const configNotice=$('configuration-notice');
    configNotice.hidden=!['configuration_changed','configuration_invalid'].includes(status.freshness);
    if(!configNotice.hidden){
      const reason=status.freshness==='configuration_changed'?'Refresh required after configuration change.':'Reviewed configuration is unavailable.';
      const detail=snapshot?' Displayed research uses the last committed configuration.':'';
      if(configNotice.textContent!==reason+detail)configNotice.textContent=reason+detail;
    }
    if (previous.state === 'running' && status.state === 'success') {
      announce('Refresh complete.');
      $('refresh').classList.remove('refresh-complete');
      void $('refresh').offsetWidth;
      $('refresh').classList.add('refresh-complete');
    }
  }
  let polling = false, pollTimer;
  async function poll() {
    if (polling) return;
    clearTimeout(pollTimer);
    polling=true;
    try {
      const response=await fetch('/api/status');
      if(!response.ok)throw Error('status');
      const status=await response.json();
      const version=JSON.stringify([status.snapshot_version,status.last_successful_refresh]);
      if(version!==loadedVersion){
        const data=await fetch('/api/dashboard-data');
        if(!data.ok)throw Error('snapshot');
        const committed=await data.json();
        render(committed);
        loadedVersion=data.headers.get('X-ThemeScope-Snapshot')||version;
      }
      showStatus(status);
      if(!savedReady)await loadSaved(status.mode).catch(()=>{});
    } catch {
      const message=snapshot?`Connection lost · showing completed session ${snapshot.session}`:'Connection lost · no snapshot loaded';
      if($('progress').textContent!==message)$('progress').textContent=message;
      if(!snapshot){render(null);$('error').hidden=false;$('error').textContent='Unable to load research. The app will reconnect automatically.';}
    } finally {
      polling=false;
      pollTimer=setTimeout(poll,currentStatus.state==='running'?650:5000);
    }
  }
  document.addEventListener('submit',event => { if (event.target.matches('form')) event.preventDefault(); });
  document.addEventListener('click',event => {
    const button=event.target.closest('button'),link=event.target.closest('a'),point=event.target.closest('[data-map-theme]');
    if(point){showMapReadout(point.dataset.mapTheme,true);return;}
    if(link?.dataset.export){announce('Preparing '+link.dataset.export+' export.');const menu=link.closest('.export-menu');if(menu)menu.open=false;}
    if (button?.dataset.inspectTheme) {
      openInspector('theme',button.dataset.inspectTheme,button.dataset.focusKey);return;
    }
    if (link?.dataset.inspectTicker && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey) {
      event.preventDefault();openInspector('ticker',link.dataset.inspectTicker,link.dataset.focusKey,link.dataset.contextTheme||'');return;
    }
    if (link?.getAttribute('href') === '#workspace') { event.preventDefault(); $('workspace').focus(); $('workspace').scrollIntoView(); return; }
    if (link?.getAttribute('aria-disabled') === 'true') { event.preventDefault(); return; }
    if (link?.getAttribute('href')?.startsWith('#themes/')) {
      if (!route.startsWith('#themes/')) { origin = route || '#themes'; themeOriginFocus=link.dataset.focusKey; }
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
    if (button.dataset.save) { changeSaved(button.dataset.save,false,button.dataset.saveTheme||''); return; }
    if (button.dataset.remove) { changeSaved(button.dataset.remove,true); return; }
    if (button.dataset.universe) { ui.universe=button.dataset.universe; if(ui.universe!=='active')$('theme-state-filter').value='';ui.themeSort=ui.universe==='active'?'score':'name';ui.themeDescending=ui.universe==='active'; renderThemes();requestAnimationFrame(UX.indicators);return;}
    if (button.dataset.candidateMode) { const changed=ui.candidateMode!==button.dataset.candidateMode;ui.candidateMode=button.dataset.candidateMode;renderCandidates();UX.indicators();if(changed)UX.move($('candidates'),'sweep');return; }
    if (button.dataset.reset === 'themes') { $('theme-filters').reset();ui.themeSort=ui.universe==='active'?'score':'name';ui.themeDescending=ui.universe==='active';renderThemes(); UX.move($('theme-table'),'reveal'); }
    if (button.dataset.reset === 'candidates') { $('candidate-filters').reset(); renderCandidates(); UX.move($('candidates'),'reveal'); }
  });
  function filterChange(event) {
    const id = event.target.id;
    if(id==='map-selection'){showMapReadout(event.target.value,true); return; }
    if (id === 'inspector-search') { inspectorView().search = event.target.value; renderInspectorMembers(); return; }
    if(id==='inspector-view'){inspectorView().filter=event.target.value;renderInspectorMembers();return;}
    if (id === 'inspector-sort') { inspectorView().sort = event.target.value; renderInspectorMembers(); return; }
    if (['theme-search','theme-family','theme-state-filter'].includes(id)) renderThemes();
    if (id === 'theme-sort') { const [key,direction] = event.target.value.split(':'); ui.themeSort = key; ui.themeDescending = direction === 'desc'; renderThemes(); $('theme-sort')?.focus(); }
    if (id.startsWith('candidate-') && id !== 'candidate-filters') renderCandidates();
    if(event.type==='change'&&id.startsWith('theme-'))UX.move($('theme-table'),'reveal');
    if(event.type==='change'&&id.startsWith('candidate-'))UX.move($('candidates'),'reveal');
    if (id.startsWith('member-') && ['member-search','member-role','member-eligibility','member-sort'].includes(id)) {
      const view = memberView(detailId());
      view.memberSearch = $('member-search').value; view.memberRole = $('member-role').value; view.memberEligibility = $('member-eligibility').value; view.memberSort = $('member-sort').value; renderMembers(detailId());
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
    requestError = '';
    $('refresh').disabled = true;
    try {
      const response = await fetch('/api/refresh',{method:'POST'});
      if (!response.ok && response.status !== 409) requestError = 'Unable to start refresh. Previous results remain available. Open Snapshot and refresh and select Refresh Data to retry.';
    } catch { requestError = 'Unable to reach the local server. Previous results remain available. Open Snapshot and refresh and select Refresh Data to retry.'; }
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
  poll();
})();
