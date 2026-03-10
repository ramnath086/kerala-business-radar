import requests
import json
import os
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import instaloader

# ==============================
# ENVIRONMENT VARIABLES
# ==============================

BOT_TOKEN = os.environ["8707781362:AAEP0BV35V52tb5jXr-kBJUMTW4vcPA9pFU"]
CHAT_ID = os.environ["1050884051"]
GOOGLE_API_KEY = os.environ["AIzaSyCmBEwcl-bP5s_XdGt2O_ZuMT70RG4p8Nw"]

# Google service account JSON stored as environment variable
SERVICE_ACCOUNT = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT"])

# ==============================
# GOOGLE SHEETS CONNECTION
# ==============================

scope = [
"https://spreadsheets.google.com/feeds",
"https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(
SERVICE_ACCOUNT,
scope
)

client = gspread.authorize(creds)
sheet = client.open("Kerala Merchant Leads").sheet1

# Load existing leads to prevent duplicates
existing = set()

for r in sheet.get_all_records():
    existing.add(r["Business Name"].lower())

# ==============================
# CONFIG
# ==============================

cities = [
"Kochi",
"Ernakulam",
"Thrissur",
"Thiruvananthapuram",
"Kozhikode",
"Palakkad",
"Kottayam"
]

business_types = [
"restaurant",
"pharmacy",
"supermarket",
"bakery",
"salon",
"clinic"
]

gst_keywords = [
"traders",
"enterprises",
"distributors",
"industries"
]

instagram_tags = [
"kochi",
"kochirestaurant",
"thrissurbusiness",
"calicutfood"
]

# ==============================
# TELEGRAM
# ==============================

def send_telegram(text):

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    max_len = 4000

    for i in range(0,len(text),max_len):

        requests.post(url,data={
            "chat_id":CHAT_ID,
            "text":text[i:i+max_len]
        })


# ==============================
# SAVE LEAD
# ==============================

def save_lead(date,city,name,category,address,phone,website):

    if name.lower() in existing:
        return

    sheet.append_row([
        date,
        city,
        name,
        category,
        address,
        phone,
        website
    ])

    existing.add(name.lower())


# ==============================
# GOOGLE MAPS SEARCH
# ==============================

def google_search():

    report="\nNew Businesses (Google Maps)\n"

    today=datetime.now().strftime("%d %B %Y")

    for city in cities:

        report+=f"\nCity: {city}\n"

        for business in business_types:

            url="https://maps.googleapis.com/maps/api/place/textsearch/json"

            params={
                "query":f"{business} in {city}",
                "key":GOOGLE_API_KEY
            }

            data=requests.get(url,params=params).json()

            for place in data.get("results",[])[:10]:

                if place.get("user_ratings_total",0) > 5:
                    continue

                name=place.get("name","")
                address=place.get("formatted_address","")
                pid=place.get("place_id","")

                details=requests.get(
                "https://maps.googleapis.com/maps/api/place/details/json",
                params={
                    "place_id":pid,
                    "fields":"formatted_phone_number,website",
                    "key":GOOGLE_API_KEY
                }).json()

                phone=details.get("result",{}).get("formatted_phone_number","N/A")
                website=details.get("result",{}).get("website","N/A")

                report+=f"\n{name}\n{business}\n{address}\nPhone:{phone}\n"

                save_lead(today,city,name,business,address,phone,website)

    return report


# ==============================
# GST STYLE BUSINESS SEARCH
# ==============================

def gst_search():

    report="\nPossible GST Businesses\n"

    today=datetime.now().strftime("%d %B %Y")

    for city in cities:

        for keyword in gst_keywords:

            data=requests.get(
            "https://maps.googleapis.com/maps/api/place/textsearch/json",
            params={
                "query":f"{keyword} in {city}",
                "key":GOOGLE_API_KEY
            }).json()

            for place in data.get("results",[])[:3]:

                name=place.get("name","")
                address=place.get("formatted_address","")
                pid=place.get("place_id","")

                details=requests.get(
                "https://maps.googleapis.com/maps/api/place/details/json",
                params={
                    "place_id":pid,
                    "fields":"formatted_phone_number,website",
                    "key":GOOGLE_API_KEY
                }).json()

                phone=details.get("result",{}).get("formatted_phone_number","N/A")
                website=details.get("result",{}).get("website","N/A")

                report+=f"\n{name}\n{address}\nPhone:{phone}\n"

                save_lead(today,city,name,"GST Business",address,phone,website)

    return report


# ==============================
# INSTAGRAM BUSINESS DETECTION
# ==============================

def instagram_scan():

    report="\nInstagram New Business Signals\n"

    L=instaloader.Instaloader()

    for tag in instagram_tags:

        posts=instaloader.Hashtag.from_name(L.context,tag).get_posts()

        count=0

        for p in posts:

            if count > 5:
                break

            caption=str(p.caption).lower()

            if "opening" in caption or "launch" in caption:

                report+=f"\n@{p.owner_username}\n{p.url}\n"

                count+=1

    return report


# ==============================
# MAIN
# ==============================

message="Kerala Business Radar\n\n"

message+=google_search()

message+=gst_search()

message+=instagram_scan()

send_telegram(message)

print("Radar completed")