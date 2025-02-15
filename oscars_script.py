from bs4 import BeautifulSoup
import pandas as pd
import argparse
import numpy as np
from slugify import slugify
import requests
import os

def fetch_oscars_data(file_path: str) -> pd.DataFrame:
    """
    Fetches and parses Oscars data from an HTML file.
    Args:
        file_path (str): The path to the HTML file containing the Oscars data.
    Returns:
        pd.DataFrame: A DataFrame containing the parsed Oscars data with columns:
                      'Category', 'Honoree', 'Film', and 'Winner'.
    """
    # Read the HTML file content
    with open(file_path, 'r', encoding='utf-8') as file:
        html = file.read()

    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')

    # Handle the current year's layout
    categories = soup.find_all('div', class_='paragraph--type--award-category')
    
    data = []
    for category in categories:
        category_name = category.find('div', class_='field--name-field-award-category-oscars').text.strip()
        
        honorees = category.find_all('div', class_='paragraph--type--award-honoree')
        for honoree in honorees:
            honoree_type = honoree.find('div', class_='field--name-field-honoree-type').text.strip()
            honoree_name = honoree.find('div', class_='field--name-field-award-entities').text.strip()
            film_name = honoree.find('div', class_='field--name-field-award-film').text.strip()
            
            if category_name in {"International Feature Film", "Music (Original Song)"}:
                honoree_name, film_name = film_name, honoree_name
                if category_name == "Music (Original Song)":
                    film_name = film_name.split('from ')[1].split(';')[0].strip()
            
            is_winner = honoree_type == "Winner"
            data.append([category_name, honoree_name, film_name, is_winner])
    
    return pd.DataFrame(data, columns=['Category', 'Honoree', 'Film', 'Winner'])

def get_film_slugs(data: pd.DataFrame, slug_replacements: dict={}) -> dict:
    """
    Returns the unique slugified films from the Oscars data.
    Args:
        data (pd.DataFrame): The Oscars data DataFrame.
        slug_replacements (dict): A dictionary of slug replacements for specific films.
        
    Returns:
        dict: A dictionary with slugified film names as keys and original film names as values.
    """
    return {slug_replacements.get(slug := slugify(film), slug): film for film in data['Film'].unique()}
    

def get_mubi_data(film_slug: str, film_name: str) -> pd.DataFrame:
    url = f"https://mubi.com/en/films/{film_slug}/awards"

    # Fetch the HTML content of the page using requests
    response = requests.get(url)
    response.raise_for_status()  # Ensure we notice bad responses
    html = response.text

    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')

     # Extract ceremony name and award name
    data = []
    awards = soup.find_all('div', class_='css-si2n6f')
    for award in awards:
        ceremony_name = award.find('a', class_='css-pgwez').text.strip()
        award_name = award.find('div', class_='css-16kkjs').text.strip()
        year, name = award_name.split('|')
        year = year.strip()
        name = name.strip()
        data.append([film_name, ceremony_name, name, year])

    return pd.DataFrame(data, columns=['Film', 'Ceremony', 'Award', 'Year'])

def fetch_mubi_data_for_films(film_slugs: dict) -> pd.DataFrame:
    """
    Fetches Mubi awards data for the given film slugs.
    Args:
        film_slugs (dict): A dictionary with slugified film names as keys and original film names as values.
    Returns:
        pd.DataFrame: A DataFrame containing the Mubi awards data with columns:
                      'Film', 'Ceremony', 'Award', and 'Year'.
    """
    all_data = []
    for slug, film in film_slugs.items():
        print(f"Fetching: {slug}")
        try:
            film_data = get_mubi_data(slug, film)
            all_data.append(film_data)
        except Exception as e:
            print(f"Failed to fetch data for film slug '{slug}': {e}")
    
    if all_data:
        return pd.concat(all_data, ignore_index=True)
    else:
        return pd.DataFrame(columns=['Film', 'Ceremony', 'Award', 'Year'])

def main():
    parser = argparse.ArgumentParser(description="Fetch Oscars data from a local HTML file.")
    parser.add_argument("file_path", type=str, help="Path to the local HTML file")
    args = parser.parse_args()
    
    # Create a new folder based on the file_path name
    folder_name = os.path.splitext(os.path.basename(args.file_path))[0]
    os.makedirs(folder_name, exist_ok=True)

    # Get Nominee Data
    df = fetch_oscars_data(args.file_path)
    nominees_csv_path = os.path.join(folder_name, 'nominees.csv')
    df.to_csv(nominees_csv_path, index=False)
    print(f"Nominee data has been exported to '{nominees_csv_path}'")

    # Get Award Data
    slug_replacements = {
        "in-the-shadow-of-the-cypress": "in-the-shadow-of-cypress",
        "i-m-still-here": "i-m-still-here-2024",
        "incident": "incident-2023",
        "sing-sing": "sing-sing-2023",
        "the-apprentice": "the-apprentice-2025",
        "wicked": "wicked-2024",
        "flow": "flow-2024",
        "maria": "maria-2024",
        "nosferatu": "nosferatu-391740",
        "the-six-triple-eight": "six-triple-eight",
        "elton-john-never-too-late": "goodbye-yellow-brick-road-the-final-elton-john-performances-and-the-years-that-made-his-legend",
        "nickel-boys": "the-nickel-boys",
        "i-m-not-a-robot": "i-m-not-a-robot-2023"
    }

    slugs = get_film_slugs(df, slug_replacements)
    award_data = fetch_mubi_data_for_films(slugs)
    award_data_csv_path = os.path.join(folder_name, 'awards_data.csv')
    award_data.to_csv(award_data_csv_path, index=False)
    print(f"Awards data has been exported to '{award_data_csv_path}'")

if __name__ == "__main__":
    main()