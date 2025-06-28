// MCTS Chess Engine JavaScript

// Game state
let gameBoard = null;
let selectedSquare = null;
let legalMoves = [];
let isAIThinking = false;
let sessionId = null; // Store session ID for backend communication
let gameMode = 'human_vs_ai'; // Default game mode
let playerName = ''; // Current player's name
let isJoiningGame = false; // Flag to track if joining an existing game
let useRLEngine = false; // RL enhancement setting
let gameState = {
    current_player: 'white',
    is_check: false,
    is_checkmate: false,
    is_stalemate: false
};

// API configuration
const API_BASE = 'http://localhost:8000/api';

// Sound management
let audioContext = null;
let soundEnabled = true;

// Initialize audio context (must be done after user interaction)
function initAudio() {
    if (!audioContext) {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
    }
}

// Sound generation functions
function playSound(frequency, duration, type = 'sine', volume = 0.3) {
    if (!soundEnabled || !audioContext) return;
    
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();
    
    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);
    
    oscillator.frequency.setValueAtTime(frequency, audioContext.currentTime);
    oscillator.type = type;
    
    gainNode.gain.setValueAtTime(volume, audioContext.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + duration);
    
    oscillator.start(audioContext.currentTime);
    oscillator.stop(audioContext.currentTime + duration);
}

function playChord(frequencies, duration, volume = 0.2) {
    frequencies.forEach(freq => playSound(freq, duration, 'sine', volume));
}

// Specific game sounds
const gameSounds = {
    gameStart: () => playChord([261.63, 329.63, 392.00], 0.8, 0.3), // C major chord
    move: () => playSound(400, 0.15, 'square', 0.2),
    capture: () => {
        playSound(600, 0.1, 'sawtooth', 0.3);
        setTimeout(() => playSound(300, 0.2, 'triangle', 0.2), 100);
    },
    check: () => {
        playSound(800, 0.3, 'triangle', 0.4);
        setTimeout(() => playSound(1000, 0.2, 'sine', 0.3), 150);
    },
    invalidMove: () => {
        playSound(200, 0.3, 'square', 0.3);
        setTimeout(() => playSound(150, 0.2, 'square', 0.2), 150);
    },
    checkmate: () => {
        // Victory fanfare
        const notes = [523.25, 659.25, 783.99, 1046.50]; // C5, E5, G5, C6
        notes.forEach((note, i) => {
            setTimeout(() => playSound(note, 0.4, 'sine', 0.4), i * 200);
        });
    },
    queenCapture: () => {
        // Special dramatic sound for queen capture
        playSound(1000, 0.2, 'sawtooth', 0.4);
        setTimeout(() => playSound(800, 0.3, 'triangle', 0.3), 100);
        setTimeout(() => playSound(600, 0.4, 'sine', 0.3), 200);
    },
    promotion: () => {
        // Ascending scale for pawn promotion
        const notes = [261.63, 293.66, 329.63, 349.23, 392.00];
        notes.forEach((note, i) => {
            setTimeout(() => playSound(note, 0.2, 'sine', 0.3), i * 80);
        });
    }
};

// Chess piece symbols
const pieceSymbols = {
    'white': {
        'P': '♙', 'R': '♖', 'N': '♘', 'B': '♗', 'Q': '♕', 'K': '♔'
    },
    'black': {
        'P': '♟', 'R': '♜', 'N': '♞', 'B': '♝', 'Q': '♛', 'K': '♚'
    }
};

