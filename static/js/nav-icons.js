/* nav-icons.js — THE single home of every sidebar navigation icon.
   --------------------------------------------------------------------------
   Same architecture as action-icons.js: inline-SVG sprite injected once per
   page; every nav button references a symbol with
   <svg class="nav-icon"><use href="#n-..."/></svg>. Outline, minimalist,
   hand-drawn, arcs-free (lines, polylines, rects, circles only) to match the
   action-icon family. Strokes use currentColor, so icons inherit the nav
   button's color on rest, hover, and active states with zero extra code.
   Set: n-dashboard (monitor) · n-pr (document) · n-iar (tray + down arrow) ·
        n-inventory (2x2 grid) · n-withdraw (tray + up arrow) ·
        n-return (arrow into tray) · n-product (tag) · n-users (two heads) ·
        n-settings (sliders) · n-reports (bars) · n-logout (exit arrow).
   Loaded right after action-icons.js on every page with a sidebar.
   -------------------------------------------------------------------------- */

(function () {
    if (document.getElementById('nav-icon-sprite')) return;
    var NS = 'http://www.w3.org/2000/svg';
    var svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('id', 'nav-icon-sprite');
    svg.setAttribute('aria-hidden', 'true');
    svg.setAttribute('focusable', 'false');
    svg.setAttribute('width', '0');
    svg.setAttribute('height', '0');
    svg.style.position = 'absolute';
    // [symbol id, [[element, {attrs}, [children]], ...], stroke-width override].
    var defs = [
        ['n-dashboard', [
            ['rect', { x: '3', y: '4', width: '18', height: '12' }],
            ['path', { d: 'M9 20h6M12 16v4' }]
        ]],
        ['n-pr', [
            ['path', { d: 'M14 2H6v20h12V8z' }],
            ['path', { d: 'M14 2v6h6' }],
            ['path', { d: 'M9 13h6M9 17h6' }]
        ]],
        ['n-iar', [
            ['path', { d: 'M4 13v8h16v-8' }],
            ['path', { d: 'M12 4v8M8 8l4 4 4-4' }]
        ]],
        ['n-inventory', [
            ['rect', { x: '4', y: '4', width: '7', height: '7' }],
            ['rect', { x: '13', y: '4', width: '7', height: '7' }],
            ['rect', { x: '4', y: '13', width: '7', height: '7' }],
            ['rect', { x: '13', y: '13', width: '7', height: '7' }]
        ]],
        ['n-withdraw', [
            ['path', { d: 'M4 15v5h16v-5' }],
            ['path', { d: 'M12 16V6M8 10l4-4 4 4' }]
        ]],
        ['n-return', [
            ['path', { d: 'M5 11h9v9H5z' }],
            ['path', { d: 'M11 5l-6 6 6 6' }]
        ]],
        ['n-product', [
            ['path', { d: 'M4 4h7l9 9-7 7-9-9z' }],
            ['circle', { cx: '8.5', cy: '8.5', r: '1.5' }]
        ]],
        ['n-users', [
            ['circle', { cx: '9', cy: '8', r: '3' }],
            ['path', { d: 'M3.5 19l1-4.5h5L10.5 19' }],
            ['circle', { cx: '16.5', cy: '9', r: '2.5' }],
            ['path', { d: 'M14.5 19l.8-3.5h4.4l.8 3.5' }]
        ]],
        ['n-settings', [
            ['path', { d: 'M4 8h16M4 16h16' }],
            ['rect', { x: '11', y: '6', width: '4', height: '4' }],
            ['rect', { x: '7', y: '14', width: '4', height: '4' }]
        ]],
        ['n-reports', [
            ['path', { d: 'M4 20h16' }],
            ['path', { d: 'M8 20v-7M12 20V6M16 20v-4' }]
        ]],
        ['n-logout', [
            ['path', { d: 'M9 4H4v16h5' }],
            ['path', { d: 'M13 12h8M17 8l4 4-4 4' }]
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
