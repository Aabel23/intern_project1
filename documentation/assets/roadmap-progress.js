(() => {
  'use strict';

  const labels = {
    todo: '○ Chưa xác nhận',
    doing: '◔ Đang làm',
    review: '◇ Chờ kiểm',
    done: '✓ Đạt',
    blocked: '! Bị chặn',
  };
  const gates = {
    G0: ['p0'],
    G1: ['p1', 'p2'],
    G2: ['p3', 'p4'],
    G3: ['p5', 'p6'],
    G4: ['p7'],
  };
  const items = [...document.querySelectorAll('.phase .steps li')].map(li => ({
    li,
    id: li.querySelector('code')?.textContent.trim(),
    phase: li.closest('.phase').id,
  }));
  const total = items.length;
  const bar = document.getElementById('progress-track');
  bar.setAttribute('aria-valuemax', String(total));

  function statusFor(record) {
    return Object.hasOwn(labels, record?.status) ? record.status : 'todo';
  }

  function renderRecord(item, record) {
    const { li } = item;
    const status = statusFor(record);
    const body = li.children[1];
    let badge = body.querySelector('.step-status');
    let detail = body.querySelector('.step-record');
    if (!badge) {
      badge = document.createElement('span');
      badge.className = 'step-status';
      body.querySelector('strong').after(badge);
    }
    if (!detail) {
      detail = document.createElement('span');
      detail.className = 'step-record';
      badge.after(detail);
    }
    badge.className = `step-status ${status}`;
    badge.textContent = labels[status];
    const parts = [];
    if (record?.owner) parts.push(`Phụ trách: ${record.owner}`);
    if (record?.updated) parts.push(record.updated);
    if (record?.reviewer && status === 'done') parts.push(`Kiểm: ${record.reviewer}`);
    if (record?.evidence) parts.push(`Bằng chứng đã ghi: ${record.evidence}`);
    if (record?.note) parts.push(`Ghi chú: ${record.note}`);
    detail.textContent = parts.join(' · ');
    detail.hidden = parts.length === 0;
    li.classList.toggle('is-done', status === 'done');
    li.classList.toggle('is-blocked', status === 'blocked');
    return status;
  }

  function render(data) {
    if (data?.version !== 1 || !data.steps || !data.gates) throw new Error('Sổ tiến độ sai cấu trúc.');
    const statuses = {};
    for (const item of items) statuses[item.id] = renderRecord(item, data.steps[item.id]);
    const count = status => Object.values(statuses).filter(value => value === status).length;
    const done = count('done');
    const percent = Math.round(done / total * 100);
    document.getElementById('progress-count').innerHTML = `${done}/${total}<small>bước đạt</small>`;
    document.getElementById('progress-fill').style.width = `${percent}%`;
    bar.setAttribute('aria-valuenow', String(done));
    document.getElementById('progress-stats').replaceChildren(...[
      `${count('doing')} đang làm`,
      `${count('review')} chờ kiểm`,
      `${count('blocked')} bị chặn`,
      `${count('todo')} chưa xác nhận`,
    ].map(value => {
      const node = document.createElement('span');
      node.className = 'progress-stat';
      node.textContent = value;
      return node;
    }));

    for (const phase of document.querySelectorAll('.phase')) {
      const phaseItems = items.filter(item => item.phase === phase.id);
      const phaseDone = phaseItems.filter(item => statuses[item.id] === 'done').length;
      let widget = phase.querySelector('.phase-progress');
      if (!widget) {
        widget = document.createElement('div');
        widget.className = 'phase-progress';
        widget.innerHTML = '<div class="phase-ring"><span class="phase-ring-value"></span></div><div class="phase-progress-copy">Bước đạt<span class="phase-count"></span></div>';
        phase.querySelector('.phase-head .mark').replaceWith(widget);
      }
      const phasePercent = Math.round(phaseDone / phaseItems.length * 100);
      widget.querySelector('.phase-count').textContent = `${phaseDone}/${phaseItems.length}`;
      widget.querySelector('.phase-ring-value').textContent = `${phasePercent}%`;
      widget.querySelector('.phase-ring').style.setProperty('--phase-percent', `${phasePercent}%`);
    }

    let currentGateSelected = false;
    for (const [gate, phases] of Object.entries(gates)) {
      const route = document.querySelector(`.route a[href="#${phases[0]}"]`);
      if (!route) continue;
      let badge = route.querySelector('.gate-state');
      if (!badge) {
        badge = document.createElement('span');
        badge.className = 'gate-state';
        route.append(badge);
      }
      const gateItems = items.filter(item => phases.includes(item.phase));
      const ready = gateItems.every(item => statuses[item.id] === 'done');
      const approval = data.gates[gate];
      const passed = ready && approval?.approved === true && approval?.evidence;
      badge.className = `gate-state ${passed ? 'passed' : ready ? 'ready' : ''}`;
      badge.textContent = passed ? '✓ Đã qua cổng' : ready ? '◇ Chờ bạn duyệt cổng' : `${gateItems.filter(item => statuses[item.id] === 'done').length}/${gateItems.length} bước đạt`;
      route.classList.toggle('gate-passed', Boolean(passed));
      route.classList.toggle('now', !passed && !currentGateSelected);
      if (!passed) currentGateSelected = true;
    }
    document.getElementById('progress-guide').classList.remove('progress-alert');
  }

  async function refresh() {
    try {
      const response = await fetch('roadmap-progress.json', { cache: 'no-store' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      render(await response.json());
    } catch (error) {
      const guide = document.getElementById('progress-guide');
      guide.classList.add('progress-alert');
      guide.textContent = `Chưa đọc được sổ tiến độ (${error.message}). Mở tài liệu qua server documentation; không suy ra bước nào đã đạt.`;
    }
  }

  refresh();
  setInterval(refresh, 15000);
})();
