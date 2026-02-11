import asyncio
from typing import List, Optional, Dict
from datetime import datetime
from data_manager import DataManager
from parser import PowerOnParser
from config import Config

class ScheduleMonitor:
    def __init__(self, data_manager: DataManager, parser: PowerOnParser):
        self.data_manager = data_manager
        self.parser = parser
        self.bot = None
        self._monitoring_task = None
        self._stop_event = asyncio.Event()
        self._required_confirmations = 2
    
    def start_monitoring(self, bot):
        self.bot = bot
        self._stop_event.clear()
        import asyncio
        self._monitoring_task = asyncio.create_task(self._monitor_loop())
    
    async def stop_monitoring(self):
        self._stop_event.set()
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
    
    async def _monitor_loop(self):
        while not self._stop_event.is_set():
            try:
                await self._check_all_users()
                await asyncio.sleep(Config.CHECK_INTERVAL_MINUTES * 60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                await asyncio.sleep(60)
    
    async def _check_all_users(self):
        users = self.data_manager.get_all_users()
        
        for chat_id_str, user_data in users.items():
            try:
                chat_id = int(chat_id_str)
                user_group = user_data.get('group')
                
                if not user_group:
                    continue
                
                changes = await self.check_user_schedule(chat_id, user_group)
                
                if changes:
                    message = f"⚠️ *Зміни в графіку групи {user_group}:*\n\n{changes}"
                    await self.bot.send_notification(chat_id, message)
                    
            except Exception as e:
                pass
    
    async def check_user_schedule(self, chat_id: int, group: str) -> Optional[str]:
        try:
            current_schedule = self.parser.get_group_schedule(group)

            # If we couldn't fetch/parse current schedule (transient error), do NOT treat it as a change
            # and do NOT overwrite the saved schedule.
            if current_schedule is None:
                return None
            
            current_schedule_normalized = self.parser.normalize_schedule(current_schedule)
            saved_schedule = self.data_manager.get_user_schedule(chat_id)
            saved_schedule_normalized = self.parser.normalize_schedule(saved_schedule)

            # If same as saved -> clear any pending change confirmation and do nothing.
            if self._schedules_equal(current_schedule_normalized, saved_schedule_normalized):
                self.data_manager.clear_pending_change(chat_id)
                return None

            # Debounce: require the same changed schedule to be observed multiple times in a row
            pending_schedule = self.data_manager.get_pending_schedule(chat_id)
            pending_count = self.data_manager.get_pending_count(chat_id)

            if pending_schedule == current_schedule_normalized:
                pending_count += 1
            else:
                pending_schedule = current_schedule_normalized
                pending_count = 1

            self.data_manager.set_pending_change(chat_id, pending_schedule, pending_count)

            if pending_count < self._required_confirmations:
                return None

            # Confirmed change -> persist and notify
            self.data_manager.update_user_schedule(chat_id, current_schedule_normalized)
            self.data_manager.clear_pending_change(chat_id)
            return self._format_changes_message(current_schedule_normalized, saved_schedule_normalized)
            
        except Exception as e:
            return None
    
    def _schedules_equal(self, schedule1: List[List[str]], schedule2: List[List[str]]) -> bool:
        if len(schedule1) != len(schedule2):
            return False
        
        schedule1_sorted = sorted(schedule1, key=lambda x: x[0])
        schedule2_sorted = sorted(schedule2, key=lambda x: x[0])
        
        for interval1, interval2 in zip(schedule1_sorted, schedule2_sorted):
            if interval1[0] != interval2[0] or interval1[1] != interval2[1]:
                return False
        
        return True
    
    def _format_changes_message(self, current: List[List[str]], previous: List[List[str]]) -> str:
        message = ""
        
        if not previous and current:
            message += "🆕 *З'явився новий графік:*\n"
            message += self._format_schedule_list(current)
        elif not current and previous:
            message += "❌ *Графік видалено*\n"
            message += f"Раніше: {self._format_schedule_list(previous)}"
        else:
            added = self._find_added_intervals(current, previous)
            removed = self._find_removed_intervals(current, previous)
            changed = self._find_changed_intervals(current, previous)
            
            if added:
                message += "➕ *Додані інтервали:*\n"
                message += self._format_schedule_list(added)
            
            if removed:
                if message:
                    message += "\n"
                message += "➖ *Видалені інтервали:*\n"
                message += self._format_schedule_list(removed)
            
            if changed:
                if message:
                    message += "\n"
                message += "🔄 *Змінені інтервали:*\n"
                for old_interval, new_interval in changed:
                    message += f"  • {old_interval[0]}-{old_interval[1]} → {new_interval[0]}-{new_interval[1]}\n"
        
        if not message:
            message += "📊 *Оновлений графік:*\n"
            message += self._format_schedule_list(current)
        
        return message.strip()
    
    def _find_added_intervals(self, current: List[List[str]], previous: List[List[str]]) -> List[List[str]]:
        added = []
        for interval in current:
            if interval not in previous:
                added.append(interval)
        return added
    
    def _find_removed_intervals(self, current: List[List[str]], previous: List[List[str]]) -> List[List[str]]:
        removed = []
        for interval in previous:
            if interval not in current:
                removed.append(interval)
        return removed
    
    def _find_changed_intervals(self, current: List[List[str]], previous: List[List[str]]) -> List[tuple]:
        changed = []
        
        for prev_interval in previous:
            if prev_interval in current:
                continue
            
            for curr_interval in current:
                if curr_interval in previous:
                    continue
                
                if self._intervals_overlap(prev_interval, curr_interval):
                    changed.append((prev_interval, curr_interval))
                    break
        
        return changed
    
    def _intervals_overlap(self, interval1: List[str], interval2: List[str]) -> bool:
        start1 = self._time_to_minutes(interval1[0])
        end1 = self._time_to_minutes(interval1[1])
        start2 = self._time_to_minutes(interval2[0])
        end2 = self._time_to_minutes(interval2[1])
        
        return not (end1 <= start2 or end2 <= start1)
    
    def _time_to_minutes(self, time_str: str) -> int:
        hours, minutes = map(int, time_str.split(':'))
        return hours * 60 + minutes
    
    def _format_schedule_list(self, schedule: List[List[str]]) -> str:
        if not schedule:
            return "Відключень немає"
        
        formatted = []
        for start, end in schedule:
            formatted.append(f"  • {start} - {end}")
        
        return "\n".join(formatted)
