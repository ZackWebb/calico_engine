import requests
import os

def download_calico_tiles():
    # Define the colors and patterns
    colors = ['lightBlue', 'green', 'pink', 'purple', 'darkBlue', 'yellow']
    patterns = range(1, 7)  # 1 to 6

    # Create a directory to store the images
    if not os.path.exists('calico_tiles'):
        os.makedirs('calico_tiles')

    # Base URL
    base_url = "https://myautoma.github.io/games/calico/img/tiles/{color}/{pattern}.png"

    # Download each image
    for color in colors:
        for pattern in patterns:
            # Construct the URL
            url = base_url.format(color=color, pattern=pattern)
            
            # Construct the file name
            file_name = f"{color}_{pattern}.png"
            file_path = os.path.join('calico_tiles', file_name)

            # Download the image
            response = requests.get(url)
            if response.status_code == 200:
                with open(file_path, 'wb') as file:
                    file.write(response.content)
                print(f"Downloaded: {file_name}")
            else:
                print(f"Failed to download: {file_name}")

    print("Download complete!")

if __name__ == "__main__":
    download_calico_tiles()