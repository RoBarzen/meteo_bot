import os
import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from datetime import datetime, timedelta

# --- CONFIGURATION ---
BOT_TOKEN = '7511310203:AAFxn7ukc50zmD5c5Hcnufm_Br5EOGDP2S4'  # Replace with your bot token

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot_interactions.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Forecast types mapping
FORECAST_TYPES = {
    'flugdistanz': 'Flugdistanz (PFD, 18m)',
    'thermikkarte': 'Thermikkarte',
    'wolkenverteilung': 'Wolkenverteilung',
    'ortsvorhersage': 'Ortsvorhersage Langenfeld',
    'pfd_summary': 'PFD 18m-Klasse Übersicht'
}

def get_file_update_time(file_path):
    """Get the last update time of a file in a readable format"""
    if not os.path.exists(file_path):
        return "Nicht verfügbar"
    
    file_mtime = os.path.getmtime(file_path)
    update_time = datetime.fromtimestamp(file_mtime)
    now = datetime.now()
    
    # Calculate time difference
    time_diff = now - update_time
    
    if time_diff.total_seconds() < 60:
        return "Gerade aktualisiert"
    elif time_diff.total_seconds() < 3600:  # Less than 1 hour
        minutes = int(time_diff.total_seconds() // 60)
        return f"Vor {minutes} Min"
    elif time_diff.total_seconds() < 7200:  # Less than 2 hours
        hours = int(time_diff.total_seconds() // 3600)
        minutes = int((time_diff.total_seconds() % 3600) // 60)
        return f"Vor {hours}h {minutes}min"
    else:
        return update_time.strftime("%d.%m %H:%M")

def log_user_action(update: Update, action: str, details: str = ""):
    """Log user actions with user info"""
    user = update.effective_user
    user_info = f"User ID: {user.id}, Username: {user.username or 'N/A'}, First Name: {user.first_name or 'N/A'}"
    chat_info = f"Chat ID: {update.effective_chat.id}, Chat Type: {update.effective_chat.type}"
    
    if details:
        logger.info(f"ACTION: {action} | {user_info} | {chat_info} | Details: {details}")
    else:
        logger.info(f"ACTION: {action} | {user_info} | {chat_info}")

def get_available_days():
    """Get list of available day directories"""
    days = []
    for i in range(6):  # days 0-5
        day_dir = f'day{i}'
        if os.path.exists(day_dir):
            days.append(i)
    return days

def get_day_name(day_num):
    """Convert day number to readable name"""
    today = datetime.now()
    target_date = today + timedelta(days=day_num)
    if day_num == 0:
        return "Heute"
    elif day_num == 1:
        return "Morgen"
    else:
        return target_date.strftime("%A, %d.%m")  # e.g., "Montag, 08.07"

def get_available_hours(day_num, forecast_type):
    """Get available hours for a specific day and forecast type"""
    day_dir = f'day{day_num}'
    if not os.path.exists(day_dir):
        return []
    
    hours = []
    for file in os.listdir(day_dir):
        if file.startswith(f'forecast_{forecast_type}_day{day_num}_hour'):
            # Extract hour from filename
            hour_str = file.split('_hour')[1].split('.')[0]
            try:
                hour = int(hour_str)
                hours.append(hour)
            except ValueError:
                continue
    
    return sorted(hours)

async def get_or_create_menu_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get existing menu message or create a new one"""
    log_user_action(update, "get_or_create_menu_message", "Attempting to get/create menu message")
    
    chat_id = update.effective_chat.id
    menu_message_id = context.user_data.get('menu_message_id')
    
    if menu_message_id:
        try:
            # Try to get the existing message
            await context.bot.get_chat(chat_id)
            logger.info(f"Using existing menu message ID: {menu_message_id}")
            return menu_message_id
        except:
            # Message doesn't exist, remove from context
            context.user_data.pop('menu_message_id', None)
            logger.warning(f"Existing menu message {menu_message_id} not found, creating new one")
    
    # Create new menu message
    welcome_text = """
🌤️ *TopMeteo Forecast Bot*

Willkommen! Ich kann dir Wettervorhersagen für Segelflug zur Verfügung stellen.

*Verfügbare Vorhersagen:*
• Flugdistanz (PFD, 18m)
• Thermikkarte
• Wolkenverteilung
• Ortsvorhersage Langenfeld
• PFD 18m-Klasse Übersicht

Verwende /forecast um eine Vorhersage auszuwählen.
"""
    
    keyboard = [
        [InlineKeyboardButton("🌤️ Vorhersage anzeigen", callback_data="show_forecast")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = await context.bot.send_message(
        chat_id=chat_id,
        text=welcome_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    
    context.user_data['menu_message_id'] = message.message_id
    logger.info(f"Created new menu message with ID: {message.message_id}")
    return message.message_id

async def update_menu_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str, keyboard: list):
    """Update the persistent menu message"""
    menu_message_id = context.user_data.get('menu_message_id')
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    logger.info(f"Updating menu message. Old ID: {menu_message_id}, Chat ID: {chat_id}")
    
    try:
        # Try to delete the old menu message if it exists
        if menu_message_id:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=menu_message_id)
                logger.info(f"Deleted old menu message ID: {menu_message_id}")
            except Exception as e:
                logger.warning(f"Could not delete old menu message {menu_message_id}: {e}")
                pass  # Message might not exist, continue anyway
        
        # Create new menu message (this will be at the bottom)
        message = await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        context.user_data['menu_message_id'] = message.message_id
        logger.info(f"Created new menu message with ID: {message.message_id}")
        
    except Exception as e:
        logger.error(f"Error updating menu message: {e}")
        # If update fails, create new menu message
        message = await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        context.user_data['menu_message_id'] = message.message_id
        logger.info(f"Created fallback menu message with ID: {message.message_id}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message when the command /start is issued."""
    log_user_action(update, "start_command", "User started the bot")
    await get_or_create_menu_message(update, context)

async def forecast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /forecast command"""
    log_user_action(update, "forecast_command", "User requested forecast menu")
    await show_days(update, context)

async def show_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show available days"""
    query = update.callback_query
    if query:
        await query.answer()
        log_user_action(update, "show_days", f"Callback query: {query.data}")
    else:
        log_user_action(update, "show_days", "Direct command")
    
    days = get_available_days()
    logger.info(f"Available days found: {days}")
    
    if not days:
        logger.warning("No forecast data available")
        text = "❌ Keine Vorhersagedaten verfügbar."
        keyboard = [[InlineKeyboardButton("🔙 Hauptmenü", callback_data="main_menu")]]
        await update_menu_message(context, update.effective_chat.id, text, keyboard)
        return
    
    text = "📅 *Wähle einen Tag:*"
    keyboard = []
    
    for day in days:
        day_name = get_day_name(day)
        keyboard.append([InlineKeyboardButton(day_name, callback_data=f"day_{day}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Hauptmenü", callback_data="main_menu")])
    await update_menu_message(context, update.effective_chat.id, text, keyboard)

async def show_forecast_types(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show available forecast types for a selected day"""
    query = update.callback_query
    await query.answer()
    
    day_num = int(query.data.split('_')[1])
    day_name = get_day_name(day_num)
    
    log_user_action(update, "show_forecast_types", f"Day selected: {day_num} ({day_name})")
    
    text = f"🌤️ *Vorhersagetypen für {day_name}:*"
    keyboard = []
    
    available_types = []
    for forecast_type, display_name in FORECAST_TYPES.items():
        # Check if any files exist for this type and day
        day_dir = f'day{day_num}'
        if os.path.exists(day_dir):
            files = [f for f in os.listdir(day_dir) if f.startswith(f'forecast_{forecast_type}_day{day_num}')]
            if files:
                keyboard.append([InlineKeyboardButton(display_name, callback_data=f"type_{day_num}_{forecast_type}")])
                available_types.append(forecast_type)
    
    # Add PFD summary option (available for any day)
    keyboard.append([InlineKeyboardButton(FORECAST_TYPES['pfd_summary'], callback_data=f"type_{day_num}_pfd_summary")])
    available_types.append('pfd_summary')
    
    logger.info(f"Available forecast types for day {day_num}: {available_types}")
    
    keyboard.append([InlineKeyboardButton("🔙 Zurück zu Tagen", callback_data="show_days")])
    await update_menu_message(context, update.effective_chat.id, text, keyboard)

async def show_hours_or_send_flugdistanz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show available hours for hourly forecasts, or directly send Flugdistanz/Ortsvorhersage"""
    query = update.callback_query
    await query.answer()
    
    # Parse callback data - handle both 3-part and 4-part formats
    parts = query.data.split('_')
    if len(parts) >= 3:
        day_num = int(parts[1])
        forecast_type = parts[2]
        
        # If there's a 4th part, it's the full forecast type name
        if len(parts) == 4 and parts[2] == 'pfd' and parts[3] == 'summary':
            forecast_type = 'pfd_summary'
    else:
        logger.error(f"Invalid callback data format: {query.data}")
        return
    
    day_name = get_day_name(day_num)
    forecast_name = FORECAST_TYPES[forecast_type]
    
    log_user_action(update, "show_hours_or_send_flugdistanz", f"Forecast type selected: {forecast_type} for day {day_num}")
    
    # For Flugdistanz and Ortsvorhersage, send directly without hour selection
    if forecast_type in ['flugdistanz', 'ortsvorhersage']:
        logger.info(f"Sending {forecast_type} directly for day {day_num}")
        if forecast_type == 'flugdistanz':
            await send_flugdistanz_image(update, context, day_num)
        else:
            await send_ortsvorhersage_image(update, context, day_num)
        return
    
    # For PFD summary, send directly without day selection
    if forecast_type == 'pfd_summary':
        logger.info("Sending PFD summary directly")
        await send_pfd_summary(update, context)
        return
    
    # For other forecast types, show hour selection
    hours = get_available_hours(day_num, forecast_type)
    logger.info(f"Available hours for {forecast_type} day {day_num}: {hours}")
    
    if not hours:
        logger.warning(f"No data available for {forecast_type} on day {day_num}")
        text = f"❌ Keine Daten verfügbar für {forecast_name} am {day_name}."
        keyboard = [[InlineKeyboardButton("🔙 Zurück", callback_data=f"day_{day_num}")]]
        await update_menu_message(context, update.effective_chat.id, text, keyboard)
        return
    
    text = f"🕐 *{forecast_name} - {day_name}*\nWähle eine Uhrzeit:"
    keyboard = []
    
    # Group hours in rows of 3
    for i in range(0, len(hours), 3):
        row = []
        for hour in hours[i:i+3]:
            row.append(InlineKeyboardButton(f"{hour:02d}:00", callback_data=f"hour_{day_num}_{forecast_type}_{hour}"))
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("🔙 Zurück", callback_data=f"day_{day_num}")])
    await update_menu_message(context, update.effective_chat.id, text, keyboard)

async def send_flugdistanz_image(update: Update, context: ContextTypes.DEFAULT_TYPE, day_num):
    """Send Flugdistanz image directly (no hour selection needed)"""
    query = update.callback_query
    
    day_name = get_day_name(day_num)
    forecast_name = FORECAST_TYPES['flugdistanz']
    
    log_user_action(update, "send_flugdistanz_image", f"Attempting to send Flugdistanz for day {day_num}")
    
    # Construct file path for Flugdistanz (always hour 10)
    filename = f'forecast_flugdistanz_day{day_num}_hour10.png'
    file_path = os.path.join(f'day{day_num}', filename)
    
    if not os.path.exists(file_path):
        logger.error(f"Flugdistanz file not found: {file_path}")
        text = f"❌ Datei nicht gefunden: {filename}"
        keyboard = [[InlineKeyboardButton("🔙 Zurück", callback_data=f"day_{day_num}")]]
        await update_menu_message(context, update.effective_chat.id, text, keyboard)
        return
    
    # Create caption
    update_time = get_file_update_time(file_path)
    caption = f"🌤️ *{forecast_name}*\n📅 {day_name}\n📊 Tagesvorhersage\n🕐 Aktualisiert: {update_time}"
    
    # Send image above the menu
    try:
        with open(file_path, 'rb') as photo:
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=photo,
                caption=caption,
                parse_mode='Markdown'
            )
        
        logger.info(f"Successfully sent Flugdistanz image for day {day_num}")
        
        # Update menu with options (this will delete old menu and create new one at bottom)
        text = "✅ Flugdistanz-Vorhersage gesendet!"
        keyboard = [
            [InlineKeyboardButton("📅 Andere Vorhersage", callback_data="show_forecast")],
            [InlineKeyboardButton("🔄 Neue Vorhersage", callback_data=f"day_{day_num}")]
        ]
        await update_menu_message(context, update.effective_chat.id, text, keyboard)
        
    except Exception as e:
        logger.error(f"Error sending Flugdistanz image: {e}")
        text = "❌ Fehler beim Senden der Flugdistanz-Vorhersage."
        keyboard = [[InlineKeyboardButton("🔙 Zurück", callback_data=f"day_{day_num}")]]
        await update_menu_message(context, update.effective_chat.id, text, keyboard)

async def send_ortsvorhersage_image(update: Update, context: ContextTypes.DEFAULT_TYPE, day_num):
    """Send Ortsvorhersage image directly (no hour selection needed)"""
    query = update.callback_query
    
    day_name = get_day_name(day_num)
    forecast_name = FORECAST_TYPES['ortsvorhersage']
    
    log_user_action(update, "send_ortsvorhersage_image", f"Attempting to send Ortsvorhersage for day {day_num}")
    
    # Construct file path for Ortsvorhersage (no hour in filename)
    filename = f'forecast_ortsvorhersage_day{day_num}.png'
    file_path = os.path.join(f'day{day_num}', filename)
    
    if not os.path.exists(file_path):
        logger.error(f"Ortsvorhersage file not found: {file_path}")
        text = f"❌ Datei nicht gefunden: {filename}"
        keyboard = [[InlineKeyboardButton("🔙 Zurück", callback_data=f"day_{day_num}")]]
        await update_menu_message(context, update.effective_chat.id, text, keyboard)
        return
    
    # Create caption
    update_time = get_file_update_time(file_path)
    caption = f"🌤️ *{forecast_name}*\n📅 {day_name}\n📍 Langenfeld, Nordrhein-Westfalen\n📊 Tagesvorhersage\n🕐 Aktualisiert: {update_time}"
    
    # Send image above the menu
    try:
        with open(file_path, 'rb') as photo:
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=photo,
                caption=caption,
                parse_mode='Markdown'
            )
        
        logger.info(f"Successfully sent Ortsvorhersage image for day {day_num}")
        
        # Update menu with options (this will delete old menu and create new one at bottom)
        text = "✅ Ortsvorhersage für Langenfeld gesendet!"
        keyboard = [
            [InlineKeyboardButton("📅 Andere Vorhersage", callback_data="show_forecast")],
            [InlineKeyboardButton("🔄 Neue Vorhersage", callback_data=f"day_{day_num}")]
        ]
        await update_menu_message(context, update.effective_chat.id, text, keyboard)
        
    except Exception as e:
        logger.error(f"Error sending Ortsvorhersage image: {e}")
        text = "❌ Fehler beim Senden der Ortsvorhersage."
        keyboard = [[InlineKeyboardButton("🔙 Zurück", callback_data=f"day_{day_num}")]]
        await update_menu_message(context, update.effective_chat.id, text, keyboard)

