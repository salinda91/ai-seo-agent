// Manifest V3 Background Service Worker for AI SEO Agent

chrome.runtime.onInstalled.addListener(() => {
  console.log('AI SEO Agent extension installed.');
  // Configure side panel to open on action click
  if (chrome.sidePanel && chrome.sidePanel.setPanelBehavior) {
    chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch((err) => {
      console.warn('Failed to set side panel behavior:', err);
    });
  }

  // Set up periodic alarm to check pending approvals
  if (chrome.alarms) {
    chrome.alarms.create('checkPendingTasks', { periodInMinutes: 2 });
  }
});

// Periodic alarm listener to check pending approvals
if (chrome.alarms && chrome.alarms.onAlarm) {
  chrome.alarms.onAlarm.addListener(async (alarm) => {
    if (alarm.name === 'checkPendingTasks') {
      try {
        const data = await chrome.storage.local.get(['agent_token', 'agent_base_url']);
        const baseUrl = data.agent_base_url || 'http://127.0.0.1:8765';
        const token = data.agent_token;

        if (token) {
          const res = await fetch(`${baseUrl}/api/tasks?limit=10`, {
            headers: { 'X-Agent-Token': String(token) }
          });
          if (res.ok) {
            const tasks = await res.json();
            const pendingApproval = tasks.filter((t: any) => t.status === 'waiting_approval').length;
            if (pendingApproval > 0) {
              chrome.action.setBadgeText({ text: String(pendingApproval) });
              chrome.action.setBadgeBackgroundColor({ color: '#f59e0b' });
            } else {
              chrome.action.setBadgeText({ text: '' });
            }
          }
        }
      } catch {
        // Agent offline or network error
      }
    }
  });
}

// Forwarding messages between content script and side panel
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type === 'PING') {
    sendResponse({ status: 'PONG' });
  }
  return true;
});