// Initialize the game
async function initGame() {
    try {
        // Initialize audio on first user interaction
        initAudio();
        
        // Initialize RL settings
        initializeRLSettings();
        
        // Check if joining an existing game via URL parameter
        const urlParams = new URLSearchParams(window.location.search);
        const inviteSessionId = urlParams.get('session_id'); // Legacy support
        const invitationCode = urlParams.get('invitation_code'); // New invitation system
        
        if (invitationCode) {
            // Joining via invitation code (preferred method)
            isJoiningGame = true;
            gameMode = 'human_vs_human';
            document.getElementById('gameModeSelect').value = 'human_vs_human';
            
            // Connect WebSocket for real-time updates
            // Note: We'll get the actual session ID after joining
            
            // Show join game interface with invitation code
            await showJoinGameInterface(invitationCode);
            return;
        } else if (inviteSessionId) {
            // Legacy: Joining via session ID (for backward compatibility)
            isJoiningGame = true;
            sessionId = inviteSessionId;
            gameMode = 'human_vs_human';
            document.getElementById('gameModeSelect').value = 'human_vs_human';
            
            // Connect WebSocket for real-time updates
            connectWebSocket();
            
            // Show join game interface
            await showJoinGameInterface();
            return;
        }
        
        // For Human vs Human mode, skip session creation and go to invitation setup
        if (gameMode === 'human_vs_human') {
            updateUIForGameMode();
            return;
        }
        
        // Create new session with selected game mode (for Human vs AI)
        const createResponse = await fetch(`${API_BASE}/session`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                game_mode: gameMode
            })
        });
        
        const createData = await createResponse.json();
        if (!createData.success) {
            throw new Error('Failed to create session');
        }
        
        sessionId = createData.session_id;
        console.log('Created session:', sessionId, 'Mode:', gameMode);
        
        // Connect WebSocket for real-time updates (especially for multiplayer)
        connectWebSocket();
        
        // Get initial game state
        const response = await fetch(`${API_BASE}/game/state?session_id=${sessionId}`);
        if (!response.ok) throw new Error('Failed to get game state');
        
        const data = await response.json();
        
        updateGameState(data);
        updateConnectionStatus(true);
        renderBoard();
        
        updateUIForGameMode();
        
        // Play game start sound
        setTimeout(() => gameSounds.gameStart(), 300);
        
    } catch (error) {
        console.error('Failed to initialize game:', error);
        updateConnectionStatus(false);
        document.getElementById('status').textContent = 'Failed to connect to chess engine';
    }
}

function updateStatusForGameMode() {
    updateUIForGameMode();
}

async function changeGameMode() {
    const select = document.getElementById('gameModeSelect');
    gameMode = select.value;
    console.log('Game mode changed to:', gameMode);
    
    // Reset joining state
    isJoiningGame = false;
    playerName = '';
    
    // Start a new game with the new mode
    await initGame();
}

function updateConnectionStatus(connected) {
    const status = document.getElementById('connectionStatus');
    if (connected) {
        status.textContent = '🟢 Connected';
        status.className = 'connection-status connected';
    } else {
        status.textContent = '🔴 Disconnected';
        status.className = 'connection-status disconnected';
    }
}

function updateGameState(data) {
    // Handle different response structures
    let stateData = data;
    if (data.game_state) {
        // Newer structure: { success: true, game_state: {...}, ... }
        stateData = data.game_state;
    }

    // Check if this is a direct game state response (from /api/game/state)
    if (stateData.board && Array.isArray(stateData.board)) {
        // Direct GameStateResponse structure: board is 2D array
        gameBoard = stateData.board;
        gameState = {
            current_player: stateData.current_player,
            is_check: stateData.is_check,
            is_checkmate: stateData.is_checkmate,
            is_stalemate: stateData.is_stalemate,
            material_balance: stateData.material_balance
        };
    } else if (stateData.board && stateData.board.board) {
        // Nested structure: board is wrapped in an object
        gameBoard = stateData.board.board;
        gameState = {
            current_player: stateData.board.current_player,
            is_check: stateData.is_check,
            is_checkmate: stateData.is_checkmate,
            is_stalemate: stateData.is_stalemate,
            material_balance: stateData.material_balance || stateData.board.material_balance
        };
    }
    
    // Legal moves should be at the top level in both response types
    legalMoves = stateData.legal_moves || [];

    // If session type is human_vs_human, update invitation and controls
    if (gameMode === 'human_vs_human') {
        updateHumanVsHumanUI();
    }

    console.log('Updated game state:', gameState);
    console.log('Legal moves count:', legalMoves.length);
    console.log('Material balance:', gameState.material_balance);
    
    updateGameInfo();
}

function updateHumanVsHumanUI() {
    // This function is now handled by updateUIForGameMode()
    // Keep for backward compatibility but delegate to new system
    updateUIForGameMode();
}