async def send_forecast_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send the selected forecast image (for hourly forecasts)"""
    query = update.callback_query
    await query.answer()
    
    _, day_num, forecast_type, hour = query.data.split('_')
    day_num = int(day_num)
    hour = int(hour)
    
    day_name = get_day_name(day_num)
    forecast_name = FORECAST_TYPES[forecast_type]
    
    log_user_action(update, "send_forecast_image", f"Attempting to send {forecast_type} for day {day_num} hour {hour}")
    
    # Construct file path
    filename = f'forecast_{forecast_type}_day{day_num}_hour{hour:02d}.png'
    file_path = os.path.join(f'day{day_num}', filename)
    
    if not os.path.exists(file_path):
        logger.error(f"Forecast file not found: {file_path}")
        text = f"❌ Datei nicht gefunden: {filename}"
        keyboard = [[InlineKeyboardButton("🔙 Zurück", callback_data=f"type_{day_num}_{forecast_type}")]]
        await update_menu_message(context, update.effective_chat.id, text, keyboard)
        return
    
    # Create caption
    update_time = get_file_update_time(file_path)
    caption = f"🌤️ *{forecast_name}*\n📅 {day_name}\n🕐 {hour:02d}:00 UTC\n🕐 Aktualisiert: {update_time}"
    
    # Send image above the menu
    try:
        with open(file_path, 'rb') as photo:
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=photo,
                caption=caption,
                parse_mode='Markdown'
            )
        
        logger.info(f"Successfully sent {forecast_type} image for day {day_num} hour {hour}")
        
        # Update menu with options (this will delete old menu and create new one at bottom)
        text = "✅ Vorhersage gesendet!"
        keyboard = [
            [InlineKeyboardButton("📅 Andere Vorhersage", callback_data="show_forecast")],
            [InlineKeyboardButton("🔄 Neue Vorhersage", callback_data=f"type_{day_num}_{forecast_type}")]
        ]
        await update_menu_message(context, update.effective_chat.id, text, keyboard)
        
    except Exception as e:
        logger.error(f"Error sending forecast image: {e}")
        text = "❌ Fehler beim Senden der Vorhersage."
        keyboard = [[InlineKeyboardButton("🔙 Zurück", callback_data=f"type_{day_num}_{forecast_type}")]]
        await update_menu_message(context, update.effective_chat.id, text, keyboard)

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return to main menu"""
    query = update.callback_query
    await query.answer()
    
    log_user_action(update, "main_menu", "User returned to main menu")
    
    welcome_text = """
🌤️ *TopMeteo Forecast Bot*

Willkommen! Ich kann dir Wettervorhersagen für Segelflug zur Verfügung stellen.

*Verfügbare Vorhersagen:*
• Flugdistanz (PFD, 18m)
• Thermikkarte
• Wolkenverteilung
• Ortsvorhersage Langenfeld
• PFD 18m-Klasse Übersicht

Verwende /forecast um eine Vorhersage auszuwählen.
"""
    
    keyboard = [
        [InlineKeyboardButton("🌤️ Vorhersage anzeigen", callback_data="show_forecast")]
    ]
    await update_menu_message(context, update.effective_chat.id, welcome_text, keyboard)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    
    log_user_action(update, "button_handler", f"Button pressed: {query.data}")
    
    if query.data == "show_forecast":
        await show_days(update, context)
    elif query.data == "main_menu":
        await main_menu(update, context)
    elif query.data.startswith("day_"):
        await show_forecast_types(update, context)
    elif query.data.startswith("type_"):
        await show_hours_or_send_flugdistanz(update, context)
    elif query.data.startswith("hour_"):
        await send_forecast_image(update, context)
    else:
        logger.warning(f"Unknown callback data: {query.data}")

