from django.urls import path
from . import views


urlpatterns = [
    path('', views.index_page, name='index_page'),
    path('all-tools/', views.all_tools_page, name='all_tools_page'),
    path('pdf-to-word/', views.pdf_to_word_page, name='pdf_to_word_page'),
    path('word-to-pdf/', views.word_to_pdf_page, name='word_to_pdf_page'),
    path('pdf-to-jpg/', views.pdf_to_jpg_page, name='pdf_to_jpg_page'),
    path('jpg-to-pdf/', views.jpg_to_pdf_page, name='jpg_to_pdf_page'),
    path('pdf-to-excel/', views.pdf_to_excel_page, name='pdf_to_excel_page'),
    # PDF Edit pages
    path('pdf-edit/rotate/', views.rotate_pdf_page, name='rotate_pdf_page'),
    path('pdf-edit/add-page-numbers/', views.add_page_numbers_page, name='add_page_numbers_page'),
    path('pdf-edit/add-watermark/', views.add_watermark_page, name='add_watermark_page'),
    path('pdf-edit/crop/', views.crop_pdf_page, name='crop_pdf_page'),
    # PDF Organize pages
    path('pdf-organize/merge/', views.merge_pdf_page, name='merge_pdf_page'),
    path('pdf-organize/split/', views.split_pdf_page, name='split_pdf_page'),
    path('pdf-organize/remove-pages/', views.remove_pages_page, name='remove_pages_page'),
    path('pdf-organize/extract-pages/', views.extract_pages_page, name='extract_pages_page'),
    path('pdf-organize/organize/', views.organize_pdf_page, name='organize_pdf_page'),
    path('pdf-organize/compress/', views.compress_pdf_page, name='compress_pdf_page'),
    # PDF Security pages
    path('pdf-security/protect/', views.protect_pdf_page, name='protect_pdf_page'),
    path('pdf-security/unlock/', views.unlock_pdf_page, name='unlock_pdf_page'),
]
