import logging
from selenium import webdriver
from selenium.webdriver.firefox.options import Options  # Import Options para Firefox
from time import sleep
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import re
import hashlib
import json
from datetime import datetime

# Configure logging for general errors
general_logger = logging.getLogger('general')
general_handler = logging.FileHandler('logs/general_errors.log')
general_handler.setLevel(logging.ERROR)
general_handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(message)s'))
general_logger.addHandler(general_handler)

# Configure a separate logger for NoSuchElementException
no_such_element_logger = logging.getLogger('NoSuchElementException')
no_such_element_handler = logging.FileHandler('logs/no_such_element_errors.log')
no_such_element_handler.setLevel(logging.ERROR)
no_such_element_handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(message)s'))
no_such_element_logger.addHandler(no_such_element_handler)

class DiscogsScraper:
    ALBUM_TABLE_XPATH = '/html/body/div[2]/div/div/div/div[2]/div[3]/section/div/table/tbody/tr[1]'
    HEADER_XPATH_TEMPLATE = '/html/body/div[2]/div/div/div/div[2]/div[2]/div/div[2]/table/tbody/tr[{}]/th/h2'
    LINK_XPATH_TEMPLATE = '/html/body/div[2]/div/div/div/div[2]/div[2]/div/div[2]/table/tbody/tr[{}]/td/a[{}]'

    def __init__(self, genre, num_artists_to_scrape, num_albums_to_scrape_per_artist, num_albums_per_page=250, full_albums_scrape=False):
        """
        Initialize the DiscogsScraper with the given parameters.

        :param genre: Genre to scrape
        :param num_artists_to_scrape: Number of artists to scrape
        :param num_albums_to_scrape_per_artist: Number of albums to scrape per artist
        :param num_albums_per_page: Number of albums per page
        :param full_albums_scrape: Whether to scrape all albums
        """
        self.genre = genre
        self.num_artists_to_scrape = num_artists_to_scrape
        self.num_albums_to_scrape_per_artist = num_albums_to_scrape_per_artist
        self.num_albums_per_page = num_albums_per_page
        self.full_albums_scrape = full_albums_scrape
        self.artists = []

        # Configure the driver in headless mode
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        self.driver = webdriver.Firefox(options=options)
        
        # Create JSONL files with current date and minute in the name
        current_time = datetime.now().strftime("%Y%m%d_%H%M")
        self.artists_file = f'data/artist_data/artists_{current_time}.jsonl'
        self.albums_file = f'data/album_data/albums_{current_time}.jsonl'
        self.songs_file = f'data/song_data/songs_{current_time}.jsonl'
        
        # Initialize the files
        open(self.artists_file, 'w').close()
        open(self.albums_file, 'w').close()
        open(self.songs_file, 'w').close()

    def wait_for_element(self, xpath, timeout=10):
        """
        Wait for an element to be present on the page.

        :param xpath: XPATH of the element to wait for
        :param timeout: Maximum time to wait for the element
        :return: The element if found, None otherwise
        """
        try:
            return WebDriverWait(self.driver, timeout).until(EC.visibility_of_element_located((By.XPATH, xpath)))
        except TimeoutException:
            general_logger.error(f"Element not found: {xpath}")
            return None
        
    def close_cockies(self):
        try:
            button = self.wait_for_element('//*[@id="onetrust-reject-all-handler"]', 5)
            button.click()
        except NoSuchElementException:
            pass
        except Exception as e:
            raise

    def select_genre(self):
        """
        Select the genre for scraping.
        """
        genre_map = {
            'rock': 'Rock',
            'electronic': 'Electronic',
            'jazz': 'Jazz',
            'hiphop': 'HipHop',
            'folkworldcountry': 'FolkWorldCountry'
        }
        genre = genre_map.get(self.genre.lower())
        self.driver.get(f'https://www.discogs.com/search/?limit={self.num_albums_per_page}&genre_exact={genre}&sort=have%2Cdesc&ev=gs_mc&page=1')
        sleep(0.5)

    def scrape_artist_details(self, artist_name, artist_url):
        """
        Scrape details of a specific artist.

        :param artist_name: Name of the artist
        :param artist_url: URL of the artist's page
        :return: Dictionary containing artist data
        """
        artist_data = {
            'artist_id': self.generate_hash(artist_name),
            'name': artist_name,
            'artist_principal_genre': self.genre,
            'discogs_url': artist_url,
            'artist_real_name': None,
            'sites': [],
            'members': [],
            'num_total_albums': None
        }
        self.wait_for_element('/html/body/div[2]/div/div/div/div[2]/div[2]/div/div[2]/h1', 1)
        self.extract_artist_info(artist_data)
        self.extract_artist_albums(artist_data)
        self.driver.close()
        self.driver.switch_to.window(self.driver.window_handles[0])
        self.save_artist(artist_data)
        return artist_data

    def extract_artist_info(self, artist_data):
        """
        Extract artist information from the page.

        :param artist_data: Dictionary to store artist data
        """
        for i in range(1, 10):
            try:
                header = self.driver.find_element(By.XPATH, f'/html/body/div[2]/div/div/div/div[2]/div[2]/div/div[2]/div[2]/table/tbody/tr[{i}]/th/h2')
                if header.text in ['Real Name:', 'Sites:', 'Members:']:
                    self.process_artist_header(header, artist_data, i)
            except NoSuchElementException as e:
                no_such_element_logger.error(e)
                break
            except Exception as e:
                raise

    def extract_artist_albums(self, artist_data):
        """
        Extract albums of a specific artist.

        :param artist_data: Dictionary to store artist data
        """
        try:
            albums_button = self.wait_for_element('/html/body/div[2]/div/div/div/div[4]/div[1]/div[1]/div/div[1]/button[2]/p', 3)
            if albums_button and albums_button.text == 'Albums':
                artist_data['num_total_albums'] = int(self.driver.find_element(By.XPATH, '/html/body/div[2]/div/div/div/div[4]/div[1]/div[1]/div/div[1]/button[2]/span').text)
                if artist_data['num_total_albums'] > 0:
                    self.scrape_albums(artist_data)
        except Exception as e:
            general_logger.error(f"Error getting artist albums: {e}")

    def process_artist_header(self, header, artist_data, i):
        """
        Process the artist header to extract relevant data.

        :param header: Header element
        :param artist_data: Dictionary to store artist data
        :param i: Index of the header
        """
        count = 1
        while True:
            try:
                link = self.driver.find_element(By.XPATH, f'/html/body/div[2]/div/div/div/div[2]/div[2]/div/div[2]/div[2]/table/tbody/tr[{i}]/td/a[{count}]')
                if header.text == 'Real Name:':
                    artist_data['artist_real_name'] = link.text
                elif header.text == 'Sites:':
                    artist_data['sites'].append(link.get_attribute('href'))
                elif header.text == 'Members:':
                    artist_data['members'].append(re.sub(r"\(\d+\)", "", link.text))
                count += 1
            except NoSuchElementException as e:
                no_such_element_logger.error(e)
                break

    def scrape_albums(self, artist_data):
        """
        Scrape albums of a specific artist.

        :param artist_data: Dictionary to store artist data
        """
        if self.full_albums_scrape:
            self.num_albums_to_scrape_per_artist = artist_data['num_total_albums']
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", self.driver.find_element(By.XPATH, '/html/body/div[2]/div/div/div/div[4]/div[1]/div[1]/div/div[1]/button[2]/p'))
        self.driver.find_element(By.XPATH, '/html/body/div[2]/div/div/div/div[4]/div[1]/div[1]/div/div[1]/button[2]/p').click()
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", self.driver.find_element(By.XPATH, '//*[@id="show"]'))
        Select(self.driver.find_element(By.XPATH, '//*[@id="show"]')).select_by_value('500')
        self.wait_for_element(f'/html/body/div[2]/div/div/div/div[4]/div[1]/div[2]/div[2]/table/tbody/tr[1]/td[3]/a', 10)
        count = 1
        for album in range(1, artist_data['num_total_albums'] + 1):
            if count > self.num_albums_to_scrape_per_artist or album == 500 or album > artist_data['num_total_albums']:
                break
            try:
                album_link = self.driver.find_element(By.XPATH, f'/html/body/div[2]/div/div/div/div[4]/div[1]/div[2]/div[2]/table/tbody/tr[{album}]/td[3]/a')
                if album_link:
                    album_name = album_link.text
                    record_label = self.driver.find_element(By.XPATH, f'/html/body/div[2]/div/div/div/div[4]/div[1]/div[2]/div[2]/table/tbody/tr[{album}]/td[4]/a[1]').text
                    self.driver.execute_script(f"window.open('{album_link.get_attribute('href')}', '_blank');")
                    self.driver.switch_to.window(self.driver.window_handles[-1])
                    album_data = self.get_album_data(artist_data, album_name, record_label)
                    self.save_album(album_data)
                    self.scrap_song(album_data)
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[1])
                    count += 1
            except NoSuchElementException as e:
                no_such_element_logger.error(e)
            except Exception as e:
                general_logger.error(f"Error scraping album: {e}")

    def get_album_data(self, artist_data, album_name, record_label):
        """
        Scrape album data from the page.

        :param artist_data: Dictionary to store artist data
        :param album_name: Name of the album
        :param record_label: Record label of the album
        :return: Dictionary containing album data
        """
        album_data = {
            "artist_id": artist_data["artist_id"],
            "album_id": self.generate_hash(f'{artist_data["name"]}{album_name}'),
            "album_name": album_name,
            "album_genre": [],
            "album_style": [],
            "album_year": None,
            "record_label": record_label
        }
        self.wait_for_element(self.ALBUM_TABLE_XPATH)
        for i in range(1, 10):
            try:
                header = self.driver.find_element(By.XPATH, self.HEADER_XPATH_TEMPLATE.format(i))
                if header.text in ['Label:', 'Genre:', 'Style:', 'Year:', 'Released:']:
                    self.process_album_header(header, album_data, i)
            except NoSuchElementException as e:
                no_such_element_logger.error(e)
                break
            except Exception as e:
                general_logger.error(f'Unexpected error in header data: {e}')
                raise
        return album_data

    def process_album_header(self, header, album_data, i):
        """
        Process the album header to extract relevant data.

        :param header: Header element
        :param album_data: Dictionary to store album data
        :param i: Index of the header
        """
        count = 1
        while True:
            try:
                link = self.driver.find_element(By.XPATH, self.LINK_XPATH_TEMPLATE.format(i, count))
                if header.text in ['Year:', 'Released:']:
                    album_data['album_year'] = link.text
                    break
                elif header.text == 'Genre:':
                    album_data['album_genre'].append(link.text)
                elif header.text == 'Style:':
                    album_data['album_style'].append(link.text)
                count += 1
            except NoSuchElementException as e:
                no_such_element_logger.error(e)
                break

    def scrap_song(self, album_data):
        """
        Scrape song data from the album page.

        :param album_data: Dictionary containing album data
        """
        self.wait_for_element(self.ALBUM_TABLE_XPATH, 20)
        count = 1
        track_number = 1
        sub_track_first_name = ''
        while True:
            music = {
                "album_id": album_data['album_id'],
                'album_name': album_data["album_name"],
                'music_name': None,
                'music_duration': None,
                'music_number_on_album': None
            }
            try:
                row = self.driver.find_element(By.XPATH, f'/html/body/div[2]/div/div/div/div[2]/div[3]/section/div/table/tbody/tr[{count}]')
                row_class = row.get_attribute("class")
                if row_class == "":
                    music['music_name'] = row.find_element(By.XPATH, f'td[3]').text
                    music['music_duration'] = row.find_element(By.XPATH, f'td[4]').text or None
                    music['music_number_on_album'] = track_number
                    track_number += 1
                elif row_class == "heading_lgT5E":
                    pass
                elif row_class == "index_1zun9":
                    sub_track_first_name = row.find_element(By.XPATH, f'td[3]').text
                elif row_class == "subtrack_24C3X":
                    music['music_name'] = f'{sub_track_first_name}: {row.find_element(By.XPATH, f'td[3]').text}'
                    music['music_duration'] = row.find_element(By.XPATH, f'td[4]').text or None
                    music['music_number_on_album'] = track_number
                    track_number += 1
                count += 1
                if music['music_name']:
                    self.save_music(music)
            except NoSuchElementException as e:
                no_such_element_logger.error(e)
                break
            except Exception as e:
                raise

    def next_genre_page(self):
        """
        Navigate to the specified element and click it.
        """
        try:
            element = self.driver.find_element(By.XPATH, '/html/body/div[1]/div[3]/div[3]/div[2]/nav[1]/form/div[1]/ul/li[2]/a')
            if element:
                element.click()
                self.wait_for_element('/html/body/div[1]/div[3]/div[3]/div[2]/nav[1]/form/div[1]/ul/li[2]/a', 5)
        except Exception as e:
            general_logger.error(f"Error navigating to and clicking the element: {e}")
            raise e

    def save_music(self, music):
        """
        Save music data to a file.

        :param music: Dictionary containing music data
        """
        with open(self.songs_file, 'a') as file:
            file.write(json.dumps(music) + '\n')

    def save_artist(self, artist):
        """
        Save artist data to a file.

        :param artist: Dictionary containing artist data
        """
        with open(self.artists_file, 'a') as file:
            file.write(json.dumps(artist) + '\n')

    def save_album(self, album):
        """
        Save album data to a file.

        :param album: Dictionary containing album data
        """
        with open(self.albums_file, 'a') as file:
            file.write(json.dumps(album) + '\n')

    def generate_hash(self, text):
        """
        Generate a hash for the given text.

        :param text: Text to hash
        :return: Hashed text
        """
        try:
            cleaned_text = text.replace(" ", "").lower().strip()
            return hashlib.sha256(cleaned_text.encode('utf-8')).hexdigest()
        except Exception as e:
            raise

    def scraping_discogs(self):
        """
        Main method to start scraping Discogs.
        """
        try:
            self.select_genre()
            self.close_cockies()
            i = 1
            while len(self.artists) < self.num_artists_to_scrape:
                if i > 250:
                    i = 1
                    self.next_genre_page()
                try:
                    artist = self.driver.find_element(By.XPATH, f'/html/body/div[1]/div[3]/div[3]/div[2]/ul/li[{i}]/div[2]/span/a')
                    if not any(item['artist_id'] == self.generate_hash(artist.text) for item in self.artists):
                        self.driver.execute_script(f"window.open('{artist.get_attribute('href')}', '_blank');")
                        name = artist.text
                        url = artist.get_attribute('href')
                        self.driver.switch_to.window(self.driver.window_handles[-1])
                        self.artists.append(self.scrape_artist_details(name, url))
                except NoSuchElementException as e:
                    no_such_element_logger.error(f"Unexpected error: Artist page not found at index /html/body/div[1]/div[3]/div[3]/div[2]/ul/li[{i}]/div[2]/span/a")
                    raise 
                except Exception as e:
                    general_logger.error(f"Unexpected error getting artist page: {e}")
                    raise 
                finally:
                    i += 1
        except Exception as e:
            general_logger.error(f"Unexpected error starting the process: {e}")
            raise
        finally:
            self.driver.quit()
