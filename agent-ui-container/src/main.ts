import { initFederation } from '@angular-architects/native-federation';

initFederation()
  .then(() => import('./bootstrap'))
  .catch((err) => {
    console.error('Fatal federation bootstrap error:', err);
    const root = document.querySelector('app-root') ?? document.body;
    const banner = document.createElement('div');
    banner.setAttribute('role', 'alert');
    banner.style.cssText = 'color:#b91c1c;background:#fef2f2;border:1px solid #f87171;padding:16px;margin:16px;border-radius:6px;font-family:monospace;';
    banner.textContent = `Fatal Error: Failed to initialize application federation (${err instanceof Error ? err.message : String(err)}).`;
    root.replaceChildren(banner);
  });

