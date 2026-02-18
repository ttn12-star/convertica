# Convertica - Free Online PDF Tools

[![Website](https://img.shields.io/badge/Website-convertica.net-blue)](https://convertica.net)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.2-green.svg)](https://www.djangoproject.com/)

**[Convertica](https://convertica.net)** is a modern web platform for working with PDF files. Built with Django 5.2 and Python 3.12, it provides a comprehensive suite of tools for PDF conversion, editing, organization, and security.

🌐 **Live Site:** [https://convertica.net](https://convertica.net)

## 🌟 Why Convertica?

- 🆓 **100% Free** - All basic PDF tools available for free
- 🔒 **Secure** - Files processed securely, automatically deleted after conversion
- ⚡ **Fast** - Optimized for performance with async processing
- 🌍 **Multilingual** - Available in 7 languages
- 📱 **Responsive** - Works on all devices
- 🎨 **Modern UI** - Beautiful interface built with Tailwind CSS

## 🚀 Features

### 📄 PDF Conversion Tools

All conversion tools available at [convertica.net](https://convertica.net):

1. **[PDF to Word](https://convertica.net/pdf-to-word/)** - Convert PDF to DOCX
   - Preserves formatting and structure
   - Supports complex layouts
   - High-quality text extraction

2. **[Word to PDF](https://convertica.net/word-to-pdf/)** - Convert DOCX to PDF
   - Supports .doc and .docx formats
   - Maintains original formatting
   - Fast conversion with LibreOffice

3. **[PDF to JPG](https://convertica.net/pdf-to-jpg/)** - Convert PDF pages to images
   - Adjustable quality (DPI: 72-600)
   - Select specific pages
   - High-resolution output

4. **[JPG to PDF](https://convertica.net/jpg-to-pdf/)** - Convert images to PDF
   - Multiple images to single PDF
   - Auto-scaling to A4 format
   - Batch processing support

5. **[PDF to Excel](https://convertica.net/pdf-to-excel/)** - Extract tables from PDF
   - Preserves table structure
   - Accurate data extraction

6. **[Excel to PDF](https://convertica.net/excel-to-pdf/)** - Convert spreadsheets to PDF
   - Supports .xls and .xlsx
   - Maintains formatting

7. **[PowerPoint to PDF](https://convertica.net/ppt-to-pdf/)** - Convert presentations to PDF
   - Preserves slides layout
   - Supports .ppt and .pptx

8. **[HTML to PDF](https://convertica.net/html-to-pdf/)** - Convert HTML/URL to PDF
   - Web page to PDF conversion
   - Custom page sizes and margins
   - Powered by Playwright

### ✏️ Редактирование PDF

- **Поворот страниц** - поворот страниц на 90°, 180°, 270°
- **Обрезка PDF** - визуальный редактор для обрезки страниц
- **Добавление номеров страниц** - автоматическая нумерация
- **Добавление водяных знаков** - текстовые и графические водяные знаки с настройкой позиции и прозрачности

### 📚 Организация PDF

- **Объединение PDF** - объединение нескольких PDF в один
- **Разделение PDF** - разделение PDF на отдельные файлы
- **Удаление страниц** - удаление выбранных страниц
- **Извлечение страниц** - извлечение конкретных страниц в новый PDF
- **Организация страниц** - перестановка и реорганизация страниц
- **Сжатие PDF** - уменьшение размера файла с сохранением качества

### 🔒 Безопасность PDF

- **Защита PDF** - установка пароля на PDF
- **Разблокировка PDF** - снятие защиты с PDF (если известен пароль)

## 🌍 Multilingual Support

Available in 7 languages with automatic language detection:
- 🇬🇧 English
- 🇷🇺 Русский (Russian)
- 🇵🇱 Polski (Polish)
- 🇮🇳 हिंदी (Hindi)
- 🇪🇸 Español (Spanish)
- 🇮🇩 Bahasa Indonesia (Indonesian)
- 🇸🇦 العربية (Arabic)

Автоматическое определение языка пользователя, SEO-оптимизированный контент для каждого языка.

### CI Auto-Translation (on demand)

You can trigger bulk translation for all locale files directly from CI by adding `--translate`
or `[translate]` to the commit message on `main`/`develop`.

- Workflow job: `auto-translate` in `.github/workflows/ci.yml`
- Script: `scripts/translate_all_locales.sh`
- Files processed: `locale/*/LC_MESSAGES/django.po` (except `en`)
- Result: updated `.po` files + `compilemessages` run + auto-commit back to the same branch
- Runner behavior: if `/home/n_krivda/learning/po-all/l10n-quality` exists (self-hosted), CI uses it first; otherwise it falls back to GitHub package source.

Required GitHub secrets for translation API:
- `POQT_API_URL` (or `L10N_QUALITY_API_URL`)
- `POQT_API_KEY` (or `L10N_QUALITY_API_KEY`) **or** `POQT_DEV_BYPASS` (or `L10N_QUALITY_DEV_BYPASS`)

If API URL is not configured, CI can start self-hosted `l10n-quality-tool` on the runner (`http://127.0.0.1:18080`) and use dev-bypass automatically.  
For that fallback mode, set at least:
- `AI_PRIMARY_API_KEY` (and optionally `AI_FALLBACK_API_KEY`)

## 📝 Блог и SEO

- **Многоязычный блог** - статьи на всех поддерживаемых языках
- **SEO-оптимизация** - уникальный контент, мета-теги, структурированные данные
- **Категории статей** - организация контента по темам
- **Поиск по блогу** - быстрый поиск статей
- **Sitemap.xml** - автоматическая генерация карты сайта

## 🔒 Безопасность и защита

- **Антиспам защита**:
  - hCaptcha интеграция
  - Honeypot поля
  - Rate limiting по IP
  - Проверка минимального времени между запросами
- **Валидация файлов** - проверка типа, размера, содержимого
- **Защита админ-панели** - IP whitelist, кастомный URL
- **HTTPS ready** - готовность к SSL/TLS
- **CSRF защита** - встроенная защита Django

## 📋 Требования

### Системные требования:
- Python 3.12+
- Django 5.2+
- PostgreSQL 16+ (для production) или SQLite (для development)
- Redis 7+ (для кеширования и Celery)
- Node.js и npm (для Tailwind CSS)

### Системные утилиты:
- **LibreOffice** (для конвертации Word → PDF)
- **Poppler** (для работы с PDF)
- **Tesseract OCR** (для извлечения текста из PDF)

### Установка системных зависимостей:

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y \
    libreoffice \
    poppler-utils \
    tesseract-ocr \
    libtesseract-dev \
    ghostscript
```

**macOS:**
```bash
brew install libreoffice poppler tesseract ghostscript
```

**Windows:**
- Скачайте LibreOffice с https://www.libreoffice.org/download/
- Установите Poppler и Tesseract через Chocolatey или вручную

## 🛠️ Установка и запуск

### 1. Клонирование репозитория
```bash
git clone <repository-url>
cd convertica
```

### 2. Создание виртуального окружения
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# или
venv\Scripts\activate  # Windows
```

### 3. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 4. Настройка окружения
```bash
cp env.example .env
# Отредактируйте .env файл, добавив необходимые настройки
```

### 5. Настройка базы данных
```bash
python manage.py migrate
```

### 6. Создание суперпользователя
```bash
python manage.py createsuperuser
```

### 7. Сборка Tailwind CSS
```bash
npm install
npm run build:css
```

### 8. Сборка статических файлов
```bash
python manage.py collectstatic --noinput
```

### 9. Запуск сервера разработки
```bash
python manage.py runserver
```

Сервер будет доступен по адресу: `http://127.0.0.1:8000`

### 10. Запуск Celery (для асинхронных задач)
```bash
# В отдельном терминале
celery -A utils_site worker -l info
celery -A utils_site beat -l info
```

## 🐳 Docker

Проект полностью готов к контейнеризации. Подробные инструкции см. в [ci/DEPLOYMENT_GUIDE.md](ci/DEPLOYMENT_GUIDE.md).

### Быстрый старт с Docker:
```bash
# Production (с Nginx для статики)
docker compose up -d

# Development
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

Или используйте Makefile:
```bash
make dev          # Запуск development окружения
make build        # Сборка образов
make up          # Запуск production
make down        # Остановка
```

### ⚡ Оптимизация статических файлов

Проект использует **Nginx контейнер** для быстрой отдачи статики:
- ⚡ Статика отдается напрямую Nginx (5-10x быстрее)
- 📦 Gzip сжатие (~70% уменьшение размера)
- 💾 Кеширование на 1 год

**Альтернатива:** WhiteNoise (проще, но медленнее) - можно настроить в `utils_site/settings.py`

## 🔄 CI/CD

Проект использует GitHub Actions для автоматизации разработки:

- ✅ **Lint** - проверка качества кода (flake8, black, isort)
- ✅ **Security** - проверка безопасности (safety, bandit)
- ✅ **Tests** - запуск всех тестов (55 тестов) с coverage
- ✅ **Build** - сборка Docker образов для multi-platform
- ✅ **Deploy** - автоматический деплой (настраивается отдельно)

### Быстрая настройка

1. Добавьте Secrets в GitHub:
   - `DOCKER_USERNAME` - логин Docker Hub
   - `DOCKER_PASSWORD` - пароль Docker Hub

2. Push в репозиторий - CI/CD запустится автоматически!

📖 **Подробная инструкция:** [ci/AUTO_DEPLOY_SETUP.md](ci/AUTO_DEPLOY_SETUP.md)

## 📡 API Endpoints

### Базовый URL
```
http://127.0.0.1:8000/api/
```

### Доступные endpoints:

#### Конвертация
- `POST /api/pdf-to-word/` - PDF → Word
- `POST /api/word-to-pdf/` - Word → PDF
- `POST /api/pdf-to-jpg/` - PDF → JPG
- `POST /api/jpg-to-pdf/` - JPG → PDF
- `POST /api/pdf-to-excel/` - PDF → Excel

#### Редактирование
- `POST /api/pdf-edit/rotate/` - Поворот страниц
- `POST /api/pdf-edit/crop/` - Обрезка PDF
- `POST /api/pdf-edit/add-page-numbers/` - Добавление номеров страниц
- `POST /api/pdf-edit/add-watermark/` - Добавление водяного знака

#### Организация
- `POST /api/pdf-organize/merge/` - Объединение PDF
- `POST /api/pdf-organize/split/` - Разделение PDF
- `POST /api/pdf-organize/remove-pages/` - Удаление страниц
- `POST /api/pdf-organize/extract-pages/` - Извлечение страниц
- `POST /api/pdf-organize/organize/` - Организация страниц
- `POST /api/pdf-organize/compress/` - Сжатие PDF

#### Безопасность
- `POST /api/pdf-security/protect/` - Защита PDF паролем
- `POST /api/pdf-security/unlock/` - Разблокировка PDF

### Примеры использования

#### cURL
```bash
# PDF → Word
curl -X POST http://127.0.0.1:8000/api/pdf-to-word/ \
  -F "pdf_file=@document.pdf" \
  -o output.docx

# Объединение PDF
curl -X POST http://127.0.0.1:8000/api/pdf-organize/merge/ \
  -F "pdf_files=@file1.pdf" \
  -F "pdf_files=@file2.pdf" \
  -o merged.pdf
```

#### Python (requests)
```python
import requests

# PDF → Word
with open('document.pdf', 'rb') as f:
    response = requests.post(
        'http://127.0.0.1:8000/api/pdf-to-word/',
        files={'pdf_file': f}
    )
    if response.status_code == 200:
        with open('output.docx', 'wb') as out:
            out.write(response.content)
```

## 📊 Swagger документация

После запуска сервера, Swagger документация доступна по адресу:
```
http://127.0.0.1:8000/swagger/
```

## ⚙️ Настройки

Основные настройки находятся в `utils_site/settings.py` и `.env` файле:

```python
# Максимальный размер загружаемого файла
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB

# Таймаут конвертации
CONVERSION_TIMEOUT = 600  # 10 минут

# Настройки DPI для PDF → JPG
DEFAULT_DPI = 300
MAX_DPI = 600
MIN_DPI = 72

# hCaptcha (Anti-spam)
HCAPTCHA_SITE_KEY = 'your-site-key'
HCAPTCHA_SECRET_KEY = 'your-secret-key'

# Rate Limiting
API_RATE_LIMIT = {
    'default': '100/m',
    'pdf_conversion': '20/m',
    'file_upload': '30/m',
}
```

## 📝 Логирование

Проект использует структурированное логирование с поддержкой UTF-8.

Логи сохраняются в:
- `logs/convertica.log` - все логи
- `logs/errors.log` - только ошибки

## 🧪 Тестирование

```bash
# Запуск всех тестов
python manage.py test

# Запуск тестов конкретного модуля
python manage.py test src.api.tests
```

## 🏗️ Структура проекта

```
convertica/
├── utils_site/              # Django проект
│   ├── src/
│   │   ├── api/             # API endpoints
│   │   │   ├── pdf_convert/ # Конвертация PDF
│   │   │   ├── pdf_edit/    # Редактирование PDF
│   │   │   ├── pdf_organize/# Организация PDF
│   │   │   ├── pdf_security/# Безопасность PDF
│   │   │   ├── base_views.py
│   │   │   ├── spam_protection.py  # Антиспам защита
│   │   │   └── ...
│   │   ├── blog/            # Блог приложение
│   │   │   ├── models.py    # Модели статей
│   │   │   ├── views.py     # Представления
│   │   │   └── ...
│   │   ├── frontend/        # Frontend приложение
│   │   │   ├── views.py     # Страницы
│   │   │   ├── middleware.py # Автоопределение языка
│   │   │   └── ...
│   │   └── exceptions.py    # Кастомные исключения
│   ├── settings.py
│   └── urls.py
├── templates/               # HTML шаблоны
│   ├── base.html
│   ├── frontend/            # Frontend шаблоны
│   └── blog/                # Блог шаблоны
├── static/                  # Статические файлы
│   ├── css/                 # CSS файлы
│   └── js/                  # JavaScript файлы
├── locale/                  # Переводы (i18n)
├── logs/                    # Логи приложения
├── ci/                      # Документация по деплою и CI/CD
│   ├── DEPLOYMENT_GUIDE.md  # Полное руководство по деплою
│   ├── DEPLOYMENT_QUICK_START.md  # Быстрый старт
│   ├── AUTO_DEPLOY_SETUP.md # Настройка CI/CD
│   ├── Dockerfile           # Docker образ приложения
│   └── nginx.Dockerfile     # Docker образ Nginx
├── Dockerfile               # Docker образ
├── docker-compose.yml       # Production compose
├── docker-compose.dev.yml   # Development compose
├── Makefile                 # Команды управления
├── requirements.txt         # Python зависимости
└── package.json             # Node.js зависимости
```

## 🚀 Деплой в production

Полная инструкция по деплою доступна в [ci/DEPLOYMENT_GUIDE.md](ci/DEPLOYMENT_GUIDE.md).

### Рекомендуемые платформы:
- **DigitalOcean App Platform** (⭐ рекомендуется для начала)
- **Railway** (отлично для Docker)
- **Render** (бесплатный тариф)
- **AWS / Google Cloud / Azure** (для крупных проектов)

### Быстрый чеклист:
1. Купите домен
2. Настройте базу данных (PostgreSQL)
3. Настройте Redis
4. Настройте переменные окружения
5. Задеплойте приложение
6. Настройте DNS и SSL

## 🔒 Безопасность

- ✅ Валидация типов файлов (по расширению и MIME-типу)
- ✅ Проверка размера файлов
- ✅ Санитизация имен файлов
- ✅ Обработка временных файлов с автоматической очисткой
- ✅ Антиспам защита (hCaptcha, honeypot, rate limiting)
- ✅ Защита админ-панели (IP whitelist, кастомный URL)
- ✅ Детальное логирование для аудита
- ✅ CSRF защита
- ✅ Rate limiting

## 🐛 Обработка ошибок

API возвращает понятные сообщения об ошибках:

- `400 Bad Request` - невалидный файл, неподдерживаемый формат
- `413 Request Entity Too Large` - файл слишком большой
- `429 Too Many Requests` - превышен лимит запросов
- `500 Internal Server Error` - ошибка сервера при конвертации

## 📈 Производительность и масштабирование

- ✅ Кеширование (Redis) - страницы, категории, поиск
- ✅ Асинхронная обработка (Celery) - для тяжелых операций
- ✅ Оптимизация запросов (select_related, only)
- ✅ Rate limiting - защита от перегрузки
- ✅ Мониторинг производительности
- ✅ Готовность к горизонтальному масштабированию

## 🔄 CI/CD

Проект использует GitHub Actions для автоматизации разработки:

- ✅ **Lint** - проверка качества кода (flake8, black, isort)
- ✅ **Security** - проверка безопасности (safety, bandit)
- ✅ **Tests** - запуск всех тестов (55 тестов) с coverage
- ✅ **Build** - сборка Docker образов для multi-platform (amd64, arm64)
- ✅ **Deploy** - автоматический деплой (настраивается отдельно)

### Быстрая настройка

1. Добавьте Secrets в GitHub:
   - `DOCKER_USERNAME` - логин Docker Hub
   - `DOCKER_PASSWORD` - пароль Docker Hub

2. Push в репозиторий - CI/CD запустится автоматически!

📖 **Подробная инструкция:** [ci/AUTO_DEPLOY_SETUP.md](ci/AUTO_DEPLOY_SETUP.md)

## 📄 Лицензия

См. файл [LICENSE](LICENSE)


## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи в `logs/errors.log`
2. Убедитесь, что все системные зависимости установлены
3. Проверьте настройки в `.env` файле
4. Проверьте, что файл не поврежден и соответствует требованиям

## 🔄 Roadmap

- [x] PowerPoint ↔ PDF conversion
- [x] Batch processing API
- [x] HTML to PDF with Playwright
- [x] Premium subscription system
- [ ] OCR improvements for scanned documents
- [ ] PNG, TIFF support for image conversion
- [ ] Cloud storage integration (Google Drive, Dropbox)
- [ ] Mobile apps (iOS, Android)
- [ ] Desktop apps (Electron)
- [ ] Browser extensions (Chrome, Firefox)

## 📚 Documentation

- [ci/DEPLOYMENT_GUIDE.md](ci/DEPLOYMENT_GUIDE.md) - Full deployment guide
- [ci/DEPLOYMENT_QUICK_START.md](ci/DEPLOYMENT_QUICK_START.md) - Quick start guide
- [ci/AUTO_DEPLOY_SETUP.md](ci/AUTO_DEPLOY_SETUP.md) - CI/CD setup
- [ci/PRODUCTION_CHECKLIST.md](ci/PRODUCTION_CHECKLIST.md) - Production checklist

## 🔗 Links

- 🌐 **Website:** [convertica.net](https://convertica.net)
- 📄 **PDF to Word:** [convertica.net/pdf-to-word](https://convertica.net/pdf-to-word/)
- 📄 **Word to PDF:** [convertica.net/word-to-pdf](https://convertica.net/word-to-pdf/)
- 🖼️ **PDF to JPG:** [convertica.net/pdf-to-jpg](https://convertica.net/pdf-to-jpg/)
- 🖼️ **JPG to PDF:** [convertica.net/jpg-to-pdf](https://convertica.net/jpg-to-pdf/)
- 📊 **PDF to Excel:** [convertica.net/pdf-to-excel](https://convertica.net/pdf-to-excel/)
- 🔀 **Merge PDF:** [convertica.net/pdf-organize/merge/](https://convertica.net/pdf-organize/merge/)
- ✂️ **Split PDF:** [convertica.net/pdf-organize/split/](https://convertica.net/pdf-organize/split/)
- 🗜️ **Compress PDF:** [convertica.net/pdf-organize/compress/](https://convertica.net/pdf-organize/compress/)
- 🔒 **Protect PDF:** [convertica.net/pdf-security/protect/](https://convertica.net/pdf-security/protect/)

## 📄 License

Proprietary - All rights reserved

---

<div align="center">

**[Convertica.net](https://convertica.net) - Free Online PDF Tools** 🚀

**22 Free PDF Tools:**

[PDF to Word Converter](https://convertica.net/pdf-to-word/) | [Word to PDF Converter](https://convertica.net/word-to-pdf/) | [PDF to JPG Converter](https://convertica.net/pdf-to-jpg/) | [JPG to PDF Converter](https://convertica.net/jpg-to-pdf/) | [PDF to Excel Converter](https://convertica.net/pdf-to-excel/) | [Excel to PDF Converter](https://convertica.net/excel-to-pdf/) | [PowerPoint to PDF](https://convertica.net/ppt-to-pdf/) | [HTML to PDF](https://convertica.net/html-to-pdf/) | [Merge PDF Files Online](https://convertica.net/pdf-organize/merge/) | [Split PDF Online](https://convertica.net/pdf-organize/split/) | [Compress PDF Online](https://convertica.net/pdf-organize/compress/) | [Rotate PDF Pages](https://convertica.net/pdf-edit/rotate/) | [Crop PDF Online](https://convertica.net/pdf-edit/crop/) | [Add Page Numbers to PDF](https://convertica.net/pdf-edit/add-page-numbers/) | [Add Watermark to PDF](https://convertica.net/pdf-edit/add-watermark/) | [Extract PDF Pages](https://convertica.net/pdf-organize/extract-pages/) | [Remove PDF Pages](https://convertica.net/pdf-organize/remove-pages/) | [Organize PDF Pages](https://convertica.net/pdf-organize/organize/) | [Protect PDF with Password](https://convertica.net/pdf-security/protect/) | [Unlock PDF Online](https://convertica.net/pdf-security/unlock/) | [PDF to HTML Converter](https://convertica.net/pdf-to-html/) | [PDF to PowerPoint](https://convertica.net/pdf-to-ppt/)

Made with ❤️ using Django and Python

</div>
