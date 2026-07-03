from orchestrator.layers.l1_crawler import CrawlerLayer
from orchestrator.layers.l2_content import ContentLayer
from orchestrator.layers.l3_storyboard import StoryboardLayer
from orchestrator.layers.l4_render import RenderLayer
from orchestrator.layers.l5_scheduler import SchedulerLayer
from orchestrator.layers.l6_qa import QALayer
from orchestrator.layers.l7_publish import PublishLayer
from orchestrator.layers.l8_data import DataLayer
from orchestrator.layers.base import BaseLayer

LAYER_REGISTRY: dict[str, BaseLayer] = {
    "L1": CrawlerLayer(),
    "L2": ContentLayer(),
    "L3": StoryboardLayer(),
    "L4": RenderLayer(),
    "L5": SchedulerLayer(),
    "L6": QALayer(),
    "L7": PublishLayer(),
    "L8": DataLayer(),
}

DEFAULT_PIPELINE = ["L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8"]
