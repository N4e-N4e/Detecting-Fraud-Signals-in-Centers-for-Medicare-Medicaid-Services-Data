const CHAT_ENDPOINT = 'https://backend-site-lifv.onrender.com/chat';
const chatWindow = document.getElementById('chat-window');
const chatInput = document.getElementById('chat-input');
const chatSend = document.getElementById('chat-send');
if (chatWindow && chatInput && chatSend) {
  function appendMessage(role, text) {
    const wrapper = document.createElement('div');
    wrapper.classList.add('msg');
    wrapper.classList.add(role === 'user' ? 'user' : 'assistant');

    const avatar = document.createElement('div');
    avatar.classList.add('msg-avatar');
    avatar.innerHTML = role === 'user' ? 'You' : '<svg viewBox="0 0 24 24"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>';

    const content = document.createElement('div');
    content.classList.add('msg-content');

    const label = document.createElement('div');
    label.classList.add('msg-label');
    label.textContent = role === 'user' ? 'You' : 'DEMIrobato';

    const body = document.createElement('div');
    body.classList.add('msg-body');
    body.innerHTML = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/^#{1,3} (.+)$/gm, '<strong>$1</strong>')
      .replace(/^\s*[-•]\s+(.+)$/gm, '&bull; $1<br>')
      .replace(/^\d+\.\s+(.+)$/gm, (m, p1) => `${m.match(/^\d+/)[0]}. ${p1}<br>`)
      .replace(/\n\n/g, '<br><br>')
      .replace(/\n/g, '<br>')
      .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" style="color:#38bdf8;">$1</a>')
      .replace(/(?<!href=")(https?:\/\/[^\s<]+?)([).,'";]*(?:\s|$))/g, '<a href="$1" target="_blank" rel="noopener noreferrer" style="color:#38bdf8;">$1</a>$2');

    content.appendChild(label);
    content.appendChild(body);
    wrapper.appendChild(avatar);
    wrapper.appendChild(content);
    chatWindow.appendChild(wrapper);
    chatWindow.scrollTop = chatWindow.scrollHeight;
    return wrapper;
  }
  appendMessage('assistant', 'Hello! I\'m DEMIrobato. How can I help you today?');
  async function sendMessage() {
    const prompt = chatInput.value.trim();
    if (!prompt) return;
    appendMessage('user', prompt);
    chatInput.value = '';
    const loadingNode = appendMessage('assistant', 'typing...');
    try {
      const response = await fetch(CHAT_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: prompt })
      });
      const data = await response.json();
      loadingNode.remove();
      if (data.reply) {
        appendMessage('assistant', data.reply);
      } else if (data.error) {
        appendMessage('assistant', `Error: ${data.error}`);
      } else {
        appendMessage('assistant', 'No response returned by the backend.');
      }
    } catch (error) {
      console.error(error);
      loadingNode.remove();
      appendMessage('assistant', 'Error fetching results from the backend.');
    }
  }
  chatSend.addEventListener('click', sendMessage);
  chatInput.addEventListener('keypress', (event) => {
    if (event.key === 'Enter') sendMessage();
  });
}
