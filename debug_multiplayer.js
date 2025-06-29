// Real-time multiplayer debugging console tool
// Paste this into the browser console to debug WebSocket communication

console.log("🔧 Starting Multiplayer Debug Tool...");

// Store original WebSocket methods
const originalWebSocket = window.WebSocket;
const originalSend = WebSocket.prototype.send;
const originalClose = WebSocket.prototype.close;

// Track all WebSocket instances
window.debugWebSockets = [];
window.debugMessages = [];

// Override WebSocket constructor to track connections
window.WebSocket = function(url, protocols) {
    console.log("🔌 Creating WebSocket connection:", url);
    const ws = new originalWebSocket(url, protocols);
    
    // Add debug info
    ws.debugId = window.debugWebSockets.length;
    ws.debugUrl = url;
    window.debugWebSockets.push(ws);
    
    // Override event handlers
    const originalOnOpen = ws.onopen;
    const originalOnMessage = ws.onmessage;
    const originalOnError = ws.onerror;
    const originalOnClose = ws.onclose;
    
    ws.onopen = function(event) {
        console.log(`✅ WebSocket ${ws.debugId} opened:`, ws.debugUrl);
        if (originalOnOpen) originalOnOpen.call(this, event);
    };
    
    ws.onmessage = function(event) {
        const timestamp = new Date().toISOString();
        console.log(`📥 WebSocket ${ws.debugId} received [${timestamp}]:`, event.data);
        window.debugMessages.push({
            type: 'received',
            wsId: ws.debugId,
            timestamp,
            data: event.data
        });
        if (originalOnMessage) originalOnMessage.call(this, event);
    };
    
    ws.onerror = function(event) {
        console.error(`❌ WebSocket ${ws.debugId} error:`, event);
        if (originalOnError) originalOnError.call(this, event);
    };
    
    ws.onclose = function(event) {
        console.log(`🔒 WebSocket ${ws.debugId} closed:`, event.code, event.reason);
        if (originalOnClose) originalOnClose.call(this, event);
    };
    
    return ws;
};

// Override send method to track outgoing messages
WebSocket.prototype.send = function(data) {
    const timestamp = new Date().toISOString();
    console.log(`📤 WebSocket ${this.debugId} sending [${timestamp}]:`, data);
    window.debugMessages.push({
        type: 'sent',
        wsId: this.debugId,
        timestamp,
        data: data
    });
    return originalSend.call(this, data);
};

// Helper functions for debugging
window.debugMultiplayer = {
    showConnections: () => {
        console.log("🔌 Active WebSocket connections:");
        window.debugWebSockets.forEach((ws, i) => {
            console.log(`  ${i}: ${ws.debugUrl} (state: ${ws.readyState})`);
        });
    },
    
    showMessages: (count = 10) => {
        console.log(`📋 Last ${count} WebSocket messages:`);
        const recent = window.debugMessages.slice(-count);
        recent.forEach(msg => {
            console.log(`  ${msg.timestamp} [WS${msg.wsId}] ${msg.type}: ${msg.data}`);
        });
    },
    
    clearMessages: () => {
        window.debugMessages = [];
        console.log("🗑️ Cleared message history");
    },
    
    showGameState: () => {
        console.log("🎮 Current game state:");
        console.log("  Session ID:", window.currentSessionId || "Not set");
        console.log("  Player Name:", window.currentPlayerName || "Not set");
        console.log("  Game Mode:", window.currentGameMode || "Not set");
        console.log("  Current Turn:", window.game ? window.game.turn() : "No game");
        
        // Check if elements exist
        const playersPanel = document.getElementById('players-panel');
        const gameBoard = document.getElementById('board');
        console.log("  Players Panel visible:", playersPanel && !playersPanel.classList.contains('hidden'));
        console.log("  Game Board visible:", gameBoard && gameBoard.style.display !== 'none');
    },
    
    testMove: (from, to) => {
        console.log(`🎯 Testing move: ${from} to ${to}`);
        if (window.game) {
            try {
                const move = window.game.move({from, to});
                console.log("✅ Move successful:", move);
                // Trigger UI update
                if (window.updateBoard) window.updateBoard();
                if (window.updateStatus) window.updateStatus();
            } catch (e) {
                console.error("❌ Move failed:", e);
            }
        } else {
            console.error("❌ No game instance found");
        }
    }
};

console.log("✅ Multiplayer Debug Tool loaded!");
console.log("🔧 Available commands:");
console.log("  debugMultiplayer.showConnections() - Show WebSocket connections");
console.log("  debugMultiplayer.showMessages() - Show recent messages");
console.log("  debugMultiplayer.showGameState() - Show current game state");
console.log("  debugMultiplayer.testMove('e2', 'e4') - Test a move");
console.log("  debugMultiplayer.clearMessages() - Clear message history");

// Auto-check connection status every 5 seconds
setInterval(() => {
    const activeConnections = window.debugWebSockets.filter(ws => ws.readyState === WebSocket.OPEN).length;
    if (activeConnections === 0) {
        console.warn("⚠️ No active WebSocket connections detected!");
    }
}, 5000);
