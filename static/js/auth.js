/* auth.js — login/signup toggle + auth page transitions. Loaded after ui_helpers.js. */

        function toggleForm() {
            const card = document.getElementById('main-card');
            const signin = document.getElementById('signin-form');
            const signup = document.getElementById('signup-form');
            const title = document.getElementById('banner-title');
            const text = document.getElementById('banner-text');
            const btn = document.getElementById('toggle-btn');

            if (signin.classList.contains('hidden')) {
                signup.classList.add('fade-out-right');

                setTimeout(() => {
                    signup.classList.add('hidden');
                    signup.classList.remove('fade-out-right');

                    card.classList.remove('signup-mode');
                    signin.classList.add('fade-out');
                    signin.classList.remove('hidden');

                    title.innerText = 'Hello, Friend';
                    text.innerText = 'Enter your Personal Informations To Create A User';
                    btn.innerText = 'Sign Up';

                    setTimeout(() => {
                        signin.classList.remove('fade-out');
                    }, 50);
                }, 200);

            } else {
                signin.classList.add('fade-out');

                setTimeout(() => {
                    signin.classList.add('hidden');
                    signin.classList.remove('fade-out');

                    card.classList.add('signup-mode');
                    signup.classList.add('fade-out-right');
                    signup.classList.remove('hidden');

                    title.innerText = 'Hello, Friend';
                    text.innerText = 'Already has a user? please Log in using your created user.';
                    btn.innerText = 'Log In';

                    setTimeout(() => {
                        signup.classList.remove('fade-out-right');
                    }, 50);
                }, 200);
            }
        }
    
        // fx21 label sync (covers typed text AND late browser autofill,
        // which fires no input event — re-check after paint).
        function syncAuthFx21(){
            document.querySelectorAll('.form-container .effect-21').forEach(inp=>{
                inp.classList.toggle('has-content',(inp.value||'').trim()!=='');
            });
        }
        document.addEventListener('DOMContentLoaded', function(){
            syncAuthFx21();
            setTimeout(syncAuthFx21, 400);
            setTimeout(syncAuthFx21, 1200);
        });

        // Smooth transition for Forgot Password link

        document.addEventListener('DOMContentLoaded', function() {
            const forgotLink = document.querySelector('.forgot-pass');
            if (forgotLink) {
                forgotLink.addEventListener('click', function(e) {
                    e.preventDefault();
                    const href = this.getAttribute('href');
                    const card = document.getElementById('main-card');
                    card.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                    card.style.opacity = '0';
                    card.style.transform = 'scale(0.97)';
                    document.body.style.transition = 'opacity 0.3s ease';
                    document.body.style.opacity = '0';
                    setTimeout(() => { window.location.href = href; }, 300);
                });
            }
        });
    
        // Smooth exit transition (guarded: login page has no back button)
        (function(){
            const backBtn = document.getElementById('back-to-login');
            if(!backBtn) return;

        document.getElementById('back-to-login').addEventListener('click', function(e) {
            e.preventDefault();
            const href = this.getAttribute('href');
            const card = document.getElementById('reset-card');
            card.classList.add('fade-out');
            document.body.style.transition = 'opacity 0.3s ease';
            document.body.style.opacity = '0';
            setTimeout(() => { window.location.href = href; }, 300);
        });
    
        })();
