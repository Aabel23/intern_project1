(function(){
  const blocks = Array.from(document.querySelectorAll('script[type="text/x-mermaid"]'));
  let seq = 0;
  const tok = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();

  function classDefs(){
    const ink = tok('--ink');
    const d = (n, fill, stroke, extra) => `  classDef ${n} fill:${fill},stroke:${stroke},color:${ink},stroke-width:1.4px${extra||''}`;
    return [
      d('ui',    tok('--ui-soft'),    tok('--ui')),
      d('proc',  tok('--proc-soft'),  tok('--proc')),
      d('hw',    tok('--hw-soft'),    tok('--hw')),
      d('store', tok('--store-soft'), tok('--store')),
      d('file',  tok('--store-soft'), tok('--store'), ',stroke-dasharray:5 3'),
      d('dec',   tok('--amber-soft'), tok('--amber')),
      d('human', tok('--amber-soft'), tok('--amber')),
      d('ok',    tok('--ok-soft'),    tok('--ok')),
      d('bad',   tok('--red-soft'),   tok('--red')),
      d('muted', tok('--surface-2'), tok('--ink-3'), ',stroke-dasharray:4 3'),
      `  classDef hot fill:${tok('--proc-soft')},stroke:${tok('--red')},color:${ink},stroke-width:3px`
    ].join('\n');
  }

  function config(){
    const sans = getComputedStyle(document.documentElement).getPropertyValue('--sans');
    const v = {
      fontFamily: sans, fontSize:'13px',
      background: tok('--surface'),
      primaryColor: tok('--proc-soft'), primaryTextColor: tok('--ink'), primaryBorderColor: tok('--proc'),
      secondaryColor: tok('--surface-2'), tertiaryColor: tok('--surface-2'),
      lineColor: tok('--ink-3'), textColor: tok('--ink'),
      mainBkg: tok('--proc-soft'), nodeBorder: tok('--proc'),
      clusterBkg: tok('--card'), clusterBorder: tok('--line-2'), titleColor: tok('--ink-2'),
      edgeLabelBackground: tok('--surface'),
      actorBkg: tok('--card'), actorBorder: tok('--line-2'), actorTextColor: tok('--ink'), actorLineColor: tok('--line-2'),
      signalColor: tok('--accent'), signalTextColor: tok('--ink'),
      labelBoxBkgColor: tok('--surface-2'), labelBoxBorderColor: tok('--line-2'), labelTextColor: tok('--ink'),
      noteBkgColor: tok('--amber-soft'), noteBorderColor: tok('--amber'), noteTextColor: tok('--ink'),
      sequenceNumberColor: '#FFFFFF',
      stateLabelColor: tok('--ink'), transitionColor: tok('--ink-3'), transitionLabelColor: tok('--ink-2'),
      stateBkg: tok('--proc-soft'), altBackground: tok('--surface-2'), compositeBackground: tok('--surface-2'),
      specialStateColor: tok('--ink-2')
    };
    return {
      startOnLoad:false, theme:'base', themeVariables:v, securityLevel:'loose',
      flowchart:{ htmlLabels:true, curve:'basis', nodeSpacing:28, rankSpacing:40, padding:8, useMaxWidth:false },
      sequence:{ useMaxWidth:false, mirrorActors:false, wrap:false, width:118, actorMargin:22, boxMargin:6, messageMargin:26, messageFontSize:13, noteFontSize:13, actorFontSize:13, showSequenceNumbers:true },
      state:{ useMaxWidth:false }
    };
  }

  function sourceOf(block){
    let src = block.textContent.replace(/^\n+/, '').replace(/\s+$/, '');
    if (block.dataset.kind === 'flow' || /\n\s*class /.test(src)) src += '\n' + classDefs();
    return src;
  }

  function showSource(canvas, text){
    canvas.innerHTML = '';
    const pre = document.createElement('pre'); pre.className = 'fallback'; pre.textContent = text;
    canvas.appendChild(pre);
  }


  // Thu nhỏ vừa khung nếu chỉ rộng hơn khung một chút; quá rộng thì giữ cỡ thật và cho cuộn ngang.
  function fit(canvas){
    const svg = canvas.querySelector('svg'); if (!svg) return;
    const vb = svg.viewBox && svg.viewBox.baseVal;
    const natural = vb && vb.width ? vb.width : svg.getBoundingClientRect().width;
    const room = canvas.clientWidth;
    svg.style.maxWidth = 'none';
    if (natural > room && room / natural >= 0.6){ svg.style.width = room + 'px'; }
    else { svg.style.width = natural + 'px'; }
  }

  function addTools(block, canvas){
    if (canvas.nextElementSibling && canvas.nextElementSibling.classList.contains('dg-tools')) return;
    const bar = document.createElement('div'); bar.className = 'dg-tools';
    const zoom = document.createElement('button'); zoom.type = 'button'; zoom.textContent = 'Phóng to';
    zoom.addEventListener('click', () => openZoom(canvas.querySelector('svg')));
    const btn = document.createElement('button'); btn.type = 'button'; btn.textContent = 'Mã nguồn';
    btn.addEventListener('click', function(){
      const text = block.textContent.replace(/^\n+/, '').replace(/\s+$/, '');
      const done = () => { btn.textContent = 'Đã chép'; setTimeout(()=>{btn.textContent='Mã nguồn'}, 1600); };
      try{ navigator.clipboard.writeText(text).then(done, () => showSource(canvas, text)); }
      catch(e){ showSource(canvas, text); }
    });
    bar.append(zoom, btn);
    canvas.after(bar);
  }

  async function renderAll(){
    if (!window.mermaid){ blocks.forEach(b => showSource(b.nextElementSibling, b.textContent.trim())); return; }
    mermaid.initialize(config());
    for (const block of blocks){
      const canvas = block.nextElementSibling;
      try{
        const { svg } = await mermaid.render('mmd' + (++seq), sourceOf(block));
        canvas.innerHTML = svg;
        fit(canvas);
      }catch(err){ console.error(err); showSource(canvas, block.textContent.trim()); }
      addTools(block, canvas);
    }
  }

  // ---------- phóng to ----------
  const zoomEl = document.getElementById('zoom'), zoomBody = document.getElementById('zoom-body');
  let lastFocus = null;
  function openZoom(svg){
    if (!svg) return;
    lastFocus = document.activeElement;
    const copy = svg.cloneNode(true);
    const vb = svg.viewBox && svg.viewBox.baseVal;
    copy.removeAttribute('style');
    if (vb && vb.width){ copy.setAttribute('width', Math.round(vb.width * (svg.classList.contains('ov') ? 1.25 : 1))); copy.removeAttribute('height'); }
    zoomBody.innerHTML = ''; zoomBody.appendChild(copy);
    zoomEl.hidden = false; document.getElementById('zoom-close').focus();
  }
  function closeZoom(){ zoomEl.hidden = true; zoomBody.innerHTML = ''; if (lastFocus) lastFocus.focus(); }
  document.getElementById('zoom-close').addEventListener('click', closeZoom);
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && !zoomEl.hidden) closeZoom(); });
  document.querySelectorAll('[data-zoom]').forEach(b => b.addEventListener('click', () => openZoom(document.querySelector('svg.ov'))));

  const start = () => (document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve()).then(renderAll);
  start();

  let last = document.documentElement.getAttribute('data-theme');
  new MutationObserver(() => {
    const now = document.documentElement.getAttribute('data-theme');
    if (now !== last){ last = now; renderAll(); }
  }).observe(document.documentElement, {attributes:true, attributeFilter:['data-theme']});
  if (window.matchMedia){
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    if (mq.addEventListener) mq.addEventListener('change', renderAll);
  }
  let rt; window.addEventListener('resize', () => { clearTimeout(rt); rt = setTimeout(() => document.querySelectorAll('.dg-canvas').forEach(fit), 150); });

  // ---------- mục lục ----------
  const links = Array.from(document.querySelectorAll('.toc a'));
  const map = new Map(links.map(a => [a.getAttribute('href').slice(1), a]));
  if ('IntersectionObserver' in window){
    const io = new IntersectionObserver(entries => {
      entries.forEach(e => {
        if (e.isIntersecting){
          links.forEach(l => l.classList.remove('on'));
          const a = map.get(e.target.id); if (a) a.classList.add('on');
        }
      });
    }, {rootMargin:'-20% 0px -70% 0px'});
    map.forEach((a, id) => { const el = document.getElementById(id); if (el) io.observe(el); });
  }
})();
