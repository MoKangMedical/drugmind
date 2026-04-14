import { spawn } from 'node:child_process';
import { copyFile, mkdir, rm } from 'node:fs/promises';
import { createRequire } from 'node:module';
import path from 'node:path';
import process from 'node:process';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');

const projectRoot = process.cwd();
const frontendDir = path.join(projectRoot, 'frontend');
const mediaDir = path.join(frontendDir, 'media');
const outputDir = path.join(projectRoot, 'output', 'playwright', 'demo-reel-video');
const serverPort = 8124;
const viewport = { width: 1600, height: 900 };
const pageUrl = `http://127.0.0.1:${serverPort}/demo-reel.html?record=1`;
const posterPath = path.join(mediaDir, 'drugmind-demo-poster.png');
const webmPath = path.join(mediaDir, 'drugmind-demo.webm');

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForServer() {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    try {
      const response = await fetch(pageUrl, { cache: 'no-store' });
      if (response.ok) return;
    } catch (error) {
      // Keep polling until the static server is ready.
    }
    await wait(500);
  }
  throw new Error('Static demo server did not start in time');
}

async function ensureCleanOutput() {
  await mkdir(outputDir, { recursive: true });
  await mkdir(mediaDir, { recursive: true });
  await rm(outputDir, { recursive: true, force: true });
  await mkdir(outputDir, { recursive: true });
}

async function renderVideo() {
  await ensureCleanOutput();

  const server = spawn('python3', ['-m', 'http.server', String(serverPort), '-d', frontendDir], {
    cwd: projectRoot,
    stdio: ['ignore', 'pipe', 'pipe'],
  });

  server.stdout.on('data', () => {});
  server.stderr.on('data', () => {});

  try {
    await waitForServer();

    const browser = await chromium.launch({
      channel: 'chrome',
      headless: true,
      args: ['--autoplay-policy=no-user-gesture-required'],
    });

    const context = await browser.newContext({
      viewport,
      recordVideo: {
        dir: outputDir,
        size: viewport,
      },
      colorScheme: 'dark',
      deviceScaleFactor: 1,
    });

    const page = await context.newPage();
    await page.goto(pageUrl, { waitUntil: 'networkidle' });
    const totalDurationMs = await page.evaluate(() => window.DRUGMIND_DEMO?.totalDurationMs || 24000);

    await page.waitForTimeout(Math.floor(totalDurationMs * 0.72));
    await page.screenshot({ path: posterPath });
    await page.waitForTimeout(Math.max(totalDurationMs - Math.floor(totalDurationMs * 0.72) + 900, 900));

    const video = page.video();
    await page.close();
    await context.close();
    await browser.close();

    const recordedPath = await video.path();
    await copyFile(recordedPath, webmPath);

    return { totalDurationMs, recordedPath };
  } finally {
    server.kill('SIGINT');
  }
}

try {
  const result = await renderVideo();
  console.log(JSON.stringify({
    status: 'ok',
    totalDurationMs: result.totalDurationMs,
    webm: webmPath,
    poster: posterPath,
  }, null, 2));
} catch (error) {
  console.error(error);
  process.exitCode = 1;
}
