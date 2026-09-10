// One navigation for every viewer page, so the set can grow without eight
// copies drifting apart. Each page carries <nav id="viewnav"></nav>; this fills
// it in and marks the current page. Plain script, no build step, works over
// file:// like the rest of the viewer.
(function () {
  var PAGES = [
    { href: 'index.html',          group: 'Image-based rendering', name: 'Interpolation',      note: '13.88 dB' },
    { href: 'sala_skymask.html',   group: 'Gaussian splatting',    name: 'Sala · sky masked',  note: 'pavilion 22.61 dB' },
    { href: 'sala.html',           group: 'Gaussian splatting',    name: 'Sala · sky trained', note: 'pavilion 22.34 dB' },
    { href: 'sala_v5.html',        group: 'Gaussian splatting',    name: 'Sala · sky blacked', note: 'whole frame 20.10 dB' },
    { href: 'lamp.html',           group: 'Gaussian splatting',    name: 'Lamp · sky trained', note: 'whole frame 20.87 dB' },
    { href: 'lamp_v5.html',        group: 'Gaussian splatting',    name: 'Lamp · sky blacked', note: 'whole frame 15.93 dB' },
    { href: 'splat.html',          group: 'Gaussian splatting',    name: 'August',             note: '22.09 dB' },
    { href: 'reconstruction.html', group: 'Photogrammetry',        name: 'Mesh',               note: 'Object Capture' }
  ];

  var CSS = [
    '#viewnav{display:grid;grid-template-columns:repeat(auto-fit,minmax(134px,1fr));',
    'gap:7px;margin:16px 0 0;max-width:1060px;font:13px/1.4 inherit}',
    '#viewnav .vn-label{grid-column:1/-1;margin:0 0 1px;font-size:10.5px;font-weight:700;',
    'letter-spacing:.13em;text-transform:uppercase;opacity:.62}',
    '#viewnav a,#viewnav span.vn-here{display:flex;flex-direction:column;gap:2px;padding:9px 11px;',
    'text-decoration:none;border:1px solid rgba(216,180,90,.19);border-radius:10px;',
    'background:rgba(255,255,255,.022);transition:border-color .18s,background-color .18s,transform .18s}',
    '#viewnav a:hover{border-color:rgba(216,180,90,.5);background:rgba(216,180,90,.08);transform:translateY(-1px)}',
    '#viewnav b{font-size:12.5px;font-weight:640;color:#f3eadc;letter-spacing:.004em}',
    '#viewnav a b{color:#e8dcc6}',
    '#viewnav em{font-style:normal;font-size:11px;opacity:.66;font-variant-numeric:tabular-nums}',
    '#viewnav span.vn-here{border-color:rgba(216,180,90,.5);background:rgba(216,180,90,.13);cursor:default}',
    '#viewnav span.vn-here b{color:#f0d68e}',
    '#viewnav a:focus-visible{outline:2px solid #f0d68e;outline-offset:3px}',
    '@media(max-width:680px){#viewnav{grid-template-columns:repeat(auto-fit,minmax(132px,1fr))}}'
  ].join('');

  function render() {
    var host = document.getElementById('viewnav');
    if (!host) return;
    var st = document.createElement('style');
    st.textContent = CSS;
    document.head.appendChild(st);

    var here = (location.pathname.split('/').pop() || 'index.html').toLowerCase();
    var html = '<p class="vn-label">Views of this project</p>';
    for (var i = 0; i < PAGES.length; i++) {
      var p = PAGES[i];
      var label = '<b>' + p.name + '</b><em>' + p.note + '</em>';
      html += (p.href.toLowerCase() === here)
        ? '<span class="vn-here" aria-current="page">' + label + '</span>'
        : '<a href="' + p.href + '">' + label + '</a>';
    }
    host.innerHTML = html;
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', render);
  else render();
})();
