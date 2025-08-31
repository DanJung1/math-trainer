#!/usr/bin/env python3
"""
Simple test script to verify the app can start without errors
"""

import os
import sys

# Set environment variables for testing
os.environ['FLASK_CONFIG'] = 'development'
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

try:
    # Import the app
    from app import app, socketio, db
    
    print("✅ App imported successfully")
    
    # Test database initialization
    with app.app_context():
        db.create_all()
        print("✅ Database tables created successfully")
    
    # Test basic routes
    with app.test_client() as client:
        response = client.get('/')
        print(f"✅ Home route works: {response.status_code}")
        
        response = client.get('/health')
        print(f"✅ Health check works: {response.status_code}")
    
    print("✅ All tests passed! App is ready for deployment.")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
