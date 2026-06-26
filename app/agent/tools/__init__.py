from app.agent.tools.search_home_docs import search_home_docs
from app.agent.tools.web_search import web_search
from app.agent.tools.image_analysis import analyze_image
from app.agent.tools.request_action import request_action

ALL_TOOLS = [search_home_docs, web_search, analyze_image, request_action]