function updateGameInfo() {
    document.getElementById('currentPlayer').textContent = 
        gameState.current_player === 'white' ? 'White' : 'Black';
    
    document.getElementById('checkStatus').textContent = 
        gameState.is_check ? 'In Check!' : 'None';
    
    let state = 'In Progress';
    if (gameState.is_checkmate) state = 'Checkmate!';
    else if (gameState.is_stalemate) state = 'Stalemate!';
    
    document.getElementById('gameState').textContent = state;
    
    // Update game mode display
    document.getElementById('currentGameMode').textContent = 
        gameMode === 'human_vs_ai' ? 'Human vs AI' : 'Human vs Human';
    
    document.getElementById('gameModeInstructions').textContent = 
        gameMode === 'human_vs_ai' ? '• You play as White, AI as Black' : '• Both players take turns';
    
    // Update material balance if available
    if (gameState.material_balance) {
        updateMaterialBalance(gameState.material_balance);
    }
    
    // Update AI move button - only show in Human vs AI mode when it's black's turn
    const aiBtn = document.getElementById('aiMoveBtn');
    if (gameMode === 'human_vs_ai') {
        aiBtn.style.display = 'inline-block';
        aiBtn.disabled = gameState.current_player !== 'black' || 
                       gameState.is_checkmate || gameState.is_stalemate || isAIThinking;
    } else {
        aiBtn.style.display = 'none';
    }
}

function renderBoard() {
    const boardElement = document.getElementById('chessBoard');
    boardElement.innerHTML = '';
    
    // Safety check - ensure gameBoard is initialized
    if (!gameBoard || !Array.isArray(gameBoard)) {
        console.error('gameBoard is not initialized or not an array:', gameBoard);
        return;
    }
    
    for (let row = 0; row < 8; row++) {
        for (let col = 0; col < 8; col++) {
            const square = document.createElement('div');
            square.className = `square ${(row + col) % 2 === 0 ? 'light' : 'dark'}`;
            square.dataset.row = row;
            square.dataset.col = col;
            
            // Add piece if present
            const piece = gameBoard[row][col];
            if (piece) {
                square.textContent = pieceSymbols[piece.color][piece.type];
                
                // Highlight king in check
                if (piece.type === 'K' && gameState.is_check && piece.color === gameState.current_player) {
                    square.style.backgroundColor = '#ff6b6b';
                    square.style.animation = 'pulse 1s infinite';
                }
            }
            
            square.addEventListener('click', () => handleSquareClick(row, col));
            boardElement.appendChild(square);
        }
    }
    
    updateSquareHighlights();
}

function updateSquareHighlights() {
    const squares = document.querySelectorAll('.square');
    squares.forEach(square => {
        square.classList.remove('selected', 'legal-move');
    });
    
    if (selectedSquare) {
        const selectedElement = document.querySelector(
            `[data-row="${selectedSquare.row}"][data-col="${selectedSquare.col}"]`
        );
        if (selectedElement) {
            selectedElement.classList.add('selected');
        }
        
        // Highlight legal moves
        const pieceMoves = getPieceMovesAt(selectedSquare.row, selectedSquare.col);
        pieceMoves.forEach(move => {
            const moveElement = document.querySelector(
                `[data-row="${move[2]}"][data-col="${move[3]}"]`
            );
            if (moveElement) {
                moveElement.classList.add('legal-move');
            }
        });
    }
}

function getPieceMovesAt(row, col) {
    return legalMoves.filter(move => move[0] === row && move[1] === col);
}

async function handleSquareClick(row, col) {
    if (isAIThinking) return;
    if (gameState.is_checkmate || gameState.is_stalemate) return;
    
    // In Human vs Human mode, allow both colors to move
    // In Human vs AI mode, only allow white moves
    if (gameMode === 'human_vs_ai' && gameState.current_player !== 'white') return;
    
    const piece = gameBoard[row][col];
    const currentPlayerColor = gameState.current_player;
    
    console.log(`Square clicked: (${row},${col}), Piece:`, piece, 'Current player:', currentPlayerColor);
    
    if (selectedSquare) {
        // Check if this is a legal move
        const pieceMoves = getPieceMovesAt(selectedSquare.row, selectedSquare.col);
        const isLegalMove = pieceMoves.some(move => move[2] === row && move[3] === col);
        
        console.log('Piece moves from selected square:', pieceMoves);
        console.log('Is legal move to target square:', isLegalMove);
        
        if (isLegalMove) {
            // Check if this is a capture
            const capturedPiece = gameBoard[row][col];
            
            // Make the move
            await makeMove(selectedSquare.row, selectedSquare.col, row, col, capturedPiece);
            selectedSquare = null;
        } else if (piece && piece.color === currentPlayerColor) {
            // Select new piece of current player's color
            selectedSquare = {row, col};
            console.log('Selected new piece:', piece);
        } else {
            // Deselect
            selectedSquare = null;
            console.log('Deselected');
        }
    } else if (piece && piece.color === currentPlayerColor) {
        // Select piece of current player's color
        selectedSquare = {row, col};
        console.log('Selected piece:', piece);
    } else {
        console.log('Cannot select:', piece ? `Wrong color (${piece.color} vs ${currentPlayerColor})` : 'Empty square');
    }
    
    updateSquareHighlights();
}

