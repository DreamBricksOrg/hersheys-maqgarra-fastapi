document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    const chancesEl = document.getElementById('chancesCount');
    const carousel = document.getElementById('carousel');
    const dotsContainer = document.getElementById('carouselDots');
    const numeroEl = document.getElementById('numeroValue');
    const posicaoEl = document.getElementById('posicaoValue');
    const btnWarnMe = document.getElementById('btn_warn_me')

    btnWarnMe.addEventListener('click', () => {
        window.location.href = '/pages/user-terms';
    });
    // Expected tags format: ?tags=KEY1,KEY2,KEY3
    const tagsParam = params.get('tags');
    const tagsArray = tagsParam ? tagsParam.split(',') : ['QRCODE-1'];
    const tagsCount = tagsArray.length;

    // Update title with number of chances
    chancesEl.textContent = tagsCount;

    // Generate real QR codes based on tags keys
    tagsArray.forEach((tagKey, index) => {
        const i = index + 1;
        // Slide
        const slide = document.createElement('div');
        slide.className = 'carousel-slide';

        const qrBox = document.createElement('div');
        qrBox.className = 'qr-container';

        const img = document.createElement('img');
        img.src = `https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=${tagKey}`;
        img.alt = `QR Code ${tagKey}`;
        qrBox.appendChild(img);

        const overlay = document.createElement('div');
        overlay.className = 'scanned-overlay';
        const overlayText = document.createElement('span');
        overlayText.textContent = 'escaneado';
        overlay.appendChild(overlayText);
        qrBox.appendChild(overlay);

        const hotspot = document.createElement('div');
        hotspot.className = 'longpress-hotspot';
        qrBox.appendChild(hotspot);
        setupLongPress(hotspot, qrBox);

        qrBox.addEventListener('contextmenu', (e) => e.preventDefault());

        const label = document.createElement('span');
        label.className = 'qr-label';

        slide.appendChild(qrBox);
        slide.appendChild(label);
        carousel.appendChild(slide);

        // Dot
        const dot = document.createElement('span');
        dot.className = 'dot' + (i === 1 ? ' active' : '');
        dot.dataset.index = i - 1;
        dot.addEventListener('click', () => {
            const target = carousel.children[dot.dataset.index];
            target.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
        });
        dotsContainer.appendChild(dot);
        dotsContainer.appendChild(dot);
    });

    // Track active slide via IntersectionObserver
    const slides = carousel.querySelectorAll('.carousel-slide');
    const dots = dotsContainer.querySelectorAll('.dot');

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const idx = Array.from(slides).indexOf(entry.target);
                dots.forEach((d, i) => d.classList.toggle('active', i === idx));
            }
        });
    }, { root: carousel, threshold: 0.6 });

    slides.forEach(slide => observer.observe(slide));

    // Mocked values
    const numero = Math.floor(Math.random() * 900) + 100;
    numeroEl.textContent = numero;

    const posicao = Math.floor(Math.random() * 50) + 1;
    posicaoEl.textContent = posicao;

    // Long-press (1s) on center hotspot to toggle scanned state
    function setupLongPress(hotspot, container) {
        let timer = null;
        const HOLD_MS = 1000;

        function startHold() {
            timer = setTimeout(() => {
                container.classList.toggle('scanned');
            }, HOLD_MS);
        }

        function cancelHold() {
            clearTimeout(timer);
            timer = null;
        }

        hotspot.addEventListener('touchstart', startHold, { passive: true });
        hotspot.addEventListener('touchmove', cancelHold);
        hotspot.addEventListener('touchend', cancelHold);
        hotspot.addEventListener('touchcancel', cancelHold);
        hotspot.addEventListener('mousedown', startHold);
        hotspot.addEventListener('mouseup', cancelHold);
        hotspot.addEventListener('mouseleave', cancelHold);
    }
});
