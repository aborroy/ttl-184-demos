// Scripted dry run of the ADW demos. Saves backup screenshots to argv[2] and times each step.
// Usage: node dryrun.cjs <out-dir> <file-for-check-in>
const { chromium } = require('playwright');
const OUT = process.argv[2];
const CHECKIN = process.argv[3];
const BASE = 'http://localhost:8080/workspace/';
const log = (...a) => console.log(new Date().toISOString().slice(11, 19), ...a);
(async () => {
  require('fs').mkdirSync(OUT, { recursive: true });
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2, acceptDownloads: true });
  const p = await ctx.newPage();
  // clip: the part of the 1440x900 window that proves the step, about 2.4:1 so it fills a slide.
  const CLIP = {
    'backup-checkout': { x: 395, y: 150, width: 470, height: 64 },
    'backup-checkin': { x: 395, y: 150, width: 470, height: 64 },
    'backup-search-before': { x: 320, y: 96, width: 780, height: 380 },
    'backup-search-after': { x: 320, y: 96, width: 780, height: 310 },
    'backup-drag-drop': { x: 538, y: 818, width: 366, height: 60 },
    'backup-viewer-breadcrumb': { x: 0, y: 0, width: 900, height: 260 },
  };
  const shot = async (n) => { await p.waitForTimeout(2000); await p.screenshot({ path: `${OUT}/${n}.png`, clip: process.env.NOCLIP ? undefined : CLIP[n] }); log('shot', n); };
  const step = async (name, fn) => { const t = Date.now(); try { await fn(); log('OK  ', name, `${((Date.now() - t) / 1000).toFixed(1)}s`); } catch (e) { log('FAIL', name, e.message.split('\n')[0]); await shot(`fail-${name}`); } };
  const openSite = async (folder) => {
    await p.goto(BASE + '#/libraries'); await p.waitForTimeout(2000);
    await p.getByText('Insurance Policies').first().dblclick(); await p.waitForTimeout(2000);
    if (folder) { await p.getByText(folder, { exact: true }).first().dblclick(); await p.waitForTimeout(2000); }
  };
  const menu = async (row, item) => { await p.getByText(row).first().click({ button: 'right' }); await p.waitForTimeout(800); await p.getByRole('menuitem', { name: item }).first().click(); };

  await p.goto(BASE); await p.waitForSelector('#username', { timeout: 60000 });
  await p.fill('#username', 'alice'); await p.fill('#password', 'alice-ttl184'); await p.click('#login-button');
  await p.waitForTimeout(4000);

  await step('checkout', async () => {
    await openSite('Contracts');
    await menu('Service-Agreement-2027.pdf', 'Edit Offline');
    await p.getByText(/Working Copy/).first().waitFor({ timeout: 15000 });
    await shot('backup-checkout');
  });
  await step('checkin', async () => {
    await p.getByText(/Working Copy/).first().click({ button: 'right' }); await p.waitForTimeout(800);
    const [chooser] = await Promise.all([p.waitForEvent('filechooser', { timeout: 10000 }),
      p.getByRole('menuitem', { name: 'Upload New Version' }).first().click()]);
    await chooser.setFiles(CHECKIN);
    await shot('checkin-dialog');
    // "Upload new version" is an <input type="button"> on top of a label; the file is already chosen.
    await p.locator('label[for="upload-single-file"]').click();
    await p.waitForTimeout(4000);
    // Close the upload panel, so it does not stay on the next screenshots.
    const close = p.locator('adf-file-uploading-dialog button, .adf-file-uploading-dialog button').filter({ hasText: /close/i }).first();
    if (await close.count()) await close.click();
    await p.waitForTimeout(1000);
    await shot('backup-checkin');
  });
  await step('search-filter', async () => {
    await p.goto(BASE + '#/search'); await p.waitForTimeout(2000);
    const box = p.getByPlaceholder('Search').first(); await box.fill('signed-contract'); await box.press('Enter');
    await p.waitForTimeout(3000);
    // Outline the Parent folder chip, so the backup slide shows where to look.
    await p.addStyleTag({ content: '.ttl184-mark { outline: 3px solid #6E33FF !important; outline-offset: 2px; border-radius: 999px; }' });
    // Mark the Parent folder chip and end the crop just after it, so no chip is cut.
    const markChip = async (n) => {
      await p.evaluate(() => { for (const el of document.querySelectorAll('button, [role=button], .mat-mdc-chip, adf-search-filter-chip *'))
        if (/^\s*Parent folder:/.test(el.textContent) && el.children.length < 6) { el.classList.add('ttl184-mark'); break; } });
      const box = await p.locator('.ttl184-mark').first().boundingBox();
      if (box) CLIP[n].width = Math.round(box.x + box.width + 16 - CLIP[n].x);
    };
    await markChip('backup-search-before');
    await shot('backup-search-before');
    await p.getByText('Parent folder: Any').first().click(); await p.waitForTimeout(800);
    await p.locator('.cdk-overlay-pane input').first().fill('POL-2026-0013'); await p.waitForTimeout(2500);
    await p.getByRole('option', { name: /POL-2026-0013/ }).first().click(); await p.waitForTimeout(800);
    const apply = p.getByRole('button', { name: /Apply/i }).first();
    if (await apply.count()) await apply.click();
    await p.waitForTimeout(3000); await markChip('backup-search-after'); await shot('backup-search-after');
  });
  await step('drag-drop', async () => {
    await openSite('Inbox');
    const src = p.getByText('scan-001.pdf').first(); const dst = p.getByText('Claims', { exact: true }).first();
    const s = await src.boundingBox(); const d = await dst.boundingBox();
    await p.mouse.move(s.x + 20, s.y + s.height / 2); await p.mouse.down();
    for (let i = 1; i <= 20; i++) { await p.mouse.move(s.x + 20 + (d.x - s.x) * i / 20, s.y + s.height / 2 + (d.y - s.y) * i / 20); await p.waitForTimeout(40); }
    await shot('drag-in-flight');
    await p.mouse.up(); await p.waitForTimeout(3000);
    await shot('backup-drag-drop');
  });
  await step('viewer-breadcrumb', async () => {
    await openSite('Reports');
    await p.getByText('Quarterly-Report-Q3.pdf').first().dblclick(); await p.waitForTimeout(3000);
    await shot('backup-viewer-breadcrumb');
    await p.keyboard.press('Escape'); await p.waitForTimeout(1500);
  });
  await step('download', async () => {
    await openSite('Reports');
    const [dl] = await Promise.all([p.waitForEvent('download', { timeout: 15000 }), menu('Quarterly-Report-Q3.pdf', 'Download')]);
    log('downloaded', dl.suggestedFilename());
  });
  await b.close();
})().catch(e => { console.error(e.message); process.exit(1); });
