from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import time
import re
import pandas as pd

# Input URL and paths
url = input('Please give me the URL: ')
car_name = input('Please enter your car\'s name: ')
csv_path = 'C:/Users/Amir/Desktop/Car Price Prediction/DB/%s.csv' %car_name # save csv in this folder 
driver_path = 'C:/Users/Amir/Desktop/Car Price Prediction/chromedriver/chromedriver.exe' # path of ChromeDriver

# Reading data from the site
service = Service(driver_path)
driver = webdriver.Chrome(service=service)
driver.get(url)

# Scrolling to load all content
last_height = driver.execute_script("return document.body.scrollHeight")
while True:
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(3)
    new_height = driver.execute_script("return document.body.scrollHeight")
    if new_height == last_height:
        break
    last_height = new_height

# Reading car's details
details = driver.find_elements(By.CLASS_NAME, 'bama-ad__detail-row')
names = driver.find_elements(By.CLASS_NAME, 'bama-ad__title')
prices = driver.find_elements(By.CLASS_NAME, 'bama-ad__price')

# Function to clean and split details into columns
car_data = []
names_data = [re.sub(r'،' ,'', name.text).strip() for name in names]
prices_data = [re.sub(r'[,"]', '', price.text).strip() for price in prices]

for detail in details:
    text = detail.text.replace('"', '')  # Remove double quotes
    lines = text.split("\n")  # Split by newline to separate details
    if len(lines) == 3:  # Expected 3 lines: Year, Kilometers, Model/Type
        year = lines[0]
        km = lines[1]
        
        # Guys, "صفر کیلومتر" means zero kilometers
        # Replace "صفر کیلومتر" with 0 and clean km
        if "صفر کیلومتر" in km:
            km = "0"
        else:
            km = km.replace(',', '').replace(' km', '').strip()  # Remove commas and 'km'
        
        model = lines[2]
        car_data.append([year, km, model])
    elif len(lines) == 2:  # Handle cases with missing data
        year = lines[0]
        km = ''
        model = lines[1]
        car_data.append([year, km, model])

# Creating DataFrame with separated columns
columns = ['Year', 'Kilometers', 'Model']
details_df = pd.DataFrame(car_data, columns=columns)


# Adding the 'name' column
details_df['Name'] = names_data

# Adding the 'price' column
details_df['Price'] = prices_data

#Guys, "کارکرده" means how many kilometers it has worked
# Removing rows where 'Kilometers' is "کارکرده"
details_df = details_df[details_df['Kilometers'] != 'کارکرده']

# Converting Data
details_df['Year'] = details_df['Year'].astype(int)
details_df['Kilometers'] = details_df['Kilometers'].astype(int)
details_df['Price'] = details_df['Price'].astype(float)

# Save to CSV without double quotes
details_df.to_csv(csv_path, index=False, encoding='utf-8')

# Close the driverhttps://bama.ir/car/hyundai-santafeix45
driver.quit()
