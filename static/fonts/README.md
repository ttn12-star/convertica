# Self-Hosted Fonts

## 📁 Current Structure

```
static/fonts/
├── inter/                         # Inter font family (body text)
│   ├── inter-v13-latin_cyrillic-regular.woff2    # 400 weight
│   ├── inter-v13-latin_cyrillic-500.woff2        # 500 weight (medium)
│   ├── inter-v13-latin_cyrillic-600.woff2        # 600 weight (semibold)
│   └── inter-v13-latin_cyrillic-700.woff2        # 700 weight (bold)
│
├── poppins/                       # Poppins font family (headings)
│   ├── poppins-v20-latin-regular.woff2           # 400 weight
│   ├── poppins-v20-latin-500.woff2               # 500 weight (medium)
│   ├── poppins-v20-latin-600.woff2               # 600 weight (semibold)
│   └── poppins-v20-latin-700.woff2               # 700 weight (bold)
│
└── README.md
```

## 🔽 Download Fonts

Use the provided script:

```bash
./scripts/download_fonts.sh
```

Or re-download with force:

```bash
./scripts/download_fonts.sh --force
```

The script downloads fonts from [google-webfonts-helper](https://gwfh.mranftl.com/fonts).

## 🎯 Why Self-Hosted?

| Metric | Google Fonts CDN | Self-Hosted |
|--------|-----------------|-------------|
| DNS Lookup | ~50ms | 0ms |
| SSL Handshake | ~100ms | 0ms |
| GDPR | ⚠️ IP tracked | ✅ No tracking |
| Offline | ❌ | ✅ Works |
| **Total FCP Improvement** | - | **~300ms** |

## 📊 File Sizes

- **Inter** (Latin + Cyrillic): ~29KB per weight
- **Poppins** (Latin only): ~8KB per weight
- **Total**: ~148KB for all 8 files

## ✅ After Changes

1. Run collectstatic:
   ```bash
   python manage.py collectstatic --noinput
   ```

2. Verify in browser DevTools Network tab:
   - ✅ Fonts load from your domain
   - ❌ No requests to fonts.googleapis.com
   - ❌ No requests to fonts.gstatic.com

## 📝 CSS Reference

Fonts are loaded via `/static/css/fonts.css`:

```css
@font-face {
  font-family: 'Inter';
  font-weight: 400;
  font-display: swap;
  src: url('../fonts/inter/inter-v13-latin_cyrillic-regular.woff2') format('woff2');
}
```
