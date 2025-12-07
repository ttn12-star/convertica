"""Management command to create sample articles."""

from django.core.management.base import BaseCommand
from django.utils import timezone
from src.blog.models import Article, ArticleCategory


class Command(BaseCommand):
    help = "Create sample articles for the blog"

    def handle(self, *args, **options):
        # Create category if it doesn't exist
        category, created = ArticleCategory.objects.get_or_create(
            slug="pdf-guides",
            defaults={
                "name_en": "PDF Guides",
                "name_ru": "Руководства по PDF",
                "description_en": "Comprehensive guides and tutorials for working with PDF files",
                "description_ru": "Подробные руководства и учебники по работе с PDF файлами",
            },
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(f"Created category: {category.name_en}")
            )
        else:
            self.stdout.write(f"Using existing category: {category.name_en}")

        # Article 1: PDF to Word Conversion Guide
        article1, created1 = Article.objects.get_or_create(
            slug="complete-guide-pdf-to-word-conversion",
            defaults={
                "title_en": "Complete Guide to PDF to Word Conversion: Tips, Tricks, and Best Practices",
                "title_ru": "",
                "content_en": """<h2>Introduction to PDF to Word Conversion</h2>
<p>Converting PDF files to Word documents is one of the most common document transformation tasks. Whether you need to edit a PDF that was created from a scanned document, extract text for reuse, or modify content that's locked in PDF format, understanding the conversion process is essential.</p>

<h2>Why Convert PDF to Word?</h2>
<p>PDF files are excellent for preserving document formatting and ensuring consistent appearance across different devices. However, they're not designed for easy editing. Converting PDF to Word format offers several advantages:</p>

<ul>
<li><strong>Editability:</strong> Word documents allow you to modify text, change formatting, and update content easily.</li>
<li><strong>Collaboration:</strong> Multiple users can work on Word documents simultaneously using track changes and comments.</li>
<li><strong>Reusability:</strong> Extract and reuse content from PDFs in new documents.</li>
<li><strong>Accessibility:</strong> Word documents are easier to navigate and modify for users with assistive technologies.</li>
</ul>

<h2>Best Practices for PDF to Word Conversion</h2>

<h3>1. Choose the Right Tool</h3>
<p>Select a reliable online converter like Convertica that uses advanced OCR (Optical Character Recognition) technology for scanned documents and maintains formatting accuracy for text-based PDFs.</p>

<h3>2. Prepare Your PDF</h3>
<p>Before converting, ensure your PDF is:</p>
<ul>
<li>Not password-protected (or unlock it first)</li>
<li>Not corrupted or damaged</li>
<li>High quality if it's a scanned document (at least 300 DPI)</li>
</ul>

<h3>3. Review and Edit After Conversion</h3>
<p>Always review the converted document because:</p>
<ul>
<li>Complex layouts may need adjustment</li>
<li>Tables might require reformatting</li>
<li>Images and graphics may need repositioning</li>
<li>Fonts might need to be replaced if not available</li>
</ul>

<h2>Common Conversion Challenges and Solutions</h2>

<h3>Scanned Documents</h3>
<p>Scanned PDFs require OCR technology to extract text. Modern converters can handle this automatically, but results may vary based on scan quality.</p>

<h3>Complex Layouts</h3>
<p>Documents with multiple columns, tables, or intricate formatting may require manual adjustment after conversion.</p>

<h3>Images and Graphics</h3>
<p>Embedded images are usually preserved, but their positioning might need fine-tuning in the Word document.</p>

<h2>Tips for Better Conversion Results</h2>
<ol>
<li>Use high-quality source PDFs whenever possible</li>
<li>Convert one page at a time for complex documents</li>
<li>Check the converted document's formatting immediately</li>
<li>Save your work frequently during editing</li>
<li>Use Word's "Compare Documents" feature to verify accuracy</li>
</ol>

<h2>Conclusion</h2>
<p>PDF to Word conversion is a powerful capability that unlocks the content of PDF files for editing and reuse. By following best practices and using reliable conversion tools, you can achieve excellent results that save time and maintain document quality.</p>

<p>Ready to convert your PDF to Word? Try our free online converter at Convertica - no registration required, instant results, and complete privacy protection.</p>""",
                "content_ru": "",
                "excerpt_en": "Learn everything you need to know about converting PDF files to Word documents. Discover best practices, common challenges, and expert tips for successful conversions.",
                "excerpt_ru": "",
                "category": category,
                "meta_title_en": "PDF to Word Conversion Guide: Complete Tutorial & Best Practices 2025",
                "meta_title_ru": "",
                "meta_description_en": "Master PDF to Word conversion with our comprehensive guide. Learn tips, tricks, and best practices for converting PDF files to editable Word documents. Free online tools included.",
                "meta_description_ru": "",
                "meta_keywords_en": "PDF to Word, convert PDF to Word, PDF conversion guide, PDF to DOCX, edit PDF, PDF converter tutorial, Word document conversion",
                "meta_keywords_ru": "",
                "status": "published",
                "published_at": timezone.now(),
            },
        )

        if created1:
            self.stdout.write(
                self.style.SUCCESS(f"Created article: {article1.title_en}")
            )
        else:
            self.stdout.write(f"Article already exists: {article1.title_en}")

        # Article 2: PDF Compression Guide
        article2, created2 = Article.objects.get_or_create(
            slug="ultimate-guide-pdf-compression-reduce-file-size",
            defaults={
                "title_en": "Ultimate Guide to PDF Compression: How to Reduce File Size Without Losing Quality",
                "title_ru": "",
                "content_en": """<h2>Understanding PDF Compression</h2>
<p>PDF compression is the process of reducing file size while maintaining acceptable quality. This is crucial for email attachments, web uploads, storage optimization, and faster document sharing.</p>

<h2>Why Compress PDF Files?</h2>
<p>Large PDF files can cause numerous problems:</p>
<ul>
<li><strong>Email Limitations:</strong> Most email services limit attachment sizes to 25MB</li>
<li><strong>Slow Uploads:</strong> Large files take longer to upload and download</li>
<li><strong>Storage Issues:</strong> Uncompressed PDFs consume excessive storage space</li>
<li><strong>Performance:</strong> Large files are slower to open and process</li>
</ul>

<h2>How PDF Compression Works</h2>
<p>PDF compression uses various techniques to reduce file size:</p>

<h3>1. Image Compression</h3>
<p>Images often take up the most space in PDF files. Compression reduces image quality slightly while maintaining visual acceptability.</p>

<h3>2. Text Compression</h3>
<p>Text content is compressed using algorithms that remove redundancy without losing information.</p>

<h3>3. Object Optimization</h3>
<p>Removes unused objects, compresses fonts, and optimizes the PDF structure.</p>

<h3>4. Content Stream Compression</h3>
<p>Compresses the actual content streams within the PDF document.</p>

<h2>Compression Levels Explained</h2>

<h3>Low Compression</h3>
<p>Minimal size reduction (5-15%) with maximum quality preservation. Best for documents that require perfect quality.</p>

<h3>Medium Compression</h3>
<p>Balanced approach (20-40% reduction) with good quality. Ideal for most use cases.</p>

<h3>High Compression</h3>
<p>Maximum size reduction (40-70%+) with acceptable quality. Perfect for web sharing and email attachments.</p>

<h2>Best Practices for PDF Compression</h2>

<ol>
<li><strong>Choose the Right Level:</strong> Match compression level to your needs</li>
<li><strong>Test Results:</strong> Always check compressed files for quality</li>
<li><strong>Backup Originals:</strong> Keep original files before compressing</li>
<li><strong>Consider Content:</strong> Text-heavy PDFs compress better than image-heavy ones</li>
<li><strong>Use Professional Tools:</strong> Reliable compressors maintain better quality</li>
</ol>

<h2>When to Compress PDFs</h2>
<ul>
<li>Before emailing large documents</li>
<li>When uploading to websites with size limits</li>
<li>For archiving large document collections</li>
<li>To improve website loading times</li>
<li>For mobile device compatibility</li>
</ul>

<h2>Common Compression Mistakes to Avoid</h2>
<ul>
<li>Over-compressing and losing important details</li>
<li>Not checking compressed file quality</li>
<li>Compressing already compressed files multiple times</li>
<li>Using inappropriate compression for the content type</li>
</ul>

<h2>Advanced Compression Techniques</h2>

<h3>Multi-Pass Compression</h3>
<p>Some advanced tools use multiple compression passes to achieve better results without significant quality loss.</p>

<h3>Selective Compression</h3>
<p>Compress different parts of the document at different levels based on importance.</p>

<h3>Metadata Removal</h3>
<p>Removing unnecessary metadata can reduce file size without affecting content.</p>

<h2>Conclusion</h2>
<p>PDF compression is an essential skill for anyone working with digital documents. By understanding compression levels, techniques, and best practices, you can significantly reduce file sizes while maintaining acceptable quality.</p>

<p>Need to compress a PDF? Try Convertica's free PDF compression tool with multiple compression levels, instant processing, and no file size limits. Compress your PDFs in seconds!</p>""",
                "content_ru": "",
                "excerpt_en": "Discover how to compress PDF files effectively. Learn about compression levels, techniques, and best practices to reduce file size while maintaining quality.",
                "excerpt_ru": "",
                "category": category,
                "meta_title_en": "PDF Compression Guide: Reduce File Size Without Quality Loss 2025",
                "meta_title_ru": "",
                "meta_description_en": "Learn how to compress PDF files effectively. Complete guide to PDF compression levels, techniques, and tools. Reduce file size by up to 70% while maintaining quality.",
                "meta_description_ru": "",
                "meta_keywords_en": "PDF compression, reduce PDF size, compress PDF, PDF file size, PDF optimizer, shrink PDF, PDF compression guide",
                "meta_keywords_ru": "",
                "status": "published",
                "published_at": timezone.now(),
            },
        )

        if created2:
            self.stdout.write(
                self.style.SUCCESS(f"Created article: {article2.title_en}")
            )
        else:
            self.stdout.write(f"Article already exists: {article2.title_en}")

        self.stdout.write(self.style.SUCCESS("Sample articles created successfully!"))
