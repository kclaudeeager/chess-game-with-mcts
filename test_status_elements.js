// Test script to verify both status elements are being updated
// Run this in browser console

console.log('🧪 Testing Status Element Updates...');

// Check if both status elements exist
const mobileStatus = document.getElementById('status');
const desktopStatus = document.getElementById('status-desktop');

console.log('Mobile status element:', mobileStatus);
console.log('Desktop status element:', desktopStatus);

if (mobileStatus) {
    console.log('✅ Mobile status current text:', mobileStatus.textContent);
} else {
    console.log('❌ Mobile status element not found');
}

if (desktopStatus) {
    console.log('✅ Desktop status current text:', desktopStatus.textContent);
} else {
    console.log('❌ Desktop status element not found');
}

// Test the updateStatus function
if (typeof updateStatus === 'function') {
    console.log('✅ updateStatus function is available');
    
    // Test updating status
    updateStatus('🧪 Test status update - ' + Date.now());
    
    // Check if both elements were updated
    setTimeout(() => {
        console.log('After update - Mobile status:', mobileStatus?.textContent);
        console.log('After update - Desktop status:', desktopStatus?.textContent);
        
        if (mobileStatus?.textContent === desktopStatus?.textContent) {
            console.log('✅ Both status elements are synchronized!');
        } else {
            console.log('❌ Status elements are not synchronized');
        }
    }, 100);
} else {
    console.log('❌ updateStatus function not found');
}

// Check current game state and status
console.log('\n🎮 Current Game Info:');
console.log('Game Mode:', gameMode);
console.log('Player Name:', playerName);
console.log('Session ID:', sessionId);
console.log('Is Joining Game:', isJoiningGame);

// Test color detection
if (typeof getMyPlayerColor === 'function') {
    console.log('My Player Color:', getMyPlayerColor());
}
