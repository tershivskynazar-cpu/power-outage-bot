import logging
from typing import List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from config import Config
from data_manager import DataManager
from parser import PowerOnParser
from scheduler import ScheduleMonitor

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class PowerOutageBot:
    def __init__(self):
        self.data_manager = DataManager()
        self.parser = PowerOnParser()
        self.schedule_monitor = ScheduleMonitor(self.data_manager, self.parser)
        
        self.application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
        self.application.job_queue.run_repeating(
            self._scheduled_check,
            interval=Config.CHECK_INTERVAL_MINUTES * 60,
            first=5,
        )
        
        self._setup_handlers()
    
    def _setup_handlers(self):
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("group", self.group_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("check", self.check_command))
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_chat.id
        
        await update.message.reply_text(
            "👋 Вітаю! Я бот для відстеження графіків відключення електроенергії.\n\n"
            "Оберіть вашу групу, щоб я міг надсилати вам сповіщення про зміни:"
        )
        
        await self._send_group_selection(user_id, context)
    
    async def group_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_chat.id
        
        await update.message.reply_text(
            "📋 Оберіть вашу групу:"
        )
        
        await self._send_group_selection(user_id, context)
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_chat.id
        
        user_group = self.data_manager.get_user_group(user_id)
        if not user_group:
            await update.message.reply_text(
                "❌ Ви ще не обрали групу. Використайте команду /group для вибору."
            )
            return
        
        current_schedule = self.parser.get_group_schedule(user_group)
        saved_schedule = self.data_manager.get_user_schedule(user_id)
        
        message = f"📊 *Статус групи {user_group}*\n\n"
        
        if current_schedule:
            message += "🔄 *Поточний графік:*\n"
            message += self._format_schedule(current_schedule)
        else:
            message += "❌ *Графік не знайдено на сайті*\n"
        
        if saved_schedule:
            message += "\n💾 *Збережений графік:*\n"
            message += self._format_schedule(saved_schedule)
        else:
            message += "\n💾 *Збережений графік порожній*\n"
        
        keyboard = [
            [InlineKeyboardButton("📊 Статус", callback_data="cmd_status")],
            [InlineKeyboardButton("🔄 Перевірити", callback_data="cmd_check")],
            [InlineKeyboardButton("📋 Змінити групу", callback_data="cmd_group")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
    
    async def check_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_chat.id
        
        user_group = self.data_manager.get_user_group(user_id)
        if not user_group:
            await update.message.reply_text(
                "❌ Ви ще не обрали групу. Використайте команду /group для вибору."
            )
            return
        
        await update.message.reply_text("🔍 Перевіряю графік...")
        
        changes = await self.schedule_monitor.check_user_schedule(user_id, user_group)
        
        if changes:
            keyboard = [
                [InlineKeyboardButton("📊 Статус", callback_data="cmd_status")],
                [InlineKeyboardButton("🔄 Перевірити", callback_data="cmd_check")],
                [InlineKeyboardButton("📋 Змінити групу", callback_data="cmd_group")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"⚠️ *Знайдено зміни в графіку групи {user_group}:*\n\n{changes}",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        else:
            keyboard = [
                [InlineKeyboardButton("📊 Статус", callback_data="cmd_status")],
                [InlineKeyboardButton("🔄 Перевірити", callback_data="cmd_check")],
                [InlineKeyboardButton("📋 Змінити групу", callback_data="cmd_group")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✅ Графік групи {user_group} не змінився.",
                reply_markup=reply_markup
            )
    
    async def _send_group_selection(self, user_id: int, context_or_query):
        available_groups = self.parser.get_available_groups()
        
        if not available_groups:
            if hasattr(context_or_query, 'edit_message_text'):
                await context_or_query.edit_message_text("❌ Не вдалося отримати список груп. Спробуйте пізніше.")
            else:
                await context_or_query.bot.send_message(
                    chat_id=user_id,
                    text="❌ Не вдалося отримати список груп. Спробуйте пізніше."
                )
            return
        
        keyboard = []
        
        for i in range(0, len(available_groups), 4):
            row = []
            for group in available_groups[i:i+4]:
                row.append(InlineKeyboardButton(f"Група {group}", callback_data=f"group_{group}"))
            keyboard.append(row)
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if hasattr(context_or_query, 'edit_message_text'):
            await context_or_query.edit_message_text(
                "📍 Оберіть вашу групу:",
                reply_markup=reply_markup
            )
        else:
            await context_or_query.bot.send_message(
                chat_id=user_id,
                text="📍 Оберіть вашу групу:",
                reply_markup=reply_markup
            )
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_chat.id
        callback_data = query.data
        
        if callback_data.startswith("group_"):
            group = callback_data.replace("group_", "")
            
            available_groups = self.parser.get_available_groups()
            if group in available_groups:
                self.data_manager.set_user_group(user_id, group)
                
                current_schedule = self.parser.get_group_schedule(group)
                if current_schedule:
                    self.data_manager.update_user_schedule(user_id, current_schedule)
                    schedule_text = self._format_schedule(current_schedule)
                    
                    keyboard = [
                        [InlineKeyboardButton("📊 Статус", callback_data="cmd_status")],
                        [InlineKeyboardButton("🔄 Перевірити", callback_data="cmd_check")],
                        [InlineKeyboardButton("📋 Змінити групу", callback_data="cmd_group")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await query.edit_message_text(
                        f"✅ *Групу {group} збережено!*\n\n"
                        f"📊 *Поточний графік:*\n{schedule_text}\n\n"
                        f"🔔 Я буду повідомляти вас про зміни в графіку кожні {Config.CHECK_INTERVAL_MINUTES} хвилин.",
                        parse_mode='Markdown',
                        reply_markup=reply_markup
                    )
                else:
                    keyboard = [
                        [InlineKeyboardButton("📊 Статус", callback_data="cmd_status")],
                        [InlineKeyboardButton("🔄 Перевірити", callback_data="cmd_check")],
                        [InlineKeyboardButton("📋 Змінити групу", callback_data="cmd_group")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await query.edit_message_text(
                        f"✅ *Групу {group} збережено!*\n\n"
                        f"⚠️ Наразі графік для цієї групи відсутній на сайті.\n"
                        f"🔔 Я буду повідомляти вас про зміни в графіку кожні {Config.CHECK_INTERVAL_MINUTES} хвилин.",
                        parse_mode='Markdown',
                        reply_markup=reply_markup
                    )
            else:
                await query.edit_message_text("❌ Невідома група. Спробуйте ще раз.")
        
        elif callback_data == "cmd_status":
            await self._handle_status_command(query, user_id)
        elif callback_data == "cmd_check":
            await self._handle_check_command(query, user_id)
        elif callback_data == "cmd_group":
            await self._handle_group_command(query, user_id)
    
    async def _handle_status_command(self, query, user_id: int):
        user_group = self.data_manager.get_user_group(user_id)
        if not user_group:
            keyboard = [
                [InlineKeyboardButton("📋 Змінити групу", callback_data="cmd_group")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "❌ Ви ще не обрали групу. Оберіть групу нижче:",
                reply_markup=reply_markup
            )
            return
        
        current_schedule = self.parser.get_group_schedule(user_group)
        saved_schedule = self.data_manager.get_user_schedule(user_id)
        
        message = f"📊 *Статус групи {user_group}*\n\n"
        
        if current_schedule:
            message += "🔄 *Поточний графік:*\n"
            message += self._format_schedule(current_schedule)
        else:
            message += "❌ *Графік не знайдено на сайті*\n"
        
        if saved_schedule:
            message += "\n💾 *Збережений графік:*\n"
            message += self._format_schedule(saved_schedule)
        else:
            message += "\n💾 *Збережений графік порожній*\n"
        
        keyboard = [
            [InlineKeyboardButton("📊 Статус", callback_data="cmd_status")],
            [InlineKeyboardButton("🔄 Перевірити", callback_data="cmd_check")],
            [InlineKeyboardButton("📋 Змінити групу", callback_data="cmd_group")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=reply_markup)
    
    async def _handle_check_command(self, query, user_id: int):
        user_group = self.data_manager.get_user_group(user_id)
        if not user_group:
            keyboard = [
                [InlineKeyboardButton("📋 Змінити групу", callback_data="cmd_group")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "❌ Ви ще не обрали групу. Оберіть групу нижче:",
                reply_markup=reply_markup
            )
            return
        
        await query.edit_message_text("🔍 Перевіряю графік...")
        
        changes = await self.schedule_monitor.check_user_schedule(user_id, user_group)
        
        if changes:
            keyboard = [
                [InlineKeyboardButton("📊 Статус", callback_data="cmd_status")],
                [InlineKeyboardButton("🔄 Перевірити", callback_data="cmd_check")],
                [InlineKeyboardButton("📋 Змінити групу", callback_data="cmd_group")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"⚠️ *Знайдено зміни в графіку групи {user_group}:*\n\n{changes}",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        else:
            keyboard = [
                [InlineKeyboardButton("📊 Статус", callback_data="cmd_status")],
                [InlineKeyboardButton("🔄 Перевірити", callback_data="cmd_check")],
                [InlineKeyboardButton("📋 Змінити групу", callback_data="cmd_group")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"✅ Графік групи {user_group} не змінився.",
                reply_markup=reply_markup
            )
    
    async def _handle_group_command(self, query, user_id: int):
        await self._send_group_selection(user_id, query)
    
    def _format_schedule(self, schedule: List[List[str]]) -> str:
        if not schedule:
            return "Відключень немає"
        
        formatted = []
        for start, end in schedule:
            formatted.append(f"  • {start} - {end}")
        
        return "\n".join(formatted)
    
    async def send_notification(self, user_id: int, message: str):
        try:
            await self.application.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='Markdown'
            )
        except Exception as e:
            pass

    async def _scheduled_check(self, context: ContextTypes.DEFAULT_TYPE):
        users = self.data_manager.get_all_users()

        for chat_id_str, user_data in users.items():
            try:
                chat_id = int(chat_id_str)
                user_group = user_data.get('group')
                if not user_group:
                    continue

                changes = await self.schedule_monitor.check_user_schedule(chat_id, user_group)
                if changes:
                    message = f"⚠️ *Зміни в графіку групи {user_group}:*\n\n{changes}"
                    await self.send_notification(chat_id, message)
            except Exception:
                pass
    
    def run(self):
        self.application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    bot = PowerOutageBot()
    bot.run()
