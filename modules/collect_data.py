"""
This module is used to gather data for analysis using thehiddenwiki.org.
"""
import csv
import datetime
import uuid
import requests
import os

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from .link import LinkNode
from .utils import multi_thread
from .utils import find_file
from threading import Lock


dev_file = find_file("torbot_dev.env", "/home")
if not dev_file:
    raise FileNotFoundError
load_dotenv(dotenv_path=dev_file)


def parse_links(html):
    soup = BeautifulSoup(html, 'html.parser')
    entries = soup.find('div', attrs={'class': 'entry'})
    tags = entries.find_all('a')
    return [tag['href'] for tag in tags if LinkNode.valid_link(tag['href'])]


class ThreadSafeCSVWriter:
    def __init__(self, csv_stream, fieldnames):
        self._csv = csv_stream
        self._writer = csv.DictWriter(self._csv, fieldnames=fieldnames)
        if fieldnames:
            self._writer.writeheader()
        self._mutex = Lock()

    def writerow(self, value):
        with self._mutex:
            self._writer.writerow(value)


def collect_data():
    resp = requests.get('https://thehiddenwiki.org')
    links = parse_links(resp.content)
    time_stamp = datetime.datetime.now().isoformat()
    data_path = os.getenv('TORBOT_DATA_DIR')
    file_path = f'{data_path}/torbot_{time_stamp}.csv'
    with open(file_path, 'w', newline='') as outcsv:
        writer = ThreadSafeCSVWriter(outcsv, fieldnames=['ID',
                                                         'Title',
                                                         'Meta Tags',
                                                         'Content'])
        def handle_link(link):
            response = requests.get(link)
            body = response.content
            soup = BeautifulSoup(body, 'html.parser')
            title = soup.title.getText() if soup.title else 'No Title'
            meta_tags = soup.find_all('meta')
            entry = {
                "ID": uuid.uuid4(),
                "Title": title.strip(),
                "Meta Tags": meta_tags,
                "Content": body
            }
            print(entry)
            writer.writerow(entry)

        multi_thread(links, handle_link)
