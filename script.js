const chatSection = document.getElementById('chatSection');
const messagesDiv = document.getElementById('messages');
const placeholder = document.getElementById('placeholder');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const themeToggle = document.getElementById('themeToggle');

let chatHistory = [];

async function sendMessage() {
    const text = userInput.value.trim();
    if (!text) return;

    if (placeholder) placeholder.remove();

    appendMessage('me', text);
    userInput.value = '';

    const response = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, history: chatHistory })
    });

    const data = await response.json();
    appendMessage('anne', data.reply);

    chatHistory.push({ role: 'user', content: text });
    chatHistory.push({ role: 'assistant', content: data.reply });
}

function appendMessage(sender, text) {
    const wrapper = document.createElement('div');
    wrapper.className = `message-wrapper ${sender}`;
    
    wrapper.innerHTML = `
        <div class="bubble">${text}</div>
        <button class="copy-btn" onclick="copyText(this, '${text.replace(/'/g, "\\'")}')">copy</button>
    `;
    
    messagesDiv.appendChild(wrapper);
    chatSection.scrollTo({ top: chatSection.scrollHeight, behavior: 'smooth' });
}

function copyText(btn, text) {
    navigator.clipboard.writeText(text);
    btn.innerText = 'copied!';
    setTimeout(() => btn.innerText = 'copy', 2000);
}

// UI Controls
document.getElementById('menuBtn').onclick = () => document.getElementById('dropdownMenu').classList.toggle('hidden');
document.getElementById('refreshBtn').onclick = () => location.reload();

themeToggle.onclick = () => {
    const isDark = document.body.classList.toggle('dark-theme');
    document.body.classList.toggle('light-theme');
    themeToggle.innerText = isDark ? 'Light Mode' : 'Dark Mode';
};

sendBtn.onclick = sendMessage;
userInput.onkeypress = (e) => { if(e.key === 'Enter') sendMessage(); };

