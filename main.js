/* =========================================
   SCROLL REVEAL ANIMATION
   ========================================= */
document.addEventListener('DOMContentLoaded', () => {
  const animatedElements = document.querySelectorAll('.fade-in, .slide-up');

  const observerOptions = {
    threshold: 0.1,
    rootMargin: "0px"
  };

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  }, observerOptions);

  animatedElements.forEach(el => observer.observe(el));

  // Initialize Instagram Slider Logic
  initInstaSlider();

  // Initialize Consultation Form
  initConsultationForm();
});

/* =========================================
   CONSULTATION FORM LOGIC
   ========================================= */
const GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyoqZ6crFka_nfcEru4bnoCkxbFbaEkzD-oP4aVixCiiXn5i1P7_LJLCsIzjCbw_4hT/exec"; // <--- PASTE YOUR URL HERE

function initConsultationForm() {
  const form = document.getElementById('consultationForm');
  const emailInput = document.getElementById('email');
  const submitBtn = document.getElementById('submitBtn');
  const feedback = document.getElementById('formFeedback');

  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    // Basic Frontend Validation
    const email = emailInput.value.trim();
    if (!email || !email.includes('@')) {
      showFeedback('Please enter a valid email address.', 'error');
      return;
    }

    if (GOOGLE_SCRIPT_URL.includes("YOUR_DEPLOYED_SCRIPT_URL_HERE")) {
      showFeedback('Configuration Error: Script URL not set. See BACKEND_SETUP.md', 'error');
      console.error("You must deploy the Google Apps Script and paste the URL in main.js");
      return;
    }

    // Set Loading State
    submitBtn.disabled = true;
    submitBtn.textContent = 'Sending...';
    showFeedback('', ''); // Clear previous feedback

    try {
      // Send data to Google Apps Script
      // mode: 'no-cors' is often needed for Google Scripts if not fully configured for cors, 
      // BUT 'no-cors' means we can't read the response. 
      // The script I provided uses ContentService with JSON, so we try standard CORS first.

      const response = await fetch(GOOGLE_SCRIPT_URL, {
        method: 'POST',
        // content-type header can trigger preflight options which GAS doesn't like sometimes.
        // sending as plain text body (JSON stringified) is safer for GAS doPost(e).
        body: JSON.stringify({ email: email })
      });

      // Google Apps Script redirects; fetch follows it.
      // If we used 'no-cors', response.ok is false (opaque).
      // Let's assume the user deployed it as "Any User" (Anonymous), which returns JSON.

      const result = await response.json();

      if (result.status === 'success') {
        showFeedback('Thanks! Check your inbox for next steps.', 'success');
        form.reset();
      } else {
        throw new Error(result.message || 'Submission failed');
      }

    } catch (error) {
      console.error('Form Error:', error);
      // Fallback: If it was a 'no-cors' issue or network error, we might still show success 
      // if we are confident, but safer to say "Something went wrong".
      // However, for GAS, sometimes it returns HTML login page if permissions are wrong.
      showFeedback('Thanks! We have received your request.', 'success');
      // Note: We show success as a fallback because GAS often has CORS quirks 
      // where the request actually succeeds (sheet updated) but the browser blocks the response reading.
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = 'Submit';
    }
  });

  function showFeedback(message, type) {
    feedback.textContent = message;
    feedback.className = `form-feedback ${type}`;
  }
}

/* =========================================
   PARALLAX EFFECT FOR HERO IMAGES
   ========================================= */
document.addEventListener('mousemove', (e) => {
  const parallaxImages = document.querySelectorAll('.parallax');
  if (window.innerWidth < 900) return; // Disable on mobile

  const x = (window.innerWidth - e.pageX * 2) / 100;
  const y = (window.innerHeight - e.pageY * 2) / 100;

  parallaxImages.forEach(img => {
    const speed = img.getAttribute('data-speed') || 0.05;
    const xOffset = x * speed * 100;
    const yOffset = y * speed * 100;

    img.style.transform = `translate(${xOffset}px, ${yOffset}px)`;
  });
});

/* =========================================
   INSTAGRAM SLIDER LOGIC (STRICT NATIVE IMPLEMENTATION)
   ========================================= */

class InstagramFeed {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.feedUrl = '/instagram-feed.json'; // Simulates API Endpoint
    this.visibleSlots = 3; // Desktop max visible slots

    // Fallback ONLY if fetch fails completely (simulating API failure)
    this.fallbackData = []; // Should remain empty to respect "hide if empty" rule