async function makeMove(fromRow, fromCol, toRow, toCol, capturedPiece = null) {
    try {
        // Check if we have a session ID
        if (!sessionId) {
            console.error('No session ID available');
            document.getElementById('status').textContent = 'Session error - please refresh the page';
            return;
        }
        
        console.log(`Making move: (${fromRow},${fromCol}) → (${toRow},${toCol})`);
        if (capturedPiece) {
            console.log('Capturing piece:', capturedPiece);
        }
        
        // Include session ID as query parameter
        const url = `${API_BASE}/game/move?session_id=${sessionId}`;
        
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                from_row: fromRow,
                from_col: fromCol,
                to_row: toRow,
                to_col: toCol
            })
        });
        
        const data = await response.json();
        console.log('Move response:', data);
        
        if (data.success) {
            // Play appropriate sound based on move type
            if (capturedPiece) {
                if (capturedPiece.type === 'Q') {
                    gameSounds.queenCapture();
                } else {
                    gameSounds.capture();
                }
                showCaptureNotification(capturedPiece);
            } else {
                gameSounds.move();
            }
            
            updateGameState(data);
            renderBoard();
            
            // Play check sound if opponent is in check
            if (gameState.is_check) {
                setTimeout(() => gameSounds.check(), 200);
            }
            
            // Add move to history
            const playerName = gameState.current_player === 'black' ? 
                (gameMode === 'human_vs_ai' ? 'White' : 'White Human') : 
                (gameMode === 'human_vs_ai' ? 'Black' : 'Black Human');
            addMoveToHistory(fromRow, fromCol, toRow, toCol, playerName, capturedPiece);
            
            if (gameState.is_checkmate) {
                const winner = gameState.current_player === 'white' ? 'Black' : 'White';
                document.getElementById('status').textContent = `Checkmate! ${winner} wins! 🎉`;
                showMilestoneNotification('Checkmate!', '👑');
                setTimeout(() => gameSounds.checkmate(), 300);
            } else if (gameState.is_stalemate) {
                document.getElementById('status').textContent = 'Stalemate! Draw! 🤝';
                showMilestoneNotification('Stalemate!', '🤝');
            } else if (gameMode === 'human_vs_ai' && gameState.current_player === 'black') {
                document.getElementById('status').textContent = 'Black to move - AI is thinking...';
                // Auto-trigger AI move after short delay
                setTimeout(getAIMove, 500);
            } else {
                // Human vs Human or it's white's turn in Human vs AI
                const currentPlayerName = gameState.current_player === 'white' ? 'White' : 'Black';
                document.getElementById('status').textContent = `${currentPlayerName} to move - Select a piece!`;
            }
        } else {
            console.error('Invalid move:', data);
            document.getElementById('status').textContent = `Invalid move! ${data.message || 'Try again.'}`;
            gameSounds.invalidMove();
            setTimeout(() => {
                updateStatusForGameMode();
            }, 2000);
        }
    } catch (error) {
        console.error('Failed to make move:', error);
        updateConnectionStatus(false);
        document.getElementById('status').textContent = 'Move failed - connection error';
        gameSounds.invalidMove();
    }
}

