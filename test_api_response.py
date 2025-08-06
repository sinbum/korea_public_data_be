#!/usr/bin/env python3

import sys
import json
from datetime import datetime, timezone

try:
    data = json.load(sys.stdin)
    print('Status:', data.get('success', 'unknown'))
    print('Total Count:', data.get('data', {}).get('total_count', 0))
    
    items = data.get('data', {}).get('items', [])
    print('\nFirst few announcements (마감임박순):')
    
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    print(f'Today: {today}')
    
    for i, item in enumerate(items, 1):
        announcement_data = item.get('announcement_data', {})
        end_date = announcement_data.get('end_date', 'N/A')
        title = announcement_data.get('title', 'No title')[:50]
        print(f'{i}. End Date: {end_date} | Title: {title}...')
        
        if end_date and end_date != 'N/A':
            is_future = end_date >= today
            print(f'   -> Is future/today: {is_future}')
            
except Exception as e:
    print(f'Error: {e}')
    content = sys.stdin.read()
    print('Raw content:', content[:500])