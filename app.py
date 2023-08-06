from flask import Flask, jsonify, request
from flask_cors import CORS, cross_origin
from flask.helpers import send_from_directory
import os
import tkinter as tk
from tkinter import filedialog
from concurrent.futures import ThreadPoolExecutor


app = Flask(__name__)
CORS = CORS(app)

app.config['CORS_HEADERS'] = 'Content-Type'

# This will hold the path to the folder selected by the user
folder_path = ""

def select_folder():
    global folder_path

    root = tk.Tk()
    root.withdraw()  # Hide the main window

    # Open the folder selection dialog
    folder_path = filedialog.askdirectory()
    print(f"Selected folder: {folder_path}")

def fetch_files(dirpath, filename):
    full_path = os.path.join(dirpath, filename)
    relative_path = os.path.relpath(full_path, folder_path)  # relative to the selected folder
    return relative_path.replace("\\", "/")

@app.route("/openapi.yaml")
@cross_origin()
def serve_openapi_spec():
    return send_from_directory(".", "openapi.yaml")

@app.route("/.well-known/ai-plugin.json")
@cross_origin()
def serve_manifest():
    return send_from_directory(".", "ai-plugin.json")

@app.route("/files", methods=["GET"])
@cross_origin()
def get_files():
    global folder_path

    # Get a list of all files in the selected folder, including those in subdirectories
    files = []
    with ThreadPoolExecutor() as executor:
        for dirpath, dirnames, filenames in os.walk(folder_path):
            # Check if the current directory is or is a subdirectory of .git or node_modules
            if ".git" in dirnames:
                dirnames.remove(".git")
            if "node_modules" in dirnames:
                dirnames.remove("node_modules")

            files.extend(executor.map(fetch_files, [dirpath]*len(filenames), filenames))
    # Return the file list
    return jsonify(files)

@app.route("/file", methods=["POST"])
@cross_origin()
def get_file_contents():
    global folder_path

    # Get the file path from the request body
    data = request.get_json()
    file_path = data.get('path', '')

    # Make sure the file is inside the selected folder
    full_path = os.path.join(folder_path, file_path)
    if not os.path.commonpath([folder_path]) == os.path.commonpath([folder_path, full_path]):
        return jsonify({"error": "Cannot access files outside the selected folder"}), 400

    # Make sure the file exists
    if not os.path.isfile(full_path):
        return jsonify({"error": "File not found"}), 404

    # Read the file and return its contents
    with open(full_path, 'r') as file:
        contents = file.read()
    return jsonify({"contents": contents})


if __name__ == "__main__":
    select_folder()
    app.run(port=5001)
