/* Theme: follows the system light/dark preference automatically.
   The moon/sun button stores a manual override in localStorage; choosing
   the theme that matches the system again clears the override so the
   page resumes tracking system changes live. Loaded synchronously in
   <head> so the data-theme attribute is set before first paint. */
(function () {
    var root = document.documentElement;
    var media = window.matchMedia('(prefers-color-scheme: dark)');
    var stored = null;
    try { stored = localStorage.getItem('theme'); } catch (e) {}
    if (stored === 'dark' || stored === 'light') root.setAttribute('data-theme', stored);

    function effective() {
        return root.getAttribute('data-theme') || (media.matches ? 'dark' : 'light');
    }

    function sync() {
        var dark = effective() === 'dark';
        var meta = document.querySelector('meta[name="theme-color"]');
        if (meta) meta.setAttribute('content', dark ? '#161616' : '#ffffff');
        var btn = document.getElementById('themeToggle');
        if (btn) {
            var label = dark ? 'Switch to light theme' : 'Switch to dark theme';
            btn.setAttribute('aria-label', label);
            btn.setAttribute('title', label);
        }
    }

    function wire() {
        var btn = document.getElementById('themeToggle');
        if (btn) btn.addEventListener('click', function () {
            var next = effective() === 'dark' ? 'light' : 'dark';
            var system = media.matches ? 'dark' : 'light';
            if (next === system) {
                root.removeAttribute('data-theme');
                try { localStorage.removeItem('theme'); } catch (e) {}
            } else {
                root.setAttribute('data-theme', next);
                try { localStorage.setItem('theme', next); } catch (e) {}
            }
            sync();
        });
        sync();
    }

    if (media.addEventListener) media.addEventListener('change', sync);
    else if (media.addListener) media.addListener(sync);

    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', wire);
    else wire();
})();
