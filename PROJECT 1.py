import requests
from bs4 import BeautifulSoup
import os
import re
import csv

Index_url = "https://books.toscrape.com/"
Category_Url_Path = "catalogue/category/books/"

def get_category_urls(base_url):
    response = requests.get(base_url)
    if not response.ok:
        print("Website unavailable or wrong URL...")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    category_list = soup.select_one('.nav.nav-list ul')
    if not category_list:
        print("No category list found...")
        return []

    categories = category_list.find_all('a')
    category_urls = {cat.get_text(strip=True): base_url + cat['href'] for cat in categories}

    return category_urls


def clean_description(description):
    # Ensures the description is readable
    description = re.sub(r'[^\x20-\x7E]', '', description)
    return description

def clean_price(price):
    # Remove any characters that are not digits or decimal point
    return re.sub(r'[^\d.]+', '', price)

def get_books_data(URL):
    
    # Get the URL and check response
    response = requests.get(URL)
    response.encoding = 'utf-8'
    data_all = {}

    if response.ok:
        soup = BeautifulSoup(response.text, "html.parser")
    
    # Scrape the relevant data through the HTML elements
    upc = soup.select_one("th:contains('UPC') + td").text
    title = soup.select_one("div.product_main h1").text
    price_incl_tax = clean_price(soup.select_one("th:contains('Price (incl. tax)') + td").text)
    price_excl_tax = clean_price(soup.select_one("th:contains('Price (excl. tax)') + td").text)
    number_available = soup.select_one("th:contains('Availability') + td").text
    product_description = clean_description(soup.select_one("#product_description + p").text)
    category = soup.select_one(".breadcrumb li:nth-child(3) a").text.strip()
    review_rating = soup.select_one(".star-rating")["class"][1] if soup.select_one(".star-rating") else "No rating"
    image_url = Index_url + soup.select_one("div.item.active img")["src"].lstrip("../")
    
    # Create a dictonnary with all relevant data
    data_all = {
            "Product Page URL": URL,
            "UPC": upc,
            "Title": title,
            "Price Including Tax": price_incl_tax,
            "Price Excluding Tax": price_excl_tax,
            "Number Available": number_available,
            "Product Description": product_description,
            "Category": category,
            "Review Rating": review_rating,
            "Image URL": image_url
        }

    return data_all

# Save data in an image directory and have each category in his own directory

def download_and_save_image(image_url, category_name, book_number):
    response = requests.get(image_url)
    if response.ok:
        # Create directory for the images if it doesn't exist
        category_dir = f"images/{category_name.replace(' ', '_').lower()}"
        os.makedirs(category_dir, exist_ok=True)
        
        # Format the file with name of category and the number of the book
        filename = f"{category_dir}/{category_name.replace(' ', '_').lower()}_{book_number}.jpg"
        
        # Write the image file into the directory
        with open(filename, 'wb') as file:
            file.write(response.content)
        print(f"Image saved: {filename}")

# Handle pagination in cases of multiple pages in a category

def get_books_page(category_url):
    book_categories = []
    current_page = 1
    page_url = category_url

    while True:
        response = requests.get(page_url)
        if not response.ok:
            break

        soup = BeautifulSoup(response.text, 'html.parser')
        book_links = soup.find_all('h3')
        if not book_links:
            break

        for link in book_links:
            a_tag = link.find('a')
            if a_tag and 'href' in a_tag.attrs:
                book_url = a_tag['href']
                book_url = Index_url + 'catalogue/' + book_url.replace('../', '')
                book_categories.append(book_url)

        # Extract the page number from the URL
        page_number_match = re.search(r'page-(\d+)\.html', page_url)
        if page_number_match:
            current_page = int(page_number_match.group(1))

        # Goto the URL for the next page
        if current_page < 10:
            page_url = category_url.replace('index.html', f'page-{current_page + 1}.html')
        else:
            page_url = category_url.replace('index.html', f'page-{current_page + 1}/index.html')

    return book_categories

# Call the scraping and pagination handling

def scrape_books_category(category_url):
    book_urls = get_books_page(category_url)
    all_books_data = []

    for book_url in book_urls:
        book_data = get_books_data(book_url)
        if book_data:  
            all_books_data.append(book_data)

    return all_books_data

# Save the data to the format required: CSV

def save_data_to_csv(data, filename):
    fieldnames = [
        'Product Page URL', 'UPC', 'Title', 'Price Including Tax', 
        'Price Excluding Tax', 'Number Available', 'Product Description', 
        'Category', 'Review Rating', 'Image URL'
    ]
    
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        
        for book_data in data:
            writer.writerow(book_data)

# Calling all relevant functions and saving to CSV

def scrape_and_save_categories(category_urls):
    for name, category_url in category_urls.items():
        print(f"Scraping category...: {name}")
        books_data = scrape_books_category(category_url)
        book_number = 1  # Initialize book number for image filenames
        if books_data:
            filename = f"{name.replace(' ', '_').lower()}_books.csv"
            for book_data in books_data:
                # Download and save each book's image
                download_and_save_image(book_data["Image URL"], name, book_number)
                book_number += 1  # Add book number for the next image
            save_data_to_csv(books_data, filename)
            print(f"Data for category '{name}' saved to {filename}! Continuing scraping...")
        else:
            print(f"No data found for category '{name}'...")

# Main execution, useful only if running locally            
if __name__ == "__main__":
    category_urls = get_category_urls(Index_url)
    scrape_and_save_categories(category_urls)
