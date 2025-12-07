#!/usr/bin/env python3
"""
Pinecone Management Utility

This script provides easy commands to manage your Pinecone vector database:
- List all meetings
- Delete specific meetings by ID
- View statistics
- Clear test data

Usage:
    python scripts/manage_pinecone.py list
    python scripts/manage_pinecone.py delete meeting_abc12345
    python scripts/manage_pinecone.py stats
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.retrievers.pinecone import PineconeManager
from src.config.settings import Config


def list_meetings():
    """List all meetings stored in Pinecone."""
    print("\n📋 Listing all meetings in Pinecone...\n")
    
    pm = PineconeManager()
    meetings = pm.list_meetings(namespace=Config.PINECONE_NAMESPACE, limit=1000)
    
    if not meetings:
        print("❌ No meetings found in Pinecone.")
        return
    
    print(f"Found {len(meetings)} unique meeting(s):\n")
    print("-" * 80)
    
    for i, meeting in enumerate(meetings, 1):
        print(f"{i}. Meeting ID: {meeting['meeting_id']}")
        print(f"   Title: {meeting.get('meeting_title', 'N/A')}")
        print(f"   Date: {meeting.get('meeting_date', 'N/A')}")
        print(f"   Duration: {meeting.get('meeting_duration', 'N/A')}")
        print(f"   Source File: {meeting.get('source_file', 'N/A')}")
        print(f"   Participants: {', '.join(meeting.get('speaker_mapping', [])) or 'N/A'}")
        print("-" * 80)


def delete_meeting(meeting_id: str):
    """Delete a specific meeting by ID."""
    print(f"\n🗑️  Deleting meeting: {meeting_id}...\n")
    
    # Confirm deletion
    confirm = input(f"⚠️  Are you sure you want to delete '{meeting_id}'? (yes/no): ")
    if confirm.lower() != 'yes':
        print("❌ Deletion cancelled.")
        return
    
    pm = PineconeManager()
    deleted_count = pm.delete_by_meeting_id(meeting_id, namespace=Config.PINECONE_NAMESPACE)
    
    if deleted_count > 0:
        print(f"\n✅ Successfully deleted {deleted_count} vectors for meeting '{meeting_id}'")
    else:
        print(f"\n❌ No vectors found for meeting '{meeting_id}'")


def show_stats():
    """Show Pinecone index statistics."""
    print("\n📊 Pinecone Index Statistics\n")
    
    pm = PineconeManager()
    stats = pm.index.describe_index_stats()
    
    print(f"Index Name: {pm.index_name}")
    print(f"Total Vectors: {stats.total_vector_count}")
    print(f"\nNamespaces:")
    
    for namespace, info in stats.namespaces.items():
        print(f"  - {namespace}: {info.vector_count} vectors")


def clear_namespace():
    """Clear all data from the default namespace."""
    print(f"\n⚠️  WARNING: This will delete ALL data in the '{Config.PINECONE_NAMESPACE}' namespace!\n")
    
    confirm = input("Type 'DELETE ALL' to confirm: ")
    if confirm != 'DELETE ALL':
        print("❌ Operation cancelled.")
        return
    
    pm = PineconeManager()
    pm.delete_namespace(Config.PINECONE_NAMESPACE)
    print(f"\n✅ All data cleared from '{Config.PINECONE_NAMESPACE}' namespace.")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    try:
        if command == "list":
            list_meetings()
        
        elif command == "delete":
            if len(sys.argv) < 3:
                print("❌ Error: Please provide a meeting_id to delete")
                print("Usage: python scripts/manage_pinecone.py delete meeting_abc12345")
                sys.exit(1)
            meeting_id = sys.argv[2]
            delete_meeting(meeting_id)
        
        elif command == "stats":
            show_stats()
        
        elif command == "clear":
            clear_namespace()
        
        else:
            print(f"❌ Unknown command: {command}")
            print(__doc__)
            sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
