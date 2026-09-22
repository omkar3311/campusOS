(() => {
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => document.querySelectorAll(s);

  const body = document.body;
  const cursor = $(".cursor");
  const panels = [...$$(".panel")];
  const reveals = $$(".reveal");
  const cards = $$(".visual");
  const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---------- Mouse Glow Cursor ---------- */
  if (cursor && !reduceMotion) {
    let mx = innerWidth / 2, my = innerHeight / 2;
    let cx = mx, cy = my;

    window.addEventListener("pointermove", (e) => {
      mx = e.clientX;
      my = e.clientY;
    }, { passive: true });

    function animateCursor() {
      cx += (mx - cx) * 0.12;
      cy += (my - cy) * 0.12;
      cursor.style.transform = `translate(${cx}px, ${cy}px)`;
      requestAnimationFrame(animateCursor);
    }
    requestAnimationFrame(animateCursor);
  }

  /* ---------- Scroll Reveal Observer ---------- */
  const revealObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("show");
      } else {
        entry.target.classList.remove("show");
      }
    });
  }, { threshold: 0.15 });

  reveals.forEach((el) => revealObserver.observe(el));

  /* ---------- Smooth 3D Cinematic Scroll Camera ---------- */
  let lastScrollY = window.scrollY;
  let ticking = false;

  function updateCamera() {
    const vh = window.innerHeight;
    const center = vh * 0.5;

    panels.forEach((panel) => {
      const rect = panel.getBoundingClientRect();
      const panelCenter = rect.top + rect.height * 0.5;
      const progress = (panelCenter - center) / (vh * 0.85);
      const clampedP = Math.max(-1, Math.min(1, progress));

      if (!reduceMotion) {
        const depth = clampedP * 140;
        const scale = 1 - Math.abs(clampedP) * 0.06;
        const rotate = clampedP * 2.5;
        const blur = Math.abs(clampedP) * 3;
        const opacity = 1 - Math.abs(clampedP) * 0.28;

        panel.style.transform = `translate3d(0, ${clampedP * 45}px, ${depth}px) scale(${scale}) rotateX(${rotate}deg)`;
        panel.style.opacity = opacity;
        panel.style.filter = `blur(${blur}px)`;
      }
    });

    ticking = false;
  }

  window.addEventListener("scroll", () => {
    if (!ticking) {
      requestAnimationFrame(updateCamera);
      ticking = true;
    }
  }, { passive: true });

  if (!reduceMotion) updateCamera();

  /* ---------- 3D Card Interactive Tilt ---------- */
  cards.forEach((card) => {
    if (reduceMotion) return;

    card.addEventListener("mousemove", (e) => {
      const r = card.getBoundingClientRect();
      const x = (e.clientX - r.left) / r.width - 0.5;
      const y = (e.clientY - r.top) / r.height - 0.5;

      const rx = -y * 12;
      const ry = x * 12;

      card.style.transform = `perspective(1000px) rotateX(${rx}deg) rotateY(${ry}deg) translateY(-6px)`;
    });

    card.addEventListener("mouseleave", () => {
      card.style.transform = "";
    });
  });

  /* ---------- Interactive Dynamic Score Fluctuation ---------- */
  const scoreVal = $(".score-val");
  if (scoreVal) {
    let score = 96.4;
    setInterval(() => {
      score += (Math.random() - 0.5) * 0.4;
      score = Math.max(95.5, Math.min(98.2, score));
      scoreVal.textContent = score.toFixed(1) + "%";
    }, 2000);
  }

  /* ---------- Helpdesk Dynamic Chat Rotator ---------- */
  const userChatP = $(".campus-chat-window .chat-bubble.user p");
  const botChatP = $(".campus-chat-window .chat-bubble.bot p");

  if (userChatP && botChatP) {
    const chatPairs = [
      {
        q: "When is the deadline for CS402 assignment submission?",
        a: "CS402 Assignment #3 is due tomorrow, <b>Oct 24 at 11:59 PM</b> via CampusOS Portal."
      },
      {
        q: "How do I request a bonafide certificate?",
        a: "Submit a request under <b>Services > Certificates</b>. Auto-approved in <b>5 mins</b>."
      },
      {
        q: "Where is Dr. Sharma's office located?",
        a: "Dr. Sharma is in <b>Block B, Room 304</b>. Office hours: <b>2:00 PM - 4:00 PM</b>."
      }
    ];

    let chatIdx = 0;
    setInterval(() => {
      chatIdx = (chatIdx + 1) % chatPairs.length;
      const pair = chatPairs[chatIdx];

      userChatP.style.opacity = "0";
      botChatP.parentElement.style.opacity = "0";

      setTimeout(() => {
        userChatP.textContent = pair.q;
        botChatP.innerHTML = pair.a;
        userChatP.style.opacity = "1";
        botChatP.parentElement.style.opacity = "1";
      }, 300);
    }, 5000);
  }

  /* ---------- Header Active State & Scroll Bar ---------- */
  const header = $(".header");
  const progressBar = document.createElement("div");
  progressBar.className = "progress-bar";
  body.appendChild(progressBar);

  window.addEventListener("scroll", () => {
    if (window.scrollY > 40) {
      header?.classList.add("active");
    } else {
      header?.classList.remove("active");
    }

    const doc = document.documentElement;
    const scrollP = doc.scrollTop / (doc.scrollHeight - doc.clientHeight);
    progressBar.style.transform = `scaleX(${scrollP})`;
  }, { passive: true });

  /* ---------- Dynamic Section Background Palette Transition ---------- */
  const sectionColors = [
    "#070709",
    "#091024",
    "#180a24",
    "#05151c",
    "#061a16",
    "#070709"
  ];

  window.addEventListener("scroll", () => {
    let currentIdx = 0;
    panels.forEach((panel, i) => {
      const r = panel.getBoundingClientRect();
      if (r.top < innerHeight * 0.45 && r.bottom > innerHeight * 0.45) {
        currentIdx = i;
      }
    });

    if (sectionColors[currentIdx]) {
      body.style.background = sectionColors[currentIdx];
    }
  }, { passive: true });
})();