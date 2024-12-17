import os
import sys
import time
import threading
import logging
import random
import json
import queue
import traceback
from datetime import datetime, timedelta
from xml.etree import ElementTree as ET

import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import font as tkfont

from ttkbootstrap import Style
from plexapi.server import PlexServer
import requests

# ------------------------------ Constants and Configuration ------------------------------

# Define file paths for logs and configuration
LOG_DIR = 'logs'
LOG_FILE = os.path.join(LOG_DIR, 'DynamiX.log')
CONFIG_FILE = 'config.json'
USED_COLLECTIONS_FILE = 'used_collections.json'
USER_EXEMPTIONS_FILE = 'user_exemptions.json'

# Ensure the logs directory exists
os.makedirs(LOG_DIR, exist_ok=True)

# Configure logging to file and stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, mode='w', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

# ------------------------------ Helper Functions ------------------------------

def sanitize_time_blocks(time_blocks):
    """
    Ensure time_blocks is properly formatted as a dictionary.

    Args:
        time_blocks (Any): The time_blocks data to sanitize.

    Returns:
        dict: Sanitized time_blocks dictionary.
    """
    if not isinstance(time_blocks, dict):
        logging.warning(f"Sanitizing time_blocks: expected dict but got {type(time_blocks)}. Resetting to empty.")
        return {}
    sanitized = {}
    for day, blocks in time_blocks.items():
        if not isinstance(blocks, dict):
            logging.warning(f"Invalid blocks for day '{day}': resetting to empty dictionary.")
            sanitized[day] = {}
        else:
            sanitized[day] = blocks
    return sanitized

def load_config():
    """
    Load configuration from the CONFIG_FILE.

    Returns:
        dict: Configuration dictionary.
    """
    if not os.path.exists(CONFIG_FILE):
        logging.error(f"Configuration file '{CONFIG_FILE}' not found. Creating a default configuration.")
        return {}

    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except json.JSONDecodeError:
        logging.error(f"Configuration file '{CONFIG_FILE}' is empty or invalid. Resetting to default.")
        return {}

    # Sanitize libraries_settings and time_blocks
    libraries_settings = config.get("libraries_settings", {})
    if not isinstance(libraries_settings, dict):
        logging.warning(f"Sanitizing libraries_settings: resetting to empty dictionary.")
        libraries_settings = {}
    for library, settings in libraries_settings.items():
        time_blocks = settings.get("time_blocks", {})
        settings["time_blocks"] = sanitize_time_blocks(time_blocks)
    config["libraries_settings"] = libraries_settings

    return config

def save_config(config):
    """
    Save the configuration dictionary to CONFIG_FILE.

    Args:
        config (dict): Configuration dictionary to save.
    """
    try:
        logging.info(f"Final configuration to save: {json.dumps(config, indent=4)}")
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        logging.info("Configuration file saved successfully.")
    except Exception as e:
        logging.error(f"Error saving configuration file: {e}")
        raise

