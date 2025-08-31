# QuickMath - Math Training Game 🧮

A fun and engaging web-based math training game with Google OAuth authentication and persistent leaderboards. The game helps users improve their mathematical skills through interactive challenges and social features.

## 🔐 Google OAuth Setup

To enable Google Sign-In functionality:

1. **Create a Google Cloud Project**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the Google+ API

2. **Create OAuth 2.0 Credentials**:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth 2.0 Client IDs"
   - Choose "Web application"
   - Add authorized redirect URIs:
     - `http://localhost:5000/callback` (for local development)
     - `https://yourdomain.com/callback` (for production)

3. **Download Credentials**:
   - Download the JSON file
   - Rename it to `client_secret.json`
   - Place it in the root directory of this project

4. **Set Environment Variables** (optional):
   ```bash
   export GOOGLE_CLIENT_ID="your-client-id"
   export GOOGLE_CLIENT_SECRET="your-client-secret"
   ```

## 🎮 Current Features

- **Authentication & User Management**
  - Google OAuth Sign-In
  - User profiles with profile pictures
  - Session management
  - Secure authentication flow

- **Basic Math Operations**
  - Addition
  - Subtraction
  - Multiplication
  - Division
  - Mixed operations

- **Game Modes**
  - Standard Mode: Quick math challenges
  - Training Mode: Focus on specific operations with customizable ranges
  - Marathon Mode: Extended practice sessions
  - ⚔️ **Duel Mode**: Real-time multiplayer battles with WebSocket support

- **Leaderboards & Competition**
  - Persistent high score tracking
  - Global leaderboards for each game mode
  - User ranking system
  - Real-time score updates

- **Game Mechanics**
  - Timed challenges
  - Progressive difficulty levels
  - Score tracking
  - Immediate feedback on answers
  - Clean and intuitive user interface

- **Technical Features**
  - Web-based application with WebSocket support
  - Responsive design for all devices
  - Real-time performance tracking
  - Cross-platform compatibility
  - PostgreSQL/SQLite database support
  - Production-ready deployment configuration

## 🚀 Deployment

### Quick Deploy to Render (Free)
1. **Fork/Clone** this repository to GitHub
2. **Connect to Render**: [dashboard.render.com](https://dashboard.render.com)
3. **Deploy Blueprint**: Render will automatically detect the `render.yaml` configuration
4. **Set Environment Variables**: Add your Google OAuth credentials
5. **Initialize Database**: Visit `/setup-db` after deployment

### Manual Deployment
See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions to:
- Render (recommended)
- Heroku
- DigitalOcean
- AWS/GCP/Azure

### WebSocket Support
The duel mode requires WebSocket support. Ensure your deployment platform supports:
- Persistent connections
- Eventlet worker class
- Single worker process (`-w 1`)

## 🚀 Future Features

### Core Gameplay Enhancements
- [ ] Multiple game modes (Time Attack, Endurance, Practice)
- [ ] Customizable difficulty settings
- [ ] Special challenges and daily missions
- [ ] Achievement system
- [ ] Power-ups and special abilities
- [ ] Different mathematical concepts (Algebra, Geometry, etc.)

### Social Features
- [x] User profiles and statistics
- [x] Global leaderboards
- [x] ⚔️ **Real-time multiplayer duels** (NEW!)
- [ ] Friend system
- [ ] Social sharing of achievements
- [ ] Community challenges and events

### Gamification Elements
- [ ] Experience points and leveling system
- [ ] Virtual currency and rewards
- [ ] Customizable avatars
- [ ] Badges and titles
- [ ] Daily rewards and streaks
- [ ] Seasonal events and special challenges

### Learning Features
- [ ] Detailed progress tracking
- [ ] Personalized learning paths
- [ ] Performance analytics
- [ ] Weakness identification
- [ ] Custom practice sessions
- [ ] Educational content integration

### Technical Improvements
- [ ] Mobile app version
- [ ] Offline mode
- [ ] Performance optimizations
- [ ] Enhanced security features
- [ ] API for third-party integrations
- [ ] Multi-language support

## 🛠️ Technology Stack

- Python
- Flask
- HTML/CSS
- JavaScript
- Heroku (Deployment)

## 🎯 Project Goals

1. Create an engaging and addictive learning experience
2. Build a strong community of math enthusiasts
3. Make mathematics more accessible and enjoyable
4. Provide meaningful progress tracking and feedback
5. Foster healthy competition and social interaction

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

*"Making mathematics fun, one problem at a time!"* 🎯 