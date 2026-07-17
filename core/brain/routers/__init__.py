from core.brain.routers.tv import ROUTES as tv_routes
from core.brain.routers.music import ROUTES as music_routes
from core.brain.routers.weather_time import ROUTES as wt_routes
from core.brain.routers.lists import ROUTES as lists_routes
from core.brain.routers.timer import ROUTES as timer_routes
from core.brain.routers.calendar import ROUTES as calendar_routes
from core.brain.routers.youtube import ROUTES as youtube_routes
from core.brain.routers.smart_home import ROUTES as smart_home_routes

# Agrega todas as rotas em uma única lista
ROUTES = tv_routes + music_routes + wt_routes + lists_routes + timer_routes + calendar_routes + youtube_routes + smart_home_routes
