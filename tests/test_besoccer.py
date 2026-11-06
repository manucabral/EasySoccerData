"""
Unit tests for BeSoccer HTML parsers.
"""

from esd.besoccer.types import parse_livescore_html, parse_standings_html


def test_parse_besoccer_livescore_html():
    sample_html = """
    <div class="panel">
      <div class="panel-head">
        <a href="https://es.besoccer.com/competicion/torneo_final" data-cy="competitionName">
          <div class="panel-title"><span>Clausura Argentina</span></div>
        </a>
      </div>
      <a class="match-link match-home" id="match-2026240000"
         href="https://es.besoccer.com/partido/aldosivi/ca-river-plate/2026240000"
         data-status-id="4" data-local-id="5902" data-visitor-id="593"
         starttime="2026-11-05T19:00:00+01:00">
        <div class="info-head">
          <div class="middle-info tv-info">ESPN Premium</div>
        </div>
        <div class="team-box">
          <div class="team-info">
            <div class="team-name">Aldosivi</div>
            <img class="team-shield" src="https://cdn.resfu.com/img_data/equipos/5902.png" />
          </div>
          <div class="marker">
            <span><span class="r1">0</span>-<span class="r2">2</span></span>
          </div>
          <div class="team-info">
            <img class="team-shield" src="https://cdn.resfu.com/img_data/equipos/593.png" />
            <div class="team-name">River Plate</div>
          </div>
        </div>
      </a>
    </div>
    """
    matches = parse_livescore_html(sample_html)
    assert len(matches) == 1
    assert matches[0].id == 2026240000
    assert matches[0].competition_name == "Clausura Argentina"
    assert matches[0].home_team.name == "Aldosivi"
    assert matches[0].home_team.score == 0
    assert matches[0].away_team.name == "River Plate"
    assert matches[0].away_team.score == 2
    assert matches[0].tv_network == "ESPN Premium"


def test_parse_besoccer_standings_html():
    sample_html = """
    <table>
      <tr class="row-body">
        <td class="number-box"><div>1</div></td>
        <td class="td-shield">
          <img src="https://cdn.resfu.com/img_data/equipos/3068.png" alt="Instituto" />
        </td>
        <td class="name">
          <a href="https://es.besoccer.com/equipo/instituto">
            <span class="team-name">Instituto</span>
          </a>
          <div class="match-res">
            <span class="bg-match-res win">V</span>
            <span class="bg-match-res draw">E</span>
          </div>
        </td>
        <td class="green bold br-l">33</td>
        <td>15</td>
        <td>10</td>
        <td>3</td>
        <td>2</td>
        <td>24</td>
        <td>13</td>
        <td>+11</td>
      </tr>
    </table>
    """
    rows = parse_standings_html(sample_html)
    assert len(rows) == 1
    assert rows[0].position == 1
    assert rows[0].team.name == "Instituto"
    assert rows[0].team.id == 3068
    assert rows[0].points == 33
    assert rows[0].goal_diff == 11
    assert rows[0].form == ["V", "E"]
