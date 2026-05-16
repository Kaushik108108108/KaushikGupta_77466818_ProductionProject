// This script handles the chatbot logic for both administrators and students.
// It manages sending messages, showing the typing indicator, and formatting the AI's responses.
document.addEventListener('DOMContentLoaded', function () {
  // We start by finding the input field, the send button, and the message container on the page.
  const input = document.getElementById('chatInput');
  const sendBtn = document.getElementById('chatSend');
  const messages = document.getElementById('chatMessages');
  if (!input || !sendBtn || !messages) return;

  // We determine if the user is an admin or a student to style the chat correctly.
  const role = typeof CHAT_ROLE !== 'undefined' ? CHAT_ROLE : 'admin';
  const apiUrl = typeof CHAT_API !== 'undefined' ? CHAT_API : '';

  // This function cleans up the AI's response and formats things like bold text and links.
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

  // This function adds a new message to the chat window.
  function appendMsg(text, sender) {
    const d = document.createElement('div');
    // We apply different styles depending on whether the user or the bot sent the message.
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

    // After adding a message, we automatically scroll to the bottom so the user sees the latest text.
    messages.appendChild(d);
    messages.scrollTop = messages.scrollHeight;
  }

  // If the page loads with previous messages, we make sure it's scrolled to the bottom.
  if (messages.children.length > 2) {
    messages.scrollTop = messages.scrollHeight;
  }

  // This shows a "Thinking..." message while we wait for the AI to respond.
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

  // This removes the "Thinking..." message once the actual response arrives.
  function removeTyping() {
    const t = document.getElementById('typing-indicator');
    if (t) t.remove();
  }

  // This is the core function that sends the user's message to the server.
  async function sendMessage() {
    const text = input.value.trim();
    // We don't send anything if the input is empty.
    if (!text || !apiUrl) return;

    // Show the user's message immediately and start the loading state.
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
      // Whether it succeeded or failed, we re-enable the send button.
      sendBtn.disabled = false;
    }
  }

  // We listen for clicks on the send button or when the user presses the Enter key.
  sendBtn.addEventListener('click', sendMessage);
  input.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') sendMessage();
  });

  // If the user clicks on one of the suggested questions, we fill the input field for them.
  document.querySelectorAll('.chat-prompt-item').forEach(chip => {
    chip.addEventListener('click', function () {
      input.value = this.textContent.trim();
      input.focus();
    });
  });
});