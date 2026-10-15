"""Additive budget contrast. Original calibration code and settings are unchanged."""
from bench import *
PROFILES['clean-think-long']={**PROFILES['clean-think'],'thinking_budget':3072}
PROFILES['clean-native-long']={**PROFILES['clean-native'],'thinking_budget':3072}
