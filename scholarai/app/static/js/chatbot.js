/* ============================================================
   ScholarAI — Chatbot AJAX handler
   Works for both admin (/admin/chatbot/send)
   and student (/student/chatbot/send)
   ============================================================ */
document.addEventListener('DOMContentLoaded', function () {
  const input = document.getElementById('chatInput');
  const sendBtn = document.getElementById('chatSend');
  const messages = document.getElementById('chatMessages');
  if (!input || !sendBtn || !messages) return;

  const role = typeof CHAT_ROLE !== 'undefined' ? CHAT_ROLE : 'admin';
  const apiUrl = typeof CHAT_API !== 'undefined' ? CHAT_API : '';
  function formatBotText(text) {
    let safeText = String(text || '').replace(/[&<>'"]/g, tag => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
    }[tag] || tag));

    // Bold
    safeText = safeText.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Markdown Links [Text](URL)
    safeText = safeText.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" style="color:var(--blue);text-decoration:underline;font-weight:600;">$1</a>');
    
    // Raw URLs (only if not already part of an anchor tag)
    safeText = safeText.replace(/(^|[^="'>])(https?:\/\/[^\s<()]+)/g, '$1<a href="$2" target="_blank" style="color:var(--blue);text-decoration:underline;font-weight:600;">$2</a>');

    // Newlines
    safeText = safeText.replace(/\n/g, '<br>');
    return safeText;
  }

  function appendMsg(text, sender) {
    const d = document.createElement('div');
    d.className = `chat-msg ${sender}${sender === 'user' && role === 'student' ? ' student' : ''}`;

    if (sender === 'bot') {
      d.innerHTML = `
        <div class="chat-msg__avatar ${role}">AI</div>
        <div class="chat-msg__bubble">${formatBotText(text)}</div>
      `;
    } else {
      const safeText = String(text || '').replace(/[&<>'"]/g, tag => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
      }[tag] || tag)).replace(/\n/g, '<br>');
      d.innerHTML = `
        <div class="chat-msg__bubble">${safeText}</div>
      `;
    }

    messages.appendChild(d);
    messages.scrollTop = messages.scrollHeight;
  }

  // Scroll to bottom immediately on load if backend supplied history
  if (messages.children.length > 2) { // more than just the greeting
    messages.scrollTop = messages.scrollHeight;
  }

  function showTyping() {
    const d = document.createElement('div');
    d.className = 'chat-msg bot';
    d.id = 'typing-indicator';
    d.innerHTML = `
      <div class="chat-msg__avatar ${role}">AI</div>
      <div class="chat-msg__bubble" style="color:var(--text-lt);font-style:italic;">Thinking...</div>
    `;
    messages.appendChild(d);
    messages.scrollTop = messages.scrollHeight;
  }

  function removeTyping() {
    const t = document.getElementById('typing-indicator');
    if (t) t.remove();
  }

  async function sendMessage() {
    const text = input.value.trim();
    if (!text || !apiUrl) return;

    appendMsg(text, 'user');
    input.value = '';
    showTyping();
    sendBtn.disabled = true;

    try {
      const res = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          message: text
        })
      });

      const data = await res.json();
      removeTyping();

      if (!res.ok) {
        appendMsg(data.detail || data.error || 'Sorry, I could not process that request.', 'bot');
        return;
      }

      appendMsg(data.reply || 'Sorry, I could not process that request.', 'bot');
    } catch (err) {
      removeTyping();
      appendMsg('Connection error. Please try again.', 'bot');
      console.error('Chat error:', err);
    } finally {
      sendBtn.disabled = false;
    }
  }

  sendBtn.addEventListener('click', sendMessage);
  input.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') sendMessage();
  });

  document.querySelectorAll('.chat-prompt-item').forEach(chip => {
    chip.addEventListener('click', function () {
      input.value = this.textContent.trim();
      input.focus();
    });
  });
});