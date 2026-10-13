// Quy ước chung cho sơ đồ trình tự: nút số rõ hơn, xử lý nội bộ không vẽ vòng tự gọi.
(function(){
  function adjust(svg){
    const marker = svg.querySelector('marker#sequencenumber circle');
    if (marker) marker.setAttribute('r', '8.4'); // Mermaid mặc định 6: x1.4.
    svg.querySelectorAll('text.sequenceNumber').forEach(el => el.setAttribute('font-size', '16.8px'));
    svg.querySelectorAll('path[marker-start]').forEach(path => {
      const match = /^M\s*([\d.]+),([\d.]+)\s+C\s*[\d.]+,[\d.]+\s+[\d.]+,[\d.]+\s+([\d.]+),([\d.]+)/
        .exec(path.getAttribute('d') || '');
      if (!match || Math.abs(Number(match[1]) - Number(match[3])) > 2) return;
      const x = Number(match[1]);
      const y = Number(match[2]);
      path.setAttribute('d', `M ${x},${y} L ${x},${y + 0.1}`);
      path.removeAttribute('marker-end');
    });
  }

  function scan(root){
    if (root.nodeType !== 1) return;
    if (root.matches?.('.dg-canvas svg')) adjust(root);
    root.querySelectorAll?.('.dg-canvas svg').forEach(adjust);
  }

  const start = () => {
    scan(document.body);
    new MutationObserver(records => records.forEach(record => record.addedNodes.forEach(scan)))
      .observe(document.body, {childList:true, subtree:true});
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, {once:true});
  else start();
})();
