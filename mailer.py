import requests
from lxml import html
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# User-Agent headers to simulate browser request (avoid being blocked)
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8"
}

# URL of the Product Hunt homepage or specific product listing
url = "https://www.producthunt.com/"

# Function to get the database connection
def get_db_connection():
    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))  # Use the PostgreSQL URL from the .env file
        conn.autocommit = True  # Enable auto commit for the database connection
        return conn
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        return None

# Function to send email
def send_email(subject, body, recipient_email):
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")
    
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
        print(f"Email sent to {recipient_email}")
    except Exception as e:
        print(f"Error sending email to {recipient_email}: {e}")

# Function to send emails to subscribers
def send_emails_to_subscribers(products):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT email FROM subscribers')  # Only fetch the 'email' column to avoid index errors
    subscribers = cursor.fetchall()
    conn.close()

    for subscriber in subscribers:
        email = subscriber[0]  # Accessing by index since it's a tuple
        if email:
            subject = "Check Out Today's New Products on Product Hunt"
            body = "Hello, \n\nHere are the new products launched today on Product Hunt:\n\n"
            
            for product in products:
                body += f"{product['product']}\n{product['description']}\nLink: {product['link']}\n\n"
            
            send_email(subject, body, email)

# Send GET request to Product Hunt URL
response = requests.get(url, headers=headers)

# Parse the page content using lxml's html parser
tree = html.fromstring(response.content)

# XPath to locate the section containing the top products today
top_products_section = tree.xpath('//*[@data-test="homepage-section-0"]//section')

# Extract product details
if top_products_section:
    product_details = []

    # Loop through each product section
    for section in top_products_section:
        # Extract product name, description, and link
        product_name = section.xpath('.//a[contains(@class, "text-16 font-semibold text-dark-gray")]/text()')
        product_description = section.xpath('.//a[contains(@class, "text-16 font-normal text-dark-gray text-gray-700")]/text()')
        product_link = section.xpath('.//a[contains(@class, "text-16 font-normal text-dark-gray text-gray-700")]/@href')

        if product_name and product_description and product_link:
            product_details.append({
                'product': product_name[0].strip(),
                'description': product_description[0].strip(),
                'link': "https://www.producthunt.com" + product_link[0]
            })

    # Format the product details into an email message
    email_content = "Here are the latest products from Product Hunt:\n\n"
    
    for product in product_details:
        email_content += f"Product Name: {product['product']}\n"
        email_content += f"Description: {product['description']}\n"
        email_content += f"Link: {product['link']}\n"
        email_content += "-" * 50 + "\n"
else:
    email_content = "No products found on Product Hunt at the moment."

# Send emails to all subscribers
send_emails_to_subscribers(product_details)

print("Product Hunt products sent via email!")
