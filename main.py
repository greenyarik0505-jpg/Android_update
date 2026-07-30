from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.clock import mainthread
import requests
import urllib.parse
import json
import os
import threading
import time
import random

CONFIG_FILE = "brawl_updater_config.json"

CLUBS = {
    "Dark Brotherhood": {
        "tag": "#809L8LRUL",
        "firebase": "https://dark-club-57e07-default-rtdb.europe-west1.firebasedatabase.app",
        "web_api_key": "AIzaSyCh14CMKFKwVqtEz6s9mSxKyMmxoEFscFc"
    },
    "Holy Empire (Священная Империя)": {
        "tag": "#2QCLRR800",
        "firebase": "https://brawlclub-432dd-default-rtdb.europe-west1.firebasedatabase.app",
        "web_api_key": "AIzaSyDzvGVlyssX3t-ZZJzmdydaiY-nBKBou7c"
    }
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_config(data):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print("Failed to save config:", e)


def get_brawl_stars_members(api_key, club_tag):
    tag = urllib.parse.quote(club_tag)
    url = f"https://api.brawlstars.com/v1/clubs/{tag}/members"
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    r = requests.get(url, headers=headers, timeout=15)
    if r.status_code == 200:
        return r.json().get("items", [])
    raise Exception(f"Brawl Stars API Error {r.status_code}: {r.text}")


def get_firebase_token(web_api_key, email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={web_api_key}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    r = requests.post(url, json=payload, timeout=15)
    if r.status_code == 200:
        return r.json().get("idToken")
    err = r.json().get("error", {}).get("message", r.text)
    raise Exception(f"Firebase sign-in error: {err}")


def get_firebase_data(firebase_url):
    url = f"{firebase_url.rstrip('/')}/brawlClubData.json"
    r = requests.get(url, timeout=15)
    if r.status_code == 200:
        data = r.json()
        if not data:
            raise Exception("Firebase DB is empty")
        return data
    raise Exception(f"Firebase API Error {r.status_code}: {r.text}")


def update_firebase_data(firebase_url, new_data, id_token):
    url = f"{firebase_url.rstrip('/')}/brawlClubData.json?auth={id_token}"
    r = requests.put(url, json=new_data, timeout=20)
    if r.status_code != 200:
        raise Exception(f"Firebase Update Error {r.status_code}: {r.text}")


class UpdaterLayout(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=12, spacing=8, **kwargs)
        self.config = load_config()

        self.add_widget(Label(text='⚡ BRAWL STARS SYNC (Android)', size_hint_y=None, height=40))

        self.club_spinner = Spinner(text=list(CLUBS.keys())[0], values=list(CLUBS.keys()), size_hint_y=None, height=44)
        self.club_spinner.bind(text=self.on_club)
        self.add_widget(self.club_spinner)

        self.api_input = TextInput(hint_text='Brawl Stars API Key', multiline=False, size_hint_y=None, height=44)
        self.add_widget(self.api_input)

        self.email_input = TextInput(hint_text='Firebase admin email', multiline=False, size_hint_y=None, height=44)
        self.add_widget(self.email_input)

        self.pass_input = TextInput(hint_text='Firebase password', password=True, multiline=False, size_hint_y=None, height=44)
        self.add_widget(self.pass_input)

        self.tag_label = Label(text='Tag: ' + CLUBS[self.club_spinner.text]['tag'], size_hint_y=None, height=30)
        self.add_widget(self.tag_label)

        self.fb_label = Label(text='Firebase: ' + CLUBS[self.club_spinner.text]['firebase'], size_hint_y=None, height=30)
        self.add_widget(self.fb_label)

        self.update_btn = Button(text='🚀 FULL SYNC', size_hint_y=None, height=48)
        self.update_btn.bind(on_release=self.on_update)
        self.add_widget(self.update_btn)

        # load saved
        data = self.config.get(self.club_spinner.text, {})
        self.api_input.text = data.get('api_key', '')
        self.email_input.text = data.get('fb_email', '')
        self.pass_input.text = data.get('fb_password', '')

    def on_club(self, spinner, text):
        # save previous
        # load
        self.tag_label.text = 'Tag: ' + CLUBS[text]['tag']
        self.fb_label.text = 'Firebase: ' + CLUBS[text]['firebase']
        data = self.config.get(text, {})
        self.api_input.text = data.get('api_key', '')
        self.email_input.text = data.get('fb_email', '')
        self.pass_input.text = data.get('fb_password', '')

    def show_popup(self, title, message):
        content = BoxLayout(orientation='vertical')
        content.add_widget(Label(text=message))
        btn = Button(text='OK', size_hint_y=None, height=40)
        content.add_widget(btn)
        popup = Popup(title=title, content=content, size_hint=(0.9, 0.6))
        btn.bind(on_release=popup.dismiss)
        popup.open()

    def on_update(self, *args):
        selected = self.club_spinner.text
        api_key = self.api_input.text.strip()
        club_tag = CLUBS[selected]['tag']
        firebase_url = CLUBS[selected]['firebase']
        fb_email = self.email_input.text.strip()
        fb_pass = self.pass_input.text.strip()
        web_api_key = CLUBS[selected]['web_api_key']

        if not api_key or not fb_email or not fb_pass:
            self.show_popup('Error', 'Fill all fields (API key, email, password)')
            return

        # save
        self.config[selected] = {'api_key': api_key, 'fb_email': fb_email, 'fb_password': fb_pass}
        save_config(self.config)

        self.update_btn.disabled = True
        threading.Thread(target=self.sync_thread, args=(api_key, club_tag, firebase_url, fb_email, fb_pass, web_api_key, selected), daemon=True).start()

    def sync_thread(self, api_key, club_tag, firebase_url, fb_email, fb_pass, web_api_key, selected_club):
        try:
            id_token = get_firebase_token(web_api_key, fb_email, fb_pass)
            bs_members = get_brawl_stars_members(api_key, club_tag)
            fb_data = get_firebase_data(firebase_url)

            role_map = {"president":"Президент","vicePresident":"Вице-президент","senior":"Ветеран","member":"Участник"}
            fb_members = fb_data.get('members', [])
            old_map = {m.get('name',''): m for m in fb_members}

            new_members = []
            added = 0
            updated = 0

            for i, m in enumerate(bs_members):
                name = m.get('name','Unknown')
                trophies = m.get('trophies', 0)
                ru = role_map.get(m.get('role','member'), 'Участник')
                if name in old_map:
                    old = old_map[name]
                    if old.get('trophies') != trophies or old.get('role') != ru:
                        updated += 1
                    old['trophies'] = trophies
                    old['role'] = ru
                    new_members.append(old)
                    del old_map[name]
                else:
                    added += 1
                    new_members.append({'id': f"m_auto_{int(time.time())}_{i}_{random.randint(100,999)}", 'name':name, 'role':ru, 'trophies':trophies, 'avatar':'👤'})

            removed = len(old_map)
            fb_data['members'] = new_members
            update_firebase_data(firebase_url, fb_data, id_token)

            msg = f"Sync complete! Updated: {updated}, Added: {added}, Removed: {removed}"
            self._show_result('Success', msg)
        except Exception as e:
            self._show_result('Error', str(e))
        finally:
            self._enable_button()

    @mainthread
    def _show_result(self, title, message):
        self.show_popup(title, message)

    @mainthread
    def _enable_button(self):
        self.update_btn.disabled = False


class BrawlApp(App):
    def build(self):
        return UpdaterLayout()


if __name__ == '__main__':
    BrawlApp().run()

