/* ── Roast & Co. Streaming Chat Controller ────────────────────────── */

let currentChatId = null;
let isSending = false;

window.quickPrompt = function(promptText) {
    if (isSending) return;
    const input = document.getElementById('messageInput');
    if (input) {
        input.value = promptText;
        input.focus();
        const sendBtn = document.getElementById('sendBtn');
        if (sendBtn) sendBtn.click();
    }
};

document.addEventListener('DOMContentLoaded', () => {
    const chatSidebar        = document.getElementById('chatSidebar');
    const toggleSidebarBtn   = document.getElementById('toggleSidebarBtn');
    const chatList           = document.getElementById('chatList');
    const messagesArea       = document.getElementById('messagesArea');
    const messageInput       = document.getElementById('messageInput');
    const sendBtn            = document.getElementById('sendBtn');
    const typingContainer    = document.getElementById('typingIndicatorContainer');
    const newChatBtn         = document.getElementById('newChatBtn');
    const activeChatTitle    = document.getElementById('activeChatTitle');

    // ── Sidebar Toggle Functionality ──
    if (toggleSidebarBtn && chatSidebar) {
        const isCollapsed = localStorage.getItem('roastco_sidebar_collapsed') === 'true';
        if (isCollapsed) {
            chatSidebar.classList.add('collapsed');
        }

        toggleSidebarBtn.addEventListener('click', () => {
            chatSidebar.classList.toggle('collapsed');
            const collapsed = chatSidebar.classList.contains('collapsed');
            localStorage.setItem('roastco_sidebar_collapsed', collapsed ? 'true' : 'false');
        });
    }

    // ── Auto-resize Textarea ──
    if (messageInput) {
        messageInput.addEventListener('input', () => {
            messageInput.style.height = 'auto';
            messageInput.style.height = Math.min(messageInput.scrollHeight, 120) + 'px';
        });
    }

    // ── Event Listeners ──
    if (newChatBtn) newChatBtn.addEventListener('click', createNewChat);
    if (sendBtn) sendBtn.addEventListener('click', sendMessage);

    if (messageInput) {
        messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }

    // Delegate sidebar clicks
    if (chatList) {
        chatList.addEventListener('click', (e) => {
            const deleteBtn = e.target.closest('.chat-item-delete');
            if (deleteBtn) {
                e.stopPropagation();
                deleteChat(deleteBtn.dataset.chatId, e);
                return;
            }
            const chatItem = e.target.closest('.chat-item');
            if (chatItem) loadChat(chatItem.dataset.chatId);
        });

        // Auto-load first chat if available
        const firstItem = chatList.querySelector('.chat-item');
        if (firstItem) loadChat(firstItem.dataset.chatId);
    }

    // ── Message Formatting ──
    function formatMarkdown(text) {
        if (!text) return '';
        
        let formatted = text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');

        // Inline code `code`
        formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');

        // Bold **text**
        formatted = formatted.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

        // Headers ### Heading
        formatted = formatted.replace(/^### (.*$)/gim, '<h4 style="margin: 0.6rem 0 0.25rem 0; font-family: var(--font-heading);">$1</h4>');
        formatted = formatted.replace(/^## (.*$)/gim, '<h3 style="margin: 0.8rem 0 0.35rem 0; font-family: var(--font-heading);">$1</h3>');

        // Italics *text* or _text_
        formatted = formatted.replace(/(^|[^\*])\*([^*]+)\*([^\*]|$)/g, '$1<em>$2</em>$3');

        // Bullet lists
        formatted = formatted.replace(/^\s*[-*•]\s+(.*)$/gm, '<li>$1</li>');

        // Paragraph line breaks
        formatted = formatted.replace(/\n\n+/g, '<br><br>');
        formatted = formatted.replace(/\n/g, '<br>');

        return formatted;
    }

    function appendMessage(role, content) {
        const emptyState = document.getElementById('emptyState');
        if (emptyState) emptyState.remove();

        const div = document.createElement('div');
        div.className = 'message ' + role;

        if (role === 'assistant') {
            div.innerHTML = formatMarkdown(content);
        } else {
            div.textContent = content;
        }

        messagesArea.appendChild(div);
        scrollToBottom();
        return div;
    }

    function scrollToBottom() {
        if (messagesArea) {
            messagesArea.scrollTop = messagesArea.scrollHeight;
        }
    }

    function setActiveChat(id, title = null) {
        currentChatId = id;
        chatList.querySelectorAll('.chat-item').forEach(el => {
            const isActive = el.dataset.chatId == id;
            el.classList.toggle('active', isActive);
            if (isActive && !title) {
                const titleSpan = el.querySelector('.chat-item-title');
                if (titleSpan && activeChatTitle) activeChatTitle.textContent = titleSpan.textContent;
            }
        });
        if (title && activeChatTitle) {
            activeChatTitle.textContent = title;
        }
    }

    // ── API Operations ──
    async function createNewChat() {
        if (isSending) return;
        try {
            const res = await fetch('/chat/new', { method: 'POST' });
            if (!res.ok) throw new Error('Failed to create chat');
            const data = await res.json();

            const placeholder = chatList.querySelector('.sidebar-empty');
            if (placeholder) placeholder.remove();

            const div = document.createElement('div');
            div.className = 'chat-item active';
            div.dataset.chatId = data.id;
            div.innerHTML = `
                <div class="chat-item-content">
                    <span class="chat-item-title" title="${data.title}">${data.title}</span>
                    <span class="chat-item-time">Just now</span>
                </div>
                <button class="chat-item-delete" data-chat-id="${data.id}" title="Delete conversation" aria-label="Delete chat">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                </button>
            `;
            chatList.prepend(div);

            setActiveChat(data.id, data.title);
            messagesArea.innerHTML = `
                <div class="chat-empty-state" id="emptyState">
                    <div class="empty-state-card">
                        <h2>New Conversation</h2>
                        <p>Ask anything about our single-origin coffees, shipping policies, brewing guides, or place and track an order.</p>
                    </div>
                </div>
            `;
            messageInput.disabled = false;
            sendBtn.disabled = false;
            messageInput.value = '';
            messageInput.focus();
        } catch (err) {
            console.error(err);
            alert('Could not create a new chat.');
        }
    }

    async function loadChat(chatId) {
        if (isSending) return;
        if (currentChatId == chatId && messagesArea.children.length > 0) return;
        setActiveChat(chatId);

        try {
            const res = await fetch(`/chat/${chatId}/messages`);
            if (!res.ok) throw new Error('Failed to load messages');
            const messages = await res.json();

            messagesArea.innerHTML = '';
            if (messages.length === 0) {
                messagesArea.innerHTML = `
                    <div class="chat-empty-state" id="emptyState">
                        <div class="empty-state-card">
                            <h2>Roast &amp; Co. Concierge</h2>
                            <p>How can we assist you with freshly roasted coffee today?</p>
                        </div>
                    </div>
                `;
            } else {
                messages.forEach(m => {
                    if (m.role === 'user' || m.role === 'assistant') {
                        appendMessage(m.role, m.content);
                    }
                });
            }

            messageInput.disabled = false;
            sendBtn.disabled = false;
            scrollToBottom();
        } catch (err) {
            console.error(err);
            messagesArea.innerHTML = '<div class="message assistant">Failed to load conversation history.</div>';
        }
    }

    // ── Streaming Send Message ──
    async function sendMessage() {
        if (isSending) return;
        
        if (!currentChatId) {
            await createNewChat();
        }
        const text = messageInput.value.trim();
        if (!text) return;

        isSending = true;
        appendMessage('user', text);
        messageInput.value = '';
        messageInput.style.height = 'auto';
        sendBtn.disabled = true;
        messageInput.disabled = true;
        
        if (typingContainer) typingContainer.style.display = 'block';
        scrollToBottom();

        // Create the assistant bubble placeholder
        let assistantBubble = null;
        let accumulatedText = '';

        try {
            const res = await fetch(`/chat/${currentChatId}/message`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text }),
            });

            if (!res.ok) throw new Error('Network error sending message');

            const reader = res.body.getReader();
            const decoder = new TextDecoder('utf-8');
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop(); // keep last incomplete line

                for (const line of lines) {
                    const trimmed = line.trim();
                    if (!trimmed.startsWith('data: ')) continue;
                    
                    try {
                        const jsonPayload = JSON.parse(trimmed.slice(6));
                        
                        if (jsonPayload.chunk) {
                            if (typingContainer) typingContainer.style.display = 'none';
                            
                            if (!assistantBubble) {
                                assistantBubble = appendMessage('assistant', '');
                            }
                            
                            accumulatedText += jsonPayload.chunk;
                            assistantBubble.innerHTML = formatMarkdown(accumulatedText);
                            scrollToBottom();
                        }

                        if (jsonPayload.done && jsonPayload.chat_title) {
                            const titleEl = chatList.querySelector(
                                `.chat-item[data-chat-id="${currentChatId}"] .chat-item-title`
                            );
                            if (titleEl) titleEl.textContent = jsonPayload.chat_title;
                            if (activeChatTitle) activeChatTitle.textContent = jsonPayload.chat_title;
                        }
                    } catch (parseErr) {
                        console.warn('Failed to parse SSE line:', line);
                    }
                }
            }

            if (typingContainer) typingContainer.style.display = 'none';

        } catch (err) {
            console.error('Streaming error:', err);
            if (typingContainer) typingContainer.style.display = 'none';
            if (!assistantBubble) {
                appendMessage('assistant', 'I encountered an error processing your request. Please try again in a moment.');
            }
        } finally {
            isSending = false;
            sendBtn.disabled = false;
            messageInput.disabled = false;
            messageInput.focus();
            scrollToBottom();
        }
    }

    async function deleteChat(chatId, event) {
        if (isSending) return;
        if (!confirm('Are you sure you want to delete this conversation?')) return;

        try {
            const res = await fetch(`/chat/${chatId}`, { method: 'DELETE' });
            if (!res.ok) throw new Error('Failed to delete chat');

            const item = chatList.querySelector(`.chat-item[data-chat-id="${chatId}"]`);
            if (item) item.remove();

            if (currentChatId == chatId) {
                currentChatId = null;
                const nextItem = chatList.querySelector('.chat-item');
                if (nextItem) {
                    loadChat(nextItem.dataset.chatId);
                } else {
                    messagesArea.innerHTML = `
                        <div class="chat-empty-state" id="emptyState">
                            <div class="empty-state-card">
                                <h2>No active conversation</h2>
                                <p>Click "+ New Conversation" to start chatting with Roast &amp; Co.</p>
                            </div>
                        </div>
                    `;
                    if (activeChatTitle) activeChatTitle.textContent = 'Roastery Assistant';
                }
            }
        } catch (err) {
            console.error(err);
            alert('Failed to delete chat.');
        }
    }
});
