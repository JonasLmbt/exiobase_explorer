from .registry import stage_registry
from .stage_bubble import StageBubbleMethod
from .region_registry import region_registry
from .region_methods import RegionWorldMapMethod, RegionTopNMethod, RegionFlopNMethod, RegionPieMethod

stage_registry.register(StageBubbleMethod())

region_registry.register(RegionWorldMapMethod())
region_registry.register(RegionTopNMethod())
region_registry.register(RegionFlopNMethod())
region_registry.register(RegionPieMethod())
