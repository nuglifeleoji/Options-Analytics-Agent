"""
Test client for Options Microservice
Tests all API endpoints
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health check endpoint"""
    print("\n" + "="*70)
    print("🏥 Testing Health Check...")
    print("="*70)
    
    response = requests.get(f"{BASE_URL}/")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200


def test_search_options():
    """Test search options endpoint"""
    print("\n" + "="*70)
    print("🔍 Testing Search Options...")
    print("="*70)
    
    payload = {
        "ticker": "AAPL",
        "date": "2025-11",
        "limit": 50
    }
    
    print(f"Request: {json.dumps(payload, indent=2)}")
    
    response = requests.post(
        f"{BASE_URL}/api/search_options",
        json=payload
    )
    
    print(f"\nStatus: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success!")
        print(f"   • Found: {data['count']} contracts")
        print(f"   • Total available: {data['total_available']}")
        print(f"   • First contract: {data['results'][0]['ticker'] if data['results'] else 'None'}")
        return data
    else:
        print(f"❌ Error: {response.text}")
        return None


def test_make_csv(options_data):
    """Test CSV generation endpoint"""
    print("\n" + "="*70)
    print("📄 Testing CSV Generation...")
    print("="*70)
    
    if not options_data:
        print("⚠️ Skipping: No options data available")
        return False
    
    payload = {
        "ticker": "AAPL",
        "data": options_data
    }
    
    response = requests.post(
        f"{BASE_URL}/api/make_csv",
        json=payload
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Success!")
        print(f"   • Filename: {result['filename']}")
        print(f"   • Rows: {result['rows']}")
        return True
    else:
        print(f"❌ Error: {response.text}")
        return False


def test_plot_chart(options_data):
    """Test chart generation endpoint"""
    print("\n" + "="*70)
    print("📊 Testing Chart Generation...")
    print("="*70)
    
    if not options_data:
        print("⚠️ Skipping: No options data available")
        return False
    
    payload = {
        "ticker": "AAPL",
        "data": options_data
    }
    
    response = requests.post(
        f"{BASE_URL}/api/plot_chart",
        json=payload
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Success!")
        print(f"   • Filename: {result['filename']}")
        print(f"   • Total Calls: {result['total_calls']}")
        print(f"   • Total Puts: {result['total_puts']}")
        return True
    else:
        print(f"❌ Error: {response.text}")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("🚀 Options Microservice Test Suite")
    print("="*70)
    
    try:
        # Test 1: Health check
        if not test_health():
            print("\n❌ Health check failed! Make sure the service is running.")
            print("Run: cd microservice && docker-compose up -d")
            return
        
        # Test 2: Search options
        options_data = test_search_options()
        
        # Test 3: Generate CSV
        test_make_csv(options_data)
        
        # Test 4: Generate chart
        test_plot_chart(options_data)
        
        # Summary
        print("\n" + "="*70)
        print("✅ ALL TESTS COMPLETED!")
        print("="*70)
        print("\n📝 Check the microservice directory for generated files:")
        print("   • CSV files: *_options_*.csv")
        print("   • Chart files: *_butterfly_*.png")
        
    except requests.ConnectionError:
        print("\n❌ Cannot connect to service!")
        print("Make sure the service is running on http://localhost:8000")
        print("\nTo start the service:")
        print("  cd microservice")
        print("  docker-compose up -d")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")


if __name__ == "__main__":
    main()

