/* ============================================================
   ScholarAI — Shared JavaScript
   ============================================================ */

/* ── ACTIVE NAV LINK ── */
document.addEventListener('DOMContentLoaded', function () {
  const current = window.location.pathname.split('/').pop();
  document.querySelectorAll('.topnav__link').forEach(link => {
    if (link.dataset.page === current) link.classList.add('active');
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
      this.textContent = 'APPLIED ✓';
      setTimeout(() => { this.textContent = 'APPLY'; }, 1500);
    });
  }

  /* ── EMAIL TEMPLATE AUTOFILL ── */
  const templateSelect = document.getElementById('emailTemplate');
  const emailSubject = document.getElementById('emailSubject');
  const emailBody = document.getElementById('emailBody');
  if (templateSelect) {
    templateSelect.addEventListener('change', function () {
      const templates = {
        'High Risk Warning': {
          subject: 'URGENT: Academic Performance Concern — Student Review Required',
          body: 'Dear Parent/Guardian,\n\nWe wish to urgently bring to your attention that your ward has been flagged as HIGH RISK based on our AI-powered performance prediction system.\n\nCurrent Performance Index: 72%\nRisk Level: HIGH\nOutstanding Dues: ₹4,500\n\nWe strongly recommend scheduling a meeting with the class teacher at your earliest convenience.\n\nRegards,\nSchool Administration — ScholarAI System'
        },
        'Attendance Alert': {
          subject: 'Attendance Below Threshold — Immediate Action Required',
          body: 'Dear Parent/Guardian,\n\nThis is to inform you that your ward\'s attendance has fallen below the required 75% threshold.\n\nCurrent Attendance: 68%\nMinimum Required: 75%\n\nPlease ensure regular attendance to avoid academic penalties.\n\nRegards,\nSchool Administration'
        },
        'Fee Dues Reminder': {
          subject: 'Reminder: Outstanding Fee Dues — Action Required',
          body: 'Dear Parent/Guardian,\n\nThis is a reminder regarding outstanding fee dues of ₹4,500 which remain unpaid.\n\nPlease clear the dues at the earliest to avoid any disruption to your ward\'s academic progress.\n\nRegards,\nAccounts Department — ScholarAI'
        },
        'Performance Improvement Notice': {
          subject: 'Performance Improvement Plan — Student Progress Review',
          body: 'Dear Parent/Guardian,\n\nWe have prepared a personalised Performance Improvement Plan for your ward based on recent AI-generated predictions.\n\nKey Focus Areas:\n- Mathematics (Predicted: 62%)\n- History (Predicted: 50%)\n\nWe recommend additional tutoring sessions and increased attendance.\n\nRegards,\nAcademic Counselling Team'
        },
        'Parent Meeting Request': {
          subject: 'Request for Parent-Teacher Meeting',
          body: 'Dear Parent/Guardian,\n\nWe would like to invite you for a parent-teacher meeting to discuss your ward\'s academic progress and risk assessment.\n\nPlease contact the school office to schedule a convenient time.\n\nRegards,\nClass Teacher'
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

  /* ── SEND EMAIL BUTTON ── */
  const sendEmailBtn = document.getElementById('sendEmailBtn');
  if (sendEmailBtn) {
    sendEmailBtn.addEventListener('click', function () {
      this.textContent = '⏳ SENDING...';
      this.disabled = true;
      setTimeout(() => {
        this.textContent = '✓ EMAIL SENT';
        this.style.background = 'var(--green)';
        setTimeout(() => {
          this.textContent = 'SEND EMAIL →';
          this.style.background = '';
          this.disabled = false;
        }, 2500);
      }, 1200);
    });
  }

  /* ── BULK EMAIL BUTTON ── */
  const bulkEmailBtn = document.getElementById('bulkEmailBtn');
  if (bulkEmailBtn) {
    bulkEmailBtn.addEventListener('click', function () {
      if (confirm('Send warning emails to all 12 HIGH RISK students and their guardians?')) {
        this.textContent = '⏳ SENDING TO 12 STUDENTS...';
        this.disabled = true;
        setTimeout(() => {
          this.textContent = '✓ 12 EMAILS SENT';
          this.style.background = 'var(--green)';
          setTimeout(() => {
            this.textContent = '📧 BULK EMAIL HIGH RISK';
            this.style.background = '';
            this.disabled = false;
          }, 3000);
        }, 2000);
      }
    });
  }

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
});
