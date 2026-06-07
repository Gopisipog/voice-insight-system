const { app, BrowserWindow, Menu, dialog, shell } = require('electron');
const path = require('path');
const fs = require('fs');

// Configuration
const BACKEND_URL = process.env.VITE_BACKEND_HOST || 'voice-insight-system.onrender.com';
const BACKEND_PORT = process.env.VITE_SERVER_PORT || '10000';
const VITE_PORT = 5173; // Local dev server port if running
const PWA_URL = `http://voice-insight-system.netlify.app`; // Default production URL

let mainWindow;

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1200,
        height: 800,
        minWidth: 800,
        minHeight: 600,
        title: 'VoiceInsight',
        icon: path.join(__dirname, 'icon.png'),
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            nodeIntegration: false,
            contextIsolation: true,
            webSecurity: false,
        },
        backgroundColor: '#1a1a2e',
        show: false,
    });

    // Custom Menu
    const menuTemplate = [
        {
            label: 'VoiceInsight',
            submenu: [
                { label: 'About', click: () => showAbout() },
                { type: 'separator' },
                { role: 'quit' }
            ]
        },
        {
            label: 'View',
            submenu: [
                { role: 'reload' },
                { role: 'toggleDevTools' },
                { type: 'separator' },
                { role: 'zoomIn' },
                { role: 'zoomOut' },
                { role: 'resetZoom' }
            ]
        },
        {
            label: 'Backend',
            submenu: [
                {
                    label: 'Open Backend Dashboard',
                    click: () => shell.openExternal(`https://dashboard.render.com/web/srv-d8ikcge47okc739fns60`)
                },
                { type: 'separator' },
                {
                    label: 'Health Check',
                    click: () => mainWindow.loadURL(getBackendUrl() + '/health')
                }
            ]
        },
        {
            label: 'Help',
            submenu: [
                {
                    label: 'Download Update',
                    click: () => downloadUpdate()
                },
                { type: 'separator' },
                {
                    label: 'Report Issue',
                    click: () => shell.openExternal('https://github.com/Gopisipog/voice-insight-system/issues')
                }
            ]
        }
    ];

    const menu = Menu.buildFromTemplate(menuTemplate);
    Menu.setApplicationMenu(menu);

    // Load the PWA
    mainWindow.loadURL(PWA_URL);

    // Show window when ready
    mainWindow.once('ready-to-show', () => {
        mainWindow.show();
    });

    mainWindow.on('closed', () => {
        mainWindow = null;
    });

    // Handle external links
    mainWindow.webContents.setWindowOpenHandler(({ url }) => {
        shell.openExternal(url);
        return { action: 'deny' };
    });
}

function getBackendUrl() {
    return `https://${BACKEND_URL}:${BACKEND_PORT}`;
}

function showAbout() {
    dialog.showMessageBox(mainWindow, {
        type: 'info',
        title: 'About VoiceInsight',
        message: 'Voice Insight System v1.0.0',
        detail: `A real-time voice transcription and analysis system.\n\nBackend: ${BACKEND_URL}\nWebSocket: wss://${BACKEND_URL}/ws/audio\n\nBuilt with Electron + React + FastAPI + Whisper`
    });
}

async function downloadUpdate() {
    const result = await dialog.showSaveDialog(mainWindow, {
        title: 'Save VoiceInsight Installer',
        defaultPath: 'VoiceInsight-Setup-1.0.0.exe',
        filters: [
            { name: 'Installer', extensions: ['exe'] },
            { name: 'Portable', extensions: ['exe'] }
        ]
    });

    if (!result.canceled && result.filePath) {
        // In a real app, this would download from GitHub releases
        dialog.showMessageBox(mainWindow, {
            type: 'info',
            title: 'Download Starting',
            message: 'Downloading VoiceInsight installer...',
            detail: `The latest version will be saved to:\n${result.filePath}`
        });
        
        // For demo: copy the app's own executable (in production, download from releases)
        try {
            const releaseUrl = 'https://github.com/Gopisipog/voice-insight-system/releases/latest/download/VoiceInsight-Setup-1.0.0.exe';
            shell.openExternal('https://github.com/Gopisipog/voice-insight-system/releases');
        } catch (err) {
            dialog.showErrorBox('Download Error', 'Could not download the installer. Please visit:\nhttps://github.com/Gopisipog/voice-insight-system/releases');
        }
    }
}

// Auto-updater check (in production, use electron-updater)
function checkForUpdates() {
    console.log('Checking for updates...');
    // Placeholder for electron-updater
}

app.whenReady().then(() => {
    createWindow();
    
    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});
