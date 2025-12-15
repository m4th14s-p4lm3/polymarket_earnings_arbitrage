import requests


class TelegramBot:
    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{self.token}"

    def send_message(self, text):
        url = f"{self.api_url}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": text}
        response = requests.post(url, json=payload)
        return response.json()

    def edit_message(self, message_id, new_text):
        url = f"{self.api_url}/editMessageText"
        payload = {"chat_id": self.chat_id, "message_id": message_id, "text": new_text}
        response = requests.post(url, json=payload)
        return response.json()

    def delete_message(self, message_id):
        url = f"{self.api_url}/deleteMessage"
        payload = {"chat_id": self.chat_id, "message_id": message_id}
        response = requests.post(url, json=payload)
        return response.json()


# Usage
if __name__ == "__main__":
    TOKEN = None
    CHAT_ID = None
    bot = TelegramBot(TOKEN, CHAT_ID)

    message = "Progress: 0 %"
    response = bot.send_message(message)
    message_id = response["result"]["message_id"]

    print(response)

    import time

    for i in range(101):
        time.sleep(0.5)
        bot.edit_message(message_id, f"Progress: {i} %")
