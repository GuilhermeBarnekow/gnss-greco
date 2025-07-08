import kivy
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.properties import NumericProperty, ListProperty
from kivy.lang import Builder
from gps_module import GNSSModule
from db_module import Database
import logging
import os
from datetime import datetime

# Configure logging
log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_file = os.path.join(log_dir, f'gss_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('GSS')
Builder.load_file('ui.kv')

# Set window size for 800x480
from kivy.core.window import Window
Window.size = (800, 480)

from kivy.uix.textinput import TextInput
from kivy.base import EventLoop

class GPSWidget(Widget):
    grid_cols = NumericProperty(5)
    grid_rows = NumericProperty(5)
    quadrant_colors = ListProperty([])  # List of colors for each quadrant
    gnss_connected_color = ListProperty([1, 0, 0, 1])  # Red by default (disconnected)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = logging.getLogger('GSS.GPSWidget')
        self.simulation_mode = False
        try:
            self.gnss = GNSSModule(port=None, baudrate=115200, simulation=True)
            self.logger.info("GNSS module initialized in simulation mode successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize GNSS module: {e}")
            # Set status to red to indicate error
            self.gnss_connected_color = [1, 0, 0, 1]
            self.gnss = None

        try:
            self.db = Database()
            self.logger.info("Database initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            self.db = None

        self.total_hectares = 0.0
        self.quadrant_colors = [(1, 1, 1, 1)] * (self.grid_cols * self.grid_rows)  # default white
        Clock.schedule_interval(self.update, 1.0 / 30.0)  # 30 FPS
        self.create_grid()
        self.keyboard = None
        self.logger.info("GPSWidget initialized successfully")

    def update(self, dt):
        if not self.gnss:
            return

        try:
            data = self.gnss.read_data()
            if data:
                # Update GNSS connection icon to green
                self.gnss_connected_color = [0, 1, 0, 1]
                # Update lat/lon labels
                try:
                    parts = data.split(',')
                    if len(parts) >= 3:
                        lat = float(parts[1])
                        lon = float(parts[2])
                        self.ids.lat_label.text = f"Lat: {lat:.6f}"
                        self.ids.lon_label.text = f"Lon: {lon:.6f}"
                        
                        if self.db:
                            try:
                                # Calculate hectares covered (dummy calculation for example)
                                self.total_hectares += 0.01
                                self.db.add_record(lat, lon, self.total_hectares)
                                self.update_grid_colors()
                            except Exception as e:
                                self.logger.error(f"Error updating database: {e}")
                        else:
                            self.logger.warning("Database not initialized, skipping record")
                    else:
                        self.logger.warning(f"Invalid GPS data format: {data}")
                except ValueError as e:
                    self.logger.error(f"Error parsing GPS coordinates: {e}")
                except Exception as e:
                    self.logger.error(f"Unexpected error processing GPS data: {e}")
                # Update tractor position on the grid based on lat/lon
                self.update_tractor_position(lat, lon)
            else:
                # No data, set GNSS icon to red
                self.gnss_connected_color = [1, 0, 0, 1]
                self.logger.debug("No GPS data received")
        except Exception as e:
            self.logger.error(f"Error reading GPS data: {e}")
            self.gnss_connected_color = [1, 0, 0, 1]

    # ... rest of the class remains unchanged


    def create_grid(self):
        grid = self.ids.grid
        grid.clear_widgets()
        for i in range(self.grid_cols * self.grid_rows):
            from kivy.uix.button import Button
            btn = Button(background_color=self.quadrant_colors[i])
            btn.bind(on_press=self.on_grid_cell_pressed)
            grid.add_widget(btn)

    def on_grid_cell_pressed(self, instance):
        index = self.ids.grid.children.index(instance)
        print(f"Grid cell {index} pressed")
        # Toggle green color for demonstration
        current_color = instance.background_color
        green = [0, 1, 0, 1]
        white = [1, 1, 1, 1]
        new_color = green if current_color == white else white
        instance.background_color = new_color


    def update_grid_colors(self):
        # Update quadrant colors based on total hectares and grid size
        green = [0, 1, 0, 1]
        white = [1, 1, 1, 1]
        # Simple logic: color quadrants green based on hectares covered
        num_green = int(self.total_hectares / (self.grid_cols * self.grid_rows) * 10)
        for i in range(self.grid_cols * self.grid_rows):
            color = green if i < num_green else white
            self.quadrant_colors[i] = color
        self.refresh_grid()

    def refresh_grid(self):
        grid = self.ids.grid
        for i, btn in enumerate(grid.children):
            btn.background_color = self.quadrant_colors[i]

    def set_route_a(self):
        print("Route A set")

    def set_route_b(self):
        print("Route B set")

    def show_keyboard(self, instance, value):
        if value:
            self._keyboard = Window.request_keyboard(self._keyboard_closed, self)
            if self._keyboard.widget:
                # If it is a widget, this means that it is a virtual keyboard
                pass
            self._keyboard.bind(on_key_down=self._on_keyboard_down)
        else:
            if hasattr(self, '_keyboard'):
                self._keyboard.unbind(on_key_down=self._on_keyboard_down)
                self._keyboard = None

    def _keyboard_closed(self):
        self._keyboard.unbind(on_key_down=self._on_keyboard_down)
        self._keyboard = None

    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
        if keycode[1] == 'enter':
            self.on_text_entered(self.ids.input_field.text)
            return True
        return False

    def on_text_entered(self, text):
        print(f"Text entered: {text}")
        # Process the entered text here, e.g., update grid size or other parameters
        try:
            value = int(text)
            if value > 0:
                self.grid_cols = value
                self.grid_rows = value
                self.quadrant_colors = [(1, 1, 1, 1)] * (self.grid_cols * self.grid_rows)
                self.create_grid()
        except ValueError:
            print("Invalid input for grid size")
        self.ids.input_field.text = ''

    def toggle_mode(self):
        self.simulation_mode = not self.simulation_mode
        self.gnss.stop()
        self.gnss = GNSSModule(port=None, baudrate=115200, simulation=self.simulation_mode)
        mode = "Simulação" if self.simulation_mode else "Real"
        print(f"Modo alterado para: {mode}")

class GPSApp(App):
    def build(self):
        return GPSWidget()

if __name__ == '__main__':
    GPSApp().run()
