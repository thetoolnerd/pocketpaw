/**
 * PocketPaw - Chat Feature Module
 *
 * Created: 2026-02-05
 * Extracted from app.js as part of componentization refactor.
 *
 * Contains chat/messaging functionality:
 * - Message handling
 * - Streaming support
 * - Chat scroll management
 */

window.PocketPaw = window.PocketPaw || {};

window.PocketPaw.Chat = {
    name: 'Chat',
    /**
     * Get initial state for Chat
     */
    getState() {
        return {
            // Agent state
            agentActive: true,
            isStreaming: false,
            isThinking: false,
            streamingContent: '',
            streamingMessageId: null,
            hasShownWelcome: false,

            // Messages
            messages: [],
            inputText: '',
            pendingUploads: [],
        };
    },

    /**
     * Get methods for Chat
     */
    getMethods() {
        return {
            /**
             * Handle notification
             */
            handleNotification(data) {
                const content = data.content || '';

                // Skip duplicate connection messages
                if (content.includes('Connected to PocketPaw') && this.hasShownWelcome) {
                    return;
                }
                if (content.includes('Connected to PocketPaw')) {
                    this.hasShownWelcome = true;
                }

                this.showToast(content, 'info');
                this.log(content, 'info');
            },

            /**
             * Handle incoming message
             */
            handleMessage(data) {
                const content = data.content || '';
                const media = Array.isArray(data.media) ? data.media : [];

                // Check if it's a status update (don't show in chat)
                if (content.includes('System Status') || content.includes('🧠 CPU:')) {
                    this.status = Tools.parseStatus(content);
                    return;
                }

                // Server-side stream flag — auto-enter streaming if we missed stream_start
                if (data.is_stream_chunk && !this.isStreaming) {
                    this.startStreaming();
                }

                // Clear thinking state on first text content
                if (this.isThinking && content) {
                    this.isThinking = false;
                }

                // Handle streaming vs complete messages
                if (this.isStreaming) {
                    this.streamingContent += content;
                    // Scroll during streaming to follow new content
                    this.$nextTick(() => this.scrollToBottom());
                    // Don't log streaming chunks - they flood the terminal
                } else {
                    this.addMessage('assistant', content, { media });
                    // Only log complete messages (not streaming chunks)
                    if (content.trim()) {
                        this.log(content.substring(0, 100) + (content.length > 100 ? '...' : ''), 'info');
                    }
                }
            },

            /**
             * Handle code blocks
             */
            handleCode(data) {
                const content = data.content || '';
                if (this.isStreaming) {
                    this.streamingContent += '\n```\n' + content + '\n```\n';
                } else {
                    this.addMessage('assistant', '```\n' + content + '\n```');
                }
            },

            /**
             * Start streaming mode
             */
            startStreaming() {
                if (this._streamTimeout) {
                    clearTimeout(this._streamTimeout);
                }
                this.isStreaming = true;
                this.isThinking = true;
                this.streamingContent = '';
                // Safety timeout — prevent infinite spinner if backend hangs
                this._streamTimeout = setTimeout(() => {
                    if (this.isStreaming) {
                        this.addMessage('assistant', 'Response timed out. The agent may not be configured — check Settings.');
                        this.endStreaming();
                    }
                }, 90000);
            },

            /**
             * End streaming mode
             */
            endStreaming(streamEndData = {}) {
                if (this._streamTimeout) {
                    clearTimeout(this._streamTimeout);
                    this._streamTimeout = null;
                }
                const media = Array.isArray(streamEndData.media) ? streamEndData.media : [];
                if (this.isStreaming && this.streamingContent) {
                    this.addMessage('assistant', this.streamingContent, { media });
                } else if (media.length > 0) {
                    this.addMessage('assistant', 'Generated files ready for download:', { media });
                }
                this.isStreaming = false;
                this.isThinking = false;
                this.streamingContent = '';

                // Refresh sidebar sessions and auto-title
                if (this.loadSessions) this.loadSessions();
                if (this.autoTitleCurrentSession) this.autoTitleCurrentSession();
            },

            /**
             * Add a message to the chat
             */
            addMessage(role, content, extras = {}) {
                this.messages.push({
                    role,
                    content: content || '',
                    time: Tools.formatTime(),
                    isNew: true,
                    media: Array.isArray(extras.media) ? extras.media : []
                });

                // Auto scroll to bottom with slight delay for DOM update
                this.$nextTick(() => {
                    this.scrollToBottom();
                });
            },

            /**
             * Scroll chat to bottom
             */
            scrollToBottom() {
                if (this._scrollRAF) return;
                this._scrollRAF = requestAnimationFrame(() => {
                    const el = this.$refs.messages;
                    if (el) el.scrollTop = el.scrollHeight;
                    this._scrollRAF = null;
                });
            },

            onUploadPicked(event) {
                const picked = Array.from(event.target.files || []);
                if (picked.length === 0) return;
                const maxBytes = 20 * 1024 * 1024; // 20MB per file
                for (const file of picked) {
                    if (file.size > maxBytes) {
                        this.showToast(`Skipped ${file.name}: over 20MB limit`, 'warning');
                        continue;
                    }
                    this.pendingUploads.push(file);
                }
                event.target.value = '';
                this.$nextTick(() => {
                    if (window.refreshIcons) window.refreshIcons();
                });
            },

            removePendingUpload(index) {
                this.pendingUploads.splice(index, 1);
                this.$nextTick(() => {
                    if (window.refreshIcons) window.refreshIcons();
                });
            },

            clearPendingUploads() {
                this.pendingUploads = [];
                this.$nextTick(() => {
                    if (window.refreshIcons) window.refreshIcons();
                });
            },

            async _fileToBase64(file) {
                return await new Promise((resolve, reject) => {
                    const reader = new FileReader();
                    reader.onload = () => {
                        const out = String(reader.result || '');
                        const comma = out.indexOf(',');
                        resolve(comma >= 0 ? out.slice(comma + 1) : out);
                    };
                    reader.onerror = reject;
                    reader.readAsDataURL(file);
                });
            },

            mediaDownloadUrl(path) {
                return `/api/files/download?path=${encodeURIComponent(path)}`;
            },

            mediaFilename(path) {
                if (!path) return 'file';
                const clean = String(path).replace(/\\/g, '/');
                const parts = clean.split('/');
                return parts[parts.length - 1] || clean;
            },

            openMedia(path) {
                window.open(this.mediaDownloadUrl(path), '_blank', 'noopener,noreferrer');
            },

            /**
             * Send a chat message
             */
            async sendMessage() {
                const text = this.inputText.trim();
                const files = [...this.pendingUploads];
                if (!text && files.length === 0) return;

                // Check for skill command (starts with /)
                if (text.startsWith('/')) {
                    const parts = text.slice(1).split(' ');
                    const skillName = parts[0];
                    const args = parts.slice(1).join(' ');

                    // Add user message
                    this.addMessage('user', text);
                    this.inputText = '';

                    // Run the skill
                    socket.send('run_skill', { name: skillName, args });
                    this.log(`Running skill: /${skillName} ${args}`, 'info');
                    return;
                }

                // Add user message
                const userContent = files.length > 0
                    ? `${text || 'Uploaded file(s)'}\n\nAttached: ${files.map((f) => f.name).join(', ')}`
                    : text;
                this.addMessage('user', userContent);
                this.inputText = '';
                this.pendingUploads = [];

                // Start streaming indicator
                this.startStreaming();

                // Encode selected files for websocket media transport
                const media = [];
                for (const file of files) {
                    try {
                        media.push({
                            name: file.name,
                            mime_type: file.type || 'application/octet-stream',
                            data: await this._fileToBase64(file),
                        });
                    } catch (e) {
                        this.log(`Failed to encode ${file.name}: ${e}`, 'error');
                    }
                }

                // Send to server
                socket.chat(text, media);

                this.log(`You: ${text || `[${files.length} file(s) uploaded]`}`, 'info');
            },

            /**
             * Toggle agent mode
             */
            toggleAgent() {
                socket.toggleAgent(this.agentActive);
                this.log(`Switched Agent Mode: ${this.agentActive ? 'ON' : 'OFF'}`, 'info');
            }
        };
    }
};

window.PocketPaw.Loader.register('Chat', window.PocketPaw.Chat);
