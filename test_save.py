import os

filename = "my_file.txt"
home_dir = os.path.expanduser("~")
file_path = os.path.join(home_dir, filename)

try:
    with open(file_path, "w") as f:
        f.write("This is some text.")
    print(f"File saved to: {file_path}")
except Exception as e:
    print(f"An error occurred: {e}")