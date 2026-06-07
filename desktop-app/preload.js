const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
    getBackendUrl: () => ipcRenderer.invoke('get-backend-url'),
    downloadUpdate: () => ipcRenderer.invoke('download-update'),
    openExternal: (url) => ipcRenderer.invoke('open-external', url),
    getAppVersion: () => ipcRenderer.invoke('get-app-version'),
    
    // Listen for events
    onUpdateAvailable: (callback) => ipcRenderer.on('update-available', callback),
    onDownloadProgress: (callback) => ipcRenderer.on('download-progress', callback),
});
