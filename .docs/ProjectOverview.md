**Project: Elite Dangerous Exploration Data Logger - EDMC Plugin**

**Date:** May 28, 2025

**Objective:**
Develop a new, lightweight E:D Market Connector (EDMC) plugin specifically designed to capture and transmit detailed stellar and planetary/moon characteristics from the Elite Dangerous Pilot's Journal to an external web API. This plugin is intended for a scientific research project focused on analyzing star class composition and the detailed properties of celestial bodies within those systems. The plugin should be simple, maintainable, and easy for potential research contributors to install and use.

**Background & Context:**
Initial discussions explored modifying a forked version of the "BGS-Tally" plugin (`ArnarValur/BGS-Tally-Explorer`). While this provided a good learning base and confirmed the feasibility of data extraction, the BGS-Tally plugin is large and complex due to its focus on the Background Simulation (BGS). For the specific research goal, a more streamlined and focused plugin is desirable. The idea is to create a new plugin, potentially reusing well-designed, generic components (like robust HTTP request management or threading) from the BGS-Tally fork if they can be cleanly extracted and are suitable.

**Core Requirements for the New Plugin:**

1.  **Focused Data Extraction:**
    *   The plugin must *only* process journal events relevant to capturing stellar and planetary/moon and astroid characteristics.
    *   **Primary Events of Interest:**
        *   `FSDJump`: For system context (SystemName, SystemAddress, StarPos) and initial arrival star identification.
        *   `Scan`: This is the most critical event. It must differentiate between star scans and planet/moon scans and extract a specific, predefined set of characteristics for each.
        *   `SAAScanComplete`: To record if a body has been surface-mapped by the player, if this status is deemed relevant to the "detailed" analysis.
    *   **Data to Exclude:** All non-essential data for astrophysical characterization (e.g., faction states, commodity prices, mission data, player fuel levels, BGS-specific information, UI flow events like `FSSSignalDiscovered` unless they directly precede a necessary `Scan` event). The goal is a lean data payload.

2.  **Specific Data Fields to Capture (from previous detailed discussions):**
    *   **For Systems (from `FSDJump`):** `timestamp`, `event_type` ("FSDJump"), `commander_name`, `StarSystem`, `SystemAddress`, `StarPos`.
    *   **For Stars (from `Scan`):** `timestamp`, `event_type` ("Scan"), `event_subtype` ("StarScan"), `commander_name`, `SystemAddress`, `BodyID`, `BodyName`, `StarType`, `Subclass`, `StellarMass`, `Radius` (km), `AbsoluteMagnitude`, `Age_MY`, `SurfaceTemperature` (K), `Luminosity`, `RotationPeriod`, `AxialTilt`, and orbital parameters if applicable (`Parents`, `SemiMajorAxis`, etc.).
    *   **For Planets/Moons (from `Scan`):** `timestamp`, `event_type` ("Scan"), `event_subtype` ("PlanetScan"), `commander_name`, `SystemAddress`, `BodyID`, `BodyName`, `PlanetClass`, `TerraformState`, `AtmosphereType`, `AtmosphereComposition` (array), `Volcanism`, `MassEM`, `Radius` (km), `SurfaceGravity`, `SurfaceTemperature` (K), `SurfacePressure`, `Landable`, `Materials` (array), `Composition` (object), `TidalLock`, `Rings` (array), and orbital parameters (`Parents`, `SemiMajorAxis`, etc.).
    *   **For Mapped Status (from `SAAScanComplete`, optional):** `timestamp`, `event_type` ("SAAScanComplete"), `commander_name`, `SystemAddress`, `BodyID`, `BodyName`.

3.  **Data Transmission:**
    *   The plugin will send the extracted and structured data as a JSON payload to a configurable external web API endpoint via an HTTP POST request.
    *   **Crucially, all network calls must be performed in a separate worker thread** to prevent freezing the EDMC UI.
    *   The plugin should support an optional API key for authentication (e.g., sent as a Bearer token in the Authorization header).
    *   Robust error handling and logging for network requests are required.

4.  **Plugin Structure & EDMC Integration:**
    *   The plugin will be a new, self-contained folder (e.g., `Stellar-Analysis`) with a `load.py` file.
    *   `load.py` will implement standard EDMC plugin functions:
        *   `plugin_start(plugin_dir)`: Initialize settings, API client.
        *   `plugin_stop()`: Cleanup.
        *   `journal_entry(cmdr, is_beta, system, station, entry, state)`: Core logic to filter events and dispatch to processing functions.
        *   `plugin_prefs(parent, cmdr, is_beta)`: Provide a simple `tkinter`-based UI within EDMC settings for:
            *   Enabling/disabling the plugin.
            *   Configuring the API endpoint URL.
            *   Configuring the optional API key.
        *   `prefs_changed(cmdr, is_beta)`: Save settings using EDMC's config system.
    *   Helper functions within `load.py` (or a separate imported module if logic becomes complex) will handle the specifics of processing `FSDJump` and `Scan` events and managing the threaded API calls.

5.  **Data Flow Architecture:**
    *   Pilots Journal (Local) -> **New EDMC Plugin** (extracts, formats, sends via HTTP POST) -> **Web Application API Endpoint** (receives, validates) -> Web Application Server-Side Logic (processes, writes) -> **Firestore Database**.
    *   The plugin will **NOT** attempt to write directly to Firestore to maintain security and allow for server-side validation/logic.

6.  **Reusability from BGS-Tally (Conceptual):**
    *   If the BGS-Tally fork contains particularly well-implemented, generic, and easily extractable modules for:
        *   Threaded HTTP request management (e.g., a class that handles queuing, retries, and threading for `requests.post`).
        *   Robust configuration management beyond basic EDMC `config.get/set`.
    *   These could be considered for adaptation or direct inclusion into the new plugin to save development time, provided they don't bring in unnecessary BGS-specific dependencies. The primary focus, however, is on a new, lean implementation.

**Desired Outcome of this Phase (for the coding agent):**
A functional `load.py` (and any necessary supporting Python files) for a new EDMC plugin that:
*   Implements the settings UI as described.
*   Correctly identifies `FSDJump` and `Scan` events.
*   Extracts *only* the specified essential stellar and planetary characteristics.
*   Constructs a JSON payload for each relevant event.
*   Sends this payload to a configurable API endpoint using a non-blocking threaded HTTP POST request.
*   Includes basic logging for its operations and errors.
*   Is disabled by default and only acts when explicitly enabled by the user via settings.

---

For Pilot Journal documentation references, use the following url:

https://elite-journal.readthedocs.io/en/latest/Exploration.html