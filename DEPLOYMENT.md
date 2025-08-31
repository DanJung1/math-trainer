# Math Trainer Game - Production Deployment Guide

This guide will help you deploy the Math Trainer game with real-time multiplayer duels to production.

## 🚀 **Quick Deploy to Render (Recommended)**

### **1. Prerequisites**
- GitHub account with your code repository
- Render account (free at [render.com](https://render.com))

### **2. Prepare Your Repository**
Make sure your repository contains:
- ✅ `requirements.txt` (with WebSocket dependencies)
- ✅ `render.yaml` (deployment configuration)
- ✅ `config.py` (production configuration)
- ✅ All templates and static files

### **3. Deploy to Render**

1. **Push to GitHub**: Ensure all changes are committed and pushed
2. **Go to Render Dashboard**: [dashboard.render.com](https://dashboard.render.com)
3. **Click "New +"** → **"Blueprint"**
4. **Connect GitHub**: Select your repository
5. **Deploy**: Render will automatically detect the `render.yaml` and deploy

### **4. Set Environment Variables**
In Render dashboard, add these environment variables:
```
FLASK_CONFIG=production
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

### **5. Initialize Database**
After deployment, visit: `https://your-app.onrender.com/setup-db`

## 🔧 **Manual Deployment Steps**

### **Option 1: Render Web Service**

1. **Create Web Service**:
   - **Name**: `math-trainer-game`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn --worker-class eventlet -w 1 app:app`

2. **Add PostgreSQL Database**:
   - **Name**: `math-trainer-db`
   - **Plan**: `Free`

3. **Link Database**: Copy connection string to `DATABASE_URL` environment variable

### **Option 2: Heroku**

1. **Install Heroku CLI**
2. **Create Procfile**:
   ```
   web: gunicorn --worker-class eventlet -w 1 app:app
   ```
3. **Deploy**:
   ```bash
   heroku create your-math-trainer
   heroku addons:create heroku-postgresql:mini
   git push heroku main
   ```

### **Option 3: DigitalOcean App Platform**

1. **Create App**: Connect GitHub repository
2. **Environment**: Python
3. **Build Command**: `pip install -r requirements.txt`
4. **Run Command**: `gunicorn --worker-class eventlet -w 1 app:app`

## 🎯 **WebSocket Configuration**

### **Important Notes**
- **Worker Class**: Must use `eventlet` for WebSocket support
- **Single Worker**: Use `-w 1` to avoid WebSocket connection issues
- **CORS**: WebSocket CORS is configured in the app

### **Gunicorn Configuration**
```bash
gunicorn --worker-class eventlet -w 1 app:app
```

### **Alternative: Use Eventlet Directly**
```python
# In app.py, replace the run command
if __name__ == '__main__':
    import eventlet
    eventlet.monkey_patch()
    socketio.run(app, debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5001)))
```

## 🗄️ **Database Setup**

### **PostgreSQL (Recommended)**
```bash
# Install PostgreSQL dependencies
pip install psycopg2-binary

# Set DATABASE_URL
export DATABASE_URL=postgresql://user:pass@host:port/database
```

### **SQLite (Development)**
```python
# Automatically used in development
SQLALCHEMY_DATABASE_URI = 'sqlite:///math_trainer.db'
```

### **Initialize Tables**
```bash
# Visit the setup route
curl https://your-app.com/setup-db

# Or use the migration script
python migrate_db.py create
```

## 🔒 **Security Configuration**

### **Environment Variables**
```bash
# Required
FLASK_CONFIG=production
SECRET_KEY=your-super-secret-key

# Optional (for Google OAuth)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

### **Production Settings**
- `SESSION_COOKIE_SECURE = False` (set to `True` when HTTPS available)
- `SESSION_COOKIE_HTTPONLY = True`
- `SESSION_COOKIE_SAMESITE = 'Lax'`

## 📱 **Testing WebSocket Functionality**

### **1. Test Connection**
```javascript
// In browser console
const socket = io();
socket.on('connect', () => console.log('Connected!'));
```

### **2. Test Duel Creation**
1. Visit `/duel`
2. Create a new duel
3. Share room code with friend
4. Test real-time gameplay

### **3. Monitor WebSocket Events**
Check browser console and server logs for:
- Connection events
- Room joining
- Answer submissions
- Game state updates

## 🚨 **Common Issues & Solutions**

### **WebSocket Connection Failed**
- **Cause**: CORS or worker configuration
- **Solution**: Ensure `eventlet` worker class and proper CORS settings

### **Database Connection Error**
- **Cause**: Invalid DATABASE_URL or missing dependencies
- **Solution**: Check connection string and install `psycopg2-binary`

### **App Won't Start**
- **Cause**: Missing dependencies or invalid configuration
- **Solution**: Check `requirements.txt` and environment variables

### **WebSocket Events Not Working**
- **Cause**: Multiple workers or incorrect event handling
- **Solution**: Use single worker (`-w 1`) and check event handlers

## 📊 **Performance Optimization**

### **Database Indexes**
The app includes optimized indexes for:
- Leaderboard queries
- User lookups
- Duel management
- Progress tracking

### **WebSocket Optimization**
- Single worker process
- Eventlet async handling
- Efficient room management
- Minimal data transfer

### **Caching Strategy**
Consider implementing Redis for:
- Session storage
- Leaderboard caching
- Duel state caching

## 🔍 **Monitoring & Debugging**

### **Health Check Endpoint**
```
GET /health
Response: {"status": "healthy"}
```

### **Database Status**
```
GET /setup-db
Response: Database initialization status
```

### **Logs**
- Check Render/Heroku logs for errors
- Monitor WebSocket connections
- Track database performance

## 🚀 **Scaling Considerations**

### **For High Traffic**
1. **Multiple Instances**: Use load balancer
2. **Redis**: Centralized session and cache storage
3. **Database**: Consider managed PostgreSQL service
4. **CDN**: For static assets

### **WebSocket Scaling**
- **Sticky Sessions**: Ensure WebSocket connections stay on same instance
- **Redis Adapter**: For SocketIO clustering
- **Load Balancing**: WebSocket-aware load balancer

## 📋 **Deployment Checklist**

- [ ] All code committed to GitHub
- [ ] `requirements.txt` includes WebSocket dependencies
- [ ] `render.yaml` (or equivalent) configured
- [ ] Environment variables set
- [ ] Database created and linked
- [ ] App deployed successfully
- [ ] Database tables initialized (`/setup-db`)
- [ ] WebSocket connection tested
- [ ] Duel mode functionality verified
- [ ] Error monitoring configured

## 🎮 **Testing Multiplayer Features**

### **Local Testing**
1. Run app locally: `python app.py`
2. Open two browser tabs
3. Create duel in one, join in other
4. Test real-time gameplay

### **Production Testing**
1. Deploy to staging environment
2. Test with multiple users
3. Verify WebSocket stability
4. Check database performance

## 📞 **Support & Troubleshooting**

### **Common Commands**
```bash
# Check app status
curl https://your-app.com/health

# Initialize database
curl https://your-app.com/setup-db

# View logs (Render)
# Dashboard → Your App → Logs

# View logs (Heroku)
heroku logs --tail
```

### **Debug Mode**
For development, set:
```bash
export FLASK_CONFIG=development
export FLASK_DEBUG=1
```

The Math Trainer game is now production-ready with full WebSocket support for real-time multiplayer duels! 🎉
