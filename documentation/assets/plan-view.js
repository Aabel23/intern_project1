(() => {
  'use strict';

  const root = document.getElementById('plan-root');
  const escape = value => String(value ?? '').replace(/[&<>"']/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  })[char]);
  const card = row => `<article><b>${escape(row.label)}</b><p>${row.body}</p></article>`;

  function renderSection(section) {
    let body = `<h2>${escape(section.title)}</h2>`;
    if (section.intro) body += `<p>${section.intro}</p>`;
    if (section.facts) {
      body += `<div class="facts">${section.facts.map(row => `<article class="fact"><span class="flag ${escape(row.flagClass)}">${escape(row.flag)}</span><h3>${escape(row.title)}</h3><p>${row.body}</p></article>`).join('')}</div>`;
    }
    if (section.route) {
      body += `<div class="route" aria-label="Năm cổng triển khai">${section.route.map(row => `<a href="${escape(row.href)}"><b>${escape(row.code)}</b><strong>${escape(row.title)}</strong><small>${escape(row.detail)}</small></a>`).join('')}</div>`;
      body += '<div class="legend"><span><i class="sw proc"></i> Việc xây/triển khai</span><span><i class="sw human"></i> Quyết định của bạn</span><span><i class="sw ok"></i> Bằng chứng qua cổng</span></div>';
    }
    if (section.table) {
      body += `<div class="table-wrap" style="margin-top:15px"><table><thead><tr>${section.table.headers.map(value => `<th>${escape(value)}</th>`).join('')}</tr></thead><tbody>${section.table.rows.map(row => `<tr>${row.map(value => `<td>${escape(value)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
    }
    if (section.callout) body += `<div class="callout">${section.callout}</div>`;
    if (section.phases) {
      body += section.phases.map(phase => `<article class="phase" id="${escape(phase.anchor)}">
        <div class="phase-head"><div><h3>${escape(phase.title)}</h3><p>${phase.intro}</p></div><span class="mark">${escape(phase.mark)}</span></div>
        <ol class="steps">${phase.steps.map(step => `<li><code>${escape(step.id)}</code><div><strong>${escape(step.title)}</strong><p>${step.body}</p></div><div class="proof"><b>Bằng chứng</b>${escape(step.proof)}</div></li>`).join('')}</ol>
        <div class="gate"><b>${escape(phase.gate.label)}</b><span>${phase.gate.body}</span></div>
      </article>`).join('');
    }
    if (section.workstreams) {
      body += `<div class="workstreams">${section.workstreams.map(row => `<article><h3>${escape(row.title)}</h3><ul>${row.items.map(item => `<li>${item}</li>`).join('')}</ul></article>`).join('')}</div>`;
    }
    if (section.decisions) body += `<div class="decision-grid">${section.decisions.map(card).join('')}</div>`;
    if (section.sources) body += `<ol class="source-list">${section.sources.map(source => `<li>${source}</li>`).join('')}</ol>`;
    return `<section class="sec" id="${escape(section.id)}">${body}</section>`;
  }

  function render(data) {
    if (data.version !== 1 || !Array.isArray(data.sections)) throw new Error('plan.json sai cấu trúc');
    document.title = data.header.title;
    root.innerHTML = `<p style="padding:10px 18px;text-align:center;background:#e9f3ef;color:#174b3d;font:700 13px sans-serif">${escape(data.banner)}</p>
      <div class="page"><header class="masthead"><div><div class="eyebrow">${escape(data.header.eyebrow)}</div><h1>${escape(data.header.title)}</h1><p class="lead">${data.header.lead}</p></div>
      <div class="meta">${data.header.meta.map(row => `<span><b>${escape(row.label)}</b> ${escape(row.value)}</span>`).join('')}</div></header>
      <div class="topline">${data.summary.map(card).join('')}</div>
      <section class="progress-panel" id="tien-do" aria-labelledby="progress-title"><div class="progress-top"><div><h2 id="progress-title">${escape(data.progress.title)}</h2><p>${data.progress.intro}</p></div><div class="progress-count" id="progress-count">—<small>bước đạt</small></div></div>
      <div class="progress-track" role="progressbar" aria-label="Tỷ lệ bước đã đạt" aria-valuemin="0" aria-valuemax="0" aria-valuenow="0" id="progress-track"><span class="progress-fill" id="progress-fill"></span></div><div class="progress-stats" id="progress-stats" aria-live="polite"></div><p class="progress-guide" id="progress-guide">${data.progress.guide}</p></section>
      <main>${data.sections.map(renderSection).join('')}</main></div>`;
    const progress = document.createElement('script');
    progress.src = '../assets/roadmap-progress.js';
    document.body.append(progress);
  }

  fetch('plan.json', { cache: 'no-store' })
    .then(response => { if (!response.ok) throw new Error(`HTTP ${response.status}`); return response.json(); })
    .then(render)
    .catch(error => { root.textContent = `Không đọc được plan.json (${error.message}). Mở trang qua server documentation.`; });
})();
