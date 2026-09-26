/* action-icons.js — THE single home of every action icon in the system.
   --------------------------------------------------------------------------
   Inline-SVG sprite injected once per page; every button references a symbol
   with <svg class="act-icon"><use href="#i-..."/></svg>. Inline SVG was
   chosen over CSS masks so icons render identically on every browser
   version — no mask engine involved at all. Strokes use currentColor, so
   each icon still inherits its button's color (green/red/slate/white).
   Geometry is arcs-free by design (lines, polylines, one circle element).
    Set: i-check (approve, thumbs-up) · i-disapprove (thumbs-down) ·
         i-x (delete/remove) · i-view (inspect) · i-edit · i-plus ·
         i-refresh · i-print (printer, A4 reports) · i-filter (funnel) · i-bell ·
         i-upload (import, tray with up-arrow).
   Loaded right after ui_helpers.js on every page that shows action buttons.
   -------------------------------------------------------------------------- */

(function () {
    if (document.getElementById('act-icon-sprite')) return;
    var NS = 'http://www.w3.org/2000/svg';
    var svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('id', 'act-icon-sprite');
    svg.setAttribute('aria-hidden', 'true');
    svg.setAttribute('focusable', 'false');
    svg.setAttribute('width', '0');
    svg.setAttribute('height', '0');
    svg.style.position = 'absolute';
    // [symbol id, [[element, {attrs}, [children]], ...], stroke-width override].
    // i-check reuses the feather thumbs-down geometry mirrored vertically, so
    // both thumbs share a pixel-identical footprint and stroke (same visual
    // size and weight at 16px by construction, not by eyeballing).
    var defs = [
        ['i-check', [
            ['g', { transform: 'translate(0,24) scale(1,-1)' }, [
                ['path', { d: 'M10 15v4a3 3 0 0 0 3 3l4-9V2H6.28a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17' }]
            ]]
        ]],
        ['i-disapprove', [['path', { d: 'M10 15v4a3 3 0 0 0 3 3l4-9V2H6.28a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17' }]]],
        ['i-x', [['path', { d: 'M6 6l12 12M18 6L6 18' }]]],
        ['i-view', [['circle', { cx: '11', cy: '11', r: '6.5' }], ['path', { d: 'M16 16l4.5 4.5' }]]],
        ['i-edit', [['path', { d: 'M4 20l1-4L16.5 4.5a2.1 2.1 0 0 1 3 3L8 19l-4 1z' }]]],
        ['i-plus', [['path', { d: 'M12 5v14M5 12h14' }]]],
        ['i-refresh', [['path', { d: 'M23 4v6h-6' }], ['path', { d: 'M1 20v-6h6' }], ['path', { d: 'M3.51 9a9 9 0 0 1 14.85-3.36L23 10' }], ['path', { d: 'M1 14l4.64 4.36A9 9 0 0 0 20.49 15' }]]],
        ['i-print', [['path', { d: 'M6 9V3h12v6' }], ['path', { d: 'M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2' }], ['rect', { x: '6', y: '14', width: '12', height: '7' }]]],
        ['i-filter', [['path', { d: 'M22 3H2l8 9.5V19l4 2v-8.5z' }]]],
        ['i-upload', [['path', { d: 'M12 15V3' }], ['path', { d: 'M7 8l5-5 5 5' }], ['path', { d: 'M4 13v7h16v-7' }]]],
        ['i-bell', [['path', { d: 'M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9' }], ['path', { d: 'M13.73 21a2 2 0 0 1-3.46 0' }]]]
    ];
    defs.forEach(function (d) {
        var sym = document.createElementNS(NS, 'symbol');
        sym.setAttribute('id', d[0]);
        sym.setAttribute('viewBox', '0 0 24 24');
        sym.setAttribute('fill', 'none');
        sym.setAttribute('stroke', 'currentColor');
        sym.setAttribute('stroke-width', d[2] || '2.2');
        sym.setAttribute('stroke-linecap', 'round');
        sym.setAttribute('stroke-linejoin', 'round');
        d[1].forEach(function (c) {
            var el = document.createElementNS(NS, c[0]);
            Object.keys(c[1]).forEach(function (k) { el.setAttribute(k, c[1][k]); });
            (c[2] || []).forEach(function (g) {
                var ch = document.createElementNS(NS, g[0]);
                Object.keys(g[1]).forEach(function (k) { ch.setAttribute(k, g[1][k]); });
                el.appendChild(ch);
            });
            sym.appendChild(el);
        });
        svg.appendChild(sym);
    });
    document.body.insertBefore(svg, document.body.firstChild);
})();
