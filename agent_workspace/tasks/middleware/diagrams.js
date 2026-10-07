/* Nút "Phóng to" và "Mã nguồn" cho mỗi figure.dg. Sơ đồ SVG đọc được không cần file này. */
(function () {
  'use strict';
  var figures = document.querySelectorAll('figure.dg');
  if (!figures.length || typeof HTMLDialogElement !== 'function') return;

  var dialog, titleEl, bodyEl, copyBtn, opener = null, seq = 0, sourceText = '';
  var REF_ATTRS = ['href', 'xlink:href', 'fill', 'stroke', 'marker-start', 'marker-mid', 'marker-end',
    'clip-path', 'mask', 'filter', 'aria-labelledby', 'aria-describedby'];

  function buildDialog() {
    dialog = document.createElement('dialog');
    dialog.className = 'dg-dialog';
    dialog.setAttribute('aria-labelledby', 'dg-dialog-title');
    var bar = document.createElement('div');
    bar.className = 'dg-dialog-bar';
    titleEl = document.createElement('h2');
    titleEl.id = 'dg-dialog-title';
    var actions = document.createElement('div');
    copyBtn = document.createElement('button');
    copyBtn.type = 'button';
    copyBtn.textContent = 'Chép mã';
    copyBtn.addEventListener('click', copySource);
    var close = document.createElement('button');
    close.type = 'button';
    close.textContent = 'Đóng';
    close.className = 'dg-close';
    close.addEventListener('click', function () { dialog.close(); });
    actions.append(copyBtn, close);
    bar.append(titleEl, actions);
    bodyEl = document.createElement('div');
    bodyEl.className = 'dg-dialog-body';
    bodyEl.tabIndex = 0;
    bodyEl.setAttribute('role', 'region');
    bodyEl.setAttribute('aria-label', 'Nội dung hộp thoại, cuộn để xem hết');
    dialog.append(bar, bodyEl);
    document.body.append(dialog);
    // Escape do showModal xử lý (sự kiện cancel → close); mọi cách đóng đều trả focus.
    dialog.addEventListener('close', function () {
      bodyEl.replaceChildren();
      sourceText = '';
      if (opener && document.contains(opener)) opener.focus();
      opener = null;
    });
  }

  // Bản sao trong dialog đổi mọi id và tham chiếu để không trùng id với SVG gốc.
  function namespaceIds(svg, prefix) {
    var map = {};
    var nodes = [svg].concat(Array.prototype.slice.call(svg.querySelectorAll('*')));
    nodes.forEach(function (el) {
      if (el.id) { map[el.id] = prefix + el.id; el.id = prefix + el.id; }
    });
    nodes.forEach(function (el) {
      REF_ATTRS.forEach(function (name) {
        var v = el.getAttribute(name);
        if (!v) return;
        var nv = v.replace(/url\(#([^)]+)\)/g, function (m, id) { return map[id] ? 'url(#' + map[id] + ')' : m; });
        if (/href$/.test(name) && v.charAt(0) === '#' && map[v.slice(1)]) nv = '#' + map[v.slice(1)];
        if (/^aria-/.test(name)) nv = v.split(/\s+/).map(function (id) { return map[id] || id; }).join(' ');
        if (nv !== v) el.setAttribute(name, nv);
      });
    });
  }

  function open(btn, title, content, isSource) {
    opener = btn;
    titleEl.textContent = title;
    copyBtn.hidden = !isSource;
    bodyEl.replaceChildren(content);
    dialog.showModal();
    dialog.querySelector('.dg-close').focus();
  }

  function copySource() {
    if (!sourceText) return;
    var done = function () { copyBtn.textContent = 'Đã chép'; setTimeout(function () { copyBtn.textContent = 'Chép mã'; }, 1500); };
    var pre = bodyEl.querySelector('pre');
    var selectAll = function () {
      var range = document.createRange();
      range.selectNodeContents(pre);
      var sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(sourceText).then(done, selectAll);
    } else {
      selectAll();
    }
  }

  buildDialog();
  Array.prototype.forEach.call(figures, function (figure) {
    var svg = figure.querySelector('.dg-canvas svg');
    var head = figure.querySelector('h3');
    if (!svg || !head) return;
    var name = head.textContent.trim();
    var tools = document.createElement('div');
    tools.className = 'dg-tools';
    var zoom = document.createElement('button');
    zoom.type = 'button';
    zoom.textContent = 'Phóng to';
    zoom.setAttribute('aria-haspopup', 'dialog');
    zoom.setAttribute('aria-label', 'Phóng to sơ đồ: ' + name);
    zoom.addEventListener('click', function () {
      var copy = svg.cloneNode(true);
      namespaceIds(copy, 'zoom' + (++seq) + '-');
      var vb = svg.viewBox && svg.viewBox.baseVal;
      if (vb && vb.width) {
        copy.setAttribute('width', String(Math.round(vb.width * 1.15)));
        copy.setAttribute('height', String(Math.round(vb.height * 1.15)));
      }
      open(zoom, name, copy, false);
    });
    var src = document.createElement('button');
    src.type = 'button';
    src.textContent = 'Mã nguồn';
    src.setAttribute('aria-haspopup', 'dialog');
    src.setAttribute('aria-label', 'Mã nguồn SVG của sơ đồ: ' + name);
    src.addEventListener('click', function () {
      var pre = document.createElement('pre');
      sourceText = svg.outerHTML;
      pre.textContent = sourceText;
      open(src, 'Mã nguồn SVG — ' + name, pre, true);
    });
    tools.append(zoom, src);
    figure.querySelector('.dg-canvas').after(tools);
  });
})();
