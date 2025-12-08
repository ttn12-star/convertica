"""
Django management command to add translations to existing articles.
"""

from django.core.management.base import BaseCommand
from src.blog.models import Article


class Command(BaseCommand):
    help = "Add translations to existing articles for all supported languages"

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS("Starting to add translations to articles...")
        )

        articles = Article.objects.all()
        total = articles.count()

        if total == 0:
            self.stdout.write(self.style.WARNING("No articles found in database."))
            return

        self.stdout.write(f"Found {total} article(s) to process.")

        # Translation data for articles
        translations_data = {
            "ultimate-guide-pdf-compression-reduce-file-size": {
                "ru": {
                    "title": "Полное руководство по сжатию PDF: Как уменьшить размер файла без потери качества",
                    "content": """<h2>Введение в сжатие PDF</h2>
<p>PDF файлы часто занимают много места на диске, особенно если они содержат изображения или графику. Сжатие PDF позволяет уменьшить размер файла, сохраняя при этом качество документа.</p>

<h2>Методы сжатия PDF</h2>
<p>Существует несколько методов сжатия PDF файлов:</p>
<ul>
<li><strong>Сжатие изображений:</strong> Уменьшение разрешения и качества изображений в документе</li>
<li><strong>Оптимизация шрифтов:</strong> Удаление неиспользуемых шрифтов и встраивание только необходимых</li>
<li><strong>Сжатие контента:</strong> Применение алгоритмов сжатия к тексту и графике</li>
<li><strong>Удаление метаданных:</strong> Очистка документа от ненужной информации</li>
</ul>

<h2>Как использовать наш инструмент</h2>
<p>Наш бесплатный онлайн-инструмент для сжатия PDF позволяет быстро и легко уменьшить размер ваших файлов:</p>
<ol>
<li>Загрузите PDF файл</li>
<li>Выберите уровень сжатия (низкий, средний, высокий)</li>
<li>Нажмите "Сжать PDF"</li>
<li>Скачайте оптимизированный файл</li>
</ol>

<h2>Советы по сжатию</h2>
<p>Для достижения наилучших результатов:</p>
<ul>
<li>Используйте средний уровень сжатия для большинства документов</li>
<li>Высокий уровень сжатия может незначительно снизить качество изображений</li>
<li>Проверьте результат перед использованием в важных проектах</li>
</ul>

<h2>Заключение</h2>
<p>Сжатие PDF - это простой способ сэкономить место на диске и ускорить отправку файлов по электронной почте. Наш инструмент делает этот процесс быстрым и удобным.</p>""",
                    "excerpt": "Узнайте, как уменьшить размер PDF файлов без потери качества. Полное руководство по сжатию PDF с практическими советами и рекомендациями.",
                    "meta_title": "Сжатие PDF: Как уменьшить размер файла без потери качества | Convertica",
                    "meta_description": "Бесплатный онлайн-инструмент для сжатия PDF. Уменьшите размер файлов быстро и легко. Сохраните качество документа при максимальном сжатии.",
                    "meta_keywords": "сжатие PDF, уменьшить размер PDF, оптимизация PDF, сжать PDF онлайн, бесплатно",
                },
                "pl": {
                    "title": "Kompletny przewodnik po kompresji PDF: Jak zmniejszyć rozmiar pliku bez utraty jakości",
                    "content": """<h2>Wprowadzenie do kompresji PDF</h2>
<p>Pliki PDF często zajmują dużo miejsca na dysku, zwłaszcza jeśli zawierają obrazy lub grafikę. Kompresja PDF pozwala zmniejszyć rozmiar pliku, zachowując jakość dokumentu.</p>

<h2>Metody kompresji PDF</h2>
<p>Istnieje kilka metod kompresji plików PDF:</p>
<ul>
<li><strong>Kompresja obrazów:</strong> Zmniejszenie rozdzielczości i jakości obrazów w dokumencie</li>
<li><strong>Optymalizacja czcionek:</strong> Usunięcie nieużywanych czcionek i osadzenie tylko niezbędnych</li>
<li><strong>Kompresja treści:</strong> Zastosowanie algorytmów kompresji do tekstu i grafiki</li>
<li><strong>Usunięcie metadanych:</strong> Oczyszczenie dokumentu z niepotrzebnych informacji</li>
</ul>

<h2>Jak korzystać z naszego narzędzia</h2>
<p>Nasze darmowe narzędzie online do kompresji PDF pozwala szybko i łatwo zmniejszyć rozmiar plików:</p>
<ol>
<li>Prześlij plik PDF</li>
<li>Wybierz poziom kompresji (niski, średni, wysoki)</li>
<li>Kliknij "Kompresuj PDF"</li>
<li>Pobierz zoptymalizowany plik</li>
</ol>

<h2>Wskazówki dotyczące kompresji</h2>
<p>Aby uzyskać najlepsze wyniki:</p>
<ul>
<li>Użyj średniego poziomu kompresji dla większości dokumentów</li>
<li>Wysoki poziom kompresji może nieznacznie obniżyć jakość obrazów</li>
<li>Sprawdź wynik przed użyciem w ważnych projektach</li>
</ul>

<h2>Podsumowanie</h2>
<p>Kompresja PDF to prosty sposób na oszczędzenie miejsca na dysku i przyspieszenie wysyłania plików e-mailem. Nasze narzędzie czyni ten proces szybkim i wygodnym.</p>""",
                    "excerpt": "Dowiedz się, jak zmniejszyć rozmiar plików PDF bez utraty jakości. Kompletny przewodnik po kompresji PDF z praktycznymi wskazówkami i zaleceniami.",
                    "meta_title": "Kompresja PDF: Jak zmniejszyć rozmiar pliku bez utraty jakości | Convertica",
                    "meta_description": "Darmowe narzędzie online do kompresji PDF. Zmniejsz rozmiar plików szybko i łatwo. Zachowaj jakość dokumentu przy maksymalnej kompresji.",
                    "meta_keywords": "kompresja PDF, zmniejszyć rozmiar PDF, optymalizacja PDF, kompresować PDF online, za darmo",
                },
                "hi": {
                    "title": "PDF संपीड़न की पूरी गाइड: गुणवत्ता खोए बिना फ़ाइल आकार कैसे कम करें",
                    "content": """<h2>PDF संपीड़न का परिचय</h2>
<p>PDF फ़ाइलें अक्सर डिस्क पर बहुत स्थान लेती हैं, खासकर यदि उनमें छवियां या ग्राफिक्स हैं। PDF संपीड़न फ़ाइल के आकार को कम करने की अनुमति देता है, दस्तावेज़ की गुणवत्ता को बनाए रखते हुए।</p>

<h2>PDF संपीड़न के तरीके</h2>
<p>PDF फ़ाइलों को संपीड़ित करने के कई तरीके हैं:</p>
<ul>
<li><strong>छवि संपीड़न:</strong> दस्तावेज़ में छवियों के रिज़ॉल्यूशन और गुणवत्ता को कम करना</li>
<li><strong>फ़ॉन्ट अनुकूलन:</strong> अप्रयुक्त फ़ॉन्ट हटाना और केवल आवश्यक फ़ॉन्ट एम्बेड करना</li>
<li><strong>सामग्री संपीड़न:</strong> पाठ और ग्राफिक्स पर संपीड़न एल्गोरिदम लागू करना</li>
<li><strong>मेटाडेटा हटाना:</strong> दस्तावेज़ को अनावश्यक जानकारी से साफ करना</li>
</ul>

<h2>हमारे उपकरण का उपयोग कैसे करें</h2>
<p>हमारा मुफ्त ऑनलाइन PDF संपीड़न उपकरण आपको अपनी फ़ाइलों के आकार को जल्दी और आसानी से कम करने की अनुमति देता है:</p>
<ol>
<li>PDF फ़ाइल अपलोड करें</li>
<li>संपीड़न स्तर चुनें (कम, मध्यम, उच्च)</li>
<li>"PDF संपीड़ित करें" पर क्लिक करें</li>
<li>अनुकूलित फ़ाइल डाउनलोड करें</li>
</ol>

<h2>संपीड़न युक्तियाँ</h2>
<p>सर्वोत्तम परिणामों के लिए:</p>
<ul>
<li>अधिकांश दस्तावेज़ों के लिए मध्यम संपीड़न स्तर का उपयोग करें</li>
<li>उच्च संपीड़न स्तर छवियों की गुणवत्ता को थोड़ा कम कर सकता है</li>
<li>महत्वपूर्ण परियोजनाओं में उपयोग करने से पहले परिणाम जांचें</li>
</ul>

<h2>निष्कर्ष</h2>
<p>PDF संपीड़न डिस्क स्थान बचाने और ईमेल द्वारा फ़ाइलें भेजने में तेजी लाने का एक सरल तरीका है। हमारा उपकरण इस प्रक्रिया को तेज़ और सुविधाजनक बनाता है।</p>""",
                    "excerpt": "जानें कि गुणवत्ता खोए बिना PDF फ़ाइलों के आकार को कैसे कम करें। व्यावहारिक युक्तियों और सिफारिशों के साथ PDF संपीड़न की पूरी गाइड।",
                    "meta_title": "PDF संपीड़न: गुणवत्ता खोए बिना फ़ाइल आकार कैसे कम करें | Convertica",
                    "meta_description": "मुफ्त ऑनलाइन PDF संपीड़न उपकरण। फ़ाइल आकार को जल्दी और आसानी से कम करें। अधिकतम संपीड़न पर दस्तावेज़ गुणवत्ता बनाए रखें।",
                    "meta_keywords": "PDF संपीड़न, PDF आकार कम करें, PDF अनुकूलन, PDF ऑनलाइन संपीड़ित करें, मुफ्त",
                },
                "es": {
                    "title": "Guía completa de compresión PDF: Cómo reducir el tamaño del archivo sin perder calidad",
                    "content": """<h2>Introducción a la compresión PDF</h2>
<p>Los archivos PDF a menudo ocupan mucho espacio en disco, especialmente si contienen imágenes o gráficos. La compresión PDF permite reducir el tamaño del archivo manteniendo la calidad del documento.</p>

<h2>Métodos de compresión PDF</h2>
<p>Existen varios métodos para comprimir archivos PDF:</p>
<ul>
<li><strong>Compresión de imágenes:</strong> Reducir la resolución y calidad de las imágenes en el documento</li>
<li><strong>Optimización de fuentes:</strong> Eliminar fuentes no utilizadas e incrustar solo las necesarias</li>
<li><strong>Compresión de contenido:</strong> Aplicar algoritmos de compresión al texto y gráficos</li>
<li><strong>Eliminación de metadatos:</strong> Limpiar el documento de información innecesaria</li>
</ul>

<h2>Cómo usar nuestra herramienta</h2>
<p>Nuestra herramienta gratuita en línea para comprimir PDF le permite reducir rápidamente el tamaño de sus archivos:</p>
<ol>
<li>Suba el archivo PDF</li>
<li>Seleccione el nivel de compresión (bajo, medio, alto)</li>
<li>Haga clic en "Comprimir PDF"</li>
<li>Descargue el archivo optimizado</li>
</ol>

<h2>Consejos de compresión</h2>
<p>Para obtener los mejores resultados:</p>
<ul>
<li>Use el nivel medio de compresión para la mayoría de documentos</li>
<li>El nivel alto de compresión puede reducir ligeramente la calidad de las imágenes</li>
<li>Verifique el resultado antes de usar en proyectos importantes</li>
</ul>

<h2>Conclusión</h2>
<p>La compresión PDF es una forma sencilla de ahorrar espacio en disco y acelerar el envío de archivos por correo electrónico. Nuestra herramienta hace que este proceso sea rápido y conveniente.</p>""",
                    "excerpt": "Aprenda cómo reducir el tamaño de los archivos PDF sin perder calidad. Guía completa de compresión PDF con consejos prácticos y recomendaciones.",
                    "meta_title": "Compresión PDF: Cómo reducir el tamaño del archivo sin perder calidad | Convertica",
                    "meta_description": "Herramienta gratuita en línea para comprimir PDF. Reduzca el tamaño de archivos rápida y fácilmente. Mantenga la calidad del documento con máxima compresión.",
                    "meta_keywords": "comprimir PDF, reducir tamaño PDF, optimización PDF, comprimir PDF en línea, gratis",
                },
                "id": {
                    "title": "Panduan Lengkap Kompresi PDF: Cara Mengurangi Ukuran File Tanpa Kehilangan Kualitas",
                    "content": """<h2>Pengenalan Kompresi PDF</h2>
<p>File PDF sering memakan banyak ruang disk, terutama jika berisi gambar atau grafik. Kompresi PDF memungkinkan Anda mengurangi ukuran file sambil mempertahankan kualitas dokumen.</p>

<h2>Metode Kompresi PDF</h2>
<p>Ada beberapa metode untuk mengompres file PDF:</p>
<ul>
<li><strong>Kompresi gambar:</strong> Mengurangi resolusi dan kualitas gambar dalam dokumen</li>
<li><strong>Optimasi font:</strong> Menghapus font yang tidak digunakan dan menyematkan hanya yang diperlukan</li>
<li><strong>Kompresi konten:</strong> Menerapkan algoritma kompresi ke teks dan grafik</li>
<li><strong>Penghapusan metadata:</strong> Membersihkan dokumen dari informasi yang tidak perlu</li>
</ul>

<h2>Cara Menggunakan Alat Kami</h2>
<p>Alat online gratis kami untuk mengompres PDF memungkinkan Anda dengan cepat dan mudah mengurangi ukuran file Anda:</p>
<ol>
<li>Unggah file PDF</li>
<li>Pilih tingkat kompresi (rendah, sedang, tinggi)</li>
<li>Klik "Kompres PDF"</li>
<li>Unduh file yang dioptimalkan</li>
</ol>

<h2>Tips Kompresi</h2>
<p>Untuk hasil terbaik:</p>
<ul>
<li>Gunakan tingkat kompresi sedang untuk sebagian besar dokumen</li>
<li>Tingkat kompresi tinggi mungkin sedikit mengurangi kualitas gambar</li>
<li>Periksa hasilnya sebelum digunakan dalam proyek penting</li>
</ul>

<h2>Kesimpulan</h2>
<p>Kompresi PDF adalah cara sederhana untuk menghemat ruang disk dan mempercepat pengiriman file melalui email. Alat kami membuat proses ini cepat dan nyaman.</p>""",
                    "excerpt": "Pelajari cara mengurangi ukuran file PDF tanpa kehilangan kualitas. Panduan lengkap kompresi PDF dengan tips praktis dan rekomendasi.",
                    "meta_title": "Kompresi PDF: Cara Mengurangi Ukuran File Tanpa Kehilangan Kualitas | Convertica",
                    "meta_description": "Alat online gratis untuk mengompres PDF. Kurangi ukuran file dengan cepat dan mudah. Pertahankan kualitas dokumen dengan kompresi maksimal.",
                    "meta_keywords": "kompres PDF, kurangi ukuran PDF, optimasi PDF, kompres PDF online, gratis",
                },
            },
            "complete-guide-pdf-to-word-conversion": {
                "ru": {
                    "title": "Полное руководство по конвертации PDF в Word: Советы, трюки и лучшие практики",
                    "content": """<h2>Введение в конвертацию PDF в Word</h2>
<p>Конвертация PDF в Word - это процесс преобразования PDF документов в редактируемые файлы Microsoft Word. Это полезно, когда вам нужно внести изменения в документ или извлечь текст.</p>

<h2>Зачем конвертировать PDF в Word?</h2>
<p>Есть несколько причин для конвертации PDF в Word:</p>
<ul>
<li><strong>Редактирование:</strong> PDF файлы обычно не редактируются, а Word документы можно легко изменять</li>
<li><strong>Извлечение текста:</strong> Быстрое извлечение текста из PDF для использования в других документах</li>
<li><strong>Форматирование:</strong> Сохранение форматирования для дальнейшего редактирования</li>
<li><strong>Совместная работа:</strong> Удобство совместной работы над документом</li>
</ul>

<h2>Как использовать наш инструмент</h2>
<p>Наш бесплатный онлайн-конвертер PDF в Word прост в использовании:</p>
<ol>
<li>Загрузите PDF файл</li>
<li>Дождитесь обработки</li>
<li>Скачайте готовый Word документ</li>
</ol>

<h2>Советы по конвертации</h2>
<p>Для лучших результатов:</p>
<ul>
<li>Используйте PDF файлы с четким текстом</li>
<li>Избегайте сканированных документов (они могут требовать OCR)</li>
<li>Проверьте результат после конвертации</li>
<li>Сохраните оригинальный PDF на случай необходимости</li>
</ul>

<h2>Заключение</h2>
<p>Конвертация PDF в Word открывает множество возможностей для работы с документами. Наш инструмент делает этот процесс быстрым и эффективным.</p>""",
                    "excerpt": "Узнайте, как конвертировать PDF в Word быстро и эффективно. Полное руководство с практическими советами и рекомендациями.",
                    "meta_title": "PDF в Word: Полное руководство по конвертации | Convertica",
                    "meta_description": "Бесплатный онлайн-конвертер PDF в Word. Конвертируйте PDF документы в редактируемые Word файлы быстро и легко.",
                    "meta_keywords": "PDF в Word, конвертер PDF, PDF в DOCX, конвертировать PDF, онлайн конвертер",
                },
                "pl": {
                    "title": "Kompletny przewodnik konwersji PDF na Word: Wskazówki, triki i najlepsze praktyki",
                    "content": """<h2>Wprowadzenie do konwersji PDF na Word</h2>
<p>Konwersja PDF na Word to proces przekształcania dokumentów PDF w edytowalne pliki Microsoft Word. Jest to przydatne, gdy chcesz wprowadzić zmiany w dokumencie lub wyodrębnić tekst.</p>

<h2>Dlaczego konwertować PDF na Word?</h2>
<p>Istnieje kilka powodów konwersji PDF na Word:</p>
<ul>
<li><strong>Edycja:</strong> Pliki PDF zazwyczaj nie są edytowalne, a dokumenty Word można łatwo modyfikować</li>
<li><strong>Wyodrębnianie tekstu:</strong> Szybkie wyodrębnianie tekstu z PDF do użycia w innych dokumentach</li>
<li><strong>Formatowanie:</strong> Zachowanie formatowania do dalszej edycji</li>
<li><strong>Współpraca:</strong> Wygoda wspólnej pracy nad dokumentem</li>
</ul>

<h2>Jak korzystać z naszego narzędzia</h2>
<p>Nasz darmowy konwerter online PDF na Word jest łatwy w użyciu:</p>
<ol>
<li>Prześlij plik PDF</li>
<li>Poczekaj na przetworzenie</li>
<li>Pobierz gotowy dokument Word</li>
</ol>

<h2>Wskazówki dotyczące konwersji</h2>
<p>Dla najlepszych wyników:</p>
<ul>
<li>Użyj plików PDF z wyraźnym tekstem</li>
<li>Unikaj zeskanowanych dokumentów (mogą wymagać OCR)</li>
<li>Sprawdź wynik po konwersji</li>
<li>Zachowaj oryginalny PDF na wypadek potrzeby</li>
</ul>

<h2>Podsumowanie</h2>
<p>Konwersja PDF na Word otwiera wiele możliwości pracy z dokumentami. Nasze narzędzie czyni ten proces szybkim i efektywnym.</p>""",
                    "excerpt": "Dowiedz się, jak konwertować PDF na Word szybko i efektywnie. Kompletny przewodnik z praktycznymi wskazówkami i zaleceniami.",
                    "meta_title": "PDF na Word: Kompletny przewodnik konwersji | Convertica",
                    "meta_description": "Darmowy konwerter online PDF na Word. Konwertuj dokumenty PDF na edytowalne pliki Word szybko i łatwo.",
                    "meta_keywords": "PDF na Word, konwerter PDF, PDF na DOCX, konwertować PDF, konwerter online",
                },
                "hi": {
                    "title": "PDF से Word रूपांतरण की पूरी गाइड: युक्तियाँ, ट्रिक्स और सर्वोत्तम प्रथाएं",
                    "content": """<h2>PDF से Word रूपांतरण का परिचय</h2>
<p>PDF से Word रूपांतरण PDF दस्तावेज़ों को संपादन योग्य Microsoft Word फ़ाइलों में बदलने की प्रक्रिया है। यह तब उपयोगी होता है जब आपको दस्तावेज़ में परिवर्तन करने या पाठ निकालने की आवश्यकता होती है।</p>

<h2>PDF को Word में क्यों बदलें?</h2>
<p>PDF को Word में बदलने के कई कारण हैं:</p>
<ul>
<li><strong>संपादन:</strong> PDF फ़ाइलें आमतौर पर संपादन योग्य नहीं होती हैं, जबकि Word दस्तावेज़ों को आसानी से संशोधित किया जा सकता है</li>
<li><strong>पाठ निष्कर्षण:</strong> अन्य दस्तावेज़ों में उपयोग के लिए PDF से पाठ का त्वरित निष्कर्षण</li>
<li><strong>फ़ॉर्मेटिंग:</strong> आगे के संपादन के लिए फ़ॉर्मेटिंग बनाए रखना</li>
<li><strong>सहयोग:</strong> दस्तावेज़ पर सहयोग करने की सुविधा</li>
</ul>

<h2>हमारे उपकरण का उपयोग कैसे करें</h2>
<p>हमारा मुफ्त ऑनलाइन PDF से Word कनवर्टर उपयोग करने में आसान है:</p>
<ol>
<li>PDF फ़ाइल अपलोड करें</li>
<li>प्रसंस्करण की प्रतीक्षा करें</li>
<li>तैयार Word दस्तावेज़ डाउनलोड करें</li>
</ol>

<h2>रूपांतरण युक्तियाँ</h2>
<p>सर्वोत्तम परिणामों के लिए:</p>
<ul>
<li>स्पष्ट पाठ के साथ PDF फ़ाइलें उपयोग करें</li>
<li>स्कैन किए गए दस्तावेज़ों से बचें (उन्हें OCR की आवश्यकता हो सकती है)</li>
<li>रूपांतरण के बाद परिणाम जांचें</li>
<li>आवश्यकता के मामले में मूल PDF सहेजें</li>
</ul>

<h2>निष्कर्ष</h2>
<p>PDF से Word रूपांतरण दस्तावेज़ों के साथ काम करने के लिए कई संभावनाएं खोलता है। हमारा उपकरण इस प्रक्रिया को तेज़ और कुशल बनाता है।</p>""",
                    "excerpt": "जानें कि PDF को Word में कैसे जल्दी और कुशलता से बदलें। व्यावहारिक युक्तियों और सिफारिशों के साथ पूरी गाइड।",
                    "meta_title": "PDF से Word: रूपांतरण की पूरी गाइड | Convertica",
                    "meta_description": "मुफ्त ऑनलाइन PDF से Word कनवर्टर। PDF दस्तावेज़ों को संपादन योग्य Word फ़ाइलों में जल्दी और आसानी से बदलें।",
                    "meta_keywords": "PDF से Word, PDF कनवर्टर, PDF से DOCX, PDF बदलें, ऑनलाइन कनवर्टर",
                },
                "es": {
                    "title": "Guía completa de conversión PDF a Word: Consejos, trucos y mejores prácticas",
                    "content": """<h2>Introducción a la conversión PDF a Word</h2>
<p>La conversión de PDF a Word es el proceso de transformar documentos PDF en archivos editables de Microsoft Word. Es útil cuando necesita hacer cambios en un documento o extraer texto.</p>

<h2>¿Por qué convertir PDF a Word?</h2>
<p>Hay varias razones para convertir PDF a Word:</p>
<ul>
<li><strong>Edición:</strong> Los archivos PDF generalmente no son editables, mientras que los documentos Word se pueden modificar fácilmente</li>
<li><strong>Extracción de texto:</strong> Extracción rápida de texto de PDF para usar en otros documentos</li>
<li><strong>Formato:</strong> Mantener el formato para edición posterior</li>
<li><strong>Colaboración:</strong> Facilidad de colaboración en documentos</li>
</ul>

<h2>Cómo usar nuestra herramienta</h2>
<p>Nuestro convertidor gratuito en línea de PDF a Word es fácil de usar:</p>
<ol>
<li>Suba el archivo PDF</li>
<li>Espere el procesamiento</li>
<li>Descargue el documento Word listo</li>
</ol>

<h2>Consejos de conversión</h2>
<p>Para mejores resultados:</p>
<ul>
<li>Use archivos PDF con texto claro</li>
<li>Evite documentos escaneados (pueden requerir OCR)</li>
<li>Verifique el resultado después de la conversión</li>
<li>Guarde el PDF original por si acaso</li>
</ul>

<h2>Conclusión</h2>
<p>La conversión de PDF a Word abre muchas posibilidades para trabajar con documentos. Nuestra herramienta hace que este proceso sea rápido y eficiente.</p>""",
                    "excerpt": "Aprenda cómo convertir PDF a Word rápida y eficientemente. Guía completa con consejos prácticos y recomendaciones.",
                    "meta_title": "PDF a Word: Guía completa de conversión | Convertica",
                    "meta_description": "Convertidor gratuito en línea de PDF a Word. Convierta documentos PDF en archivos Word editables rápida y fácilmente.",
                    "meta_keywords": "PDF a Word, convertidor PDF, PDF a DOCX, convertir PDF, convertidor en línea",
                },
                "id": {
                    "title": "Panduan Lengkap Konversi PDF ke Word: Tips, Trik, dan Praktik Terbaik",
                    "content": """<h2>Pengenalan Konversi PDF ke Word</h2>
<p>Konversi PDF ke Word adalah proses mengubah dokumen PDF menjadi file Microsoft Word yang dapat diedit. Ini berguna ketika Anda perlu membuat perubahan pada dokumen atau mengekstrak teks.</p>

<h2>Mengapa Mengonversi PDF ke Word?</h2>
<p>Ada beberapa alasan untuk mengonversi PDF ke Word:</p>
<ul>
<li><strong>Pengeditan:</strong> File PDF biasanya tidak dapat diedit, sementara dokumen Word dapat dengan mudah dimodifikasi</li>
<li><strong>Ekstraksi teks:</strong> Ekstraksi teks cepat dari PDF untuk digunakan dalam dokumen lain</li>
<li><strong>Pemformatan:</strong> Mempertahankan pemformatan untuk pengeditan lebih lanjut</li>
<li><strong>Kolaborasi:</strong> Kemudahan kolaborasi pada dokumen</li>
</ul>

<h2>Cara Menggunakan Alat Kami</h2>
<p>Konverter online gratis kami dari PDF ke Word mudah digunakan:</p>
<ol>
<li>Unggah file PDF</li>
<li>Tunggu pemrosesan</li>
<li>Unduh dokumen Word yang siap</li>
</ol>

<h2>Tips Konversi</h2>
<p>Untuk hasil terbaik:</p>
<ul>
<li>Gunakan file PDF dengan teks yang jelas</li>
<li>Hindari dokumen yang dipindai (mungkin memerlukan OCR)</li>
<li>Periksa hasilnya setelah konversi</li>
<li>Simpan PDF asli untuk berjaga-jaga</li>
</ul>

<h2>Kesimpulan</h2>
<p>Konversi PDF ke Word membuka banyak kemungkinan untuk bekerja dengan dokumen. Alat kami membuat proses ini cepat dan efisien.</p>""",
                    "excerpt": "Pelajari cara mengonversi PDF ke Word dengan cepat dan efisien. Panduan lengkap dengan tips praktis dan rekomendasi.",
                    "meta_title": "PDF ke Word: Panduan Lengkap Konversi | Convertica",
                    "meta_description": "Konverter online gratis PDF ke Word. Konversi dokumen PDF menjadi file Word yang dapat diedit dengan cepat dan mudah.",
                    "meta_keywords": "PDF ke Word, konverter PDF, PDF ke DOCX, konversi PDF, konverter online",
                },
            },
        }

        for article in articles:
            self.stdout.write(f"\nProcessing: {article.slug}")

            if article.slug in translations_data:
                article_translations = translations_data[article.slug]

                # Get or create translations dict
                if not article.translations:
                    article.translations = {}

                # Add translations for each language
                for lang_code, lang_data in article_translations.items():
                    if lang_code not in article.translations:
                        article.translations[lang_code] = {}

                    # Update translations
                    article.translations[lang_code].update(lang_data)
                    self.stdout.write(f"  ✓ Added {lang_code} translation")

                # Save article
                article.save()
                self.stdout.write(
                    self.style.SUCCESS(f"  ✓ Saved translations for {article.slug}")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"  ⚠ No translation data found for {article.slug}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(f"\n✅ Completed! Processed {total} article(s).")
        )
