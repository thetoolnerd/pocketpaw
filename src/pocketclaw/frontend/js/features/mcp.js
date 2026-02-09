/**
 * PocketPaw - MCP Servers Feature Module
 *
 * Created: 2026-02-07
 *
 * Manages MCP (Model Context Protocol) server connections:
 * - List/add/remove servers
 * - Enable/disable servers
 * - View tool inventory
 */

window.PocketPaw = window.PocketPaw || {};

window.PocketPaw.MCP = {
    /**
     * Get initial state for MCP
     */
    getState() {
        return {
            showMCP: false,
            mcpServers: {},
            mcpForm: {
                name: '',
                transport: 'stdio',
                command: '',
                args: '',
                url: ''
            },
            mcpLoading: false
        };
    },

    /**
     * Get methods for MCP
     */
    getMethods() {
        return {
            /**
             * Open MCP modal and fetch status
             */
            async openMCP() {
                this.showMCP = true;
                await this.getMCPStatus();
                this.$nextTick(() => {
                    if (window.refreshIcons) window.refreshIcons();
                });
            },

            /**
             * Fetch MCP server status from backend
             */
            async getMCPStatus() {
                try {
                    const res = await fetch('/api/mcp/status');
                    if (res.ok) {
                        this.mcpServers = await res.json();
                    }
                } catch (e) {
                    console.error('Failed to get MCP status', e);
                }
            },

            /**
             * Add a new MCP server
             */
            async addMCPServer() {
                if (!this.mcpForm.name) return;
                this.mcpLoading = true;
                try {
                    const body = {
                        name: this.mcpForm.name,
                        transport: this.mcpForm.transport,
                        command: this.mcpForm.command,
                        args: this.mcpForm.args
                            ? this.mcpForm.args.split(',').map(s => s.trim())
                            : [],
                        url: this.mcpForm.url,
                        enabled: true
                    };
                    const res = await fetch('/api/mcp/add', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(body)
                    });
                    const data = await res.json();
                    if (data.status === 'ok') {
                        this.showToast(`MCP server "${this.mcpForm.name}" added`, 'success');
                        this.mcpForm = { name: '', transport: 'stdio', command: '', args: '', url: '' };
                        await this.getMCPStatus();
                    } else {
                        this.showToast(data.error || 'Failed to add server', 'error');
                    }
                } catch (e) {
                    this.showToast('Failed to add MCP server: ' + e.message, 'error');
                } finally {
                    this.mcpLoading = false;
                    this.$nextTick(() => {
                        if (window.refreshIcons) window.refreshIcons();
                    });
                }
            },

            /**
             * Remove an MCP server
             */
            async removeMCPServer(name) {
                try {
                    const res = await fetch('/api/mcp/remove', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ name })
                    });
                    const data = await res.json();
                    if (data.status === 'ok') {
                        this.showToast(`MCP server "${name}" removed`, 'info');
                        await this.getMCPStatus();
                    } else {
                        this.showToast(data.error || 'Failed to remove', 'error');
                    }
                } catch (e) {
                    this.showToast('Failed to remove server: ' + e.message, 'error');
                }
            },

            /**
             * Toggle (enable/disable) an MCP server
             */
            async toggleMCPServer(name) {
                try {
                    const res = await fetch('/api/mcp/toggle', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ name })
                    });
                    const data = await res.json();
                    if (data.status === 'ok') {
                        const state = data.enabled ? 'enabled' : 'disabled';
                        this.showToast(`MCP server "${name}" ${state}`, 'success');
                        await this.getMCPStatus();
                    } else {
                        this.showToast(data.error || 'Failed to toggle', 'error');
                    }
                } catch (e) {
                    this.showToast('Failed to toggle server: ' + e.message, 'error');
                }
                this.$nextTick(() => {
                    if (window.refreshIcons) window.refreshIcons();
                });
            },

            /**
             * Get the count of connected MCP servers (for sidebar badge)
             */
            connectedMCPCount() {
                return Object.values(this.mcpServers).filter(s => s.connected).length;
            }
        };
    }
};
