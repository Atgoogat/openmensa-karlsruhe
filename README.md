# Openmensa Parser for Mensa Adenauerring, Karlsruhe

[https://openmensa.org/c/1719](https://openmensa.org/c/1719)

[https://www.sw-ka.de/de/hochschulgastronomie/speiseplan/mensa_adenauerring/](https://www.sw-ka.de/de/hochschulgastronomie/speiseplan/mensa_adenauerring/)

## Source
This parser scrapes the meal plan from https://www.sw-ka.de/de/hochschulgastronomie/speiseplan/mensa_adenauerring/ (one request per calendar week via `?kw=<week>`).

## Tests
```sh
pip install -r requirements.in pytest
python -m pytest tests
```

