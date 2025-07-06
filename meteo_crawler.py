import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
from datetime import datetime, timedelta

# --- CONFIGURATION ---
USERNAME = 'robby'
PASSWORD = 'Lillyba1'
LOGIN_URL = 'https://vfr.topmeteo.eu/de/de/login/'
FORECAST_URL = 'https://vfr.topmeteo.eu/de/de/map/28/1/10/'
OUTPUT_IMAGE = 'forecast.png'

# --- SELENIUM SETUP ---
chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--window-size=1920,1080')  # Set larger window size for better screenshots

def should_download_file(file_path, max_age_hours=2):
    """Check if file should be downloaded based on age"""
    if not os.path.exists(file_path):
        return True
    
    # Get file modification time
    file_mtime = os.path.getmtime(file_path)
    file_age = datetime.now() - datetime.fromtimestamp(file_mtime)
    
    # Download if file is older than max_age_hours
    return file_age > timedelta(hours=max_age_hours)

def get_forecast_update_time():
    """Get the current forecast update cycle time (every 2 hours)"""
    now = datetime.utcnow()
    # Forecasts are updated every 2 hours at even hours (00, 02, 04, etc.)
    current_hour = now.hour
    # Find the most recent even hour
    last_update_hour = (current_hour // 2) * 2
    last_update_time = now.replace(hour=last_update_hour, minute=0, second=0, microsecond=0)
    return last_update_time

def extract_pfd_data(driver):
    """Extract PFD 18m-Klasse [km] data from the Ortsvorhersage page"""
    try:
        # Wait for the page to fully load
        time.sleep(5)
        print("Starting PFD data extraction...")
        
        # Debug: Print page title to confirm we're on the right page
        page_title = driver.title
        print(f"Page title: {page_title}")
        
        # Debug: Check if we can find any tables
        tables = driver.find_elements(By.TAG_NAME, "table")
        print(f"Found {len(tables)} tables on the page")
        
        # Debug: Look for any text containing "PFD"
        pfd_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'PFD')]")
        print(f"Found {len(pfd_elements)} elements containing 'PFD'")
        
        # Method 1: Direct table search with debugging
        try:
            print("Method 1: Searching for PFD 18m-Klasse in tables...")
            for i, table in enumerate(tables):
                print(f"Checking table {i+1}...")
                table_text = table.text
                if "PFD 18m-Klasse" in table_text:
                    print(f"Found PFD 18m-Klasse in table {i+1}")
                    
                    # Get all rows in this table
                    rows = table.find_elements(By.TAG_NAME, "tr")
                    print(f"Table {i+1} has {len(rows)} rows")
                    
                    for j, row in enumerate(rows):
                        row_text = row.text
                        print(f"Row {j+1}: {row_text[:100]}...")  # Show first 100 chars
                        
                        if "PFD 18m-Klasse [km]" in row_text:
                            print(f"Found PFD row in table {i+1}, row {j+1}")
                            
                            # Get all cells in this row
                            cells = row.find_elements(By.TAG_NAME, "td")
                            print(f"PFD row has {len(cells)} cells")
                            
                            data_values = []
                            for k, cell in enumerate(cells):
                                cell_text = cell.text.strip()
                                print(f"Cell {k+1}: '{cell_text}'")
                                
                                # Skip the first cell (title)
                                if k == 0:
                                    continue
                                
                                if cell_text and cell_text != "":
                                    import re
                                    numbers = re.findall(r'\d+', cell_text)
                                    if numbers:
                                        data_values.append(f"Hour {k-1}: {numbers[0]} km")
                                        print(f"Added: Hour {k-1}: {numbers[0]} km")
                                    else:
                                        data_values.append(f"Hour {k-1}: {cell_text}")
                                        print(f"Added: Hour {k-1}: {cell_text}")
                            
                            if data_values:
                                result = "\n".join(data_values)
                                print(f"Successfully extracted {len(data_values)} PFD values")
                                return result
                            else:
                                print("No valid PFD values found in the row")
        except Exception as e:
            print(f"Method 1 failed: {e}")
        
        # Method 2: Try to find by class name
        try:
            print("Method 2: Searching for product-content cells...")
            product_cells = driver.find_elements(By.CLASS_NAME, "product-content")
            print(f"Found {len(product_cells)} product-content cells")
            
            # Look for the row that contains PFD 18m-Klasse
            pfd_row = None
            for cell in product_cells:
                try:
                    # Go up to find the row
                    row = cell.find_element(By.XPATH, "./ancestor::tr")
                    row_text = row.text
                    if "PFD 18m-Klasse [km]" in row_text:
                        pfd_row = row
                        print("Found PFD row using product-content method")
                        break
                except:
                    continue
            
            if pfd_row:
                cells = pfd_row.find_elements(By.TAG_NAME, "td")
                print(f"PFD row has {len(cells)} cells")
                
                data_values = []
                for i, cell in enumerate(cells[1:], 1):  # Skip first cell
                    cell_text = cell.text.strip()
                    print(f"Cell {i}: '{cell_text}'")
                    
                    if cell_text and cell_text != "":
                        import re
                        numbers = re.findall(r'\d+', cell_text)
                        if numbers:
                            data_values.append(f"Hour {i-1}: {numbers[0]} km")
                
                if data_values:
                    result = "\n".join(data_values)
                    print(f"Successfully extracted {len(data_values)} PFD values")
                    return result
        except Exception as e:
            print(f"Method 2 failed: {e}")
        
        # Method 3: Try JavaScript extraction
        try:
            print("Method 3: Trying JavaScript extraction...")
            script = """
            // Look for any JavaScript variables that might contain forecast data
            let result = [];
            
            // Check various possible variable names
            const possibleVars = ['forecastData', 'products', 'data', 'forecast'];
            
            for (let varName of possibleVars) {
                if (typeof window[varName] !== 'undefined') {
                    console.log('Found variable:', varName);
                    console.log('Content:', window[varName]);
                    
                    for (let key in window[varName]) {
                        let item = window[varName][key];
                        if (item && item.title && item.title.includes('PFD 18m-Klasse')) {
                            console.log('Found PFD data in', varName, key);
                            if (item.columns) {
                                item.columns.forEach((col, index) => {
                                    if (col.value && col.value !== '') {
                                        result.push(`Hour ${index}: ${col.value} km`);
                                    }
                                });
                                return result.join('\\n');
                            }
                        }
                    }
                }
            }
            
            return null;
            """
            
            result = driver.execute_script(script)
            if result:
                print("JavaScript extraction successful")
                return result
            else:
                print("JavaScript extraction returned null")
        except Exception as e:
            print(f"Method 3 failed: {e}")
        
        # Method 4: Save page source for manual inspection
        try:
            print("Method 4: Saving page source for debugging...")
            page_source = driver.page_source
            
            # Look for PFD in the page source
            if "PFD 18m-Klasse" in page_source:
                print("Found 'PFD 18m-Klasse' in page source")
                
                # Find the position of PFD data
                start_pos = page_source.find("PFD 18m-Klasse [km]")
                if start_pos != -1:
                    # Extract a portion around this text
                    end_pos = min(start_pos + 2000, len(page_source))
                    relevant_text = page_source[start_pos:end_pos]
                    print(f"Relevant text around PFD: {relevant_text[:500]}...")
                    
                    # Try to extract values using regex
                    import re
                    # Look for numbers after PFD 18m-Klasse
                    numbers = re.findall(r'PFD 18m-Klasse \[km\].*?(\d+)', relevant_text, re.DOTALL)
                    if numbers:
                        print(f"Found numbers: {numbers}")
                        data_values = []
                        for i, num in enumerate(numbers[:24]):  # Limit to 24 hours
                            data_values.append(f"Hour {i}: {num} km")
                        return "\n".join(data_values)
            else:
                print("'PFD 18m-Klasse' not found in page source")
        except Exception as e:
            print(f"Method 4 failed: {e}")
        
        print("All extraction methods failed")
        return "PFD 18m-Klasse [km] data not found in the page"
        
    except Exception as e:
        print(f"Error in extract_pfd_data: {e}")
        return f"Error extracting PFD data: {str(e)}"

