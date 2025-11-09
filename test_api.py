import requests
import json
from pathlib import Path

BASE_URL = 'http://localhost:5000/api'

def test_full_flow():
    """Test complete API flow"""
    
    # 1. Upload project
    print("1. Uploading project...")
    files = {'file': open('test_project.zip', 'rb')}
    response = requests.post(f'{BASE_URL}/upload', files=files)
    print(f"Response: {response.status_code}")
    upload_data = response.json()
    print(json.dumps(upload_data, indent=2))
    
    project_id = upload_data['project_id']
    
    # 2. Analyze project
    print("\n2. Analyzing project...")
    response = requests.post(f'{BASE_URL}/analyze')
    print(f"Response: {response.status_code}")
    analysis_data = response.json()
    print(json.dumps(analysis_data, indent=2))
    
    # 3. Confirm context
    print("\n3. Confirming context...")
    context = {
        'purpose': 'E-commerce platform',
        'features': ['user authentication', 'shopping cart', 'payment processing'],
        'business_logic': 'Users can browse products, add to cart, and checkout',
        'requirements': ['maintain user sessions', 'secure payment handling']
    }
    response = requests.post(f'{BASE_URL}/confirm-context', json=context)
    print(f"Response: {response.status_code}")
    context_data = response.json()
    print(json.dumps(context_data, indent=2))
    
    # 4. Convert project
    print("\n4. Converting project...")
    conversion_request = {
        'target_framework': 'Django'
    }
    response = requests.post(f'{BASE_URL}/convert', json=conversion_request)
    print(f"Response: {response.status_code}")
    conversion_data = response.json()
    print(json.dumps(conversion_data, indent=2))
    
    # 5. Download result
    print("\n5. Downloading result...")
    response = requests.get(f'{BASE_URL}/download/{project_id}')
    print(f"Response: {response.status_code}")
    
    if response.status_code == 200:
        with open('converted_project.zip', 'wb') as f:
            f.write(response.content)
        print("Downloaded: converted_project.zip")

if __name__ == '__main__':
    test_full_flow()