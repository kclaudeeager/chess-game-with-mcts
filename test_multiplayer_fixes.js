// Multiplayer Test Script - Run in browser console
console.log('🧪 Testing Multiplayer Fixes...');

// Test functions that should be available
const tests = [
    {
        name: 'Player Color Detection',
        test: () => {
            if (typeof getMyPlayerColor === 'function') {
                const color = getMyPlayerColor();
                console.log('✅ getMyPlayerColor() returns:', color);
                return color !== null;
            }
            return false;
        }
    },
    {
        name: 'Player Name Detection', 
        test: () => {
            if (typeof getMyPlayerName === 'function') {
                const name = getMyPlayerName();
                console.log('✅ getMyPlayerName() returns:', name);
                return name !== null && name !== '';
            }
            return false;
        }
    },
    {
        name: 'Game Mode Check',
        test: () => {
            console.log('✅ Current game mode:', gameMode);
            console.log('✅ Current player name:', playerName);
            console.log('✅ Is joining game:', isJoiningGame);
            console.log('✅ Current invitation code:', window.currentInvitationCode);
            return true;
        }
    },
    {
        name: 'Game State Check',
        test: () => {
            console.log('✅ Current game state:', gameState);
            console.log('✅ Current player turn:', gameState.current_player);
            console.log('✅ White player:', gameState.player_white);
            console.log('✅ Black player:', gameState.player_black);
            return true;
        }
    },
    {
        name: 'WebSocket Status',
        test: () => {
            if (socket) {
                console.log('✅ WebSocket state:', socket.readyState);
                console.log('✅ WebSocket URL:', socket.url);
                return socket.readyState === WebSocket.OPEN;
            } else {
                console.log('❌ No WebSocket connection');
                return false;
            }
        }
    },
    {
        name: 'Session ID',
        test: () => {
            console.log('✅ Session ID:', sessionId);
            return sessionId !== null && sessionId !== '';
        }
    }
];

// Run all tests
let passed = 0;
let total = tests.length;

tests.forEach(test => {
    try {
        const result = test.test();
        if (result) {
            console.log(`✅ ${test.name}: PASSED`);
            passed++;
        } else {
            console.log(`❌ ${test.name}: FAILED`);
        }
    } catch (error) {
        console.log(`❌ ${test.name}: ERROR -`, error.message);
    }
});

console.log(`\n🎯 Test Results: ${passed}/${total} tests passed`);

// Additional debugging info
console.log('\n🔍 Debugging Info:');
console.log('URL params:', new URLSearchParams(window.location.search).get('invitation_code'));
console.log('Document title:', document.title);
console.log('Status element:', document.getElementById('status')?.textContent);

// Test color assignment logic specifically
console.log('\n🎨 Color Assignment Test:');
if (typeof getMyPlayerColor === 'function') {
    const detectedColor = getMyPlayerColor();
    const isHost = !isJoiningGame && window.currentInvitationCode;
    const isGuest = isJoiningGame || new URLSearchParams(window.location.search).get('invitation_code');
    
    console.log('Detected color:', detectedColor);
    console.log('Should be host (white):', isHost);
    console.log('Should be guest (black):', isGuest);
    
    if (isHost && detectedColor === 'white') {
        console.log('✅ Host correctly assigned WHITE');
    } else if (isGuest && detectedColor === 'black') {
        console.log('✅ Guest correctly assigned BLACK');
    } else {
        console.log('❌ Color assignment may be incorrect');
    }
}
