# Math Trainer Game - Production Deployment Guide

This guide will help you deploy the Math Trainer game to production with a proper database-backed leaderboard system.

## 🚀 Quick Start

### 1. Environment Setup

Set the following environment variables for production:

```bash
export FLASK_CONFIG=production
export SECRET_KEY=your-super-secret-production-key
export DATABASE_URL=your-database-url
export GOOGLE_CLIENT_ID=your-google-client-id
export GOOGLE_CLIENT_SECRET=your-google-client-secret
```

### 2. Database Setup

The application uses SQLite by default, but for production, consider using PostgreSQL or MySQL:

#### Option A: PostgreSQL (Recommended)
```bash
# Install PostgreSQL dependencies
pip install psycopg2-binary

# Set database URL
export DATABASE_URL=postgresql://username:password@localhost/mathtrainer
```

#### Option B: MySQL
```bash
# Install MySQL dependencies
pip install mysqlclient

# Set database URL
export DATABASE_URL=mysql://username:password@localhost/mathtrainer
```

#### Option C: SQLite (Simple)
```bash
# Uses local SQLite file (good for small to medium scale)
export DATABASE_URL=sqlite:///math_trainer.db
```

### 3. Database Migration

Run the migration script to set up your database:

```bash
# Create tables
python migrate_db.py create

# Add sample data (optional)
python migrate_db.py sample

# Check database status
python migrate_db.py status
```

## 🏗️ Production Architecture

### Recommended Stack

1. **Web Server**: Nginx or Apache
2. **WSGI Server**: Gunicorn or uWSGI
3. **Database**: PostgreSQL (recommended) or MySQL
4. **Process Manager**: Systemd or Supervisor
5. **SSL**: Let's Encrypt or your preferred SSL provider

### Example Nginx Configuration

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /path/to/your/certificate.crt;
    ssl_certificate_key /path/to/your/private.key;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /path/to/your/app/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### Gunicorn Configuration

Create `gunicorn.conf.py`:

```python
# Gunicorn configuration
bind = "127.0.0.1:8000"
workers = 4
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2
max_requests = 1000
max_requests_jitter = 100
preload_app = True
```

### Systemd Service

Create `/etc/systemd/system/mathtrainer.service`:

```ini
[Unit]
Description=Math Trainer Game
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/your/app
Environment="PATH=/path/to/your/venv/bin"
Environment="FLASK_CONFIG=production"
Environment="DATABASE_URL=your-database-url"
Environment="SECRET_KEY=your-secret-key"
ExecStart=/path/to/your/venv/bin/gunicorn -c gunicorn.conf.py wsgi:app
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always

[Install]
WantedBy=multi-user.target
```

## 🔧 Database Management

### Backup Strategy

Set up automated backups:

```bash
# Create backup script
cat > backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/path/to/backups"
python migrate_db.py backup
cp backup_math_trainer_*.db $BACKUP_DIR/
find $BACKUP_DIR -name "backup_math_trainer_*.db" -mtime +7 -delete
EOF

chmod +x backup.sh

# Add to crontab for daily backups
echo "0 2 * * * /path/to/backup.sh" | crontab -
```

### Database Maintenance

Regular maintenance tasks:

```bash
# Check database status
python migrate_db.py status

# Optimize SQLite database (if using SQLite)
sqlite3 instance/math_trainer.db "VACUUM;"

# For PostgreSQL
psql $DATABASE_URL -c "VACUUM ANALYZE;"
```

## 📊 Performance Optimization

### Database Indexes

The application includes optimized indexes for:
- Leaderboard queries (mode + score)
- User score lookups (user_id + mode)
- Time-based queries (created_at)
- Progress tracking (user_id + operation)
- Analytics (user_id + session_date)

### Caching Strategy

Consider implementing Redis for:
- Session storage
- Leaderboard caching
- Rate limiting

Example Redis configuration:

```python
# Add to requirements.txt
# redis==4.5.0

# In app.py
import redis
redis_client = redis.Redis(host='localhost', port=6379, db=0)

# Cache leaderboard for 5 minutes
def get_cached_leaderboard(mode):
    cache_key = f"leaderboard:{mode}"
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # Fetch from database
    data = fetch_leaderboard_from_db(mode)
    redis_client.setex(cache_key, 300, json.dumps(data))
    return data
```

## 🔒 Security Considerations

### Environment Variables

Never commit sensitive data to version control:

```bash
# .env file (not in git)
FLASK_CONFIG=production
SECRET_KEY=your-super-secret-key
DATABASE_URL=postgresql://user:pass@localhost/db
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

### Rate Limiting

Implement rate limiting to prevent abuse:

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@app.route('/api/submit-score', methods=['POST'])
@limiter.limit("10 per minute")
def submit_score():
    # ... existing code
```

### Input Validation

The application includes:
- Score range validation (0-10000)
- Mode validation (standard/marathon)
- User authentication checks
- SQL injection prevention (SQLAlchemy ORM)

## 📈 Monitoring and Logging

### Application Logging

Configure structured logging:

```python
import logging
from logging.handlers import RotatingFileHandler

if not app.debug:
    file_handler = RotatingFileHandler('logs/mathtrainer.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Math Trainer startup')
```

### Health Checks

Add health check endpoint:

```python
@app.route('/health')
def health_check():
    try:
        # Test database connection
        db.session.execute('SELECT 1')
        return jsonify({'status': 'healthy', 'database': 'connected'})
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500
```

## 🚀 Deployment Checklist

- [ ] Set production environment variables
- [ ] Configure database and run migrations
- [ ] Set up SSL certificates
- [ ] Configure web server (Nginx/Apache)
- [ ] Set up process manager (Systemd/Supervisor)
- [ ] Configure logging and monitoring
- [ ] Set up automated backups
- [ ] Test all functionality
- [ ] Monitor performance and errors

## 🔧 Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Check DATABASE_URL format
   - Verify database server is running
   - Check firewall settings

2. **Google OAuth Issues**
   - Verify redirect URIs in Google Console
   - Check client ID and secret
   - Ensure HTTPS in production

3. **Performance Issues**
   - Check database indexes
   - Monitor query performance
   - Consider caching strategies

### Useful Commands

```bash
# Check application status
systemctl status mathtrainer

# View logs
journalctl -u mathtrainer -f

# Database status
python migrate_db.py status

# Backup database
python migrate_db.py backup
```

## 📞 Support

For issues or questions:
1. Check the logs for error messages
2. Verify environment configuration
3. Test database connectivity
4. Review security settings

The application is designed to be production-ready with proper error handling, logging, and security measures in place.
