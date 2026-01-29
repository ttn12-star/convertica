#!/bin/bash
# Обновление SSL сертификатов для Convertica
# Используется с certbot для автоматического обновления

set -e

# Переход в директорию проекта
cd /opt/convertica

# Остановка Nginx контейнера
echo "Остановка Nginx..."
docker compose -f docker-compose.yml -f ci/docker-compose.prod.yml stop nginx

# Обновление сертификатов через certbot
echo "Обновление SSL сертификатов..."
certbot renew --quiet

# Копирование новых сертификатов в директорию для Docker
echo "Копирование сертификатов..."
cp -L /etc/letsencrypt/live/convertica.net/fullchain.pem /opt/convertica/ssl/fullchain.pem
cp -L /etc/letsencrypt/live/convertica.net/privkey.pem /opt/convertica/ssl/privkey.pem

# Установка правильных прав доступа
chmod 644 /opt/convertica/ssl/fullchain.pem
chmod 600 /opt/convertica/ssl/privkey.pem

# Запуск Nginx контейнера
echo "Запуск Nginx..."
docker compose -f docker-compose.yml -f ci/docker-compose.prod.yml start nginx

echo "✅ SSL сертификаты успешно обновлены!"