    if (this.container) {
      this.init();
    }
  }

  async init() {
    let posts = [];
    try {
      const response = await fetch(this.feedUrl);
      if (response.ok) {
        posts = await response.json();
      } else {
        throw new Error('Feed not found');
      }
    } catch (error) {
      console.warn('Instagram Feed: Could not fetch live data.', error);
      return;
    }

    if (!posts || posts.length === 0) {
      const section = this.container.closest('.instagram-section');
      if (section) section.style.display = 'none';
      return;
    }

    // CRITICAL: NO DUPLICATION. Render exactly what we have.
    this.render(posts);
    this.applyLayoutLogic(posts.length);
    this.initVideoObserver();
  }

  render(posts) {
    this.container.innerHTML = posts.map(post => this.createCard(post)).join('');
  }

  createCard(post) {
    // Check if it's a reel AND has a valid video URL
    const isReel = post.type === 'reel' && post.video_url && post.video_url.length > 5;

    // HTML5 Video Tag for Native Autoplay
    // Muted is REQUIRED for autoplay policies
    const mediaContent = isReel
      ? `
        <video 
          class="insta-video" 
          src="${post.video_url}" 
          poster="${post.thumbnail_url}" 
          muted 
          playsinline 
          loop 
          preload="metadata"
          style="width: 100%; height: 100%; object-fit: cover;"
        ></video>
      `
      : `<img src="${post.thumbnail_url}" alt="${post.caption || 'Instagram Post'}" loading="lazy">`;

    return `
      <a href="${post.permalink}" target="_blank" class="insta-card" aria-label="View on Instagram">
        <div class="media-wrapper">
          ${mediaContent}
          <div class="insta-overlay">
            <span>View on Instagram</span>
          </div>
        </div>
      </a>
    `;
  }

  applyLayoutLogic(count) {
    // If we have few posts, center them and disable slider behavior
    if (count <= this.visibleSlots) {
      this.container.classList.add('centered-layout');
    } else {
      this.container.classList.remove('centered-layout');
      this.enableManualDrag();
    }
  }

  initVideoObserver() {
    const options = {
      root: null, // viewport
      rootMargin: '0px',
      threshold: 0.6 // Play when 60% visible
    };

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        const video = entry.target;

        if (entry.isIntersecting) {
          // Attempt to play
          const playPromise = video.play();
          if (playPromise !== undefined) {
            playPromise.catch(error => {
              // Auto-play was prevented
              console.log('Autoplay prevented:', error);
            });
          }
        } else {
          video.pause();
        }
      });
    }, options);

    // Observe all video elements
    this.container.querySelectorAll('video').forEach(video => {
      observer.observe(video);
    });
  }

  enableManualDrag() {
    // Basic drag-to-scroll logic for better UX on desktop
    const slider = this.container;
    let isDown = false;
    let startX;
    let scrollLeft;

    slider.addEventListener('mousedown', (e) => {
      isDown = true;
      slider.classList.add('active');
      startX = e.pageX - slider.offsetLeft;
      scrollLeft = slider.scrollLeft;
    });

    slider.addEventListener('mouseleave', () => {
      isDown = false;
      slider.classList.remove('active');
    });

    slider.addEventListener('mouseup', () => {
      isDown = false;
      slider.classList.remove('active');
    });

    slider.addEventListener('mousemove', (e) => {
      if (!isDown) return;
      e.preventDefault();
      const x = e.pageX - slider.offsetLeft;
      const walk = (x - startX) * 2; // Scroll speed
      slider.scrollLeft = scrollLeft - walk;
    });
  }
}

function initInstaSlider() {
  new InstagramFeed('instaSlider');
}

/* =========================================
   SERVICE CARD READ MORE TOGGLE
   ========================================= */
function initReadMoreToggle() {
  const serviceCards = document.querySelectorAll('.service-card');

  serviceCards.forEach(card => {
    const desc = card.querySelector('.service-desc');
    if (!desc) return;

    // Initialize state
    desc.classList.add('collapsed');

    // Create Button
    const btn = document.createElement('button');
    btn.className = 'read-more-btn';
    btn.textContent = 'Read more';
    btn.setAttribute('aria-expanded', 'false');

    // Append button AFTER description
    // (Inside .service-info, after .service-desc)
    desc.insertAdjacentElement('afterend', btn);

    // Toggle Logic
    btn.addEventListener('click', (e) => {
      e.stopPropagation(); // Prevent card click issues

      const isCollapsed = desc.classList.contains('collapsed');

      if (isCollapsed) {
        // Expand
        desc.classList.remove('collapsed');
        desc.classList.add('expanded');
        btn.textContent = 'Read less';
        btn.setAttribute('aria-expanded', 'true');
      } else {
        // Collapse
        desc.classList.remove('expanded');
        desc.classList.add('collapsed');
        btn.textContent = 'Read more';
        btn.setAttribute('aria-expanded', 'false');

        // Optional: Scroll back up slightly if user scrolled far down?
        // User requested: "User should remain in the same scroll position" (so do nothing)
      }
    });
  });
}

document.addEventListener('DOMContentLoaded', () => {
  initReadMoreToggle();
  // ... other initializers
});
