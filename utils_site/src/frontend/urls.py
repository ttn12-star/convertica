from django.urls import path
from . import views


urlpatterns = [
    path('', views.index_page, name='index_page'),
    path('pdf-to-word/', views.pdf_to_word_page, name='pdf_to_word_page'),
    path('word-to-pdf/', views.word_to_pdf_page, name='word_to_pdf_page'),
]
