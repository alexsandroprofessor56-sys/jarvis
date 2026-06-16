import config.settings as settings

def test_evolve_config_default():
    cfg = settings.load()
    assert "evolution" in cfg
    assert cfg["evolution"]["enabled"] is True
    assert cfg["evolution"]["max_changes_per_hour"] == 5
