# Project Adaption: BGS-Tally to Stellar-Analysis-Logger

This document outlines the plan for creating a new, lightweight Elite Dangerous Market Connector (EDMC) plugin, `Stellar-Analysis-Logger`, by adapting components from the existing `BGS-Tally` plugin.

## 1. TASK DESCRIPTION

The primary goal is to develop a "stripped down" plugin focused on capturing specific exploration-related journal events, extracting predefined data, and sending this data to a configurable external API.

**Core Requirements:**
*   **Event Capturing:** Listen for `FSDJump`, `Scan`, and optionally `SAAScanComplete` journal events.
*   **Data Extraction:** Extract predefined stellar and planetary characteristics as detailed in `ProjectOverview.md`.
*   **Data Transmission:** Send data as a JSON payload to a user-configurable external API endpoint.
    *   Must use a non-blocking, threaded HTTP POST request.
*   **User Interface:** A simple Tkinter-based settings UI for:
    *   Enabling/disabling the plugin.
    *   Configuring the API URL.
    *   Configuring an optional API key.
*   **Logging:** Basic logging for diagnostics.
*   **Default State:** The plugin should be disabled by default.
*   **Licensing:** Reuse of MIT-licensed code from BGS-Tally is permitted.

## 2. BGS-TALLY CODEBASE ANALYSIS & REUSABLE COMPONENTS

The following components from `BGS-Tally-Explorer` have been identified as relevant for adaptation or inspiration:

*   **`bgstally\exploration_handler.py`**:
    *   **Relevance:** Highly relevant. Already handles exploration event processing, payload building, and threaded data sending.
    *   **Adaptation:** Will be a core piece, modified for the specific data fields and simpler API interaction of the new plugin.
*   **`bgstally\requestmanager.py`**:
    *   **Relevance:** Provides a good basis for a robust, threaded HTTP client.
    *   **Adaptation:** Could be adapted into a generic `HttpClient` class for the new plugin, potentially offering better error handling and retry mechanisms than the direct `requests.post` in `ExplorationDataHandler`. The alternative is to refine the sending mechanism within the adapted `ExplorationDataHandler`.
