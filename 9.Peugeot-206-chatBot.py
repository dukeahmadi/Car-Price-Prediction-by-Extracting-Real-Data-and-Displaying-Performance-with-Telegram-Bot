from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import jdatetime
import logging
import pickle
import numpy as np

# Set up basic logging to capture errors and information
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# List to store car information
car = {}
# Dictionary to track user states (like waiting for year input, etc.)
USER_STATE = {}

# Function to handle the /start command and initialize user state
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    USER_STATE[user_id] = 'AWAITING_YEAR'  # Set the state to wait for car's year
    car[user_id] = []  # Initialize an empty list to store car info for the user

    # Ask the user to enter the car's manufacturing year
    await update.message.reply_text("Please enter the year of your car in English:")
    
# Function to get the car's year from the user input
async def get_year(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if USER_STATE.get(user_id) != 'AWAITING_YEAR':  # Check if we are expecting the year input
        return

    try:
        year = int(update.message.text)  # Convert input to integer
        current_year = jdatetime.datetime.now().year  # Get the current year in Jalali calendar
        
        if 1380 <= year <= current_year:
            car[user_id].append(year)  # Save the year if valid
            USER_STATE[user_id] = 'AWAITING_KILOMETERS'  # Move to the next step (kilometers input)
            await update.message.reply_text("Please enter your vehicle operation in English")
        else:
            await update.message.reply_text("Please enter a valid number!")
    except ValueError:
        await update.message.reply_text("Please enter a valid number!")

# Function to get the car's kilometers from the user input
async def get_kilometers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if USER_STATE.get(user_id) != 'AWAITING_KILOMETERS':  # Check if we are expecting kilometers input
        return

    try:
        kilometers = int(update.message.text)  # Convert input to integer
        if kilometers >= 0:
            car[user_id].append(kilometers)  # Save kilometers if valid
            USER_STATE[user_id] = 'AWAITING_MODEL'  # Move to the next step (model selection)
            await ask_trim(update, context)
        else:
            await update.message.reply_text("Please enter a valid number!")
    except ValueError:
        await update.message.reply_text("Please enter a valid number!")

# Function to handle inline button presses and process the callback data
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id

    # Handle button responses based on the user's state
    if USER_STATE.get(user_id) == 'AWAITING_MODEL':
        car[user_id].append(int(query.data))  # Save car model selection
        USER_STATE[user_id] = 'AWAITING_PANORAMA'  # Move to the next step (Panorama query)
        await ask_panorama(update, context)
    elif USER_STATE.get(user_id) == 'AWAITING_PANORAMA':
        car[user_id].append('yes' if query.data == '1' else 'no')  # Save panorama info
        USER_STATE[user_id] = 'COMPLETED'  # Mark the process as completed
        await show_car_info(update, context)

# Function to display the car model selection as inline buttons
async def ask_trim(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [
            InlineKeyboardButton("تیپ 2", callback_data='2'),
            InlineKeyboardButton("تیپ 3", callback_data='3'),
        ],
        [
            InlineKeyboardButton("تیپ 5", callback_data='5'),
            InlineKeyboardButton("تیپ 6", callback_data='6'),
        ],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Please select your vehicle type:', reply_markup=reply_markup)

# Function to ask if the car has a panorama roof via inline buttons
async def ask_panorama(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [
            InlineKeyboardButton("yes", callback_data='1'),
            InlineKeyboardButton("no", callback_data='0'),
        ],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.message.reply_text('Is your car panoramic?', reply_markup=reply_markup)
    else:
        await update.message.reply_text('Is your car panoramic?', reply_markup=reply_markup)


# Function to show the car's collected information to the user and predict the price
async def show_car_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    car_info = car.get(user_id, [])  # Retrieve car info for the user
    
    # Ensure all car information is present
    if len(car_info) == 4:
        # Prepare the car data for prediction
        year = car_info[0]
        kilometers = car_info[1]
        model = car_info[2]
        panorama = 1 if car_info[3] == 'yes' else 0  # Convert 'yes/no' to 1/0
        
        try:
            # Load the model from the .pkl file
            with open("C:/Users/Amir/Desktop/Car Price Prediction/Models/Peugeot206Model.pkl", 'rb') as file:
                loaded_model = pickle.load(file)
            
            # Check if the loaded object is actually a model
            if hasattr(loaded_model, 'predict'):
                # Create the input data for prediction (assuming the model expects this format)
                input_data = np.array([[year, kilometers, model, panorama]])
            
                # Predict the car price
                predicted_price = loaded_model.predict(input_data)[0]
            
                # Prepare the response message
                message = (
                   f"Your vehicle information:\n"
                   f"Year of manufacture: {year}\n"
                   f"function: {kilometers} km\n"
                   f"type: type {model}\n"
                   f"Panorama: {'Yes' if panorama == 1 else 'No'}\n\n"
                   f"Estimated price: {predicted_price:,.0f} Tomans"
 )
            else:
                message = "The model was not loaded correctly. The loaded object does not have a 'predict' method."
        except FileNotFoundError:
            message = "Model file not found. Please check the file path."
        except Exception as e:
            message = f"Error loading or using model: {str(e)}"
    else:
        message ="Full vehicle information is not available."

    # Send the result to the user
    if update.callback_query:
        await update.callback_query.message.reply_text(message)
        await update.callback_query.message.reply_text("Process completed. Use /start command to restart.")
    else:
        await update.message.reply_text(message)
        await update.message.reply_text("Process completed. Use /start command to restart.")


# Function to handle all incoming text messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    state = USER_STATE.get(user_id)  # Check the user's current state

    if state == 'COMPLETED':
        await update.message.reply_text("The process has already completed. Use the /start command to restart it.")
        return

    # Route the message based on the current user state
    if state == 'AWAITING_YEAR':
        await get_year(update, context)
    elif state == 'AWAITING_KILOMETERS':
        await get_kilometers(update, context)

# Main function to set up and run the bot
def main() -> None:
    # Create the application with the bot's token
    application = Application.builder().token("7532981171:AAHiXOYjWfs54V4TtdyBbMj8UKMfUjLZch8").build()

    # Add the command and message handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the bot by polling updates from Telegram
    application.run_polling()

if __name__ == '__main__':
    main()


