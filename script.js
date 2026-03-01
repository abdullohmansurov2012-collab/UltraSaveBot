/**
 * UltraSave Web App - Main Script
 * Handles UI interactions, API requests (via Cobalt), and dynamic DOM rendering.
 */

document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const downloadForm = document.getElementById('downloadForm');
    const videoUrlInput = document.getElementById('videoUrl');
    const searchSection = document.querySelector('.search-section');
    const loaderSection = document.getElementById('loaderSection');
    const resultsSection = document.getElementById('resultsSection');
    const qualityList = document.getElementById('qualityList');
    const newSearchBtn = document.getElementById('newSearchBtn');
    const toastContainer = document.getElementById('toastContainer');

    // Video Info Elements
    const videoTitle = document.getElementById('videoTitle');
    const videoSource = document.getElementById('videoSource');
    const videoThumb = document.getElementById('videoThumb');

    // Form Submit Handler
    downloadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const url = videoUrlInput.value.trim();

        if (!url) {
            showToast('Iltimos, video manzilini kiriting!');
            return;
        }

        if (!isValidUrl(url)) {
            showToast('Kiritilgan manzil noto\'g\'ri formatda!');
            return;
        }

        if (url.includes('youtube.com') || url.includes('youtu.be')) {
            showToast('DIQQAT: YouTube tizimida texnik ishlar ketmoqda, hozircha undan yuklab bo\'lmaydi.');
            // We can still try, or prevent it. User asked to write it clearly, 
            // but didn't say to block it completely. I'll just show the toast and let it try.
        }

        await processRealVideo(url);
    });

    // New Search Button
    newSearchBtn.addEventListener('click', () => {
        resultsSection.style.display = 'none';
        searchSection.style.display = 'block';
        videoUrlInput.value = '';
        videoUrlInput.focus();
    });

    // Process Video via Python Backend API
    async function processRealVideo(url) {
        // Hide search, show loader
        searchSection.style.display = 'none';
        loaderSection.style.display = 'flex';
        qualityList.innerHTML = '';

        try {
            // Using a relative path so it works everywhere (Local and Render)
            const apiUrl = '/api/download';

            const response = await fetch(apiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({
                    url: url
                })
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || "Serverdan xato javob keldi.");
            }

            const data = await response.json();

            if (data.status !== "success") {
                throw new Error("Noma'lum xatolik yuz berdi.");
            }

            renderRealResults(data);

            // Show results
            loaderSection.style.display = 'none';
            resultsSection.style.display = 'flex';

        } catch (error) {
            console.error("Error fetching video:", error);
            loaderSection.style.display = 'none';
            searchSection.style.display = 'block';
            showToast(`Xatolik: ${error.message}`);
        }
    }

    // Render Real Results
    function renderRealResults(data) {
        // Identify platform for UI icons based on extractor name
        const platformStr = data.platform.toLowerCase();
        let platformIcon = 'bx-video';
        let platformName = 'Video';

        if (platformStr.includes('instagram')) { platformIcon = 'bxl-instagram'; platformName = 'Instagram'; }
        else if (platformStr.includes('youtube')) { platformIcon = 'bxl-youtube'; platformName = 'YouTube'; }
        else if (platformStr.includes('tiktok')) { platformIcon = 'bxl-tiktok'; platformName = 'TikTok'; }

        videoTitle.textContent = data.title || "Video Muvaqqaiyatli Topildi!";
        videoSource.innerHTML = `<i class='bx ${platformIcon}'></i> ${platformName}`;

        if (data.thumbnail) {
            videoThumb.src = data.thumbnail;
        } else {
            videoThumb.src = "https://images.unsplash.com/photo-1611162617474-5b21e879e113?q=80&w=600&auto=format&fit=crop";
        }

        // Clear previous qualities
        qualityList.innerHTML = '';

        if (data.qualities && data.qualities.length > 0) {
            data.qualities.forEach((q, index) => {
                let badgeClass = 'q-sd';
                if (q.height.includes('720') || q.height.includes('1080') || q.height === 'Avto') badgeClass = 'q-hd';
                if (q.height.includes('1440') || q.height.includes('2k') || q.height.includes('2160') || q.height.includes('4k')) badgeClass = 'q-4k';

                const sizeLabel = q.size !== "Noma'lum" ? `~${q.size} MB` : `(${q.ext.toUpperCase()})`;

                renderSingleQualityCard(q.url, q.height, sizeLabel, badgeClass, index);
            });
        } else {
            showToast("Video formatlari topilmadi.");
        }
    }

    function renderSingleQualityCard(downloadUrl, heightLabel, sizeLabel, badgeClass, index = 0) {
        const card = document.createElement('div');
        card.className = `quality-card ${badgeClass}`;

        // Check if 1080p for recommended badge
        const isRecommended = heightLabel === '1080p' || heightLabel.includes('1080');
        const recommendedBadge = isRecommended ? '<span class="recommended-badge"><i class="bx bxs-star"></i> Tavsiya etiladi</span>' : '';

        // Add a nice staggered entrance animation for each card
        card.style.animation = `fadeInUp 0.6s cubic-bezier(0.34, 1.56, 0.64, 1) ${index * 0.15}s both`;

        card.innerHTML = `
            ${recommendedBadge}
            <div class="quality-header">
                <span class="quality-badge">${heightLabel}</span>
                <span class="size-info">${sizeLabel}</span>
            </div>
            <a href="${downloadUrl}" target="_blank" rel="noopener noreferrer" class="btn-download-sm" style="text-decoration: none;">
                <i class='bx bx-download'></i> Yuklab olish
            </a>
        `;

        qualityList.appendChild(card);
    }

    // Helper: Identify Platform from URL
    function identifyPlatform(url) {
        if (url.includes('instagram.com')) return 'Instagram';
        if (url.includes('youtube.com') || url.includes('youtu.be')) return 'YouTube';
        if (url.includes('tiktok.com')) return 'TikTok';
        return 'Boshqa Manba';
    }

    // Helper: Valid URL Check
    function isValidUrl(string) {
        try {
            new URL(string);
            return true;
        } catch (_) {
            return false;
        }
    }

    // Toast Notification System
    window.showToast = function (message) {
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.innerHTML = `<i class='bx bx-info-circle'></i> ${message}`;

        toastContainer.appendChild(toast);

        setTimeout(() => {
            if (toast.parentElement) toast.remove();
        }, 3000);
    }
});
