import json
import os
from typing import Dict, List, Optional, Tuple
from config import Config

class DataManager:
    def __init__(self):
        self.data_file = Config.DATA_FILE
        self._data = self._load_data()
    
    def _load_data(self) -> Dict:
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Помилка завантаження даних: {e}")
                return {}
        return {}
    
    def _save_data(self) -> bool:
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
            return True
        except IOError as e:
            print(f"Помилка збереження даних: {e}")
            return False
    
    def set_user_group(self, chat_id: int, group: str) -> bool:
        if chat_id not in self._data:
            self._data[chat_id] = {}
        
        self._data[chat_id]['group'] = group
        self._data[chat_id]['last_schedule'] = []
        
        return self._save_data()
    
    def get_user_group(self, chat_id: int) -> Optional[str]:
        return self._data.get(str(chat_id), {}).get('group')
    
    def update_user_schedule(self, chat_id: int, schedule: List[List[str]]) -> bool:
        if str(chat_id) not in self._data:
            self._data[str(chat_id)] = {}
        
        self._data[str(chat_id)]['last_schedule'] = schedule
        return self._save_data()
    
    def get_user_schedule(self, chat_id: int) -> List[List[str]]:
        return self._data.get(str(chat_id), {}).get('last_schedule', [])
    
    def get_all_users(self) -> Dict:
        return self._data
    
    def remove_user(self, chat_id: int) -> bool:
        if str(chat_id) in self._data:
            del self._data[str(chat_id)]
            return self._save_data()
        return True
