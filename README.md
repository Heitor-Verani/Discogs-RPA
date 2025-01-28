# Discogs RPA

This project is a Robotic Process Automation (RPA) to interact with the Discogs website and collect information about artists, albums, and songs.

## Description

The Discogs RPA allows the collection of data about Artists, Albums, and Songs from the Discogs website. It collects the list of albums by artists in order of the most successful albums. You can select by musical genre and the number of artists from whom you want to collect information.

## Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/Heitor-Verani/Discogs-RPA.git
    ```
2. Navigate to the project directory:
    ```bash
    cd Discogs-RPA
    ```
3. Create the virtual environment:
    ```bash
    poetry shell
    ```
4. Install the dependencies in the virtual environment:
    ```bash
    poetry install
    ```
5. To ensure the proper functioning of the proprietary package:
    ```bash
    pip install -e .
    ```

## Usage

1. Run the script in the main folder:
    ```bash
    python main.py
    ```
2. If desired, you can change the parameters in main.py

## parameters
    ```markdown
    - `genre` (str): The musical genre to scrape. Options are 'rock', 'electronic', 'jazz', 'hiphop', 'folkworldcountry'.
    - `num_artists_to_scrape` (int): The number of artists to scrape.
    - `num_albums_to_scrape_per_artist` (int): The number of albums to scrape per artist.
    - `num_albums_per_page` (int, optional): Number of albums per page (default is 250).
    - `full_albums_scrape` (bool, optional): Whether to scrape all albums for each artist (default is False).
    ```

## Contact

Heitor Verani - [heitorverani.work@gmail.com]