async function getAIMove() {
    if (isAIThinking) return;
    if (gameState.current_player !== 'black') return;
    
    // Check if we have a session ID
    if (!sessionId) {
        console.error('No session ID available');
        document.getElementById('status').textContent = 'Session error - please refresh the page';
        return;
    }
    
    isAIThinking = true;
    document.getElementById('status').textContent = 'AI is thinking...';
    document.getElementById('status').classList.add('thinking');
    document.getElementById('aiMoveBtn').disabled = true;
    
    try {
        // Include session ID as query parameter
        const url = `${API_BASE}/game/ai_move?session_id=${sessionId}`;
        
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        const data = await response.json();
        updateGameState(data);
        renderBoard();
        
        // Add AI move to history (we'd need to track the actual move made)
        addMoveToHistory(null, null, null, null, 'Black (AI)');
        
        if (gameState.is_checkmate) {
            document.getElementById('status').textContent = 'Checkmate! Black wins! 🤖';
        } else if (gameState.is_stalemate) {
            document.getElementById('status').textContent = 'Stalemate! Draw! 🤝';
        } else {
            document.getElementById('status').textContent = 'White to move - Your turn!';
        }
        
    } catch (error) {
        console.error('Failed to get AI move:', error);
        updateConnectionStatus(false);
        document.getElementById('status').textContent = 'AI move failed - connection error';
    } finally {
        isAIThinking = false;
        document.getElementById('status').classList.remove('thinking');
        updateGameInfo();
    }
}

function addMoveToHistory(fromRow, fromCol, toRow, toCol, player, capturedPiece = null) {
    const historyElement = document.getElementById('moveHistory');
    const moveElement = document.createElement('p');
    
    if (fromRow !== null) {
        const fromSquare = String.fromCharCode(97 + fromCol) + (8 - fromRow);
        const toSquare = String.fromCharCode(97 + toCol) + (8 - toRow);
        let moveText = `${player}: ${fromSquare} → ${toSquare}`;
        
        if (capturedPiece) {
            const capturedSymbol = pieceSymbols[capturedPiece.color][capturedPiece.type];
            moveText += ` (captured ${capturedSymbol})`;
            moveElement.style.color = '#ffaa44'; // Highlight captures
        }
        
        moveElement.textContent = moveText;
    } else {
        moveElement.textContent = `${player} moved`;
    }
    
    historyElement.appendChild(moveElement);
    historyElement.scrollTop = historyElement.scrollHeight;
}

function updateMaterialBalance(materialBalance) {
    document.getElementById('whiteMaterial').textContent = materialBalance.white_material;
    document.getElementById('blackMaterial').textContent = materialBalance.black_material;
    
    // Update piece counts
    document.getElementById('whitePieces').textContent = 
        materialBalance.white_pieces ? materialBalance.white_pieces.join(' ') : '';
    document.getElementById('blackPieces').textContent = 
        materialBalance.black_pieces ? materialBalance.black_pieces.join(' ') : '';
    
    // Update balance
    const difference = materialBalance.material_balance;
    let balanceText = 'Even';
    let balanceColor = '#ffffff';
    
    if (difference > 0) {
        balanceText = `White +${difference}`;
        balanceColor = '#90EE90';
    } else if (difference < 0) {
        balanceText = `Black +${Math.abs(difference)}`;
        balanceColor = '#FFB6C1';
    }
    
    const balanceElement = document.getElementById('materialDifference');
    balanceElement.textContent = balanceText;
    balanceElement.style.color = balanceColor;
}

function showCaptureNotification(capturedPiece) {
    const pieceValues = {
        'P': 1, 'N': 3, 'B': 3, 'R': 5, 'Q': 9, 'K': 0
    };
    
    const pieceValue = pieceValues[capturedPiece.type] || 0;
    const pieceSymbol = pieceSymbols[capturedPiece.color][capturedPiece.type];
    
    let message = `Captured ${pieceSymbol}`;
    if (pieceValue > 0) {
        message += ` (+${pieceValue} point${pieceValue !== 1 ? 's' : ''})`;
    }
    
    // Special messages for valuable pieces
    if (capturedPiece.type === 'Q') {
        message += ' 👑 QUEEN CAPTURED!';
    } else if (capturedPiece.type === 'R') {
        message += ' 🏰 ROOK CAPTURED!';
    }
    
    showNotification(message, 'capture');
}

function showMilestoneNotification(message, emoji) {
    showNotification(`${emoji} ${message} ${emoji}`, 'milestone');
}

function showNotification(message, type = 'normal') {
    // Remove any existing notifications
    const existingNotifications = document.querySelectorAll('.notification');
    existingNotifications.forEach(n => n.remove());
    
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // Remove after animation
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 2000);
}

