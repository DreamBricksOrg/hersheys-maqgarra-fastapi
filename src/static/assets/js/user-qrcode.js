document.addEventListener('DOMContentLoaded', async () => {
    const params = new URLSearchParams(window.location.search);
    const chancesEl = document.getElementById('chancesCount');
    const carousel = document.getElementById('carousel');
    const dotsContainer = document.getElementById('carouselDots');
    const numeroEl = document.getElementById('numeroValue');
    const posicaoEl = document.getElementById('posicaoValue');
    const btnWarnMe = document.getElementById('btn_warn_me');
    const pageWrapper = document.getElementById('pageWrapper');
    const doneWrapper = document.getElementById('doneWrapper');
    const posicaoContainer = document.getElementById('posicaoContainer');
    const calledContainer = document.getElementById('calledContainer');
    const buttonsContainer = document.getElementById('buttonsContainer');

    let qid = params.get('qid');
    let sid = params.get('sid');

    if (qid) setQueueId(qid);
    if (sid) setSessionId(sid);

    if (!qid) qid = getQueueId();
    if (!sid) sid = getSessionId();

    if (!qid || !sid) {
        console.error('Missing qid or sid parameters');
        return;
    }

    const AUTH_HEADERS = {
        'Content-Type': 'application/json',
        'x-api-key': 'capibarra-tablet-01',
        'x-device-id': 'tablet-01'
    };

    btnWarnMe.addEventListener('click', () => {
        window.location.href = `/pages/user-terms?sid=${sid}&qid=${qid}`;
    });

    try {
        const [tagsResp, queueResp] = await Promise.all([
            fetch(`/api/sessions/${sid}/tags`, { headers: AUTH_HEADERS }),
            fetch(`/api/queue/${qid}`, { headers: AUTH_HEADERS })
        ]);

        if (!tagsResp.ok || !queueResp.ok) {
            throw new Error('Falha ao carregar dados do servidor');
        }

        const tagsData = await tagsResp.json();
        const queueData = await queueResp.json();

        const tagsArray = tagsData.tags || [];
        const tagsCount = tagsArray.length;

        // Update UI elements
        chancesEl.textContent = tagsCount;
        numeroEl.textContent = queueData.queue_number || '--';
        posicaoEl.textContent = (queueData.people_ahead !== undefined) ? (queueData.people_ahead + 1) : '--';

        // Generate QR codes based on tag_key
        tagsArray.forEach((tag, index) => {
            const i = index + 1;
            const tagKey = tag.tag_key;

            // Slide
            const slide = document.createElement('div');
            slide.className = 'carousel-slide';

            const qrBox = document.createElement('div');
            qrBox.className = 'qr-container';

            const img = document.createElement('img');
            img.src = `https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=${encodeURIComponent(tagKey)}`;
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
            // label.textContent = `TAG ${i}`; // Opcional: mostrar número da tag

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
        });

        // Track active slide via IntersectionObserver
        setupCarouselObserver();

    } catch (err) {
        console.error('Erro ao inicializar página de QR Codes:', err);
    }

    // Polling de status a cada 5 segundos
    setInterval(updateQueueStatus, 5000);

    async function updateQueueStatus() {
        try {
            const resp = await fetch(`/api/queue/${qid}`, { headers: AUTH_HEADERS });
            if (!resp.ok) return;
            const data = await resp.json();
            updateUIByStatus(data);
        } catch (e) {
            console.warn('[DEBUG] Erro no polling:', e);
        }
    }

    function updateUIByStatus(data) {
        const { status, people_ahead, queue_number } = data;
        
        // Atualiza posição/número se ainda estiver na fila
        if (numeroEl) numeroEl.textContent = queue_number || '--';
        if (posicaoEl) posicaoEl.textContent = (people_ahead !== undefined) ? (people_ahead + 1) : '--';

        if (status === 'called' || status === 'playing') {
            if (posicaoContainer) posicaoContainer.style.display = 'none';
            if (calledContainer) calledContainer.style.display = 'flex';
            if (buttonsContainer) buttonsContainer.style.display = 'none';
        } else if (status === 'done') {
            if (pageWrapper) pageWrapper.style.display = 'none';
            if (doneWrapper) doneWrapper.style.display = 'flex';
            document.body.style.overflow = 'hidden'; // Evita scroll na tela de agradecimento
        } else {
            // "waiting" ou outro
            if (posicaoContainer) posicaoContainer.style.display = 'flex';
            if (calledContainer) calledContainer.style.display = 'none';
        }
    }

    function setupCarouselObserver() {
        const slides = carousel.querySelectorAll('.carousel-slide');
        const dots = dotsContainer.querySelectorAll('.dot');
        if (slides.length === 0) return;

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const idx = Array.from(slides).indexOf(entry.target);
                    dots.forEach((d, i) => d.classList.toggle('active', i === idx));
                }
            });
        }, { root: carousel, threshold: 0.6 });

        slides.forEach(slide => observer.observe(slide));
    }

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
