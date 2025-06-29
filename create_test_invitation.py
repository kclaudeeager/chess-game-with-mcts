#!/usr/bin/env python3
"""
Simple script to create a test invitation for manual browser testing
"""
import requests

API_BASE = "http://localhost:8000/api"

def create_test_invitation():
    """Create a test invitation for manual browser testing"""
    print("🎮 Creating test invitation for browser testing...")
    
    # Create invitation
    response = requests.post(f"{API_BASE}/invitation", json={
        "host_name": "Alice",
        "use_rl_engine": False
    })
    
    if response.ok:
        data = response.json()
        invitation_code = data["invitation_code"]
        invitation_url = f"http://localhost:8000?invitation_code={invitation_code}"
        
        print(f"✅ Invitation created!")
        print(f"📋 Invitation Code: {invitation_code}")
        print(f"🔗 Invitation URL: {invitation_url}")
        print()
        print("🔧 Manual Test Instructions:")
        print("1. Open the main page: http://localhost:8000")
        print(f"2. Open the invitation URL in another tab: {invitation_url}")
        print("3. In tab 1: Set name as 'Alice' and create game")
        print("4. In tab 2: Enter name as 'Bob' and join game")
        print("5. Try making moves alternately in both tabs")
        
        return invitation_code, invitation_url
    else:
        print(f"❌ Failed to create invitation: {response.status_code}")
        print(response.text)
        return None, None

if __name__ == "__main__":
    create_test_invitation()
