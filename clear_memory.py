"""
Clear conversation memory to fix context length exceeded error.
Author: Leo Ji

This script clears the SQLite conversation history when it gets too long.
"""

import sqlite3
import os

db_path = "data/conversation_memory.db"

if os.path.exists(db_path):
    print(f"🔍 Found database: {db_path}")
    
    # Connect and check size
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get table info
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"📊 Tables: {tables}")
    
    # Count checkpoints
    if tables:
        cursor.execute("SELECT COUNT(*) FROM checkpoints;")
        count = cursor.fetchone()[0]
        print(f"💾 Total checkpoints: {count}")
    
    # Ask for confirmation
    response = input("\n⚠️  Do you want to CLEAR all conversation history? (yes/no): ")
    
    if response.lower() == 'yes':
        # Clear all tables
        try:
            cursor.execute("DELETE FROM checkpoints;")
            print("   ✓ Cleared checkpoints table")
        except Exception as e:
            print(f"   ⚠️  Checkpoints: {e}")
        
        try:
            cursor.execute("DELETE FROM writes;")
            print("   ✓ Cleared writes table")
        except Exception as e:
            print(f"   ⚠️  Writes: {e}")
        
        # Commit and vacuum to reclaim space
        conn.commit()
        cursor.execute("VACUUM;")
        print("   ✓ Database vacuumed")
        
        print("\n✅ Conversation history cleared!")
        print("🔄 Now you can restart search_tools.py")
        print("\n💡 The new session will have:")
        print("   • Automatic context management")
        print("   • Smart message filtering")
        print("   • No orphaned tool messages")
    else:
        print("❌ Operation cancelled.")
    
    conn.close()
else:
    print(f"❌ Database not found: {db_path}")
    print("Nothing to clear.")