def load_used_collections():
    """
    Load used collections from USED_COLLECTIONS_FILE.

    Returns:
        dict: Dictionary of used collections.
    """
    if not os.path.exists(USED_COLLECTIONS_FILE):
        return {}
    with open(USED_COLLECTIONS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_used_collections(used_collections):
    """
    Save used collections to USED_COLLECTIONS_FILE.

    Args:
        used_collections (dict): Dictionary of used collections to save.
    """
    with open(USED_COLLECTIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(used_collections, f, ensure_ascii=False, indent=4)
    logging.info("Used collections file saved.")

def load_user_exemptions():
    """
    Load user exemptions from USER_EXEMPTIONS_FILE.

    Returns:
        list: List of user exemptions.
    """
    if not os.path.exists(USER_EXEMPTIONS_FILE):
        return []
    with open(USER_EXEMPTIONS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_user_exemptions(user_exemptions):
    """
    Save user exemptions to USER_EXEMPTIONS_FILE.

    Args:
        user_exemptions (list): List of user exemptions to save.
    """
    with open(USER_EXEMPTIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(user_exemptions, f, ensure_ascii=False, indent=4)
    logging.info("User exemptions file saved.")

def reset_exclusion_list_file():
    """
    Reset the exclusion list by clearing USED_COLLECTIONS_FILE.
    """
    with open(USED_COLLECTIONS_FILE, 'w', encoding='utf-8') as f:
        f.write("{}")
    logging.info("Exclusion list file has been reset.")

def connect_to_plex(config):
    """
    Connect to the Plex server using the provided configuration.

    Args:
        config (dict): Configuration dictionary containing Plex URL and token.

    Returns:
        PlexServer: Connected PlexServer instance.
    """
    logging.info("Connecting to Plex server...")
    plex = PlexServer(config['plex_url'], config['plex_token'])
    logging.info("Connected to Plex server successfully.")
    return plex

def handle_new_episodes_pinning(plex, libraries, always_pin_new_episodes):
    """
    Handle pinning or unpinning of 'New Episodes' collections based on configuration.

    Args:
        plex (PlexServer): Connected PlexServer instance.
        libraries (list): List of library names to process.
        always_pin_new_episodes (bool): Flag to always pin 'New Episodes'.
    """
    logging.info("Handling 'New Episodes' collections...")

    for library_name in libraries:
        try:
            library = plex.library.section(library_name)
            for collection in library.collections():
                if collection.title.lower() == "new episodes":
                    if always_pin_new_episodes:
                        try:
                            hub = collection.visibility()
                            hub.promoteHome()
                            hub.promoteShared()
                            logging.info(f"'New Episodes' collection pinned in '{library_name}'.")
                        except Exception as e:
                            logging.error(f"Error while pinning 'New Episodes': {e}")
                    else:
                        try:
                            hub = collection.visibility()
                            hub.demoteHome()
                            hub.demoteShared()
                            logging.info(f"'New Episodes' collection unpinned in '{library_name}'.")
                        except Exception as e:
                            logging.error(f"Error while unpinning 'New Episodes': {e}")
                    break  # Assuming only one 'New Episodes' collection per library
        except Exception as e:
            logging.error(f"Error accessing library '{library_name}': {e}")

def unpin_collections(plex, libraries, always_pin_new_episodes):
    """
    Unpin all collections except 'New Episodes' if always_pin_new_episodes is True.

    Args:
        plex (PlexServer): Connected PlexServer instance.
        libraries (list): List of library names to process.
        always_pin_new_episodes (bool): Flag to always pin 'New Episodes'.
    """
    logging.info("Unpinning currently pinned collections...")

    for library_name in libraries:
        try:
            library = plex.library.section(library_name)
            for collection in library.collections():
                if always_pin_new_episodes and collection.title.lower() == "new episodes":
                    continue  # Skip 'New Episodes' if it's always pinned
                try:
                    hub = collection.visibility()
                    hub.demoteHome()
                    hub.demoteShared()
                except Exception as e:
                    logging.error(f"Error while unpinning collection '{collection.title}': {e}")
        except Exception as e:
            logging.error(f"Error accessing library '{library_name}': {e}")

def log_and_update_exclusion_list(previous_pinned, used_collections, exclusion_days):
    """
    Log pinned collections and update the exclusion list with their expiration dates.

    Args:
        previous_pinned (list): List of previously pinned collections.
        used_collections (dict): Current exclusion list.
        exclusion_days (int): Number of days to exclude the collection.
    """
    current_date = datetime.now().date()

    for collection in previous_pinned:
        expiration_date = (current_date + timedelta(days=exclusion_days)).strftime('%Y-%m-%d')
        logging.info(f"Adding collection '{collection.title}' to exclusion list (expires: {expiration_date}).")
        used_collections[collection.title] = expiration_date

    save_used_collections(used_collections)

def get_current_time_block(config, library_name):
    """
    Determine the current time block and its corresponding limit for a given library.

    Args:
        config (dict): Configuration dictionary.
        library_name (str): Name of the library.

    Returns:
        tuple: (current_block_name, limit)
    """
    now = datetime.now()
    current_day = now.strftime("%A")  # e.g., "Monday"
    current_time = now.strftime("%H:%M")

    # Access library-specific settings
    library_settings = config.get("libraries_settings", {}).get(library_name, {})
    time_blocks = library_settings.get("time_blocks", {})
    default_limits = config.get("default_limits", {})
    library_default_limit = default_limits.get(library_name, 5)

    day_blocks = time_blocks.get(current_day, {})
    if not isinstance(day_blocks, dict):
        logging.error(f"Invalid time_blocks for day '{current_day}' in library '{library_name}'")
        return "Default", library_default_limit

    for block, details in day_blocks.items():
        if details.get("start_time") <= current_time < details.get("end_time"):
            return block, details.get("limit", library_default_limit)

    return "Default", library_default_limit

# ------------------------------ Main Automation Function ------------------------------

import random

def main(gui_instance=None, stop_event=None):
    """
    Main automation function for managing Plex collections.
    Handles dynamic pinning and unpinning based on time blocks and limits.
    """
    logging.info("Starting DynamiX automation...")

    try:
        # Load configuration
        config = load_config()
        if not config:
            logging.error("Configuration could not be loaded. Exiting.")
            return

        logging.info("Configuration loaded successfully.")

        # Connect to Plex server
        plex = connect_to_plex(config)

        # Retrieve configuration settings
        libraries = config.get("libraries", [])
        min_items = config.get("minimum_items", 1)
        exclusion_days = config.get("exclusion_days", 3)
        always_pin_new_episodes = config.get("always_pin_new_episodes", False)
        pinning_interval = config.get("pinning_interval", 30) * 60  # Convert minutes to seconds

        # Load persistent state files
        used_collections = load_used_collections()
        user_exemptions = load_user_exemptions()

        # Initialize SystemRandom for better randomness
        sys_random = random.SystemRandom()

        logging.info("Entering main automation loop.")
        while not stop_event.is_set():
            current_date = datetime.now().date()

            # Step 1: Clean up expired exclusions
            logging.info("Cleaning up expired exclusions...")
            used_collections = {
                name: date for name, date in used_collections.items()
                if datetime.strptime(date, '%Y-%m-%d').date() > current_date
            }
            save_used_collections(used_collections)
            logging.info("Updated exclusion list.")

            # Step 2: Handle 'New Episodes' Pinning
            handle_new_episodes_pinning(plex, libraries, always_pin_new_episodes)

            # Step 3: Unpin existing collections
            unpin_collections(plex, libraries, always_pin_new_episodes)

            # Step 4: Pin new collections based on time blocks
            logging.info("Pinning new collections based on current time block...")
            previous_pinned = []
            reset_needed = False  # Flag to determine if reset is required

            for library_name in libraries:
                try:
                    logging.info(f"Processing library: {library_name}")
                    library = plex.library.section(library_name)
                    collections = library.collections()

                    # Determine the current time block and limit
                    current_block, current_limit = get_current_time_block(config, library_name)
                    logging.info(f"Library '{library_name}' - Time Block: {current_block}, Limit: {current_limit}")

                    # Retrieve the default limit if no time block matches
                    library_settings = config.get("libraries_settings", {}).get(library_name, {})
                    default_limit = library_settings.get("default_limit", 5)

                    # Fallback if no valid time block limit found
                    final_limit = current_limit if current_block != "Default" else default_limit

                    # Filter valid collections for pinning
                    valid_collections = [
                        collection for collection in collections
                        if len(collection.items()) >= min_items
                           and collection.title not in used_collections
                           and collection.title not in user_exemptions
                    ]

                    if len(valid_collections) < final_limit:
                        logging.warning(
                            f"Not enough valid collections for '{library_name}'. "
                            f"Required: {final_limit}, Available: {len(valid_collections)}. Resetting exclusion list."
                        )
                        reset_needed = True
                        break  # Exit the loop to reset the exclusion list

                    if not valid_collections:
                        logging.info(f"No valid collections found for '{library_name}'. Skipping.")
                        continue

                    # Determine pin limit
                    pin_limit = min(len(valid_collections), final_limit)

                    # Randomly select collections to pin using SystemRandom
                    collections_to_pin = sys_random.sample(valid_collections, pin_limit)

                    logging.info(f"Valid collections in '{library_name}': {[c.title for c in valid_collections]}")
                    logging.info("Selected collections to pin successfully.")

                    for collection in collections_to_pin:
                        try:
                            hub = collection.visibility()
                            hub.promoteHome()
                            hub.promoteShared()
                            previous_pinned.append(collection)
                            logging.info(f"Collection '{collection.title}' pinned successfully.")
                        except Exception as e:
                            logging.error(f"Error pinning collection '{collection.title}': {e}")

                except Exception as e:
                    logging.error(f"Error processing library '{library_name}': {e}")

            # Step 4.1: Reset exclusion list if needed
            if reset_needed:
                if gui_instance:
                    logging.info("Resetting exclusion list due to insufficient collections.")
                    gui_instance.reset_exclusion_list()
                    used_collections = load_used_collections()  # Reload after reset
                else:
                    reset_exclusion_list_file()
                    used_collections = {}

                # Optionally, continue to the next iteration to retry pinning immediately
                continue  # Skip the rest of the loop and restart

            # Step 5: Pin selected collections
            if previous_pinned:
                # Update exclusion list with newly pinned collections
                log_and_update_exclusion_list(previous_pinned, used_collections, exclusion_days)
            else:
                logging.info("No new collections were pinned in this iteration.")

            # GUI update scheduling (if applicable)
            if gui_instance:
                gui_instance.after(0, gui_instance.refresh_exclusion_list)

            # Sleep for the configured pinning interval
            logging.info(f"Sleeping for {pinning_interval // 60} minutes before next iteration.")
            time.sleep(pinning_interval)

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        traceback.print_exc()

    finally:
        logging.info("Automation script terminated.")

# ------------------------------ Custom Logging Handler ------------------------------

class GuiHandler(logging.Handler):
    """
    Custom logging handler for displaying logs in the GUI using a queue.
    """

    def __init__(self, log_queue):
        """
        Initialize the GuiHandler with a queue.

        Args:
            log_queue (queue.Queue): Queue to hold log messages.
        """
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        """
        Enqueue the log message.

        Args:
            record (logging.LogRecord): Log record.
        """
        msg = self.format(record)
        self.log_queue.put(msg)

# ------------------------------ Scrollable Frame Class ------------------------------

class ScrollableFrame(ttk.Frame):
    """
    A scrollable frame that can contain other widgets.
    """

    def __init__(self, container, *args, **kwargs):
        """
        Initialize the ScrollableFrame.

        Args:
            container (tk.Widget): Parent widget.
        """
        super().__init__(container, *args, **kwargs)
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        # Configure canvas scroll region
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        # Create window inside the canvas
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        # Pack canvas and scrollbar
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

    def display_widget(self):
        """
        Return the inner scrollable frame.

        Returns:
            ttk.Frame: The scrollable frame.
        """
        return self.scrollable_frame

# ------------------------------ GUI Application Class ------------------------------

class DynamiXGUI(tk.Tk):
    """
    The main GUI application for DynamiX - Plex Collection Manager.
    """

    def __init__(self):
        """
        Initialize the GUI application.
        """
        super().__init__()
        self.title("DynamiX - Plex Recommendations Manager")
        self.geometry("920x875")  # Set default window size
        self.resizable(False, False)

        icon_path = os.path.join("resources", "myicon.ico")
        self.iconbitmap(icon_path)

        # Center the window on the screen
        self.center_window(920, 875)

        # Apply ttkbootstrap style
        self.style = Style(theme="darkly")
        self.configure(bg="black")

        # Initialize variables and state
        self.script_thread = None
        self.stop_event = threading.Event()  # Event to signal stopping the script
        self.config = load_config() or {}
        self.user_exemptions = load_user_exemptions() or []
        self.user_exemption_checkboxes = {}
        self.plex = None
        self.log_queue = queue.Queue()  # Queue for log messages

        # Default font settings
        self.default_font = tkfont.Font(family="Segoe UI", size=30)

        # Initialize UI components
        self.create_widgets()
        self.refresh_user_exemptions()
        self.refresh_exclusion_list()

    def center_window(self, width, height):
        """
        Center the window on the screen based on the given width and height.

        Args:
            width (int): Width of the window.
            height (int): Height of the window.
        """
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # Calculate position to center the window
        x_position = (screen_width // 2) - (width // 2)
        y_position = (screen_height // 2) - (height // 2)

        # Set geometry to center the window
        self.geometry(f"{width}x{height}+{x_position}+{y_position}")

    def create_widgets(self):
        """
        Create and arrange all widgets in the GUI.
        """
        # Create the main tab control
        self.tab_control = ttk.Notebook(self)

        # Define all tabs
        self.server_tab = ttk.Frame(self.tab_control)
        self.settings_tab = ttk.Frame(self.tab_control)
        self.logs_tab = ttk.Frame(self.tab_control)
        self.exclusion_tab = ttk.Frame(self.tab_control)
        self.user_exemptions_tab = ttk.Frame(self.tab_control)

        # Check for missing configuration fields and add Missing Information tab if needed
        if self._has_missing_fields():
            self.missing_info_tab = ttk.Frame(self.tab_control)
            self.tab_control.add(self.missing_info_tab, text="Missing Configuration Information")
            self._create_missing_info_tab()

        # Add other tabs
        self.tab_control.add(self.logs_tab, text="Logs")
        self.tab_control.add(self.exclusion_tab, text="Dynamic Exclusions")
        self.tab_control.add(self.user_exemptions_tab, text="User-Set Exemptions")
        self.tab_control.add(self.server_tab, text="Plex Server Config")
        self.tab_control.add(self.settings_tab, text="Settings")

        # Pack the tab control
        self.tab_control.pack(expand=True, fill="both")

        # Initialize content for each tab
        self._create_server_tab()
        self._create_settings_tab()
        self._create_logs_tab()
        self._create_exclusion_tab()
        self._create_user_exemptions_tab()

    def _has_missing_fields(self):
        """
        Check if required configuration fields are missing.

        Returns:
            bool: True if any required field is missing, False otherwise.
        """
        required_fields = ["plex_url", "plex_token", "libraries", "pinning_interval"]
        for field in required_fields:
            if field not in self.config or not self.config[field]:
                return True  # Field is missing or empty
        return False  # All required fields are present

    def _create_missing_info_tab(self):
        """
        Create the Missing Information tab to allow users to fill in missing config fields.
        """
        # Main Frame for Missing Information
        frame = ttk.Frame(self.missing_info_tab, padding=10)
        frame.pack(fill="both", expand=True)

        # Title Label
        ttk.Label(frame, text="Fill in Missing Configuration Fields", font=("Segoe UI", 16, "bold")).pack(pady=10)

        # Frame for missing fields
        self.missing_fields_frame = ttk.Frame(frame)
        self.missing_fields_frame.pack(fill="both", expand=True, pady=10)

        # Populate Missing Fields
        self.missing_entries = {}
        self._populate_missing_fields()

        # If plex_token is missing, add a centered, more in-depth explanation
        if "plex_token" in self.missing_entries:
            plex_token_explanation = (
                "How to Find Your Plex Token (Easier Method):\n\n"
                "1. Open the Plex Web App in your browser and log into your Plex server.\n"
                "2. Select any movie or episode.\n"
                "3. Click the 'Get Info' button (click the 3 dot icon) for that item.\n"
                "4. In the Info panel, look for the option 'View XML' and click it.\n"
                "5. A new page/tab will open showing the XML data for that media.\n"
                "6. Look at the URL in the browser's address bar. Your Plex token appears at the end "
                "of the URL after 'X-Plex-Token='.\n"
                "7. Copy that token and paste it here.\n\n"
                "This token allows the script to securely access your Plex server."
            )

            explanation_frame = ttk.Frame(frame)
            explanation_frame.pack(expand=True, fill="both", pady=(0, 10))

            explanation_label = ttk.Label(
                explanation_frame,
                text=plex_token_explanation,
                font=("Segoe UI", 9, "italic"),
                foreground="red",
                wraplength=800,
                justify="center",
                anchor="center"  # Anchor text center within the label
            )
            explanation_label.pack(expand=True, fill="both", anchor='center')

        # Save Button
        save_button = ttk.Button(frame, text="Save Missing Information", command=self._save_missing_fields)
        save_button.pack(pady=10)

    def _populate_missing_fields(self):
        """
        Populate the Missing Information tab with entry fields for missing configuration.
        """
        # Clear previous fields
        for widget in self.missing_fields_frame.winfo_children():
            widget.destroy()
        self.missing_entries = {}

        # Define the required fields with descriptions
        required_fields = {
            "plex_url": "URL of your Plex server (Can't be 'localhost')",
            "plex_token": "Token for accessing your Plex server",
            "libraries": "Comma-separated list of libraries to manage",
            "pinning_interval": "Time interval (in minutes) for pinning"
        }

        # Center grid columns for better alignment
        self.missing_fields_frame.grid_columnconfigure(0, weight=1)  # Left padding
        self.missing_fields_frame.grid_columnconfigure(1, weight=2)  # Main content
        self.missing_fields_frame.grid_columnconfigure(2, weight=1)  # Right padding

        # Dynamically add fields for missing/empty entries
        row = 0
        for key, description in required_fields.items():
            if key not in self.config or not self.config[key]:
                # Add Label
                ttk.Label(
                    self.missing_fields_frame,
                    text=f"{key.replace('_', ' ').title()}:",
                    font=("Segoe UI", 12)
                ).grid(row=row, column=1, sticky="w", pady=5, padx=50)

                # Add Entry box
                entry = ttk.Entry(self.missing_fields_frame, width=40)
                entry.grid(row=row, column=1, pady=5, padx=50)
                entry.configure(justify="center")  # Center the text input

                # Add Description
                ttk.Label(
                    self.missing_fields_frame,
                    text=f"({description})",
                    font=("Segoe UI", 10, "italic"),
                    foreground="gray"
                ).grid(row=row + 1, column=1, sticky="w", pady=2, padx=50)

                self.missing_entries[key] = entry
                row += 2  # Increment row for spacing

        # Show message if nothing is missing
        if not self.missing_entries:
            ttk.Label(
                self.missing_fields_frame,
                text="No missing configuration fields detected!",
                font=("Segoe UI", 12, "italic")
            ).grid(row=row, column=1, pady=20)

    def _save_missing_fields(self):
        """
        Save the newly filled missing fields to the config and restart the GUI.
        """
        try:
            # Update the config dictionary with new values
            for key, widget in self.missing_entries.items():
                value = widget.get().strip()
                if key == "libraries":
                    self.config[key] = [lib.strip() for lib in value.split(",") if lib.strip()]
                elif key == "pinning_interval":
                    self.config[key] = int(value) if value.isdigit() else 30
                else:
                    self.config[key] = value

            # Save updated configuration
            save_config(self.config)

            messagebox.showinfo("Success", "Missing information saved successfully! Restarting the application...")
            logging.info("Missing configuration fields have been updated. Restarting the GUI.")

            # Restart the application
            self.restart_program()

        except Exception as e:
            logging.error(f"Error saving missing configuration fields: {e}")
            messagebox.showerror("Error", f"Failed to save missing information: {e}")

    def _create_server_tab(self):
        """
        Create the Plex Server configuration tab.
        """
        frame = ttk.Frame(self.server_tab, padding="10", style="TFrame")
        frame.pack(fill="both", expand=True)

        # Configure rows/columns for proper layout and centering
        for i in range(7):
            frame.grid_rowconfigure(i, weight=0)
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_rowconfigure(6, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=1)

        # Title
        ttk.Label(
            frame,
            text="Plex Server Configuration",
            font=("Segoe UI", 30, "bold"),
            bootstyle="warning"
        ).grid(row=1, column=0, columnspan=2, pady=10)

        # Plex URL
        ttk.Label(frame, text="Plex URL (Can't be 'localhost'):", font=("Segoe UI", 12)).grid(row=2, column=0, sticky="e", padx=10, pady=5)
        self.plex_url_entry = ttk.Entry(frame, width=50)
        self.plex_url_entry.grid(row=2, column=1, sticky="w", padx=10, pady=5)
        self.plex_url_entry.insert(0, self.config.get("plex_url", ""))

        # Plex Token
        ttk.Label(frame, text="Plex Token:", font=("Segoe UI", 12)).grid(row=3, column=0, sticky="e", padx=10, pady=5)
        self.plex_token_entry = ttk.Entry(frame, width=50, show="*")
        self.plex_token_entry.grid(row=3, column=1, sticky="w", padx=10, pady=5)
        self.plex_token_entry.insert(0, self.config.get("plex_token", ""))

        # More in-depth explanation centered under the Plex Token field
        plex_token_explanation = (
            "How to Find Your Plex Token (Easier Method):\n\n"
            "1. In the Plex Web App, navigate to a movie or TV episode.\n"
            "2. Click the 'Get Info' button for that media item.\n"
            "3. In the info window, select 'View XML' (or a similar option) to open the XML data.\n"
            "4. Check the URL of the newly opened page. Your Plex token is at the end of the URL "
            "after 'X-Plex-Token='.\n"
            "5. Copy this token and paste it here.\n\n"
            "This token lets this tool manage your Plex server's collections securely."
        )

        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=1)

        explanation_label = ttk.Label(
            frame,
            text=plex_token_explanation,
            font=("Segoe UI", 9, "italic"),
            foreground="red",
            wraplength=600,
            justify="center",
            anchor="center"  # Anchor text center within the label
        )
        explanation_label.grid(row=4, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 20))

        # Save Configuration Button
        ttk.Button(
            frame,
            text="Save Configuration",
            command=self._save_and_refresh_server_name,
            bootstyle="warning"
        ).grid(row=5, column=0, columnspan=2, pady=20)

        # Server Name Label
        self.server_name_label = ttk.Label(
            frame,
            text="Server Name: Fetching...",
            font=("Segoe UI", 20, "bold"),
            bootstyle="warning"
        )
        self.server_name_label.grid(row=6, column=0, columnspan=2, pady=10)

        # Fetch and display the Plex server name
        self._fetch_and_display_server_name()

    def _save_and_refresh_server_name(self):
        """
        Save the server configuration and refresh the server name display.
        """
        self.save_server_config()  # Save the configuration
        self._fetch_and_display_server_name()  # Refresh the server name

    def save_server_config(self):
        """
        Save the Plex server configuration from the server tab.
        """
        try:
            plex_url = self.plex_url_entry.get().strip()
            plex_token = self.plex_token_entry.get().strip()
            if not plex_url or not plex_token:
                messagebox.showerror("Error", "Plex URL and Token cannot be empty.")
                return

            self.config["plex_url"] = plex_url
            self.config["plex_token"] = plex_token
            save_config(self.config)
            messagebox.showinfo("Success", "Plex server configuration saved successfully.")
            logging.info("Plex server configuration saved.")
        except Exception as e:
            logging.error(f"Error saving Plex server configuration: {e}")
            messagebox.showerror("Error", f"Failed to save Plex server configuration: {e}")

    def _fetch_and_display_server_name(self):
        """
        Fetch the Plex server name and update the server name label.
        """
        plex_url = self.plex_url_entry.get()
        plex_token = self.plex_token_entry.get()

        if plex_url and plex_token:
            try:
                response = requests.get(f"{plex_url}/?X-Plex-Token={plex_token}", timeout=10)
                if response.status_code == 200:
                    root = ET.fromstring(response.content)
                    server_name = root.attrib.get("friendlyName", "Unknown Server")
                    self.server_name_label.config(text=f"Server Name: {server_name}")
                else:
                    self.server_name_label.config(text="Server Name: Unable to fetch")
            except Exception as e:
                self.server_name_label.config(text=f"Server Name: Error fetching ({str(e)})")
        else:
            self.server_name_label.config(text="Server Name: Missing URL or Token")

    def _add_general_field(self, parent_frame, label_text, start_row, config_key, explanation=""):
        """
        Place a label and entry for a config field, followed by an explanation label on the next row.
        Returns the next available row index after placing these elements.
        """
        # Field Row
        ttk.Label(parent_frame, text=label_text).grid(row=start_row, column=0, sticky="e", padx=10, pady=5)

        value = self.config.get(config_key, "")
        if config_key == "libraries" and isinstance(value, list):
            value = ", ".join(value)

        entry = ttk.Entry(parent_frame, width=50)
        entry.grid(row=start_row, column=1, sticky="w", padx=10, pady=5)
        entry.insert(0, value)
        setattr(self, f"{config_key}_entry", entry)

        # Explanation Row
        next_row = start_row + 1
        if explanation:
            ttk.Label(
                parent_frame,
                text=explanation,
                font=("Segoe UI", 9, "italic"),
                foreground="red",
                wraplength=600
            ).grid(row=next_row, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 10))
            next_row += 1
        else:
            # Add some spacing if no explanation, to maintain consistent layout
            next_row += 1

        return next_row

    def _create_settings_tab(self):
        """
        Create the Settings tab with General Settings, Default Limits, and Time Block Configuration.
        Includes explanations for each setting and preserves the original scrolling functionality.
        """
        # Parent container for the settings tab
        container = ttk.Frame(self.settings_tab)
        container.pack(fill="both", expand=True)

        # Create a canvas and scrollbar for scrolling (EXACTLY as originally was)
        canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        canvas.create_window((0, 0), window=scrollable_frame, anchor="n", width=900)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event):
            canvas.yview_scroll(-1 * (event.delta // 120), "units")

        # These lines remain EXACTLY as originally was
        canvas.bind("<Enter>",
                    lambda e: self.exemptions_canvas.bind_all("<MouseWheel>", _on_mousewheel))
        canvas.bind("<Leave>", lambda e: self.exemptions_canvas.unbind_all("<MouseWheel>"))

        # Title
        ttk.Label(scrollable_frame, text="Settings", font=("Segoe UI", 24, "bold")).pack(pady=20)

        # --- Save Settings Button at the Top ---
        save_settings_button = ttk.Button(
            scrollable_frame,
            text="Save Settings",
            command=self.save_settings,
            bootstyle="warning"
        )
        save_settings_button.pack(pady=10, padx=20, fill="x")

        # --- General Configuration ---
        general_config_frame = ttk.LabelFrame(scrollable_frame, text="General Configuration", padding=10)
        general_config_frame.pack(fill="x", padx=20, pady=10)

        # Using row indexes to neatly place fields and explanations
        current_row = 0
        current_row = self._add_general_field(
            general_config_frame,
            "Library Names (comma-separated):",
            current_row,
            "libraries",
            explanation="A comma-separated list of the Plex libraries you want to manage (e.g., 'Movies, TV Shows')."
        )

        current_row = self._add_general_field(
            general_config_frame,
            "Pinning Program Run Interval (minutes):",
            current_row,
            "pinning_interval",
            explanation="How often (in minutes) the script attempts to pin/unpin collections."
        )

        current_row = self._add_general_field(
            general_config_frame,
            "Days to Exclude Collections after Pinning:",
            current_row,
            "exclusion_days",
            explanation="Number of days a pinned collection is excluded from being re-pinned again."
        )

        current_row = self._add_general_field(
            general_config_frame,
            "Minimum Items for Valid Collection:",
            current_row,
            "minimum_items",
            explanation="Minimum number of items required in a collection for it to be considered for pinning."
        )

        # Always Pin 'New Episodes' checkbox
        self.new_episodes_var = tk.BooleanVar(value=self.config.get("always_pin_new_episodes", False))
        ttk.Checkbutton(
            general_config_frame,
            text="Always Pin 'New Episodes' if Available as a Collection",
            variable=self.new_episodes_var
        ).grid(row=current_row, column=0, columnspan=2, sticky="w", padx=10, pady=5)
        current_row += 1
        ttk.Label(
            general_config_frame,
            text="If checked, the 'New Episodes' collection will always be pinned if present.",
            font=("Segoe UI", 9, "italic"),
            foreground="red",
            wraplength=600
        ).grid(row=current_row, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 10))
        current_row += 1

        # --- Library Default Limits Configuration ---
        default_limits_frame = ttk.LabelFrame(scrollable_frame, text="Library Default Limits", padding=10)
        default_limits_frame.pack(fill="x", padx=20, pady=10)

        ttk.Label(
            default_limits_frame,
            text="Set default pinning limits for each library when no specific time block applies:",
            font=("Segoe UI", 9, "italic"), foreground="red", wraplength=600
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=5)

        self.default_limit_entries = {}
        libraries = self.config.get("libraries", [])
        dl_current_row = 1
        for library in libraries:
            ttk.Label(default_limits_frame, text=f"{library}:").grid(row=dl_current_row, column=0, padx=5, pady=5,
                                                                     sticky="e")
            entry = ttk.Entry(default_limits_frame, width=10)
            entry.grid(row=dl_current_row, column=1, padx=5, pady=5, sticky="w")
            entry.insert(0, self.config.get("default_limits", {}).get(library, 5))
            self.default_limit_entries[library] = entry
            dl_current_row += 1

        # --- Library Time Block Configuration ---
        time_block_frame = ttk.LabelFrame(scrollable_frame, text="Dynamic Library Time Block Configuration", padding=10)
        time_block_frame.pack(fill="x", padx=20, pady=10)

        # Original code retained; just adding explanations inline
        ttk.Label(
            time_block_frame,
            text="Configure different pinning limits based on the day and time of day.",
            font=("Segoe UI", 9, "italic"),
            foreground="red",
            wraplength=600
        ).grid(row=0, column=0, columnspan=7, pady=5, sticky="n")

        # Library selection dropdown
        ttk.Label(time_block_frame, text="Select Library:").grid(row=1, column=0, columnspan=7, pady=5, sticky="n")
        self.selected_library = tk.StringVar()
        self.library_dropdown = ttk.Combobox(
            time_block_frame,
            textvariable=self.selected_library,
            values=self.config.get("libraries", []),
            state="readonly"
        )
        self.library_dropdown.grid(row=2, column=0, columnspan=7, padx=10, pady=5, sticky="ew")
        self.library_dropdown.bind("<<ComboboxSelected>>", self._on_library_selected)

        # Days of the Week Selection
        days_frame = ttk.LabelFrame(time_block_frame, text="Select Days", padding=10)
        days_frame.grid(row=3, column=0, columnspan=7, pady=10, sticky="ew")

        ttk.Label(
            days_frame,
            text="Choose which days these time blocks apply:",
            font=("Segoe UI", 9, "italic"),
            wraplength=600
        ).grid(row=0, column=0, columnspan=7, sticky="w", padx=10, pady=5)

        for i in range(7):
            days_frame.grid_columnconfigure(i, weight=1)

        self.day_vars = {}
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        for idx, day in enumerate(days):
            var = tk.BooleanVar(value=False)
            chk = ttk.Checkbutton(days_frame, text=day, variable=var)
            chk.grid(row=1, column=idx, padx=5, pady=5, sticky="w")
            self.day_vars[day] = var

        ttk.Label(
            time_block_frame,
            text="Define start/end times (HH:MM) and pin limits for each block.",
            font=("Segoe UI", 9, "italic"), foreground="red", wraplength=600
        ).grid(row=4, column=0, columnspan=7, padx=10, pady=(0, 10), sticky="w")

        self.time_block_entries = {}
        blocks = ["Morning", "Afternoon", "Evening"]
        for idx, block_name in enumerate(blocks):
            ttk.Label(time_block_frame, text=f"{block_name} Start:").grid(row=5 + idx, column=1, padx=5, pady=5,
                                                                          sticky="e")
            start_entry = ttk.Entry(time_block_frame, width=10)
            start_entry.grid(row=5 + idx, column=2, padx=5, pady=5, sticky="w")

            ttk.Label(time_block_frame, text="End:").grid(row=5 + idx, column=3, padx=5, pady=5, sticky="e")
            end_entry = ttk.Entry(time_block_frame, width=10)
            end_entry.grid(row=5 + idx, column=4, padx=5, pady=5, sticky="w")

            ttk.Label(time_block_frame, text="Limit:").grid(row=5 + idx, column=5, padx=5, pady=5, sticky="e")
            limit_entry = ttk.Entry(time_block_frame, width=5)
            limit_entry.grid(row=5 + idx, column=6, padx=5, pady=5, sticky="w")

            self.time_block_entries[block_name] = {
                "start_time": start_entry,
                "end_time": end_entry,
                "limit": limit_entry
            }

        # --- Save Time Blocks Button ---
        save_time_blocks_button = ttk.Button(
            time_block_frame,
            text="Save Time Blocks",
            command=self._apply_time_blocks_to_days,
            bootstyle="warning"
        )
        save_time_blocks_button.grid(row=5 + len(blocks), column=0, columnspan=7, pady=10, sticky="ew", padx=5)

        # --- Schedule Summary ---
        self.schedule_summary_frame = ttk.LabelFrame(scrollable_frame, text="Current Time Blocks", padding=10)
        self.schedule_summary_frame.pack(fill="both", padx=20, pady=10)

        ttk.Label(
            self.schedule_summary_frame,
            text="A summary of your configured time blocks:",
            font=("Segoe UI", 9, "italic"),
            wraplength=600
        ).pack(anchor="w", pady=5, padx=10)

        self._refresh_schedule_summary()

    def save_settings(self):
        """Save settings from the Settings tab to the config file."""
        try:
            # Correct attribute names based on config_key
            self.config["minimum_items"] = int(self.minimum_items_entry.get())  # Corrected
            self.config["exclusion_days"] = int(self.exclusion_days_entry.get())
            self.config["always_pin_new_episodes"] = self.new_episodes_var.get()
            self.config["libraries"] = [lib.strip() for lib in self.libraries_entry.get().split(",") if lib.strip()]
            self.config["pinning_interval"] = int(self.pinning_interval_entry.get())

            # Save default limits
            self.config["default_limits"] = {}
            for library, entry in self.default_limit_entries.items():
                self.config["default_limits"][library] = int(entry.get())

            save_config(self.config)
            messagebox.showinfo("Success", "Settings saved successfully!")
            logging.info("Settings saved.")
        except ValueError:
            messagebox.showerror("Error", "Invalid input. Please enter valid integers.")
            logging.error("Invalid input in settings tab.")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while saving settings: {e}")
            logging.error(f"Error saving settings: {e}")

    def _apply_time_blocks_to_days(self):
        """
        Apply the current time block settings to selected days.
        """
        selected_days = [day for day, var in self.day_vars.items() if var.get()]
        library_name = self.selected_library.get()

        if not library_name:
            messagebox.showwarning("Warning", "No library selected.")
            return

        for day in selected_days:
            time_blocks = {}
            for block_name, entries in self.time_block_entries.items():
                start_time = entries["start_time"].get().strip()
                end_time = entries["end_time"].get().strip()
                limit = entries["limit"].get().strip()

                # Validate time format and numeric limits
                if self._validate_time_format(start_time) and self._validate_time_format(end_time) and limit.isdigit():
                    time_blocks[block_name] = {
                        "start_time": start_time,
                        "end_time": end_time,
                        "limit": int(limit)
                    }
                else:
                    messagebox.showerror(
                        "Error",
                        f"Invalid input in {block_name} block for {day}. Ensure time is HH:MM and limit is a number."
                    )
                    return

            self.config.setdefault("libraries_settings", {}).setdefault(library_name, {}).setdefault("time_blocks", {})[
                day] = time_blocks

        save_config(self.config)
        self._refresh_schedule_summary()
        messagebox.showinfo("Success", "Time blocks applied to selected days.")

    def _refresh_schedule_summary(self):
        """
        Refresh the summary table showing current time block settings.
        """
        # Clear existing widgets in the schedule summary frame
        for widget in self.schedule_summary_frame.winfo_children():
            widget.destroy()

        # Get the selected library
        library_name = self.selected_library.get()
        if not library_name:
            ttk.Label(self.schedule_summary_frame, text="No library selected.").pack()
            return

        # Fetch the time block settings for the library
        library_settings = self.config.get("libraries_settings", {}).get(library_name, {})
        time_blocks = library_settings.get("time_blocks", {})

        # Display the time blocks for all days of the week
        days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        for day in days_of_week:
            # Display the day header
            ttk.Label(self.schedule_summary_frame, text=f"{day}", font=("Segoe UI", 10, "bold")).pack(anchor="w",
                                                                                                      pady=2)

            # Fetch blocks for the current day
            day_blocks = time_blocks.get(day, {})
            if not day_blocks:
                ttk.Label(self.schedule_summary_frame, text="  No blocks configured").pack(anchor="w", padx=10, pady=1)
            else:
                # Iterate through the blocks and display each one
                for block_name, details in day_blocks.items():
                    # Ensure 'details' is a dictionary
                    if not isinstance(details, dict):
                        logging.warning(f"Invalid time block format for {block_name} in {day}. Skipping.")
                        continue

                    start_time = details.get("start_time", "N/A")
                    end_time = details.get("end_time", "N/A")
                    limit = details.get("limit", "N/A")

                    # Display block details
                    summary = f"  {block_name}: {start_time} - {end_time} (Limit: {limit})"
                    ttk.Label(self.schedule_summary_frame, text=summary).pack(anchor="w", padx=20, pady=1)

    def _create_logs_tab(self):
        """
        Create the Logs tab with a scrollable text area to display activity logs.
        """
        # Create a frame for the logs tab
        frame = ttk.Frame(self.logs_tab, padding=20)
        frame.pack(expand=True, fill="both")

        # Add a title
        ttk.Label(frame, text="Activity Logs", font=("Segoe UI", 30, "bold")).pack(pady=10)

        # Add a scrollable text area for logs
        self.logs_text = tk.Text(
            frame,
            wrap="word",
            state="disabled",
            bg="black",
            fg="white",
            height=20,
            width=80,
            font=("Consolas", 10),
        )
        self.logs_text.pack(expand=True, fill="both", padx=10, pady=10)

        # Add a vertical scrollbar
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.logs_text.yview)
        self.logs_text["yscrollcommand"] = scrollbar.set
        scrollbar.pack(side="right", fill="y")

        # Add a frame for buttons
        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=10)

        # Run Main Function button
        self.run_main_button = ttk.Button(button_frame, text="Run Main Function", bootstyle="warning", command=self.start_script)
        self.run_main_button.pack(side="left", padx=10)

        # Restart Program button
        self.restart_button = ttk.Button(button_frame, text="Restart Program", bootstyle="warning", command=self.restart_program)
        self.restart_button.pack(side="left", padx=10)

        # Add the custom log handler with queue
        gui_handler = GuiHandler(self.log_queue)
        gui_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        logging.getLogger().addHandler(gui_handler)

        # Schedule a periodic check of the log queue
        self.after(100, self.process_log_queue)

    def process_log_queue(self):
        """
        Process all messages in the log queue and display them in the logs_text widget.
        """
        while not self.log_queue.empty():
            msg = self.log_queue.get()
            self.logs_text.config(state="normal")
            self.logs_text.insert(tk.END, msg + "\n")
            self.logs_text.config(state="disabled")
            self.logs_text.see(tk.END)
        self.after(100, self.process_log_queue)

    def _create_exclusion_tab(self):
        """
        Create the Exclusion List tab with options to refresh, remove, and reset exclusions.
        """
        # Main frame for the tab
        frame = ttk.Frame(self.exclusion_tab, padding="10")
        frame.pack(fill="both", expand=True)

        # Wrapper frame to center all content horizontally
        center_frame = ttk.Frame(frame)
        center_frame.pack(fill="none", expand=True, anchor="center")  # Center horizontally and vertically

        # Listbox for exclusions
        self.exclusion_listbox = tk.Listbox(center_frame, height=50, width=100)
        self.exclusion_listbox.pack(side="left", fill="y", padx=10, pady=10)

        # Scrollbar for the listbox
        exclusion_scrollbar = ttk.Scrollbar(center_frame, orient="vertical", command=self.exclusion_listbox.yview)
        exclusion_scrollbar.pack(side="left", fill="y")
        self.exclusion_listbox.config(yscrollcommand=exclusion_scrollbar.set)

        # Buttons frame
        button_frame = ttk.Frame(center_frame)
        button_frame.pack(side="left", fill="y", padx=10, pady=10)

        # Buttons inside the button frame
        ttk.Button(button_frame, text="Refresh", bootstyle="warning", command=self.refresh_exclusion_list).pack(fill="x", pady=5)
        ttk.Button(button_frame, text="Remove Selected", bootstyle="warning", command=self.remove_exclusion_list_item).pack(fill="x", pady=5)
        ttk.Button(button_frame, text="Reset List", bootstyle="warning", command=self.reset_exclusion_list).pack(fill="x", pady=5)

        # Load exclusions immediately at startup
        self.refresh_exclusion_list()

    def remove_exclusion_list_item(self):
        """
        Remove selected items from the exclusion list.
        """
        selected_items = self.exclusion_listbox.curselection()
        if not selected_items:
            messagebox.showwarning("Warning", "No collection selected.")
            return

        used_collections = load_used_collections()
        for index in selected_items:
            item_text = self.exclusion_listbox.get(index)
            collection_name = item_text.split(" (")[0]
            if collection_name in used_collections:
                del used_collections[collection_name]

        save_used_collections(used_collections)
        self.refresh_exclusion_list()
        messagebox.showinfo("Success", "Selected collections removed from the exclusion list.")

    def reset_exclusion_list(self):
        """
        Reset the exclusion list and refresh the Exclusion List tab.
        """
        try:
            reset_exclusion_list_file()
            # Refresh the Exclusion List tab
            self.refresh_exclusion_list()
        except Exception as e:
            logging.error(f"Error resetting exclusion list: {e}")
            messagebox.showerror("Error", "Failed to reset the exclusion list.")

    def refresh_exclusion_list(self):
        """
        Refresh and populate the exclusion list from the saved exclusions file.
        """
        logging.info("Refreshing Exclusion List tab.")
        # Clear the listbox
        self.exclusion_listbox.delete(0, tk.END)

        # Load used collections
        used_collections = load_used_collections()

        # Populate the listbox with exclusions
        for collection_name, expiration_date in used_collections.items():
            self.exclusion_listbox.insert(tk.END, f"{collection_name} (Expires: {expiration_date})")

    def _create_user_exemptions_tab(self):
        """
        Create the User Exemptions tab with library sections and checkboxes.
        """
        frame = ttk.Frame(self.user_exemptions_tab, padding="10")
        frame.pack(fill="both", expand=True)

        # Top Save Button
        save_button = ttk.Button(frame, text="Save Exemptions", bootstyle="warning", command=self.save_user_exemptions_gui)
        save_button.pack(anchor="center", pady=(0, 10))

        # Explanation label
        explanation_label = ttk.Label(
            frame,
            text="Checkbox States: ✓ = User Exemption (permanent), Empty = Eligible for Pinning",
            font=("Segoe UI", 10, "italic"),
            wraplength=900,
            justify="center",
        )
        explanation_label.pack(anchor="center", pady=(0, 10))

        # Scrollable Canvas Frame
        scrollable_frame = ttk.Frame(frame)
        scrollable_frame.pack(fill="both", expand=True)

        # Create a canvas and scrollbar
        self.exemptions_canvas = tk.Canvas(scrollable_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(scrollable_frame, orient="vertical", command=self.exemptions_canvas.yview)
        self.exemptions_canvas.configure(yscrollcommand=scrollbar.set)

        # Pack canvas and scrollbar
        self.exemptions_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Frame for library sections inside the canvas
        self.libraries_frame = ttk.Frame(self.exemptions_canvas)
        self.canvas_window = self.exemptions_canvas.create_window((0, 0), window=self.libraries_frame, anchor="n")

        # Adjust scroll region dynamically
        def on_frame_configure(event):
            self.exemptions_canvas.configure(scrollregion=self.exemptions_canvas.bbox("all"))

        self.libraries_frame.bind("<Configure>", on_frame_configure)

        # Bind mousewheel scrolling
        def _on_mousewheel(event):
            self.exemptions_canvas.yview_scroll(-1 * (event.delta // 120), "units")

        self.exemptions_canvas.bind("<Enter>",
                                    lambda e: self.exemptions_canvas.bind_all("<MouseWheel>", _on_mousewheel))
        self.exemptions_canvas.bind("<Leave>", lambda e: self.exemptions_canvas.unbind_all("<MouseWheel>"))

        # Load libraries and populate
        self.refresh_user_exemptions()

    def save_user_exemptions_gui(self):
        """
        Save the user exemptions from the GUI to the file.
        """
        try:
            # Collect all selected exemptions across all libraries
            exemptions = []
            for library_name, checkboxes in self.user_exemption_checkboxes.items():
                for collection_name, var in checkboxes.items():
                    if var.get() == 1:  # If the checkbox is selected
                        exemptions.append(collection_name)

            # Save exemptions to file
            self.user_exemptions = exemptions
            save_user_exemptions(exemptions)
            messagebox.showinfo("Success", "User exemptions saved successfully.")
            logging.info("User exemptions saved successfully.")
        except Exception as e:
            logging.error(f"Error saving user exemptions: {e}")
            messagebox.showerror("Error", "Failed to save user exemptions.")

    def refresh_user_exemptions(self):
        """
        Refresh the list of collections for user exemptions.
        """
        # Clear existing widgets and reset the dictionary
        for widget in self.libraries_frame.winfo_children():
            widget.destroy()
        self.user_exemption_checkboxes = {}

        # Connect to Plex server if not already connected
        if not self.plex:
            try:
                self.plex = connect_to_plex(self.config)
            except Exception as e:
                logging.error("Error connecting to Plex server.")
                return

        # Grid positioning
        row, col = 0, 0  # Start at the first row and column

        # Process each library
        for library_name in self.config.get("libraries", []):
            try:
                # Create a labeled frame for the library
                library_frame = ttk.LabelFrame(self.libraries_frame, text=library_name, padding=10)
                library_frame.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
                self.user_exemption_checkboxes[library_name] = {}

                # Add a Select All checkbox
                select_all_var = tk.BooleanVar(value=False)  # Independent state for "Select All"
                ttk.Checkbutton(
                    library_frame,
                    text="Select All",
                    variable=select_all_var,
                    command=lambda lib=library_name, var=select_all_var: self._toggle_select_all(lib, var)
                ).pack(anchor="w", padx=5, pady=5)

                # Load collections for the library
                library = self.plex.library.section(library_name)
                for idx, collection in enumerate(library.collections()):
                    var = tk.IntVar(value=1 if collection.title in self.user_exemptions else 0)

                    # Alternate background colors for better readability
                    bg_color = "white" if idx % 2 == 0 else "lightgray"

                    cb = tk.Checkbutton(
                        library_frame,
                        text=collection.title,
                        variable=var,
                        anchor="w",
                        bg=bg_color
                    )
                    cb.pack(fill="x", padx=20, pady=2)
                    self.user_exemption_checkboxes[library_name][collection.title] = var

                # Update grid position
                col += 1  # Move to the next column
                if col >= 3:  # Wrap to the next row after 3 columns
                    col = 0
                    row += 1

            except Exception as e:
                logging.error(f"Error loading library '{library_name}': {e}")
                messagebox.showerror("Error", f"Error loading library '{library_name}': {e}")

    def _toggle_select_all(self, library_name, select_all_var):
        """
        Toggle all checkboxes in a specific library based on the 'Select All' state.

        Args:
            library_name (str): Name of the library.
            select_all_var (tk.BooleanVar): Variable linked to the 'Select All' checkbox.
        """
        new_state = 1 if select_all_var.get() else 0  # 1 = Checked, 0 = Unchecked
        for collection_title, var in self.user_exemption_checkboxes[library_name].items():
            var.set(new_state)

    def _on_library_selected(self, event=None):
        """
        Handler when a library is selected from the dropdown.

        Args:
            event (tk.Event, optional): Event object.
        """
        self._populate_library_time_blocks()
        self._refresh_schedule_summary()

    def _populate_library_time_blocks(self):
        """
        Populate time block input fields for the selected library.
        """
        library_name = self.selected_library.get()
        if not library_name:
            return

        # Reset inputs
        for block in self.time_block_entries.values():
            for field in block.values():
                field.delete(0, "end")

        # Fetch library time block data
        library_settings = self.config.get("libraries_settings", {}).get(library_name, {})
        time_blocks = library_settings.get("time_blocks", {})

        if not isinstance(time_blocks, dict):
            logging.error(f"Invalid time_blocks for library '{library_name}': {time_blocks}")
            return

        for block_name, entries in self.time_block_entries.items():
            block_data = time_blocks.get(block_name, {})
            entries["start_time"].insert(0, block_data.get("start_time", ""))
            entries["end_time"].insert(0, block_data.get("end_time", ""))
            entries["limit"].insert(0, str(block_data.get("limit", "")))

    def _validate_time_format(self, time_str):
        """
        Ensure the time format is HH:MM.

        Args:
            time_str (str): Time string to validate.

        Returns:
            bool: True if valid, False otherwise.
        """
        try:
            datetime.strptime(time_str, "%H:%M")
            return True
        except ValueError:
            return False

    def start_script(self, show_message=True):
        """
        Start the automation script in a separate thread to avoid blocking the GUI.

        Args:
            show_message (bool, optional): Whether to show a message upon starting.
        """
        if not self.script_thread or not self.script_thread.is_alive():
            # Clear the stop event before starting
            self.stop_event.clear()

            # Start the script in a separate thread with the latest configuration
            self.script_thread = threading.Thread(target=main, args=(self, self.stop_event), daemon=True)
            self.script_thread.start()

            # Update button states
            self.run_main_button.config(state="disabled")
            logging.info("Automation script started with the updated configuration.")
        else:
            logging.warning("Script is already running.")

    def stop_script(self, show_message=True):
        """
        Stop the automation script.

        Args:
            show_message (bool, optional): Whether to show a message upon stopping.
        """
        if self.script_thread and self.script_thread.is_alive():
            logging.info("Attempting to stop the automation script...")
            self.stop_event.set()  # Signal the main function to stop

            try:
                self.script_thread.join(timeout=10)  # Wait for the thread to finish (10 seconds timeout)
            except Exception as e:
                logging.error(f"Error stopping script thread: {e}")
            finally:
                self.script_thread = None  # Reset the thread reference

            logging.info("Automation script stopped.")
            self.run_main_button.config(state="normal")
        else:
            logging.warning("Script is not running.")

    def restart_program(self):
        """
        Restart the entire application.
        """
        logging.info("Restarting the program...")
        print("Restarting the program...")

        # Stop the automation script if it's running
        if self.script_thread and self.script_thread.is_alive():
            logging.info("Stopping the automation script before restarting...")
            print("Stopping the automation script before restarting...")
            self.stop_script()
            self.script_thread.join()
            logging.info("Automation script stopped.")
            print("Automation script stopped.")

        # Restart the program
        try:
            python = sys.executable
            os.execl(python, python, *sys.argv)
        except Exception as e:
            logging.error(f"Failed to restart the program: {e}")
            print(f"Failed to restart the program: {e}")
            messagebox.showerror("Error", f"Failed to restart the program: {e}")

# ------------------------------ Application Entry Point ------------------------------

if __name__ == "__main__":
    try:
        app = DynamiXGUI()
        app.mainloop()
    except Exception as e:
        logging.error(f"Unhandled exception: {e}")
        traceback.print_exc()
