from pathlib import Path
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / 'app.py'

def test_dashboard_without_credentials_or_data(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    app=AppTest.from_file(str(APP)).run(timeout=15)
    assert not app.exception
    assert app.title[0].value=='Market Research Lab'
    for section in ['Strategy Lab','Risk Center','Paper Portfolio','Research Journal','Probability Lab','Event Intelligence']:
        app.sidebar.radio[0].set_value(section).run(timeout=15)
        assert not app.exception
    assert not list(tmp_path.glob('reports/*'))
