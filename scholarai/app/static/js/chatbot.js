/* ============================================================
   ScholarAI — Chatbot AJAX handler
   Works for both admin (/admin/chatbot/send)
   and student (/student/chatbot/send)
   ============================================================ */
document.addEventListener('DOMContentLoaded', function () {
  const input    = document.getElementById('chatInput');
  const sendBtn  = document.getElementById('chatSend');
  const messages = document.getElementById('chatMessages');
  if (!input || !messages) return;

  const role    = typeof CHAT_ROLE !== 'undefined' ? CHAT_ROLE : 'admin';
  const apiUrl  = typeof CHAT_API  !== 'undefined' ? CHAT_API  : '';

  function appendMsg(text, sender) {
    const d = document.createElement('div');
    d.className = `chat-msg ${sender}${sender === 'user' && role === 'student' ? ' student' : ''}`;
    if (sender === 'bot') {
      d.innerHTML = `<div class="chat-msg__avatar ${role}">${role === 'admin' ? 'AI' : 'AI'}</div>
                     <div class="chat-msg__bubble">${text.replace(/\n/g, '<br>')}</div>`;
    } else {
      d.innerHTML = `<div class="chat-msg__bubble">${text}</div>`;
    }
    messages.appendChild(d);
    messages.scrollTop = messages.scrollHeight;
  }

  function showTyping() {
    const d = document.createElement('div');
    d.className = `chat-msg bot`;
    d.id = 'typing-indicator';
    d.innerHTML = `<div class="chat-msg__avatar ${role}">AI</div>
                   <div class="chat-msg__bubble" style="color:var(--text-lt);font-style:italic;">Thinking...</div>`;
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
    try {
      const res  = await fetch(apiUrl, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ message: text })
      });
      const data = await res.json();
      removeTyping();
      appendMsg(data.reply || 'Sorry, I could not process that request.', 'bot');
    } catch (err) {
      removeTyping();
      appendMsg('Connection error. Please try again.', 'bot');
    }
  }

  sendBtn.addEventListener('click', sendMessage);
  input.addEventListener('keydown', e => { if (e.key === 'Enter') sendMessage(); });

  // Quick prompt chips
  document.querySelectorAll('.chat-prompt-item').forEach(chip => {
    chip.addEventListener('click', function () {
      input.value = this.textContent.trim();
      input.focus();
    });
  });
});
