/* kpi-icons.js — THE single home of every dashboard KPI icon.
   --------------------------------------------------------------------------
   Same architecture as action-icons.js / nav-icons.js: inline-SVG sprite
   injected once per page; every KPI card references a symbol with
   <svg class="kpi-icon"><use href="#k-..."/></svg>. Outline, minimalist,
   hand-drawn, arcs-free (lines, polylines, rects only) to match both icon
   families. Strokes use currentColor, so icons inherit their card's color
   with zero extra code. Geometry echoes nav-icons.js where concepts
   overlap (document, tray + arrows) so the dashboard speaks the same
   visual language as the sidebar.
   Set: k-alert (warning triangle) · k-pr (document) · k-iar (tray + down) ·
        k-withdraw (tray + up) · k-return (arrow into tray) ·
        k-asset (coin + peso bars) · k-products (2x2 grid).
   Loaded right after nav-icons.js on dashboard pages.
   -------------------------------------------------------------------------- */

(function () {
    if (document.getElementById('kpi-icon-sprite')) return;
    var NS = 'http://www.w3.org/2000/svg';
    var svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('id', 'kpi-icon-sprite');
    svg.setAttribute('aria-hidden', 'true');
    svg.setAttribute('focusable', 'false');
    svg.setAttribute('width', '0');
    svg.setAttribute('height', '0');
    svg.style.position = 'absolute';
    // [symbol id, [[element, {attrs}, [children]], ...], stroke-width override].
    var defs = [
        ['k-alert', [
            ['path', { d: 'M12 3L22 20H2z' }],
            ['path', { d: 'M12 9v5' }],
            ['path', { d: 'M12 17v.5' }]
        ]],
        ['k-pr', [
            ['path', { d: 'M14 2H6v20h12V8z' }],
            ['path', { d: 'M14 2v6h6' }],
            ['path', { d: 'M9 13h6M9 17h6' }]
        ]],
        ['k-iar', [
            ['path', { d: 'M4 13v8h16v-8' }],
            ['path', { d: 'M12 4v8M8 8l4 4 4-4' }]
        ]],
        ['k-withdraw', [
            ['path', { d: 'M4 15v5h16v-5' }],
            ['path', { d: 'M12 16V6M8 10l4-4 4 4' }]
        ]],
        ['k-return', [
            ['path', { d: 'M5 11h9v9H5z' }],
            ['path', { d: 'M11 5l-6 6 6 6' }]
        ]],
        ['k-asset', [
            ['circle', { cx: '12', cy: '12', r: '8.5' }],
            ['path', { d: 'M12 7v10M9.5 9.5h4.5M9.5 12h5' }]
        ]],
        ['k-products', [
            ['rect', { x: '4', y: '4', width: '7', height: '7' }],
            ['rect', { x: '13', y: '4', width: '7', height: '7' }],
            ['rect', { x: '4', y: '13', width: '7', height: '7' }],
            ['rect', { x: '13', y: '13', width: '7', height: '7' }]
        ]]
    ];
    defs.forEach(function (d) {
        var sym = document.createElementNS(NS, 'symbol');
        sym.setAttribute('id', d[0]);
        sym.setAttribute('viewBox', '0 0 24 24');
        sym.setAttribute('fill', 'none');
        sym.setAttribute('stroke', 'currentColor');
        sym.setAttribute('stroke-width', d[2] || '2');
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
