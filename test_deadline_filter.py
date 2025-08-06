#!/usr/bin/env python3

import requests
import json
from datetime import datetime, timezone

# Test the API with deadline approaching sort
api_url = 'http://localhost:8000/announcements'
params = {
    'page': 1,
    'page_size': 5,
    'sort_by': 'end_date'
}

try:
    response = requests.get(api_url, params=params)
    print(f'Status Code: {response.status_code}')
    
    if response.status_code == 200:
        data = response.json()
        print(f'Total items: {data.get("total_count", 0)}')
        
        # Check first few items to verify filtering
        items = data.get('items', [])
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        print(f'Today: {today}')
        print('\nFirst 5 announcements (마감임박순):')
        
        for i, item in enumerate(items[:5], 1):
            announcement_data = item.get('announcement_data', {})
            end_date = announcement_data.get('end_date', 'N/A')
            title = announcement_data.get('title', 'No title')[:50]
            print(f'{i}. End Date: {end_date} | Title: {title}...')
            
            # Verify that end_date is today or later
            if end_date and end_date != 'N/A':
                is_future = end_date >= today
                print(f'   -> Is future/today: {is_future}')
    else:
        print(f'Error: {response.text}')
        
except Exception as e:
    print(f'Request failed: {e}')