import pandas as pd
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import time

def get_coordinates(location, country):
    """Get coordinates for a location using Nominatim geocoder"""
    try:
        # Create geocoder instance
        geolocator = Nominatim(user_agent="disasters_geocoder")
        
        # Try with location and country first
        query = f"{location}, {country}"
        result = geolocator.geocode(query, timeout=10)
        
        # If no result, try just the country
        if result is None and country:
            result = geolocator.geocode(country, timeout=10)
            
        # Add delay to respect rate limits
        time.sleep(1)
        
        if result:
            return result.latitude, result.longitude
        return None, None
        
    except GeocoderTimedOut:
        print(f"Timeout for location: {location}, {country}")
        return None, None
    except Exception as e:
        print(f"Error geocoding {location}, {country}: {str(e)}")
        return None, None

def main():
    # Read the CSV file
    print("Reading disasters.csv...")
    df = pd.read_csv('data/disasters.csv')
    
    # Create new columns for coordinates if they don't exist
    if 'Latitude' not in df.columns:
        df['Latitude'] = ''
    if 'Longitude' not in df.columns:
        df['Longitude'] = ''
    
    # Count rows that need geocoding
    empty_coords = df[(df['Latitude'].isna() | (df['Latitude'] == '')) & 
                     (df['Longitude'].isna() | (df['Longitude'] == ''))].shape[0]
    print(f"Found {empty_coords} locations that need geocoding")
    
    # Process each row that needs coordinates
    for idx, row in df.iterrows():
        if (pd.isna(row['Latitude']) or row['Latitude'] == '') and \
           (pd.isna(row['Longitude']) or row['Longitude'] == '') and \
           not pd.isna(row['Location']):
            
            # Get first location from the list
            first_location = row['Location'].split(',')[0].strip()
            
            print(f"Processing {idx+1}/{len(df)}: {first_location}, {row['Country']}")
            
            # Get coordinates
            lat, lon = get_coordinates(first_location, row['Country'])
            
            # Update dataframe
            if lat and lon:
                df.at[idx, 'Latitude'] = lat
                df.at[idx, 'Longitude'] = lon
    
    # Save processed data
    print("Saving processed data...")
    df.to_csv('data/disasters_FINAL.csv', index=False)
    print("Done!")

if __name__ == "__main__":
    main() 