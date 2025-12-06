# Convertica

**Convertica** - это веб-приложение для конвертации файлов между различными форматами. Проект построен на Django REST Framework и предоставляет RESTful API для конвертации документов и изображений.

## 🚀 Возможности

### Поддерживаемые конвертации:

1. **PDF → Word (DOCX)**
   - Конвертация PDF документов в формат Word
   - Сохранение структуры и форматирования

2. **Word → PDF**
   - Конвертация документов Word (.doc, .docx) в PDF
   - Поддержка старых форматов .doc и современных .docx

3. **PDF → JPG**
   - Конвертация страниц PDF в изображения JPG
   - Настраиваемое качество (DPI: 72-600)
   - Выбор конкретной страницы для конвертации

4. **JPG → PDF**
   - Конвертация изображений JPG/JPEG в PDF документы
   - Автоматическое масштабирование под формат A4

## 📋 Требования

### Системные требования:
- Python 3.8+
- Django 5.2+
- LibreOffice (для конвертации Word → PDF)

### Python зависимости:
Все зависимости перечислены в `requirements.txt`. Установите их командой:
```bash
pip install -r requirements.txt
```

### Установка LibreOffice:
```bash
# Ubuntu/Debian
sudo apt-get install libreoffice

# macOS
brew install --cask libreoffice

# Windows
# Скачайте с https://www.libreoffice.org/download/
```

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

### 4. Настройка базы данных
```bash
python manage.py migrate
```

### 5. Создание суперпользователя (опционально)
```bash
python manage.py createsuperuser
```

### 6. Запуск сервера разработки
```bash
python manage.py runserver
```

Сервер будет доступен по адресу: `http://127.0.0.1:8000`

## 📡 API Endpoints

### Базовый URL
```
http://127.0.0.1:8000/api/
```

### Доступные endpoints:

#### 1. PDF → Word
```
POST /api/pdf-to-word/
Content-Type: multipart/form-data

Body:
- pdf_file: (file) PDF файл для конвертации
```

#### 2. Word → PDF
```
POST /api/word-to-pdf/
Content-Type: multipart/form-data

Body:
- word_file: (file) Word файл (.doc или .docx) для конвертации
```

#### 3. PDF → JPG
```
POST /api/pdf-to-jpg/
Content-Type: multipart/form-data

Body:
- pdf_file: (file) PDF файл для конвертации
- page: (integer, optional) Номер страницы (по умолчанию: 1)
- dpi: (integer, optional) Качество изображения 72-600 (по умолчанию: 300)
```

#### 4. JPG → PDF
```
POST /api/jpg-to-pdf/
Content-Type: multipart/form-data

Body:
- image_file: (file) JPG/JPEG изображение для конвертации
```

## 📖 Примеры использования

### cURL

#### PDF → Word
```bash
curl -X POST http://127.0.0.1:8000/api/pdf-to-word/ \
  -F "pdf_file=@document.pdf" \
  -o output.docx
```

#### Word → PDF
```bash
curl -X POST http://127.0.0.1:8000/api/word-to-pdf/ \
  -F "word_file=@document.docx" \
  -o output.pdf
```

#### PDF → JPG (первая страница, 300 DPI)
```bash
curl -X POST http://127.0.0.1:8000/api/pdf-to-jpg/ \
  -F "pdf_file=@document.pdf" \
  -F "page=1" \
  -F "dpi=300" \
  -o page1.jpg
```

#### JPG → PDF
```bash
curl -X POST http://127.0.0.1:8000/api/jpg-to-pdf/ \
  -F "image_file=@image.jpg" \
  -o output.pdf
```

### Python (requests)

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

# PDF → JPG (страница 2, 600 DPI)
with open('document.pdf', 'rb') as f:
    response = requests.post(
        'http://127.0.0.1:8000/api/pdf-to-jpg/',
        files={'pdf_file': f},
        data={'page': 2, 'dpi': 600}
    )
    if response.status_code == 200:
        with open('page2.jpg', 'wb') as out:
            out.write(response.content)
```

### JavaScript (fetch)

```javascript
// PDF → Word
const formData = new FormData();
formData.append('pdf_file', fileInput.files[0]);

fetch('http://127.0.0.1:8000/api/pdf-to-word/', {
    method: 'POST',
    body: formData
})
.then(response => response.blob())
.then(blob => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'converted.docx';
    a.click();
});
```

## 📊 Swagger документация

После запуска сервера, Swagger документация доступна по адресу:
```
http://127.0.0.1:8000/swagger/
```

## ⚙️ Настройки

Основные настройки находятся в `utils_site/settings.py`:

```python
# Максимальный размер загружаемого файла
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB

# Таймаут конвертации
CONVERSION_TIMEOUT = 600  # 10 минут

# Префикс для временных директорий
TEMP_DIR_PREFIX = "convertica_"

# Настройки DPI для PDF → JPG
DEFAULT_DPI = 300
MAX_DPI = 600
MIN_DPI = 72
```

## 📝 Логирование

Проект использует структурированное логирование. Подробности см. в [README_LOGGING.md](README_LOGGING.md).

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
│   │   │   ├── pdf_to_word/
│   │   │   ├── word_to_pdf/
│   │   │   ├── pdf_to_jpg/
│   │   │   ├── jpg_to_pdf/
│   │   │   ├── base_views.py      # Базовый класс для views
│   │   │   ├── file_validation.py # Валидация файлов
│   │   │   ├── logging_utils.py   # Утилиты логирования
│   │   │   └── urls.py
│   │   ├── exceptions.py    # Кастомные исключения
│   │   └── frontend/        # Frontend приложение
│   ├── settings.py
│   └── urls.py
├── logs/                    # Логи приложения
├── static/                  # Статические файлы
├── templates/               # HTML шаблоны
└── requirements.txt         # Python зависимости
```

## 🔒 Безопасность

- Валидация типов файлов (по расширению и MIME-типу)
- Проверка размера файлов
- Санитизация имен файлов
- Обработка временных файлов с автоматической очисткой
- Детальное логирование для аудита

## 🐛 Обработка ошибок

API возвращает понятные сообщения об ошибках:

- `400 Bad Request` - невалидный файл, неподдерживаемый формат
- `413 Request Entity Too Large` - файл слишком большой
- `500 Internal Server Error` - ошибка сервера при конвертации

## 📄 Лицензия

См. файл [LICENSE](LICENSE)

## 🤝 Вклад в проект

1. Fork проекта
2. Создайте feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit изменения (`git commit -m 'Add some AmazingFeature'`)
4. Push в branch (`git push origin feature/AmazingFeature`)
5. Откройте Pull Request

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи в `logs/errors.log`
2. Убедитесь, что LibreOffice установлен (для Word → PDF)
3. Проверьте, что файл не поврежден и соответствует требованиям

## 🔄 Планы развития

- [ ] Поддержка конвертации Excel ↔ PDF
- [ ] Пакетная конвертация нескольких файлов
- [ ] Асинхронная обработка больших файлов
- [ ] API для конвертации всех страниц PDF в JPG
- [ ] Поддержка других форматов изображений (PNG, TIFF)
