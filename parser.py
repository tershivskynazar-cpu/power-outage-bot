import re
import time
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from config import Config

class PowerOnParser:
    def __init__(self):
        self.session = requests.Session()
        
        retry_strategy = Retry(
            total=Config.MAX_RETRIES,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        self.session.headers.update({
            'User-Agent': Config.USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'uk,en-US;q=0.7,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def fetch_page(self) -> Optional[str]:
        if Config.USE_TEST_DATA:
            from test_data import TEST_SCHEDULE_DATA
            return TEST_SCHEDULE_DATA
        
        try:
            response = self.session.get(
                Config.POWERON_URL,
                timeout=Config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            
            # Ensure proper encoding
            response.encoding = response.apparent_encoding or 'utf-8'
            
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"Помилка завантаження сторінки: {e}")
            return None
    
    def parse_schedule(self, html_content: str) -> Dict[str, List[List[str]]]:
        if not html_content:
            return {}
        
        soup = BeautifulSoup(html_content, 'lxml')
        
        schedule_data = {}
        
        text_content = soup.get_text()
        
        group_pattern = r'Група\s+(\d+\.\d+)\.?\s*Електроенергії\s+немає\s+з\s+([^.]*)\.?'
        
        matches = re.findall(group_pattern, text_content, re.IGNORECASE | re.UNICODE)
        
        for group, time_str in matches:
            time_intervals = self._parse_time_intervals(time_str)
            if time_intervals:
                schedule_data[group] = time_intervals
        
        return schedule_data
    
    def _parse_time_intervals(self, time_str: str) -> List[List[str]]:
        intervals = []
        
        time_pattern = r'(\d{1,2}):(\d{2})\s*до\s*(\d{1,2}):(\d{2})'
        
        matches = re.findall(time_pattern, time_str, re.IGNORECASE)
        
        for start_h, start_m, end_h, end_m in matches:
            start_time = f"{int(start_h):02d}:{start_m}"
            end_time = f"{int(end_h):02d}:{end_m}"
            
            if end_time == "24:00":
                end_time = "23:59"
            
            intervals.append([start_time, end_time])
        
        return intervals
    
    def get_group_schedule(self, group: str) -> Optional[List[List[str]]]:
        html_content = self.fetch_page()
        if not html_content:
            return None
        
        schedule_data = self.parse_schedule(html_content)
        return schedule_data.get(group)
    
    def get_all_schedules(self) -> Optional[Dict[str, List[List[str]]]]:
        html_content = self.fetch_page()
        if not html_content:
            return None
        
        return self.parse_schedule(html_content)
    
    def get_available_groups(self) -> List[str]:
        html_content = self.fetch_page()
        if not html_content:
            return []
        
        soup = BeautifulSoup(html_content, 'lxml')
        text_content = soup.get_text()
        
        group_pattern = r'Група\s+(\d+\.\d+)\.?\s*Електроенергії\s+немає'
        matches = re.findall(group_pattern, text_content, re.IGNORECASE | re.UNICODE)
        
        groups = sorted(list(set(matches)), key=lambda x: (float(x.split('.')[0]), float(x.split('.')[1])))
        
        return groups
    
    def normalize_time_format(self, time_str: str) -> str:
        if ':' not in time_str:
            return time_str
        
        hours, minutes = time_str.split(':')
        return f"{int(hours):02d}:{minutes}"
    
    def normalize_schedule(self, schedule: List[List[str]]) -> List[List[str]]:
        normalized = []
        for start, end in schedule:
            normalized_start = self.normalize_time_format(start)
            normalized_end = self.normalize_time_format(end)
            normalized.append([normalized_start, normalized_end])
        
        normalized.sort(key=lambda x: x[0])
        
        return normalized
