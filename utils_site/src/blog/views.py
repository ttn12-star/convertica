"""Views for blog application."""

from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.utils.translation import get_language
from django.views.decorators.cache import cache_page

from .models import Article, ArticleCategory


def article_list(request):
    """Display list of published articles."""
    language_code = get_language()

    # Get published articles with optimized queries
    articles = (
        Article.objects.filter(status="published")
        .select_related("category")
        .order_by("-published_at", "-created_at")
    )

    # Filter by category if provided
    category_slug = request.GET.get("category")
    if category_slug:
        category = get_object_or_404(ArticleCategory, slug=category_slug)
        articles = articles.filter(category=category)
    else:
        category = None

    # Search - search in English fields and translations JSON
    # Cache search results for 5 minutes to reduce database load
    search_query = request.GET.get("q", "").strip()
    if search_query:
        # Create cache key for search results
        search_cache_key = f'article_search:{language_code}:{category_slug or "all"}:{search_query[:50]}'
        cached_results = cache.get(search_cache_key)
        if cached_results is not None:
            articles = cached_results
        else:
            # Search in base English fields
            base_query = (
                Q(title_en__icontains=search_query)
                | Q(content_en__icontains=search_query)
                | Q(excerpt_en__icontains=search_query)
            )

            # Get articles matching English search
            articles_list = list(articles.filter(base_query))
            article_ids_found = {a.id for a in articles_list}

            # Also search in translations for current language
            # Optimize: only load id, translations, published_at, created_at for search
            if language_code != "en" and language_code in [
                "ru",
                "pl",
                "hi",
                "es",
                "id",
            ]:
                # Get all articles (respecting category filter if any) - only load needed fields
                all_articles = (
                    Article.objects.filter(status="published")
                    .only(
                        "id",
                        "translations",
                        "published_at",
                        "created_at",
                        "category_id",
                    )
                    .select_related("category")
                )
                if category:
                    all_articles = all_articles.filter(category=category)

                search_lower = search_query.lower()

                # Check translations for each article (batch processing)
                # Limit to first 1000 articles to prevent memory issues
                # Collect IDs first, then batch load to avoid N+1 queries
                translation_match_ids = []
                for article in all_articles[:1000]:
                    if article.id in article_ids_found:
                        continue  # Already found in English search

                    # Check if translation exists and contains search query
                    if article.translations and language_code in article.translations:
                        trans = article.translations[language_code]

                        # Search in translated title, content, excerpt
                        if (
                            trans.get("title", "").lower().find(search_lower) != -1
                            or trans.get("content", "").lower().find(search_lower) != -1
                            or trans.get("excerpt", "").lower().find(search_lower) != -1
                        ):
                            translation_match_ids.append(article.id)
                            article_ids_found.add(article.id)

                # Batch load all matching articles in one query (fixes N+1)
                if translation_match_ids:
                    full_articles = Article.objects.filter(
                        id__in=translation_match_ids
                    ).select_related("category")
                    articles_list.extend(full_articles)

                # Sort by published_at (newest first) and convert to list for pagination
                articles_list.sort(
                    key=lambda x: (
                        (x.published_at or x.created_at)
                        if (x.published_at or x.created_at)
                        else x.id
                    ),
                    reverse=True,
                )
                articles = articles_list
            else:
                articles = articles.filter(base_query)

            # Cache search results for 5 minutes
            cache.set(search_cache_key, articles, 3600)  # Cache for 1 hour

    # Pagination - 9 articles per page (3 columns x 3 rows)
    # Paginator works with both QuerySet and list
    paginator = Paginator(articles, 9)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Get categories for sidebar (cached)
    categories_cache_key = f"article_categories:{language_code}"
    categories = cache.get(categories_cache_key)
    if categories is None:
        categories = ArticleCategory.objects.all()
        cache.set(categories_cache_key, categories, 3600)  # Cache for 1 hour

    context = {
        "page_obj": page_obj,
        "articles": page_obj,
        "categories": categories,
        "current_category": category,
        "search_query": search_query,
        "language_code": language_code,
        "page_title": "Blog - Convertica",
        "page_description": "Read our articles about PDF tools, document conversion tips, and useful guides.",
    }

    return render(request, "blog/article_list.html", context)


@cache_page(600)  # Cache for 10 minutes
def article_detail(request, slug):
    """Display single article."""
    language_code = get_language()

    # Get article with optimized query
    article = get_object_or_404(
        Article.objects.select_related("category"), slug=slug, status="published"
    )

    # Increment view count (async, non-blocking)
    article.increment_view_count()

    # Get related articles (same category, excluding current, ordered by published date)
    # Optimized with select_related
    related_articles = (
        Article.objects.filter(category=article.category, status="published")
        .exclude(id=article.id)
        .select_related("category")
        .order_by("-published_at", "-created_at")[:3]
    )

    # If not enough articles in same category, get latest articles
    if len(related_articles) < 3:
        additional = (
            Article.objects.filter(status="published")
            .exclude(id=article.id)
            .exclude(id__in=[a.id for a in related_articles])
            .select_related("category")
            .order_by("-published_at", "-created_at")[: 3 - len(related_articles)]
        )
        related_articles = list(related_articles) + list(additional)

    # Get categories for sidebar (cached)
    categories_cache_key = f"article_categories:{language_code}"
    categories = cache.get(categories_cache_key)
    if categories is None:
        categories = ArticleCategory.objects.all()
        cache.set(categories_cache_key, categories, 3600)  # Cache for 1 hour

    # Get meta information based on language
    meta_title = article.get_meta_title(language_code)
    meta_description = article.get_meta_description(language_code)
    meta_keywords = article.get_meta_keywords(language_code)

    context = {
        "article": article,
        "related_articles": related_articles,
        "categories": categories,
        "language_code": language_code,
        "page_title": meta_title or article.get_title(language_code),
        "page_description": meta_description,
        "page_keywords": meta_keywords,
        "meta_title": meta_title,
        "meta_description": meta_description,
        "meta_keywords": meta_keywords,
    }

    return render(request, "blog/article_detail.html", context)
