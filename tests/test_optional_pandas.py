"""Core clients remain importable when pandas is not installed."""

import subprocess
import sys


def test_core_import_and_actionable_error_without_pandas():
    code = '''
import importlib.abc
import sys

class WithoutPandas(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "pandas" or fullname.startswith("pandas."):
            raise ModuleNotFoundError("No module named 'pandas'", name="pandas")
        if fullname == "pyarrow" or fullname.startswith("pyarrow."):
            raise ModuleNotFoundError("No module named 'pyarrow'", name="pyarrow")

sys.meta_path.insert(0, WithoutPandas())
import esd
assert "pandas" not in sys.modules
assert "pyarrow" not in sys.modules
assert esd.ESPNClient() is not None
from esd.espn.types import ESPNMatch
match = esd.normalize_match(ESPNMatch(id="001"))
assert match.match_id == "001"
assert match.source == "espn"
assert "pandas" not in sys.modules
from unittest.mock import Mock
from esd.espn.types import ESPNSeasonCalendar
import esd.datasets
client = Mock()
client.get_season_calendar.return_value = ESPNSeasonCalendar("eng.1", 2024, ("2024-08-16",))
client.get_scoreboard.return_value = []
esd.datasets.ESPNClient = Mock(return_value=client)
dataset = esd.load_dataset(source="espn", league="eng.1", season=2024, request_delay=0)
assert dataset.complete
assert dataset.match_records == ()
assert "pandas" not in sys.modules
import esd._provider_datasets as providers
providers.get_api_json = lambda *args, **kwargs: {"games": []}
other = esd.load_dataset(source="scores365", league=72, season=2024,
    start_date="2024-08-16", end_date="2024-08-16", request_delay=0)
assert other.complete and other.match_records == ()
providers.get_api_json = lambda *args, **kwargs: {"dates": [], "players": []}
other = esd.load_dataset(source="understat", league="EPL", season=2024,
    tables=["match_stats", "player_stats", "shots"], request_delay=0)
assert other.complete
providers.get_api_json = lambda *args, **kwargs: {"events": [], "hasNextPage": False}
other = esd.load_dataset(source="sofascore", league=17, season=2024,
    season_id=61627, request_delay=0)
assert other.complete
assert "pandas" not in sys.modules and "pyarrow" not in sys.modules
import esd._remaining_datasets as remaining
providers.get_api_json = lambda *args, **kwargs: {
    "LeagueInfo": [36, "League", "2024-2025"], "TeamInfo": [], "ScheduleList": {}}
assert esd.load_dataset(source="goaloo", league=36, season=2024,
    source_season="2024-2025", request_delay=0).complete
remaining.get_text = lambda *args, **kwargs: '<table id="sched_empty"><tbody></tbody></table>'
assert esd.load_dataset(source="fbref", league=9, season=2024,
    start_date="2024-08-16", end_date="2024-08-16", request_delay=0).complete
remaining.get_text = lambda *args, **kwargs: '<a data-cy="competitionName" href="/competicion/other">Other</a>'
assert esd.load_dataset(source="besoccer", league="premier_league", season=2024,
    start_date="2024-08-16", end_date="2024-08-16", request_delay=0).complete
remaining.get_api_json = lambda *args, **kwargs: {"leagues": []}
assert esd.load_dataset(source="promiedos", league="hc", season=2024,
    start_date="2024-08-16", end_date="2024-08-16", request_delay=0).complete
providers.get_api_json = lambda *args, **kwargs: {"data": {"id": "9", "name": "Player"}}
entity = esd.load_dataset(source="transfermarkt", league="GB1", season=2024,
    tables=["players"], player_ids=[9], request_delay=0)
assert entity.complete and entity.player_records[0].player_id == "9"
report = esd.check_dataset_compatibility(dataset, dataset)
assert report.schema_compatible
assert "pandas" not in sys.modules and "pyarrow" not in sys.modules
try:
    esd.to_dataframe([])
except ImportError as exc:
    assert "EasySoccerData[pandas]" in str(exc)
else:
    raise AssertionError("Missing pandas must raise ImportError")
try:
    dataset.matches
except ImportError as exc:
    assert "EasySoccerData[pandas]" in str(exc)
else:
    raise AssertionError("Dataset frames require pandas")
import tempfile
from pathlib import Path
with tempfile.TemporaryDirectory() as directory:
    try:
        dataset.save(Path(directory) / "saved")
    except ImportError as exc:
        assert "EasySoccerData[parquet]" in str(exc)
    else:
        raise AssertionError("Saving requires the parquet extra")
    try:
        esd.open_dataset(directory)
    except ImportError as exc:
        assert "EasySoccerData[parquet]" in str(exc)
    else:
        raise AssertionError("Opening requires the parquet extra")
'''
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                            timeout=30, check=False)
    assert result.returncode == 0, result.stderr


def test_disk_cache_resumes_in_another_process_without_optional_dependencies(tmp_path):
    code = '''
import importlib.abc
import sys

class WithoutExtras(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in ("pandas", "pyarrow"):
            raise ModuleNotFoundError("Optional package blocked", name=fullname.split(".")[0])

sys.meta_path.insert(0, WithoutExtras())
import esd
import esd.espn.service
calls = []

def fetch(url, **kwargs):
    calls.append(url)
    if sys.argv[2] == "resume":
        raise AssertionError("Resume must use disk responses")
    return {"events": [], "leagues": [{"slug": "eng.1", "season": {"year": 2024},
            "calendarType": "day", "calendar": ["2024-08-16T07:00Z"]}]}

esd.espn.service.get_api_json = fetch
result = esd.load_dataset(source="espn", league="eng.1", season=2024,
                          cache_dir=sys.argv[1], request_delay=0)
assert result.complete
assert len(calls) == (2 if sys.argv[2] == "prime" else 0)
assert "pandas" not in sys.modules and "pyarrow" not in sys.modules
'''
    for mode in ("prime", "resume"):
        result = subprocess.run([sys.executable, "-c", code, str(tmp_path), mode],
                                capture_output=True, text=True, timeout=30, check=False)
        assert result.returncode == 0, result.stderr
