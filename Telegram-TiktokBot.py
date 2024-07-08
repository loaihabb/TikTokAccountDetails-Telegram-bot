import os
import re
import json
from bs4 import BeautifulSoup
import requests
import pycountry
from telegram import Update
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext


class Users:
    URI_BASE = 'https://www.tiktok.com/'

    def __init__(self):
        self.user = ''
        self.status_code = ''

    def details(self, user):
        if not user:
            raise ValueError('Missing required argument: "user"')

        self.user = self.prepare(user)

        request_data = self.request()

        if self.status_code == 404:
            return 'This account cannot be found.'

        # Parse HTML using BeautifulSoup
        soup = BeautifulSoup(request_data, 'html.parser')
        #print(f"html.parser: {request_data}")

        # Find script tag containing data
        script_tag = soup.find('script',
                               id='__UNIVERSAL_DATA_FOR_REHYDRATION__')
        #print(f"script_tag: {script_tag}")
        if not script_tag:
            return 'Data extraction failed.'

        # Extract content inside script tag
        script_content = script_tag.string

        # Convert extracted content to JSON
        try:
            response = json.loads(script_content)
        except json.JSONDecodeError as e:
            print(f"JSON Decode Error: {e}")
            return 'Data extraction failed.'

        # Process extracted JSON data
        user_info = self.process_user_info(response)

        # Format the result for Telegram
        formatted_result = self.format_telegram_response(user_info)

        return formatted_result

    def request(self, method='GET', get_params=None):
        if get_params is None:
            get_params = {}

        headers = {
            'User-Agent':
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        url = f'{self.URI_BASE}@{self.user}/?lang=ru'

        print(f"Requesting URL: {url}")

        response = requests.get(url, headers=headers)

        self.status_code = response.status_code

        print(f"Response Status Code: {self.status_code}")

        return response.text

    def prepare(self, user):
        return re.sub(r'@', '', user, 1).lower()

    def extract(self, pattern, data):
        matches = re.search(pattern, data)
        if matches:
            try:
                json_data = matches.group(2)
                return json.loads(json_data)
            except json.JSONDecodeError as e:
                print(f"JSON Decode Error: {e}")
                return None
        return None

    def process_user_info(self, response):
        try:
            default_scope = response.get('__DEFAULT_SCOPE__', {})
            user_detail = default_scope.get('webapp.user-detail', {}).get('userInfo', {}).get('user', {})
            user_detail_stats = default_scope.get('webapp.user-detail', {}).get('userInfo', {}).get('stats', {})
            print(user_detail)
            if not user_detail:
                raise ValueError('User info not found or empty.')

            user_info = {
                'username': user_detail.get('nickname', 'Unknown'),
                'profile_name': user_detail.get('uniqueId', 'Unknown'),
                'avatar': user_detail.get('avatarMedium', 'Unknown'),
                'description': user_detail.get('signature', 'Unknown'),
                'region': user_detail.get('region', 'Unknown'),
                'verified': user_detail.get('verified', False),
                'following': user_detail_stats.get('followingCount', 0),
                'follower': user_detail_stats.get('followerCount', 0),
                'video': user_detail_stats.get('videoCount', 0),
                'like': user_detail_stats.get('heartCount', 0),
                'private': user_detail.get('privateAccount', False),
            }
            
            
            #print(f"Processed user_info: {user_info}")
            #print(f"Processed user_stats: {user_stats}")
            return user_info

        except Exception as e:
            print(f"Error processing user info: {str(e)}")
            return None

    def format_telegram_response(self, user_info):
        try:
            if not user_info:
                return 'Error processing user info.'

            region_code = user_info.get('region', 'Unknown')
            flag_emoji = self.get_flag_emoji(region_code)

            formatted_text = f"Username: {user_info.get('username', 'Unknown')}\n"
            formatted_text += f"Profile Name: {user_info.get('profile_name', 'Unknown')}\n"
            formatted_text += f"Avatar: {user_info.get('avatar', 'Unknown')}\n"
            formatted_text += f"Description: {user_info.get('description', 'Unknown')}\n"
            formatted_text += f"Region: {region_code} - {flag_emoji}\n"
            formatted_text += f"Verified: {user_info.get('verified', False)}\n"
            formatted_text += f"Following: {user_info.get('following', 0)}\n"
            formatted_text += f"Follower: {user_info.get('follower', 0)}\n"
            formatted_text += f"Video Count: {user_info.get('video', 0)}\n"
            formatted_text += f"Like Count: {user_info.get('like', 0)}"

            return formatted_text

        except Exception as e:
            print(f"Error formatting Telegram response: {str(e)}")
            return 'Error formatting Telegram response.'


    def get_flag_emoji(self, country_code):
        country = pycountry.countries.get(alpha_2=country_code)
        if country:
            flag_emoji = country.flag
            country_name = country.name
            return f"{country_name} - {flag_emoji}"
        else:
            return 'Unknown - 🌐'  # Default: unknown flag


def get_tiktok_details(update: Update, context: CallbackContext) -> None:
    username = update.message.text
    user_instance = Users()
    result = user_instance.details(username)
    update.message.reply_text(result, parse_mode=None)


def main():
    # Replace 'YOUR_BOT_TOKEN' with your actual bot token
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    updater = Updater(token=BOT_TOKEN, use_context=True)

    dp = updater.dispatcher

    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, get_tiktok_details))

    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    main()