async function resetGame() {
    try {
        // Check if we have a session ID
        if (!sessionId) {
            console.error('No session ID available');
            document.getElementById('status').textContent = 'Session error - please refresh the page';
            return;
        }
        
        // Include session ID as query parameter
        const url = `${API_BASE}/game/reset?session_id=${sessionId}`;
        
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        const data = await response.json();
        updateGameState(data);
        selectedSquare = null;
        isAIThinking = false;
        
        renderBoard();
        
        document.getElementById('status').textContent = 'New game started - White to move!';
        document.getElementById('moveHistory').innerHTML = '<p>Game started. White to move.</p>';
        
    } catch (error) {
        console.error('Failed to reset game:', error);
        updateConnectionStatus(false);
        document.getElementById('status').textContent = 'Reset failed - connection error';
    }
}

// Player and invitation management functions
async function showJoinGameInterface(invitationCode = null) {
    try {
        if (invitationCode) {
            console.log('showJoinGameInterface: Starting with invitation code', invitationCode);
            
            // Get invitation details
            const response = await fetch(`${API_BASE}/invitation/${invitationCode}`);
            if (!response.ok) {
                throw new Error('Invitation not found or expired');
            }

            const invitationData = await response.json();
            console.log('showJoinGameInterface: Got invitation data', invitationData);
            
            // Show join interface with invitation details
            document.getElementById('joinGame').style.display = 'block';
            document.getElementById('playerSetup').style.display = 'none';
            document.getElementById('inviteLink').style.display = 'none';
            
            // Update join info
            const hostName = invitationData.host_name || 'Host';
            document.getElementById('joinGameInfo').textContent = 
                `${hostName} has invited you to play chess. Enter your name to join as Black.`;

            // Store invitation code for later use in joinGameSession
            window.currentInvitationCode = invitationCode;
            
        } else {
            // Legacy session ID flow
            console.log('showJoinGameInterface: Starting for session', sessionId);
            
            // Get game state to check if it exists
            const response = await fetch(`${API_BASE}/game/state?session_id=${sessionId}`);
            if (!response.ok) {
                throw new Error('Game session not found');
            }

            const data = await response.json();
            console.log('showJoinGameInterface: Got game state', data);
            
            // Show join interface
            document.getElementById('joinGame').style.display = 'block';
            document.getElementById('playerSetup').style.display = 'none';
            document.getElementById('inviteLink').style.display = 'none';
            
            // Update join info
            const hostName = data.player_white || 'Host';
            document.getElementById('joinGameInfo').textContent = 
                `${hostName} has invited you to play chess. Enter your name to join as Black.`;

            updateGameState(data);
            updateConnectionStatus(true);
            renderBoard();
        }
        
    } catch (error) {
        console.error('Failed to load game session:', error);
        document.getElementById('status').textContent = 'Invalid invitation link or game not found';
        updateConnectionStatus(false);
    }
}

async function joinGameSession() {
    const joinName = document.getElementById('joinPlayerName').value.trim();
    if (!joinName) {
        alert('Please enter your name');
        return;
    }
    
    try {
        let joinData;
        
        if (window.currentInvitationCode) {
            // Join using invitation code
            console.log('Joining with invitation code:', window.currentInvitationCode);
            const response = await fetch(`${API_BASE}/invitation/${window.currentInvitationCode}/join`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    player_name: joinName
                })
            });
            
            if (!response.ok) {
                throw new Error('Failed to join game via invitation');
            }
            
            joinData = await response.json();
            console.log('Invitation join response received:', joinData);
            
            // Set the session ID from the invitation response
            if (joinData.session_id) {
                sessionId = joinData.session_id;
                console.log('Session ID set from invitation:', sessionId);
            }
            
        } else {
            // Legacy: Join using session ID directly
            const response = await fetch(`${API_BASE}/session/${sessionId}/join`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    player_name: joinName,
                    color: 'black'
                })
            });
            
            if (!response.ok) {
                throw new Error('Failed to join game');
            }
            
            joinData = await response.json();
            console.log('Direct join response received:', joinData);
        }
        
        if (!joinData.success) {
            throw new Error(joinData.message || 'Failed to join game');
        }
        
        playerName = joinName;
        document.getElementById('joinGame').style.display = 'none';
        document.getElementById('status').textContent = `Welcome ${joinName}! You are playing as Black.`;
        
        // Connect WebSocket now that we have a session ID
        connectWebSocket();
        
        // Use the game state from the join response and ensure board is rendered
        if (joinData.game_state) {
            updateGameState(joinData.game_state);
            renderBoard(); // Explicitly render the board
            updateGameInfo();
        } else {
            // Fallback: fetch game state if not included in join response
            console.log('No game state in join response, fetching separately...');
            const stateResponse = await fetch(`${API_BASE}/game/state?session_id=${sessionId}`);
            if (stateResponse.ok) {
                const stateData = await stateResponse.json();
                updateGameState(stateData);
                renderBoard();
                updateGameInfo();
            }
        }
        
        updateUIForGameMode();
        updateConnectionStatus(true);
        
    } catch (error) {
        console.error('Failed to join game:', error);
        document.getElementById('status').textContent = `Failed to join game: ${error.message}`;
        updateConnectionStatus(false);
    }
}

