# 🚀 Deployment Checklist for Convertica

## ⚠️ CRITICAL: Data Loss Prevention

### ❌ NEVER DO THIS:
```bash
# This will DELETE ALL DATA including PostgreSQL database!
docker compose down -v
docker-compose down --volumes
make clean
```

### ✅ SAFE DEPLOYMENT:
```bash
# 1. Pull latest code
git pull origin main

# 2. Rebuild and restart (preserves data)
docker compose down
docker compose build
docker compose up -d

# Or use make command
make rebuild
```

---

## 📊 Database Backup Before Deploy

**Always backup before major changes:**

```bash
# 1. Backup PostgreSQL database
docker compose exec db pg_dump -U convertica convertica > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. Backup operation data
docker compose exec web python manage.py operation_stats --days 365 --export

# 3. Check backup created
ls -lh backup_*.sql
ls -lh logs/operation_stats/
```

---

## 🔍 Post-Deploy Verification

**After every deployment, verify:**

```bash
# 1. Check all containers running
docker compose ps

# 2. Verify database data
docker compose exec web python manage.py shell -c "from src.users.models import OperationRun, SubscriptionPlan; print(f'Operations: {OperationRun.objects.count()}'); print(f'Plans: {SubscriptionPlan.objects.count()}')"

# 3. Check migrations
docker compose exec web python manage.py showmigrations

# 4. Test admin access
curl -I https://convertica.net/admin-1108-convertica-secret/

# 5. Check logs for errors
docker compose logs web --tail 50
docker compose logs celery --tail 50
```

---

## 📦 Volume Management

**Check volumes:**
```bash
# List volumes
docker volume ls | grep convertica

# Inspect volume
docker volume inspect convertica_postgres_data

# NEVER remove volumes in production!
# If you need to reset dev environment:
docker compose -f docker-compose.dev.yml down -v
```

---

## 🔄 Safe Redeploy Process

```bash
# 1. Backup first!
./scripts/backup_database.sh  # Create this script

# 2. Pull latest
git pull origin main

# 3. Stop services (keeps volumes)
docker compose down

# 4. Rebuild
docker compose build

# 5. Start services
docker compose up -d

# 6. Wait for health checks
sleep 30

# 7. Verify data
docker compose exec web python manage.py shell -c "from src.users.models import OperationRun; print('Operations:', OperationRun.objects.count())"

# 8. Check admin
# Open browser: https://convertica.net/admin-1108-convertica-secret/users/operationrun/
```

---

## 🆘 Data Recovery

**If data was lost:**

1. **Check if backup exists:**
   ```bash
   ls -lh backup_*.sql
   ls -lh logs/operation_exports/
   ```

2. **Restore from backup:**
   ```bash
   # Restore PostgreSQL
   cat backup_YYYYMMDD_HHMMSS.sql | docker compose exec -T db psql -U convertica convertica
   ```

3. **If no backup - data is lost permanently**
   - Future operations will be tracked (retention: 365 days)
   - Exports created automatically before cleanup

---

## 📝 Common Issues

### Issue: Admin shows empty after deploy
**Solution:**
1. Clear browser cache (Ctrl + Shift + R)
2. Re-login to admin
3. Check data exists: `docker compose exec web python manage.py operation_stats --days 30`

### Issue: Migrations not applied
**Solution:**
```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py create_subscription_plans
```

### Issue: Containers not starting
**Solution:**
```bash
docker compose logs web
docker compose logs db
docker compose restart web
```

---

## 🎯 Summary

**Golden Rules:**
1. ✅ **NEVER** use `docker compose down -v` in production
2. ✅ **ALWAYS** backup before major changes
3. ✅ **VERIFY** data after deployment
4. ✅ Use `docker compose down` (without -v) for safe restarts
5. ✅ Check operation count after every deploy

**Data Retention:**
- Operations: 365 days (auto-export before deletion)
- Exports: `/app/logs/operation_exports/`
- Statistics: `python manage.py operation_stats`

---

**Last Updated:** 2026-01-03
**Version:** 2.0.11
