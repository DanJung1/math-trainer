#!/usr/bin/env python3
"""
Database migration script for Math Trainer Game
This script helps with database schema updates and production deployments.
"""

import os
import sys
from datetime import datetime

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User, Progress, Analytics, LearningPath, LeaderboardScore

def create_tables():
    """Create all database tables"""
    print("Creating database tables...")
    with app.app_context():
        db.create_all()
        print("✅ Database tables created successfully!")

def drop_tables():
    """Drop all database tables (WARNING: This will delete all data!)"""
    print("⚠️  WARNING: This will delete all data!")
    confirm = input("Are you sure you want to drop all tables? (yes/no): ")
    if confirm.lower() == 'yes':
        with app.app_context():
            db.drop_all()
            print("✅ All tables dropped successfully!")
    else:
        print("❌ Operation cancelled.")

def add_sample_data():
    """Add sample data for testing"""
    print("Adding sample data...")
    with app.app_context():
        # Create sample users
        users = []
        for i in range(1, 6):
            user = User(
                username=f"Player{i}",
                email=f"player{i}@example.com"
            )
            users.append(user)
            db.session.add(user)
        
        db.session.commit()
        print(f"✅ Created {len(users)} sample users")
        
        # Add sample leaderboard scores
        import random
        modes = ['standard', 'marathon']
        for user in users:
            for mode in modes:
                score = LeaderboardScore(
                    user_id=user.id,
                    mode=mode,
                    score=random.randint(10, 100)
                )
                db.session.add(score)
        
        db.session.commit()
        print("✅ Added sample leaderboard scores")

def check_database_status():
    """Check the current status of the database"""
    print("Checking database status...")
    with app.app_context():
        try:
            # Check if tables exist
            tables = db.engine.table_names()
            print(f"📊 Found {len(tables)} tables: {', '.join(tables)}")
            
            # Count records in each table
            user_count = User.query.count()
            progress_count = Progress.query.count()
            analytics_count = Analytics.query.count()
            learning_path_count = LearningPath.query.count()
            leaderboard_count = LeaderboardScore.query.count()
            
            print(f"👥 Users: {user_count}")
            print(f"📈 Progress records: {progress_count}")
            print(f"📊 Analytics records: {analytics_count}")
            print(f"🎯 Learning paths: {learning_path_count}")
            print(f"🏆 Leaderboard scores: {leaderboard_count}")
            
            # Check top scores
            print("\n🏆 Top Scores:")
            for mode in ['standard', 'marathon']:
                top_score = LeaderboardScore.query.filter_by(mode=mode)\
                    .order_by(LeaderboardScore.score.desc())\
                    .first()
                if top_score:
                    print(f"  {mode.capitalize()}: {top_score.score} by {top_score.user.username}")
                else:
                    print(f"  {mode.capitalize()}: No scores yet")
                    
        except Exception as e:
            print(f"❌ Error checking database: {e}")

def backup_database():
    """Create a backup of the current database"""
    import shutil
    from datetime import datetime
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"backup_math_trainer_{timestamp}.db"
    
    if os.path.exists("instance/math_trainer.db"):
        shutil.copy2("instance/math_trainer.db", backup_file)
        print(f"✅ Database backed up to: {backup_file}")
    else:
        print("❌ No database file found to backup")

def main():
    """Main function to handle command line arguments"""
    if len(sys.argv) < 2:
        print("""
Math Trainer Database Migration Tool

Usage:
  python migrate_db.py <command>

Commands:
  create     - Create all database tables
  drop       - Drop all database tables (WARNING: deletes all data!)
  sample     - Add sample data for testing
  status     - Check database status
  backup     - Create a backup of the current database
  reset      - Drop all tables and recreate them (WARNING: deletes all data!)
  full       - Create tables and add sample data
        """)
        return
    
    command = sys.argv[1].lower()
    
    if command == 'create':
        create_tables()
    elif command == 'drop':
        drop_tables()
    elif command == 'sample':
        add_sample_data()
    elif command == 'status':
        check_database_status()
    elif command == 'backup':
        backup_database()
    elif command == 'reset':
        print("⚠️  WARNING: This will delete all data!")
        confirm = input("Are you sure you want to reset the database? (yes/no): ")
        if confirm.lower() == 'yes':
            with app.app_context():
                db.drop_all()
                db.create_all()
                print("✅ Database reset successfully!")
        else:
            print("❌ Operation cancelled.")
    elif command == 'full':
        create_tables()
        add_sample_data()
    else:
        print(f"❌ Unknown command: {command}")
        print("Run without arguments to see available commands.")

if __name__ == "__main__":
    main()