# Path to chromedriver (ensure it's in your PATH or specify full path)
driver = webdriver.Chrome(options=chrome_options)
wait = WebDriverWait(driver, 20)

try:
    # 1. Go to login page
    driver.get(LOGIN_URL)
    
    # 2. Fill in login form
    username_input = wait.until(EC.presence_of_element_located((By.ID, 'id_username')))
    password_input = driver.find_element(By.ID, 'id_password')
    username_input.send_keys(USERNAME)
    password_input.send_keys(PASSWORD)
    password_input.send_keys(Keys.RETURN)

    # 3. Wait for login to complete (check for absence of login form)
    time.sleep(2)
    login_form_present = True
    try:
        driver.find_element(By.ID, 'id_username')
        driver.find_element(By.ID, 'id_password')
        login_form_present = True
    except:
        login_form_present = False

    # Check for login error message
    error_message = None
    try:
        error_message = driver.find_element(By.CLASS_NAME, 'errorlist').text
    except:
        pass

    if login_form_present:
        print("Login failed! Please check your credentials or site availability.")
        if error_message:
            print(f"Error message: {error_message}")
        driver.quit()
        exit(1)
    else:
        print("Login successful!")

    # Get current forecast update time
    forecast_update_time = get_forecast_update_time()
    print(f"Current forecast update cycle: {forecast_update_time.strftime('%Y-%m-%d %H:%M UTC')}")

    # 4. Download forecast images for multiple products and days 0 to 5
    products = [
        (28, 'flugdistanz', [10]),  # Flugdistanz only at 10 UTC
        (24, 'thermikkarte', range(6, 19)),  # Thermikkarte from 6-18 UTC
        (26, 'wolkenverteilung', range(6, 19)),  # Wolkenverteilung from 6-18 UTC
    ]
    
    # Download Ortsvorhersage for Langenfeld (local forecast)
    langenfeld_id = '315181'  # Langenfeld location ID
    for day in range(0, 6):
        # Create directory for this day
        day_dir = f'day{day}'
        if not os.path.exists(day_dir):
            os.makedirs(day_dir)
            print(f"Created directory: {day_dir}")
        
        # Check if Ortsvorhersage file already exists and is recent
        ortsvorhersage_file = os.path.join(day_dir, f'forecast_ortsvorhersage_day{day}.png')
        if should_download_file(ortsvorhersage_file):
            # Ortsvorhersage URL structure: /de/de/loc/{location_id}/{day}/3/1/1/
            # The parameters are: day, start_hour=3, resolution=1, forecast_type=1
            url = f'https://vfr.topmeteo.eu/de/de/loc/{langenfeld_id}/{day}/3/1/1/'
            print(f"Processing Ortsvorhersage for Langenfeld day {day}: {url}")
            driver.get(url)
            time.sleep(5)  # Wait for JS to load content
            
            # Take screenshot of the Ortsvorhersage page
            try:
                # Find the main content area for the forecast
                forecast_container = driver.find_element(By.CLASS_NAME, 'location-forecast')
                if forecast_container:
                    # Set window size to ensure good quality
                    driver.set_window_size(1920, 1080)
                    time.sleep(2)  # Wait for resize to complete
                    
                    # Scroll to the forecast container to ensure it's visible
                    driver.execute_script("arguments[0].scrollIntoView();", forecast_container)
                    time.sleep(1)
                    
                    # Take screenshot of the specific forecast container
                    forecast_container.screenshot(ortsvorhersage_file)
                    print(f"Ortsvorhersage for Langenfeld day {day} saved as {ortsvorhersage_file}")
                    
                    # Extract PFD 18m-Klasse data
                    try:
                        # Look for PFD 18m-Klasse data in the page
                        pfd_data = extract_pfd_data(driver)
                        if pfd_data:
                            pfd_file = os.path.join(day_dir, f'pfd_18m_day{day}.txt')
                            with open(pfd_file, 'w', encoding='utf-8') as f:
                                f.write(pfd_data)
                            print(f"PFD 18m-Klasse data for day {day} saved as {pfd_file}")
                        else:
                            print(f"No PFD 18m-Klasse data found for day {day}")
                    except Exception as pfd_e:
                        print(f"Could not extract PFD data for day {day}: {pfd_e}")
                        
                else:
                    print(f"Could not find Ortsvorhersage content for day {day}")
            except Exception as e:
                print(f"Could not capture Ortsvorhersage for day {day}: {e}")
                # Fallback: try to take full page screenshot
                try:
                    driver.save_screenshot(ortsvorhersage_file)
                    print(f"Fallback: Full page screenshot saved for day {day}")
                except Exception as fallback_e:
                    print(f"Fallback screenshot also failed for day {day}: {fallback_e}")
        else:
            print(f"Ortsvorhersage for day {day} already exists and is recent, skipping...")
    
    # Download regular forecast images
    for product_id, product_name, hours in products:
        for day in range(0, 6):
            # Create directory for this day (already created above, but check again)
            day_dir = f'day{day}'
            if not os.path.exists(day_dir):
                os.makedirs(day_dir)
                print(f"Created directory: {day_dir}")
            
            for hour in hours:
                # Check if file already exists and is recent
                forecast_file = os.path.join(day_dir, f'forecast_{product_name}_day{day}_hour{hour:02d}.png')
                if should_download_file(forecast_file):
                    url = f'https://vfr.topmeteo.eu/de/de/map/{product_id}/{day}/{hour}/'
                    print(f"Processing {product_name} for day {day} at {hour} UTC: {url}")
                    driver.get(url)
                    time.sleep(5)  # Wait for JS to load image

                    # Find the forecast image inside the projection-map-image container
                    forecast_img_url = None
                    try:
                        map_container = driver.find_element(By.ID, 'projection-map-image')
                        img = map_container.find_element(By.TAG_NAME, 'img')
                        forecast_img_url = img.get_attribute('src')
                    except Exception as e:
                        print(f"Could not find forecast image for {product_name} day {day} hour {hour}: {e}")
                        continue

                    if not forecast_img_url:
                        print(f"Forecast image not found for {product_name} day {day} hour {hour}!")
                        continue

                    # If the src is a relative path, prepend the base URL
                    if forecast_img_url.startswith('./'):
                        forecast_img_url = 'https://vfr.topmeteo.eu' + forecast_img_url[1:]
                    elif forecast_img_url.startswith('/'):
                        forecast_img_url = 'https://vfr.topmeteo.eu' + forecast_img_url

                    # Download the image using requests (with session cookies)
                    session = requests.Session()
                    for cookie in driver.get_cookies():
                        session.cookies.set(cookie['name'], cookie['value'])
                    response = session.get(forecast_img_url)
                    if response.status_code == 200:
                        with open(forecast_file, 'wb') as f:
                            f.write(response.content)
                        print(f"Forecast image for {product_name} day {day} hour {hour} saved as {forecast_file}")
                    else:
                        print(f"Failed to download image for {product_name} day {day} hour {hour}: {response.status_code}")
                else:
                    print(f"Forecast for {product_name} day {day} hour {hour} already exists and is recent, skipping...")

    print(f"\nForecast update completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Next forecast update will be available in approximately 2 hours.")
    
finally:
    driver.quit() 