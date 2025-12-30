import requests
import os

def download_calico_tiles():
    colors = ['blue', 'green', 'pink', 'purple', 'yellow', 'darkBlue']  # Changed 'teal' to 'darkBlue'
    patterns = range(1, 7)  # 1 to 6

    download_images('calico_tiles', 
                    "https://myautoma.github.io/games/calico/img/tiles/{color}/{pattern}.png",
                    colors, patterns)

def download_buttons():
    colors = ['blue', 'green', 'pink', 'purple', 'yellow', 'darkBlue', 'lightBlue', 'rainbow']
    patterns = [None]  # We don't need patterns for buttons

    download_images('calico_buttons', 
                    "https://myautoma.github.io/games/calico/img/buttons/{color}.png",
                    colors, patterns)

def download_grey_tiles():
    colors = ['black']  # We use 'black' in the URL for grey tiles
    patterns = range(1, 7)  # 1 to 6

    download_images('calico_grey_tiles', 
                    "https://myautoma.github.io/games/calico/img/tiles/{color}/{pattern}.png",
                    colors, patterns)

def download_images(directory, url_template, colors, patterns):
    if not os.path.exists(directory):
        os.makedirs(directory)

    for color in colors:
        for pattern in patterns:
            if pattern is None:
                url = url_template.format(color=color)
                file_name = f"{color}.png"
            else:
                url = url_template.format(color=color, pattern=pattern)
                file_name = f"{color}_{pattern}.png"
            
            file_path = os.path.join(directory, file_name)

            response = requests.get(url)
            if response.status_code == 200:
                with open(file_path, 'wb') as file:
                    file.write(response.content)
                print(f"Downloaded: {file_name}")
            else:
                print(f"Failed to download: {file_name}")

def main():
    print("Downloading Calico tiles...")
    download_calico_tiles()
    
    print("\nDownloading buttons...")
    download_buttons()
    
    print("\nDownloading grey tiles...")
    download_grey_tiles()
    
    print("\nAll downloads complete!")

if __name__ == "__main__":
    main()