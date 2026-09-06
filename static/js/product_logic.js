/* product_logic.js — shared product catalog logic (Admin + Staff). Loaded after ui_helpers.js. */

        const dp=document.getElementById('custom-date-picker'); if(dp){ dp.setAttribute('max', new Date().toISOString().split('T')[0]); }
        function toggleCustomDate(v){ const d=document.getElementById('custom-date-picker'); if(v==='Custom') d.classList.remove('hidden'); else { d.classList.add('hidden'); document.getElementById('filter-form').submit(); } }

        function openAddModal(){ document.getElementById('add-modal').classList.remove('hidden'); }
        function closeAddModal(){ document.getElementById('add-modal').classList.add('hidden'); }
        function validateProductForm(f){
            const price=parseFloat(f.price.value); if(isNaN(price)||price<0){ alert('Price must be 0 or more.'); f.price.focus(); return false; }
            return true;
        }
        /* Delete-blocked warning modal: auto-opens when the backend refused
           a delete (data-blocked flag rendered by the catalog route). */
        document.addEventListener('DOMContentLoaded', function(){
            const m = document.getElementById('delete-blocked-modal');
            if(m && m.dataset.blocked === '1') m.classList.remove('hidden');
        });
        function closeDeleteBlockedModal(){ document.getElementById('delete-blocked-modal').classList.add('hidden'); }
        // Static backdrop: only close via .btn-close / Cancel (no backdrop click)
    
        document.addEventListener('DOMContentLoaded', function() {
            const isFromLogin = document.referrer.includes('/login');
            const skeleton = document.getElementById('skeleton-overlay');
            // Only show skeleton when coming from /login, otherwise bypass and do cascade
            if (!isFromLogin) {
                document.getElementById('skeleton-overlay')?.remove();
                const main = document.getElementById('main-dashboard-content');
                if (main) { main.style.opacity = '1'; main.classList.add('loaded'); }
                // Also handle dashboards that use .main-wrapper without #main-dashboard-content
                const fallbackMain = document.querySelector('.main-wrapper') || document.body;
                if (fallbackMain && !main) {
                    fallbackMain.style.opacity = '1';
                }
            }
            // Progressive cascade unveil - top to bottom, sidebar stays static
            const header = document.querySelector('.top-header');
            const cards = document.querySelector('.cards-grid');
            const tables = document.querySelectorAll('.action-bar-card, .table-card, .chart-card, .dashboard-container, .control-card, .content-card, .workspace-grid');
            // Only run cascade if internal navigation (not from login) OR if no skeleton present
            if (!isFromLogin || !skeleton) {
                if (header) { header.classList.add('cascade-unveil'); header.style.animationDelay = '0s'; }
                if (cards) { cards.classList.add('cascade-unveil'); cards.style.animationDelay = '0.25s'; }
                tables.forEach(el => { 
                    if (el.classList.contains('dashboard-container') && el.querySelector('.cards-grid')) return;
                    el.classList.add('cascade-unveil'); el.style.animationDelay = '0.5s'; 
                });
                const lockTarget = document.getElementById('main-dashboard-content') || document.querySelector('.main-wrapper') || document.querySelector('.dashboard-container') || document.body;
                if (lockTarget) {
                    lockTarget.classList.add('cascade-lock');
                    lockTarget.style.pointerEvents = 'none';
                    lockTarget.style.userSelect = 'none';
                    const lastEl = tables.length ? tables[tables.length - 1] : (cards || header);
                    if (lastEl) {
                        lastEl.addEventListener('animationend', () => {
                            lockTarget.classList.remove('cascade-lock');
                            lockTarget.style.pointerEvents = 'auto';
                            lockTarget.style.userSelect = 'auto';
                        }, { once: true });
                    }
                    setTimeout(() => {
                        lockTarget.classList.remove('cascade-lock');
                        lockTarget.style.pointerEvents = 'auto';
                        lockTarget.style.userSelect = 'auto';
                    }, 1800);
                }
            }

            // Navigation-Only Unveil Trigger: suppress cascade for search/filter/refresh
            const isNavigation = document.referrer && !document.referrer.includes(window.location.pathname);
            const hasSearchOrFilter = window.location.search.length > 0;
            if (!isNavigation || hasSearchOrFilter) {
                document.querySelectorAll('.top-header, .cards-grid, .action-bar-card, .table-card, .dashboard-container, .control-card')
                    .forEach(el => {
                        el.classList.remove('cascade-unveil');
                        el.style.opacity = '1';
                        el.style.transform = 'none';
                        el.style.clipPath = 'none';
                        el.style.animation = 'none';
                    });
                const lockTarget2 = document.getElementById('main-dashboard-content') || document.querySelector('.main-wrapper') || document.querySelector('.dashboard-container') || document.body;
                if (lockTarget2) {
                    lockTarget2.classList.remove('cascade-lock');
                    lockTarget2.style.pointerEvents = 'auto';
                    lockTarget2.style.userSelect = 'auto';
                }
            }
        });
    
        /* Staff products page only: suppress entrance animation on fresh navigation/search (preserves admin behavior). */
        if (window.location.pathname.indexOf('/staff/') === 0) {

        // Navigation-Only Unveil Trigger for Staff Product
        document.addEventListener('DOMContentLoaded', function() {
            const isNavigationFromOtherPage = document.referrer && !document.referrer.includes(window.location.pathname);
            const hasSearchOrFilter = window.location.search.length > 0;
            if (!isNavigationFromOtherPage || hasSearchOrFilter) {
                document.querySelectorAll('.top-header, .cards-grid, .action-bar-card, .table-card, .dashboard-container, .control-card')
                    .forEach(el => {
                        el.classList.remove('cascade-unveil');
                        el.style.opacity = '1';
                        el.style.transform = 'none';
                        el.style.animation = 'none';
                    });
            }
        });
        }
