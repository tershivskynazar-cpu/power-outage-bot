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

    def _fetch_api_schedule_html(self) -> Optional[str]:
        try:
            url = (
                f"{Config.LOE_API_BASE_URL}{Config.LOE_API_PREFIX}/menus"
                f"?page=1&type={Config.LOE_API_SCHEDULE_MENU_TYPE}"
            )
            resp = self.session.get(url, timeout=Config.REQUEST_TIMEOUT)
            resp.raise_for_status()

            data = resp.json()
            members = data.get("hydra:member") or []
            if not members:
                return None

            menu = members[0]
            items = menu.get("menuItems") or []
            if not items:
                return None

            # Prefer the entry named 'Today' if present, otherwise first item.
            today = None
            for it in items:
                if str(it.get("name", "")).strip().lower() == "today":
                    today = it
                    break

            item = today or items[0]
            raw_html = item.get("rawHtml") or item.get("rawMobileHtml")
            if isinstance(raw_html, str) and raw_html.strip():
                return raw_html

            return None
        except Exception:
            return None
    
    def fetch_page(self) -> Optional[str]:
        if Config.USE_TEST_DATA:
            from test_data import TEST_SCHEDULE_DATA
            return TEST_SCHEDULE_DATA

        api_html = self._fetch_api_schedule_html()
        if api_html:
            return api_html
        
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
            return None
    
    def parse_schedule(self, html_content: str) -> Dict[str, List[List[str]]]:
        if not html_content:
            return {}
        
        soup = BeautifulSoup(html_content, 'lxml')
        
        schedule_data = {}

        # LOE API `rawHtml` sometimes has multiple groups concatenated in one block.
        # Parse by splitting the plain text into per-group chunks.
        text_content = soup.get_text(" ", strip=True)
        if not text_content:
            return {}

        group_chunk_pattern = re.compile(
            r'(Група\s+\d+\.\d+\.?\s*.*?)(?=\s*Група\s+\d+\.\d+\.?\s*|$)',
            re.IGNORECASE | re.UNICODE | re.DOTALL,
        )

        for chunk in group_chunk_pattern.findall(text_content):
            m = re.search(r'Група\s+(\d+\.\d+)\.?', chunk, re.IGNORECASE | re.UNICODE)
            if not m:
                continue

            group = m.group(1)
            intervals = self._parse_time_intervals(chunk)
            if intervals:
                schedule_data[group] = intervals

        # Fallback: strict pattern
        if not schedule_data:
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
        schedules = self.get_all_schedules()
        if schedules:
            keys = sorted(schedules.keys(), key=lambda x: (int(x.split('.')[0]), int(x.split('.')[1])))
            if keys:
                return keys

        html_content = self.fetch_page()
        if not html_content:
            return list(Config.FALLBACK_GROUPS)

        soup = BeautifulSoup(html_content, 'lxml')
        text_content = soup.get_text()

        group_patterns = [
            r'Група\s+(\d+\.\d+)\.?\s*Електроенергії\s+немає',
            r'Група\s+(\d+\.\d+)\.?',
        ]

        matches: List[str] = []
        for pattern in group_patterns:
            matches.extend(re.findall(pattern, text_content, re.IGNORECASE | re.UNICODE))

        unique = sorted(set(matches), key=lambda x: (int(x.split('.')[0]), int(x.split('.')[1])))
        return unique or list(Config.FALLBACK_GROUPS)
    
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
