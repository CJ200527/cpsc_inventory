/* ui_helpers.js — shared page chrome: live clock, toast auto-dismiss, cascade unveil. */
function updateClock(){
    const now = new Date();
    const clockEl = document.getElementById('live-clock');
    if(!clockEl) return;
    clockEl.innerText = `${now.toLocaleDateString('en-US', {month:'long', day:'numeric', year:'numeric'})} | ${now.toLocaleTimeString('en-US', {hour:'2-digit', minute:'2-digit', second:'2-digit', hour12:true})}`;
}
setInterval(updateClock, 1000); updateClock();

        document.addEventListener('DOMContentLoaded', function() {
            const toasts = document.querySelectorAll('.toast-card');
            toasts.forEach(toast => {
                setTimeout(() => {
                    toast.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
                    toast.style.opacity = '0';
                    toast.style.transform = 'translateY(-20px) scale(0.9)';
                    setTimeout(() => { if (toast.parentNode) toast.remove(); }, 400);
                }, 4000);
            });
        });
    
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
                    // avoid double-animating the container if it contains cards/header
                    if (el.classList.contains('dashboard-container') && el.querySelector('.cards-grid')) return;
                    el.classList.add('cascade-unveil'); el.style.animationDelay = '0.5s'; 
                });
                // Click lock during transition
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
        });
    
        /* ---- front-shell skeleton loader (from base.html) ---- */
        const SKELETON_ENABLED = true;
        document.addEventListener('DOMContentLoaded', function() {
            const skeleton = document.getElementById('skeleton-overlay');
            const main = document.getElementById('main-dashboard-content');
            const isFromLogin = document.referrer.includes('/login');
            if (!isFromLogin) {
                document.getElementById('skeleton-overlay')?.remove();
                if (main) { main.style.opacity = '1'; main.classList.add('loaded'); }
                // Progressive cascade unveil - top to bottom, sidebar stays static
                const header = document.querySelector('.top-header');
                const cards = document.querySelector('.cards-grid');
                const tables = document.querySelectorAll('.action-bar-card, .table-card, .chart-card, .dashboard-container, .control-card');
                if (header) { header.classList.add('cascade-unveil'); header.style.animationDelay = '0s'; }
                if (cards) { cards.classList.add('cascade-unveil'); cards.style.animationDelay = '0.25s'; }
                tables.forEach(el => { el.classList.add('cascade-unveil'); el.style.animationDelay = '0.5s'; });
                // Click lock during transition
                const lockTarget = document.getElementById('main-dashboard-content') || document.querySelector('.main-wrapper') || document.body;
                if (lockTarget) {
                    lockTarget.classList.add('cascade-lock');
                    lockTarget.style.pointerEvents = 'none';
                    lockTarget.style.userSelect = 'none';
                    const lastEl = tables[tables.length - 1] || cards || header;
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
                return;
            }
            if (!SKELETON_ENABLED || !skeleton || !main) {
                if (skeleton) skeleton.style.display = 'none';
                if (main) { main.style.opacity = '1'; main.classList.add('loaded'); }
                return;
            }
            setTimeout(() => {
                skeleton.style.transition = 'opacity 0.4s ease';
                skeleton.style.opacity = '0';
                main.classList.add('loaded');
                main.style.opacity = '1';
                setTimeout(() => { skeleton.style.display = 'none'; }, 400);
            }, 1200);
        });
