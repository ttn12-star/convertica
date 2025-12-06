# CI/CD and Docker Infrastructure

Эта директория содержит документацию и конфигурацию для CI/CD и Docker.

## Структура

- `README.md` - этот файл
- `DEPLOYMENT.md` - **полная инструкция по деплою в production** (⭐ начните отсюда!)
- `DIGITALOCEAN_DOCKER.md` - ⭐ **Деплой на DigitalOcean с Docker Compose (БД в контейнере)**
- `README_CI.md` - инструкции по настройке CI/CD
- `DOCKER.md` - инструкции по Docker

## Основные файлы (в корне проекта)

- `Dockerfile` - образ Docker для приложения
- `docker-compose.yml` - production конфигурация
- `docker-compose.dev.yml` - development конфигурация
- `.dockerignore` - исключения для Docker build
- `.github/workflows/` - GitHub Actions workflows
- `Makefile` - удобные команды для управления

## Быстрый старт

### Production

```bash
docker-compose up -d
```

### Development

```bash
make dev
```

## Быстрый старт для production

1. **Прочитайте [DEPLOYMENT.md](DEPLOYMENT.md)** - полная инструкция от покупки домена до масштабирования
2. Выберите платформу (рекомендуем DigitalOcean App Platform или Railway)
3. Следуйте пошаговым инструкциям

Подробнее:
- [DEPLOYMENT.md](DEPLOYMENT.md) - деплой в production
- [DIGITALOCEAN_DOCKER.md](DIGITALOCEAN_DOCKER.md) - ⭐ Деплой на DigitalOcean с Docker (БД в контейнере)
- [DOCKER.md](DOCKER.md) - работа с Docker
- [README_CI.md](README_CI.md) - настройка CI/CD