async function setPlayerName() {
    const name = document.getElementById('playerName').value.trim();
    if (!name) {
        alert('Please enter your name');
        return;
    }
    
    try {
        // Create invitation code instead of session
        const response = await fetch(`${API_BASE}/invitation`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                host_name: name,
                use_rl_engine: useRLEngine
            })
        });
        
        if (!response.ok) {
            throw new Error('Failed to create invitation');
        }
        
        const invitationData = await response.json();
        console.log('Invitation created:', invitationData);
        
        if (!invitationData.success) {
            throw new Error('Failed to create invitation');
        }
        
        playerName = name;
        window.currentInvitationCode = invitationData.invitation_code;
        
        document.getElementById('playerStatus').textContent = `Welcome ${name}! You are hosting as White.`;
        document.getElementById('setNameBtn').disabled = true;
        document.getElementById('playerName').disabled = true;
        
        // Show invitation link with invitation code
        showInvitationLink(invitationData.invitation_code);
        
    } catch (error) {
        console.error('Failed to create invitation:', error);
        alert('Failed to create invitation');
    }
}

function showInvitationLink(invitationCode) {
    const inviteDiv = document.getElementById('inviteLink');
    const inviteUrl = `${window.location.origin}${window.location.pathname}?invitation_code=${invitationCode}`;
    
    document.getElementById('inviteUrl').value = inviteUrl;
    inviteDiv.style.display = 'block';
    
    document.getElementById('inviteStatus').textContent = 'Waiting for your friend to join...';
}

function copyInviteLink() {
    const inviteUrl = document.getElementById('inviteUrl');
    inviteUrl.select();
    inviteUrl.setSelectionRange(0, 99999); // For mobile devices
    
    try {
        navigator.clipboard.writeText(inviteUrl.value);
        document.getElementById('inviteStatus').textContent = 'Link copied! Share it with your friend.';
        setTimeout(() => {
            document.getElementById('inviteStatus').textContent = 'Waiting for your friend to join...';
        }, 3000);
    } catch (err) {
        console.error('Failed to copy link:', err);
        document.getElementById('inviteStatus').textContent = 'Failed to copy link. Please copy manually.';
    }
}

function updateUIForGameMode() {
    // Hide all mode-specific UI elements first
    document.getElementById('playerSetup').style.display = 'none';
    document.getElementById('inviteLink').style.display = 'none';
    document.getElementById('joinGame').style.display = 'none';
    
    // Update AI settings visibility
    updateAISettingsVisibility();
    
    if (gameMode === 'human_vs_human' && !isJoiningGame) {
        // Show player setup for host
        document.getElementById('playerSetup').style.display = 'block';
        document.getElementById('status').textContent = 'Set your name to start a Human vs Human game';
    } else if (gameMode === 'human_vs_ai') {
        document.getElementById('status').textContent = 'White to move - Select a piece!';
    } else if (isJoiningGame) {
        // Join interface is already shown in showJoinGameInterface
        return;
    }
    
    updateGameInfo();
}

