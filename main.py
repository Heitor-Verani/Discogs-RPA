from discogs_rpa.discogs_scraper import DiscogsScraper
from webdriver_manager.firefox import GeckoDriverManager

def main():
    GeckoDriverManager().install()
    scraper = DiscogsScraper(genre='rock', num_artists_to_scrape=10, num_albums_to_scrape_per_artist=10)
    scraper.scraping_discogs()

if __name__ == "__main__":
    main()