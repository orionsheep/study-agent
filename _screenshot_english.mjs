import { chromium } from 'playwright';
import { mkdirSync, existsSync } from 'fs';

const TOKEN = 'lf_5_uDEGK4xbbRvEX5eK4s-KebKPAjunBqZLQOKg3Zt0c';
const SID = 'stu-211485830b75da90';
const APP_ID = 'app_d032d44c53ea';
const OUT = '/tmp/ew_screenshots';
const EXEC = '/Users/mychanging/Library/Caches/ms-playwright/chromium_headless_shell-1223/chrome-headless-shell-mac-arm64/chrome-headless-shell';
const CONV = 'conv-' + SID;
const BASE = 'http://localhost:5173';

if (!existsSync(OUT)) mkdirSync(OUT, { recursive: true });

async function shoot(mode) {
  console.log(`[${mode}] Launching browser...`);
  const browser = await chromium.launch({
    executablePath: EXEC,
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });

  // Set localStorage BEFORE page load so useTheme() picks up the right theme
  await page.addInitScript(({ token, sid, conv, appId, theme }) => {
    localStorage.setItem('learnforge.auth.token', token);
    localStorage.setItem('learnforge.session.context', JSON.stringify({
      studentId: sid,
      courseId: 'ai-course',
      conversationId: conv,
    }));
    localStorage.setItem('learnforge.settings.theme', JSON.stringify(theme));
    localStorage.setItem('learnforge.canvas.viewport', JSON.stringify({ x: 0, y: 0, scale: 1 }));
    localStorage.setItem('learnforge.canvas.windows.' + conv, JSON.stringify([appId]));
  }, { token: TOKEN, sid: SID, conv: CONV, appId: APP_ID, theme: mode });

  console.log(`[${mode}] Navigating to ${BASE}...`);
  await page.goto(BASE, { waitUntil: 'networkidle', timeout: 30000 });
  console.log(`[${mode}] Page loaded. Waiting 5s for React render...`);
  await page.waitForTimeout(5000);

  // Check page title
  const title = await page.title();
  console.log(`[${mode}] Page title: "${title}"`);

  // Check if dark class is present on html
  const hasDarkClass = await page.evaluate(() => document.documentElement.classList.contains('dark'));
  console.log(`[${mode}] html.dark class present: ${hasDarkClass}`);

  // Check localStorage theme
  const storedTheme = await page.evaluate(() => localStorage.getItem('learnforge.settings.theme'));
  console.log(`[${mode}] localStorage theme: ${storedTheme}`);

  // Try to find and click the English workspace button
  const btnSelectors = [
    'text=英语工作区',
    'text=English',
    '[data-testid="english-workspace-btn"]',
    'button:has-text("英语")',
  ];

  let clicked = false;
  for (const sel of btnSelectors) {
    try {
      const btn = await page.$(sel);
      if (btn) {
        console.log(`[${mode}] Found button with selector "${sel}", clicking...`);
        await btn.click();
        clicked = true;
        break;
      }
    } catch (e) {
      // continue
    }
  }

  if (!clicked) {
    console.log(`[${mode}] No English workspace button found. Trying to find any buttons...`);
    const allButtons = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('button, [role="button"], a'))
        .slice(0, 20)
        .map(el => ({ tag: el.tagName, text: el.textContent?.trim()?.slice(0, 60), class: el.className?.slice(0, 80) }));
    });
    console.log(`[${mode}] Available buttons:`, JSON.stringify(allButtons, null, 2));
  }

  await page.waitForTimeout(2000);

  // Check if English workspace is visible
  const hasEW = await page.evaluate(() => {
    return {
      workspace: !!document.querySelector('.english-workspace'),
      fissionGraph: !!document.querySelector('.fission-graph-container'),
      wordList: !!document.querySelector('.word-list-container'),
      wordDetail: !!document.querySelector('.word-detail-panel'),
    };
  });
  console.log(`[${mode}] English workspace elements:`, JSON.stringify(hasEW));

  const path = `${OUT}/${mode}_english.png`;
  await page.screenshot({ path, fullPage: false });
  console.log(`[${mode}] Screenshot saved: ${path}`);

  await browser.close();
  console.log(`[${mode}] Done.`);
}

try {
  await shoot('dark');
  await shoot('light');
  console.log('All screenshots complete!');
} catch (err) {
  console.error('Script error:', err.message);
  console.error(err.stack);
  process.exit(1);
}