// RL Engine Settings
async function toggleRLEngine() {
    const checkbox = document.getElementById('useRLEngine');
    useRLEngine = checkbox.checked;
    
    // Update status
    const statusDiv = document.getElementById('rlStatus');
    if (useRLEngine) {
        statusDiv.textContent = '🟢 RL Enhancement: Enabled - AI will learn from recorded games';
        statusDiv.style.color = '#4CAF50';
    } else {
        statusDiv.textContent = '🔴 RL Enhancement: Disabled - Using standard MCTS';
        statusDiv.style.color = '#FF5722';
    }
    
    // Send setting to backend if we have a session - but don't change sessionId!
    if (sessionId && sessionId.trim() !== '') {
        try {
            console.log('Updating RL setting for session:', sessionId);
            const response = await fetch(`${API_BASE}/session/${sessionId}/settings`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    use_rl_engine: useRLEngine
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                console.log('RL setting updated on backend:', result);
                // Important: Don't update sessionId here, keep the existing one
            } else {
                console.warn('Failed to update RL setting on backend, status:', response.status);
                const errorText = await response.text();
                console.warn('Error response:', errorText);
            }
        } catch (error) {
            console.warn('Error updating RL setting:', error);
        }
    } else {
        console.log('No valid session ID available, RL setting will be applied to next session');
    }
}

function updateAISettingsVisibility() {
    const aiSettings = document.getElementById('aiSettings');
    if (gameMode === 'human_vs_ai') {
        aiSettings.style.display = 'block';
    } else {
        aiSettings.style.display = 'none';
    }
}

// Initialize RL status on page load
function initializeRLSettings() {
    const checkbox = document.getElementById('useRLEngine');
    checkbox.checked = useRLEngine;
    toggleRLEngine(); // Update status text
}

// Initialize the game when page loads
window.addEventListener('load', initGame);

// Check connection periodically
setInterval(async () => {
    try {
        // Only check connection if we have a session ID and it's not empty
        if (sessionId && sessionId.trim() !== '') {
            const url = `${API_BASE}/game/state?session_id=${sessionId}`;
            const response = await fetch(url);
            updateConnectionStatus(response.ok);
        } else {
            // Just check if backend is alive when no session - use root endpoint
            const response = await fetch('http://localhost:8000/', {
                method: 'GET',
                mode: 'cors'
            });
            updateConnectionStatus(response.ok);
        }
    } catch (error) {
        updateConnectionStatus(false);
    }
}, 5000);

// WebSocket management
let socket = null;
let reconnectAttempts = 0;
const maxReconnectAttempts = 5;

function connectWebSocket() {
    if (!sessionId) {
        console.log('No session ID available for WebSocket connection');
        return;
    }
    
    // Don't connect if already connected
    if (socket && socket.readyState === WebSocket.OPEN) {
        return;
    }
    
    try {
        const wsUrl = `ws://localhost:8000/ws/${sessionId}`;
        console.log('Connecting to WebSocket:', wsUrl);
        socket = new WebSocket(wsUrl);
        
        socket.onopen = function(event) {
            console.log('🔗 WebSocket connected');
            reconnectAttempts = 0;
            updateConnectionStatus(true);
        };
        
        socket.onmessage = function(event) {
            try {
                const data = JSON.parse(event.data);
                console.log('📨 WebSocket message received:', data);
                handleWebSocketMessage(data);
            } catch (error) {
                console.error('Error parsing WebSocket message:', error);
            }
        };
        
        socket.onclose = function(event) {
            console.log('🔌 WebSocket disconnected');
            updateConnectionStatus(false);
            
            // Attempt to reconnect for multiplayer games
            if (gameMode === 'human_vs_human' && reconnectAttempts < maxReconnectAttempts) {
                reconnectAttempts++;
                console.log(`Attempting to reconnect (${reconnectAttempts}/${maxReconnectAttempts})...`);
                setTimeout(connectWebSocket, 2000 * reconnectAttempts);
            }
        };
        
        socket.onerror = function(error) {
            console.error('❌ WebSocket error:', error);
            updateConnectionStatus(false);
        };
        
    } catch (error) {
        console.error('Failed to create WebSocket connection:', error);
        updateConnectionStatus(false);
    }
}

function handleWebSocketMessage(data) {
    switch (data.type) {
        case 'game_update':
            if (data.game_state) {
                updateGameState(data.game_state);
                renderBoard();
                updateGameInfo();
            }
            break;
        case 'player_joined':
            document.getElementById('status').textContent = data.message || 'A player has joined the game';
            break;
        case 'move_made':
            if (data.game_state) {
                updateGameState(data.game_state);
                renderBoard();
                updateGameInfo();
                playMoveSound();
            }
            break;
        case 'game_finished':
            document.getElementById('status').textContent = data.message || 'Game finished';
            break;
        default:
            console.log('Unknown WebSocket message type:', data.type);
    }
}

function disconnectWebSocket() {
    if (socket) {
        socket.close();
        socket = null;
    }
}
