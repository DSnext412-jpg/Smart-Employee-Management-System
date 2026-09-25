document.addEventListener('DOMContentLoaded', function() {
    var sidebar = document.querySelector('.sidebar');
    if (sidebar) {
        var toggleBtn = document.createElement('button');
        toggleBtn.textContent = '';
        toggleBtn.className = 'sidebar-toggle';
        toggleBtn.style.cssText = 'display:none;position:fixed;top:4rem;left:0.5rem;z-index:1001;background:var(--primary-color);color:#fff;border:none;border-radius:4px;padding:0.4rem 0.6rem;cursor:pointer;font-size:1.2rem;';
        toggleBtn.setAttribute('aria-label', 'Toggle sidebar');
        document.body.appendChild(toggleBtn);

        function checkSidebar() {
            if (window.innerWidth <= 768) {
                toggleBtn.style.display = 'block';
                sidebar.classList.remove('active');
            } else {
                toggleBtn.style.display = 'none';
                sidebar.classList.add('active');
            }
        }
        checkSidebar();
        window.addEventListener('resize', checkSidebar);
        toggleBtn.addEventListener('click', function() {
            sidebar.classList.toggle('active');
        });
    }
});