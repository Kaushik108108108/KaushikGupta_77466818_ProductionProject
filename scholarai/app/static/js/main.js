/* ============================================================
   ScholarAI — Shared JavaScript
   ============================================================ */

/* ── THEME INITIALIZATION (Runs immediately) ── */
(function() {
  const savedTheme = localStorage.getItem('scholarai_theme') || 'light';
  if (savedTheme === 'dark') {
    document.documentElement.setAttribute('data-theme', 'dark');
  }
})();

/* ── ACTIVE NAV LINK ── */
document.addEventListener('DOMContentLoaded', function () {
  const current = window.location.pathname.split('/').pop();
  document.querySelectorAll('.topnav__link').forEach(link => {
    if (link.dataset.page === current) link.classList.add('active');
  });

  /* ── THEME TOGGLER ── */
  const themeToggleBtn = document.getElementById('themeToggleBtn');
  if (themeToggleBtn) {
    // We use simple text instead of icons for the theme toggle to keep the interface clean.
    const lightText = 'LIGHT';
    const darkText  = 'DARK';
    
    // Set the initial label based on the current theme.
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
    themeToggleBtn.innerHTML = currentTheme === 'dark' ? lightText : darkText;

    themeToggleBtn.addEventListener('click', function() {
      let activeTheme = document.documentElement.getAttribute('data-theme') || 'light';
      let newTheme = activeTheme === 'light' ? 'dark' : 'light';
      
      document.documentElement.setAttribute('data-theme', newTheme);
      localStorage.setItem('scholarai_theme', newTheme);
      
      // Update the button text to match the new theme.
      this.innerHTML = newTheme === 'dark' ? lightText : darkText;
    });
  }

  /* ── AUTO DISMISS ALERTS ── */
  document.querySelectorAll('.alert').forEach(alert => {
    setTimeout(() => {
      alert.style.transition = 'opacity 0.5s ease';
      alert.style.opacity = '0';
      setTimeout(() => alert.remove(), 500);
    }, 3000);
  });

  /* ── CHAT FUNCTIONALITY ── */
  const chatInput = document.getElementById('chatInput');
  const chatMessages = document.getElementById('chatMessages');
  const chatSendBtn = document.getElementById('chatSend');

  // Chat functionality is handled by chatbot.js (loaded separately per page)

  /* ── FILTER SELECTS ── */
  const applyBtn = document.getElementById('applyFilter');
  if (applyBtn) {
    applyBtn.addEventListener('click', function () {
      // We briefly update the button text to confirm that the filters have been applied.
      this.textContent = 'APPLIED';
      setTimeout(() => { this.textContent = 'APPLY'; }, 1500);
    });
  }

  /* ── EMAIL TEMPLATE AUTOFILL ── */
  const templateSelect = document.getElementById('emailTemplate');
  const emailSubject = document.getElementById('emailSubject');
  const emailBody = document.getElementById('emailBody');
  if (templateSelect) {
    templateSelect.addEventListener('change', function () {
      const sd = window.studentData || {
        full_name: 'Student',
        risk_level: 'HIGH',
        performance_index: 0,
        due_amount: 0,
        attendance_rate: 0
      };

      const templates = {
        'High Risk Warning': {
          subject: `URGENT: Academic Performance Concern — ${sd.full_name}`,
          body: `Dear Parent/Guardian,\n\nWe wish to urgently bring to your attention that your ward, ${sd.full_name}, has been flagged as ${sd.risk_level} RISK based on our AI-powered performance prediction system.\n\nCurrent Performance Index: ${sd.performance_index}%\nRisk Level: ${sd.risk_level}\nOutstanding Dues: Rs. ${sd.due_amount.toLocaleString()}\n\nWe strongly recommend scheduling a meeting with the class teacher at your earliest convenience.\n\nRegards,\nSchool Administration — ScholarAI System`
        },
        'Attendance Alert': {
          subject: `Attendance Below Threshold — ${sd.full_name}`,
          body: `Dear Parent/Guardian,\n\nThis is to inform you that your ward's attendance has fallen to ${sd.attendance_rate}%, which is below the required 75% threshold.\n\nPlease ensure ${sd.full_name} attends classes regularly to avoid academic penalties.\n\nRegards,\nSchool Administration`
        },
        'Fee Dues Reminder': {
          subject: `Reminder: Outstanding Fee Dues of Rs. ${sd.due_amount.toLocaleString()} — ${sd.full_name}`,
          body: `Dear Parent/Guardian,\n\nThis is a reminder regarding outstanding fee dues of Rs. ${sd.due_amount.toLocaleString()} for your ward ${sd.full_name}.\n\nPlease clear the dues at the earliest to avoid any disruption to academic progress.\n\nRegards,\nAccounts Department — ScholarAI`
        },
        'Performance Improvement Notice': {
          subject: `Performance Improvement Plan — ${sd.full_name}`,
          body: `Dear Parent/Guardian,\n\nWe have prepared a personalised Performance Improvement Plan for your ward ${sd.full_name} based on recent AI-generated predictions (Current Index: ${sd.performance_index}%).\n\nWe recommend additional tutoring sessions and increased attendance to help improve these results.\n\nRegards,\nAcademic Counselling Team`
        },
        'Parent Meeting Request': {
          subject: `Request for Parent-Teacher Meeting — ${sd.full_name}`,
          body: `Dear Parent/Guardian,\n\nWe would like to invite you for a parent-teacher meeting to discuss your ward ${sd.full_name}'s academic progress and risk assessment.\n\nPlease contact the school office to schedule a convenient time.\n\nRegards,\nClass Teacher`
        }
      };
      const t = templates[this.value];
      if (t) {
        if (emailSubject) emailSubject.value = t.subject;
        if (emailBody) emailBody.value = t.body;
      }
    });
  }

  /* ── PREDICT BUTTON ANIMATION ── */
  const predictBtn = document.getElementById('predictBtn');
  if (predictBtn) {
    predictBtn.addEventListener('click', function () {
      this.textContent = '⏳ PREDICTING...';
      this.disabled = true;
      setTimeout(() => {
        this.textContent = '✓ PREDICTION COMPLETE';
        document.getElementById('resultSection') && (document.getElementById('resultSection').style.display = 'block');
        setTimeout(() => {
          this.textContent = '🔮 PREDICT PERFORMANCE →';
          this.disabled = false;
        }, 3000);
      }, 1500);
    });
  }

  /* ── SEND EMAIL BUTTON (Loading State Only) ── */
  // Handled by AJAX logic in send_email.html to prevent page reload conflits

  /* ── BULK EMAIL BUTTON ── */
  // Handled dynamically by dashboard.html inline script which uses
  // the live high-risk count from the DB and calls /admin/bulk-email-high-risk

  /* ── HIGHLIGHT ROW on Details click ── */
  document.querySelectorAll('.view-details-btn').forEach(btn => {
    btn.addEventListener('click', function () {
      const row = this.closest('tr');
      if (row) {
        row.style.outline = '2px solid var(--blue)';
        setTimeout(() => window.location.href = this.dataset.href || 'admin-student-details.html', 300);
      }
    });
  });

  /* ── RESPONSIVE MOBILE MENU ── */
  const menuToggle = document.querySelector('.topnav__toggle');
  const menuLinks = document.querySelector('.topnav__links');
  if (menuToggle && menuLinks) {
    menuToggle.addEventListener('click', function() {
      menuLinks.classList.toggle('active');
    });
  }
});
