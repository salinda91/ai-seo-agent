// Content script for active page SEO auditing

function auditCurrentPage() {
  const title = document.title || '';
  const descEl = document.querySelector('meta[name="description"], meta[property="og:description"]');
  const description = descEl ? descEl.getAttribute('content') || '' : '';
  const canonicalEl = document.querySelector('link[rel="canonical"]');
  const canonical = canonicalEl ? canonicalEl.getAttribute('href') || '' : '';
  const robotsEl = document.querySelector('meta[name="robots"]');
  const robots = robotsEl ? robotsEl.getAttribute('content') || '' : '';

  const h1s = Array.from(document.querySelectorAll('h1')).map(h => h.innerText.trim());
  const h2s = Array.from(document.querySelectorAll('h2')).map(h => h.innerText.trim());

  const imgs = Array.from(document.querySelectorAll('img'));
  const missingAlt = imgs.filter(img => !img.getAttribute('alt') || !img.getAttribute('alt')!.trim()).length;

  const schemas = Array.from(document.querySelectorAll('script[type="application/ld+json"]')).map(s => {
    try {
      return JSON.parse(s.innerHTML)?.['@type'] || 'JSON-LD';
    } catch {
      return 'Invalid JSON-LD';
    }
  });

  return {
    url: window.location.href,
    title,
    titleLength: title.length,
    description,
    descriptionLength: description.length,
    canonical,
    robots,
    h1s,
    h2Count: h2s.length,
    totalImages: imgs.length,
    missingAlt,
    schemas
  };
}

chrome.runtime.onMessage.addListener((request, _sender, sendResponse) => {
  if (request.type === 'INSPECT_ACTIVE_PAGE') {
    const data = auditCurrentPage();
    sendResponse({ success: true, data });
  }
  return true;
});
