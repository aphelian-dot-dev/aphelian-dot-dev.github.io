const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');

function pngSize(filename) {
  const image = fs.readFileSync(path.join(root, filename));
  assert.equal(image.subarray(1, 4).toString('ascii'), 'PNG', `${filename} must be a PNG`);
  return {
    width: image.readUInt32BE(16),
    height: image.readUInt32BE(20),
  };
}

test('document head exposes favicon and Apple touch icon assets', () => {
  assert.match(html, /<link rel="icon" href="favicon\.svg" type="image\/svg\+xml">/);
  assert.match(html, /<link rel="icon" href="favicon-32x32\.png" sizes="32x32" type="image\/png">/);
  assert.match(html, /<link rel="apple-touch-icon" href="apple-touch-icon\.png" sizes="180x180">/);
  assert.match(html, /<link rel="manifest" href="site\.webmanifest">/);
  assert.deepEqual(pngSize('favicon-32x32.png'), { width: 32, height: 32 });
  assert.deepEqual(pngSize('apple-touch-icon.png'), { width: 180, height: 180 });
});

test('Open Graph metadata provides an absolute iMessage share preview', () => {
  assert.match(html, /<meta property="og:type" content="website">/);
  assert.match(html, /<meta property="og:url" content="https:\/\/aphelian\.dev\/">/);
  assert.match(html, /<meta property="og:title" content="APHELIAN — The Last Orrery">/);
  assert.match(html, /<meta property="og:image" content="https:\/\/aphelian\.dev\/social-preview\.png">/);
  assert.match(html, /<meta property="og:image:width" content="1200">/);
  assert.match(html, /<meta property="og:image:height" content="630">/);
  assert.match(html, /<meta property="og:image:alt" content="The Little Orrery emblem beside the title APHELIAN — The Last Orrery">/);
  assert.deepEqual(pngSize('social-preview.png'), { width: 1200, height: 630 });
});

test('web app manifest carries Aphelian identity and install icons', () => {
  const manifest = JSON.parse(fs.readFileSync(path.join(root, 'site.webmanifest'), 'utf8'));
  assert.equal(manifest.name, 'APHELIAN — The Last Orrery');
  assert.equal(manifest.short_name, 'Aphelian');
  assert.deepEqual(
    manifest.icons.map(({ src, sizes, type }) => ({ src, sizes, type })),
    [
      { src: 'icon-192.png', sizes: '192x192', type: 'image/png' },
      { src: 'icon-512.png', sizes: '512x512', type: 'image/png' },
    ]
  );
  assert.deepEqual(pngSize('icon-192.png'), { width: 192, height: 192 });
  assert.deepEqual(pngSize('icon-512.png'), { width: 512, height: 512 });
});