*   **`bgstally\state.py`**:
    *   **Relevance:** Its approach to managing plugin settings (using Tkinter variables linked to EDMC's config object) is a good model.
    *   **Adaptation:** The principles will be used for simpler settings management (plugin enabled, API URL, API key). Exploration-specific settings are directly relevant.
*   **`bgstally\debug.py`**:
    *   **Relevance:** Demonstrates a good logging setup.
    *   **Adaptation:** The style will be adopted, but implementation will use Python's standard `logging` module directly for self-containment.
*   **`bgstally\ui.py`**:
    *   **Relevance:** The `_add_exploration_settings` method provides a good example for the new plugin's settings panel.
    *   **Adaptation:** Will serve as a template for creating the simpler UI.
*   **`bgstally\constants.py`**:
    *   **Relevance:** Contains useful Enums like `CheckStates` and datetime formats.
    *   **Adaptation:** These can be directly reused.
*   **`bgstally\utils.py`**:
    *   **Relevance:** The `get_by_path` function is valuable for safely accessing nested data within journal entries.
    *   **Adaptation:** This utility function will be extracted and reused.
*   **`bgstally\widgets.py`**:
    *   **Relevance:** `EntryPlus` could be a nice-to-have for the settings UI.
    *   **Adaptation:** Optional inclusion if its features are desired for the API URL/key input fields.
*   **`bgstally\updatemanager.py`**:
    *   **Relevance:** Useful for future auto-updates.
    *   **Adaptation:** Not essential for the initial version but can be integrated later.
*   **`bgstally\api.py` & `bgstally\apimanager.py`**:
    *   **Relevance:** These handle interactions with (potentially multiple) defined API endpoints in BGS-Tally.
    *   **Adaptation:** Considered overkill for the initial version of `Stellar-Analysis-Logger`, which targets a single, user-configured API endpoint. The simpler, direct sending approach (either from an adapted `ExplorationDataHandler` or a new minimal HTTP client) is preferred. These modules would be relevant if future versions require support for multiple, distinctly configured API targets.

## 3. COMPONENTS TO BE EXCLUDED

The majority of BGS-Tally specific modules will be discarded for this focused plugin, including (but not limited to):
*   `bgstally\bgstally.py` (main BGS-Tally application logic)
*   `bgstally\activitymanager.py`
*   `bgstally\discord.py`
*   `bgstally\colonisation.py`
*   `bgstally\fleetcarrier.py`
*   `bgstally\market.py`
*   `bgstally\missionlog.py`
*   `bgstally\objectivesmanager.py`
*   `bgstally\overlay.py`
*   `bgstally\targetmanager.py`
*   `bgstally\tick.py`
*   `bgstally\webhookmanager.py`
*   Most UI components not related to the simple settings panel.

## 4. PLANNED IMPLEMENTATION STEPS FOR `Stellar-Analysis-Logger`

1.  **New Plugin Scaffolding:**
    *   Create the new plugin folder (e.g., `Stellar-Analysis-Logger`).
    *   Create the main `load.py` file.
2.  **Core `load.py` Implementation:**
    *   Implement standard EDMC plugin functions (`plugin_start`, `plugin_stop`, `journal_entry`, `plugin_prefs`, `prefs_changed`).
    *   Develop the `tkinter`-based settings UI for enabling/disabling, API URL, and API key. `load.py` will delegate most logic to other specialized modules/classes.
3.  **Settings Management:**
    *   Implement loading and saving of settings (plugin enabled, API URL, API key) using EDMC's `config` object. This will be encapsulated within a **dedicated settings management module and class** (e.g., `settings_manager.py` containing a `SettingsManager` class), inspired by `BGS-Tally-Explorer/bgstally/state.py`. `load.py` will instantiate and interact with this manager.
4.  **Logging Implementation:**
    *   Set up standard Python `logging`. The core logging configuration and any helper functions will be placed in a **dedicated logging module** (e.g., `logger.py`). Modules will import and use this pre-configured logger. This approach is inspired by `BGS-Tally-Explorer/bgstally/debug.py`.
5.  **HTTP Client Implementation:**
    *   **Adopt an OOP approach by adapting `BGS-Tally-Explorer/bgstally/requestmanager.py` into a generic, reusable `HttpClient` class** within its own module (e.g., `http_client.py`). This class will handle the threaded POST requests and encapsulate all HTTP communication logic.
6.  **Data Handling Logic (adapting `ExplorationDataHandler`):**
    *   Extract and significantly adapt `BGS-Tally-Explorer/bgstally/exploration_handler.py` into a new module (e.g., `data_handler.py` or `exploration_logger.py`).
    *   Modify its payload construction methods (e.g., `_build_system_entry_payload`, `_build_scan_payload`) to precisely match the data fields specified in `ProjectOverview.md`.
    *   Ensure it uses the API URL and key from the plugin's settings.
    *   Integrate it with the chosen HTTP client.
7.  **Integration:**
    *   In `load.py`'s `journal_entry` function, filter for `FSDJump`, `Scan`, (and `SAAScanComplete` if included) and pass them to the adapted data handler.
    *   Ensure the data handler's worker thread for sending data is managed correctly during plugin start/stop and when settings (like API URL or enabled state) are changed.
8.  **Utility Code:**
    *   Create a `constants.py` for shared values (e.g., `CheckStates` from BGS-Tally, datetime formats).
    *   Create a `utils.py` and include the `get_by_path` function from BGS-Tally.
    *   Optionally, create `widgets.py` if `EntryPlus` (or other custom widgets) are used for the UI.

This plan aims to leverage the robust and tested components of BGS-Tally while creating a new, focused, and maintainable plugin for exploration data logging.
