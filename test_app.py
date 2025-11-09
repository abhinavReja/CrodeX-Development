"""
Simple test script to verify the Flask application is working
"""
import requests
import json

BASE_URL = "http://localhost:5000"

def test_health_check():
    """Test the health check endpoint"""
    print("🔍 Testing Health Check Endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ Health check passed!")
            print(f"   Response: {response.json()}")
            return True
        else:
            print(f"❌ Health check failed with status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Is the Flask app running?")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_home_page():
    """Test the home page"""
    print("\n🔍 Testing Home Page...")
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            print("✅ Home page accessible!")
            return True
        else:
            print(f"❌ Home page failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_upload_page():
    """Test the upload page"""
    print("\n🔍 Testing Upload Page...")
    try:
        response = requests.get(f"{BASE_URL}/upload")
        if response.status_code == 200:
            print("✅ Upload page accessible!")
            return True
        else:
            print(f"❌ Upload page failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_api_endpoints():
    """Test API endpoints"""
    print("\n🔍 Testing API Endpoints...")
    
    # Test autocomplete endpoint
    try:
        response = requests.get(f"{BASE_URL}/api/autocomplete/description?q=zip")
        if response.status_code == 200:
            print("✅ Autocomplete endpoint working!")
        else:
            print(f"⚠️  Autocomplete endpoint returned status {response.status_code}")
    except Exception as e:
        print(f"⚠️  Autocomplete endpoint error: {e}")

if __name__ == "__main__":
    print("=" * 50)
    print("🧪 Testing CrodeX Flask Application")
    print("=" * 50)
    
    results = []
    results.append(test_health_check())
    results.append(test_home_page())
    results.append(test_upload_page())
    test_api_endpoints()
    
    print("\n" + "=" * 50)
    if all(results):
        print("✅ All basic tests passed!")
    else:
        print("⚠️  Some tests failed. Check the output above.")
    print("=" * 50)