def get_pfd_summary():
    """Get PFD 18m-Klasse summary for all available days"""
    summary_lines = []
    summary_lines.append("📊 *PFD 18m-Klasse [km] - Tagesübersicht*\n")
    
    for day in range(6):  # days 0-5
        day_name = get_day_name(day)
        pfd_file = f'day{day}/pfd_18m_day{day}.txt'
        
        if os.path.exists(pfd_file):
            try:
                with open(pfd_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                
                # Skip if it's an error message
                if "not found" in content or "Error" in content:
                    summary_lines.append(f"📅 *{day_name}:* Keine PFD-Daten verfügbar")
                    continue
                
                # Extract the actual PFD values from the content
                lines = content.split('\n')
                daily_values = []
                
                for line in lines:
                    if ':' in line and 'km' in line:
                        # Extract km value
                        parts = line.split(':')
                        if len(parts) >= 2:
                            value_part = parts[1].strip()
                            
                            # Extract km value using regex
                            km_match = re.search(r'(\d+)', value_part)
                            if km_match:
                                km_value = int(km_match.group(1))
                                daily_values.append(km_value)
                
                if daily_values:
                    # Calculate total km for the day
                    total_km = sum(daily_values)
                    
                    # Get the date for the day
                    today = datetime.now()
                    target_date = today + timedelta(days=day)
                    date_str = target_date.strftime("%d.%m")
                    
                    # Format the day name with date
                    if day == 0:
                        day_display = f"Heute ({date_str})"
                    elif day == 1:
                        day_display = f"Morgen ({date_str})"
                    else:
                        day_display = f"{day_name} ({date_str})"
                    
                    summary_lines.append(f"📅 *{day_display}:* {total_km} km")
                else:
                    summary_lines.append(f"📅 *{day_name}:* Keine PFD-Daten verfügbar")
            except Exception as e:
                summary_lines.append(f"📅 *{day_name}:* Fehler beim Lesen der Daten")
        else:
            summary_lines.append(f"📅 *{day_name}:* Keine PFD-Datei gefunden")
    
    if len(summary_lines) <= 2:  # Only header and no data
        return "❌ Keine PFD 18m-Klasse Daten verfügbar."
    
    return "\n".join(summary_lines)

async def send_pfd_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send PFD 18m-Klasse summary as text message"""
    query = update.callback_query
    
    log_user_action(update, "send_pfd_summary", "Sending PFD 18m-Klasse summary")
    
    # Get PFD summary
    pfd_summary = get_pfd_summary()
    
    # Send text message above the menu
    try:
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=pfd_summary,
            parse_mode='Markdown'
        )
        
        logger.info("Successfully sent PFD 18m-Klasse summary")
        
        # Update menu with options (this will delete old menu and create new one at bottom)
        text = "✅ PFD 18m-Klasse Übersicht gesendet!"
        keyboard = [
            [InlineKeyboardButton("📅 Andere Vorhersage", callback_data="show_forecast")],
            [InlineKeyboardButton("🔄 Neue Übersicht", callback_data="pfd_summary")]
        ]
        await update_menu_message(context, update.effective_chat.id, text, keyboard)
        
    except Exception as e:
        logger.error(f"Error sending PFD summary: {e}")
        text = "❌ Fehler beim Senden der PFD-Übersicht."
        keyboard = [[InlineKeyboardButton("🔙 Zurück", callback_data="show_forecast")]]
        await update_menu_message(context, update.effective_chat.id, text, keyboard)

def main():
    """Start the bot."""
    logger.info("Starting TopMeteo Forecast Bot")
    
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("forecast", forecast_command))
    application.add_handler(CallbackQueryHandler(button_handler))

    logger.info("Bot handlers registered, starting polling...")
    
    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main() 