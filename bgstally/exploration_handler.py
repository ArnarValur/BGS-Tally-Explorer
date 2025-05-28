import json
import threading
import time
from datetime import datetime, UTC
from queue import Queue, Empty # Modified import
from typing import Dict, List, Optional
from os import path

import requests
from bgstally.debug import Debug
from bgstally.utils import get_by_path

class ExplorationDataHandler:
    """
    Handles exploration data collection and transmission to external API.
    
    Focuses on cataloging and analyzing star class composition, type, and 
    planetary/moon bodies with their fundamental physical, chemical, and 
    orbital characteristics for in-game scientific research.
    
    Processes:
    - FSDJump events for system context and galactic positioning
    - Scan events for detailed stellar and planetary body characteristics
      This module operates independently of BGS functionality.
    """
    
    def __init__(self, bgstally):
        self.bgstally = bgstally
        self.enabled = False
        self.api_endpoint = ""
        self.api_key = ""
        self.batch_size = 10
        self.batch_timeout = 30  # seconds
        
        # Event queue for batching
        self.events_queue: Queue = Queue()
        self.last_batch_time = time.time()
        
        # Worker thread for API communication
        self.worker_thread = None
        self.worker_running = False
        
        # Events we're interested in - FSDJump for system context and Scan
        # for stellar/planetary data
        self.exploration_events = {'FSDJump', 'Scan'}

    def start_worker(self):
        """Start the background worker thread for API communication."""
        if self.worker_thread is None or not self.worker_thread.is_alive():
            self.worker_running = True
            self.worker_thread = threading.Thread(
                target=self._worker_loop, 
                name="BGSTally-Explorer-Worker",
                daemon=True
            )
            self.worker_thread.start()
            Debug.logger.info("Exploration data worker thread started")

    def stop_worker(self):
        """Stop the background worker thread."""
        self.worker_running = False
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5)
            Debug.logger.info("Exploration data worker thread stopped")

    def update_settings(self, enabled: bool, api_endpoint: str,
                        api_key: str = ""):
        """Update exploration module settings."""
        self.enabled = enabled
        self.api_endpoint = api_endpoint.rstrip('/')
        self.api_key = api_key
        if self.enabled and self.api_endpoint:
            self.start_worker()
        else:  # Corrected indentation
            self.stop_worker()
            # Clear queue if disabled
            with self.events_queue.mutex:
                self.events_queue.queue.clear()

    def journal_entry(self, cmdr: str, is_beta: bool, system: str,
                      station: str, entry: dict, state: dict):
        """
        Process journal entries for system entry and stellar/planetary 
        scan events. Called from the main BGSTally journal_entry method.
        """
        if not self.enabled or not self.api_endpoint or is_beta:
            return
        
        event_type = entry.get('event')
        if event_type not in self.exploration_events:
            return
        
        # DEBUG: Log the raw journal entry
        Debug.logger.info(f"[EXPLORATION DEBUG] Processing event: "
                          f"{event_type}")
        # Debug.logger.info(f"[EXPLORATION DEBUG] Raw journal entry: "
        #                   f"{json.dumps(entry, indent=2)}")
        
        # Build exploration data payload
        exploration_payload = self._build_exploration_payload(cmdr, entry,
                                                               state)
        if exploration_payload:
            # DEBUG: Log the processed payload
            Debug.logger.info(f"[EXPLORATION DEBUG] Generated payload: "
                              f"{json.dumps(exploration_payload, indent=2)}")
            self.events_queue.put(exploration_payload)
            Debug.logger.debug(f"Queued exploration event: {event_type}")
        else:
            Debug.logger.warning(f"[EXPLORATION DEBUG] Failed to build "
                                 f"payload for event: {event_type}")
    
    def _build_exploration_payload(self, cmdr: str, entry: dict,
                                   state: dict) -> Optional[Dict]:
        """
        Build exploration data payload from journal entry.
        Handles FSDJump for system context and Scan events for stellar/planetary characteristics.
        """
        event_type = entry.get('event')
        timestamp = entry.get(
            'timestamp',
            datetime.now(UTC).isoformat()
        )
        
        try:
            if event_type == 'FSDJump':
                return self._build_system_entry_payload(cmdr, entry, timestamp)
            elif event_type == 'Scan':
                return self._build_scan_payload(cmdr, entry, timestamp)
            else:
                return None
                
        except Exception as e:
            Debug.logger.error(f"Error building exploration payload: {e}")
            return None
    
    def _build_system_entry_payload(self, cmdr: str, entry: dict, timestamp: str) -> Optional[Dict]:
        """Build SystemEntry payload from FSDJump event."""
        payload = {
            'commander_name': cmdr,
            'event_timestamp': timestamp,
            'event_type': 'SystemEntry',
            'system_address': entry.get('SystemAddress'),
            'data': {
                'SystemAddress': entry.get('SystemAddress'),
                'StarSystem': entry.get('StarSystem'),
                'StarPos': entry.get('StarPos'),
                'WasDiscovered': entry.get('WasDiscovered'),  # System-level discovery, often null in FSDJump
                'BodyName': entry.get('Body'),  # Name of the arrival body (e.g., main star)
                'BodyID': entry.get('BodyID'),    # ID of the arrival body
                'Commander': cmdr
            }
        }
        return payload
    
    def _build_scan_payload(self, cmdr: str, entry: dict, timestamp: str) -> Optional[Dict]:
        """Build scan payload for stellar or planetary bodies, including asteroid clusters."""
        event_subtype = None
        is_asteroid_cluster = False

        if entry.get('StarType'):
            event_subtype = 'StellarBodyScan'
        elif entry.get('PlanetClass'):
            event_subtype = 'PlanetaryBodyScan'
        else:
            # Check for asteroid cluster by looking for a 'Ring' in Parents
            parents = entry.get('Parents')
            if isinstance(parents, list):
                for parent_info in parents:
                    if isinstance(parent_info, dict) and 'Ring' in parent_info:
                        is_asteroid_cluster = True
                        event_subtype = 'AsteroidClusterScan'
                        break
        
        if not event_subtype:
            # Skip if it's not a star, planet/moon, or identified asteroid cluster
            return None

        payload = {
            'commander_name': cmdr,
            'event_timestamp': timestamp,
            'event_type': event_subtype,
            'system_address': entry.get('SystemAddress'),
            'body_id': entry.get('BodyID'),
            'data': {}
        }
        
        # Universal scan data
        scan_data = {
            'BodyName': entry.get('BodyName'),
            'BodyID': entry.get('BodyID'),
            'SystemAddress': entry.get('SystemAddress'),
            'DistanceFromArrivalLS': entry.get('DistanceFromArrivalLS'),
            'Commander': cmdr,
            'WasDiscovered': entry.get('WasDiscovered'),
            'WasMapped': entry.get('WasMapped')
        }

        if event_subtype == 'StellarBodyScan':
            scan_data.update({
                # Essential stellar characteristics
                'StarType': entry.get('StarType'),
                'Subclass': entry.get('Subclass'),
                'StellarMass': entry.get('StellarMass'),
                'Radius': entry.get('Radius'),
                'AbsoluteMagnitude': entry.get('AbsoluteMagnitude'),
                'Age_MY': entry.get('Age_MY'),
                'SurfaceTemperature': entry.get('SurfaceTemperature'),
                'Luminosity': entry.get('Luminosity'),
                'RotationPeriod': entry.get('RotationPeriod'),
                'AxialTilt': entry.get('AxialTilt')
            })
            
            # Orbital characteristics for secondary stars
            if entry.get('Parents'):
                scan_data['Parents'] = entry.get('Parents')
            
            if entry.get('SemiMajorAxis') is not None:
                scan_data.update({
                    'SemiMajorAxis': entry.get('SemiMajorAxis'),
                    'Eccentricity': entry.get('Eccentricity'),
                    'OrbitalInclination': entry.get('OrbitalInclination'),
                    'Periapsis': entry.get('Periapsis'),
                    'OrbitalPeriod': entry.get('OrbitalPeriod')
                })
        
        # Planet/moon-specific data
        elif event_subtype == 'PlanetaryBodyScan':
            scan_data.update({
                # Essential planetary/moon characteristics
                'PlanetClass': entry.get('PlanetClass'),
                'TerraformState': entry.get('TerraformState'),
                'AtmosphereType': entry.get('AtmosphereType'),
                'AtmosphereComposition': entry.get('AtmosphereComposition', []),
                'Volcanism': entry.get('Volcanism'),
                'MassEM': entry.get('MassEM'),
                'Radius': entry.get('Radius'),
                'SurfaceGravity': entry.get('SurfaceGravity'),
                'SurfaceTemperature': entry.get('SurfaceTemperature'),
                'SurfacePressure': entry.get('SurfacePressure'),
                'Landable': entry.get('Landable'),
                'Materials': entry.get('Materials', []),
                'Composition': entry.get('Composition', {}),
                'TidalLock': entry.get('TidalLock')
            })
            
            # Essential orbital characteristics
            if entry.get('Parents'):
                scan_data['Parents'] = entry.get('Parents')
            
            if entry.get('SemiMajorAxis') is not None:
                scan_data.update({
                    'SemiMajorAxis': entry.get('SemiMajorAxis'),
                    'Eccentricity': entry.get('Eccentricity'),
                    'OrbitalInclination': entry.get('OrbitalInclination'),
                    'Periapsis': entry.get('Periapsis'),
                    'OrbitalPeriod': entry.get('OrbitalPeriod')
                })
            
            # Rotation data (if available)
            if entry.get('RotationPeriod') is not None:
                scan_data.update({
                    'RotationPeriod': entry.get('RotationPeriod'),
                    'AxialTilt': entry.get('AxialTilt')
                })

        elif event_subtype == 'AsteroidClusterScan':
            # Asteroid cluster specific data
            if entry.get('Parents'): # Already checked but good to be explicit
                scan_data['Parents'] = entry.get('Parents')
            pass

        if event_subtype == 'StellarBodyScan' or event_subtype == 'PlanetaryBodyScan':
            if entry.get('Rings'):
                rings_data = []
                for ring in entry.get('Rings', []):
                    ring_info = {
                        'Name': ring.get('Name'),
                        'RingClass': ring.get('RingClass'),
                        'MassMT': ring.get('MassMT'),
                        'InnerRad': ring.get('InnerRad'),
                        'OuterRad': ring.get('OuterRad')
                    }
                    rings_data.append(ring_info)
                scan_data['Rings'] = rings_data
                
                # Reserve level for planetary rings
                if entry.get('PlanetClass') and entry.get('ReserveLevel'):
                    scan_data['ReserveLevel'] = entry.get('ReserveLevel')
        
        payload['data'] = scan_data
        return payload
    
    def _worker_loop(self):
        """Main worker loop for processing queued events."""
        batch = []
        
        while self.worker_running:
            try:
                current_time = time.time()
                
                # Collect events from queue
                while not self.events_queue.empty() and len(batch) < self.batch_size:
                    try:
                        event = self.events_queue.get_nowait()
                        batch.append(event)
                    except Empty:
                        break
                
                # Send batch if conditions are met
                should_send = (
                    len(batch) >= self.batch_size or
                    (len(batch) > 0 and current_time - self.last_batch_time >= self.batch_timeout)
                )
                
                if should_send and batch:
                    self._send_batch(batch)
                    batch.clear()
                    self.last_batch_time = current_time
                
                time.sleep(1)  # Check every second
                
            except Exception as e:
                Debug.logger.error(f"Error in exploration worker loop: {e}")
                time.sleep(5)  # Wait longer on error
    
    def _send_batch(self, batch: List[Dict]):
        """Send a batch of events to the API endpoint."""
        if not self.api_endpoint or not batch:
            return
        
        try:
            headers = {'Content-Type': 'application/json'}
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'
            
            # Send as array for batch processing
            response = requests.post(
                f"{self.api_endpoint}/exploration/events",
                json=batch,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                Debug.logger.info(f"Successfully sent {len(batch)} exploration events")
            else:
                Debug.logger.warning(
                    f"API returned status {response.status_code}: "
                    f"{response.text}"
                )
                
        except requests.exceptions.Timeout:
            Debug.logger.error("Timeout sending exploration data to API")
        except requests.exceptions.ConnectionError:
            Debug.logger.error("Connection error sending exploration data to API")
        except Exception as e:
            Debug.logger.error(f"Unexpected error sending exploration data: {e}")
