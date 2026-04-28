/* DrugMind v2.0 — Interactive Functionality */
(function() {
  'use strict';

  /* Mobile Nav */
  var toggle = document.querySelector('.nav-toggle');
  var navLinks = document.querySelector('.nav-links');
  if (toggle && navLinks) {
    toggle.addEventListener('click', function() { navLinks.classList.toggle('open'); });
    document.addEventListener('click', function(e) {
      if (!toggle.contains(e.target) && !navLinks.contains(e.target)) navLinks.classList.remove('open');
    });
  }

  /* Scroll Reveal */
  var reveals = document.querySelectorAll('.reveal');
  if (reveals.length) {
    var obs = new IntersectionObserver(function(entries) {
      entries.forEach(function(e) { if (e.isIntersecting) { e.target.classList.add('visible'); obs.unobserve(e.target); } });
    }, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });
    reveals.forEach(function(el) { obs.observe(el); });
  }

  /* Counter Animation */
  document.querySelectorAll('[data-count]').forEach(function(el) {
    var target = parseFloat(el.getAttribute('data-count'));
    var suffix = el.getAttribute('data-suffix') || '';
    var prefix = el.getAttribute('data-prefix') || '';
    var dec = target % 1 !== 0 ? 1 : 0;
    var cObs = new IntersectionObserver(function(entries) {
      entries.forEach(function(e) {
        if (e.isIntersecting) {
          var start = 0, dur = 2000, t0 = null;
          function step(ts) {
            if (!t0) t0 = ts;
            var p = Math.min((ts - t0) / dur, 1);
            var v = start + (target - start) * (1 - Math.pow(1 - p, 3));
            el.textContent = prefix + v.toFixed(dec).replace(/\B(?=(\d{3})+(?!\d))/g, ',') + suffix;
            if (p < 1) requestAnimationFrame(step);
          }
          requestAnimationFrame(step);
          cObs.unobserve(el);
        }
      });
    }, { threshold: 0.5 });
    cObs.observe(el);
  });

  /* Smooth Scroll */
  document.querySelectorAll('a[href^="#"]').forEach(function(a) {
    a.addEventListener('click', function(e) {
      var t = document.querySelector(this.getAttribute('href'));
      if (t) { e.preventDefault(); t.scrollIntoView({ behavior: 'smooth' }); if (navLinks) navLinks.classList.remove('open'); }
    });
  });

  /* Molecular Docking Demo */
  var dockingForm = document.getElementById('docking-form');
  var dockingResult = document.getElementById('docking-result');
  if (dockingForm && dockingResult) {
    dockingForm.addEventListener('submit', function(e) {
      e.preventDefault();
      var molecule = document.getElementById('molecule-input').value.trim();
      var target = document.getElementById('target-select').value;
      if (!molecule) return;

      dockingResult.classList.add('show');
      dockingResult.innerHTML = '<div style="text-align:center;padding:2rem"><div class="animate-pulse" style="color:var(--accent)">Computing molecular docking...</div></div>';

      setTimeout(function() {
        var score = (Math.random() * -8 - 4).toFixed(2);
        var ic50 = (Math.random() * 500 + 10).toFixed(1);
        var admet = {
          absorption: ['High','Medium','Low'][Math.floor(Math.random()*3)],
          toxicity: ['Low','Medium'][Math.floor(Math.random()*2)],
          solubility: (Math.random() * 5 + 1).toFixed(1),
          halfLife: (Math.random() * 20 + 2).toFixed(1)
        };
        var html = '<h3>Docking Results: ' + molecule + '</h3>';
        html += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin:1rem 0">';
        html += '<div class="stat-card"><div class="stat-number">' + score + '</div><div class="stat-label">Binding Affinity (kcal/mol)</div></div>';
        html += '<div class="stat-card"><div class="stat-number">' + ic50 + '</div><div class="stat-label">IC50 (nM)</div></div>';
        html += '<div class="stat-card"><div class="stat-number">' + admet.absorption + '</div><div class="stat-label">Absorption</div></div>';
        html += '<div class="stat-card"><div class="stat-number">' + admet.toxicity + '</div><div class="stat-label">Toxicity Risk</div></div>';
        html += '</div>';
        html += '<div style="margin-top:1rem">';
        html += '<p style="font-size:0.85rem;color:var(--text-dim)"><strong>Target:</strong> ' + target + '</p>';
        html += '<p style="font-size:0.85rem;color:var(--text-dim)"><strong>Solubility:</strong> ' + admet.solubility + ' logS</p>';
        html += '<p style="font-size:0.85rem;color:var(--text-dim)"><strong>Half-life:</strong> ' + admet.halfLife + ' hours</p>';
        html += '</div>';
        html += '<p style="margin-top:1rem;font-size:0.8rem;color:var(--text-dim)">Note: This is a demo simulation. Real molecular docking requires computational chemistry tools.</p>';
        dockingResult.innerHTML = html;
      }, 2000);
    });
  }

  /* FAQ Accordion */
  document.querySelectorAll('.faq-q').forEach(function(q) {
    q.addEventListener('click', function() {
      var a = this.nextElementSibling;
      var open = a.style.maxHeight;
      document.querySelectorAll('.faq-a').forEach(function(x) { x.style.maxHeight = null; });
      if (!open) a.style.maxHeight = a.scrollHeight + 'px';
    });
  });

  /* Copy Code */
  document.querySelectorAll('.copy-btn').forEach(function(btn) {
    btn.addEventListener('click', function() {
      var code = this.closest('.code-block').querySelector('code').textContent;
      navigator.clipboard.writeText(code).then(function() { btn.textContent = 'Copied!'; setTimeout(function() { btn.textContent = 'Copy'; }, 2000); });
    });
  });
})();
