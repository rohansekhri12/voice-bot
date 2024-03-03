
import pyttsx3
import datetime
import speech_recognition as sr
from pymongo import MongoClient
import pygame
import time
import openai

# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client.voice_chat_box
collection = db.master

engine = pyttsx3.init('sapi5')
voices = engine.getProperty('voices')
engine.setProperty('voice', voices[0].id)
engine.setProperty('rate', 150)
engine.setProperty('volume', 1.0)

# Initialize OpenAI API
openai.api_key = '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'  # Replace with your actual OpenAI API key

def speak(audio):
    engine.say(audio)
    engine.runAndWait()

def get_time_of_day():
    time = datetime.datetime.now().hour
    if 0 <= time < 12:
        return "morning"
    elif 12 <= time < 17:
        return "afternoon"
    else:
        return "evening"

def get_phone_number():
    while True:
        speak("Please enter your phone number:")
        phone_number = input("Enter your phone number: ")
        user = find_user_by_phone_number(phone_number)
        if user:
            return phone_number
        else:
            speak("Sorry, we couldn't find a user with that phone number. Please provide a valid number.")

def find_user_by_phone_number(phone_number):
    user = collection.find_one({"Phone_no": phone_number})
    return user

def greet_user(user):
    if user:
        last_name = user.get("Last_Name")
        if last_name:
            speak(f"Good {get_time_of_day()}, Mr {last_name}")
        else:
            speak(f"Good {get_time_of_day()}, Mr/Ms. User")
    else:
        speak("Sorry, we couldn't find a user with that phone number.")

def play_music():
    pygame.init()
    pygame.mixer.music.load("whip-110235.mp3")
    pygame.mixer.music.play()

    start_time = time.time()
    while pygame.mixer.music.get_busy() and time.time() - start_time < 6:
        pass

    pygame.mixer.music.stop()

def stop_music():
    pygame.mixer.music.stop()

def task():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        speak("please state your problem")
        print("Listening...")
        r.pause_threshold = 1
        r.energy_threshold = 1500
        try:
            audio = r.listen(source, timeout=10)
            print("Recognizing...")
            query = r.recognize_google(audio, language='en-in')
            print("User said:", query)
            return query
        except sr.WaitTimeoutError:
            user = find_user_by_phone_number(phone_number)
            last_name = user.get("Last_Name") if user else "User"
            response = f"Hello, Mr {last_name}, are you there?"
            speak(response)
            return "None"
        except Exception as e:
            speak("Please speak again")
            return "None"

def save_complaint(ca_number, complaint, complaint_key):
    existing_complaint = db.complaint_db.find_one({"CA_No": ca_number, "Complaint_Key": complaint_key})
    
    if existing_complaint:
        speak("You have already registered this complaint.")
    else:
        db.complaint_db.insert_one({"CA_No": ca_number, "Complaint": complaint, "Complaint_Key": complaint_key})
        speak(f"Sorry for the inconvenience. I will generate your complaint against CA number {ca_number}.")

def process_user_query(query, phone_number):
    if any(word in query for word in ['no electricity', 'no power', 'light cut', 'fluctuation']):
        user = find_user_by_phone_number(phone_number)
        if user:
            ca_number = user.get("CA_No")
            if ca_number:
                complaint_key = next((word for word in ['no electricity', 'no power', 'light cut', 'fluctuation'] if word in query), None)
                save_complaint(ca_number, query, complaint_key)
            else:
                speak("Sorry, we couldn't find your CA number. Please provide a valid phone number.")
        else:
            speak("Sorry, we couldn't find a user with that phone number. Please provide a valid number.")
    elif any(word in query for word in ['quit', 'exit', 'leave', 'band karo']):
        speak("Terminating the script. Thank you for using our service. Have a great day!")
        exit()
    elif any(word in query for word in ['electricity bill', 'bill', 'not received bill']):
        user = find_user_by_phone_number(phone_number)
        if user:
            ca_number = user.get("CA_No")
            if ca_number:
                bill_record = db.CRM_table.find_one({"CA_No": ca_number})
                if bill_record:
                    issue_date = bill_record.get("Issue date")
                    due_date = bill_record.get("Due Date")
                    amount = bill_record.get("Amount")
                    speak("Sorry for the inconvenience caused. Give me a few seconds to check your details from my database.")
                    
                    play_music()  # Play the waiting music
                    time.sleep(4)  # Wait for 4 seconds

                    speak(f"Thank you for waiting, I have checked the records and I got to know that your Issue date is {issue_date}, your Due Date is {due_date} and the amount to be paid is {amount}.")
                    stop_music() # Stop the music

                    # Ask if there's anything else
                    speak("Is there anything else I can help you with?")
                else:
                    speak("Sorry, we couldn't find billing information for your CA number.")
            else:
                speak("Sorry, we couldn't find your CA number. Please provide a valid phone number.")
    else:
        # If query doesn't match predefined patterns, use GPT-3
        response = ask_gpt3(query)
        speak(response)

def ask_gpt3(prompt):
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=100,
        temperature=0.6,
        top_p=1.0,
        frequency_penalty=0.0,
        presence_penalty=0.0
    )
    return response.choices[0].text.strip()

if __name__ == "__main__":
    phone_number = get_phone_number()
    user = find_user_by_phone_number(phone_number)
    greet_user(user)
    while True:
        query = task().lower()
        if query != "None":
            process_user_query(query, phone_number)
